# env_setup.py
# Automates registration of StyrofoamWrap into Houdini's Python environment for testing

import os
import sys
import subprocess
import argparse


def run_cmd(cmd, desc=None):
    """Run a subprocess command and exit on failure."""
    if desc:
        print(f"\n==> {desc}")
    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with code {e.returncode}")
        sys.exit(e.returncode)


def check_pip(hython_exe):
    """
    Check if pip is available in hython. If not, instruct manual installation.
    """
    print("\n==> Verifying pip availability in hython")
    try:
        subprocess.check_call([hython_exe, '-m', 'pip', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✔ pip is available in hython.")
    except Exception:
        print("⚠ pip not found in hython; please manually install pip into Houdini's Python:\n")
        print("  1. Download get-pip.py from https://bootstrap.pypa.io/get-pip.py")
        print(f"  2. Run: {hython_exe} get-pip.py")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Register StyrofoamWrap and pytest into Houdini's hython for tests"
    )
    parser.add_argument(
        "--houdini-path",
        required=True,
        help="Root path of Houdini installation (HFS), e.g. C:\\Program Files\\Side Effects Software\\Houdini19.5.805"
    )
    parser.add_argument(
        "--project-path",
        default=os.getcwd(),
        help="Path to your StyrofoamWrap project root (defaults to cwd)"
    )
    args = parser.parse_args()

    # Locate hython executable
    hython_exe = os.path.join(args.houdini_path, 'bin', 'hython.exe')
    if not os.path.isfile(hython_exe):
        print(f"Error: hython not found at {hython_exe}")
        sys.exit(1)

    # Verify pip exists (manual fallback)
    check_pip(hython_exe)

    # Install project editable
    run_cmd([
        hython_exe,
        '-m', 'pip', 'install', '-e', args.project_path
    ], desc="Installing StyrofoamWrap package into hython")

    # Install pytest
    run_cmd([
        hython_exe,
        '-m', 'pip', 'install', 'pytest'
    ], desc="Installing pytest into hython environment")

    print("\n✅ Setup complete. Run tests with:")
    print(f"  {hython_exe} -m pytest -q")

if __name__ == '__main__':
    main()
