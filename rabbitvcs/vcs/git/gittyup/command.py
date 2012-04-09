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

def cancel_func():
    return False

class GittyupCommand:
    def __init__(self, command, cwd=None, notify=None, cancel=None):
        self.command = command
        
        self.notify = notify_func
        if notify:
            self.notify = notify

        self.get_cancel = cancel_func
        if cancel:
            self.get_cancel = cancel

        self.cwd = cwd
        if not self.cwd:
            self.cwd = os.getcwd()
    
    def get_lines(self, val):
        returner = []
        lines = val.rstrip("\n").split("\n")
        for line in lines:
            returner.append(line.rstrip("\x1b[K\n"))
        
        return returner 

    def execute(self):
        proc = subprocess.Popen(self.command,
                                cwd=self.cwd,
                                stdin=None,
                                stderr=subprocess.STDOUT,
                                stdout=subprocess.PIPE,
                                close_fds=True,
                                preexec_fn=os.setsid)

        stdout = []

        while True:
            #line = proc.stdout.readline()
            line = ""
            lastCharWasNewLine = False

            # Build a line of text
            while True:
                c = proc.stdout.read(1)
                # If we've reached the end of the file (pipe closed).
                if c == '':
                    break

                line += c # Append character to line

                # Break if we've complete a line.
                if c == '\n':
                    lastCharWasNewLine = True
                    break

                # Treat a carage return as newline unless 
                if c == '\r' and lastCharWasNewLine == False:
                    break

                lastCharWasNewLine = False

            if line == '':
                break
            #line = line.rstrip('\n') # Strip trailing newline.
            line = line[:-1]# Strip trailing newline.
            self.notify(line)
            stdout.append(line)

            if self.get_cancel():
                proc.kill()

        return (0, stdout, None)
