from typing import List, Optional


from pydantic_settings import BaseSettings


def to_list(frames: str):
    """
    Convert a frame range string like "1-240" or "1,3,5-10" to a list of frame specs.
    This can be expanded later if needed.
    """
    return frames




class Settings(BaseSettings):
    assets_dir: str
    hip_path: str
    frame_range: str = "1-240"
    sim_output_driver: str = "simcache"
    hda_path: Optional[str] = None
    render_output_driver: str = "render"
    up_axis: str = "y"
    deadline_command: Optional[str] = None   
    class Config:
        env_prefix = "STYROFOAM_"
        env_file = ".env"

settings = Settings()