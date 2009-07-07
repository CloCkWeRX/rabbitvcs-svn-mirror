"""

"""

from __future__ import with_statement

import threading
from Queue import Queue

import pysvn

import nautilussvn.util.vcs

class StatusChecker(threading.Thread):
    #: The queue will be populated with 4-ples of
    #: (path, recurse, invalidate, callback).
    __paths_to_check = Queue()
    
    #: This tree stores the status of the items. We monitor working copy
    #: for changes and modify this tree in-place accordingly. This way
    #: apart from an intial recursive check we don't have to do any
    #: and the speed is increased because the tree is in memory.
    #:
    #: This isn't a tree (yet) and looks like:::
    #:
    #:     __status_tree = {
    #:         "/foo": "normal",
    #:         "/foo/bar": normal",
    #:         "/foo/bar/baz": "added"
    #:     }
    #:
    #: As you can see it's not a tree (yet) and the way statuses are 
    #: collected as by iterating through the dictionary.
    __status_tree = dict()
    
    #: Need a re-entrant lock here, look at check_status/add_path_to_check
    __status_tree_lock = threading.RLock()

    def __init__(self):
        threading.Thread.__init__(self)
        
        self.vcs_client = pysvn.Client()
        
        # This means that the thread will die when everything else does. If
        # there are problems, we will need to add a flag to manually kill it.
        self.setDaemon(True)
        
    def check_status(self, path, recurse=False, invalidate=False, callback=None):
        """
        Checks the status of the given path. Must be thread safe.
        
        This can go two ways:
        
          1. If we've already looked the path up, return the statuses associated
             with it. This will block for as long as any other thread has our
             status_tree locked.
        
          2. If we haven't already got the path, return [(path, "calculating")]. 
             This will also block for max of (1) as long as the status_tree is 
             locked OR if the queue is blocking. In the meantime, the thread 
             will pop the path from the queue and look it up.
        """
        
        with self.__status_tree_lock:
            if nautilussvn.util.vcs.is_in_a_or_a_working_copy(path):
                if not invalidate and path in self.__status_tree:
                    statuses = self.__get_path_statuses(path)
                    if callback: callback(path, statuses)
                else:
                    statuses = [(path, "calculating")]
                    self.__paths_to_check.put((path, recurse, invalidate, callback))
            else:
                statuses = [(path, "unknown")]
                if callback: callback(path, statuses)
                
        return statuses
        
    def run(self):
        """
        Overrides the run method from Thread, so do not put any arguments in
        here.
        """
        
        # This loop will stop when the thread is killed, which it will 
        # because it is daemonic.
        while True:
            # This call will block if the Queue is empty, until something is
            # added to it. There is a better way to do this if we need to add
            # other flags to this.
            (path, recurse, invalidate, callback) = self.__paths_to_check.get()
            self.__update_path_status(path, recurse, invalidate, callback)
    
    def __get_path_statuses(self, path):
        statuses = []
        with self.__status_tree_lock:
            for another_path in self.__status_tree.keys():
                if another_path.startswith(path):
                    statuses.append((another_path, self.__status_tree[another_path]))
        
        return statuses
        
    def __update_path_status(self, path, recurse=False, invalidate=False, callback=None):
        statuses = []
        
        # Another status check which includes this path may have completed in
        # the meantime so let's do a sanity check.
        with self.__status_tree_lock:
            if not invalidate and path in self.__status_tree:
                statuses = self.__get_path_statuses(path)
                if callback: callback(path, statuses)
                return
        
        # Otherwise actually do a status check
        statuses = [(status.path, str(status.text_status)) 
                        for status in self.vcs_client.status(path, recurse=recurse)]
        
        with self.__status_tree_lock:
            for path, status in statuses:
                self.__status_tree[path] = status
        
        # Remember: these callbacks will block THIS thread from calculating the
        # next path on the "to do" list.
        if callback: callback(path, self.__get_path_statuses(path))
    
