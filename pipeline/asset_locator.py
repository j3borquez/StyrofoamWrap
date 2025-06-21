from abc import ABC, abstractmethod
from typing import List
import os


class AssetLocator(ABC):
    """
    Interface for locating USD assets in a given directory.
    """
    @abstractmethod
    def find_usds(self, assets_dir: str) -> List[str]:
        """
        Scan the provided assets_dir and return a list of absolute paths to .usd files.
        """
        ...


class FilesystemLocator(AssetLocator):
    """
    Filesystem-based implementation of AssetLocator.
    """
    def find_usds(self, assets_dir: str) -> List[str]:
        # Ensure the directory exists
        if not os.path.isdir(assets_dir):
            raise NotADirectoryError(f"{assets_dir!r} is not a valid directory")

        # Collect and return sorted USD file paths
        usd_files = [
            os.path.join(assets_dir, fn)
            for fn in sorted(os.listdir(assets_dir))
            if fn.lower().endswith(".usd")
        ]
        return usd_files
