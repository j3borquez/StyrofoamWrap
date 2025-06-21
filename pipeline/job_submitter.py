# pipeline/job_submitter.py

import os
import shutil
import subprocess
import tempfile
from typing import Optional

class DeadlineSubmissionError(Exception):
    pass

class DeadlineSubmitter:
    def __init__(self, deadline_command: Optional[str] = None):
        # 1) Use explicit setting if given
        if deadline_command and os.path.isfile(deadline_command):
            self.deadline_command = deadline_command
        else:
            # 2) Try finding on your PATH
            found = shutil.which("deadlinecommand") or shutil.which("deadlinecommand.exe")
            if found:
                self.deadline_command = found
            else:
                raise FileNotFoundError(
                    "Cannot find 'deadlinecommand'.\n"
                    "Either install the Deadline Client or set DEADLINE_COMMAND to the full path."
                )

    def _submit(self, job_info: list[str], plugin_info: list[str]) -> str:
        ji = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
        ji.write("\n".join(job_info)); ji.close()
        pi = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
        pi.write("\n".join(plugin_info)); pi.close()

        result = subprocess.run(
            [self.deadline_command, ji.name, pi.name],
            capture_output=True, text=True
        )
        os.remove(ji.name); os.remove(pi.name)

        if result.returncode != 0:
            raise DeadlineSubmissionError(result.stderr.strip())
        return result.stdout.strip()

    def submit_simulation(self, hip_path: str, frame_range: str, output_driver: str, name: Optional[str]=None) -> str:
        job_name = name or f"Sim_{os.path.basename(hip_path)}"
        ji = [
            "Plugin=Houdini",
            f"Name={job_name}",
            f"Frames={frame_range}",
            "Comment=Automated simulation",
        ]
        pi = [
            f"HoudiniHipFile={hip_path}",
            f"HoudiniOutputDriver={output_driver}",
        ]
        return self._submit(ji, pi)

    def submit_render(self, hip_path: str, frame_range: str, output_driver: str, depends_on: str, name: Optional[str]=None) -> str:
        job_name = name or f"Render_{os.path.basename(hip_path)}"
        ji = [
            "Plugin=Houdini",
            f"Name={job_name}",
            f"Frames={frame_range}",
            f"DependsOnJobID={depends_on}",
            "Comment=Automated render",
        ]
        pi = [
            f"HoudiniHipFile={hip_path}",
            f"HoudiniOutputDriver={output_driver}",
        ]
        return self._submit(ji, pi)
