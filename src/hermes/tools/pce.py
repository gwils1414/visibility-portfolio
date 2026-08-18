#--PCE in Docker for visualization generation--#
#if this whole project gets wrapped into a docker container, then this just becomes a subproces#
import subprocess
import subprocess
import tempfile
import os
from typing import Literal
from pydantic import BaseModel
from config.paths import PROJ_ROOT

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)



class ApprovalSchema(BaseModel):
    approval: Literal["y", "n"]

class PCE_Validation():
    def __init__(self):
        # Light pre-filter only. The real boundary is the Docker container
        # (no network, non-root, ro mount, capped mem/cpu/pids). These are
        # things legit pandas/numpy/plotly viz code never needs.
        self.unapproved_words = ["subprocess", "__import__", "pip install", "socket", "shutil.rmtree"]

    @log
    def check_code(self,code):
        '''
        The check code function evaluates if the code provided the sandbox meets the criteria.

        i.e doesnt contain pip install os
        is not trying to operate outside if its desingated scope.
        and so on
        '''
        body_flag = [word for word in self.unapproved_words if word.lower() in code.lower()] #check if body contains unapproved words
        if body_flag: 
            return "Fail" 
        else:
            return "Pass"


#TODO , add runcontext , if we start passing data or files
@log
async def execute_python_in_sandbox(code: str):
    """
    Writes code to a temp file, runs it inside the
    Docker sandbox, returns stdout or error.
    Always Write the final result to output/file.{file_type}

    parameters:
    - code: the code that the agent wants to execute in the sandbox. This is passed in as a string.
    """
    # Write the code to a temp file in the sandbox folder
    print("Running execute_python_in_sandbox")
    script_path = PROJ_ROOT / "hermes/sandbox/agent_script.py"


    validation = PCE_Validation()

    #approval = validation.check_approval(code, approval)

    #if approval.approval == "n":
        #return "User rejected code execution. Stopping."

    code_check = validation.check_code(code)
    if code_check == "Fail":
        return "Tool execution failed due to code check" 
    
    else:
        with open(script_path, "w") as f:
            f.write(code)

        try:
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "--network", "none",
                    "--memory", "512m",
                    "--cpus", "1",
                    "--pids-limit", "128",                    # fork-bomb guard. limits processes
                    "--cap-drop", "ALL",                      # drop all linux capabilities
                    "--security-opt", "no-new-privileges",    # block privilege escalation
                    "--volume", f"{PROJ_ROOT / 'hermes/sandbox'}:/sandbox:ro",#Mount: path on host / path inside the container
                    "--volume", f"{PROJ_ROOT / 'hermes/sandbox/output'}:/sandbox/output",# Mount path on host / path inside the container
                    "python-sandbox", #image
                    "python", "/sandbox/agent_script.py" #script running inside container
                ],
                capture_output=True, #grabs stdout and stderr
                text=True, #return the output as a string
                timeout=30  # Kill if it runs longer than 30 seconds
            )

            if result.returncode == 0:#normal output channel, anything printed goes to stdout
                return result.stdout or "Code executed successfully, no output returned"
            else:
                return f"Error:\n{result.stderr}" 
        #stderror is where the program sends error messages

        except subprocess.TimeoutExpired:
            return "Error: Code execution timed out (30s limit)"
        except Exception as e:
            return f"Error: {str(e)}"
    