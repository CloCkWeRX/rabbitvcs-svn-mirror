#
# Copyright (C) 2009 Jason Heeris <jason.heeris@gmail.com>
#
# RabbitVCS is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# RabbitVCS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RabbitVCS;  If not, see <http://www.gnu.org/licenses/>.
#

"""
Convenience script for performing status checks in a separate process. This
script is NOT meant to be run from the command line - the results are sent over
stdout as a byte stream (ie. the pickled results of the status check).
"""

import cPickle
import os, sys, signal
import subprocess

import rabbitvcs.vcs
import rabbitvcs.util.helper

import rabbitvcs.util._locale
import rabbitvcs.util.vcs
import rabbitvcs.vcs.status

from rabbitvcs.util.log import Log
log = Log("rabbitvcs.statuschecker_proc")

PICKLE_PROTOCOL = cPickle.HIGHEST_PROTOCOL

def Main():
    """
    Loop indefinitely, performing VCS status checks on paths (and arguments)
    sent as pickled data over stdin. The results will be pickled and sent as a
    byte stream over stdout.
    
    The loop will temrinate if there is an I/O error.
    """
    # NOTE: we cannot pickle status_list directly. It needs to be processed
    # here.
    global log
    log = Log("rabbitvcs.statuschecker:PROCESS")
    
    def interrupt_handler(*args):
        log.debug("Checker loop interrupted, exiting")
        sys.exit(0)
    
    # Upon interrupt, exit
    signal.signal(signal.SIGINT, interrupt_handler)
    
    vcs_client = rabbitvcs.vcs.create_vcs_instance()
    pickler = cPickle.Pickler(sys.stdout, PICKLE_PROTOCOL)
    unpickler = cPickle.Unpickler(sys.stdin)
        
    while True:
        try:
            (path, recurse, summary) = unpickler.load()
        except EOFError:
            # This probably means our parent service has been killed
            log.debug("Checker sub-process exiting")
            sys.exit(0)
        
        try:
            # log.debug("Checking: %s" % path)
            path_status = vcs_client.status(path, summarize=summary)
            
        except Exception, ex:
            log.exception(ex)
            path_status = rabbitvcs.vcs.status.Status.status_error(path)

        assert path_status.path == path, "Path from PySVN %s != given path %s" % (path_status.path, path)
            
        pickler.dump(path_status)
        sys.stdout.flush()
        pickler.clear_memo()
        del path_status
        

class StatusChecker():
    """ A class for performing status checks in a separate process.
    
    Since C extensions may lock the GIL, preventing multithreading and making
    our cache service block, we can do the hard parts in another process. Since
    we're transferring a LOT of data, we pickle it.
    """

    def __init__(self):
        """ Creates a new StatusChecker. This should do ALL the subprocess
        management necessary.
        """
        self.sc_proc = subprocess.Popen([sys.executable, __file__],
                                        stdin = subprocess.PIPE,
                                        stdout = subprocess.PIPE)
        self.pickler = cPickle.Pickler(self.sc_proc.stdin, PICKLE_PROTOCOL)
        self.unpickler = cPickle.Unpickler(self.sc_proc.stdout)
   
    def check_status(self, path, recurse, summary):
        """ Performs a status check in a subprocess, blocking until the check is
        done. Even though we block here, this means that other threads can
        continue to run.
        """
        self.pickler.dump((path, bool(recurse), bool(summary)))
        self.sc_proc.stdin.flush()
        status = self.unpickler.load()
        return status

    def get_memory_usage(self):
        """ Returns any additional memory of any subprocesses used by this
        checker. In other words, DO NOT return the memory usage of THIS process! 
        """
        return rabbitvcs.util.helper.process_memory(self.sc_proc.pid)

    def get_extra_PID(self):
        return self.sc_proc.pid

    def quit(self):
        os.kill(self.sc_proc.pid, signal.SIGINT)
        self.sc_proc.stdin.close()
        self.sc_proc.stdout.close()
        self.sc_proc.wait()
        log.debug("Checker loop done.")

if __name__ == '__main__':
    # I have deliberately avoided rigourous input checking since this script is
    # only designed to be called from our extension code.
   
    rabbitvcs.util._locale.initialize_locale()
    
    # Uncomment for profiling
#    import rabbitvcs.util.helper
#    import cProfile
#    import os, os.path
#    profile_data_file = os.path.join(
#                            rabbitvcs.util.helper.get_home_folder(),
#                            "rvcs_checker.stats")
#    cProfile.run("Main()", profile_data_file)
    Main()
