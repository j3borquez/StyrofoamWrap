
import hou
import time

def execute_tops_after_load():
    print("Waiting for Houdini GUI to fully initialize...")
    time.sleep(10)  # Wait for GUI to be ready
    
    hda_node_path = "/obj/assets/wrapped_assets"
    scheduler_type = "localscheduler"
    
    print(f"Executing TOPs workflow...")
    print(f"HDA node path: {hda_node_path}")
    print(f"Scheduler type: {scheduler_type}")
    
    hda_node = hou.node(hda_node_path)
    if hda_node is None:
        print(f"Error: HDA node not found: {hda_node_path}")
        return False
        
    print(f"HDA node found: {hda_node.name()} ({hda_node.type().name()})")
    
    # Set scheduler if parameter exists
    if hda_node.parm('topscheduler'):
        if scheduler_type == "deadline":
            scheduler_path = "/tasks/topnet1/deadlinescheduler"
        else:
            scheduler_path = "/tasks/topnet1/localscheduler"
            
        current_scheduler = hda_node.parm('topscheduler').eval()
        print(f"Current scheduler: {current_scheduler}")
        hda_node.parm('topscheduler').set(scheduler_path)
        new_scheduler = hda_node.parm('topscheduler').eval()
        print(f"Set scheduler to: {new_scheduler}")
        time.sleep(1)
    else:
        print("Warning: topscheduler parameter not found")
    
    # Validate required parameters
    if not hda_node.parm('dirtybutton'):
        print("Error: dirtybutton parameter not found on HDA")
        return False
    if not hda_node.parm('cookbutton'):
        print("Error: cookbutton parameter not found on HDA")
        return False
        
    print("Found required TOPs control parameters")
    
    # Execute TOPs workflow
    print("Dirtying TOPs network...")
    hda_node.parm('dirtybutton').pressButton()
    time.sleep(3)  # Wait for dirty operation
    
    print("Cooking TOPs network...")
    hda_node.parm('cookbutton').pressButton()
    print("TOPs workflow execution initiated successfully!")
    
    # Give it a moment to start
    time.sleep(2)
    print("TOPs workflow is now running - monitor progress in the network view")
    
    return True

# Schedule the execution to run after GUI loads
hou.session.startup_scripts = getattr(hou.session, 'startup_scripts', [])
hou.session.startup_scripts.append(execute_tops_after_load)

# Execute after a delay to ensure everything is loaded
import threading
threading.Timer(15.0, execute_tops_after_load).start()
