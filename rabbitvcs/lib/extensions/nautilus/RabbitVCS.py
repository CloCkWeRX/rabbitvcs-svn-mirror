#
# This is an extension to the Nautilus file manager to allow better 
# integration with the Subversion source control system.
# 
# Copyright (C) 2006-2008 by Jason Field <jason@jasonfield.com>
# Copyright (C) 2007-2008 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2008-2008 by Adam Plumb <adamplumb@gmail.com>
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

Our module for everything related to the Nautilus extension.
  
"""

from __future__ import with_statement
import copy
import os.path
from os.path import isdir, isfile, realpath, basename
import datetime
import threading

import gnomevfs
import nautilus
import pysvn
import gobject
import gtk

from rabbitvcs.lib.vcs.svn import SVN

from rabbitvcs.util.vcs import *
from rabbitvcs.lib.helper import launch_ui_window, launch_diff_tool
from rabbitvcs.lib.helper import get_file_extension, get_common_directory
from rabbitvcs.lib.helper import pretty_timedelta
from rabbitvcs.lib.decorators import timeit, disable

from rabbitvcs.lib.log import Log, reload_log_settings
log = Log("rabbitvcs.lib.extensions.nautilus.RabbitVCS")

from rabbitvcs import gettext
_ = gettext.gettext

from rabbitvcs.lib.settings import SettingsManager
settings = SettingsManager()

import rabbitvcs.services.service
from rabbitvcs.services.cacheservice import StatusCacheStub as StatusCache

class RabbitVCS(nautilus.InfoProvider, nautilus.MenuProvider, nautilus.ColumnProvider):
    """ 
    This is the main class that implements all of our awesome features.
    
    """
    
    #: Maps statuses to emblems.
    #: TODO: should probably be possible to create this dynamically
    EMBLEMS = {
        "added" :       "rabbitvcs-added",
        "deleted":      "rabbitvcs-deleted",
        "removed":      "rabbitvcs-deleted",
        "modified":     "rabbitvcs-modified",
        "conflicted":   "rabbitvcs-conflicted",
        "missing":      "rabbitvcs-conflicted",
        "normal":       "rabbitvcs-normal",
        "clean":        "rabbitvcs-normal",
        "ignored":      "rabbitvcs-ignored",
        "locked":       "rabbitvcs-locked",
        "read_only":    "rabbitvcs-read_only",
        "obstructed":   "rabbitvcs-obstructed",
        "incomplete":   "rabbitvcs-incomplete",
        "unversioned":  "rabbitvcs-unversioned",
        "unknown":      "rabbitvcs-unknown",
        "calculating":  "rabbitvcs-calculating",
        "error":        "rabbitvcs-error"
    }
    
    #: A list of statuses which count as modified (for a directory) in 
    #: TortoiseSVN emblem speak.
    MODIFIED_STATUSES = [
        SVN.STATUS["added"],
        SVN.STATUS["deleted"],
        SVN.STATUS["replaced"],
        SVN.STATUS["modified"],
        SVN.STATUS["missing"]
    ]
    
    MODIFIED_TEXT_STATUSES = [
        "added", 
        "deleted",
        "replaced",
        "modified",
        "missing"
    ]
    
    #: This is our lookup table for C{NautilusVFSFile}s which we need for attaching
    #: emblems. This is mostly a workaround for not being able to turn a path/uri
    #: into a C{NautilusVFSFile}. It looks like:::
    #: 
    #:     nautilusVFSFile_table = {
    #:        "/foo/bar/baz": <NautilusVFSFile>
    #:     
    #:     }
    #: 
    #: Keeping track of C{NautilusVFSFile}s is a little bit complicated because
    #: when an item is moved (renamed) C{update_file_info} doesn't get called. So
    #: we also add C{NautilusVFSFile}s to this table from C{get_file_items} etc.
    nautilusVFSFile_table = {}
    
    #: Without an actual status monitor it's not possible to just keep
    #: track of stuff that happens (e.g. a commit happens, files are added,
    #: such things). So at the moment we just add all interesting items
    #: to this list.
    monitored_files = []
    
    #: This is in case we want to permanently enable invalidation of the status
    #: checker info. We put a path here before we invalidate the item, so that
    #: we don't enter an endless loop when updating the status.
    #: The callback should acquire this lock when pushing the path to this.
    always_invalidate = True
    
    #: When we get the statuses from the callback, but them here for further
    #: use. There is a possible memory problem here if we put a lot of data in
    #: this - even when it's removed, Python may not release the memory. I do
    #: not know this for sure.
    #: This is of the form: [("path/to", {...status dict...}), ...]
    paths_from_callback = []
    
    
    #: It appears that the "update_file_info" call that is triggered by the
    #: "invalidate_extension_info" in the callback function happens
    #: synchronously (ie. in the same thread). However, given the nature of the
    #: python/nautilus extensions module, I'm not sure how reliable this is.
    #: It's certainly supported by debugging statements, but maybe it will
    #: change in the future? Who knows. This should work for both the current
    #: situation, and the possibility that they are asynchronous.
    callback_paths_lock = threading.RLock()
    
    #: A list of statuses that we want to keep track of for when a process
    #: might have done something.
    STATUSES_TO_MONITOR = copy.copy(MODIFIED_TEXT_STATUSES)
    STATUSES_TO_MONITOR.extend([
        "unversioned",
        # When doing a checkout Nautilus will notice a directory being
        # added and call update_file_info, but at that stage the
        # checkout likely hasn't completed yet and the status will be:
        "incomplete"
    ])
    
    def __init__(self):
        threading.currentThread().setName("RabbitVCS extension thread")
        
        # Create a global client we can use to do VCS related stuff
        self.vcs_client = SVN()
        
        self.status_checker = StatusCache(self.cb_status)
        
    def get_columns(self):
        """
        Return all the columns we support.
        
        """
        
        return (
            nautilus.Column(
                "RabbitVCS::status_column",
                "status",
                _("Status"),
                ""
            ),
            nautilus.Column(
                "RabbitVCS::revision_column",
                "revision",
                _("Revision"),
                ""
            ),
            nautilus.Column(
                "RabbitVCS::url_column",
                "url",
                _("URL"),
                ""
            ),
            nautilus.Column(
                "RabbitVCS::author_column",
                "author",
                _("Author"),
                ""
            ),
            nautilus.Column(
                "RabbitVCS::age_column",
                "age",
                _("Age"),
                ""
            )
        )
    
    #~ @timeit
    def update_file_info(self, item):
        """
        
        C{update_file_info} is called only when:
        
          - When you enter a directory (once for each item but only when the
            item was modified since the last time it was listed)
          - When you refresh (once for each item visible)
          - When an item viewable from the current window is created or modified
          
        This is insufficient for our purpose because:
        
          - You're not notified about items you don't see (which is needed to 
            keep the emblem for the directories above the item up-to-date)
        
        @type   item: NautilusVFSFile
        @param  item: 
        
        """
        if not self.valid_uri(item.get_uri()): return
        path = realpath(unicode(gnomevfs.get_local_path_from_uri(item.get_uri()), "utf-8"))
        
        # log.debug("update_file_info() called for %s" % path)
        
        # Always replace the item in the table with the one we receive, because
        # for example if an item is deleted and recreated the NautilusVFSFile
        # we had before will be invalid (think pointers and such).
        self.nautilusVFSFile_table[path] = item
        
        # This check should be pretty obvious :-)
        # TODO: how come the statuses for a few directories are incorrect
        # when we remove this line (detected as working copies, even though
        # they are not)? That shouldn't happen.
        is_in_a_or_a_working_copy = self.vcs_client.is_in_a_or_a_working_copy(path)
        if not is_in_a_or_a_working_copy: return
        
        # Do our magic...
        
        # I have added extra logic in cb_status, using a list
        # (paths_from_callback) that should allow us to work around this for
        # now. But it'd be good to have an actual status monitor. 
        
        # Useful for figuring out order of calls. See "cb_status".
        # log.debug("%s: In update_status" % threading.currentThread())
        
        found = False
        
        with self.callback_paths_lock:
            
            for idx in xrange(len(self.paths_from_callback)):
                found = (str(self.paths_from_callback[idx][0]) == str(path))
                if found: break
            
            if found: # We're here because we were triggered by a callback
                (cb_path, single_status, summary) = self.paths_from_callback[idx]
                del self.paths_from_callback[idx]
        
        # Don't bother the cache if we already have the info
        
        if not found:
            (single_status, summary) = self.status_checker.check_status(path, recurse=True, summary=True, invalidate=self.always_invalidate)

        # log.debug("US Thread: %s" % threading.currentThread())
                
        # summary = get_summarized_status_both(path, statuses)
        # single_status = {path: statuses[path]}
        
#        from pprint import pformat
#        log.debug("\n\tExtension: asked for summary [%s]\n\tGot paths:\n%s" % (path, pformat(summary.keys())))
#        log.debug("\n\tExtension: asked for single [%s]\n\tGot paths:\n%s" % (path, pformat(single_status.keys())))

        # TODO: using pysvn directly because I don't like the current
        # SVN class.
        client = pysvn.Client()
        client_info = client.info(path)

        assert summary.has_key(path), "Path [%s] not in status summary!" % summary
        assert single_status.has_key(path), "Path [%s] not in single status!" % path

        # if bool(int(settings.get("general", "enable_attributes"))): self.update_columns(item, path, single_status, client_info)
        if bool(int(settings.get("general", "enable_emblems"))): self.update_status(item, path, summary, client_info)
        
    def update_columns(self, item, path, statuses, client_info):
        """
        Update the columns (attributes) for a given Nautilus item,
        filling them in with information from the version control
        server.

        """
        # log.debug("update_colums called for %s" % path)

        values = {
            "status": "",
            "revision": "",
            "url": "",
            "author": "",
            "age": ""
        }

        try:
            if client_info is None:
                # It IS possible to reach here: ignored files satisfy the "is in
                # WC" condition, but aren't themselves versioned!
                log.debug("Unversioned file in WC: %s" % path)
                values["status"] = SVN.STATUS_REVERSE[pysvn.wc_status_kind.unversioned]
            else:
                info = client_info.data
                # FIXME: replace
                # status = client.status(path, recurse=False)[-1].data                
                status = statuses[path]
    
                values["status"] = status["text_status"]

                # If the text status shows it isn't modified, but the properties
                # DO, let them take priority.
                if status["text_status"] not in RabbitVCS.MODIFIED_TEXT_STATUSES \
                  and status["prop_status"] in RabbitVCS.MODIFIED_TEXT_STATUSES:
                    values["status"] = status["prop_status"]

                values["revision"] = str(info["commit_revision"].number)
                values["url"] = str(info["url"])
                values["author"] = str(info["commit_author"])
                values["age"] = str(
                    pretty_timedelta(
                        datetime.datetime.fromtimestamp(info["commit_time"]),
                        datetime.datetime.now()
                    )
                )
        except:
            log.exception()

        for key, value in values.items():
            item.add_string_attribute(key, value)

    
    def update_status(self, item, path, summary, client_info):
        # If we are able to set an emblem that means we have a local status
        # available. The StatusMonitor will keep us up-to-date through the 
        # C{cb_status} callback.
        # Warning! If you use invalidate=True here, it will set up an endless
        # loop:
        # 1. Update requests status (inv=True)
        # 2. Status checker returns "calculating"
        # 3. Status checker calculates status, calls callback
        # 4. Callback triggers update
                
        # Path == first index or last for old system?
        if summary[path]["text_status"] == "calculating":
            item.add_emblem(self.EMBLEMS["calculating"])
        else:
            single_status = get_single_status(summary[path])
            if single_status in self.EMBLEMS:
                item.add_emblem(self.EMBLEMS[single_status])
        
    #~ @disable
    # @timeit
    def get_file_items(self, window, items):
        """
        Menu activated with items selected. Nautilus also calls this function
        when rendering submenus, even though this is not needed since the entire
        menu has already been returned.
        
        Note that calling C{nautilusVFSFile.invalidate_extension_info()} will 
        also cause get_file_items to be called.
        
        @type   window: NautilusNavigationWindow
        @param  window:
        
        @type   items:  list of NautilusVFSFile
        @param  items:
        
        @rtype:         list of MenuItems
        @return:        The context menu entries to add to the menu.
        
        """
        
        paths = []
        for item in items:
            if self.valid_uri(item.get_uri()):
                path = realpath(unicode(gnomevfs.get_local_path_from_uri(item.get_uri()), "utf-8"))
                paths.append(path)
                self.nautilusVFSFile_table[path] = item

        if len(paths) == 0: return []
        
        return MainContextMenu(window.get_data("base_dir"), paths, self).construct_menu()
        
    
    #~ @disable
    @timeit
    def get_background_items(self, window, item):
        """
        Menu activated on entering a directory. Builds context menu for File
        menu and for window background.
        
        @type   window: NautilusNavigationWindow
        @param  window:
        
        @type   item:   NautilusVFSFile
        @param  item:
        
        @rtype:         list of MenuItems
        @return:        The context menu entries to add to the menu.
        
        """
        
        if not self.valid_uri(item.get_uri()): return
        path = realpath(unicode(gnomevfs.get_local_path_from_uri(item.get_uri()), "utf-8"))
        self.nautilusVFSFile_table[path] = item
        
        # log.debug("get_background_items() called")
        
        window.set_data("base_dir", path)
        
        return MainContextMenu(path, [path], self).construct_menu()
    
    #
    # Helper functions
    #
    
    def valid_uri(self, uri):
        """
        Check whether or not it's a good idea to have RabbitVCS do
        its magic for this URI. Some examples of URI schemes:
        
        x-nautilus-desktop:/// # e.g. mounted devices on the desktop
        
        """
        
        if not uri.startswith("file://"): return False
        
        return True
    
    #
    # Some methods to help with keeping emblems up-to-date
    #
    
    def rescan_after_process_exit(self, proc, paths):
        """ 
        Rescans all of the items on our C{monitored_files} list after the
        process specified by C{proc} completes. Also checks the paths
        that were passed.
        
        TODO: the monitored_files list could grow quite large if somebody
        browses a lot of working copies. It probably won't affect anything
        (most importantly performance) all that negatively.
        
        """
        
        def do_check():
            # We'll check the paths first (these were the paths that
            # were originally passed along to the context menu). 
            #
            # This is needed among other things for:
            #
            #   - When a directory is normal and you add files inside it
            #
            for path in paths:
                statuses = self.status_checker.check_status(path, recurse=True, invalidate=True)
            
        self.execute_after_process_exit(proc, do_check)
        
    def execute_after_process_exit(self, proc, func = None):

        def is_process_still_alive():
            log.debug("is_process_still_alive() for pid: %i" % proc.pid)
            # First we need to see if the commit process is still running

            retval = proc.poll()
            
            log.debug("%s" % retval)
            
            still_going = (retval is None)

            if not still_going and callable(func):
                func()
            
            return still_going

        # Add our callback function on a 1 second timeout
        gobject.timeout_add_seconds(1, is_process_still_alive)
        
    # 
    # Some other methods
    # 
    
    def reload_settings(self, proc):
        """
        Used to re-load settings after the settings dialog has been closed.
        
        FIXME: This probably doesn't belong here, ideally the settings manager
        does this itself and make sure everything is reloaded properly 
        after the settings dialogs saves.
        """
    
        def do_reload_settings():
            globals()["settings"] = SettingsManager()
            globals()["log"] = reload_log_settings()("rabbitvcs.lib.extensions.nautilus")
            log.debug("Re-scanning settings")
            
        self.execute_after_process_exit(proc, do_reload_settings)
        
        
    # 
    # Callbacks
    # 
    
    def cb_status(self, path, statuses):
        """
        This is the callback that C{StatusMonitor} calls. 
        
        @type   path:   string
        @param  path:   The path of the item something interesting happened to.
        
        @type   statuses: list of tuples of (path, status)
        @param  statuses: The statuses (we do nothing with this now)
        """
        # log.debug("CB Thread: %s" % threading.currentThread())
        if path in self.nautilusVFSFile_table:
            item = self.nautilusVFSFile_table[path]
            # We need to invalidate the extension info for only one reason:
            #
            # - Invalidating the extension info will cause Nautilus to remove all
            #   temporary emblems we applied so we don't have overlay problems
            #   (with ourselves, we'd still have some with other extensions).
            #
            # After invalidating C{update_file_info} applies the correct emblem.
            
            # Since invalidation triggers an "update_file_info" call, we can
            # tell it NOT to invalidate the status checker path.
            with self.callback_paths_lock:
                from pprint import pformat
                (single, summary) = statuses
                self.paths_from_callback.append((path, single, summary))
                # These are useful to establish whether the "update_status" call
                # happens INSIDE this next call, or later, or in another thread. 
                # log.debug("%s: Invalidating..." % threading.currentThread())
                item.invalidate_extension_info()
                # log.debug("%s: Done invalidate call." % threading.currentThread())
        else:
            log.debug("Path [%s] not found in file table")
        
class MainContextMenu:
    """
    
    A class that represents our context menu.
    
    See: http://code.google.com/p/rabbitvcs/wiki/ContextMenuStructure
    
    FIXME: There's currently a problem with the order in which menu items 
    appear, even though a list such as C{[<Update>, <Commit>, <RabbitVCS>]} 
    would be returned it might end up as C{[<RabbitVCS>, <Update>, <Commit>]}.
    
    """
    
    SEPARATOR = u'\u2015' * 10
    
    def __init__(self, base_dir, paths, rabbitvcs_extension):
        self.base_dir = base_dir
        self.paths = paths
        self.rabbitvcs_extension = rabbitvcs_extension
        self.vcs_client = SVN()
        
        self.status_checker = StatusCache()
        
        self.statuses = {}
        for path in self.paths:
            self.statuses.update(self.status_checker.check_status(path, recurse=True, callback=False))
        self.text_statuses = [self.statuses[key]["text_status"] for key in self.statuses.keys()]
        self.prop_statuses = [self.statuses[key]["prop_status"] for key in self.statuses.keys()]
        
        self.path_dict = {}
        self.path_dict["length"] = len(paths)
        
        checks = {
            "is_dir"                        : isdir,
            "is_file"                       : isfile,
            "is_working_copy"               : is_working_copy,
            "is_in_a_or_a_working_copy"     : is_in_a_or_a_working_copy,
            "is_versioned"                  : is_versioned,
            "is_normal"                     : lambda path: self.statuses[path]["text_status"] == "normal" and self.statuses[path]["prop_status"] == "normal",
            "is_added"                      : lambda path: self.statuses[path]["text_status"] == "added",
            "is_modified"                   : lambda path: self.statuses[path]["text_status"] == "modified" or self.statuses[path]["prop_status"] == "modified",
            "is_deleted"                    : lambda path: self.statuses[path]["text_status"] == "deleted",
            "is_ignored"                    : lambda path: self.statuses[path]["text_status"] == "ignored",
            "is_locked"                     : lambda path: self.statuses[path]["text_status"] == "locked",
            "is_missing"                    : lambda path: self.statuses[path]["text_status"] == "missing",
            "is_conflicted"                 : lambda path: self.statuses[path]["text_status"] == "conflicted",
            "is_obstructed"                 : lambda path: self.statuses[path]["text_status"] == "obstructed",
            "has_unversioned"               : lambda path: "unversioned" in self.text_statuses,
            "has_added"                     : lambda path: "added" in self.text_statuses,
            "has_modified"                  : lambda path: "modified" in self.text_statuses or "modified" in self.prop_statuses,
            "has_deleted"                   : lambda path: "deleted" in self.text_statuses,
            "has_ignored"                   : lambda path: "ignored" in self.text_statuses,
            "has_locked"                    : lambda path: "locked" in self.text_statuses,
            "has_missing"                   : lambda path: "missing" in self.text_statuses,
            "has_conflicted"                : lambda path: "conflicted" in self.text_statuses,
            "has_obstructed"                : lambda path: "obstructed" in self.text_statuses
        }

        # Each path gets tested for each check
        # If a check has returned True for any path, skip it for remaining paths
        for path in paths:
            for key, func in checks.items():
                if key not in self.path_dict or self.path_dict[key] is not True:
                    self.path_dict[key] = func(path)
        
    def construct_menu(self):
        """
        
        This function is really only used to contain the menu defintion. The
        actual menu is build using C{create_menu_from_definition}.
        
        @rtype:     list of MenuItems
        @return:    A list of MenuItems representing the context menu.
        """
        
        # The following dictionary defines the complete contextmenu
        menu_definition = [
            {
                "identifier": "RabbitVCS::Debug",
                "label": _("Debug"),
                "tooltip": "",
                "icon": "rabbitvcs-monkey",
                "signals": {
                    "activate": {
                        "callback": None,
                        "args": None
                    }
                },
                "condition": (lambda: settings.get("general", "show_debug")),
                "submenus": [
                    {
                        "identifier": "RabbitVCS::Bugs",
                        "label": _("Bugs"),
                        "tooltip": "",
                        "icon": "rabbitvcs-bug",
                        "signals": {
                            "activate": {
                                "callback": None,
                                "args": None
                            }
                        },
                        "condition": (lambda: True),
                        "submenus": [

                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Debug_Shell",
                        "label": _("Open Shell"),
                        "tooltip": "",
                        "icon": "gnome-terminal",
                        "signals": {
                            "activate": {
                                "callback": self.callback_debug_shell,
                                "args": None
                            }
                        },
                        "condition": (lambda: True),
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Refresh_Status",
                        "label": _("Refresh Status"),
                        "tooltip": "",
                        "icon": "rabbitvcs-refresh",
                        "signals": {
                            "activate": {
                                "callback": self.callback_refresh_status,
                                "args": None
                            }
                        },
                        "condition": (lambda: True),
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Debug_Revert",
                        "label": _("Debug Revert"),
                        "tooltip": _("Reverts everything it sees"),
                        "icon": "rabbitvcs-revert",
                        "signals": {
                            "activate": {
                                "callback": self.callback_debug_revert,
                                "args": None
                            }
                        },
                        "condition": (lambda: True),
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Debug_Invalidate",
                        "label": _("Invalidate"),
                        "tooltip": _("Force an invalidate_extension_info() call"),
                        "icon": "rabbitvcs-clear",
                        "signals": {
                            "activate": {
                                "callback": self.callback_debug_invalidate,
                                "args": None
                            }
                        },
                        "condition": (lambda: True),
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Debug_Add_Emblem",
                        "label": _("Add Emblem"),
                        "tooltip": _("Add an emblem"),
                        "icon": "rabbitvcs-emblems",
                        "signals": {
                            "activate": {
                                "callback": self.callback_debug_add_emblem,
                                "args": None
                            }
                        },
                        "condition": (lambda: True),
                        "submenus": [
                            
                        ]
                    },
                ]
            },
            {
                "identifier": "RabbitVCS::Checkout",
                "label": _("Checkout"),
                "tooltip": _("Check out a working copy"),
                "icon": "rabbitvcs-checkout",
                "signals": {
                    "activate": {
                        "callback": self.callback_checkout,
                        "args": None
                    }
                }, 
                "condition": self.condition_checkout,
                "submenus": [
                    
                ]
            },
            {
                "identifier": "RabbitVCS::Update",
                "label": _("Update"),
                "tooltip": _("Update a working copy"),
                "icon": "rabbitvcs-update",
                "signals": {
                    "activate": {
                        "callback": self.callback_update,
                        "args": None
                    }
                }, 
                "condition": self.condition_update,
                "submenus": [
                    
                ]
            },
            {
                "identifier": "RabbitVCS::Commit",
                "label": _("Commit"),
                "tooltip": _("Commit modifications to the repository"),
                "icon": "rabbitvcs-commit",
                "signals": {
                    "activate": {
                        "callback": self.callback_commit,
                        "args": None
                    }
                }, 
                "condition": self.condition_commit,
                "submenus": [
                    
                ]
            },
            {
                "identifier": "RabbitVCS::RabbitVCS",
                "label": _("RabbitVCS"),
                "tooltip": "",
                "icon": "rabbitvcs",
                "signals": {
                    "activate": {
                        "callback": None,
                        "args": None
                    }
                }, 
                "condition": (lambda: True),
                "submenus": [
                    {
                        "identifier": "RabbitVCS::Diff",
                        "label": _("View Diff"),
                        "tooltip": _("View the modifications made to a file"),
                        "icon": "rabbitvcs-diff",
                        "signals": {
                            "activate": {
                                "callback": self.callback_diff,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_diff,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Show_Log",
                        "label": _("Show Log"),
                        "tooltip": _("Show a file's log information"),
                        "icon": "rabbitvcs-show_log",
                        "signals": {
                            "activate": {
                                "callback": self.callback_show_log,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_show_log,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Separator1",
                        "label": self.SEPARATOR,
                        "tooltip": "",
                        "icon": None,
                        "signals": {}, 
                        "condition": (lambda: True),
                        "submenus": []
                    },
                    {
                        "identifier": "RabbitVCS::Add",
                        "label": _("Add"),
                        "tooltip": _("Schedule an item to be added to the repository"),
                        "icon": "rabbitvcs-add",
                        "signals": {
                            "activate": {
                                "callback": self.callback_add,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_add,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::AddToIgnoreList",
                        "label": _("Add to ignore list"),
                        "tooltip": "",
                        "icon": None,
                        "signals": {}, 
                        "condition": self.condition_add_to_ignore_list,
                        "submenus": [
                            {
                                "identifier": "RabbitVCS::AddToIgnoreFile",
                                "label": basename(self.paths[0]),
                                "tooltip": _("Ignore an item"),
                                "icon": None,
                                "signals": {
                                    "activate": {
                                        "callback": self.callback_ignore_filename,
                                        "args": None
                                    }
                                }, 
                                "condition": (lambda: True),
                                "submenus": [
                                ]
                            },
                            {
                                "identifier": "RabbitVCS::AddToIgnoreExt",
                                "label": "*%s" % get_file_extension(self.paths[0]),
                                "tooltip": _("Ignore all files with this extension"),
                                "icon": None,
                                "signals": {
                                    "activate": {
                                        "callback": self.callback_ignore_ext,
                                        "args": None
                                    }
                                }, 
                                "condition": self.condition_ignore_ext,
                                "submenus": [
                                ]
                            }
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::SeparatorAdd",
                        "label": self.SEPARATOR,
                        "tooltip": "",
                        "icon": None,
                        "signals": {}, 
                        "condition": (lambda: True),
                        "submenus": []
                    },
                    {
                        "identifier": "RabbitVCS::UpdateToRevision",
                        "label": _("Update to revision..."),
                        "tooltip": _("Update a file to a specific revision"),
                        "icon": "rabbitvcs-update",
                        "signals": {
                            "activate": {
                                "callback": self.callback_updateto,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_update_to,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Rename",
                        "label": _("Rename..."),
                        "tooltip": _("Schedule an item to be renamed on the repository"),
                        "icon": "rabbitvcs-rename",
                        "signals": {
                            "activate": {
                                "callback": self.callback_rename,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_rename,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Delete",
                        "label": _("Delete"),
                        "tooltip": _("Schedule an item to be deleted from the repository"),
                        "icon": "rabbitvcs-delete",
                        "signals": {
                            "activate": {
                                "callback": self.callback_delete,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_delete,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Revert",
                        "label": _("Revert"),
                        "tooltip": _("Revert an item to its unmodified state"),
                        "icon": "rabbitvcs-revert",
                        "signals": {
                            "activate": {
                                "callback": self.callback_revert,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_revert,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Resolve",
                        "label": _("Resolve"),
                        "tooltip": _("Mark a conflicted item as resolved"),
                        "icon": "rabbitvcs-resolve",
                        "signals": {
                            "activate": {
                                "callback": self.callback_resolve,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_resolve,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Relocate",
                        "label": _("Relocate..."),
                        "tooltip": _("Relocate your working copy"),
                        "icon": "rabbitvcs-relocate",
                        "signals": {
                            "activate": {
                                "callback": self.callback_relocate,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_relocate,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::GetLock",
                        "label": _("Get Lock..."),
                        "tooltip": _("Locally lock items"),
                        "icon": "rabbitvcs-lock",
                        "signals": {
                            "activate": {
                                "callback": self.callback_lock,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_lock,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Unlock",
                        "label": _("Release Lock..."),
                        "tooltip": _("Release lock on an item"),
                        "icon": "rabbitvcs-unlock",
                        "signals": {
                            "activate": {
                                "callback": self.callback_unlock,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_unlock,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Cleanup",
                        "label": _("Cleanup"),
                        "tooltip": _("Clean up working copy"),
                        "icon": "rabbitvcs-cleanup",
                        "signals": {
                            "activate": {
                                "callback": self.callback_cleanup,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_cleanup,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Separator2",
                        "label": self.SEPARATOR,
                        "tooltip": "",
                        "icon": None,
                        "signals": {}, 
                        "condition": (lambda: True),
                        "submenus": []
                    },
                    {
                        "identifier": "RabbitVCS::Export",
                        "label": _("Export"),
                        "tooltip": _("Export a working copy or repository with no versioning information"),
                        "icon": "rabbitvcs-export",
                        "signals": {
                            "activate": {
                                "callback": self.callback_export,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_export,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Create_Repository",
                        "label": _("Create Repository here"),
                        "tooltip": _("Create a repository in a folder"),
                        "icon": "rabbitvcs-run",
                        "signals": {
                            "activate": {
                                "callback": self.callback_create_repository,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_create,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Import",
                        "label": _("Import"),
                        "tooltip": _("Import an item into a repository"),
                        "icon": "rabbitvcs-import",
                        "signals": {
                            "activate": {
                                "callback": self.callback_import,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_import,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Separator3",
                        "label": self.SEPARATOR,
                        "tooltip": "",
                        "icon": None,
                        "signals": {}, 
                        "condition": (lambda: True),
                        "submenus": []
                    },
                    {
                        "identifier": "RabbitVCS::BranchTag",
                        "label": _("Branch/tag..."),
                        "tooltip": _("Copy an item to another location in the repository"),
                        "icon": "rabbitvcs-branch",
                        "signals": {
                            "activate": {
                                "callback": self.callback_branch,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_branch,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Switch",
                        "label": _("Switch..."),
                        "tooltip": _("Change the repository location of a working copy"),
                        "icon": "rabbitvcs-switch",
                        "signals": {
                            "activate": {
                                "callback": self.callback_switch,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_switch,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Merge",
                        "label": _("Merge..."),
                        "tooltip": _("A wizard with steps for merging"),
                        "icon": "rabbitvcs-merge",
                        "signals": {
                            "activate": {
                                "callback": self.callback_merge,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_merge,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Separator4",
                        "label": self.SEPARATOR,
                        "tooltip": "",
                        "icon": None,
                        "signals": {}, 
                        "condition": (lambda: True),
                        "submenus": []
                    },
                    {
                        "identifier": "RabbitVCS::Annotate",
                        "label": _("Annotate..."),
                        "tooltip": _("Annotate a file"),
                        "icon": "rabbitvcs-annotate",
                        "signals": {
                            "activate": {
                                "callback": self.callback_annotate,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_annotate,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Separator5",
                        "label": self.SEPARATOR,
                        "tooltip": "",
                        "icon": None,
                        "signals": {}, 
                        "condition": (lambda: True),
                        "submenus": []
                    },
                   {
                        "identifier": "RabbitVCS::CreatePatch",
                        "label": _("Create Patch..."),
                        "tooltip": _("Creates a unified diff file with all changes you made"),
                        "icon": "rabbitvcs-createpatch",
                        "signals": {
                            "activate": {
                                "callback": self.callback_createpatch,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_createpatch,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::ApplyPatch",
                        "label": _("Apply Patch..."),
                        "tooltip": _("Applies a unified diff file to the working copy"),
                        "icon": "rabbitvcs-applypatch",
                        "signals": {
                            "activate": {
                                "callback": self.callback_applypatch,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_applypatch,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Properties",
                        "label": _("Properties"),
                        "tooltip": _("View the properties of an item"),
                        "icon": "rabbitvcs-properties",
                        "signals": {
                            "activate": {
                                "callback": self.callback_properties,
                                "args": None
                            }
                        }, 
                        "condition": self.condition_properties,
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Separator6",
                        "label": self.SEPARATOR,
                        "tooltip": "",
                        "icon": None,
                        "signals": {
                            "activate": {
                                "callback": None,
                                "args": None
                            }
                        }, 
                        "condition": (lambda: True),
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Help",
                        "label": _("Help"),
                        "tooltip": _("View help"),
                        "icon": "rabbitvcs-help",
                        "signals": {
                            "activate": {
                                "callback": None,
                                "args": None
                            }
                        }, 
                        "condition": (lambda: False),
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::Settings",
                        "label": _("Settings"),
                        "tooltip": _("View or change RabbitVCS settings"),
                        "icon": "rabbitvcs-settings",
                        "signals": {
                            "activate": {
                                "callback": self.callback_settings,
                                "args": None
                            }
                        }, 
                        "condition": (lambda: True),
                        "submenus": [
                            
                        ]
                    },
                    {
                        "identifier": "RabbitVCS::About",
                        "label": _("About"),
                        "tooltip": _("About RabbitVCS"),
                        "icon": "rabbitvcs-about",
                        "signals": {
                            "activate": {
                                "callback": self.callback_about,
                                "args": None
                            }
                        }, 
                        "condition": (lambda: True),
                        "submenus": [
                            
                        ]
                    }
                ]
            },
        ]
        
        return self.create_menu_from_definition(menu_definition)
    
    def create_menu_from_definition(self, menu_definition):
        """
        
        Create the actual menu from a menu definiton.
        
        A single menu item definition looks like::
        
            {
                "identifier": "RabbitVCS::Identifier",
                "label": "",
                "tooltip": "",
                "icon": "",
                "signals": {
                    "activate": {
                        "callback": None,
                        "args": None
                    }
                }, 
                "condition": (lambda: True),
                "submenus": [
                    
                ]
            }
        
        @type   menu_definition:  list
        @param  menu_definition:  A list of definition items.
        
        @rtype:     list of MenuItems
        @return:    A list of MenuItems representing the context menu.
        
        """
        
        menu = []
        previous_label = None
        is_first = True
        index = 0
        length = len(menu_definition)
        
        for definition_item in menu_definition:
            is_last = (index + 1 == length)
            
            # Execute the condition associated with the definition_item
            # which will figure out whether or not to display this item.
            if not definition_item.has_key("condition") or definition_item["condition"]():
                # If the item is a separator, don't show it if this is the first
                # or last item, or if the previous item was a separator.
                if (definition_item["label"] == self.SEPARATOR and
                        (is_first or is_last or previous_label == self.SEPARATOR)):
                    index += 1
                    continue
            
                menu_item = nautilus.MenuItem(
                    definition_item["identifier"],
                    definition_item["label"],
                    definition_item["tooltip"],
                    definition_item["icon"]
                )
                
                # Making the seperator insensitive makes sure nobody
                # will click it accidently.
                if (definition_item["label"] == self.SEPARATOR): 
                  menu_item.set_property("sensitive", False)
                
                # Make sure all the signals are connected.
                for signal, value in definition_item["signals"].items():
                    if value["callback"] != None:
                        # FIXME: the adding of arguments need to be done properly
                        if "kwargs" in value:
                            menu_item.connect(signal, value["callback"], self.paths, value["kwargs"])    
                        else:
                            menu_item.connect(signal, value["callback"], self.paths)
                
                menu.append(menu_item)
                
                # The menu item above has just been added, so we can note that
                # we're no longer on the first menu item.  And we'll keep
                # track of this item so the next iteration can test if it should
                # show a separator or not
                is_first = False
                previous_label = definition_item["label"]
                
                # Since we can't just call set_submenu and run the risk of not
                # having any submenu items later (which would result in the 
                # menu item not being displayed) we have to check first.
                if definition_item.has_key("submenus"):
                    submenu = self.create_menu_from_definition(
                        definition_item["submenus"]
                    )
                    
                    if len(submenu) > 0:
                        nautilus_submenu = nautilus.Menu()
                        menu_item.set_submenu(nautilus_submenu)
                        
                        for submenu_item in submenu:
                            nautilus_submenu.append_item(submenu_item)

            index += 1
            
        return menu
    
    #
    # Conditions
    #
    
    def condition_checkout(self):
        return (self.path_dict["length"] == 1 and
                self.path_dict["is_dir"] and
                not self.path_dict["is_working_copy"])
                
    def condition_update(self):
        return (self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"] and
                not self.path_dict["is_added"])
                        
    def condition_commit(self):
        if self.path_dict["is_in_a_or_a_working_copy"]:
            if (self.path_dict["is_added"] or
                    self.path_dict["is_modified"] or
                    self.path_dict["is_deleted"] or
                    not self.path_dict["is_versioned"]):
                return True
            elif (self.path_dict["is_dir"]):
                return True
        return False
        
    def condition_diff(self):
        if self.path_dict["length"] == 2:
            return True
        elif (self.path_dict["length"] == 1 and
                self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_modified"]):
            return True        
        return False
        
    def condition_show_log(self):
        return (self.path_dict["length"] == 1 and
                self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"] and
                not self.path_dict["is_added"])
        
    def condition_add(self):
        if (self.path_dict["is_dir"] and
                self.path_dict["is_in_a_or_a_working_copy"]):
            return True
        elif (not self.path_dict["is_dir"] and
                self.path_dict["is_in_a_or_a_working_copy"] and
                not self.path_dict["is_versioned"]):
            return True
        return False
        
    def condition_add_to_ignore_list(self):
        return self.path_dict["is_versioned"]
        
    def condition_rename(self):
        return (self.path_dict["length"] == 1 and
                self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"] and
                not self.path_dict["is_added"])
        
    def condition_delete(self):
        # FIXME: This should be False for the top-level WC folder
        return self.path_dict["is_versioned"]
        
    def condition_revert(self):
        if self.path_dict["is_in_a_or_a_working_copy"]:
            if (self.path_dict["is_added"] or
                    self.path_dict["is_modified"] or
                    self.path_dict["is_deleted"]):
                return True
            else:
                if (self.path_dict["is_dir"] and
                        (self.path_dict["has_added"] or
                        self.path_dict["has_modified"] or
                        self.path_dict["has_deleted"] or
                        self.path_dict["has_missing"])):
                    return True
        return False
        
    def condition_annotate(self):
        return (self.path_dict["length"] == 1 and
                not self.path_dict["is_dir"] and
                self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"] and
                not self.path_dict["is_added"])
        
    def condition_properties(self):
        return (self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"])

    def condition_createpatch(self):
        if self.path_dict["is_in_a_or_a_working_copy"]:
            if (self.path_dict["is_added"] or
                    self.path_dict["is_modified"] or
                    self.path_dict["is_deleted"] or
                    not self.path_dict["is_versioned"]):
                return True
            elif (self.path_dict["is_dir"] and
                    (self.path_dict["has_added"] or
                    self.path_dict["has_modified"] or
                    self.path_dict["has_deleted"] or
                    self.path_dict["has_unversioned"] or
                    self.path_dict["has_missing"])):
                return True
        return False
    
    def condition_applypatch(self):
        if self.path_dict["is_in_a_or_a_working_copy"]:
            return True
        return False
    
    def condition_add_to_ignore_list(self):
        return (self.path_dict["length"] == 1 and 
                self.path_dict["is_in_a_or_a_working_copy"] and
                not self.path_dict["is_versioned"])
    
    def condition_ignore_ext(self):
        return (self.path_dict["length"] == 1 and self.path_dict["is_file"])

    def condition_lock(self):
        return self.path_dict["is_versioned"]

    def condition_branch(self):
        return self.path_dict["is_versioned"]

    def condition_relocate(self):
        return self.path_dict["is_versioned"]

    def condition_switch(self):
        return self.path_dict["is_versioned"]

    def condition_merge(self):
        return self.path_dict["is_versioned"]

    def condition_import(self):
        return (self.path_dict["length"] == 1 and
                not self.path_dict["is_in_a_or_a_working_copy"])

    def condition_export(self):
        return (self.path_dict["length"] == 1 and
                not self.path_dict["is_in_a_or_a_working_copy"])
   
    def condition_update_to(self):
        return (self.path_dict["length"] == 1 and
                self.path_dict["is_in_a_or_a_working_copy"])
    
    def condition_resolve(self):
        return (self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"] and
                self.path_dict["is_conflicted"])
            
    def condition_create(self):
        return (self.path_dict["length"] == 1 and
                not self.path_dict["is_in_a_or_a_working_copy"])

    def condition_unlock(self):
        return (self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"] and
                self.path_dict["has_locked"])

    def condition_cleanup(self):
        return self.path_dict["is_versioned"]
       
    def callback_debug_shell(self, menu_item, paths):
        """
        
        Open up an IPython shell which shares the context of the extension.
        
        See: http://ipython.scipy.org/moin/Cookbook/EmbeddingInGTK
        
        """
        import gtk
        from rabbitvcs.debug.ipython_view import IPythonView
        
        window = gtk.Window()
        window.set_size_request(750,550)
        window.set_resizable(True)
        window.set_position(gtk.WIN_POS_CENTER)
        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        ipython_view = IPythonView()
        ipython_view.updateNamespace(locals())
        ipython_view.set_wrap_mode(gtk.WRAP_CHAR)
        ipython_view.show()
        scrolled_window.add(ipython_view)
        scrolled_window.show()
        window.add(scrolled_window)
        window.show()
    
    def callback_refresh_status(self, menu_item, paths):
        """
        Refreshes an item status, which is actually just invalidate.
        """
        
        self.callback_debug_invalidate(menu_item, paths)
    
    def callback_debug_revert(self, menu_item, paths):
        client = pysvn.Client()
        for path in paths:
            client.revert(path, recurse=True)
        
    def callback_debug_invalidate(self, menu_item, paths):
        rabbitvcs_extension = self.rabbitvcs_extension
        nautilusVFSFile_table = rabbitvcs_extension.nautilusVFSFile_table
        for path in paths:
            log.debug("callback_debug_invalidate() called for %s" % path)
            if path in nautilusVFSFile_table:
                nautilusVFSFile_table[path].invalidate_extension_info()
    
    def callback_debug_add_emblem(self, menu_item, paths):
        def add_emblem_dialog():
            from subprocess import Popen, PIPE
            command = ["zenity", "--entry", "--title=RabbitVCS", "--text=Emblem to add:"]
            emblem = Popen(command, stdout=PIPE).communicate()[0].replace("\n", "")
            
            rabbitvcs_extension = self.rabbitvcs_extension
            nautilusVFSFile_table = rabbitvcs_extension.nautilusVFSFile_table
            for path in paths:
                if path in nautilusVFSFile_table:
                    nautilusVFSFile_table[path].add_emblem(emblem)
            return False
            
        gobject.idle_add(add_emblem_dialog)
    
    # End debugging callbacks

    def callback_checkout(self, menu_item, paths):
        proc = launch_ui_window("checkout", paths)
        self.rabbitvcs_extension.rescan_after_process_exit(proc, paths)
    
    def callback_update(self, menu_item, paths):
        proc = launch_ui_window("update", paths)
        self.rabbitvcs_extension.rescan_after_process_exit(proc, paths)

    def callback_commit(self, menu_item, paths):
        proc = launch_ui_window("commit", ["--base-dir=" + self.base_dir] + paths)
        self.rabbitvcs_extension.rescan_after_process_exit(proc, paths)

    def callback_add(self, menu_item, paths):
        proc = launch_ui_window("add", paths)
        # self.rabbitvcs_extension.rescan_after_process_exit(proc, paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)

    def callback_delete(self, menu_item, paths):
        proc = launch_ui_window("delete", paths)
        self.rabbitvcs_extension.rescan_after_process_exit(proc, paths)

    def callback_revert(self, menu_item, paths):
        proc = launch_ui_window("revert", paths)
        self.rabbitvcs_extension.rescan_after_process_exit(proc, paths)

    def callback_diff(self, menu_item, paths):
        launch_diff_tool(*paths)
    
    def callback_show_log(self, menu_item, paths):
        proc = launch_ui_window("log", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)

    def callback_rename(self, menu_item, paths):
        proc = launch_ui_window("rename", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)

    def callback_createpatch(self, menu_item, paths):
        proc = launch_ui_window("createpatch", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)
    
    def callback_applypatch(self, menu_item, paths):
        proc = launch_ui_window("applypatch", paths)
        self.rabbitvcs_extension.rescan_after_process_exit(proc, paths)
    
    def callback_properties(self, menu_item, paths):
        proc = launch_ui_window("properties", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)

    def callback_about(self, menu_item, paths):
        launch_ui_window("about")
        
    def callback_settings(self, menu_item, paths):
        proc = launch_ui_window("settings")
        self.rabbitvcs_extension.reload_settings(proc)
    
    def callback_ignore_filename(self, menu_item, paths):
        from rabbitvcs.ui.ignore import Ignore
        ignore = Ignore(paths[0], basename(paths[0]))
        ignore.start()

    def callback_ignore_ext(self, menu_item, paths):
        from rabbitvcs.ui.ignore import Ignore
        ignore = Ignore(paths[0], "*%s" % get_file_extension(paths[0]), glob=True)
        ignore.start()

    def callback_lock(self, menu_item, paths):
        proc = launch_ui_window("lock", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)

    def callback_branch(self, menu_item, paths):
        proc = launch_ui_window("branch", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)

    def callback_switch(self, menu_item, paths):
        proc = launch_ui_window("switch", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)

    def callback_merge(self, menu_item, paths):
        proc = launch_ui_window("merge", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)

    def callback_import(self, menu_item, paths):
        proc = launch_ui_window("import", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)

    def callback_export(self, menu_item, paths):
        proc = launch_ui_window("export", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)

    def callback_updateto(self, menu_item, paths):
        proc = launch_ui_window("updateto", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)
    
    def callback_resolve(self, menu_item, paths):
        proc = launch_ui_window("resolve", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)
        
    def callback_annotate(self, menu_item, paths):
        proc = launch_ui_window("annotate", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)

    def callback_unlock(self, menu_item, paths):
        proc = launch_ui_window("unlock", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)
        
    def callback_create_repository(self, menu_item, paths):
        proc = launch_ui_window("create", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)
    
    def callback_relocate(self, menu_item, paths):
        proc = launch_ui_window("relocate", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)

    def callback_cleanup(self, menu_item, paths):
        proc = launch_ui_window("cleanup", paths)
        self.rabbitvcs_extension.execute_after_process_exit(proc)
