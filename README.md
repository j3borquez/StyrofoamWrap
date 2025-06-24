StyrofoamWrap
Show Image

A procedural pipeline to import USD assets into Houdini, wrap them in styrofoam bases using TOPs workflows, and submit simulation/render jobs to Deadline.

Prerequisites
Houdini 19.5.805 installed on Windows.
A clone of this repository: E:\Project_Work\Amazon\StyrofoamWrap.
Python 3.8+ installed for running env_setup.py.
Quick Setup
1. Set Environment Variables
powershell
# Set HFS environment variable (add this to your PowerShell profile for persistence)
$Env:HFS = "C:\Program Files\Side Effects Software\Houdini19.5.805"

# Navigate to project directory
cd "E:\Project_Work\Amazon\StyrofoamWrap"
2. Bootstrap Environment (One-time setup)
powershell
# Install project dependencies
python env_setup.py `
  --houdini-path "C:\Program Files\Side Effects Software\Houdini19.5.805" `
  --project-path "E:\Project_Work\Amazon\StyrofoamWrap"

# Install additional packages
hython -m pip install pydantic pydantic-settings
3. Verify Installation
powershell
# Test the pipeline
hython -m pytest -q
Quick Start Commands
Simple Usage (Recommended)
powershell
# Local processing (development/small sets)
hython -m pipeline.cli --launch-local

# Deadline processing (production/large sets)  
hython -m pipeline.cli --launch-deadline

# Fresh run (cleans existing files first)
hython -m pipeline.cli --launch-local --clean-modified
Full Command Examples
If you prefer explicit paths or need to troubleshoot:

powershell
# Explicit local processing
& "$Env:HFS\bin\hython.exe" -m pipeline.cli --launch-local

# Explicit Deadline processing
& "$Env:HFS\bin\hython.exe" -m pipeline.cli --launch-deadline

# Clean run with explicit path
& "$Env:HFS\bin\hython.exe" -m pipeline.cli --launch-local --clean-modified
Command Options
Short Command	Full Command	Description
hython -m pipeline.cli --launch-local	& "$Env:HFS\bin\hython.exe" -m pipeline.cli --launch-local	Local TOPs scheduler
hython -m pipeline.cli --launch-deadline	& "$Env:HFS\bin\hython.exe" -m pipeline.cli --launch-deadline	Deadline TOPs scheduler
hython -m pipeline.cli --clean-modified	& "$Env:HFS\bin\hython.exe" -m pipeline.cli --clean-modified	Remove existing modified files
hython -m pipeline.cli --dry-run	& "$Env:HFS\bin\hython.exe" -m pipeline.cli --dry-run	Test without execution
How to Use
Setting Up Your Project
Prepare Your Assets Directory Create an assets folder in your project directory with USD files and textures:
E:\Project_Work\Amazon\StyrofoamWrap\
├── assets\
│   ├── chair_base.usd
│   ├── desk_A3DCZYC5E6B3MT80.usd
│   ├── lamp_B000BRBYJ8.usd
│   ├── chair_base_texture_diff.png
│   ├── chair_base_texture_MR.png
│   ├── chair_base_texture_normal.png
│   └── ... (more assets and textures)
Prepare Your HDA File Place your styrofoam wrapper HDA in the project directory:
E:\Project_Work\Amazon\StyrofoamWrap\
├── assets\
│   └── styrofoam_wrapper.hda
Configure Settings Edit pipeline/config.py to match your project paths:
python
# Example configuration
assets_dir = "E:/Project_Work/Amazon/StyrofoamWrap/assets"
hip_path = "E:/Project_Work/Amazon/StyrofoamWrap/styrofoam_project.hiplc"
hda_path = "E:/Project_Work/Amazon/StyrofoamWrap/assets/styrofoam_wrapper.hda"
Running the Pipeline
The pipeline has two main execution modes:

Option 1: Local Scheduler (Development)
Process assets and execute TOPs workflow using Houdini's local scheduler:

powershell
# Quick command (requires HFS environment variable)
hython -m pipeline.cli --launch-local

# Clean run (recommended for fresh processing)
hython -m pipeline.cli --launch-local --clean-modified
Option 2: Deadline Scheduler (Production)
Process assets and execute TOPs workflow using Deadline distributed scheduler:

powershell
# Quick command (requires HFS environment variable)
hython -m pipeline.cli --launch-deadline

# Clean run (recommended for fresh processing)
hython -m pipeline.cli --launch-deadline --clean-modified
What Each Mode Does
Both modes follow the same workflow:

Asset Processing
Discover USD files in your assets directory
Load/create a Houdini project file
Import USD assets into SOPs with primitive wrangle processing
Install and connect the styrofoam HDA
Create Solaris materials and lighting setup
File Management
Save the project file (with unique name if needed)
Create a submit_config.py startup script with the correct HIP file path
Houdini Launch
Launch Houdini GUI with houdini -foreground submit_config.py
Automatically load your HIP file after 8 seconds
Configure TOPs scheduler (local or deadlinescheduler1)
Execute TOPs workflow automatically
TOPs Execution
Dirty and cook the TOPs network
Generate styrofoam-wrapped assets
Monitor progress in the TOPs network view
Important: Manual Confirmation Required
You will need to manually confirm one dialog during TOPs execution:

When the TOPs workflow starts cooking, Houdini will display a "Save and Continue" dialog asking about file dependencies. Simply click "Save and Continue" to proceed with the workflow.

This is expected behavior and ensures that all file dependencies are properly resolved before TOPs execution.

Additional Options
Test Run (Dry Run)
Test the pipeline without saving files or launching Houdini:

powershell
# Quick test
hython -m pipeline.cli --launch-local --dry-run

# Full command test
& "$Env:HFS\bin\hython.exe" -m pipeline.cli --launch-local --dry-run
Combining Options
You can combine multiple flags:

powershell
# Clean run with test mode
hython -m pipeline.cli --launch-local --clean-modified --dry-run

# Deadline with clean
hython -m pipeline.cli --launch-deadline --clean-modified
Command Line Options Summary
Option	Description
--launch-local	Launch with local TOPs scheduler
--launch-deadline	Launch with Deadline TOPs scheduler (deadlinescheduler1)
--clean-modified	Remove existing modified USD files before processing
--dry-run	Test run without saving files or launching Houdini
Execution Quick Reference
Use Case	Command
Development/Testing	hython -m pipeline.cli --launch-local
Production Rendering	hython -m pipeline.cli --launch-deadline
Fresh Start	hython -m pipeline.cli --launch-local --clean-modified
Testing Only	hython -m pipeline.cli --launch-local --dry-run
Environment Setup Tips
For convenience, add the HFS environment variable to your PowerShell profile:

powershell
# Edit your PowerShell profile
notepad $PROFILE

# Add this line to the profile:
$Env:HFS = "C:\Program Files\Side Effects Software\Houdini19.5.805"
This allows you to use the short hython commands from any directory without setting the environment variable each time.

Troubleshooting Quick Commands
powershell
# Verify hython is accessible
hython --version

# Verify environment
echo $Env:HFS

# Verify project installation
hython -c "import pipeline.cli; print('Pipeline module loaded successfully')"

# Run tests
hython -m pytest -v

# Check for missing dependencies
hython -m pip list | grep -E "(pydantic|pytest)"
What the Pipeline Creates
SOP Network (/obj/assets)
Imports and processes USD geometry
Adds primitive wrangle with i@prim_amount = @primnum + 1;
Applies transformations (Z-up to Y-up conversion)
Connects to styrofoam wrapper HDA
Creates output nulls: OUT_STYROFOAM, OUT_PLASTIC, OUT_MODEL
TOPs Workflow (inside HDA)
Procedural styrofoam base generation
Asset wrapping and positioning
Simulation setup
Output management
LOP Network (/obj/styrofoam_material_pipeline)
Imports SOP geometry into Solaris
Creates MaterialX shaders for each asset
Assigns materials based on USD primitive names
Adds dome lighting
Sets up render camera
Configures Karma render settings
Material Assignment
Automatically matches textures to assets based on filename patterns
Creates PBR materials with diffuse, metallic/roughness, and normal maps
Uses MaterialX standard surface shaders
TOPs Workflow Details
The styrofoam wrapper HDA contains a TOPs network that:

Processes Each Asset: Uses the prim_amount attribute to wedge over individual assets
Generates Styrofoam Bases: Creates custom styrofoam geometry for each asset
Wraps Assets: Positions and fits assets into styrofoam packaging
Outputs Results: Three separate outputs for different material types:
OUT_STYROFOAM: Styrofoam base geometry
OUT_PLASTIC: Plastic wrapping elements
OUT_MODEL: Original asset geometry
Scheduler Configuration
Local Scheduler: Uses Houdini's built-in local scheduler for TOPs execution
Deadline Scheduler: Sets the HDA's topscheduler parameter to deadlinescheduler1 for distributed processing
Texture Naming Convention
The pipeline expects textures to follow this naming pattern:

{base_id}_texture_diff.png    # Diffuse/albedo map
{base_id}_texture_MR.png      # Metallic (R) + Roughness (G) map  
{base_id}_texture_normal.png  # Normal map
Examples:

chair_base_texture_diff.png
A3DCZYC5E6B3MT80_texture_MR.png  
B000BRBYJ8_texture_normal.png
Troubleshooting
Common Issues
"hou module not available"
Make sure you're running with hython, not regular Python
Verify HFS environment variable is set correctly
"No module named 'pipeline.cli'"
Ensure you're in the correct directory (E:\Project_Work\Amazon\StyrofoamWrap)
Use hython -m pipeline.cli not hython pipeline/cli.py
"'hython' is not recognized"
Set the HFS environment variable: $Env:HFS = "C:\Program Files\Side Effects Software\Houdini19.5.805"
Use the full path: & "$Env:HFS\bin\hython.exe"
"No USD files found"
Check your assets directory path in pipeline/config.py
Ensure USD files are in the correct location
"HDA node not found"
Verify the HDA file path in pipeline/config.py
Ensure the HDA file exists and is valid
Check that the HDA contains the expected TOPs parameters
"Save and Continue dialog appears"
This is expected behavior - simply click "Save and Continue"
The pipeline handles file dependency resolution this way
"TOPs workflow not executing"
Check Houdini console for TOPs-related errors
Verify the HDA has dirtybutton and cookbutton parameters
Ensure the topscheduler parameter exists
Advanced Features
Batch Processing
For processing multiple asset sets:

powershell
# Process different asset sets
$assetSets = @("furniture_set_1", "furniture_set_2", "props_set_1")
foreach ($set in $assetSets) {
    # Update config for each set
    # Run automated pipeline
    hython -m pipeline.cli --launch-local --clean-modified
}
Custom HDA Development
Your styrofoam wrapper HDA should:

Accept geometry input on the first input
Have TOPs parameters at the top level: topscheduler, dirtybutton, cookbutton
Provide three outputs: styrofoam, plastic, and model geometry
Use the prim_amount attribute for wedging over individual assets
Support both localscheduler and deadlinescheduler1 scheduler types
Performance Tips
Local Processing: Use --launch-local for small asset sets (< 10 assets)
Deadline Processing: Use --launch-deadline for large asset sets (> 10 assets)
Memory Management: Monitor Houdini memory usage during TOPs execution
Disk Space: Ensure adequate space for intermediate TOPs files
Project Structure
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
├── assets/                             # Your USD files, textures, and HDAs
├── env_setup.py                        # Environment setup script
├── submit_config.py                    # Auto-generated Houdini startup script
└── README.md                           # This file
Complete Workflow Example
powershell
# 1. One-time setup (only needed once)
$Env:HFS = "C:\Program Files\Side Effects Software\Houdini19.5.805"
cd "E:\Project_Work\Amazon\StyrofoamWrap"
python env_setup.py --houdini-path "C:\Program Files\Side Effects Software\Houdini19.5.805" --project-path "E:\Project_Work\Amazon\StyrofoamWrap"
hython -m pip install pydantic pydantic-settings

# 2. Daily usage (simple commands)
hython -m pipeline.cli --launch-local --clean-modified

# 3. Click "Save and Continue" when prompted in Houdini
# 4. Monitor TOPs progress in the network view
# 5. Review generated assets
Summary
Simple Daily Commands:

Development: hython -m pipeline.cli --launch-local
Production: hython -m pipeline.cli --launch-deadline
Fresh start: hython -m pipeline.cli --launch-local --clean-modified
Testing: hython -m pipeline.cli --launch-local --dry-run
Prerequisites: Set $Env:HFS environment variable and run one-time setup script.

