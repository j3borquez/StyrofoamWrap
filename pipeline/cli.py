# pipeline/cli.py

import os
import argparse
import subprocess
from pathlib import Path

# --- Configuration and Utility Imports ---
from pipeline.config import settings
from pipeline.asset_locator import FilesystemLocator
from pipeline.hip_manager import HoudiniHipManager
from pipeline.solaris_material_manager import setup_solaris_materials_from_sops
from pipeline.submit_config_generator import create_submit_config_script, get_default_submit_config_path

# Attempt to import the Deadline submitter, but don't fail if it's not there.
try:
    from pipeline.job_submitter import DeadlineSubmitter
except ImportError:
    DeadlineSubmitter = None
    print("Warning: DeadlineSubmitter module not found. Job submission will be disabled.")


def main():
    parser = argparse.ArgumentParser(
        description="StyrofoamWrap: A pipeline tool to import assets, create Solaris materials, and submit to a render farm."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Perform all steps except saving the HIP file and submitting jobs."
    )
    parser.add_argument(
        "--launch-local", action="store_true",
        help="Launch Houdini GUI and execute TOPs with local scheduler."
    )
    parser.add_argument(
        "--launch-deadline", action="store_true",
        help="Launch Houdini GUI and execute TOPs with Deadline scheduler."
    )
    parser.add_argument(
        "--clean-modified", action="store_true",
        help="Remove existing modified USD files before processing."
    )
    args = parser.parse_args()

    # --- Path Resolution ---
    assets_dir = Path(settings.assets_dir).resolve()
    hip_path = Path(settings.hip_path).resolve()
    print(f"Project Assets Directory: {assets_dir}")
    print(f"Houdini Project File: {hip_path}")

    # 1. Clean modified files if requested
    if args.clean_modified:
        print("Cleaning existing modified USD files...")
        import glob
        modified_files = glob.glob(str(assets_dir / "modified_*.usd"))
        for modified_file in modified_files:
            try:
                os.remove(modified_file)
                print(f"  Removed: {os.path.basename(modified_file)}")
            except Exception as e:
                print(f"  Warning: Could not remove {modified_file}: {e}")

    # 2. Discover Assets
    locator = FilesystemLocator()
    usds = locator.find_usds(str(assets_dir))
    print(f"Found {len(usds)} USD file(s): {[os.path.basename(f) for f in usds]}")

    # Filter out modified files for processing feedback
    original_usds = [usd for usd in usds if not os.path.basename(usd).startswith("modified_")]
    modified_usds = [usd for usd in usds if os.path.basename(usd).startswith("modified_")]
    
    if modified_usds:
        print(f"Skipping {len(modified_usds)} existing modified USD files")
    
    print(f"Will process {len(original_usds)} original USD files")

    # 3. Load the Houdini HIP File
    hip_mgr = HoudiniHipManager()
    print(f"Loading HIP file: {hip_path}")
    hip_mgr.load(str(hip_path))

    # Derive material prefixes from the discovered USD file names, excluding modified files
    if not original_usds:
        print(f"Warning: No original USD files found in {assets_dir}. Cannot create materials.")
        prefixes = []
    else:
        # Use the hip_manager method to get clean prefixes from original USD files only
        prefixes = hip_mgr.get_material_prefixes_from_usds(original_usds)
    print(f"Found {len(prefixes)} unique material prefixes: {prefixes}")

    # This code block requires a running Houdini session (e.g., via hython)
    try:
        import hou
        
        # 4. Set Houdini Up-Axis
        axis = settings.up_axis.lower()
        if axis in ("y", "z"):
            print(f"Setting Houdini up-axis to '{axis.upper()}'.")
            hou.hscript(f"upaxis -n {axis}")
        else:
            print(f"Warning: Invalid up_axis '{settings.up_axis}' in config. Skipping.")

        # 5. Import Geometry (and optionally install an HDA)
        print("Importing assets into SOPs context at '/obj/assets'...")
        sop_geo_path = "/obj/assets"
        
        hda_to_install = None
        if settings.hda_path:
            hda_file = Path(settings.hda_path).resolve()
            if hda_file.exists():
                print(f"Will install HDA from: {hda_file}")
                hda_to_install = str(hda_file)
            else:
                print(f"Warning: HDA file not found at '{hda_file}'.")

        # Show USD processing details
        for usd_path in original_usds:
            filename = os.path.basename(usd_path)
            modified_path = os.path.join(os.path.dirname(usd_path), f"modified_{filename}")
            if os.path.exists(modified_path):
                print(f"  - Will reuse existing modified file for: {filename}")
            else:
                print(f"  - Will create modified file for: {filename}")

        # The hip_manager should create or clear the geo node and import the assets.
        hip_mgr.import_usds(original_usds, obj_name="assets", hda_path=hda_to_install)
        print(f"Assets imported to '{sop_geo_path}'.")

        # 6. Build and Assign Materials in Solaris
        if prefixes:
            setup_solaris_materials_from_sops(
                sop_geo_path=sop_geo_path,
                prefixes=prefixes,
                assets_dir=str(assets_dir)
            )
        else:
            print("No asset prefixes found, skipping material creation.")

    except (ImportError, TypeError, Exception) as e:
        if isinstance(e, ImportError):
             print("\nError: The 'hou' module is not available.")
             print("This script must be run with 'hython' from a Houdini installation.")
        else:
             print(f"\nAn error occurred during Houdini processing: {e}")
             import traceback
             traceback.print_exc()
        return

    # 7. Save the HIP File
    actual_hip_path = None
    if not args.dry_run:
        print(f"\nPreparing to save HIP file...")
        
        if hip_path.exists():
            print(f"Warning: HIP file already exists at {hip_path}")
            print("A new unique filename will be created automatically.")
        
        try:
            hip_mgr.save(str(hip_path))
            actual_hip_path = hou.hipFile.path()
            
            if actual_hip_path != str(hip_path):
                print(f"HIP file saved to unique path: {actual_hip_path}")
            else:
                print(f"HIP file saved successfully to: {hip_path}")
                
        except Exception as e:
            print(f"Error saving HIP file: {e}")
            return
    else:
        print("\n[Dry Run] Skipping HIP file save and job submission.")
        actual_hip_path = str(hip_path)

    # 8. Launch Houdini GUI if requested
    if args.launch_local or args.launch_deadline:
        hfs = os.getenv("HFS")
        if not hfs:
            print("\nError: 'HFS' environment variable not set. Cannot launch Houdini GUI.")
            return
            
        houdini_exe = Path(hfs) / "bin" / "houdini.exe" if os.name == 'nt' else Path(hfs) / "bin" / "houdini"
        
        if not args.dry_run:
            # Determine scheduler type
            scheduler_type = "deadline" if args.launch_deadline else "localscheduler"
            
            # Create submit_config.py startup script using the separate module
            startup_script_path = get_default_submit_config_path()
            
            create_submit_config_script(
                hip_file_path=actual_hip_path,
                scheduler_type=scheduler_type, 
                output_path=startup_script_path
            )
            
            print(f"\nCreated Houdini startup script: {startup_script_path}")
            print(f"HIP file to load: {actual_hip_path}")
            print(f"Scheduler type: {scheduler_type}")
            
            # Launch Houdini with the startup script
            launch_cmd = [str(houdini_exe), "-foreground", startup_script_path]
            
            print(f"\nLaunching Houdini with auto-execution:")
            print(f"Command: {' '.join(launch_cmd)}")
            print("\nThis will:")
            print("1. Launch Houdini GUI")
            print("2. Load your HIP file automatically after 8 seconds") 
            print("3. Set up TOPs scheduler and parameters")
            print("4. Execute TOPs workflow automatically")
            print("5. You may need to click 'Save and Continue' once if prompted")
            
            try:
                print("\nStarting Houdini with auto-execution...")
                process = subprocess.run(launch_cmd, shell=False)
                print("Houdini GUI with auto-execution completed")
            except FileNotFoundError:
                print(f"Error: Could not find Houdini executable at {houdini_exe}")
        else:
            print(f"\n[Dry Run] Would launch Houdini with {'Deadline' if args.launch_deadline else 'local'} scheduler")
    
    # 9. Provide usage summary if no launch options were used
    elif not args.dry_run:
        print(f"\nHIP file saved successfully. To execute TOPs workflow:")
        print(f"  Option 1 (Local scheduler): hython -m pipeline.cli --launch-local")
        print(f"  Option 2 (Deadline scheduler): hython -m pipeline.cli --launch-deadline") 
        print(f"  Option 3 (Manual): Open {actual_hip_path} and execute TOPs manually")


if __name__ == "__main__":
    main()