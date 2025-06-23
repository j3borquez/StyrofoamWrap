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
    
    def submit_tops_workflow(self, hip_path: str, hda_node_path: str, name: Optional[str] = None, depends_on: Optional[str] = None) -> str:
        """
        Submit a TOPs workflow job that will dirty and cook the TOPs network in the specified HDA node.
        
        Args:
            hip_path: Path to the Houdini .hip file
            hda_node_path: Path to the HDA node containing the TOPs network (e.g., "/obj/assets/wrapped_assets")
            name: Optional custom job name
            depends_on: Optional job ID this job should depend on
        """
        job_name = name or f"TOPs_{os.path.basename(hip_path)}"
        
        # Job info
        ji = [
            "Plugin=Houdini",
            f"Name={job_name}",
            "Frames=1",  # TOPs workflows typically run on a single frame
            "Comment=Automated TOPs workflow execution",
        ]
        
        # Add dependency if specified
        if depends_on:
            ji.append(f"DependsOnJobID={depends_on}")
        
        # Plugin info - we'll use a Python script to execute the TOPs workflow
        # This script will dirty and cook the TOPs network
        script_commands = [
            f"import hou",
            f"hou.hipFile.load('{hip_path}')",
            f"hda_node = hou.node('{hda_node_path}')",
            f"if hda_node is None:",
            f"    raise RuntimeError('HDA node not found: {hda_node_path}')",
            f"print('Dirtying TOPs network...')",
            f"hda_node.parm('dirtybutton').pressButton()",
            f"print('Cooking TOPs network...')",
            f"hda_node.parm('cookbutton').pressButton()",
            f"print('TOPs workflow execution completed')"
        ]
        
        # Join script commands with semicolons for single-line execution
        python_script = "; ".join(script_commands)
        
        pi = [
            f"HoudiniHipFile={hip_path}",
            f"HoudiniIgnoreInputs=True",
            f"HoudiniPythonScript={python_script}",
        ]
        
        return self._submit(ji, pi)
    
    def submit_tops_with_scheduler(self, hip_path: str, hda_node_path: str, scheduler_type: str = "deadline", 
                                 name: Optional[str] = None, depends_on: Optional[str] = None) -> str:
        """
        Submit a TOPs workflow job with a specific scheduler (like Deadline scheduler).
        
        Args:
            hip_path: Path to the Houdini .hip file
            hda_node_path: Path to the HDA node containing the TOPs network
            scheduler_type: Type of scheduler to use ("deadline", "localscheduler", etc.)
            name: Optional custom job name
            depends_on: Optional job ID this job should depend on
        """
        job_name = name or f"TOPs_{scheduler_type}_{os.path.basename(hip_path)}"
        
        ji = [
            "Plugin=Houdini",
            f"Name={job_name}",
            "Frames=1",
            f"Comment=TOPs workflow with {scheduler_type} scheduler",
        ]
        
        if depends_on:
            ji.append(f"DependsOnJobID={depends_on}")
        
        # More sophisticated script that can configure the scheduler
        script_commands = [
            f"import hou",
            f"hou.hipFile.load('{hip_path}')",
            f"hda_node = hou.node('{hda_node_path}')",
            f"if hda_node is None:",
            f"    raise RuntimeError('HDA node not found: {hda_node_path}')",
            f"# Set the scheduler type",
            f"if hda_node.parm('topscheduler'):",
            f"    hda_node.parm('topscheduler').set('{scheduler_type}')",
            f"print('Set scheduler to: {scheduler_type}')",
            f"print('Dirtying TOPs network...')",
            f"hda_node.parm('dirtybutton').pressButton()",
            f"print('Cooking TOPs network...')",
            f"hda_node.parm('cookbutton').pressButton()",
            f"print('TOPs workflow execution completed with {scheduler_type} scheduler')"
        ]
        
        python_script = "; ".join(script_commands)
        
        pi = [
            f"HoudiniHipFile={hip_path}",
            f"HoudiniIgnoreInputs=True", 
            f"HoudiniPythonScript={python_script}",
        ]
        
        return self._submit(ji, pi)