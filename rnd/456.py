import hou

def auto_confirm_dialog():
    """Try to automatically confirm save dialogs using multiple methods"""
    import time
    
    # Method 1: Try using Houdini's UI functions
    try:
        # Give the dialog time to appear
        time.sleep(1)
        
        # Try to find and confirm any pending dialogs
        # This uses Houdini's internal dialog handling
        if hasattr(hou.ui, 'confirmDialog'):
            # Force confirm any pending dialogs
            print("Attempting to auto-confirm dialogs...")
            
        # Method 2: Try keyboard automation (send Enter key)
        try:
            import win32gui
            import win32con
            
            # Find Houdini window
            def find_houdini_window(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_text = win32gui.GetWindowText(hwnd)
                    if "Houdini" in window_text:
                        windows.append(hwnd)
                return True
            
            windows = []
            win32gui.EnumWindows(find_houdini_window, windows)
            
            if windows:
                houdini_hwnd = windows[0]
                win32gui.SetForegroundWindow(houdini_hwnd)
                time.sleep(0.5)
                
                # Send Enter key to confirm dialog
                import win32api
                win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
                win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
                print("Sent Enter key to confirm dialog")
                
        except ImportError:
            print("win32gui not available for dialog automation")
        except Exception as e:
            print(f"Dialog automation error: {e}")
            
    except Exception as e:
        print(f"Error in auto-confirm: {e}")

def load_and_execute_tops():
    import time
    time.sleep(3)
    
    hip_file_path = r"E:/Project_Work/Amazon/StyrofoamWrap/styrofoam_w_v01_001.hiplc"
    hda_node_path = "/obj/assets/wrapped_assets"
    
    try:
        print(f"Loading HIP file: {hip_file_path}")
        hou.hipFile.load(hip_file_path)
        print("HIP file loaded successfully!")
        
        print("Saving HIP file multiple times to resolve dependencies...")
        hou.hipFile.save()
        time.sleep(1)
        hou.hipFile.save()  # Save twice to be sure
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
        
        print("Attempting to dirty TOPs network...")
        dirty_param.pressButton()
        time.sleep(3)
        
        print("Attempting to cook TOPs network...")
        print("Auto-confirming any save dialogs...")
        
        # Set up a timer to auto-confirm dialogs
        try:
            from PySide2.QtCore import QTimer
            dialog_timer = QTimer()
            dialog_timer.timeout.connect(auto_confirm_dialog)
            dialog_timer.start(500)  # Check every 500ms for dialogs
            
            # Press cook button
            cook_param.pressButton()
            
            # Let the dialog timer run for a few seconds
            time.sleep(5)
            dialog_timer.stop()
            
        except ImportError:
            # Fallback without Qt timer
            cook_param.pressButton()
            time.sleep(1)
            auto_confirm_dialog()
        
        print("TOPs workflow should be running!")
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
        print("Startup timer set - will load HIP file and execute TOPs in 8 seconds")
        print("Attempting to auto-confirm any save dialogs...")
    except ImportError:
        import threading
        threading.Timer(8.0, load_and_execute_tops).start()
else:
    print("UI not available")
