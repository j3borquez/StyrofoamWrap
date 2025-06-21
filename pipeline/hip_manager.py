# pipeline/hip_manager.py

import os
from abc import ABC, abstractmethod
from typing import List, Optional

import hou


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
    def load(self, hip_path: str) -> None:
        if not os.path.isfile(hip_path):
            raise FileNotFoundError(f"HIP file not found: {hip_path}")
        hou.hipFile.load(hip_path)

    def save(self, hip_path: Optional[str] = None) -> None:
        if hip_path:
            hou.hipFile.save(hip_path)
        else:
            hou.hipFile.save()

    def import_usds(
        self,
        usd_paths: List[str],
        obj_name: str = "assets",
        hda_path: Optional[str] = None
    ) -> None:
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

        # 3) USD Import SOP per USD
        file_nodes = []
        for usd in usd_paths:
            if not os.path.isfile(usd):
                raise FileNotFoundError(f"USD file not found: {usd}")
            base = os.path.splitext(os.path.basename(usd))[0]
            usd_sop = container.createNode("usdimport", f"import_{base}")

            # Dynamically find a string parm whose name contains "file"
            matched = False
            for parm in usd_sop.parms():
                tmpl = parm.parmTemplate()
                if tmpl.type() == hou.parmTemplateType.String and "file" in parm.name().lower():
                    parm.set(usd)
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

        # 4) Merge
        merge = container.createNode("merge", "merge_usds")
        for idx, fn in enumerate(file_nodes):
            merge.setInput(idx, fn)
        merge.moveToGoodPosition()

        # 5) OUT null
        out_null = container.createNode("null", "OUT")
        out_null.setInput(0, merge)
        out_null.moveToGoodPosition()

        # 6) Rotate X -90 (Z-up → Y-up)
        xform = container.createNode("xform", "z_to_y")
        xform.setInput(0, out_null)
        xform.parm("rx").set(-90)
        xform.moveToGoodPosition()

        # 7) Connectivity
        conn = container.createNode("connectivity", "connectivity_prim_wedge")
        conn.setInput(0, xform)
        conn.parm("connecttype").set(1)
        conn.parm("attribname").set("wedge")
        conn.moveToGoodPosition()

        # 8) Blast
        blast = container.createNode("blast", "blast_wedge")
        blast.setInput(0, conn)
        blast.parm("group").set('!@wedge==@wedgenum')
        blast.moveToGoodPosition()

        # 9) Unpack USD
        unpack = container.createNode("unpackusd", "unpack_usd")
        unpack.setInput(0, blast)
        unpack.parm("output").set("polygons")
        unpack.moveToGoodPosition()

        # 10) HDA (optional)
        last_node = unpack
        if hda_path:
            if not os.path.isfile(hda_path):
                raise FileNotFoundError(f"HDA file not found: {hda_path}")
            hou.hda.installFile(hda_path)
            defs = hou.hda.definitionsInFile(hda_path)
            if not defs:
                raise RuntimeError(f"No HDA definitions found in {hda_path}")
            hda_type = defs[0].nodeTypeName()
            hda_node = container.createNode(hda_type, "wrapped_assets")
            hda_node.setInput(0, unpack)
            hda_node.moveToGoodPosition()
            last_node = hda_node

        # 11) Final null & display
        final_null = container.createNode("null", "FINAL_OUT")
        final_null.setInput(0, last_node)
        final_null.setDisplayFlag(True)
        final_null.moveToGoodPosition()

        # 12) Layout
        container.layoutChildren()



# pipeline/material_manager.py

def assign_mtlx_materials(assets_dir: str, prefixes: List[str]) -> None:
    """
    In /stage:
      - create a Material Library LOP
      - dive into it and build a USD MaterialX Builder
      - for each prefix, create:
          • a MtlX Standard Surface
          • a Texcoord (Vector2)
          • three MtlX Image nodes (diffuse, MR, normal)
          • a Separate3 node to split metallic/roughness
        wire them up
      - go back up and AssignMaterial each material to the matching prims
    """
    stage = hou.node("/stage") or hou.node("/obj").createNode("lopnet", "stage")
    matlib = stage.createNode("materiallibrary", "mtlx_library")
    matlib.moveToGoodPosition()

    # Create a builder inside the Material Library
    builder = matlib.createNode("usdMaterialXBuilder", "mtlx_builder")
    builder.moveToGoodPosition()

    # Dive inside the builder to create VOPs
    inside = builder

    for prefix in prefixes:
        # 1) Standard Surface shader
        surf = inside.createNode("mtlxstandard_surface", f"mat_{prefix}")
        surf.moveToGoodPosition()

        # 2) UV coords
        tc = inside.createNode("mtlxtexcoord", f"tc_{prefix}")
        tc.parm("signature").set("vector2")        # Vector2 texcoords :contentReference[oaicite:0]{index=0}
        tc.moveToGoodPosition()

        # 3) Diffuse map
        img_diff = inside.createNode("mtlximage", f"diff_{prefix}")
        img_diff.parm("filename").set(
            os.path.join(assets_dir, f"{prefix}_texture_diff.png")
        )
        img_diff.setInput(0, tc)                   # wire texcoord → image :contentReference[oaicite:1]{index=1}
        img_diff.moveToGoodPosition()
        surf.setInput("base_color", img_diff)       # wire image → base_color

        # 4) Metallic/Roughness map (packed in RGB)
        img_mr = inside.createNode("mtlximage", f"mr_{prefix}")
        img_mr.parm("filename").set(
            os.path.join(assets_dir, f"{prefix}_texture_MR.png")
        )
        img_mr.setInput(0, tc)
        img_mr.moveToGoodPosition()

        # split RGB: R→metallic, G→roughness
        sep = inside.createNode("separate3", f"sep_{prefix}")
        sep.setInput(0, img_mr)
        sep.moveToGoodPosition()
        surf.setInput("metallic", sep, 0)           # R channel
        surf.setInput("roughness", sep, 1)         # G channel

        # 5) Normal map
        img_n = inside.createNode("mtlximage", f"norm_{prefix}")
        img_n.parm("filename").set(
            os.path.join(assets_dir, f"{prefix}_texture_normal.png")
        )
        img_n.setInput(0, tc)
        img_n.moveToGoodPosition()

        # hook into the standard‐surface normal input via a MtlX Normal Map node
        normmap = inside.createNode("mtlxnormalmap", f"nmap_{prefix}")
        normmap.setInput(0, img_n)                 # image → normalmap
        normmap.moveToGoodPosition()
        surf.setInput("normal", normmap)           # normalmap → surface normal

    # lay out inside the builder neatly
    inside.layoutChildren()

    # 6) Back in /stage: assign each material
    for prefix in prefixes:
        mat_path = f"{matlib.path()}/mtlx_builder/mat_{prefix}"
        assign = stage.createNode("assignmaterial", f"assign_{prefix}")
        assign.moveToGoodPosition()
        assign.parm("materialpath").set(mat_path)
        # match any prim whose name starts with the prefix
        assign.parm("primpattern").set(f"/root/world/assets/{prefix}*")

    # layout the /stage tree
    stage.layoutChildren()
