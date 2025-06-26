
import hou
import time

def load_and_execute_tops():
    """Load HIP file and execute TOPs workflow."""
    time.sleep(3)  # Wait for GUI to be ready
    
    hip_file_path = r"E:/Project_Work/Amazon/StyrofoamWrap/styrofoam_w_v01_007.hiplc"
    hda_node_path = "/obj/assets/wrapped_assets"
    scheduler_type = "deadline"
    
    try:
        print(f"Loading HIP file: {hip_file_path}")
        hou.hipFile.load(hip_file_path)
        print("SUCCESS: HIP file loaded!")
        
        print("Saving HIP file to resolve dependencies...")
        hou.hipFile.save()
        print("HIP file saved")
        time.sleep(3)
        
        hda_node = hou.node(hda_node_path)
        if hda_node is None:
            print(f"ERROR: HDA node not found at {hda_node_path}")
            
            # Debug: List available nodes
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
            return
            
        print(f"SUCCESS: Found HDA node {hda_node.name()} ({hda_node.type().name()})")
        
        # Configure scheduler
        if hda_node.parm('topscheduler'):
            if scheduler_type == "deadline":
                scheduler_path = "deadlinescheduler1"
            else:
                scheduler_path = "localscheduler"
                
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
            return
        if not cook_param:
            print("ERROR: cookbutton parameter not found") 
            return
            
        print("SUCCESS: Found required TOPs control parameters")
        
        # Execute the TOPs workflow
        print("Dirtying TOPs network...")
        dirty_param.pressButton()
        time.sleep(3)
        
        print("Cooking TOPs network...")
        print("NOTE: Please click 'Save and Continue' if a dialog appears")
        cook_param.pressButton()
        
        print("SUCCESS: TOPs workflow execution initiated!")
        print("Monitor progress in the TOPs network view")
        
    except Exception as e:
        print(f"ERROR during auto-execution: {e}")
        import traceback
        traceback.print_exc()

# Set up timer for delayed execution after UI is ready
if hou.isUIAvailable():
    try:
        from PySide2.QtCore import QTimer
        timer = QTimer()
        timer.timeout.connect(load_and_execute_tops)
        timer.setSingleShot(True)
        timer.start(8000)  # 8 second delay
        print("Startup timer set - will load HIP file and execute TOPs in 8 seconds")
        print("NOTE: You may need to click 'Save and Continue' if prompted")
    except ImportError:
        print("PySide2 not available, trying threading approach")
        import threading
        threading.Timer(8.0, load_and_execute_tops).start()
        print("Using threading timer - will load HIP file and execute TOPs in 8 seconds")
        print("NOTE: You may need to click 'Save and Continue' if prompted")
else:
    print("UI not available")
