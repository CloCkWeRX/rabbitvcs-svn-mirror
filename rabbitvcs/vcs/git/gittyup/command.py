#
# command.py
#

import subprocess
from os import getcwd

from exceptions import GittyupCommandError

def notify_func(data):
    pass

class GittyupCommand:
    def __init__(self, command, cwd=None, notify=None):
        self.command = command
        
        self.notify = notify_func
        if notify:
            self.notify = notify

        self.cwd = cwd
        if not self.cwd:
            self.cwd = getcwd()
    
    def callback_stack(self, val):
        lines = val.rstrip("\n").split("\n")
        for line in lines:
            self.notify(line.rstrip("\x1b[K\n"))
    
    def execute(self):
        proc = subprocess.Popen(self.command, 
                                cwd=self.cwd,
                                stdin=None,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        
        try:
            stdout_value = proc.stdout.read()
            stderr_value = proc.stderr.read()
            
            self.callback_stack(stderr_value)
            #self.callback_stack(stdout_value)
            status = proc.wait()
        finally:
            proc.stdout.close()
            proc.stderr.close()
        
        stderr_value = stderr_value.rstrip()
        
        if status != 0:
            raise GittyupCommandError(self.command, status, stderr_value)
        
        return (status, stdout_value, stderr_value)
