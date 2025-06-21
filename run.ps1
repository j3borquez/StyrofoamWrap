<#
.SYNOPSIS
  Activate .venv, bootstrap package & dev deps, then run a command.
#>

param(
  [string] $Command = "pytest -q"
)

# 1) Activate venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
. .\.venv\Scripts\Activate.ps1
Write-Host "(.venv) activated"

# 2) If our package isn't installed, install it + pytest
if (-Not (pip show styrofoamwrap -ErrorAction SilentlyContinue)) {
  Write-Host "Installing project in editable mode + pytest…"
  pip install -e .
  pip install pytest
}

# 3) Run the requested command
Invoke-Expression $Command
