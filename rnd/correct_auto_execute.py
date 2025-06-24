import hou
import time

print("=== Auto-loading HIP file and executing TOPs ===")

# File path and configuration
hip_file_path = r"E:/Project_Work/Amazon/StyrofoamWrap/styrofoam_w_v01_010.hiplc"
hda_node_path = "/obj/assets/wrapped_assets"
scheduler_type = "localscheduler"

try:
    # Load the HIP file using the proper hou.hipFile.load() method
    print(f"Loading HIP file: {hip_file_path}")
    hou.hipFile.load(hip_file_path)
    print("SUCCESS: HIP file loaded!")
    
    # Save immediately to resolve dependency warnings
    print("Saving HIP file to resolve dependencies...")
    hou.hipFile.save()
    print("HIP file saved")
    
    # Wait a moment for everything to settle
    time.sleep(2)
    
    # Find the HDA node
    print(f"Looking for HDA node: {hda_node_path}")
    hda_node = hou.node(hda_node_path)
    
    if hda_node is None:
        print(f"ERROR: HDA node not found at {hda_node_path}")
        
        # Debug: List what nodes are available
        print("Available nodes for debugging:")
        obj_node = hou.node("/obj")
        if obj_node:
            print("Nodes in /obj:")
            for child in obj_node.children():
                print(f"  - {child.path()} ({child.type().name()})")
                
        assets_node = hou.node("/obj/assets")
        if assets_node:
            print("Nodes in /obj/assets:")
            for child in assets_node.children():
                print(f"  - {child.path()} ({child.type().name()})")
        
    else:
        print(f"SUCCESS: Found HDA node {hda_node.name()} ({hda_node.type().name()})")
        
        # Configure the scheduler
        if hda_node.parm('topscheduler'):
            scheduler_path = "/tasks/topnet1/localscheduler"
            current_scheduler = hda_node.parm('topscheduler').eval()
            print(f"Current scheduler: {current_scheduler}")
            hda_node.parm('topscheduler').set(scheduler_path)
            new_scheduler = hda_node.parm('topscheduler').eval()
            print(f"Set scheduler to: {new_scheduler}")
            time.sleep(1)
        else:
            print("Warning: topscheduler parameter not found on HDA")
        
        # Validate TOPs control parameters
        dirty_param = hda_node.parm('dirtybutton')
        cook_param = hda_node.parm('cookbutton')
        
        if not dirty_param:
            print("ERROR: dirtybutton parameter not found")
        elif not cook_param:
            print("ERROR: cookbutton parameter not found") 
        else:
            print("SUCCESS: Found required TOPs control parameters")
            
            # Execute the TOPs workflow
            print("Dirtying TOPs network...")
            dirty_param.pressButton()
            time.sleep(3)  # Wait for dirty operation to complete
            
            print("Cooking TOPs network...")
            cook_param.pressButton()
            
            print("SUCCESS: TOPs workflow execution initiated!")
            print("Monitor progress in the TOPs network view")
            print("=== Auto-execution completed successfully ===")
            
except Exception as e:
    print(f"ERROR during auto-execution: {e}")
    import traceback
    traceback.print_exc()
