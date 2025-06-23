# pipeline/cli.py

import os
import argparse
import subprocess
from pathlib import Path

# --- Configuration and Utility Imports ---
# Make sure these modules are available in your Python environment
from pipeline.config import settings
from pipeline.asset_locator import FilesystemLocator

# --- Updated Hip Manager Import with Fixed Code ---
# Import the corrected HoudiniHipManager class
from pipeline.hip_manager import HoudiniHipManager

# --- Updated Material Manager Import ---
# We now import the corrected high-level function for Solaris.
from pipeline.solaris_material_manager import setup_solaris_materials_from_sops

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
        "--launch", action="store_true",
        help="After processing, launch the Houdini GUI with the modified HIP file."
    )
    parser.add_argument(
        "--clean-modified", action="store_true",
        help="Remove existing modified USD files before processing."
    )
    parser.add_argument(
        "--use-deadline", action="store_true",
        help="Use Deadline for TOPs scheduling instead of local scheduler."
    )
    args = parser.parse_args()

    # --- Path Resolution ---
    # Resolve paths at the beginning to ensure they are absolute.
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
        # This step creates the geometry in `/obj/assets` which we will later import into Solaris.
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
        # The setup_solaris_materials_from_sops function now handles LOP network creation.
        if prefixes:
            setup_solaris_materials_from_sops(
                sop_geo_path=sop_geo_path,
                prefixes=prefixes,
                assets_dir=str(assets_dir)
            )
        else:
            print("No asset prefixes found, skipping material creation.")

    except (ImportError, TypeError, Exception) as e:
        # Catch specific and general errors for better reporting.
        if isinstance(e, ImportError):
             print("\nError: The 'hou' module is not available.")
             print("This script must be run with 'hython' from a Houdini installation.")
        else:
             print(f"\nAn error occurred during Houdini processing: {e}")
             import traceback
             traceback.print_exc()
        return # Exit if we can't do the main work

    # 7. Save the HIP File and Submit Jobs
    if not args.dry_run:
        print(f"\nPreparing to save HIP file...")
        
        # Check if the target HIP file already exists and inform user
        if hip_path.exists():
            print(f"Warning: HIP file already exists at {hip_path}")
            print("A new unique filename will be created automatically.")
        
        # Save and capture the actual path used (in case it was modified for uniqueness)
        try:
            # Save the HIP file
            hip_mgr.save(str(hip_path))
            
            # Get the actual saved path from Houdini
            actual_saved_path = hou.hipFile.path()
            
            if actual_saved_path != str(hip_path):
                print(f"HIP file saved to unique path: {actual_saved_path}")
                hip_path = Path(actual_saved_path)  # Update for launch command
            else:
                print(f"HIP file saved successfully to: {hip_path}")
                
        except Exception as e:
            print(f"Error saving HIP file: {e}")
            return

        # 8. Prepare TOPs execution info (but don't execute yet)
        actual_hip_path = hou.hipFile.path()
        hda_node_path = "/obj/assets/wrapped_assets"
        
        # Check if we'll be using Deadline for TOPs
        if args.use_deadline and DeadlineSubmitter:
            print("\nTOPs workflow will be submitted to Deadline after GUI launch")
            
        else:
            print("\nTOPs workflow will be executed locally after GUI launch")
            print("  - TOPs will be triggered once Houdini GUI is fully loaded")
                
    else:
        print("\n[Dry Run] Skipping HIP file save and job submission.")

    # 9. Launch Houdini GUI if Requested
    if args.launch:
        hfs = os.getenv("HFS")
        if not hfs:
            print("\nError: 'HFS' environment variable not set. Cannot launch Houdini GUI.")
        else:
            houdini_exe = (Path(hfs) / "bin" / "houdini").resolve() # Use 'houdini' for cross-platform
            if os.name == 'nt':
                 houdini_exe = (Path(hfs) / "bin" / "houdini.exe").resolve()

            print(f"\nLaunching Houdini: {houdini_exe} {hip_path}")
            try:
                # Launch Houdini GUI
                subprocess.Popen([str(houdini_exe), str(hip_path)], shell=False)
                print("Houdini GUI launched successfully")
                
                # Now handle TOPs execution after GUI launch
                if not args.dry_run:
                    actual_hip_path = hou.hipFile.path() if 'hou' in globals() else str(hip_path)
                    hda_node_path = "/obj/assets/wrapped_assets"
                    
                    if args.use_deadline and DeadlineSubmitter:
                        print("\nSubmitting TOPs workflow to Deadline (after GUI launch)...")
                        
                        # Wait a moment for the GUI to start up
                        import time
                        time.sleep(5)
                        
                        submitter = DeadlineSubmitter(settings.deadline_command)
                        
                        # Submit TOPs job with Deadline scheduler
                        tops_job_id = submitter.submit_tops_with_scheduler(
                            actual_hip_path,
                            hda_node_path,
                            scheduler_type="deadline",
                            name=f"TOPs_Styrofoam_{Path(actual_hip_path).stem}"
                        )
                        print(f"  - TOPs workflow submitted to Deadline (ID: {tops_job_id})")
                        
                    else:
                        print("\nTOPs workflow ready for local execution in GUI")
                        print("To execute TOPs workflow manually:")
                        print(f"  1. Navigate to: {hda_node_path}")
                        print("  2. Press the 'Dirty Button' to dirty the TOPs network")
                        print("  3. Press the 'Cook Button' to execute the TOPs workflow")
                        print("  4. Monitor progress in the TOPs network view")
                        
            except FileNotFoundError:
                print(f"Error: Could not find Houdini executable at {houdini_exe}")
    
    # 10. Handle non-GUI TOPs execution (when --launch is not used)
    elif not args.dry_run and not args.launch:
        print("\nNote: For TOPs workflow execution without GUI:")
        if args.use_deadline and DeadlineSubmitter:
            actual_hip_path = hou.hipFile.path() if 'hou' in globals() else str(hip_path)
            hda_node_path = "/obj/assets/wrapped_assets"
            
            print("Submitting TOPs workflow to Deadline...")
            submitter = DeadlineSubmitter(settings.deadline_command)
            
            # Submit TOPs job with Deadline scheduler
            tops_job_id = submitter.submit_tops_with_scheduler(
                actual_hip_path,
                hda_node_path,
                scheduler_type="deadline",
                name=f"TOPs_Styrofoam_{Path(actual_hip_path).stem}"
            )
            print(f"  - TOPs workflow submitted to Deadline (ID: {tops_job_id})")
        else:
            print("  - Use --launch flag to open GUI and manually trigger TOPs")
            print("  - Or use --use-deadline flag to submit to render farm")
            print("  - TOPs workflows work best with GUI interaction or Deadline submission")

if __name__ == "__main__":
    main()