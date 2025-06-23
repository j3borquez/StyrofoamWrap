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

        # 8. Execute TOPs Workflow
        # Get the actual saved path for job submission
        actual_hip_path = hou.hipFile.path()
        hda_node_path = "/obj/assets/wrapped_assets"
        
        if args.use_deadline and DeadlineSubmitter:
            print("\nSubmitting TOPs workflow to Deadline...")
            submitter = DeadlineSubmitter(settings.deadline_command)
            
            # Submit TOPs job with Deadline scheduler - this will handle loading the file properly
            tops_job_id = submitter.submit_tops_with_scheduler(
                actual_hip_path,
                hda_node_path,
                scheduler_type="deadline",
                name=f"TOPs_Styrofoam_{Path(actual_hip_path).stem}"
            )
            print(f"  - TOPs workflow submitted to Deadline (ID: {tops_job_id})")
            
        else:
            print("\nPreparing to execute TOPs workflow locally...")
            print("  - TOPs workflow will be executed after file is properly loaded")
            
            # For local execution, we need to save the scene, reload it fresh, then execute TOPs
            # This ensures the HDA and all its parameters are properly initialized
            
            # Save again to make sure everything is committed
            hou.hipFile.save()
            
            # Wait a moment for the file system
            import time
            time.sleep(1)
            
            # Reload the file to ensure everything is properly initialized
            print(f"  - Reloading HIP file to ensure proper initialization...")
            hou.hipFile.load(actual_hip_path)
            
            # Wait for the scene to fully load
            time.sleep(2)
            
            # Now try to get the HDA node after reload
            hda_node = hou.node(hda_node_path)
            
            if hda_node is not None:
                print("  - HDA node found after reload, executing TOPs workflow...")
                
                # Set scheduler to local
                scheduler_parm = hda_node.parm("topscheduler")
                if scheduler_parm:
                    scheduler_parm.set("localscheduler")
                    print("    - Set scheduler to localscheduler")
                else:
                    print("    - Warning: topscheduler parameter not found")
                
                # Wait a moment for parameter to update
                time.sleep(0.5)
                
                # Execute TOPs workflow locally
                print("    - Dirtying TOPs network...")
                dirty_parm = hda_node.parm("dirtybutton")
                if dirty_parm:
                    dirty_parm.pressButton()
                    print("    - TOPs network dirtied")
                else:
                    print("    - Warning: dirtybutton parameter not found")
                
                # Wait a moment between dirty and cook
                time.sleep(1)
                
                print("    - Cooking TOPs network...")
                cook_parm = hda_node.parm("cookbutton")
                if cook_parm:
                    cook_parm.pressButton()
                    print("    - TOPs workflow execution initiated")
                    print("    - TOPs workflow is now running in the current session")
                    
                    # Give some time for the TOPs to start processing
                    print("    - Waiting for TOPs to initialize...")
                    time.sleep(3)
                    print("    - Check Houdini's TOPs network for progress")
                else:
                    print("    - Warning: cookbutton parameter not found")
                    
            else:
                print(f"  - Warning: HDA node still not found at {hda_node_path} after reload")
                print("  - Skipping TOPs workflow execution")
                
                # Fallback to original simulation/render submission if available
                if DeadlineSubmitter and hasattr(settings, 'sim_output_driver'):
                    print("  - Falling back to traditional simulation/render job submission...")
                    submitter = DeadlineSubmitter(settings.deadline_command)
                    
                    # Submit simulation job
                    sim_id = submitter.submit_simulation(
                        actual_hip_path,
                        settings.frame_range,
                        settings.sim_output_driver,
                    )
                    print(f"    - Simulation job submitted (ID: {sim_id})")

                    # Submit render job, dependent on the simulation
                    rend_id = submitter.submit_render(
                        actual_hip_path,
                        settings.frame_range,
                        settings.render_output_driver,
                        depends_on=sim_id,
                    )
                    print(f"    - Render job submitted (ID: {rend_id})")
                
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
                subprocess.Popen([str(houdini_exe), str(hip_path)], shell=False)
            except FileNotFoundError:
                print(f"Error: Could not find Houdini executable at {houdini_exe}")

if __name__ == "__main__":
    main()