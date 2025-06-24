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
        # This script will load the file, wait for initialization, then execute TOPs
        script_commands = [
            f"import hou",
            f"import time",
            f"print('Loading HIP file: {hip_path}')",
            f"hou.hipFile.load('{hip_path}')",
            f"print('Waiting for scene to initialize...')",
            f"time.sleep(5)",  # Increased wait time for initialization
            f"hda_node = hou.node('{hda_node_path}')",
            f"if hda_node is None:",
            f"    raise RuntimeError('HDA node not found: {hda_node_path}')",
            f"print(f'HDA node found: {{hda_node.name()}} ({{hda_node.type().name()}})')",
            f"# Validate required parameters exist",
            f"if not hda_node.parm('dirtybutton'):",
            f"    raise RuntimeError('dirtybutton parameter not found on HDA')",
            f"if not hda_node.parm('cookbutton'):",
            f"    raise RuntimeError('cookbutton parameter not found on HDA')",
            f"print('Found required TOPs control parameters')",
            f"print('Dirtying TOPs network...')",
            f"hda_node.parm('dirtybutton').pressButton()",
            f"time.sleep(3)",  # Wait for dirty operation to complete
            f"print('Cooking TOPs network...')",
            f"hda_node.parm('cookbutton').pressButton()",
            f"print('TOPs workflow execution initiated successfully')",
            f"time.sleep(2)",
            f"print('TOPs workflow is now running - monitor progress in Houdini')"
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
        
        # Build the scheduler path based on the type
        if scheduler_type == "deadline":
            scheduler_path = "/tasks/topnet1/deadlinescheduler"
        elif scheduler_type == "localscheduler":
            scheduler_path = "/tasks/topnet1/localscheduler"
        else:
            # For custom scheduler types, assume they follow the pattern
            scheduler_path = f"/tasks/topnet1/{scheduler_type}"
        
        # More sophisticated script that can configure the scheduler
        script_commands = [
            f"import hou",
            f"import time",
            f"print('Loading HIP file: {hip_path}')",
            f"hou.hipFile.load('{hip_path}')",
            f"print('Waiting for scene to initialize...')",
            f"time.sleep(5)",  # Increased wait time
            f"hda_node = hou.node('{hda_node_path}')",
            f"if hda_node is None:",
            f"    raise RuntimeError('HDA node not found: {hda_node_path}')",
            f"print(f'HDA node found: {{hda_node.name()}} ({{hda_node.type().name()}})')",
            f"# Configure the scheduler if topscheduler parameter exists",
            f"if hda_node.parm('topscheduler'):",
            f"    current_scheduler = hda_node.parm('topscheduler').eval()",
            f"    print(f'Current scheduler: {{current_scheduler}}')",
            f"    hda_node.parm('topscheduler').set('{scheduler_path}')",
            f"    new_scheduler = hda_node.parm('topscheduler').eval()",
            f"    print(f'Set scheduler to: {{new_scheduler}}')",
            f"    time.sleep(2)",  # Allow parameter change to take effect
            f"else:",
            f"    print('Warning: topscheduler parameter not found, using default scheduler')",
            f"# Validate required parameters exist",
            f"if not hda_node.parm('dirtybutton'):",
            f"    raise RuntimeError('dirtybutton parameter not found on HDA')",
            f"if not hda_node.parm('cookbutton'):",
            f"    raise RuntimeError('cookbutton parameter not found on HDA')",
            f"print('Found required TOPs control parameters')",
            f"print('Dirtying TOPs network...')",
            f"hda_node.parm('dirtybutton').pressButton()",
            f"time.sleep(3)",  # Wait for dirty operation
            f"print('Cooking TOPs network...')",
            f"hda_node.parm('cookbutton').pressButton()",
            f"print(f'TOPs workflow execution initiated with {{scheduler_type}} scheduler')",
            f"time.sleep(2)",
            f"print('TOPs workflow is now running - check scheduler for task distribution')"
        ]
        
        python_script = "; ".join(script_commands)
        
        pi = [
            f"HoudiniHipFile={hip_path}",
            f"HoudiniIgnoreInputs=True", 
            f"HoudiniPythonScript={python_script}",
        ]
        
        return self._submit(ji, pi)
    
    def submit_tops_local_execution(self, hip_path: str, hda_node_path: str, name: Optional[str] = None) -> str:
        """
        Submit a job that executes TOPs workflow locally (non-distributed).
        This is useful for testing or when you want all work done on a single machine.
        
        Args:
            hip_path: Path to the Houdini .hip file
            hda_node_path: Path to the HDA node containing the TOPs network
            name: Optional custom job name
        """
        return self.submit_tops_with_scheduler(
            hip_path=hip_path,
            hda_node_path=hda_node_path,
            scheduler_type="localscheduler",
            name=name or f"TOPs_Local_{os.path.basename(hip_path)}"
        )
    
    def get_tops_status(self, hip_path: str, hda_node_path: str, name: Optional[str] = None) -> str:
        """
        Submit a job to check the status of a TOPs network without cooking it.
        
        Args:
            hip_path: Path to the Houdini .hip file
            hda_node_path: Path to the HDA node containing the TOPs network
            name: Optional custom job name
        """
        job_name = name or f"TOPs_Status_{os.path.basename(hip_path)}"
        
        ji = [
            "Plugin=Houdini",
            f"Name={job_name}",
            "Frames=1",
            "Comment=TOPs workflow status check",
        ]
        
        # Script to check TOPs status
        script_commands = [
            f"import hou",
            f"import time",
            f"print('Loading HIP file: {hip_path}')",
            f"hou.hipFile.load('{hip_path}')",
            f"time.sleep(3)",
            f"hda_node = hou.node('{hda_node_path}')",
            f"if hda_node is None:",
            f"    raise RuntimeError('HDA node not found: {hda_node_path}')",
            f"print(f'HDA node found: {{hda_node.name()}}')",
            f"# Check if TOPs network exists and get status",
            f"if hda_node.parm('topscheduler'):",
            f"    scheduler = hda_node.parm('topscheduler').eval()",
            f"    print(f'Current TOPs scheduler: {{scheduler}}')",
            f"else:",
            f"    print('No topscheduler parameter found')",
            f"# Check other relevant parameters",
            f"for parm_name in ['cookbutton', 'dirtybutton', 'cancelbutton']:",
            f"    if hda_node.parm(parm_name):",
            f"        print(f'Parameter {{parm_name}} is available')",
            f"    else:",
            f"        print(f'Parameter {{parm_name}} is NOT available')",
            f"print('TOPs status check completed')"
        ]
        
        python_script = "; ".join(script_commands)
        
        pi = [
            f"HoudiniHipFile={hip_path}",
            f"HoudiniIgnoreInputs=True",
            f"HoudiniPythonScript={python_script}",
        ]
        
        return self._submit(ji, pi)