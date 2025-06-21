1)Clone the repo
-------------------------
bash
Copy code
git clone git@github.com:j3borquez/StyrofoamWrap.git
cd StyrofoamWrap

2) Create & activate your Python venv
------------------------------------
powershell
Copy code
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # PowerShell
# (or .venv\Scripts\activate.bat in CMD)
3) Install project & Python deps
------------------------------------

powershell
Copy code
pip install --upgrade pip setuptools wheel tomli
pip install -e .               # registers pipeline/ and pydantic-settings
pip install pytest pydantic pydantic-settings

4) Prepare Houdini’s Python (hython)
------------------------------------

powershell
Copy code
$Env:HFS = "C:\Program Files\Side Effects Software\Houdini19.5.805"
# Ensure hython and pip are available:
& "$Env:HFS\bin\hython.exe" -m pip --version
& "$Env:HFS\bin\hython.exe" -m pip install -e . pytest pydantic pydantic-settings
Configure your assets and HIP
5) Create a .env at the project root with:
------------------------------------

ini
Copy code
STYROFOAM_ASSETS_DIR=E:\Project_Work\Amazon\StyrofoamWrap\Assets
STYROFOAM_HIP_PATH=E:\Project_Work\Amazon\StyrofoamWrap\styrofoam_w_v01.hiplc
(Optional) Install DeadlineSubmitter
If you’ve implemented pipeline/job_submitter.py, install any extra farm-API deps here.

Run & verify tests

Locally (pure-Python):

bash
Copy code
pytest -q
Under hython (exercises real hou API):

powershell
Copy code
& "$Env:HFS\bin\hython.exe" -m pytest -q
Launch the pipeline

powershell
Copy code
& "$Env:HFS\bin\hython.exe" -m pipeline.cli --launch
Imports every USD into your HIP

Saves the HIP

Submits sim/render (if configured)

Opens Houdini GUI with the updated file

Dry-run preview
To see what would happen without writing or submitting:

bash
Copy code
hython -m pipeline.cli --dry-run