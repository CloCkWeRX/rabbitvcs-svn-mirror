#
# This is an extension to the Nautilus file manager to allow better 
# integration with the Subversion source control system.
# 
# Copyright (C) 2006-2008 by Jason Field <jason@jasonfield.com>
# Copyright (C) 2007-2008 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2008-2008 by Adam Plumb <adamplumb@gmail.com>
# 
# NautilusSvn is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# NautilusSvn is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with NautilusSvn;  If not, see <http://www.gnu.org/licenses/>.
#

import os.path
from os.path import isdir, isfile, dirname
from time import time

import pysvn
from pyinotify import WatchManager, Notifier, ThreadedNotifier, EventsCodes, ProcessEvent

from nautilussvn.lib.vcs.svn import SVN
from nautilussvn.lib.log import Log

log = Log("nautilussvn.lib.vcs.svn.status_monitor")

class StatusMonitor:
    """
    
    The C{StatusMonitor} is basically a replacement for the currently limited 
    C{update_file_info} function. 
    
    What C{StatusMonitor} does:
    
      - When somebody adds a watch and if there's not already a watch for this 
        item it will add one.
    
      - Use inotify to keep track of modifications of any watched items
        (we actually only care about modifications not creations and deletions)
        
      - Either on request, or when something interesting happens, it checks
        the status for an item which means:
        
          - See C{status) for exactly what a status check means.
    
    UML sequence diagram depicting how the StatusMonitor is used::

        +---------------+          +-----------------+         
        |  NautilusSVN  |          |  StatusMonitor  |         
        +---------------+          +-----------------+         
               |                            |
               |   new(self.cb_status)      |
               |--------------------------->|
               |                            |
               |     add_watch(path)        |
               |--------------------------->|
               |                            |
               |        status(path)        |
               |--------------------------->|
               |                            |
               |  cb_status(path, status)   |
               |<---------------------------|
               |                            |
               |---+                        |
               |   | set_emblem_by_status(path, status)
               |<--+                        |
               |                            |

    
    """
    
    #: A set of statuses which count as modified in TortoiseSVN emblem speak.
    MODIFIED_STATUSES = [
        pysvn.wc_status_kind.added,
        pysvn.wc_status_kind.deleted,
        pysvn.wc_status_kind.replaced,
        pysvn.wc_status_kind.modified,
        pysvn.wc_status_kind.missing
    ]
    
    #: A dictionary to keep track of the paths we're watching.
    #: 
    #: It looks like:::
    #:
    #:     watches = {
    #:         # Always None because we just want to check if a watch has been set
    #:         "/foo/bar/baz": None
    #:     }
    #:     
    watches = {}
    
    #: A dictionary to keep track of the statuses for paths so we don't
    #: block the Nautilus extension.
    last_status_cache = {}
    
    #: The mask for the inotify events we're interested in.
    #: TODO: understand how masking works
    #: TODO: maybe we should just analyze VCSProcessEvent and determine this 
    #: dynamically because one might tend to forgot to update these
    mask = EventsCodes.IN_MODIFY | EventsCodes.IN_MOVED_TO | EventsCodes.IN_CREATE
    
    class VCSProcessEvent(ProcessEvent):
        """
        
        Our processing class for inotify events.
        
        """
        
        def __init__(self, status_monitor):
            self.status_monitor = status_monitor
        
        def process(self, event):
            path = event.path
            if event.name: path = os.path.join(path, event.name)
            
            if path.find(".svn") != -1 and not path.endswith(".svn/entries"): return
            
            # Begin debugging code
            #~ log.debug("Event %s triggered for: %s" % (event.event_name, path.rstrip(os.path.sep)))
            # End debugging code
            
            # Make sure to strip any trailing slashes because that will 
            # cause problems for the status checking
            # TODO: not 100% sure about it causing problems
            self.status_monitor.status(path.rstrip(os.path.sep), invalidate=True)
    
        def process_IN_MODIFY(self, event):
            self.process(event)
        
        def process_IN_MOVED_TO(self, event):
            # FIXME: because update_file_info isn't called when things are moved,
            # and we can't convert a path/uri to a NautilusVFSFile we can't
            # always update the emblems properly on items that are moved (our 
            # nautilusVFSFile_table points to an item that no longer exists).
            #
            # Once get_file_items() is called on an item, we once again have the 
            # NautilusVFSFile we need (happens whenever an item is selected).
            self.process(event)
            
        def process_IN_CREATE(self, event):
            # FIXME: we shouldn't be attaching watches, auto_add should handle this
            self.process(event)
    
    def __init__(self, callback):
        self.callback = callback
        
        self.watch_manager = WatchManager()
        self.notifier = ThreadedNotifier(
            self.watch_manager, self.VCSProcessEvent(self))
        self.notifier.start()
    
    def has_watch(self, path):
        return (path in self.watches)
    
    def add_watch(self, path):
        """
        Request a watch to be added for path. This function will figure out
        the best spot to add the watch (most likely a parent directory).
        """
        
        vcs_client = SVN()
        
        log.debug("StatusMonitor.add_watch() watch requested for %s" % path)
        
        path_to_check = path
        path_to_attach = None
        watch_is_already_set = False
        
        while path_to_check != "/":
            # If in /foo/bar/baz
            #                 ^
            # baz is unversioned, this will stay allow us to attach a watch and
            # keep an eye on it (for when it is added).
            if vcs_client.is_in_a_or_a_working_copy(path_to_check):
                path_to_attach = path_to_check
            
            if path_to_check in self.watches:
                watch_is_already_set = True
                break;
                
            path_to_check = os.path.split(path_to_check)[0]
        
        if not watch_is_already_set and path_to_attach:
            log.debug("StatusMonitor.add_watch() added watch for %s" % path_to_attach)
            self.watch_manager.add_watch(path_to_attach, self.mask, rec=True, auto_add=True)
            self.watches[path_to_attach] = None # don't need a value
        
        # Make sure we also attach watches for the path itself
        if (not path in self.watches and
                vcs_client.is_in_a_or_a_working_copy(path)):
            self.watches[path] = None
        
    def status(self, path, invalidate=False, bypass=False):
        """
        
        TODO: This function is really quite unmaintainable.
        
        This function doesn't return anything but calls the callback supplied
        to C{StatusMonitor} by the caller.
        
        @type   path: string
        @param  path: The path for which to check the status.
        
        @type   invalidate: boolean
        @param  invalidate: Whether or not the cache should be bypassed.
        """
        
        log.debug("StatusMonitor.status() called for %s with %s" % (path, invalidate))
        
        vcs_client = SVN()
        
        if not invalidate:
            # Temporary hack, if the working copy didn't change we don't
            # have to do all the stuff we do below (go all the way up
            # the tree and all). 
            status = vcs_client.status_with_cache(path, invalidate=invalidate, recurse=False)[-1]
            text_status = self.get_text_status(vcs_client, path, status)
            
            # If status is the same as last time, don't run callback
            if not bypass:
                if (path in self.last_status_cache and
                        self.last_status_cache[path] == text_status):
                    return
            self.last_status_cache[path] = text_status
            self.callback(path, text_status)
        else:
            # Doing a status check top-down (starting from the working copy)
            # is a better idea than doing it bottom-up. So figure out what
            # working copy this path belongs to first of all. 
            # FIXME: this won't work when you have different working copies
            # contained in eachother.
            path_to_check = path
            working_copy_path = None
            while path_to_check != "/":
                if vcs_client.is_working_copy(path_to_check):
                    working_copy_path = path_to_check
                path_to_check = os.path.split(path_to_check)[0]

            if working_copy_path:
                # Do a recursive status check (this should be relatively fast on
                # consecutive checks).
                statuses = vcs_client.status_with_cache(working_copy_path, invalidate=invalidate)
                
                # Go through all the statuses and set the correct state
                for status in statuses:
                    current_path = os.path.join(working_copy_path, status.data["path"])
                    
                    # If we don't have a watch Nautilus doesn't know about it
                    # and we're not interested.
                    # FIXME: find out a way to break out instead of continuing
                    if not self.has_watch(current_path): continue
                    text_status = self.get_text_status(vcs_client, current_path, status)
                    if not bypass:
                        if (current_path in self.last_status_cache and
                                self.last_status_cache[current_path] == text_status):
                            continue
                    
                    self.last_status_cache[current_path] = text_status
                    self.callback(current_path, text_status)
            
    def get_text_status(self, vcs_client, path, status):
        if isdir(path):
            # TODO: shouldn't conflicted/obstructed go before these?
            if status.data["text_status"] in [
                    SVN.STATUS["added"],
                    SVN.STATUS["modified"],
                    SVN.STATUS["deleted"]
                ]:
                return SVN.STATUS_REVERSE[status.data["text_status"]]
            
            # Verify the status of the children
            sub_statuses = vcs_client.status_with_cache(path, invalidate=False)
            sub_text_statuses = set([sub_status.data["text_status"] 
                for sub_status in sub_statuses])
            
            if SVN.STATUS["conflicted"] in sub_text_statuses:
                return "conflicted"
            
            if SVN.STATUS["obstructed"] in sub_text_statuses:
                return "obstructed"
                
            # A directory should have a modified status when any of its children
            # have a certain status (see modified_statuses above). Jason thought up 
            # of a nifty way to do this by using sets and the bitwise AND operator (&).
            if len(set(self.MODIFIED_STATUSES) & sub_text_statuses):
                return "modified"
        
        # If we're not a directory we end up here.
        return SVN.STATUS_REVERSE[status.data["text_status"]]
