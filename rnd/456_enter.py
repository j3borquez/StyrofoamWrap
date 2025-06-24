import hou
import time

def send_enter_key():
    """Send Enter key using ctypes (should be available in Python)"""
    try:
        import ctypes
        
        # Windows virtual key codes
        VK_RETURN = 0x0D
        KEYEVENTF_KEYUP = 0x0002
        
        print("Sending Enter key to confirm dialog...")
        
        # Send Enter key press
        ctypes.windll.user32.keybd_event(VK_RETURN, 0, 0, 0)
        time.sleep(0.1)
        # Send Enter key release
        ctypes.windll.user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
        
        print("Enter key sent successfully")
        return True
        
    except Exception as e:
        print(f"Could not send Enter key: {e}")
        return False

def load_and_execute_tops():
    time.sleep(3)
    
    hip_file_path = r"E:/Project_Work/Amazon/StyrofoamWrap/styrofoam_w_v01_001.hiplc"
    hda_node_path = "/obj/assets/wrapped_assets"
    
    try:
        print(f"Loading HIP file: {hip_file_path}")
        hou.hipFile.load(hip_file_path)
        print("HIP file loaded successfully!")
        
        print("Saving HIP file to resolve dependencies...")
        hou.hipFile.save()
        print("HIP file saved")
        time.sleep(3)
        
        hda_node = hou.node(hda_node_path)
        if hda_node is None:
            print(f"ERROR: HDA node not found")
            return
            
        print(f"SUCCESS: Found HDA node {hda_node.name()}")
        
        # Configure scheduler
        if hda_node.parm('topscheduler'):
            hda_node.parm('topscheduler').set("/tasks/topnet1/localscheduler")
            time.sleep(1)
        
        dirty_param = hda_node.parm('dirtybutton')
        cook_param = hda_node.parm('cookbutton')
        
        if not dirty_param or not cook_param:
            print("ERROR: TOPs control parameters not found")
            return
            
        print("SUCCESS: Found TOPs control parameters")
        
        print("Dirtying TOPs network...")
        dirty_param.pressButton()
        time.sleep(3)
        
        print("Cooking TOPs network...")
        print("Will automatically press Enter if save dialog appears...")
        
        # Press cook button
        cook_param.pressButton()
        
        # Wait a moment for potential dialog to appear, then send Enter
        time.sleep(1.5)
        send_enter_key()
        time.sleep(0.5)
        send_enter_key()  # Send twice to be extra sure
        
        print("TOPs workflow should now be running!")
        print("Check the TOPs network view for progress")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if hou.isUIAvailable():
    try:
        from PySide2.QtCore import QTimer
        timer = QTimer()
        timer.timeout.connect(load_and_execute_tops)
        timer.setSingleShot(True)
        timer.start(8000)
        print("Startup timer set - will auto-press Enter for dialogs")
    except ImportError:
        import threading
        threading.Timer(8.0, load_and_execute_tops).start()
        print("Using threading timer - will auto-press Enter for dialogs")
else:
    print("UI not available")
