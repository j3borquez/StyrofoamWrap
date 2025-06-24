# StyrofoamWrap

![EXR Grid Output](gridview/grid.png)

A procedural pipeline to import USD assets into Houdini, wrap them in styrofoam bases using TOPs workflows, and submit simulation/render jobs to Deadline.

## Prerequisites

- Houdini 19.5.805 installed on Windows
- Python 3.8+ 
- This repository cloned to: `E:\Project_Work\Amazon\StyrofoamWrap`

## Quick Setup

### 1. Set Environment Variables
```powershell
# Set HFS environment variable (add to your PowerShell profile for persistence)
$Env:HFS = "C:\Program Files\Side Effects Software\Houdini19.5.805"

# Navigate to project directory
cd "E:\Project_Work\Amazon\StyrofoamWrap"
```

### 2. Bootstrap Environment (One-time setup)
```powershell
# Install project dependencies
python env_setup.py `
  --houdini-path "C:\Program Files\Side Effects Software\Houdini19.5.805" `
  --project-path "E:\Project_Work\Amazon\StyrofoamWrap"

# Install additional packages
hython -m pip install pydantic pydantic-settings
```

### 3. Verify Installation
```powershell
# Test the pipeline
hython -m pytest -q
```

## Usage

### Quick Commands (Recommended)

```powershell
# Local processing (development/small sets)
hython -m pipeline.cli --launch-local

# Deadline processing (production/large sets)  
hython -m pipeline.cli --launch-deadline

# Fresh run (cleans existing files first)
hython -m pipeline.cli --launch-local --clean-modified
```

### Command Options

| Option | Description |
|--------|-------------|
| `--launch-local` | Launch with local TOPs scheduler |
| `--launch-deadline` | Launch with Deadline TOPs scheduler |
| `--clean-modified` | Remove existing modified USD files before processing |
| `--dry-run` | Test run without saving files or launching Houdini |

### Use Cases

| Use Case | Command |
|----------|---------|
| Development/Testing | `hython -m pipeline.cli --launch-local` |
| Production Rendering | `hython -m pipeline.cli --launch-deadline` |
| Fresh Start | `hython -m pipeline.cli --launch-local --clean-modified` |
| Testing Only | `hython -m pipeline.cli --launch-local --dry-run` |

## Project Setup

### 1. Prepare Assets Directory
Create an `assets` folder with USD files and textures:
```
E:\Project_Work\Amazon\StyrofoamWrap\
├── assets\
│   ├── chair_base.usd
│   ├── desk_A3DCZYC5E6B3MT80.usd
│   ├── lamp_B000BRBYJ8.usd
│   ├── chair_base_texture_diff.png
│   ├── chair_base_texture_MR.png
│   ├── chair_base_texture_normal.png
│   └── styrofoam_wrapper.hda
```

### 2. Configure Settings
Edit the `.env` file to match your project paths:
```bash
# Example .env configuration
STYROFOAM_ASSETS_DIR=E:/Project_Work/Amazon/StyrofoamWrap/assets
STYROFOAM_HIP_PATH=E:/Project_Work/Amazon/StyrofoamWrap/styrofoam_project.hiplc
STYROFOAM_HDA_PATH=E:/Project_Work/Amazon/StyrofoamWrap/assets/styrofoam_wrapper.hda
STYROFOAM_UP_AXIS=y
STYROFOAM_DEADLINE_COMMAND=C:/Program Files/Thinkbox/Deadline10/bin/deadlinecommand.exe
```

## Pipeline Workflow

The pipeline follows these steps:

1. **Asset Processing**
   - Discovers USD files in assets directory
   - Loads/creates Houdini project file
   - Imports USD assets into SOPs with primitive wrangle processing
   - Installs and connects styrofoam HDA

2. **File Management**
   - Saves project file with unique name if needed
   - Creates `submit_config.py` startup script
   - Launches Houdini GUI with proper configuration

3. **TOPs Execution**
   - Configures scheduler (local or Deadline)
   - Executes TOPs workflow automatically
   - Generates styrofoam-wrapped assets

**Important:** You'll need to manually click "Save and Continue" when prompted during TOPs execution.

## What the Pipeline Creates

### SOP Network (`/obj/assets`)
- Imports and processes USD geometry
- Adds primitive wrangle with `i@prim_amount = @primnum + 1;`
- Applies Z-up to Y-up conversion
- Connects to styrofoam wrapper HDA
- Creates output nulls: `OUT_STYROFOAM`, `OUT_PLASTIC`, `OUT_MODEL`

### LOP Network (`/obj/styrofoam_material_pipeline`)
- Imports SOP geometry into Solaris
- Creates MaterialX shaders for each asset
- Assigns materials based on USD primitive names
- Adds dome lighting and render camera
- Configures Karma render settings

### TOPs Workflow (inside HDA)
- Processes each asset using `prim_amount` attribute
- Generates custom styrofoam geometry
- Wraps and positions assets
- Outputs three separate geometry types

## Texture Naming Convention

Textures should follow this pattern:
```
{base_id}_texture_diff.png    # Diffuse/albedo map
{base_id}_texture_MR.png      # Metallic (R) + Roughness (G) map  
{base_id}_texture_normal.png  # Normal map
```

Examples:
- `chair_base_texture_diff.png`
- `A3DCZYC5E6B3MT80_texture_MR.png`
- `B000BRBYJ8_texture_normal.png`

## Troubleshooting

### Common Issues

**"hou module not available"**
- Use `hython`, not regular Python
- Verify HFS environment variable is set

**"No module named 'pipeline.cli'"**
- Ensure you're in the correct directory
- Use `hython -m pipeline.cli` not `hython pipeline/cli.py`

**"'hython' is not recognized"**
- Set HFS environment variable or use full path:
  ```powershell
  & "$Env:HFS\bin\hython.exe" -m pipeline.cli --launch-local
  ```

**"No USD files found"**
- Check your assets directory path in the `.env` file
- Ensure USD files are in correct location

**"Save and Continue dialog appears"**
- This is expected behavior - click "Save and Continue"
- The pipeline handles file dependency resolution this way

### Diagnostic Commands

```powershell
# Verify hython is accessible
hython --version

# Verify environment
echo $Env:HFS

# Verify project installation
hython -c "import pipeline.cli; print('Pipeline module loaded successfully')"

# Run tests
hython -m pytest -v
```

## Environment Setup Tips

Add HFS to your PowerShell profile for convenience:
```powershell
# Edit your PowerShell profile
notepad $PROFILE

# Add this line:
$Env:HFS = "C:\Program Files\Side Effects Software\Houdini19.5.805"
```

## Project Structure

```
StyrofoamWrap/
├── pipeline/
│   ├── cli.py                           # Main command-line interface
│   ├── config.py                        # Project configuration
│   ├── hip_manager.py                   # Houdini project management
│   ├── solaris_material_manager.py     # Material creation
│   ├── asset_locator.py                # Asset discovery
│   ├── submit_config_generator.py      # Startup script generator
│   └── job_submitter.py                # Render farm submission
├── tests/                              # Unit tests
├── assets/                             # USD files, textures, and HDAs
├── env_setup.py                        # Environment setup script
├── submit_config.py                    # Auto-generated startup script
└── README.md                           # This file
```

## Performance Tips

- **Local Processing:** Use for small asset sets (< 10 assets)
- **Deadline Processing:** Use for large asset sets (> 10 assets)
- **Memory Management:** Monitor Houdini memory usage during TOPs execution
- **Disk Space:** Ensure adequate space for intermediate TOPs files