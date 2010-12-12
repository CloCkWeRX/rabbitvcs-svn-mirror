#
# command.py
#

import subprocess
import fcntl
import select
import os

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
            self.cwd = os.getcwd()
    
    def callback_stack(self, val):
        lines = val.rstrip("\n").split("\n")
        for line in lines:
            self.notify(line.rstrip("\x1b[K\n"))
    
    def execute(self):
        proc = subprocess.Popen(self.command, 
                                cwd=self.cwd,
                                stdin=None,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                close_fds=True)
        
        fcntl.fcntl(
            proc.stdout.fileno(),
            fcntl.F_SETFL,
            fcntl.fcntl(proc.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK,
        )
        
        stdout = []
        while True:
            readx = select.select([proc.stdout.fileno()], [], [])[0]
            if readx:
                chunk = proc.stdout.read()
                if chunk == '':
                    break
                stdout.append(chunk)
                self.callback_stack(chunk)
        
        return (0, stdout, None)
