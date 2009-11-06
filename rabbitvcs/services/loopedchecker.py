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

At present the byte stream result of a pickle IS, in fact, ASCII data.
"""

import cProfile
import cPickle
import sys
import os, os.path
import subprocess
import time

from UserDict import UserDict

import pysvn

import rabbitvcs.util.locale
import rabbitvcs.util.vcs

from rabbitvcs.services.statuschecker import status_error

from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.statuschecker_proc")

PICKLE_PROTOCOL = cPickle.HIGHEST_PROTOCOL

def Main():
    """
    Perform a VCS status check on the given path (recursive as indicated). The
    results will be pickled and sent as a byte stream over stdout.
    """
    # NOTE: we cannot pickle status_list directly. It needs to be processed
    # here.

    log = Log("rabbitvcs.statuschecker:PROCESS")
    
    vcs_client = pysvn.Client()
    pickler = cPickle.Pickler(sys.stdout, PICKLE_PROTOCOL)
    unpickler = cPickle.Unpickler(sys.stdin)
    
    # FIXME: debug
    import time
    import math
    
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
            
        except Exception, e:
            log.exception(e)
            statuses = [status_error(path)]

        if summary:
            statuses = (statuses,
                        rabbitvcs.util.vcs.get_summarized_status_both_from_list(path, statuses))

        pickler.dump(statuses)
        sys.stdout.flush()
        pickler.clear_memo()
        del statuses
        

class StatusChecker():

    def __init__(self):
        self.sc_proc = subprocess.Popen([sys.executable, __file__],
                                        stdin = subprocess.PIPE,
                                        stdout = subprocess.PIPE)
        self.pickler = cPickle.Pickler(self.sc_proc.stdin, PICKLE_PROTOCOL)
        self.unpickler = cPickle.Unpickler(self.sc_proc.stdout)
   
    def check_status(self, path, recurse, summary):
        # cPickle.dump((path, bool(recurse)), sc_process.stdin, protocol=PICKLE_PROTOCOL)
        self.pickler.dump((path, bool(recurse), bool(summary)))
        self.sc_proc.stdin.flush()
        statuses = self.unpickler.load()
        return statuses

if __name__ == '__main__':
    # I have deliberately avoided rigourous input checking since this script is
    # only designed to be called from our extension code.
   
    rabbitvcs.util.locale.initialize_locale()

    # (path, recurse) = cPickle.load(sys.stdin)
       
    # Main()
    import rabbitvcs.lib.helper
    profile_data_file = os.path.join(
                            rabbitvcs.lib.helper.get_home_folder(),
                            "rvcs_checker.stats")
    cProfile.run("Main()", profile_data_file)