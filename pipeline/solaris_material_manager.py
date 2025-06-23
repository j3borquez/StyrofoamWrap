# pipeline/solaris_material_manager.py

import os
from typing import List
import hou

# --- Helper Functions (Preserved and Enhanced) ---

def safe_set_parm(node: hou.Node, parm_name: str, value):
    """
    Sets a parameter on a node, raising a clear error if the node or parameter is not found.
    This prevents the common "'NoneType' object has no attribute 'set'" error.
    """
    if not node:
        raise ValueError(f"Attempted to set parameter '{parm_name}' on a None node.")
    
    parm = node.parm(parm_name)
    if not parm:
        raise AttributeError(f"Node '{node.path()}' of type '{node.type().name()}' does not have a parameter named '{parm_name}'.")
    
    try:
        parm.set(value)
    except hou.OperationFailed as e:
        print(f"  [ERROR] Failed to set parameter '{parm_name}' on node '{node.path()}' to value '{value}'.")
        raise e

def set_file_parameter(node, filepath):
    """Helper to set a file parameter on a node, trying different common parameter names."""
    param_names = ['filename', 'file', 'map', 'tex0', 'texture', 'map1']
    
    for name in param_names:
        if node.parm(name):
            safe_set_parm(node, name, filepath)
            return True
    
    for parm in node.parms():
        if 'file' in parm.name().lower():
            safe_set_parm(node, parm.name(), filepath)
            return True

    print(f"  [ERROR] Could not find a suitable file parameter on node '{node.name()}'.")
    return False

def connect_vop_nodes(dest_node, dest_input_name, src_node, src_output_idx=0):
    """Connect VOP nodes. Attempts several connection methods for robustness."""
    try:
        for i, input_item in enumerate(dest_node.inputLabels()):
            if input_item.lower() == dest_input_name.lower():
                dest_node.setInput(i, src_node, src_output_idx)
                return True
        
        for i, input_item in enumerate(dest_node.inputNames()):
             if input_item.lower() == dest_input_name.lower():
                dest_node.setInput(i, src_node, src_output_idx)
                return True

        input_map = {
            "base_color": 1, "base": 1, "metallic": 3, "metalness": 3, 
            "specular_roughness": 6, "roughness": 6, "normal": 40,
        }
        if dest_input_name.lower() in input_map:
            dest_node.setInput(input_map[dest_input_name.lower()], src_node, src_output_idx)
            return True
            
    except Exception as e:
        print(f"    [WARNING] Failed to connect '{src_node.name()}' to '{dest_node.name()}.{dest_input_name}': {e}")
    
    print(f"    [ERROR] Could not find input '{dest_input_name}' on node '{dest_node.name()}'")
    return False

def extract_base_identifier(prefix: str) -> str:
    """
    Extract the base identifier from a prefix, removing any additional suffixes.
    Examples: 
    - 'nan_A3DCZYC5E6B3MT80_texture_MR' -> 'A3DCZYC5E6B3MT80'
    - 'B000H7BCJ4_A3DCJVRR51BY4X0U_base' -> 'B000H7BCJ4'  
    - 'chair_base' -> 'chair'
    """
    # Remove '_base' suffix if it exists
    if prefix.endswith('_base'):
        prefix = prefix[:-5]  # Remove '_base'
    
    # Split by underscore
    parts = prefix.split('_')
    
    # Special handling for 'nan_' prefix - return the part after 'nan_'
    if len(parts) >= 2 and parts[0] == 'nan':
        return parts[1]
    
    # For other cases, look for random suffix patterns and return everything before them
    if len(parts) >= 2:
        # Check each part starting from the second one
        for i in range(1, len(parts)):
            part = parts[i]
            # Check if this part looks like a random suffix
            # (long alphanumeric string that's likely a unique identifier)
            if len(part) > 8 and part.isalnum() and (part.isupper() or part.isdigit() or 
                                                     any(c.isdigit() for c in part)):
                # This looks like a random suffix, return everything before it
                return '_'.join(parts[:i])
    
    # If no random suffix pattern found, return the full prefix
    return prefix

def clear_lop_network_children(lop_network):
    """
    Safely clear all children from a LOP network
    """
    try:
        children = lop_network.children()
        if children:
            print(f"    Removing {len(children)} child nodes...")
            for child in children:
                try:
                    print(f"      Removing node: {child.name()}")
                    child.destroy()
                except Exception as e:
                    print(f"      Warning: Could not destroy node {child.name()}: {e}")
            print(f"    Successfully cleared LOP network.")
        else:
            print(f"    LOP network is already empty.")
    except Exception as e:
        print(f"    Error clearing LOP network: {e}")
        raise

# --- Solaris/LOPs Workflow Functions ---

def find_texture_files(assets_dir: str, base_id: str) -> dict:
    """
    Scan the assets directory for PNG files that match the base_id pattern.
    Returns a dict with 'diffuse', 'mr', and 'normal' texture paths.
    """
    import glob
    
    # Get all PNG files in the assets directory
    png_files = glob.glob(os.path.join(assets_dir, "*.png"))
    
    textures = {'diffuse': None, 'mr': None, 'normal': None}
    
    for png_file in png_files:
        filename = os.path.basename(png_file)
        
        # Check if this file belongs to our base_id
        if base_id in filename:
            if '_texture_diff.png' in filename:
                textures['diffuse'] = png_file
            elif '_texture_MR.png' in filename:
                textures['mr'] = png_file
            elif '_texture_normal.png' in filename:
                textures['normal'] = png_file
    
    return textures


def create_solaris_mtlx_shader(material_library: hou.Node, prefix: str, assets_dir: str, material_counter: dict = None) -> hou.Node:
    """
    Inside a Material Library LOP, creates a subnetwork containing a MaterialX shader network.
    """
    # Extract the clean base identifier for naming
    base_id = extract_base_identifier(prefix.strip())
    
    # Handle duplicate base identifiers by adding a counter
    if material_counter is None:
        material_counter = {}
    
    if base_id in material_counter:
        material_counter[base_id] += 1
        unique_base_id = f"{base_id}_{material_counter[base_id]}"
    else:
        material_counter[base_id] = 0
        unique_base_id = base_id
    
    material_name = f"{unique_base_id}_base_material"
    
    # Find texture files by scanning the assets directory
    textures = find_texture_files(assets_dir, base_id)
    
    print(f"\nCreating Solaris material for: {material_name} (base_id: {base_id})")
    print(f"  Scanning assets folder for textures matching '{base_id}':")
    print(f"    Diffuse: {textures['diffuse'] or 'Not found'} {'✓' if textures['diffuse'] else '✗'}")
    print(f"    MR: {textures['mr'] or 'Not found'} {'✓' if textures['mr'] else '✗'}")
    print(f"    Normal: {textures['normal'] or 'Not found'} {'✓' if textures['normal'] else '✗'}")

    # Create a subnet for the material inside the Material Library
    subnet = material_library.createNode("subnet", material_name)

    # --- Create nodes inside the subnet ---
    # Output connector
    out_surf = subnet.createNode("subnetconnector", "Surface_Out")
    safe_set_parm(out_surf, "connectorkind", "output")
    safe_set_parm(out_surf, "parmname", "surface")
    safe_set_parm(out_surf, "parmlabel", "surface")
    safe_set_parm(out_surf, "parmtype", "surface")

    # Standard Surface - This is the actual material that gets exported.
    std_surface = subnet.createNode("mtlxstandard_surface", unique_base_id)
    # The Material Library looks for this flag to identify exportable materials.
    std_surface.setGenericFlag(hou.nodeFlag.Material, True)

    # Connect surface to the subnet's output
    out_surf.setInput(0, std_surface)

    # Create and connect diffuse texture
    if textures['diffuse']:
        img_diff = subnet.createNode("mtlximage", f"diff_{unique_base_id}")
        safe_set_parm(img_diff, "signature", "color3")
        if set_file_parameter(img_diff, textures['diffuse']):
            # Connect diffuse image to base_color input
            try:
                std_surface.setInput(1, img_diff)  # Input 1 is base_color
                print(f"    ✓ Connected diffuse texture")
            except:
                print(f"    ✗ Failed to connect diffuse texture")
        else:
            print(f"    ✗ Failed to set diffuse file parameter")

    # Create and connect metallic/roughness texture
    if textures['mr']:
        img_mr = subnet.createNode("mtlximage", f"mr_{unique_base_id}")
        safe_set_parm(img_mr, "signature", "color3")
        if set_file_parameter(img_mr, textures['mr']):
            # Create separate node to split RGB channels
            sep_mr = subnet.createNode("mtlxseparate3c", f"sep_mr_{unique_base_id}")
            sep_mr.setInput(0, img_mr)
            
            try:
                # Find the correct input indices for metallic and specular roughness
                # Print available inputs for debugging
                input_labels = std_surface.inputLabels()
                print(f"    Available inputs: {[f'{i}:{label}' for i, label in enumerate(input_labels)]}")
                
                # Try to find metallic and specular roughness inputs by name
                metallic_input = None
                roughness_input = None
                
                for i, label in enumerate(input_labels):
                    if 'metallic' in label.lower():
                        metallic_input = i
                    elif 'roughness' in label.lower() and 'specular' in label.lower():
                        roughness_input = i
                
                if metallic_input is not None and roughness_input is not None:
                    std_surface.setInput(roughness_input, sep_mr, 1)  # G channel to specular roughness
                    std_surface.setInput(metallic_input, sep_mr, 2)    # B channel to metallic
                    print(f"    ✓ Connected G→specular_roughness (input {roughness_input}), B→metallic (input {metallic_input})")
                else:
                    # Fallback to common indices if labels don't match
                    std_surface.setInput(6, sep_mr, 1)  # G channel to specular roughness
                    std_surface.setInput(3, sep_mr, 2)  # B channel to metallic
                    print(f"    ✓ Connected metallic/roughness using fallback indices - G→roughness (6), B→metallic (3)")
            except Exception as e:
                print(f"    ✗ Failed to connect metallic/roughness: {e}")
        else:
            print(f"    ✗ Failed to set MR file parameter")

    # Create and connect normal map
    if textures['normal']:
        img_nrm = subnet.createNode("mtlximage", f"nrm_{unique_base_id}")
        safe_set_parm(img_nrm, "signature", "vector3")  # Normal maps are vector3
        if set_file_parameter(img_nrm, textures['normal']):
            # Create normal map node
            nmap_node = subnet.createNode("mtlxnormalmap", f"nmap_{unique_base_id}")
            nmap_node.setInput(0, img_nrm)
            
            try:
                # Connect normal map to normal input (input 40)
                std_surface.setInput(40, nmap_node)
                print(f"    ✓ Connected normal map")
            except:
                print(f"    ✗ Failed to connect normal map")
        else:
            print(f"    ✗ Failed to set normal file parameter")

    # Layout nodes in the subnet
    subnet.layoutChildren()
    return subnet

def create_plastic_material(material_library: hou.Node) -> hou.Node:
    """
    Create a plastic material with specific properties inside the Material Library.
    """
    print(f"\nCreating plastic material...")
    
    # Create a subnet for the plastic material
    subnet = material_library.createNode("subnet", "plastic")

    # --- Create nodes inside the subnet ---
    # Output connector
    out_surf = subnet.createNode("subnetconnector", "Surface_Out")
    safe_set_parm(out_surf, "connectorkind", "output")
    safe_set_parm(out_surf, "parmname", "surface")
    safe_set_parm(out_surf, "parmlabel", "surface")
    safe_set_parm(out_surf, "parmtype", "surface")

    # Standard Surface for plastic
    std_surface = subnet.createNode("mtlxstandard_surface", "plastic_surface")
    std_surface.setGenericFlag(hou.nodeFlag.Material, True)

    # Connect surface to the subnet's output
    out_surf.setInput(0, std_surface)

    # Set plastic material properties
    try:
        # Set specular roughness to 0.05 (very smooth/glossy)
        if std_surface.parm("specular_roughness"):
            safe_set_parm(std_surface, "specular_roughness", 0.05)
            print(f"    ✓ Set specular roughness to 0.05")
        
        # Set transmission to 1.0 (fully transparent)
        if std_surface.parm("transmission"):
            safe_set_parm(std_surface, "transmission", 1.0)
            print(f"    ✓ Set transmission to 1.0")
        
        # Try alternative parameter names if the above don't work
        for roughness_parm in ["roughness", "specular_roughness", "inputs:specular_roughness"]:
            if std_surface.parm(roughness_parm):
                safe_set_parm(std_surface, roughness_parm, 0.05)
                print(f"    ✓ Set {roughness_parm} to 0.05")
                break
        
        for transmission_parm in ["transmission", "inputs:transmission", "transmission_weight"]:
            if std_surface.parm(transmission_parm):
                safe_set_parm(std_surface, transmission_parm, 1.0)
                print(f"    ✓ Set {transmission_parm} to 1.0")
                break
                
    except Exception as e:
        print(f"    ✗ Warning: Could not set all plastic material properties: {e}")

    # Layout nodes in the subnet
    subnet.layoutChildren()
    print(f"    ✓ Created plastic material")
    return subnet

def build_solaris_material_network(lop_net: hou.Node, prefixes: List[str], assets_dir: str, input_node: hou.Node = None) -> hou.Node:
    """
    Generates a Material Library, populates it with shaders inside subnets,
    and then creates an Attribute Wrangle to assign them.
    """
    if not lop_net or lop_net.type().name() != 'lopnet':
        raise ValueError(f"A valid LOP network ('lopnet') must be provided. Got type '{lop_net.type().name() if lop_net else 'None'}'.")

    # 1. Add Dome Light first for easier debugging (separate merge at top)
    try:
        dome_light = lop_net.createNode("domelight", "dome_light")
        if input_node:
            dome_light.setInput(0, input_node)
        
        safe_set_parm(dome_light, "primpath", "/World/Lights/DomeLight")
        
        # Set HDRI texture
        safe_set_parm(dome_light, "xn__inputstexturefile_r3ah", "$HIP/hdri/studio_small_09_2k.exr")
        
        # Set intensity
        safe_set_parm(dome_light, "xn__inputsintensity_i0a", 1.0)
        
        # Enable render light geometry
        safe_set_parm(dome_light, "xn__karmalightrenderlightgeo_4fbf", True)
        
        print("Added dome light with HDRI texture and render light geometry enabled.")
        
        # Create a separate merge for dome light (merges at the top)
        dome_merge = lop_net.createNode("merge", "dome_merge")
        dome_merge.setInput(0, dome_light)

    except Exception as e:
        print(f"Warning: Could not create dome light: {e}")
        print("Continuing without dome light...")
        dome_merge = input_node if input_node else None

    # 2. Create a merge node to combine everything else
    merge_node = lop_net.createNode("merge", "scene_merge")
    merge_node.setInput(0, dome_merge)  # Dome light merge goes into first input
    
    # 3. Create a Material Library LOP
    mat_lib = lop_net.createNode("materiallibrary", "generated_materials")
    safe_set_parm(mat_lib, "matpathprefix", "/materials/")
    safe_set_parm(mat_lib, "matflag1", 0)  # Set matflag to 0 by default
    
    # Material library gets connected to merge input 1
    merge_node.setInput(1, mat_lib)
    
    # 4. Populate the library by creating a shader for each prefix.
    # Use a shared counter to handle duplicate base identifiers
    material_counter = {}
    for prefix in prefixes:
        create_solaris_mtlx_shader(mat_lib, prefix, assets_dir, material_counter)
    
    # 5. Create plastic material
    create_plastic_material(mat_lib)
        
    mat_lib.layoutChildren()
    print("\nSolaris Material Library created successfully.")

    # 6. Create an Attribute Wrangle LOP for material assignment
    wrangle_assign = lop_net.createNode("attribwrangle", "wrangle_material_assign")
    wrangle_assign.setInput(0, merge_node)  # Connect to merge instead
    
    # Set the primpattern to only process Mesh primitives
    safe_set_parm(wrangle_assign, "primpattern", "`lopinputprim('.', 0)` %type:Mesh")

    # 6. Set the VEX snippet for assignment
    vex_code = """// Skip material library primitives - don't assign materials to materials
if(startswith(s@primpath, "/materials/")) {
    return;
}

string material_id = "";

// Method 1: Try to get material ID directly from primitive name
// Since USD files are now modified, primitive names should be the base IDs
string prim_name = usd_name(0, s@primpath);
printf("Processing primitive: '%s', prim_name: '%s'\\n", s@primpath, prim_name);

if(prim_name != "" && !startswith(prim_name, "polySurface")) {
    // Check for Mesh_ prefix and extract the identifier after it
    if(startswith(prim_name, "Mesh_")) {
        string mesh_parts[] = split(prim_name, "_");
        if(len(mesh_parts) >= 2) {
            material_id = mesh_parts[1];  // Get the part after "Mesh_"
            printf("Found material ID '%s' from Mesh_ prefix in primitive name\\n", material_id);
        }
    }
    // Check if this looks like a direct base ID
    else if(len(prim_name) >= 6 && len(prim_name) <= 15 && 
       (startswith(prim_name, "B") || startswith(prim_name, "A"))) {
        material_id = prim_name;
        printf("Found material ID '%s' from primitive name\\n", material_id);
    }
}

// Method 2: Try USD name attribute
if(material_id == "") {
    string name_attr = usd_attrib(0, s@primpath, "name");
    printf("USD name attribute: '%s'\\n", name_attr);
    
    if(name_attr != "" && !startswith(name_attr, "polySurface")) {
        // Check for Mesh_ prefix in name attribute
        if(startswith(name_attr, "Mesh_")) {
            string mesh_parts[] = split(name_attr, "_");
            if(len(mesh_parts) >= 2) {
                material_id = mesh_parts[1];  // Get the part after "Mesh_"
                printf("Found material ID '%s' from Mesh_ prefix in name attribute\\n", material_id);
            }
        }
        else if(len(name_attr) >= 6 && len(name_attr) <= 15 && 
           (startswith(name_attr, "B") || startswith(name_attr, "A"))) {
            material_id = name_attr;
            printf("Found material ID '%s' from name attribute\\n", material_id);
        }
    }
}

// Method 3: Extract from primitive path
if(material_id == "") {
    string path_parts[] = split(s@primpath, "/");
    printf("Path parts: ");
    for(int i = 0; i < len(path_parts); i++) {
        printf("'%s' ", path_parts[i]);
    }
    printf("\\n");
    
    for(int i = 0; i < len(path_parts); i++) {
        string part = path_parts[i];
        
        // Check for Mesh_ prefix in path parts
        if(startswith(part, "Mesh_")) {
            string mesh_parts[] = split(part, "_");
            if(len(mesh_parts) >= 2) {
                material_id = mesh_parts[1];  // Get the part after "Mesh_"
                printf("Found material ID '%s' from Mesh_ prefix in path\\n", material_id);
                break;
            }
        }
        // Look for base ID patterns in path
        else if(len(part) >= 6 && len(part) <= 15 && 
           (startswith(part, "B") || startswith(part, "A")) && 
           part != "base" && !startswith(part, "polySurface")) {
            material_id = part;
            printf("Found material ID '%s' from primitive path\\n", material_id);
            break;
        }
    }
}

// Assign material if we found a valid identifier
if(material_id != "" && !startswith(material_id, "polySurface")) {
    string material_path = "/materials/" + material_id + "_base_material";
    printf("Attempting to assign material: '%s'\\n", material_path);
    
    // Check if the material exists before trying to assign it
    if(usd_hasapi(0, material_path, "MaterialBindingAPI")) {
        printf("Material exists, proceeding with assignment\\n");
    } else {
        printf("WARNING: Material path '%s' may not exist\\n", material_path);
    }
    
    usd_addrelationshiptarget(0, s@primpath, "material:binding", material_path);
    printf("SUCCESS: Assigned material '%s' to primitive '%s'\\n", 
           material_path, s@primpath);
} else {
    printf("FAILED: No valid material identifier found for primitive '%s' (prim_name: '%s')\\n", 
           s@primpath, prim_name);
}"""

    safe_set_parm(wrangle_assign, "snippet", vex_code)
    print("Created Attribute Wrangle for material assignment.")

    # 7. Add separate plastic material assignment wrangle
    plastic_wrangle = lop_net.createNode("attribwrangle", "wrangle_plastic_assign")
    plastic_wrangle.setInput(0, wrangle_assign)
    
    # Set the primpattern to target plastic geometry specifically
    safe_set_parm(plastic_wrangle, "primpattern", "/import_plastic %type:Mesh")
    
    # VEX code for plastic material assignment
    plastic_vex_code = """// Assign plastic material to all plastic geometry
string plastic_material_path = "/materials/plastic";

printf("Assigning plastic material to primitive: '%s'\\n", s@primpath);

// Assign the plastic material
usd_addrelationshiptarget(0, s@primpath, "material:binding", plastic_material_path);
printf("SUCCESS: Assigned plastic material '%s' to primitive '%s'\\n", 
       plastic_material_path, s@primpath);
"""
    
    safe_set_parm(plastic_wrangle, "snippet", plastic_vex_code)
    print("Created separate Attribute Wrangle for plastic material assignment.")

    # 8. Add Camera positioned as requested
    camera_lop = lop_net.createNode("camera", "render_camera")
    camera_lop.setInput(0, plastic_wrangle)  # Connect to plastic wrangle instead
    safe_set_parm(camera_lop, "primpath", "/World/Render/Camera")
    safe_set_parm(camera_lop, "tx", -1.0)   # -1 on X axis
    safe_set_parm(camera_lop, "ty", 0.3)    # 0.3 on Y axis  
    safe_set_parm(camera_lop, "tz", 1.0)    # 1 on Z axis
    safe_set_parm(camera_lop, "rx", -7.0)   # -7 degrees rotation X
    safe_set_parm(camera_lop, "ry", -45.0)   # 45 degrees rotation Y
    safe_set_parm(camera_lop, "rz", -1.0)   # -1 degrees rotation Z
    print("Added render camera at (-1, 0.3, 1) with rotation (-7, 45, -1).")

    # 9. Add Karma Render Settings - ensure we get the right node type
    karma_settings = None
    try:
        karma_settings = lop_net.createNode("karmarenderproperties", "karma_render_settings")
        karma_settings.setInput(0, camera_lop)
        safe_set_parm(karma_settings, "camera", "/World/Render/Camera")
        
        # Set output picture path
        safe_set_parm(karma_settings, "picture", "$HIP/render/model_`@model`.exr")
        
        # Set resolution mode to manual and set 1024x1024 resolution
        safe_set_parm(karma_settings, "res_mode", "manual")  # Manual resolution mode
        
        # Set resolution - using parmTuple for the resolution parameter
        resolution_tuple = karma_settings.parmTuple("resolution")
        resolution_tuple.set((1024, 1024))
        
        # Set samples per pixel
        safe_set_parm(karma_settings, "samplesperpixel", 64)  # Samples per pixel
        print("✓ Successfully created Karma render settings with 1024x1024 resolution.")
        
    except Exception as e:
        print(f"ERROR: Could not create karmarenderproperties: {e}")
        print("OUT_SCENE will connect to camera instead of render settings.")
        karma_settings = None
    
    # 10. Determine which node should be the input to OUT_SCENE
    if karma_settings is not None:
        final_input_node = karma_settings
        print("✓ Using karma_render_settings as input to OUT_SCENE.")
    else:
        final_input_node = camera_lop
        print("⚠ Using camera as input to OUT_SCENE (karma render settings failed).")
    
    # 11. Create OUT_SCENE null as the absolute final node
    try:
        out_scene = lop_net.createNode("null", "OUT_SCENE")
        out_scene.setInput(0, final_input_node)
        print(f"✓ Successfully connected OUT_SCENE to {final_input_node.name()}")
        
        # Set display flag on OUT_SCENE to make it the active node
        out_scene.setDisplayFlag(True)
        print("✓ Set display flag on OUT_SCENE - this is now the final active node.")
        
    except Exception as e:
        print(f"ERROR: Failed to create or connect OUT_SCENE: {e}")
        print(f"Using {final_input_node.name()} as the final node instead.")
        final_input_node.setDisplayFlag(True)
        out_scene = final_input_node

    # Layout the parent network to keep things tidy
    lop_net.layoutChildren()
    
    # Return OUT_SCENE as the final node in the chain
    return out_scene

# --- High-Level Orchestrator Function ---

def setup_solaris_materials_from_sops(sop_geo_path: str, prefixes: List[str], assets_dir: str) -> hou.Node:
    """
    Finds or creates a LOP network, imports geometry, builds materials, and assigns them.
    Now works directly with the modified USD files created by hip_manager.
    """
    print("--- Starting Solaris Material Setup ---")
    
    # 1. Get or create the LOP network using the robust pattern.
    obj_node = hou.node("/obj")
    if obj_node is None:
        obj_node = hou.node("/").createNode("obj", "obj")

    lopnet_name = "styrofoam_material_pipeline"
    lop_net = obj_node.node(lopnet_name)
    if lop_net is None:
        lop_net = obj_node.createNode("lopnet", lopnet_name)
        print(f"Created new LOP network at: '{lop_net.path()}'")
    else:
        print(f"Found existing LOP network at '{lop_net.path()}'. Clearing its contents.")
        clear_lop_network_children(lop_net)

    # 2. Create three separate SOP Import LOPs inside the LOP network
    
    # Model import (original geometry)
    sop_import_model = lop_net.createNode("sopimport", "import_model")
    safe_set_parm(sop_import_model, "soppath", f"{sop_geo_path}/OUT_MODEL")
    safe_set_parm(sop_import_model, "primpath", "/model")
    print(f"Created SOP Import LOP for model geometry at '{sop_geo_path}/OUT_MODEL'.")
    
    # Plastic import
    sop_import_plastic = lop_net.createNode("sopimport", "import_plastic")
    safe_set_parm(sop_import_plastic, "soppath", f"{sop_geo_path}/OUT_PLASTIC")
    safe_set_parm(sop_import_plastic, "primpath", "/plastic")
    print(f"Created SOP Import LOP for plastic geometry at '{sop_geo_path}/OUT_PLASTIC'.")
    
    # Styrofoam import
    sop_import_styrofoam = lop_net.createNode("sopimport", "import_styrofoam")
    safe_set_parm(sop_import_styrofoam, "soppath", f"{sop_geo_path}/OUT_STYROFOAM")
    safe_set_parm(sop_import_styrofoam, "primpath", "/styrofoam")
    print(f"Created SOP Import LOP for styrofoam geometry at '{sop_geo_path}/OUT_STYROFOAM'.")
    
    # 3. Merge all geometry imports
    geometry_merge = lop_net.createNode("merge", "geometry_merge")
    geometry_merge.setInput(0, sop_import_model)
    geometry_merge.setInput(1, sop_import_plastic)
    geometry_merge.setInput(2, sop_import_styrofoam)
    print(f"Created geometry merge node combining all three imports.")

    # 4. Call the material network builder
    final_node = build_solaris_material_network(
        lop_net=lop_net,
        prefixes=prefixes,
        assets_dir=assets_dir,
        input_node=geometry_merge
    )
    
    # 4. Set the display flag on the end of our new chain.
    final_node.setDisplayFlag(True)
    
    print(f"\n--- Solaris Material Setup Complete ---")
    print(f"Final node '{final_node.path()}' is now active.")
    
    return final_node


# --- Example Usage ---
if __name__ == "__main__":
    if 'hou' in locals():
        print("Running Solaris Material Manager example...")
        
        ASSET_PREFIXES = ["chair_base", "desk_base", "lamp_base"]
        ASSETS_DIRECTORY = os.path.join(hou.expandString("$HIP"), "assets", "textures")
        SOP_GEO_PATH = "/obj/assets"

        print(f"\nCreating dummy SOP geometry at '{SOP_GEO_PATH}'...")
        obj_net = hou.node("/obj")
        assets_geo = obj_net.node(os.path.basename(SOP_GEO_PATH.strip('/')))
        if not assets_geo:
            assets_geo = obj_net.createNode("geo", os.path.basename(SOP_GEO_PATH.strip('/')))
        
        clear_lop_network_children(assets_geo)

        last_node = None
        for i, prefix in enumerate(ASSET_PREFIXES):
            box = assets_geo.createNode("box", prefix)
            safe_set_parm(box, 'tx', i * 2.5)
            
            if last_node:
                 merge_node = assets_geo.createNode("merge", f"merge_{i}")
                 merge_node.setInput(0, last_node)
                 merge_node.setInput(1, box)
                 last_node = merge_node
            else:
                 last_node = box
        
        out_null = assets_geo.createNode("null", "OUT_ASSETS")
        out_null.setInput(0, last_node)
        out_null.setDisplayFlag(True)
        out_null.setRenderFlag(True)
        assets_geo.layoutChildren()
        print("Dummy geometry created.")

        setup_solaris_materials_from_sops(
            sop_geo_path=SOP_GEO_PATH,
            prefixes=ASSET_PREFIXES,
            assets_dir=ASSETS_DIRECTORY
        )
    else:
        print("This script is intended to be run within a Houdini session.")