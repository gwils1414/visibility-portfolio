import subprocess
import questionary
from rich.console import Console
import subprocess
from pathlib import Path
import os
from typing import Literal
import questionary
from rich.console import Console

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)

console = Console()
from rich.panel import Panel
from rich.syntax import Syntax
import json
from hermes.models.deps import Settings
deps = Settings()
#okay this is going to be our first go at giving the agent true bash access
#the bash access we are starting with is the gh command


#TODO add all git commands
"""
ADD
git log --oneline                  # recent commits
git log --oneline src/myfile.py    # history of a specific file
git blame src/myfile.py            # who changed what line
git diff HEAD~1                    # what changed in last commit
git log -S "function_name"         # when was this introduced

git checkout develop                            # start from develop
git pull
git switch -c new_branch                        # create + switch to new branch
# ... make changes ...
git add .                                       # stage
git diff --staged                               # review
git commit -m "msg"                             # commit
git push -u origin new_branch                   # push + set upstream
#
gh pr create --base develop --head new_branch   # open PR
#or interactive
gh pr create 
"""


#TODO , current set up cant access personal repos because of repo validation
class Bash():
    def __init__(self):
        self.deps = Settings()
        self._allowed_repos: set = None #lazy loaded as needed

        self.allowed_commands: list = ['gh','git']
        self.allowed_sub_commands: dict = {
            "issue create": {"--title", "--body", "--assignee", "--repo"},
            "issue list":   {"--repo", "--state", "--limit", "--assignee"},
            "label list":   {"--repo"},
            "repo list": {"aretecp"}, #"GarettWilson", "gwils1414"
            "repo view aretecp/": {f"{repo}" for repo in self.allowed_repos},
            "label": {"list"},
            "log": {"--oneline", "-S"},
            "diff": {"HEAD","HEAD~1"}

        }
        self.not_allowed: list = [
            "--delete", "--admin", "--token",
            "&&", ";", "|", ">", "<", "`", "$(",
            "../", "~/",
            "secret", "webhook", "deploy"
        ]

    @property
    def allowed_repos(self):
        '''
        Lazy loads allowed repos
        '''
        if self._allowed_repos is None:
            self._allowed_repos = self._fetch_repos()
        return self._allowed_repos


    @log
    def _fetch_repos(self) -> set:
        '''
        fetches repos
        '''
        result = subprocess.run(
            ["gh", "repo", "list", self.deps.GH_ORG, "--json", "nameWithOwner", "--limit", "100"],
            capture_output=True,
            text=True,
            shell=False
        )
        repos = json.loads(result.stdout)
        return [r["nameWithOwner"].lower() for r in repos]   

    @log
    def validate_commands(self, agent_pass: dict):
        '''
        validation proxy between agents commands and sub process execution
        '''
        command = agent_pass.get('command')
        sub_command = agent_pass.get('sub_command')
        args = agent_pass.get('args', {})

        # command check
        if command not in self.allowed_commands:
            return "Command not permitted"

        # sub command check
        if sub_command not in self.allowed_sub_commands:
            return "Sub command not permitted"

        # flag key check against allowlist for that sub_command
        allowed_flags = self.allowed_sub_commands[sub_command]
        for flag in args.keys():
            if flag not in allowed_flags:
                return f"Flag '{flag}' not permitted"

        # value check against blocklist
        for value in args.values():
            for blocked in self.not_allowed:
                if blocked in str(value).lower():
                    return f"Blocked pattern '{blocked}' detected in arguments"
                #limit length
                if len(str(value)) > 1000:
                    return f"Exceeded maximum length"
                
        #TODO , case insensitive pattern matching
        keys = agent_pass.get('args').keys()
        for key in keys:
            if key == '--repo':
                if str(agent_pass.get('args')[key]).lower() not in self.allowed_repos: #la
                    return "Repo not allowed"

        return None
        

    @log
    def run_subprocess(self,
                    agent_pass: str):
        '''
        execution of bash command
        '''

        # parse JSON string -> dict before validation
        agent_pass = json.loads(agent_pass)

        error = self.validate_commands(agent_pass)
        if error:
            console.print(f"[red]Validation failed: {error}[/red]")
            return error

        # build command list
        # ["gh", "issue", "create", "--title", "test title", "--body", "test body"]
        cmd = (
            [agent_pass['command']] +
            agent_pass['sub_command'].split() +
            [item for flag, value in agent_pass['args'].items() for item in (flag, str(value))]
        )

        # show human in the loop panel
        console.print(Panel(
            f"[dim]{' '.join(cmd)}[/dim]",
            title="[yellow]🔍 Pending gh command[/yellow]",
            border_style="yellow"
        ))

        approval = questionary.select(
            "Approve?",
            choices=["Yes", "No"]
        ).ask()

        if approval != "Yes":
            return "Cancelled"

        else:
            result = subprocess.run(
                cmd,
                cwd = Path.home() / 'Arete',
                capture_output=True,
                text=True,
                shell=False
            )
            return result.stdout or result.stderr
        

    #TODO , from there , add GREP, ls etc at the arete directory so we can get a handle on the working repos.
    #Hermes can run from anywhere but we only want it to have access to arete
    #need to really transition this to actually local / work API key if i am giving it gh code access