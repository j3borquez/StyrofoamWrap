# tests/test_load.py

import pytest
import os
from unittest.mock import patch, MagicMock

def test_hou_module_import():
    """Test that hou module can be imported."""
    try:
        import hou
        print("✓ hou module imported successfully")
        
        # Check if we're in a full Houdini session
        if hasattr(hou, 'hipFile'):
            try:
                current_file = hou.hipFile.path()
                print(f"Current HIP file: {current_file}")
            except:
                print("hipFile.path() failed - might be in batch mode")
        else:
            print("Running in limited Houdini environment (hython without full session)")
            
    except ImportError as e:
        pytest.fail(f"Could not import hou module: {e}")


def test_hip_file_loading():
    """Test HIP file operations if available."""
    try:
        import hou
        
        # Check if hipFile is available (full Houdini session)
        if hasattr(hou, 'hipFile'):
            try:
                print("Current file:", hou.hipFile.path())
                
                # Test creating a new scene if possible
                hou.hipFile.clear()
                print("✓ HIP file cleared successfully")
                
            except Exception as e:
                print(f"HIP file operations failed (expected in batch mode): {e}")
                # This is expected in hython batch mode
                pass
        else:
            print("hipFile not available - this is expected in hython without GUI")
            # Test that we can still import the module
            assert hou is not None
            
    except Exception as e:
        pytest.fail(f"Unexpected error during HIP file operations: {e}")


@patch('hou.hipFile')
def test_hip_file_operations_mocked(mock_hip_file):
    """Test HIP file operations with mocked hou module."""
    import hou
    
    # Configure the mock
    mock_hip_file.path.return_value = "/mock/path.hiplc"
    mock_hip_file.load = MagicMock()
    mock_hip_file.save = MagicMock()
    mock_hip_file.clear = MagicMock()
    
    # Test operations
    current_path = hou.hipFile.path()
    assert current_path == "/mock/path.hiplc"
    
    hou.hipFile.clear()
    mock_hip_file.clear.assert_called_once()
    
    hou.hipFile.load("/test/path.hiplc")
    mock_hip_file.load.assert_called_once_with("/test/path.hiplc")


def test_pipeline_imports():
    """Test that our pipeline modules can be imported."""
    try:
        from pipeline import config
        from pipeline import asset_locator
        from pipeline import hip_manager
        from pipeline import submit_config_generator
        
        print("✓ All core pipeline modules imported successfully")
        
        # Test optional imports
        try:
            from pipeline import solaris_material_manager
            print("✓ Solaris material manager imported")
        except ImportError as e:
            print(f"Warning: Could not import solaris_material_manager: {e}")
            
    except ImportError as e:
        pytest.fail(f"Could not import required pipeline modules: {e}")


def test_houdini_environment():
    """Test the Houdini environment setup."""
    import os
    
    # Check if HFS is set
    hfs = os.getenv('HFS')
    if hfs:
        print(f"✓ HFS environment variable: {hfs}")
    else:
        print("⚠ Warning: HFS environment variable not set")
    
    # Try to import hou
    try:
        import hou
        print("✓ hou module available")
        
        # Check what's available in this hou session
        available_attrs = [attr for attr in dir(hou) if not attr.startswith('_')]
        print(f"Available hou attributes: {len(available_attrs)}")
        
        # Key attributes we need for our pipeline
        key_attrs = ['hipFile', 'node', 'hscript', 'Vector3', 'Matrix4', 'hda']
        missing_attrs = []
        
        for attr in key_attrs:
            has_attr = hasattr(hou, attr)
            status = "✓" if has_attr else "✗"
            print(f"  {status} hou.{attr}")
            if not has_attr:
                missing_attrs.append(attr)
        
        # Check session type
        try:
            is_ui = hou.isUIAvailable() if hasattr(hou, 'isUIAvailable') else False
            session_type = "GUI" if is_ui else "Batch/Command-line"
            print(f"✓ Session type: {session_type}")
        except:
            print("? Session type: Unknown")
            
        # For pipeline functionality, we mainly need node, hscript, and hda
        critical_attrs = ['node', 'hscript', 'hda']
        missing_critical = [attr for attr in critical_attrs if not hasattr(hou, attr)]
        
        if missing_critical:
            pytest.fail(f"Critical hou attributes missing: {missing_critical}")
            
    except ImportError:
        pytest.fail("hou module not available - check Houdini installation")


def test_config_loading():
    """Test that pipeline configuration can be loaded."""
    try:
        from pipeline.config import settings
        
        print("✓ Pipeline settings loaded")
        print(f"  Assets directory: {settings.assets_dir}")
        print(f"  HIP path: {settings.hip_path}")
        print(f"  Up axis: {settings.up_axis}")
        print(f"  Frame range: {settings.frame_range}")
        
        # Test that required settings exist
        required_settings = ['assets_dir', 'hip_path', 'up_axis']
        for setting in required_settings:
            assert hasattr(settings, setting), f"Missing required setting: {setting}"
            
    except Exception as e:
        pytest.fail(f"Could not load pipeline configuration: {e}")


def test_asset_locator_functionality():
    """Test asset locator functionality."""
    try:
        from pipeline.asset_locator import FilesystemLocator
        
        locator = FilesystemLocator()
        print("✓ Asset locator created")
        
        # Test with a non-existent directory (should raise NotADirectoryError)
        with pytest.raises(NotADirectoryError):
            locator.find_usds("/nonexistent/directory")
            
        print("✓ Asset locator error handling works")
        
    except Exception as e:
        pytest.fail(f"Asset locator test failed: {e}")


def test_hip_manager_functionality():
    """Test hip manager basic functionality."""
    try:
        from pipeline.hip_manager import HoudiniHipManager, extract_base_identifier_from_filename
        
        hip_manager = HoudiniHipManager()
        print("✓ Hip manager created")
        
        # Test filename parsing
        test_files = [
            "chair_base.usd",
            "desk_A3DCZYC5E6B3MT80.usd",
            "nan_B000BRBYJ8.usd"
        ]
        
        for filename in test_files:
            base_id = extract_base_identifier_from_filename(filename)
            print(f"  {filename} -> {base_id}")
            assert base_id, f"Failed to extract base ID from {filename}"
            
        print("✓ Filename parsing works")
        
    except Exception as e:
        pytest.fail(f"Hip manager test failed: {e}")


def test_submit_config_generator():
    """Test submit config generator functionality."""
    try:
        from pipeline.submit_config_generator import create_submit_config_script, get_default_submit_config_path
        
        # Test getting default path
        default_path = get_default_submit_config_path()
        assert default_path.endswith("submit_config.py"), f"Unexpected default path: {default_path}"
        print(f"✓ Default submit config path: {default_path}")
        
        # Test script creation (with a temporary file)
        import tempfile
        import os
        
        # Create a temporary file manually to avoid Windows permission issues
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"test_submit_config_{os.getpid()}.py")
        
        try:
            create_submit_config_script(
                hip_file_path="/test/path.hiplc",
                scheduler_type="localscheduler",
                output_path=temp_file
            )
            print("✓ Submit config script created successfully")
            
            # Verify the file was created and has content
            with open(temp_file, 'r') as f:
                content = f.read()
                assert "load_and_execute_tops" in content, "Script missing main function"
                assert "/test/path.hiplc" in content, "HIP file path not in script"
                assert "localscheduler" in content, "Scheduler type not in script"
                
            print("✓ Submit config script content validated")
            
        finally:
            # Clean up - use try/except to handle Windows permission issues
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except (PermissionError, OSError):
                # On Windows, sometimes files are locked briefly
                import time
                time.sleep(0.1)
                try:
                    os.unlink(temp_file)
                except (PermissionError, OSError):
                    pass  # Give up if we still can't delete it
                    
    except Exception as e:
        pytest.fail(f"Submit config generator test failed: {e}")


def test_complete_pipeline_integration():
    """Test that all pipeline components can work together."""
    try:
        # Import all required modules
        from pipeline.config import settings
        from pipeline.asset_locator import FilesystemLocator
        from pipeline.hip_manager import HoudiniHipManager
        from pipeline.submit_config_generator import get_default_submit_config_path
        
        # Test basic integration
        locator = FilesystemLocator()
        hip_manager = HoudiniHipManager()
        config_path = get_default_submit_config_path()
        
        print("✓ All pipeline components integrated successfully")
        print(f"  Config assets dir: {settings.assets_dir}")
        print(f"  Default submit config: {config_path}")
        
    except Exception as e:
        pytest.fail(f"Pipeline integration test failed: {e}")