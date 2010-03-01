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

import rabbitvcs.util.locale
import rabbitvcs.util.vcs
import rabbitvcs.lib.vcs

from rabbitvcs.services.statuschecker import status_error

from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.statuschecker_proc")

PICKLE_PROTOCOL = cPickle.HIGHEST_PROTOCOL

def Main(path, recurse, summary):
    """
    Perform a VCS status check on the given path (recursive as indicated). The
    results will be pickled and sent as a byte stream over stdout.
    """
    # NOTE: we cannot pickle status_list directly. It needs to be processed
    # here.
    try:
        vcs_client = rabbitvcs.lib.vcs.create_vcs_instance()
        status_list = vcs_client.status(path, recurse=recurse)
        statuses = [(status.path,
                     str(status.text_status),
                     str(status.prop_status)) for status in status_list]
        
    except Exception, ex:
        log.exception(ex)
        statuses = [status_error(path)]

    if summary:
        statuses = (statuses,
                    rabbitvcs.util.vcs.summarize_status_pair_list(path,
                                                                  statuses))

    
    cPickle.dump(statuses, sys.stdout)
    sys.stdout.flush()

class StatusChecker():
    """ A class for performing status checks in a separate process.

    Since C extensions may lock the GIL, preventing multithreading and making
    our cache service block, we can do the hard parts in another process. Since
    we're transferring a LOT of data, we pickle it.
    
    This class differs from "loopedchecker.py" in that it creates a separate
    process for EACH request. This might seem dumb - the process creation
    overhead is (I hear) small on Linux, but it all adds up. However, this is
    a completely rock-solid way to get around potential memory leaks in
    C extension code.
    
    A better way would be to put more status monitoring into the looped
    checker...
    """
   
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

        sc_process = subprocess.Popen([sys.executable, __file__,
                                       path.encode("utf-8"),
                                       str(recurse),
                                       str(summary)],
                               stdin = subprocess.PIPE,
                               stdout = subprocess.PIPE)
        statuses = cPickle.load(sc_process.stdout)
        sc_process.stdout.close()
        sc_process.stdin.close()
        return statuses
    
    def quit(self):
        pass

if __name__ == '__main__':
    # I have deliberately avoided rigourous input checking since this script is
    # only designed to be called from our extension code.
   
    rabbitvcs.util.locale.initialize_locale()
   
    # This is correct, and should work across all locales and encodings.
    path = unicode(sys.argv[1], "utf-8")
    recurse = (sys.argv[2] in ["True", "1"])
    summary = (sys.argv[3] in ["True", "1"])
       
    Main(path, recurse, summary)
