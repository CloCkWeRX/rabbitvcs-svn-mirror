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

import sqlobject

#    ATTENTION: Developers and hackers!
# The following three lines allow you to select between three different status
# checker implementations. Simply uncomment one to try it out - there's nothing
# else you have to do.

# from rabbitvcs.services.checkerservice import StatusCheckerStub as StatusChecker
# from rabbitvcs.services.simplechecker import StatusChecker
from rabbitvcs.services.loopedchecker import StatusChecker

from rabbitvcs.lib.decorators import timeit

import rabbitvcs.util.vcs
import rabbitvcs.lib.vcs.svn

from rabbitvcs.services.statuscache import make_summary, is_under_dir, \
                                            is_directly_under_dir, \
                                            status_calculating, \
                                            status_unknown, MAX_CACHE_SIZE \

# FIXME: debug
from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.services.statuscache")

import time

class StatusCache():
    #: The queue will be populated with 4-ples of
    #: (path, recurse, invalidate, callback).
    _paths_to_check = Queue()
    
    def __init__(self):
        self.worker = threading.Thread(target = self.status_update_loop,
                                       name = "Status cache thread")

        self.client = rabbitvcs.lib.vcs.create_vcs_instance()

        # This means that the thread will die when everything else does. If
        # there are problems, we will need to add a flag to manually kill it.
        # self.checker = StatusCheckerStub()
        
        self._alive = threading.Event()
        self._alive.set()
        
        self.checker = StatusChecker()
        self.cache = CacheManager()
        
        # self.worker.setDaemon(True)
        self.worker.start()
                
    def path_modified(self, path):
        """
        Alerts the status checker that the given path was modified. It will be
        removed from the list (but not from pending actions, since they will be
        re-checked anyway).
        """
        pass
    
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
        
        statuses = None
        
        if self.client.is_in_a_or_a_working_copy(path):
            if not invalidate:
                statuses = self.cache.get_path_statuses(path)
                
            if invalidate or (statuses is None):
                # We need to calculate the status
                statuses = {}
                statuses = status_calculating(path)
                self._paths_to_check.put((path, recurse, invalidate, summary, callback))

        else:
            statuses = status_unknown(path)
         
        if summary:
            statuses = make_summary(path, statuses)
         
        return statuses
        
    def status_update_loop(self):
        # This loop will stop when the thread is killed, which it will 
        # because it is daemonic.
        while self._alive.isSet():
            # This call will block if the Queue is empty, until something is
            # added to it. There is a better way to do this if we need to add
            # other flags to this.
            (path, recurse, invalidate, summary, callback) = self._paths_to_check.get()
            self._update_path_status(path, recurse, invalidate, summary, callback)
    
    def kill(self):
        self.cache.kill()
        self._alive.clear()
    
    def _update_path_status(self, path, recurse=False, invalidate=False, summary=False, callback=None):
        statuses = None

        # We can't trust the cache when we invalidate, because some items may
        # have been renamed/deleted, and so we will end up with orphaned items
        # in the status cache that cause inaccurate results for parent folders
        
        
        if invalidate:
            self.cache.invalidate_path(path)
        else:
            # Another status check which includes this path may have completed in
            # the meantime so let's do a sanity check.
            statuses = self.cache.get_path_statuses(path)

        if statuses is None:
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

            statuses = self.cache.add_statuses(check_results, get=True, recursive_get=recurse)
            
            self.cache.clean()
            
        # Remember: these callbacks will block THIS thread from calculating the
        # next path on the "to do" list.
        if summary:
            statuses = ({path: statuses[path]}, check_summary)
        
        if callback: callback(path, statuses)

class CacheManager():

    def __init__(self):
        
        self._request_queue = Queue(1)
        self._result_queue = Queue(1)
        
        self._worker = threading.Thread(target = self.dispatcher,
                                         name = "Cache manager thread")
        # self._worker.setDaemon(True)
        self._worker.start()
    
    def dispatcher(self):
        import cProfile
        import rabbitvcs.lib.helper
        import os.path
        profile_data_file = os.path.join(
                                rabbitvcs.lib.helper.get_home_folder(),
                                "rvcs_db.stats")
        cProfile.runctx("self._real_dispatcher()", globals(), locals(), profile_data_file)
        # self._real_dispatcher()
    
    def _real_dispatcher(self):
        sqlobject.sqlhub.processConnection = \
            sqlobject.connectionForURI('sqlite:/:memory:')

        StatusData.createTable()
        PathChildren.createTable()
        
        self._alive = True
        
        while self._alive:
            (func, args, kwargs) = self._request_queue.get()
            self._result_queue.put(func(*args, **kwargs))

    def kill(self):
        self._sync_call(self._kill)

    def _kill(self):
        self._alive = False
    
    def _sync_call(self, func, *args, **kwargs):
        self._request_queue.put((func, args, kwargs))
        return self._result_queue.get()
    
    def get_path_statuses(self, path, recurse = True):
        return self._sync_call(self._get_path_statuses, path, recurse)
    
    def _get_path_statuses(self, path, recurse):
        
        statuses = None
        entry = StatusData.selectBy(path=path).getOne(None)
        
        if entry:
        
            statuses = {}

            if recurse:    
                children = entry.get_children()
                # children_new = entry.get_children()
                
                # assert set(children) == set(children_new)
                
                for child_entry in children:
                    statuses[child_entry.path] = child_entry.status_dict()
            else:
                statuses[entry.path] = entry.status_dict()
        
        return statuses

    def invalidate_path(self, path):
        return self._sync_call(self._invalidate_path, path)

    def _invalidate_path(self, path):
        entry = StatusData.selectBy(path=path).getOne(None)
        
        if entry:
            [child.destroySelf() for child in entry.get_children()]
    
    def add_statuses(self, statuses, get=False, recursive_get=True):
        return self._sync_call(self._add_statuses, statuses, get, recursive_get)

    def _add_statuses(self, statuses, get, recursive_get):
        age = self._get_max_age() + 1
   
        for path, text_status, prop_status in statuses:
            
            entry = StatusData.selectBy(path=path).getOne(None)
                        
            if entry:
                entry.set(age=age,
                          text_status=text_status,
                          prop_status=prop_status)
            else:
                StatusData(path=path, age=age,
                           text_status=text_status,
                           prop_status=prop_status)

        self._update_children(map(lambda x: x[0], statuses))

        if get:
            return self._get_path_statuses(path, recursive_get)
    
    def _update_children(self, paths):
        for path in paths:            
            
            entry = StatusData.selectBy(path=path).getOne()
            
            for other_path in paths:
                
                if is_directly_under_dir(path, other_path):
                    child_entry = StatusData.selectBy(path=other_path).getOne()
                    
                    item = PathChildren.selectBy(parent=entry, child=child_entry).getOne(None)
                    
                    if not item:                
                        PathChildren(parent=entry, child=child_entry)
                    
                elif is_directly_under_dir(other_path, path):
                    parent_entry = StatusData.selectBy(path=other_path).getOne()

                    item = PathChildren.selectBy(parent=parent_entry, child=entry).getOne(None)
                    
                    if not item:                
                        PathChildren(parent=parent_entry, child=entry)

            paths.remove(path)
    
    def clean(self):
        return self._sync_call(self._clean)

    def _clean(self):
        """
        Tries to ensure the status cache remains under a certain size. This will
        not enforce a strict limit. The actual limit of the cache is:
            max( largest WC status tree checked in one go , MAX_CACHE_SIZE )
        """
        # We only care if the cache is bigger than the max size BUT we don't
        # want to delete the entire cache every time.
        # log.debug("Status cache size: %i" % len(self._status_tree))
        
        # log.debug("Requested clean")
        
        max_age = self._get_max_age()
        min_age = self._get_min_age()
            
        while self._get_size() > MAX_CACHE_SIZE and min_age != max_age:
            old_entries = StatusData.selectBy(age=min_age)
            num_oldpaths = old_entries.count()
            for entry in old_entries:
                entry.destroySelf()
                
            min_age = self._get_min_age()
            
            # log.debug("Removed %i paths from status cache" % num_oldpaths)
    
    def _get_size(self):
        count = StatusData.select().count()
        # log.debug("Cache size is: %i" % count)
        return count
    
    def _get_max_age(self):
        age = StatusData.select().max("age")
        
        if age is None:
            age = 0
                
        return age

    def _get_min_age(self):
        age = StatusData.select().min("age")
        
        if age is None:
            age = 0
                
        return age

class StatusData(sqlobject.SQLObject):
    
    path = sqlobject.UnicodeCol(dbEncoding="UTF-8", unique=True, notNone=True)
    age = sqlobject.IntCol()
    text_status = sqlobject.UnicodeCol(dbEncoding="UTF-8", notNone=True)
    prop_status = sqlobject.UnicodeCol(dbEncoding="UTF-8", notNone=True)
    
    children = sqlobject.MultipleJoin('PathChildren', joinColumn="parent_id")
    
    def status_dict(self):
        return {"text_status" : self.text_status,
                "prop_status" : self.prop_status}
    
    def get_children_old(self):
        child_entries = StatusData.select(
                            (StatusData.q.path==self.path)
                            | (StatusData.q.path.startswith(self.path + "/")))
        return child_entries

    
    def get_children(self):
        child_list = [self]
                
        for entry in self.children:
            child_list.extend(entry.child.get_children())
        
        return child_list
        
class PathChildren(sqlobject.SQLObject):
    
    parent = sqlobject.ForeignKey('StatusData', cascade=True)
    child = sqlobject.ForeignKey('StatusData', cascade=True)
    
#    Person.sqlmeta.addJoin(MultipleJoin('PathChildren',
#                        joinMethodName='children'))

    
if __name__ == "__main__":
    
    from pprint import pformat
    
    paths = [
        "/foo",
        "/foo/bar",
        "/foo/bar/one.txt",
        "/foo/bar/two.txt",
        "/foo/bar/baz",
        "/foo/bar/baz/one.txt",
        "/foo/bam.txt",
        "/foo/baz",
        "/foo/baz/blah",
        "/foo/baz/blarg"]

    paths_later = [
        "/foo",
        "/foo/bar",
        "/foo/bar/one.txt",
        "/foo/bar/two.txt",
        "/foo/bar/three.txt",
        "/foo/bar/baz",
        "/foo/bar/baz/four.txt"]
    
    sqlobject.sqlhub.processConnection = \
    sqlobject.connectionForURI('sqlite:/:memory:')

    StatusData.createTable()
    PathChildren.createTable()
    
    for path in paths:
        parent = StatusData(path=path, age=1, text_status="testing", prop_status="testing")

    for path in paths:
        entry = StatusData.selectBy(path=path).getOne()
        for other_path in paths:
            if is_directly_under_dir(path, other_path):
                child_entry = StatusData.selectBy(path=other_path).getOne()
                PathChildren(parent=entry, child=child_entry)
        
    for path in paths_later:
        parent = StatusData.selectBy(path=path).getOne(None)
        if parent:
            parent.set(age=2, text_status="updated", prop_status="updated")
        else:
            parent = StatusData(path=path, age=2, text_status="testing_2", prop_status="testing_2")

    for path in paths_later:
        entry = StatusData.selectBy(path=path).getOne()
        for other_path in paths_later:
            if is_directly_under_dir(path, other_path):
                child_entry = StatusData.selectBy(path=other_path).getOne()
                
                item = PathChildren.selectBy(parent=entry, child=child_entry).getOne(None)
                
                if not item:                
                    PathChildren(parent=entry, child=child_entry)
    
    print "All:"
    print pformat(list(StatusData.select()))
    print "----\n"
    
    print "Parent:"
    parent = StatusData.selectBy(path = "/foo/bar").getOne()
    print parent
    print "----\n"
    
    print "Children (old):"
    children_old = parent.get_children_old()
    print pformat(list(children_old))
    print "----\n"
    
    print "Children (new):"
    children_new = parent.get_children()
    print pformat(list(children_new))

    assert set(children_old) == set(children_new)
    
    print "Child entries 1:"
    child_entries = PathChildren.select()
    print pformat(list(child_entries))
    print "----\n"
    
    StatusData.selectBy(path="/foo/bar").getOne().destroySelf()
    
    print "Child entries 2:"
    child_entries = PathChildren.select()
    print pformat(list(child_entries))
    print "----\n"
