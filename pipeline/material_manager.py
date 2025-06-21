# pipeline/material_manager.py

import os
from typing import List
import hou

def set_file_parameter(node, filepath):
    """Helper to set file parameter on a node, trying different parameter names"""
    param_names = ['filename', 'file', 'tex0', 'texture', 'map1']
    
    for name in param_names:
        parm = node.parm(name)
        if parm:
            parm.set(filepath)
            return True
    
    # If none of the standard names work, look for any parameter with 'file' in the name
    for parm in node.parms():
        if 'file' in parm.name().lower():
            parm.set(filepath)
            return True
    
    # Last resort: print all parameters
    print(f"  ERROR: Could not find file parameter on {node.name()}")
    print(f"  Available parameters:")
    for parm in node.parms()[:10]:  # Show first 10 params
        print(f"    - {parm.name()} ({parm.parmTemplate().type()})")
    
    return False


def connect_vop_nodes(dest_node, dest_input_name, src_node, src_output_idx=0):
    """Connect VOP nodes using various methods"""
    # Method 1: Try setNamedInput (some VOP nodes support this)
    try:
        dest_node.setNamedInput(dest_input_name, src_node, src_output_idx)
        return True
    except:
        pass
    
    # Method 2: Try parameter-based connection
    # Many VOP nodes expose their inputs as parameters
    try:
        parm = dest_node.parm(dest_input_name)
        if parm:
            # Some parameters want a path reference
            parm.set(src_node.path())
            return True
    except:
        pass
    
    # Method 3: Try to find the input index and use setInput
    try:
        # Common input indices for mtlxstandard_surface
        input_map = {
            "base_color": 1,
            "base": 1,
            "metallic": 4,
            "metalness": 4, 
            "roughness": 5,
            "specular_roughness": 5,
            "normal": 40,
        }
        
        if dest_input_name.lower() in input_map:
            idx = input_map[dest_input_name.lower()]
            dest_node.setInput(idx, src_node, src_output_idx)
            return True
            
    except Exception as e:
        print(f"    Failed to connect using index: {e}")
    
    return False


def create_MTLX_Subnet(matnet: hou.Node, prefix: str, assets_dir: str) -> None:
    """
    Inside a hou.matnet, create a MaterialX subnet for `prefix`,
    wiring up its diffuse/metal+rough/normal .pngs.
    """
    # Remove "_base" from prefix for texture file names
    name = prefix.strip()
    texture_prefix = name.replace("_base", "")
    
    diff = os.path.join(assets_dir, f"{texture_prefix}_texture_diff.png")
    mr   = os.path.join(assets_dir, f"{texture_prefix}_texture_MR.png")
    nrm  = os.path.join(assets_dir, f"{texture_prefix}_texture_normal.png")
    
    print(f"\nCreating material for: {name}")
    print(f"  Looking for textures with prefix: {texture_prefix}")
    print(f"  Diffuse: {os.path.basename(diff)} (exists: {os.path.exists(diff)})")
    print(f"  MR: {os.path.basename(mr)} (exists: {os.path.exists(mr)})")
    print(f"  Normal: {os.path.basename(nrm)} (exists: {os.path.exists(nrm)})")

    # Create subnet
    subnet = matnet.createNode("subnet", f"{name}_mtlx")
    subnet.moveToGoodPosition()
    
    # Clear any existing children
    for c in subnet.allSubChildren():
        subnet.deleteItems([c])

    # Create nodes inside the subnet
    # Output connector
    out_surf = subnet.createNode("subnetconnector", "Surface_Out")
    out_surf.parm("connectorkind").set("output")
    out_surf.parm("parmname").set("surface")
    out_surf.parm("parmlabel").set("surface")
    out_surf.parm("parmtype").set("surface")
    
    # Standard Surface
    std = subnet.createNode("mtlxstandard_surface", f"std_{name}")
    
    # Connect surface to output
    out_surf.setInput(0, std)
    
    # UV Coordinates
    tc = subnet.createNode("mtlxtexcoord", f"uv_{name}")
    if tc.parm("signature"):
        tc.parm("signature").set("vector2")

    # Process each texture type
    nodes_created = []
    
    # Diffuse texture
    if os.path.exists(diff):
        print("  Setting up diffuse texture...")
        img = subnet.createNode("mtlximage", f"diff_{name}")
        
        # Set signature to color3 for diffuse texture
        if img.parm("signature"):
            img.parm("signature").set("color3")
        
        if set_file_parameter(img, diff):
            # As requested, the texcoord input is NOT connected for the diffuse image.
            # The node will use its 'default' color value.
            nodes_created.append(img)
            
            # Try to connect to base_color
            if connect_vop_nodes(std, "base_color", img):
                print("    Connected diffuse to base_color")
            elif connect_vop_nodes(std, "base", img):
                print("    Connected diffuse to base")
            else:
                print("    WARNING: Could not connect diffuse")

    # Metallic/Roughness map
    if os.path.exists(mr):
        print("  Setting up metallic/roughness texture...")
        img_mr = subnet.createNode("mtlximage", f"mr_{name}")
        
        # Set signature to color3 for MR texture
        if img_mr.parm("signature"):
            img_mr.parm("signature").set("color3")
        
        if set_file_parameter(img_mr, mr):
            # As requested, the texcoord input is NOT connected for the MR image.
            # The node will use its 'default' color value.
            nodes_created.append(img_mr)
            
            # Use mtlxseparate3c to split R and G channels
            try:
                sep_mr = subnet.createNode("mtlxseparate3c", f"sep_mr_{name}")
                sep_mr.setInput(0, img_mr)
                nodes_created.append(sep_mr)

                # Connect R channel (output 0) to metallic
                if connect_vop_nodes(std, "metallic", sep_mr, src_output_idx=0):
                    print("    Connected metallic (R channel)")
                elif connect_vop_nodes(std, "metalness", sep_mr, src_output_idx=0):
                    print("    Connected metalness (R channel)")
                else:
                    print("    WARNING: Could not connect metallic")

                # Connect G channel (output 1) to roughness
                if connect_vop_nodes(std, "roughness", sep_mr, src_output_idx=1):
                    print("    Connected roughness (G channel)")
                elif connect_vop_nodes(std, "specular_roughness", sep_mr, src_output_idx=1):
                    print("    Connected specular_roughness (G channel)")
                else:
                    print("    WARNING: Could not connect roughness")
            
            except Exception as e:
                print(f"    Could not create mtlxseparate3c node: {e}")


    # Normal map
    if os.path.exists(nrm):
        print("  Setting up normal map...")
        img_n = subnet.createNode("mtlximage", f"nrm_{name}")
        
        # Set signature to vector3 for normal map data
        if img_n.parm("signature"):
            img_n.parm("signature").set("vector3")
            
        if set_file_parameter(img_n, nrm):
            # Connect texcoord (UVs) to the 'texcoord' input for the normal map.
            # This connection is required for normal mapping to work correctly.
            img_n.setInput(0, tc)
            nodes_created.append(img_n)
            
            # Normal map converter
            try:
                nmap = subnet.createNode("mtlxnormalmap", f"nmap_{name}")
                nmap.setInput(0, img_n)
                nodes_created.append(nmap)
                
                if connect_vop_nodes(std, "normal", nmap):
                    print("    Connected normal map")
                else:
                    print("    WARNING: Could not connect normal map")
                    
            except Exception as e:
                print(f"    Could not create normal map node: {e}")

    # Layout nodes
    subnet.layoutChildren()
    
    # Mark as material
    subnet.setGenericFlag(hou.nodeFlag.Material, True)
    
    print(f"  Material subnet created with {len(nodes_created)} texture nodes")


def assign_materials_to_geo(prefixes: List[str], matnet_path: str) -> None:
    """
    For each prefix, create a Material SOP in /obj/assets that
    points to the corresponding MTLX subnet under the given matnet.
    """
    geo = hou.node("/obj/assets")
    if not geo:
        raise RuntimeError("Could not find /obj/assets geo")

    matnet = hou.node(matnet_path)
    if not matnet:
        raise RuntimeError(f"Matnet not found at {matnet_path}")

    # Find the last node in the network to connect to
    last_node = None
    for node in geo.children():
        if node.type().name() != "material" and node.isDisplayFlagSet():
            last_node = node
            break
    
    # If no display flag set, find the last non-material node
    if not last_node:
        for node in reversed(list(geo.children())):
            if node.type().name() != "material":
                last_node = node
                break
    
    print(f"\nAssigning materials, starting from node: {last_node.name() if last_node else 'None'}")

    # Create material assignments
    material_nodes = []
    
    for idx, prefix in enumerate(prefixes):
        mat_sop = geo.createNode("material", f"mat_{prefix}")
        
        # Connect to previous node
        if last_node:
            mat_sop.setInput(0, last_node)
        
        # Set parameters
        group_pattern = f"{prefix}*"
        mat_path = f"{matnet_path}/{prefix}_mtlx"
        
        # Try different parameter schemes
        success = False
        
        # Scheme 1: group1, shop_materialpath1 (single slot)
        if mat_sop.parm("group1") and mat_sop.parm("shop_materialpath1"):
            mat_sop.parm("group1").set(group_pattern)
            mat_sop.parm("shop_materialpath1").set(mat_path)
            success = True
            print(f"  Material {idx+1}: group1='{group_pattern}', path='{mat_path}'")
            
        # Scheme 2: group, shop_materialpath (legacy)
        elif mat_sop.parm("group") and mat_sop.parm("shop_materialpath"):
            mat_sop.parm("group").set(group_pattern)
            mat_sop.parm("shop_materialpath").set(mat_path)
            success = True
            print(f"  Material {idx+1}: group='{group_pattern}', path='{mat_path}'")
        
        if not success:
            print(f"  WARNING: Could not set parameters for {prefix}")
            # Debug: print available parameters
            print("    Available parameters:")
            for parm in mat_sop.parms()[:20]:
                if 'group' in parm.name() or 'material' in parm.name():
                    print(f"      - {parm.name()}")
        
        mat_sop.moveToGoodPosition()
        material_nodes.append(mat_sop)
        last_node = mat_sop
    
    # Layout all nodes
    geo.layoutChildren()
    
    print(f"\nMaterial assignment complete - created {len(material_nodes)} material nodes")


# Alternative simplified version for testing
def create_basic_material(matnet: hou.Node, prefix: str, assets_dir: str) -> None:
    """Simplified material creation for debugging"""
    name = prefix.strip()
    texture_prefix = name.replace("_base", "")
    
    # Create a simple Principled Shader instead of MaterialX
    shader = matnet.createNode("principledshader", f"{name}_shader")
    
    # Set diffuse texture if it exists
    diff = os.path.join(assets_dir, f"{texture_prefix}_texture_diff.png")
    if os.path.exists(diff):
        shader.parm("basecolor_useTexture").set(1)
        shader.parm("basecolor_texture").set(diff)
    
    # Set metallic/roughness if exists
    mr = os.path.join(assets_dir, f"{texture_prefix}_texture_MR.png")
    if os.path.exists(mr):
        shader.parm("metallic_useTexture").set(1)
        shader.parm("metallic_texture").set(mr)
        shader.parm("metallic_textureChan").set("r")  # R channel
        
        shader.parm("rough_useTexture").set(1)
        shader.parm("rough_texture").set(mr)
        shader.parm("rough_textureChan").set("g")  # G channel
    
    # Set normal if exists
    nrm = os.path.join(assets_dir, f"{texture_prefix}_texture_normal.png")
    if os.path.exists(nrm):
        shader.parm("baseBumpAndNormal_enable").set(1)
        shader.parm("baseNormal_texture").set(nrm)
    
    shader.setGenericFlag(hou.nodeFlag.Material, True)
    shader.moveToGoodPosition()
    
    print(f"Created basic material: {name}_shader")