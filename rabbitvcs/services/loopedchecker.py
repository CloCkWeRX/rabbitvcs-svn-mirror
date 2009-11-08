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
import sys
import subprocess

import rabbitvcs.lib.vcs

import rabbitvcs.util.locale
import rabbitvcs.util.vcs

from rabbitvcs.services.statuschecker import status_error

from rabbitvcs.lib.log import Log
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
    
    vcs_client = rabbitvcs.lib.vcs.create_vcs_instance()
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
            status_list = vcs_client.status(path, recurse=recurse)
            statuses = [(status.path, str(status.text_status), str(status.prop_status))
                       for status in status_list]
            
            # NOTE: this is useful for debugging. You can tweak MAGIC_NUMBER to
            # make status checks appear to take longer or shorter.
#            import time, math
#            statuses = []            
#            MAGIC_NUMBER = 10
#            if os.path.isdir(path):
#                for root, dirnames, fnames in os.walk(path):
#                    names = ["."]
#                    names.extend(dirnames)
#                    names.extend(fnames)
#                    for name in names:
#                        thing = os.path.abspath(os.path.join(root, name))
#                        if "/.svn" not in thing:
#                            num = 0
#                            while num < 10:
#                                math.sin(num)
#                                num+=1
#                            statuses.append( (thing, "added", "normal") )
#            else:
#                num = 0
#                while num < 10:
#                    math.sin(num)
#                    num+=1
#                statuses.append( (path, "added", "none") )
            
        except Exception, ex:
            log.exception(ex)
            statuses = [status_error(path)]

        if summary:
            statuses = (statuses,
                        rabbitvcs.util.vcs.summarize_status_pair_list(path,
                                                                      statuses))

        pickler.dump(statuses)
        sys.stdout.flush()
        pickler.clear_memo()
        del statuses
        

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
        
        The returned status data can have two forms. If a summary is requested,
        it is:
        
            (status list, summarised dict)
            
        ...where the list is of the form
        
            [(path1, text_status1, prop_status1), (path2, ...), ...]
            
        ...and the dict is:
        
            {path: {"text_status": text_status,
                    "prop_status": prop_status}}
        
        If no summary is requested, the return value is just the status list.
        """
        self.pickler.dump((path, bool(recurse), bool(summary)))
        self.sc_proc.stdin.flush()
        statuses = self.unpickler.load()
        return statuses

if __name__ == '__main__':
    # I have deliberately avoided rigourous input checking since this script is
    # only designed to be called from our extension code.
   
    rabbitvcs.util.locale.initialize_locale()
    
    # Uncomment for profiling
#    import rabbitvcs.lib.helper
#    import cProfile
#    import os, os.path
#    profile_data_file = os.path.join(
#                            rabbitvcs.lib.helper.get_home_folder(),
#                            "rvcs_checker.stats")
#    cProfile.run("Main()", profile_data_file)
    Main()