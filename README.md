Instructions:

1) Clone the repo
   git clone git@github.com:j3borquez/StyrofoamWrap.git
   cd StyrofoamWrap

2) Create & activate your Python venv
   python -m venv .venv
   .venv\Scripts\Activate.ps1    # PowerShell
   # (or .venv\Scripts\activate.bat in CMD)

3) Install project & Python deps
   pip install --upgrade pip setuptools wheel tomli
   pip install -e .               # registers pipeline/ and pydantic-settings
   pip install pytest pydantic pydantic-settings

4) Prepare Houdini’s Python (hython)
   $Env:HFS = "C:\Program Files\Side Effects Software\Houdini19.5.805"
   # Ensure hython and pip are available:
   & "$Env:HFS\bin\hython.exe" -m pip --version
   & "$Env:HFS\bin\hython.exe" -m pip install -e . pytest pydantic pydantic-settings

5) Configure your assets and HIP
   Create a .env at the project root with:
   STYROFOAM_ASSETS_DIR=E:\Project_Work\Amazon\StyrofoamWrap\Assets
   STYROFOAM_HIP_PATH=E:\Project_Work\Amazon\StyrofoamWrap\styrofoam_w_v01.hiplc

(Optional) Install DeadlineSubmitter
If you’ve implemented pipeline/job_submitter.py, install any extra farm-API deps here.

Run & verify tests

Locally (pure-Python):
pytest -q

Under hython (exercises real hou API):
& "$Env:HFS\bin\hython.exe" -m pytest -q

Launch the pipeline
& "$Env:HFS\bin\hython.exe" -m pipeline.cli --launch
This command will:
* Imports every USD into your HIP
* Saves the HIP
* Submits sim/render (if configured)
* Opens Houdini GUI with the updated file

Dry-run preview
To see what would happen without writing or submitting:
hython -m pipeline.cli --dry-run