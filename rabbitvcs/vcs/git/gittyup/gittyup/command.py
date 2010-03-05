#
# command.py
#

import subprocess

from gittyup.exceptions import GittyupCommandError

class GittyupCommand:
    def __init__(self, command, cwd=None):
        self.command = command

        self.cwd = cwd
        if not self.cwd:
            self.cwd = os.getcwd()
    
    def execute(self):
        proc = subprocess.Popen(self.command, 
                                cwd=self.cwd,
                                stdin=None,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        
        try:
            stdout_value = proc.stdout.read()
            stderr_value = proc.stderr.read()
            status = proc.wait()
        finally:
            proc.stdout.close()
            proc.stderr.close()
        
        stdout_value = stdout_value.rstrip()
        stderr_value = stderr_value.rstrip()
        
        if status != 0:
            raise GittyupCommandError(self.command, status, stderr_value)
        
        return (status, stdout_value, stderr_value)
