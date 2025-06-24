# tests/test_asset_locator.py

import pytest
import os
import tempfile
from pathlib import Path

from pipeline.asset_locator import FilesystemLocator, AssetLocator


def test_filesystem_locator_creation():
    """Test that FilesystemLocator can be created."""
    locator = FilesystemLocator()
    assert locator is not None
    assert isinstance(locator, AssetLocator)


def test_filesystem_locator_nonexistent_directory():
    """Test that FilesystemLocator raises error for non-existent directory."""
    locator = FilesystemLocator()
    
    with pytest.raises(NotADirectoryError):
        locator.find_usds("/nonexistent/directory")


def test_filesystem_locator_empty_directory():
    """Test FilesystemLocator with empty directory."""
    locator = FilesystemLocator()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        result = locator.find_usds(temp_dir)
        assert result == []


def test_filesystem_locator_with_usd_files():
    """Test FilesystemLocator with USD files."""
    locator = FilesystemLocator()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some test files
        test_files = [
            "chair_base.usd",
            "desk_A3DCZYC5E6B3MT80.usd", 
            "lamp_B000BRBYJ8.usd",
            "texture.png",  # Non-USD file, should be ignored
            "README.txt",   # Non-USD file, should be ignored
        ]
        
        for filename in test_files:
            (Path(temp_dir) / filename).touch()
        
        result = locator.find_usds(temp_dir)
        
        # Should only return USD files
        expected_usd_files = [
            os.path.join(temp_dir, "chair_base.usd"),
            os.path.join(temp_dir, "desk_A3DCZYC5E6B3MT80.usd"),
            os.path.join(temp_dir, "lamp_B000BRBYJ8.usd"),
        ]
        
        assert len(result) == 3
        assert set(result) == set(expected_usd_files)
        
        # Verify they're sorted
        assert result == sorted(expected_usd_files)


def test_filesystem_locator_case_insensitive():
    """Test that FilesystemLocator handles different USD file extensions."""
    locator = FilesystemLocator()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create files with different case extensions
        test_files = [
            "file1.usd",
            "file2.USD", 
            "file3.Usd",
            "file4.usD",
        ]
        
        for filename in test_files:
            (Path(temp_dir) / filename).touch()
        
        result = locator.find_usds(temp_dir)
        
        # Should find all USD files regardless of case
        assert len(result) == 4
        
        # Check that all files are included
        result_basenames = [os.path.basename(f) for f in result]
        assert set(result_basenames) == set(test_files)


def test_filesystem_locator_with_subdirectories():
    """Test that FilesystemLocator only finds files in the top directory."""
    locator = FilesystemLocator()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create files in main directory
        (Path(temp_dir) / "main_file.usd").touch()
        
        # Create subdirectory with USD file
        sub_dir = Path(temp_dir) / "subdir"
        sub_dir.mkdir()
        (sub_dir / "sub_file.usd").touch()
        
        result = locator.find_usds(temp_dir)
        
        # Should only find files in the main directory, not subdirectories
        assert len(result) == 1
        assert os.path.basename(result[0]) == "main_file.usd"


def test_filesystem_locator_returns_absolute_paths():
    """Test that FilesystemLocator returns absolute paths."""
    locator = FilesystemLocator()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test file
        (Path(temp_dir) / "test.usd").touch()
        
        result = locator.find_usds(temp_dir)
        
        assert len(result) == 1
        assert os.path.isabs(result[0])
        assert result[0] == os.path.join(temp_dir, "test.usd")


def test_filesystem_locator_with_modified_files():
    """Test FilesystemLocator with modified USD files (should include them)."""
    locator = FilesystemLocator()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create original and modified files
        test_files = [
            "chair_base.usd",
            "modified_chair_base.usd",
            "desk_A3DCZYC5E6B3MT80.usd",
            "modified_desk_A3DCZYC5E6B3MT80.usd",
        ]
        
        for filename in test_files:
            (Path(temp_dir) / filename).touch()
        
        result = locator.find_usds(temp_dir)
        
        # Should find all USD files, including modified ones
        assert len(result) == 4
        
        result_basenames = [os.path.basename(f) for f in result]
        assert set(result_basenames) == set(test_files)


def test_abstract_asset_locator():
    """Test that AssetLocator is properly abstract."""
    # Should not be able to instantiate AssetLocator directly
    with pytest.raises(TypeError):
        AssetLocator()


def test_filesystem_locator_interface_compliance():
    """Test that FilesystemLocator implements the AssetLocator interface."""
    locator = FilesystemLocator()
    
    # Should have the find_usds method
    assert hasattr(locator, 'find_usds')
    assert callable(getattr(locator, 'find_usds'))
    
    # Should be an instance of AssetLocator
    assert isinstance(locator, AssetLocator)