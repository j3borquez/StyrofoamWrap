# pipeline/cli.py

import os
import argparse
import subprocess
from pathlib import Path

# --- Configuration and Utility Imports ---
# Make sure these modules are available in your Python environment
from pipeline.config import settings
from pipeline.asset_locator import FilesystemLocator
from pipeline.hip_manager import HoudiniHipManager

# --- Updated Material Manager Import ---
# We now import the new high-level function for Solaris.
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
    args = parser.parse_args()

    # --- Path Resolution ---
    # Resolve paths at the beginning to ensure they are absolute.
    assets_dir = Path(settings.assets_dir).resolve()
    hip_path = Path(settings.hip_path).resolve()
    print(f"Project Assets Directory: {assets_dir}")
    print(f"Houdini Project File: {hip_path}")

    # 1. Discover Assets
    locator = FilesystemLocator()
    usds = locator.find_usds(str(assets_dir))
    print(f"Found {len(usds)} USD file(s): {usds}")

    # 2. Load the Houdini HIP File
    hip_mgr = HoudiniHipManager()
    print(f"Loading HIP file: {hip_path}")
    hip_mgr.load(str(hip_path))

    # Derive material prefixes from the discovered USD file names, excluding modified files
    if not usds:
        print(f"Warning: No USD files found in {assets_dir}. Cannot create materials.")
        prefixes = []
    else:
        # Use the hip_manager method to get clean prefixes from original USD files only
        prefixes = hip_mgr.get_material_prefixes_from_usds(usds)
    print(f"Found {len(prefixes)} unique material prefixes: {prefixes}")

    # This code block requires a running Houdini session (e.g., via hython)
    try:
        import hou
        
        # 3. Set Houdini Up-Axis
        axis = settings.up_axis.lower()
        if axis in ("y", "z"):
            print(f"Setting Houdini up-axis to '{axis.upper()}'.")
            hou.hscript(f"upaxis -n {axis}")
        else:
            print(f"Warning: Invalid up_axis '{settings.up_axis}' in config. Skipping.")

        # 4. Import Geometry (and optionally install an HDA)
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

        # The hip_manager should create or clear the geo node and import the assets.
        hip_mgr.import_usds(usds, obj_name="assets", hda_path=hda_to_install)
        print(f"Assets imported to '{sop_geo_path}'.")

        # 5. Build and Assign Materials in Solaris
        # The check for the /stage node has been removed from this script.
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
        return # Exit if we can't do the main work

    # 6. Save the HIP File and Submit Jobs
    if not args.dry_run:
        print(f"\nSaving HIP file to: {hip_path}")
        hip_mgr.save(str(hip_path))

        if DeadlineSubmitter:
            print("Submitting jobs to Deadline...")
            submitter = DeadlineSubmitter(settings.deadline_command)
            
            # Submit simulation job
            sim_id = submitter.submit_simulation(
                str(hip_path),
                settings.frame_range,
                settings.sim_output_driver,
            )
            print(f"  - Simulation job submitted (ID: {sim_id})")

            # Submit render job, dependent on the simulation
            rend_id = submitter.submit_render(
                str(hip_path),
                settings.frame_range,
                settings.render_output_driver,
                depends_on=sim_id,
            )
            print(f"  - Render job submitted (ID: {rend_id})")
        else:
            print("Job submission skipped (DeadlineSubmitter not configured).")
    else:
        print("\n[Dry Run] Skipping HIP file save and job submission.")

    # 7. Launch Houdini GUI if Requested
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