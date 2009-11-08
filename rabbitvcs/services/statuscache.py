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
""" A VCS status cache which can be queried synchronously and asynchronously.

The "check_status" method will return "as soon as possible", with either a 
cached status or a "calculating" status. Callbacks can also be registered and
will be notified when a proper status check is done.
"""


from __future__ import with_statement

import threading
from Queue import Queue

#    ATTENTION: Developers and hackers!
# The following lines allow you to select between different status checker
# implementations. Simply uncomment one to try it out - there's nothing else you
# have to do.

# from rabbitvcs.services.checkerservice import StatusCheckerStub as StatusChecker
# from rabbitvcs.services.simplechecker import StatusChecker
from rabbitvcs.services.loopedchecker import StatusChecker

import rabbitvcs.util.vcs
import rabbitvcs.lib.vcs.svn

from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.services.statuscache")

# FIXME: hard coded
# NOTE: try changing this to a few hundred, or a few thousand to check operation
# The debugging statements below will tell you how many items are being cached
MAX_CACHE_SIZE = 1000000 # Items

def status_calculating(path):
    """ Creates a "calculating" status for the given path. """
    return {path: {"text_status": "calculating",
                   "prop_status": "calculating"}}

def status_unknown(path):
    """ Creates an "unknown" status for the given path. """
    return {path: {"text_status": "unknown",
                   "prop_status": "unknown"}}

def is_under_dir(base_path, other_path):
    """ Checks whether the given "other_path" is under "base_path".
    
    Assumes: the paths are already absolute, normalised and that the path
    separator is "/". 
    
    Warning: this function is greatly simplified compared to something more
    rigorous. This is because the Python stdlib path manipulation functions
    are just too slow for proper use here.
    
    @param base_path: the path that is the possible ancestor (parent, etc)
    @type base_path: string - an absolute, normalised, "/" separated path
    
    @param other_path: the path that is the possible descendant (child, etc)
    @type other_path: string - an absolute, normalised, "/" separated path

    
    """
    return (base_path == other_path or other_path.startswith(base_path + "/"))

def is_directly_under_dir(base_path, other_path):
    """ Checks whether the given "other_path" is EXACTLY ONE LEVEL under
    "base_path".
    
    Assumes: the paths are already absolute, normalised and that the path
    separator is "/". 
    
    Warning: this function is greatly simplified compared to something more
    rigorous. This is because the Python stdlib path manipulation functions
    are just too slow for proper use here.
    
    @param base_path: the path that is the possible direct parent
    @type base_path: string - an absolute, normalised, "/" separated path
    
    @param other_path: the path that is the possible direct child
    @type other_path: string - an absolute, normalised, "/" separated path
    """
    check_path = base_path + "/"
    return (other_path.startswith(check_path)
            and "/" not in other_path.replace(check_path, "", 1).rstrip("/"))

def make_summary(path, statuses):
    """ Simple convenience method to make the path summaries we pass back to the
    callbacks.
    
    @param path: the path that the statuses resulted from checking
    @type path: string
    
    @param statuses: the status dict for the path
    @type statuses: dict - {path: {"text_status": "whatever"
                                   "prop_status": "whatever"}, path2: ...}
                                   
    @return: (single status, summarised status)
    @rtype: see StatusCache documentation
    """
    return ({path: statuses[path]},
            rabbitvcs.util.vcs.summarize_status_pair(path, statuses))


class StatusCache():
    """ A StatusCache object maintains an internal cache of VCS status that have
    been previously checked. There are also hooks (as yet unimplemented) to be
    called by a separate status monitor when files are changed.
    
    The actual status checks are done by a separate object, which should have
    a "check_status(self, path, recurse, summary)" method (see the specific
    classes for details).
    
    If a summary is requested, the return type/callback parameter will always be
    of the form:
        
        (non-recursive status dict, summarised recursive status dict)
    
    ...where both dicts are of the form:
    
        {path: {"text_status": text_status,
                "prop_status": prop_status}}
                
    Otherwise, the return/callback value will be a single dict of the form:
    
        {path1: {"text_status": text_status1,
                 "prop_status": prop_status1},
                 
         path2: {"text_status": text_status2,
                 "prop_status": prop_status2},
        
        ...}
    
    All thread synchronisation should be taken care of BY THIS CLASS. Callers
    of public methods should not have to worry about synchronisation, except
    that callbacks may originate from a different thread (since this class is
    meant to be used in a separate process, that's probably not a big deal).
    
    Note about paths: here and there I've specified a "sane path". This class
    does not do robust path checking and normalisation, so basically what is
    meant is: this class expects absolute, normalised paths everywhere. This is
    what Nautilus gives us, it is what PySVN gives us, so unless you're
    hard-wiring something in, you should be fine.
    
    Note to developers: The major pitfall here is that the check_status needs to
    access the cache, and will therefore block while the cache is locked.
    Therefore, GREAT CARE must be taken to avoid locking the cache for longer
    than necessary.
    """
    
    # FIXME: note to developers... the major bottleneck in this class is the
    # fact that for each check of the cache, we loop over ALL of the keys to
    # find the child paths. We need to come up with a proper data structure for
    # this.
    
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
    #:                  "status": {"text_status": "normal",
    #:                             "prop_status": "normal"}},
    #:         "/foo/bar": {"age": 2,
    #:                      "status": {"text_status": "normal",
    #:                                 "prop_status": "normal"}},
    #:         "/foo/bar/baz": {"age": 2,
    #:                          "status": {"text_status": "added",
    #:                                     "prop_status": "normal"}}
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
    
    def __init__(self):
        """ Creates a new status cache.
        
        This will start the necessary worker thread and subprocess for checking.
        """
        self.worker = threading.Thread(target = self._status_update_loop,
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
        """ Alerts the status checker that the given path was modified.
        
        NOT YET IMPLEMENTED
        
        The path (and all children? ancestors?) will be removed from the cache
        (but not from pending actions, since they will be re-checked anyway).
        """
        with self._status_tree_lock:
            pass
            # Need to clarify the logic for this. Stub for now.
    
    
    
    def check_status(self, path, 
                     recurse=False, invalidate=False,
                     summary=False, callback=None):
        """
        Checks the status of the given path and registers a callback.
        
        This can go two ways:
        
          1. If we've already looked the path up, return the statuses associated
             with it. This will block for as long as any other thread has our
             status_tree locked.
        
          2. If we haven't already got the path, return [(path, "calculating")]. 
             This will also block for max of (1) as long as the status_tree is 
             locked OR if the queue is blocking (should not be a significant
             problem). In the meantime, the thread will pop the path from the
             queue and look it up.
             
        @param path: the path to check the status of
        @type path: string (a sane path)
             
        @param recurse: whether the check should be recursive
        @type recurse: boolean
        
        @param invalidate: whether to invalidate the path we are checking (ie.
                           force an update of the cache)
        @type invalidate: boolean
        
        @param summary: If True, a summarised status will be returned, and if a
                        callback is given then it will also pass back a summary.
                        See the class level documentation for details of the
                        summary. This is useful for easing inter-process
                        communication congestion.
        @type summary: boolean
        
        @param callback: This function will be called when the status check is
                         complete - it will NOT be called if we already have the
                         statuses in the cache and we are not invalidating. The
                         callback will be called from a separate thread.
        @type callback: a function with the API callback(path, statuses),
                        or None (or False) for no callback
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
                self._paths_to_check.put((path, recurse, invalidate, summary,
                                          callback))

        else:
            statuses = status_unknown(path)
        
        # log.debug("%s: found in cache (%s)" % (path, found_in_cache))
        
        if summary:
            statuses = make_summary(path, statuses)
        
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
                (path, recurse, invalidate, summary, callback) = next
            else:
                continue
            
            self._update_path_status(path, recurse, invalidate, summary,
                                     callback)
        
        log.debug("Exiting status cache update loop")
    
    def _get_path_statuses(self, path, recurse):
        """ This will check the cache for a status for the given path.
        
        @param path: the path to check for
        @type path: string (sane path)
        
        @param recurse: if True, the returned status dict will contain statuses
                        for all children of the given path
        @type recurse: boolean
        
        @return: a status dict for the given path
        @rtype: see class documentation
        """
        statuses = {}
        
        with self._status_tree_lock:
            if recurse:
                child_keys = [another_path for another_path
                                in self._status_tree.keys()
                                if is_under_dir(path, another_path)]
                
                for another_path in child_keys:
                    statuses[another_path] = \
                        self._status_tree[another_path]["status"]
            else:
                statuses[path] = self._status_tree[path]["status"]

        return statuses
    
    def _invalidate_path(self, path):
        """ Invalidates the status information for the given path. This will
        also invalidate the information for any children.
        """
        with self._status_tree_lock:
            child_keys = [another_path for another_path
                                in self._status_tree.keys()
                                if is_under_dir(path, another_path)]
            for another_path in child_keys:
                del self._status_tree[another_path]
    
    def _update_path_status(self, path, recurse=False, invalidate=False,
                               summary=False, callback=None):
        """ Update the cached information for the given path, notifying the
        callback upon completion.
        
        This function will check the cache first, just in case a previous call
        has populated the path in question and we are not invalidating.
        
        The parameters are as per check_status, but instead of a return type
        there is the callback.
        """ 
        statuses = {}

        # We can't trust the cache when we invalidate, because some items may
        # have been renamed/deleted, and so we will end up with orphaned items
        # in the status cache that cause inaccurate results for parent folders
        found_in_cache = False
        
        if invalidate:
            self._invalidate_path(path)
        else:
            # Another status check which includes this path may have completed
            # in the meantime so let's do a sanity check.
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
                (check_results, check_summary) = \
                    self.checker.check_status(path, recurse, summary)
            else:
                check_results = self.checker.check_status(path, recurse,
                                                          summary)
                
            
            with self._status_tree_lock:
                self._add_path_statuses(check_results)
                statuses = self._get_path_statuses(path, recurse)
            
        # Remember: these callbacks will block THIS thread from calculating the
        # next path on the "to do" list.
        
        if summary:
            statuses = ({path: statuses[path]}, check_summary)
        
        if callback:
            callback(path, statuses)

    def _add_path_statuses(self, statuses):
        """ Adds a list of VCS statuses to our cache.
        
        This will keep track of the "age" parameter, and always requests a clean
        for every call (the clean may not actually do anything if the cache is
        not too big).
        
        @param statuses: the VCS statuses to add to the cache
        @type statuses: a list of tuples of the form:
                        [(path1, text_status1, prop_status1), (path2, ...), ...]
        """
        with self._status_tree_lock:
            age = self._get_max_age() + 1
        
            for path, text_status, prop_status in statuses:
                self._status_tree[path] = {"age":  age,
                                            "status":
                                                {"text_status" : text_status,
                                                 "prop_status" : prop_status}}
                
            self._clean_status_cache()

    def _get_max_age(self):
        """ Computes the minimum age of any of the cached statuses.
        """
        with self._status_tree_lock:
            ages = [data["age"] for
                    (path, data) in self._status_tree.items()]
            if ages:
                age = max(data["age"] for
                          (path, data) in self._status_tree.items())
            else:
                age = 0
                
            return age

    def _get_min_age(self):
        """ Computes the minimum age of any of the cached statuses.
        """
        with self._status_tree_lock:
            ages = [data["age"] for
                    (path, data) in self._status_tree.items()]
            if ages:
                age = min(data["age"] for
                          (path, data) in self._status_tree.items())
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
            min_age = min([data["age"] for
                           (path, data) in self._status_tree.items()])
            
            while (len(self._status_tree) > MAX_CACHE_SIZE and
                    min_age != max_age):
                
                paths = (path for 
                            path in self._status_tree.keys() if
                                self._status_tree[path]["age"] == min_age)
                
                for path in paths:
                    del self._status_tree[path]
                
                min_age = min([data["age"] for
                               (path, data) in self._status_tree.items()])
                
                log.debug("Removed %i paths from status cache" % len(paths))
