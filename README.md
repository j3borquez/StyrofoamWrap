# StyrofoamWrap

A procedural pipeline to import USD assets into Houdini, wrap them in styrofoam bases, and submit simulation/render jobs to Deadline.

---

## Prerequisites

- **Houdini 19.5.805** installed on Windows.
- A clone of this repository: `E:\Project_Work\Amazon\StyrofoamWrap`.
- Python 3.8+ installed for running `env_setup.py`.

---

## 1. Bootstrap Houdini’s Python Environment

Run the helper script to register this project and `pytest` into Houdini’s `hython`:

```powershell
python env_setup.py `
  --houdini-path "C:\Program Files\Side Effects Software\Houdini19.5.805" `
  --project-path "E:\Project_Work\Amazon\StyrofoamWrap"
```

This will:
1. Verify that `pip` is available in `hython` (or instruct manual installation).
2. Install this package in editable mode.
3. Install `pytest` into Houdini’s Python.

---

## 2. (If Needed) Manually Install `pip` into `hython`

If the bootstrap script indicates `pip` is missing, do the following:

1. **Download** the `get-pip.py` installer from:
   ```text
   https://bootstrap.pypa.io/get-pip.py
   ```
2. **Run** it with `hython`:
   ```powershell
   $hython = "C:\Program Files\Side Effects Software\Houdini19.5.805\bin\hython.exe"
   & $hython ".\get-pip.py"
   ```
3. **Log in** to your SideFX account if prompted.

---

## 3. Verify `pip` Installation

```powershell
& $hython -m pip --version
```

You should see output similar to `pip 24.x.x from ... (python 3.9)`.

---

## 4. Install Project & Test Dependencies

```powershell
& $hython -m pip install -e "E:\Project_Work\Amazon\StyrofoamWrap"
& $hython -m pip install pytest
```

---

## 5. Run Unit Tests

Execute the test suite against the real `hou` API under `hython`:

```powershell
& $hython -m pytest -q
```

All tests should pass without errors.

---

**
