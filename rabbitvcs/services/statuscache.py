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
# The following three lines allow you to select between three different status
# checker implementations. Simply uncomment one to try it out - there's nothing
# else you have to do.

# from rabbitvcs.services.checkerservice import StatusCheckerStub as StatusChecker
# from rabbitvcs.services.simplechecker import StatusChecker
from rabbitvcs.services.loopedchecker import StatusChecker

import rabbitvcs.util.vcs
import rabbitvcs.lib.vcs.svn

# FIXME: debug
from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.services.statuscache")

import time

# FIXME: hard coded
# NOTE: try changing this to a few hundred, or a few thousand to check operation
# The debugging statements below will tell you how many items are being cached
MAX_CACHE_SIZE = 1000000 # Items

def status_calculating(path):
    return {path: {"text_status": "calculating",
                   "prop_status": "calculating"}}

def status_unknown(path):
    return {path: {"text_status": "unknown",
                   "prop_status": "unknown"}}

def is_under_dir(base_path, other_path):
    # Warning: this function is greatly simplified compared to something more
    # rigorous. This is because the Python stdlib path manipulation functions
    # are just too slow for proper use here.
    return (base_path == other_path or other_path.startswith(base_path + "/"))

def is_directly_under_dir(base_path, other_path):
    check_path = base_path + "/"
    return (other_path.startswith(check_path)
            and "/" not in other_path.replace(check_path, "", 1).rstrip("/"))

def make_summary(path, statuses):
    return ({path: statuses[path]},
            rabbitvcs.util.vcs.get_summarized_status_both(path, statuses))


class StatusCache():
    #: The queue will be populated with 4-ples of
    #: (path, recurse, invalidate, callback).
    _paths_to_check = Queue()
    
    #: This tree stores the status of the items. We monitor working copy
    #: for changes and modify this tree in-place accordingly. This way
    #: apart from an intial recursive check we don't have to do any
    #: and the speed is increased because the tree is in memory.
    #:
    #: This isn't a tree (yet) and looks like:::
    #:
    #:     _status_tree = {
    #:         "/foo": {"age": 1,
    #:                  "status": {"text_status": "normal", "prop_status": "normal"}},
    #:         "/foo/bar": {"age": 2,
    #:                      "status": {"text_status": "normal", "prop_status": "normal"}},
    #:         "/foo/bar/baz": {"age": 2,
    #:                          "status": {"text_status": "added", "prop_status": "normal"}}
    #:     }
    #:
    #: As you can see it's not a tree (yet) and the way statuses are 
    #: collected as by iterating through the dictionary.
    #:
    #: The age parameter is used for limiting the size of the cache. Yes, it is
    #: meant to be repeated. Yes, it is actually the opposite of age, in that
    #: higher = newer. But of course, you read this comment before you tried to
    #: do anything with it, didn't you. DIDN'T YOU?
    #:
    #: The "age" parameter should be based on when the path was requested, so
    #: even if this triggers many recursive additions to the cache, all ages for
    #: those paths should be the same.
    #: 
    #: I was worried that, being a number, this could overflow. But the Python
    #: library reference states that: "long integers have unlimited precision."
    _status_tree = dict()
        
    #: Need a re-entrant lock here, look at check_status/add_path_to_check
    _status_tree_lock = threading.RLock()
    
    # In here to avoid circular imports
    # from rabbitvcs.lib.extensions.nautilus.RabbitVCS import log

    def __init__(self):
        self.worker = threading.Thread(target = self.status_update_loop,
                                       name = "Status cache thread")

        self.client = rabbitvcs.lib.vcs.create_vcs_instance()

        self._alive = threading.Event()
        self._alive.set()

        # This means that the thread will die when everything else does. If
        # there are problems, we will need to add a flag to manually kill it.
        # self.checker = StatusCheckerStub()
        self.checker = StatusChecker()
        # self.worker.setDaemon(True)
        self.worker.start()
                
    def path_modified(self, path):
        """
        Alerts the status checker that the given path was modified. It will be
        removed from the list (but not from pending actions, since they will be
        re-checked anyway).
        """
        with self._status_tree_lock:
            pass
            # Need to clarify the logic for this. Stub for now.
    
    
    
    def check_status(self, path, 
                     recurse=False, invalidate=False,
                     summary=False, callback=None):
        """
        Checks the status of the given path. The callback must be thread safe.
        
        This can go two ways:
        
          1. If we've already looked the path up, return the statuses associated
             with it. This will block for as long as any other thread has our
             status_tree locked.
        
          2. If we haven't already got the path, return [(path, "calculating")]. 
             This will also block for max of (1) as long as the status_tree is 
             locked OR if the queue is blocking. In the meantime, the thread 
             will pop the path from the queue and look it up.
        """
        # log.debug("Status request for: %s" % path)
        
        statuses = {}
       
        found_in_cache = False
        
        if self.client.is_in_a_or_a_working_copy(path):
            if not invalidate:
                with self._status_tree_lock:
                    if path in self._status_tree:
                        # We're good, so return the status
                        found_in_cache = True
                        statuses = self._get_path_statuses(path, recurse)
                
            if invalidate or not found_in_cache:
                # We need to calculate the status
                statuses = status_calculating(path)
                self._paths_to_check.put((path, recurse, invalidate, summary, callback))

        else:
            statuses = status_unknown(path)
        
        # log.debug("%s: found in cache (%s)" % (path, found_in_cache))
        
        if summary:
            statuses = make_summary(path, statuses)
        
        return statuses
        
    def status_update_loop(self):
        # This loop will stop when the thread is killed via the kill() method
        while self._alive.isSet():
            # This call will block if the Queue is empty, until something is
            # added to it. There is a better way to do this if we need to add
            # other flags to this.
            next = self._paths_to_check.get()
            if next:
                (path, recurse, invalidate, summary, callback) = next
            else:
                continue
            self._update_path_status(path, recurse, invalidate, summary, callback)
        
        log.debug("Exiting cache")
    
    def kill(self):
        self._alive.clear()
        self._paths_to_check.put(None)
    
    def _get_path_statuses(self, path, recurse):
        statuses = {}
        with self._status_tree_lock:
            if recurse:
                child_keys = [another_path for another_path
                                in self._status_tree.keys()
                                if is_under_dir(path, another_path)]
                for another_path in child_keys:
                    statuses[another_path] = self._status_tree[another_path]["status"]
            else:
                statuses[path] = self._status_tree[path]["status"]

        return statuses
    
    def _invalidate_path(self, path):
        with self._status_tree_lock:
            child_keys = [another_path for another_path
                                in self._status_tree.keys()
                                if is_under_dir(path, another_path)]
            for another_path in child_keys:
                del self._status_tree[another_path]
    
    def _update_path_status(self, path, recurse=False, invalidate=False, summary=False, callback=None):
        statuses = {}

        # We can't trust the cache when we invalidate, because some items may
        # have been renamed/deleted, and so we will end up with orphaned items
        # in the status cache that cause inaccurate results for parent folders
        found_in_cache = False
        
        if invalidate:
            self._invalidate_path(path)
        else:
            # Another status check which includes this path may have completed in
            # the meantime so let's do a sanity check.
            found_in_cache = False
            
            with self._status_tree_lock:
                if path in self._status_tree:
                    # log.debug("Sanity check proves useful! [%s]" % path)
                    # statuses = self._get_path_statuses(path, recurse)
                    statuses = self._get_path_statuses(path, recurse)
                    found_in_cache = True
                    
        if not found_in_cache:
            # Uncomment this for useful simulation of a looooong status check :) 
            # log.debug("Sleeping for 10s...")
            # time.sleep(5)
            # log.debug("Done.")
            
            # Otherwise actually do a status check
            
            check_results = None
            check_summary = None
            
            if summary:
                (check_results, check_summary) = self.checker.check_status(path, recurse, summary)
            else:
                check_results = self.checker.check_status(path, recurse, summary)
                
            
            with self._status_tree_lock:
                self._add_path_statuses(check_results)
                statuses = self._get_path_statuses(path, recurse)
            
        # Remember: these callbacks will block THIS thread from calculating the
        # next path on the "to do" list.
        
        if summary:
            statuses = ({path: statuses[path]}, check_summary)
        
        if callback: callback(path, statuses)

    def _add_path_statuses(self, statuses):
        with self._status_tree_lock:
            age = self._get_max_age() + 1
        
            for path, text_status, prop_status in statuses:
                self._status_tree[path] = {"age":  age,
                                            "status":
                                                {"text_status" : text_status,
                                                 "prop_status" : prop_status}}
                
            self._clean_status_cache()

    def _get_max_age(self):
        with self._status_tree_lock:
            ages = [data["age"] for (path, data) in self._status_tree.items()]
            if ages:
                age = max(data["age"] for (path, data) in self._status_tree.items())
            else:
                age = 0
                
            return age

    def _get_min_age(self):
        with self._status_tree_lock:
            ages = [data["age"] for (path, data) in self._status_tree.items()]
            if ages:
                age = min(data["age"] for (path, data) in self._status_tree.items())
            else:
                age = 0
                
            return age

    
    def _clean_status_cache(self):
        """
        Tries to ensure the status cache remains under a certain size. This will
        not enforce a strict limit. The actual limit of the cache is:
            max( largest WC status tree checked in one go , MAX_CACHE_SIZE )
        """
        with self._status_tree_lock:
            # We only care if the cache is bigger than the max size BUT we don't
            # want to delete the entire cache every time.
            # log.debug("Status cache size: %i" % len(self._status_tree))
            
            max_age = self._get_max_age()
            min_age = min([data["age"] for (path, data) in self._status_tree.items()])
            
            while len(self._status_tree) > MAX_CACHE_SIZE and min_age != max_age:
                paths = [path for path in self._status_tree.keys() if self._status_tree[path]["age"] == min_age]
                for path in paths:
                    del self._status_tree[path]
                min_age = min([data["age"] for (path, data) in self._status_tree.items()])
                log.debug("Removed %i paths from status cache" % len(paths))
