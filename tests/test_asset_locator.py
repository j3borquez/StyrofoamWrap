import pytest
from pipeline.asset_locator import FilesystemLocator


def test_find_usds(tmp_path):
    # Setup: create some USD and non-USD files
    usd1 = tmp_path / "a.usd"
    usd1.write_text("")
    usd2 = tmp_path / "b.usd"
    usd2.write_text("")
    non_usd = tmp_path / "readme.md"
    non_usd.write_text("This is not a USD file.")

    # Debug: list directory contents
    all_files = sorted([str(p.name) for p in tmp_path.iterdir()])
    print(f"[DEBUG] Directory contents: {all_files}")

    # Exercise
    locator = FilesystemLocator()
    result = locator.find_usds(str(tmp_path))

    # Debug: print found USDs
    print(f"[DEBUG] Found USD files: {result}")

    # Verify: only USD files, in sorted order
    expected = [str(usd1), str(usd2)]
    assert result == expected, f"Expected {expected}, got {result}"


# Optionally, test error handling

def test_invalid_directory():
    locator = FilesystemLocator()
    # Debug: indicate start of invalid directory test
    print("[DEBUG] Testing invalid directory path")
    with pytest.raises(NotADirectoryError):
        locator.find_usds("nonexistent_folder")
    # Debug: confirm exception was raised
    print("[DEBUG] NotADirectoryError successfully raised for nonexistent_folder")
