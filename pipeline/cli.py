# pipeline/cli.py

import os
import argparse
import subprocess
from pathlib import Path

from pipeline.config import settings
from pipeline.asset_locator import FilesystemLocator
from pipeline.hip_manager import HoudiniHipManager
from pipeline.material_manager import create_MTLX_Subnet, assign_materials_to_geo

try:
    from pipeline.job_submitter import DeadlineSubmitter
except ImportError:
    DeadlineSubmitter = None


def main():
    parser = argparse.ArgumentParser(
        description="StyrofoamWrap: import USDs, assign materials, install HDA, and submit jobs"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would happen without saving or submitting jobs"
    )
    parser.add_argument(
        "--launch", action="store_true",
        help="After processing, open the HIP in Houdini GUI"
    )
    args = parser.parse_args()

    # Resolve paths so we always use absolute references
    assets_dir = Path(settings.assets_dir).resolve()
    hip_path   = Path(settings.hip_path).resolve()

    # 1. Discover USD assets
    locator = FilesystemLocator()
    usds = locator.find_usds(str(assets_dir))
    print(f"Found {len(usds)} USD(s) in {assets_dir!r}:")
    for usd in usds:
        print(f"  - {usd}")

    # 2. Load the HIP
    hip_mgr = HoudiniHipManager()
    print(f"Loading HIP: {hip_path!r}")
    hip_mgr.load(str(hip_path))

    # 3. Set up-axis if running under hython
    try:
        import hou
        axis = settings.up_axis.lower()
        if axis in ("y", "z"):
            print(f"Setting Houdini up-axis to {axis.upper()}…")
            hou.hscript(f"upaxis -n {axis}")
        else:
            print(f"Warning: invalid up_axis '{settings.up_axis}', skipping.")
    except ImportError:
        pass

    # 4. Import USDs (and install HDA if provided)
    print("Importing USDs into /obj/assets…")
    if settings.hda_path:
        hda_file = Path(settings.hda_path)
        hda_file = hda_file if hda_file.is_absolute() else Path.cwd() / hda_file
        hda_file = hda_file.resolve()
        print(f"Installing digital asset from {hda_file!r}…")
        hip_mgr.import_usds(usds, obj_name="assets", hda_path=str(hda_file))
    else:
        hip_mgr.import_usds(usds, obj_name="assets")

    # 5. Build and assign MaterialX materials under /obj
    try:
        import hou
        # create or reuse a matnet for MTLX materials
        matnet = hou.node("/obj/materialX_net")
        if not matnet:
            matnet = hou.node("/obj").createNode("matnet", "materialX_net")
        matnet.moveToGoodPosition()

        # extract unique prefixes (strip off "_texture" suffix)
        prefixes = sorted({
            Path(p).stem.rsplit("_texture", 1)[0]
            for p in usds
        })

        # create a subnet per prefix
        for prefix in prefixes:
            create_MTLX_Subnet(matnet, prefix, str(assets_dir))

        # assign them back to the geo
        assign_materials_to_geo(prefixes, matnet.path())
    except ImportError:
        print("Warning: hou module not available, skipping material assignment")

    # 6. Save & submit jobs (unless dry-run)
    if not args.dry_run:
        print(f"Saving HIP: {hip_path!r}")
        hip_mgr.save(str(hip_path))

        if DeadlineSubmitter:
            submitter = DeadlineSubmitter(settings.deadline_command)
            sim_id = submitter.submit_simulation(
                str(hip_path),
                settings.frame_range,
                settings.sim_output_driver,
            )
            print(f"Simulation job submitted (ID={sim_id})")
            rend_id = submitter.submit_render(
                str(hip_path),
                settings.frame_range,
                settings.render_output_driver,
                depends_on=sim_id,
            )
            print(f"Render job submitted (ID={rend_id})")
        else:
            print("No DeadlineSubmitter configured; skipping job submission.")

    # 7. Launch Houdini GUI if requested
    if args.launch:
        hfs = os.getenv("HFS")
        if not hfs:
            print("Error: HFS environment variable not set; cannot launch GUI.")
        else:
            houdini_exe = (Path(hfs) / "bin" / "houdini.exe").resolve()
            hip_file     = hip_path
            print(f"Launching Houdini: {houdini_exe} {hip_file}")
            subprocess.Popen([str(houdini_exe), str(hip_file)], shell=False)


if __name__ == "__main__":
    main()
