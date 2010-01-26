#
# Copyright (C) 2009 Jason Heeris <jason.heeris@gmail.com>
# Copyright (C) 2009 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2009 by Adam Plumb <adamplumb@gmail.com>#
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


from __future__ import with_statement

import threading
from Queue import Queue

#    ATTENTION: Developers and hackers!
# The following lines allow you to select between different status checker
# implementations. Simply uncomment one to try it out - there's nothing else you
# have to do.

# from rabbitvcs.services.checkerservice import StatusCheckerStub as StatusChecker
# from rabbitvcs.services.simplechecker import StatusChecker
# from rabbitvcs.services.statuschecker import StatusChecker
from rabbitvcs.services.checkers.loopedchecker import StatusChecker

import rabbitvcs.util.vcs
import rabbitvcs.lib.vcs.svn

from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.services.statuscheckerplus")

def status_calculating(path):
    """ Creates a "calculating" status for the given path. """
    return {path: {"text_status": "calculating",
                   "prop_status": "calculating"}}

def status_unknown(path):
    """ Creates an "unknown" status for the given path. """
    return {path: {"text_status": "unknown",
                   "prop_status": "unknown"}}

def make_summary(path, statuses):
    """ Simple convenience method to make the path summaries we pass back to the
    callbacks.
    
    @param path: the path that the statuses resulted from checking
    @type path: string
    
    @param statuses: the status dict for the path
    @type statuses: dict - {path: {"text_status": "whatever"
                                   "prop_status": "whatever"}, path2: ...}
                                   
    @return: (single status, summarised status)
    @rtype: see StatusChecker documentation
    """
    return ({path: statuses[path]},
            rabbitvcs.util.vcs.summarize_status_pair(path, statuses))


class StatusCheckerPlus():

    #: The queue will be populated with 4-ples of
    #: (path, recurse, invalidate, callback).
    _paths_to_check = Queue()
        
    def __init__(self):
        """ Creates a new status cache.
        
        This will start the necessary worker thread and subprocess for checking.
        """
        self.worker = threading.Thread(target = self._status_update_loop,
                                       name = "Status cache thread")

        self.client = rabbitvcs.lib.vcs.create_vcs_instance()

        self._alive = threading.Event()
        self._alive.set()

        # We need a checker for each thread (if we use locks, we're right back
        # where we started from).
        self.checker = StatusChecker()
        self.other_checker = StatusChecker()
        # self.worker.setDaemon(True)
        self.worker.start()
     
    def check_status(self, path, 
                       recurse=False, invalidate=False,
                       summary=False, callback=None):
        # The invalidate parameter is not used.
        statuses = None
                
        if callback:
            statuses = \
            self._check_status_with_callback(path, recurse, summary, callback)
        else:
            statuses = \
            self._check_status_without_callback(path, self.checker, recurse,
                                                summary)
            
        return statuses
    
    def _check_status_with_callback(self, path, recurse=False,
                                         summary=False, callback=None):
        
        if self.client.is_in_a_or_a_working_copy(path):
            statuses = status_calculating(path)
            self._paths_to_check.put((path, recurse, summary, callback))
        else:
            statuses = status_unknown(path)

        if summary:
            statuses = make_summary(path, statuses)
            
        return statuses
        
    def _check_status_without_callback(self, path, checker, recurse=False,
                                            summary=False):
        
        # This might be considered a little hacky, but we need to use a
        # different checker for each thread.        
        statuses = {}
                    
        # Uncomment this for useful simulation of a looooong status check :)
        # log.debug("Sleeping for 10s...")
        # time.sleep(5)
        # log.debug("Done.")
        
        check_results = None
        check_summary = None
        
        if summary:
            (check_results, check_summary) = \
                checker.check_status(path, recurse, summary)
        else:
            check_results = checker.check_status(path, recurse, summary)
        
        for result_path, text_status, prop_status in check_results:
            statuses[result_path] = {"text_status" : text_status,
                                     "prop_status" : prop_status}

        if summary:
            statuses = ({path: statuses[path]}, check_summary)            
        
        return statuses
        
    def kill(self):
        """ Stops operation of the cache. Future calls to check_status will just
        get old information or a "calculating status", and callbacks will never
        be called.
        
        This is here so that we can do necessary cleanup. There might be a GUI
        interface to kill the enclosing service at some later date.
        """
        self._alive.clear()
        self._paths_to_check.put(None)
        
    def _status_update_loop(self):
        """ This loops until the status cache is "killed" (via the kill()
        method), checking for new paths and doing the status check accordingly.
        """
        # This loop will stop when the thread is killed via the kill() method
        while self._alive.isSet():
            next = self._paths_to_check.get()
            
            # This is a bit hackish, but basically when the kill method is
            # called, if we're idle we'll never know. This is a way of
            # interrupting the Queue.
            if next:
                (path, recurse, summary, callback) = next
            else:
                continue
            
            self._update_path_status(path, recurse, summary, callback)
        
        log.debug("Exiting status cache update loop")
        
    def _update_path_status(self, path, recurse=False,
                               summary=False, callback=None):
                
        statuses = self._check_status_without_callback(path, self.other_checker,
                                                       recurse, summary)

        if statuses and callback:
            callback(path, statuses)
