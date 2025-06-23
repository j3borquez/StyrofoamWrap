# StyrofoamWrap

![Pipeline Overview](gridview/grid.png)

A procedural pipeline to import USD assets into Houdini, wrap them in styrofoam bases using TOPs workflows, and submit simulation/render jobs to Deadline.

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

2. **Prepare Your HDA File**
   
   Place your styrofoam wrapper HDA in the project directory:
   ```
   E:\Project_Work\Amazon\StyrofoamWrap\
   ├── assets\
   │   └── styrofoam_wrapper.hda
   ```

3. **Configure Settings**
   
   Edit `pipeline/config.py` to match your project paths:
   ```python
   # Example configuration
   assets_dir = "E:/Project_Work/Amazon/StyrofoamWrap/assets"
   hip_path = "E:/Project_Work/Amazon/StyrofoamWrap/styrofoam_project.hiplc"
   hda_path = "E:/Project_Work/Amazon/StyrofoamWrap/assets/styrofoam_wrapper.hda"
   ```

### Running the Pipeline

#### Option 1: Fully Automated Pipeline (Recommended)

Run the complete pipeline with automatic TOPs execution (no GUI required):

```powershell
$hython = "C:\Program Files\Side Effects Software\Houdini19.5.805\bin\hython.exe"
& $hython pipeline/cli.py --auto-tops
```

This will:
- Discover USD files in your assets directory
- Load/create a Houdini project file
- Import USD assets into SOPs with primitive wrangle processing
- Install and connect the styrofoam HDA
- Execute the TOPs workflow automatically (local scheduler)
- Generate styrofoam-wrapped assets
- Save the project file

#### Option 2: Interactive Pipeline with GUI

Run the pipeline and launch Houdini GUI for manual TOPs execution:

```powershell
& $hython pipeline/cli.py --launch
```

This will:
- Set up the complete scene
- Launch Houdini GUI with the prepared scene
- Provide instructions for manual TOPs execution

**Manual TOPs Execution in GUI:**
1. Navigate to `/obj/assets/wrapped_assets`
2. Press the **"Dirty Button"** to dirty the TOPs network
3. Press the **"Cook Button"** to execute the TOPs workflow
4. Monitor progress in the TOPs network view

#### Option 3: Production Pipeline with Deadline

Run the pipeline and submit TOPs to Deadline for distributed processing:

```powershell
& $hython pipeline/cli.py --use-deadline
```

#### Option 4: Clean Run (Recommended for Testing)

Remove existing modified files and run fresh:

```powershell
& $hython pipeline/cli.py --clean-modified --auto-tops
```

#### Option 5: Dry Run (Testing Only)

Test the pipeline without saving files or executing TOPs:

```powershell
& $hython pipeline/cli.py --dry-run
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--auto-tops` | **NEW**: Automatically execute TOPs workflow locally (headless) |
| `--launch` | Launch Houdini GUI after processing for manual TOPs execution |
| `--use-deadline` | Submit TOPs workflow to Deadline for distributed processing |
| `--dry-run` | Test run without saving files or executing TOPs |
| `--clean-modified` | Remove existing modified USD files before processing |

### Execution Modes Summary

| Mode | Command | When to Use |
|------|---------|-------------|
| **Automated** | `--auto-tops` | Production, batch processing, testing |
| **Interactive** | `--launch` | Development, debugging, manual control |
| **Distributed** | `--use-deadline` | Large-scale production, render farm |
| **Testing** | `--dry-run` | Validation, troubleshooting |

### What the Pipeline Creates

1. **SOP Network** (`/obj/assets`)
   - Imports and processes USD geometry
   - Adds primitive wrangle with `i@prim_amount = @primnum + 1;`
   - Applies transformations (Z-up to Y-up conversion)
   - Connects to styrofoam wrapper HDA
   - Creates output nulls: `OUT_STYROFOAM`, `OUT_PLASTIC`, `OUT_MODEL`

2. **TOPs Workflow** (inside HDA)
   - Procedural styrofoam base generation
   - Asset wrapping and positioning
   - Simulation setup
   - Output management

3. **LOP Network** (`/obj/styrofoam_material_pipeline`)
   - Imports SOP geometry into Solaris
   - Creates MaterialX shaders for each asset
   - Assigns materials based on USD primitive names
   - Adds dome lighting
   - Sets up render camera
   - Configures Karma render settings

4. **Material Assignment**
   - Automatically matches textures to assets based on filename patterns
   - Creates PBR materials with diffuse, metallic/roughness, and normal maps
   - Uses MaterialX standard surface shaders

### TOPs Workflow Details

The styrofoam wrapper HDA contains a TOPs network that:

1. **Processes Each Asset**: Uses the `prim_amount` attribute to wedge over individual assets
2. **Generates Styrofoam Bases**: Creates custom styrofoam geometry for each asset
3. **Wraps Assets**: Positions and fits assets into styrofoam packaging
4. **Outputs Results**: Three separate outputs for different material types:
   - **OUT_STYROFOAM**: Styrofoam base geometry
   - **OUT_PLASTIC**: Plastic wrapping elements  
   - **OUT_MODEL**: Original asset geometry

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

3. **"HDA node not found"**
   - Verify the HDA file path in `pipeline/config.py`
   - Ensure the HDA file exists and is valid
   - Check that the HDA contains the expected TOPs parameters

4. **"TOPs workflow not executing"**
   - Try `--launch` mode to manually inspect the TOPs network
   - Check Houdini console for TOPs-related errors
   - Verify the HDA has `dirtybutton` and `cookbutton` parameters

5. **"Material assignment failed"**
   - Verify texture files follow the naming convention
   - Check that USD primitive names match expected patterns

6. **"HIP file already exists"**
   - The pipeline will create a unique filename automatically
   - Use `--clean-modified` to start fresh

#### Debug Mode

For verbose output, you can modify the CLI script or add print statements to see:
- Which USD files are being processed
- TOPs execution progress
- Material assignment details
- Node creation progress

### Advanced Usage

#### Custom HDA Development

Your styrofoam wrapper HDA should:
- Accept geometry input on the first input
- Have TOPs parameters at the top level: `topscheduler`, `dirtybutton`, `cookbutton`
- Provide three outputs: styrofoam, plastic, and model geometry
- Use the `prim_amount` attribute for wedging over individual assets

#### Deadline Integration

Configure Deadline settings in `pipeline/config.py`:
```python
deadline_command = "deadlinecommand.exe"
```

The Deadline TOPs scheduler will:
- Submit each TOPs work item as a separate Deadline job
- Handle dependencies between work items automatically
- Provide distributed processing across your render farm

#### Batch Processing

For processing multiple asset sets:

```powershell
# Process different asset sets
$assetSets = @("furniture_set_1", "furniture_set_2", "props_set_1")
foreach ($set in $assetSets) {
    # Update config for each set
    # Run automated pipeline
    & $hython pipeline/cli.py --clean-modified --auto-tops
}
```

#### Performance Optimization

- **Local Processing**: Use `--auto-tops` for small asset sets (< 10 assets)
- **Deadline Processing**: Use `--use-deadline` for large asset sets (> 10 assets)
- **Memory Management**: Monitor Houdini memory usage during TOPs execution
- **Disk Space**: Ensure adequate space for intermediate TOPs files

---

## Pipeline Workflow Summary

1. **Asset Discovery**: Scan for USD files and textures
2. **Scene Setup**: Create Houdini project with SOP network
3. **USD Processing**: Import and rename USD primitives
4. **Primitive Attribution**: Add `prim_amount` attribute for TOPs wedging
5. **HDA Integration**: Install and connect styrofoam wrapper HDA
6. **TOPs Execution**: Run procedural styrofoam wrapping workflow
7. **Material Assignment**: Create and assign PBR materials in Solaris
8. **Output Generation**: Produce final wrapped assets

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
├── assets/                      # Your USD files, textures, and HDAs
├── env_setup.py                 # Environment setup script
└── README.md                    # This file
```