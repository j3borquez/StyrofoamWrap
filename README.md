# StyrofoamWrap

A procedural pipeline to import USD assets into Houdini, wrap them in styrofoam bases, and submit simulation/render jobs to Deadline.

## Prerequisites

- **Houdini 19.5.805** installed on Windows.
- A clone of this repository: `E:\Project_Work\Amazon\StyrofoamWrap`.
- Python 3.8+ installed for running `env_setup.py`.

## 1. Bootstrap Houdini's Python Environment

Run the helper script to register this project and `pytest` into Houdini's `hython`:

```powershell
python env_setup.py `
  --houdini-path "C:\Program Files\Side Effects Software\Houdini19.5.805" `
  --project-path "E:\Project_Work\Amazon\StyrofoamWrap"
```

This will:
1. Verify that `pip` is available in `hython` (or instruct manual installation).
2. Install this package in editable mode.
3. Install `pytest` into Houdini's Python.

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

## 3. Verify `pip` Installation

```powershell
& $hython -m pip --version
```

You should see output similar to `pip 24.x.x from ... (python 3.9)`.

## 4. Install Project & Test Dependencies

```powershell
& $hython -m pip install -e "E:\Project_Work\Amazon\StyrofoamWrap"
& $hython -m pip install pytest
```

## 5. Verify Environment Variables

```powershell
$Env:HFS = "C:\Program Files\Side Effects Software\Houdini19.5.805"
 
# Install the settings packages
& "$Env:HFS\bin\hython.exe" -m pip install pydantic pydantic-settings
```

## 6. Run Unit Tests

Execute the test suite against the real `hou` API under `hython`:

```powershell
& $hython -m pytest -q
```

All tests should pass without errors.

## How to Use

### Setting Up Your Project

1. **Prepare Your Assets Directory**
   
   Create an `assets` folder in your project directory with USD files and textures:
   ```
   E:\Project_Work\Amazon\StyrofoamWrap\
   ├── assets\
   │   ├── chair_base.usd
   │   ├── desk_A3DCZYC5E6B3MT80.usd
   │   ├── lamp_B000BRBYJ8.usd
   │   ├── chair_base_texture_diff.png
   │   ├── chair_base_texture_MR.png
   │   ├── chair_base_texture_normal.png
   │   └── ... (more assets and textures)
   ```

2. **Configure Settings**
   
   Edit `pipeline/config.py` to match your project paths:
   ```python
   # Example configuration
   assets_dir = "E:/Project_Work/Amazon/StyrofoamWrap/assets"
   hip_path = "E:/Project_Work/Amazon/StyrofoamWrap/styrofoam_project.hiplc"
   ```

### Running the Pipeline

#### Option 1: Full Pipeline Run

Run the complete pipeline with automatic Houdini launch:

```powershell
$hython = "C:\Program Files\Side Effects Software\Houdini19.5.805\bin\hython.exe"
& $hython pipeline/cli.py --launch
```

This will:
- Discover USD files in your assets directory
- Load/create a Houdini project file
- Import USD assets into SOPs
- Create Solaris materials with texture assignments
- Set up lighting and cameras
- Save the project file
- Launch Houdini GUI with the completed scene

#### Option 2: Clean Run (Recommended for Testing)

Remove existing modified files and run fresh:

```powershell
& $hython pipeline/cli.py --clean-modified --launch
```

#### Option 3: Dry Run (Testing Only)

Test the pipeline without saving files:

```powershell
& $hython pipeline/cli.py --dry-run
```

#### Option 4: Production Run (No GUI)

Run pipeline and submit to render farm without launching GUI:

```powershell
& $hython pipeline/cli.py
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--launch` | Launch Houdini GUI after processing |
| `--dry-run` | Test run without saving files or submitting jobs |
| `--clean-modified` | Remove existing modified USD files before processing |

### What the Pipeline Creates

1. **SOP Network** (`/obj/assets`)
   - Imports and processes USD geometry
   - Applies transformations (Z-up to Y-up conversion)
   - Adds normal computation
   - Optionally applies HDAs

2. **LOP Network** (`/obj/styrofoam_material_pipeline`)
   - Imports SOP geometry into Solaris
   - Creates MaterialX shaders for each asset
   - Assigns materials based on USD primitive names
   - Adds dome lighting
   - Sets up render camera
   - Configures Karma render settings

3. **Material Assignment**
   - Automatically matches textures to assets based on filename patterns
   - Creates PBR materials with diffuse, metallic/roughness, and normal maps
   - Uses MaterialX standard surface shaders

### Texture Naming Convention

The pipeline expects textures to follow this naming pattern:
```
{base_id}_texture_diff.png    # Diffuse/albedo map
{base_id}_texture_MR.png      # Metallic (R) + Roughness (G) map  
{base_id}_texture_normal.png  # Normal map
```

Examples:
```
chair_base_texture_diff.png
A3DCZYC5E6B3MT80_texture_MR.png  
B000BRBYJ8_texture_normal.png
```

### Troubleshooting

#### Common Issues

1. **"hou module not available"**
   - Make sure you're running with `hython`, not regular Python
   - Verify HFS environment variable is set

2. **"No USD files found"**
   - Check your assets directory path in `pipeline/config.py`
   - Ensure USD files are in the correct location

3. **"Material assignment failed"**
   - Verify texture files follow the naming convention
   - Check that USD primitive names match expected patterns

4. **"HIP file already exists"**
   - The pipeline will create a unique filename automatically
   - Use `--clean-modified` to start fresh

#### Debug Mode

For verbose output, you can modify the CLI script or add print statements to see:
- Which USD files are being processed
- Material assignment details
- Node creation progress

### Advanced Usage

#### Custom HDAs

Place your HDA files in the project directory and update the config:
```python
hda_path = "E:/Project_Work/Amazon/StyrofoamWrap/assets/custom_processor.hda"
```

#### Render Farm Integration

The pipeline supports Deadline submission. Configure your Deadline settings in `pipeline/config.py`:
```python
deadline_command = "deadlinecommand.exe"
frame_range = (1, 240)
sim_output_driver = "/out/sim_driver"
render_output_driver = "/out/render_driver"
```

#### Batch Processing

For processing multiple asset sets, you can create scripts that modify the config and run the CLI multiple times:

```powershell
# Process different asset sets
$assets = @("furniture_set_1", "furniture_set_2", "props_set_1")
foreach ($set in $assets) {
    # Update config for each set
    # Run pipeline
    & $hython pipeline/cli.py --clean-modified
}
```

---

## Project Structure

```
StyrofoamWrap/
├── pipeline/
│   ├── cli.py                    # Main command-line interface
│   ├── config.py                 # Project configuration
│   ├── hip_manager.py           # Houdini project management
│   ├── solaris_material_manager.py # Material creation
│   ├── asset_locator.py         # Asset discovery
│   └── job_submitter.py         # Render farm submission
├── tests/                       # Unit tests
├── assets/                      # Your USD files and textures
├── env_setup.py                 # Environment setup script
└── README.md                    # This file
```