# pipeline/hip_manager.py

import os
import re
import json
from abc import ABC, abstractmethod
from typing import List, Optional

import hou
from pxr import Usd, Sdf, UsdGeom


def extract_base_identifier_from_filename(filename: str) -> str:
    """
    Extract the base identifier from a USD filename.
    Examples:
    - 'nan_A3DCZYC5E6B3MT80.usd' -> 'A3DCZYC5E6B3MT80'
    - 'B000BRBYJ8_A3DCQGU4ZVZ7XB5H_base.usd' -> 'B000BRBYJ8'
    - 'Mesh_B0009VXBAQ.usd' -> 'B0009VXBAQ'
    """
    # Remove file extension
    base_name = os.path.splitext(filename)[0]
    
    # Split by underscore
    parts = base_name.split('_')
    
    # Special handling for 'nan_' prefix
    if len(parts) >= 2 and parts[0] == 'nan':
        return parts[1]
    
    # Handle cases like "Mesh_B0009VXBAQ"
    if len(parts) >= 2 and parts[0] == 'Mesh':
        return parts[1]
    
    # Look for product identifier patterns (alphanumeric, often starts with B or A)
    for part in parts:
        if len(part) >= 6 and len(part) <= 15 and part.isalnum():
            if part.startswith('B') or part.startswith('A'):
                if part != 'base':  # Skip the 'base' suffix
                    return part
    
    # If no pattern found, use the first part
    return parts[0] if parts else base_name


def _copy_prim_recursive(source_prim: Usd.Prim, target_parent_prim: Usd.Prim, base_id: str = None):
    """
    Recursively copies a source USD prim and its entire subtree to a new location
    under a target parent prim. All attributes, metadata, and relationships are copied.
    This function is designed to copy between potentially different stages,
    with explicit handling for normals and UVs on UsdGeom.Mesh prims.
    
    If base_id is provided, it will rename certain child primitives to use the base_id.
    """
    # Determine the new name for this prim
    original_name = source_prim.GetName()
    new_name = original_name
    
    # If we have a base_id, rename certain primitive patterns
    if base_id:
        # Handle Mesh_ prefixed primitives
        if original_name.startswith("Mesh_"):
            new_name = f"Mesh_{base_id}"
            print(f"        Renaming child prim: '{original_name}' -> '{new_name}'")
        # Handle other patterns that might need renaming
        elif len(original_name) >= 6 and (original_name.startswith("B") or original_name.startswith("A")):
            # This looks like a product ID that should be replaced with our base_id
            new_name = base_id
            print(f"        Renaming child prim: '{original_name}' -> '{new_name}'")
    
    new_path = target_parent_prim.GetPath().AppendChild(new_name)
    
    # Define the new prim in the target stage, preserving its type name
    new_prim = target_parent_prim.GetStage().DefinePrim(new_path, source_prim.GetTypeName())
    if not new_prim:
        print(f"      Warning: Failed to define new prim at {new_path}. Skipping subtree copy for {source_prim.GetPath()}")
        return

    # Copy all authored attributes from the source prim to the new prim
    for attr in source_prim.GetAttributes():
        attr_name = attr.GetName()
        attr_type = attr.GetTypeName()
        
        if attr.HasAuthoredValue():
            # Special handling for UsdGeom.Mesh specific primvars: normals and UVs
            if new_prim.IsA(UsdGeom.Mesh):
                new_mesh_prim = UsdGeom.Mesh(new_prim)
                source_geom_prim = UsdGeom.Imageable(source_prim) # Used to get source primvar for interpolation

                if attr_name == UsdGeom.Tokens.normals:
                    new_normals_attr = new_mesh_prim.GetNormalsAttr()
                    new_normals_attr.Set(attr.Get())
                    # Get and set interpolation for normals
                    source_primvar = source_geom_prim.GetPrimvar(UsdGeom.Tokens.normals)
                    if source_primvar and source_primvar.HasAuthoredInterpolation():
                        new_normals_attr.SetMetadata("interpolation", source_primvar.GetInterpolation())
                    print(f"        Copied and explicitly set normals attribute: {attr_name}")
                elif attr_name.startswith("primvars:st"):
                    # Extract just "st" from "primvars:st" or "primvars:st0" etc.
                    primvar_base_name = attr_name.split(':', 1)[-1] 
                    new_st_primvar = new_mesh_prim.CreatePrimvar(primvar_base_name, attr_type)
                    new_st_primvar.Set(attr.Get())
                    # Get and set interpolation for UVs
                    source_primvar = source_geom_prim.GetPrimvar(attr_name)
                    if source_primvar and source_primvar.HasAuthoredInterpolation():
                        new_st_primvar.SetInterpolation(source_primvar.GetInterpolation())
                    print(f"        Copied and explicitly set UV (st) primvar: {attr_name}")
                else:
                    # Generic attribute copy for other attributes on a mesh prim
                    new_attr_generic = new_prim.CreateAttribute(attr_name, attr_type)
                    new_attr_generic.Set(attr.Get())
                    print(f"        Copied general attribute on mesh: {attr_name} ({attr_type})")
            else:
                # Generic attribute copy for non-mesh prims
                new_attr_generic = new_prim.CreateAttribute(attr_name, attr_type)
                new_attr_generic.Set(attr.Get())
                print(f"        Copied general attribute: {attr_name} ({attr_type})")
        else:
            print(f"      Skipped unauthored attribute: {attr_name}")
    
    # Copy all metadata from the source prim to the new prim
    for key, value in source_prim.GetAllMetadata().items():
        # Skip metadata that is automatically set by DefinePrim or SetTypeName to avoid conflicts
        if key not in ['specifier', 'typeName']:
            new_prim.SetMetadata(key, value)
    
    # Copy relationships (e.g., material bindings, collections)
    for rel in source_prim.GetRelationships():
        new_rel = new_prim.CreateRelationship(rel.GetName())
        new_rel.SetTargets(rel.GetTargets()) # Set targets as Sdf.Path objects

    # Recursively call this function for all children of the source prim
    for child in source_prim.GetChildren():
        _copy_prim_recursive(child, new_prim, base_id)


def _prim_contains_mesh(prim: Usd.Prim) -> bool:
    """
    Recursively checks if the given prim or any of its descendants is a UsdGeom.Mesh.
    """
    if prim.IsA(UsdGeom.Mesh):
        return True
    
    for child in prim.GetChildren():
        if _prim_contains_mesh(child):
            return True
    return False


def rename_usd_primitives(usd_path: str, base_id: str) -> str:
    """
    Creates a new USD file by copying the relevant asset prim
    from the original USD, renaming it to the base_id, and saving it as a new file.
    This ensures all attributes are preserved and the asset root prim
    matches the base_id.
    Returns the path to the newly created USD file.
    """
    # Create a modified filename in the same directory as the original
    original_dir = os.path.dirname(usd_path)
    original_name = os.path.basename(usd_path)
    modified_name = f"modified_{original_name}"
    modified_path = os.path.join(original_dir, modified_name)
    
    # Check if modified file already exists and skip if it does
    if os.path.exists(modified_path):
        print(f"  Modified USD file already exists: {modified_name}. Skipping modification.")
        return modified_path
    
    print(f"  Preparing to modify USD file: {original_name} -> {modified_name}")
    print(f"  Target base_id: {base_id}")
    
    # Open the original USD file as the source stage
    source_stage = Usd.Stage.Open(usd_path)
    if not source_stage:
        raise RuntimeError(f"Failed to open source USD file: {usd_path}")
    
    # Create a new, empty USD stage in memory to build the modified asset
    new_stage = Usd.Stage.CreateNew(modified_path)
    if not new_stage:
        raise RuntimeError(f"Failed to create new USD stage at: {modified_path}")

    # Find the most suitable "asset root" prim in the source stage to copy and rename.
    # This is the highest non-root/non-world prim that contains mesh geometry.
    prim_to_rename_candidate = None
    for prim in source_stage.Traverse():
        # Skip the absolute root prim '/' and common top-level scene containers like '/World'
        if prim.GetPath() == Sdf.Path.absoluteRootPath or prim.GetName() == "World":
            continue

        # Check if this prim itself is a mesh, or if it has any UsdGeom.Mesh descendants
        if _prim_contains_mesh(prim):
            # If we haven't found a candidate yet, or if this new candidate is an
            # ancestor of the current best candidate, update our best candidate.
            # This ensures we pick the highest relevant prim that is a container for meshes.
            if prim_to_rename_candidate is None or \
               prim_to_rename_candidate.GetPath().HasPrefix(prim.GetPath()):
                prim_to_rename_candidate = prim
    
    # If no suitable prim containing mesh data was found, log a warning and return original path
    if not prim_to_rename_candidate:
        print(f"  Warning: No suitable asset root prim containing mesh data found for renaming in {original_name}. Skipping renaming.")
        # If no modification is done, we might still want to return the original path for import
        return usd_path

    # The chosen prim from the source stage to copy and rename
    source_asset_root_prim = prim_to_rename_candidate

    # IMPORTANT: Use the base_id parameter, not the source prim name
    # Define the new root prim in the new stage, at the root level, with the desired base_id name.
    new_asset_root_path = Sdf.Path.absoluteRootPath.AppendChild(base_id)
    new_asset_root_prim = new_stage.DefinePrim(new_asset_root_path, source_asset_root_prim.GetTypeName())
    
    if not new_asset_root_prim:
        raise RuntimeError(f"Failed to define new asset root prim at {new_asset_root_path} in new stage.")

    print(f"    Copying and renaming asset root from '{source_asset_root_prim.GetPath()}' to '{new_asset_root_path}' in new file.")
    print(f"    Using base_id '{base_id}' as the new prim name (ignoring source name '{source_asset_root_prim.GetName()}')")

    # Copy all attributes, metadata, and relationships from the source asset root to the new asset root
    for attr in source_asset_root_prim.GetAttributes():
        new_attr = new_asset_root_prim.CreateAttribute(attr.GetName(), attr.GetTypeName())
        if attr.HasAuthoredValue():
            new_attr.Set(attr.Get())

    for key, value in source_asset_root_prim.GetAllMetadata().items():
        if key not in ['specifier', 'typeName']:
            new_asset_root_prim.SetMetadata(key, value)

    for rel in source_asset_root_prim.GetRelationships():
        new_rel = new_asset_root_prim.CreateRelationship(rel.GetName())
        new_rel.SetTargets(rel.GetTargets())

    # Recursively copy all children (and their entire subtrees) from the source asset root
    # to be under the newly created asset root in the new stage.
    print(f"    Recursively copying children from {source_asset_root_prim.GetPath()} to {new_asset_root_path}...")
    for child in source_asset_root_prim.GetChildren():
        _copy_prim_recursive(child, new_asset_root_prim, base_id)
    
    # Save the newly created USD file
    new_stage.Save()
    print(f"  Saved modified USD: {modified_path}")
    
    return modified_path


def _create_unique_hip_filename(hip_path: str) -> str:
    """
    Create a unique HIP filename if the target already exists.
    Appends incrementing numbers until a unique filename is found.
    """
    if not os.path.exists(hip_path):
        return hip_path
    
    base_path, ext = os.path.splitext(hip_path)
    counter = 1
    
    while True:
        new_path = f"{base_path}_{counter:03d}{ext}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1


class HipManager(ABC):
    @abstractmethod
    def load(self, hip_path: str) -> None:
        pass

    @abstractmethod
    def save(self, hip_path: Optional[str] = None) -> None:
        pass

    @abstractmethod
    def import_usds(
        self,
        usd_paths: List[str],
        obj_name: str = "assets",
        hda_path: Optional[str] = None
    ) -> None:
        pass


class HoudiniHipManager(HipManager):
    def get_material_prefixes_from_usds(self, usd_paths: List[str]) -> List[str]:
        """
        Extract material prefixes from USD file paths, filtering out modified files.
        Returns the base identifiers that should be used for material creation.
        """
        prefixes = []
        for usd_path in usd_paths:
            filename = os.path.basename(usd_path)
            
            # Skip modified USD files - we only want original files for prefix extraction
            if filename.startswith("modified_"):
                continue
                
            # Extract the base identifier from the original filename
            base_id = extract_base_identifier_from_filename(filename)
            prefixes.append(base_id)
        
        return sorted(set(prefixes))  # Remove duplicates and sort

    def load(self, hip_path: str) -> None:
        if not os.path.isfile(hip_path):
            raise FileNotFoundError(f"HIP file not found: {hip_path}")
        hou.hipFile.load(hip_path)

    def save(self, hip_path: Optional[str] = None) -> None:
        if hip_path:
            # Create unique filename if target already exists
            unique_hip_path = _create_unique_hip_filename(hip_path)
            if unique_hip_path != hip_path:
                print(f"Target HIP file already exists. Saving as: {os.path.basename(unique_hip_path)}")
            hou.hipFile.save(unique_hip_path)
        else:
            hou.hipFile.save()

    def import_usds(
        self,
        usd_paths: List[str],
        obj_name: str = "assets",
        hda_path: Optional[str] = None
    ) -> None:
        # Filter out any modified USD files from the input list to avoid duplicates
        filtered_usd_paths = []
        for usd_path in usd_paths:
            filename = os.path.basename(usd_path)
            if filename.startswith("modified_"):
                print(f"Skipping modified USD file from input: {filename}")
                continue
            filtered_usd_paths.append(usd_path)
        
        usd_paths = filtered_usd_paths
        
        if not usd_paths:
            print("Warning: No valid USD files to process after filtering.")
            return

        # 1) Grab /obj
        obj = hou.node("/obj")
        if obj is None:
            raise RuntimeError("Could not find /obj context")

        # 2) Make Geo container
        container = obj.createNode("geo", obj_name)
        container.moveToGoodPosition()

        # Remove default file1 SOP
        default = container.node("file1")
        if default:
            default.destroy()

        # 3) Create a mapping of USD files to their base identifiers
        # And rename primitives within the USD files
        usd_mapping = {}
        processed_usd_paths = [] # To store paths of modified USD files
        for usd in usd_paths:
            if not os.path.isfile(usd):
                print(f"Warning: USD file not found: {usd}. Skipping.")
                continue

            filename = os.path.basename(usd)
            base_id = extract_base_identifier_from_filename(filename)
            usd_mapping[filename] = base_id
            
            print(f"Processing USD: {filename}")
            print(f"  Extracted base_id: {base_id}")
            
            # Rename primitives in the USD file by creating a new, modified USD file
            modified_usd_path = rename_usd_primitives(usd, base_id)
            processed_usd_paths.append(modified_usd_path)
            
            print(f"  Created modified USD: {os.path.basename(modified_usd_path)}")
            print(f"  Should contain primitive named: {base_id}")
            print("  " + "-"*50)
            
        # Save the mapping to a JSON file in $HIP (useful for material assignment later)
        hip_dir = hou.expandString("$HIP")
        mapping_file = os.path.join(hip_dir, "usd_material_mapping.json")
        with open(mapping_file, 'w') as f:
            json.dump(usd_mapping, f, indent=2)
        
        print(f"Saved USD mapping to: {mapping_file}")
        print(f"Mapping: {usd_mapping}")

        # 4) USD Import SOP per processed USD file
        file_nodes = []
        for usd_original_path, usd_processed_path in zip(usd_paths, processed_usd_paths):
            # The base_id comes from the original filename
            filename = os.path.basename(usd_original_path)
            base_id = usd_mapping[filename]

            # Create USD import node
            usd_sop = container.createNode("usdimport", f"import_{base_id}")

            # Set the USD file path to the *modified* USD file
            matched = False
            for parm in usd_sop.parms():
                tmpl = parm.parmTemplate()
                if tmpl.type() == hou.parmTemplateType.String and "file" in parm.name().lower():
                    parm.set(usd_processed_path) # Use the processed USD path
                    matched = True
                    break
            if not matched:
                avail = [p.name() for p in usd_sop.parms()]
                raise RuntimeError(
                    f"No file‐type parm on {usd_sop.type().name()}; "
                    f"available parms: {avail}"
                )

            usd_sop.moveToGoodPosition()
            file_nodes.append(usd_sop)

        # 5) Merge
        merge = container.createNode("merge", "merge_usds")
        for idx, fn in enumerate(file_nodes):
            merge.setInput(idx, fn)
        merge.moveToGoodPosition()

        # 6) OUT null
        out_null = container.createNode("null", "OUT")
        out_null.setInput(0, merge)
        out_null.moveToGoodPosition()


        # 11) Primitive Wrangle (NEW: added before z_to_y)
        prim_wrangle = container.createNode("attribwrangle", "primitive_wrangle")
        prim_wrangle.setInput(0, out_null)
        prim_wrangle.parm("class").set(1)  # Set to primitive mode
        prim_wrangle.parm("snippet").set("i@prim_amount = @primnum + 1;")

        prim_wrangle.moveToGoodPosition()

        # 12) Rotate X -90 (Z-up → Y-up) - Now connects to primitive wrangle
        xform = container.createNode("xform", "z_to_y")
        xform.setInput(0, prim_wrangle)
        xform.parm("rx").set(-90)
        xform.moveToGoodPosition()

        # 13) HDA (optional) - Now connects to z_to_y
        if hda_path:
            if not os.path.isfile(hda_path):
                raise FileNotFoundError(f"HDA file not found: {hda_path}")
            hou.hda.installFile(hda_path)
            defs = hou.hda.definitionsInFile(hda_path)
            if not defs:
                raise RuntimeError(f"No HDA definitions found in {hda_path}")
            hda_type = defs[0].nodeTypeName()
            hda_node = container.createNode(hda_type, "wrapped_assets")
            hda_node.setInput(0, xform)  # Connect to z_to_y instead of out_model
            hda_node.moveToGoodPosition()
            
            # 14) Create output nulls for HDA outputs
            out_styrofoam = container.createNode("null", "OUT_STYROFOAM")
            out_styrofoam.setInput(0, hda_node, 0)  # Connect to first output
            out_styrofoam.moveToGoodPosition()
            
            out_plastic = container.createNode("null", "OUT_PLASTIC") 
            out_plastic.setInput(0, hda_node, 1)  # Connect to second output
            out_plastic.moveToGoodPosition()
            
            # NEW: Third output - OUT_MODEL connects to third HDA output
            out_model = container.createNode("null", "OUT_MODEL")
            out_model.setInput(0, hda_node, 2)  # Connect to third output
            out_model.moveToGoodPosition()
            
            # Set display flag on one of the outputs
            out_styrofoam.setDisplayFlag(True)
            
        else:
            # If no HDA, create OUT_MODEL and connect it to z_to_y
            out_model = container.createNode("null", "OUT_MODEL")
            out_model.setInput(0, xform)  # Connect to z_to_y
            out_model.moveToGoodPosition()
            out_model.setDisplayFlag(True)

        # 15) Layout
        container.layoutChildren()