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

def log_all_exceptions(type, value, tb):
    import sys, traceback
    from rabbitvcs.util.log import Log
    log = Log("rabbitvcs.util.extensions.nautilus.RabbitVCS")
    log.exception_info("Error caught by master exception hook!",
                       (type, value, tb))
    
    text = ''.join(traceback.format_exception(type, value,
                                              tb, limit=None))
    
    try:
        import rabbitvcs.ui.dialog
        rabbitvcs.ui.dialog.ErrorNotification(text)
    except Exception, ex:
        log.exception("Additional exception when attempting"
                      " to display error dialog.")
        log.exception(ex)
        raise
    
    sys.__excepthook__(type, value, tb)

import sys
sys.excepthook = log_all_exceptions

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

from rabbitvcs.vcs.svn import SVN

from rabbitvcs.util.vcs import *
from rabbitvcs.util.helper import launch_ui_window, launch_diff_tool
from rabbitvcs.util.helper import get_file_extension, get_common_directory
from rabbitvcs.util.helper import pretty_timedelta
from rabbitvcs.util.decorators import timeit, disable
from rabbitvcs.util.contextmenu import MenuBuilder, MainContextMenu, SEPARATOR

import rabbitvcs.ui
import rabbitvcs.ui.property_page

from rabbitvcs.util.log import Log, reload_log_settings
log = Log("rabbitvcs.util.extensions.nautilus.RabbitVCS")

from rabbitvcs import gettext
_ = gettext.gettext

from rabbitvcs.util.settings import SettingsManager
settings = SettingsManager()

import rabbitvcs.services.service
from rabbitvcs.services.checkerservice import StatusCheckerStub as StatusChecker

class RabbitVCS(nautilus.InfoProvider, nautilus.MenuProvider,
                 nautilus.ColumnProvider, nautilus.PropertyPageProvider):
    """ 
    This is the main class that implements all of our awesome features.
    
    """
    
    EMBLEMS = rabbitvcs.ui.STATUS_EMBLEMS
    
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
    statuses_from_callback = []
    
    
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
        
        self.status_checker = StatusChecker(self.cb_status)
        
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
        status = None
        
        with self.callback_paths_lock:
            # Could replace with (st for st in self.... if st.path ...).next()
            # Need to catch exception
            for idx in xrange(len(self.statuses_from_callback)):
                found = (self.statuses_from_callback[idx].path) == path
                if found: break
            
            if found: # We're here because we were triggered by a callback
                status = self.statuses_from_callback[idx]
                del self.statuses_from_callback[idx]
        
        # Don't bother the checker if we already have the info from a callback
        
        if not found:
            status = \
                self.status_checker.check_status(path,
                                                 recurse=True,
                                                 summary=True,
                                                 callback=True,
                                                 invalidate=self.always_invalidate)

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

        # if bool(int(settings.get("general", "enable_attributes"))): self.update_columns(item, path, status, client_info)
        if bool(int(settings.get("general", "enable_emblems"))): self.update_status(item, path, status, client_info)
        
    def update_columns(self, item, path, status, client_info):
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
                    
                values["status"] = status.summary

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

    
    def update_status(self, item, path, status, client_info):
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
        if status.summary in self.EMBLEMS:
            item.add_emblem(self.EMBLEMS[status.summary])
        
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
        
        return NautilusMainContextMenu(self, window.get_data("base_dir"), paths).get_menu()
    
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
        
        return NautilusMainContextMenu(self, path, [path]).get_menu()
    
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
                # We're not interested in the result now, just the callback
                self.status_checker.check_status(path,
                                                 recurse=True,
                                                 invalidate=True,
                                                 callback=True,
                                                 summary=True)
            
        self.execute_after_process_exit(proc, do_check)
        
    def execute_after_process_exit(self, proc, func=None):

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
            globals()["log"] = reload_log_settings()("rabbitvcs.util.extensions.nautilus")
            log.debug("Re-scanning settings")
            
        self.execute_after_process_exit(proc, do_reload_settings)
        
        
    # 
    # Callbacks
    # 
    
    def cb_status(self, status):
        """
        This is the callback that C{StatusMonitor} calls. 
        
        @type   path:   string
        @param  path:   The path of the item something interesting happened to.
        
        @type   statuses: list of status objects
        @param  statuses: The statuses
        """
        # log.debug("CB Thread: %s" % threading.currentThread())
        if status.path in self.nautilusVFSFile_table:
            item = self.nautilusVFSFile_table[status.path]
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
                self.statuses_from_callback.append(status)
                # These are useful to establish whether the "update_status" call
                # happens INSIDE this next call, or later, or in another thread. 
                # log.debug("%s: Invalidating..." % threading.currentThread())
                item.invalidate_extension_info()
                # log.debug("%s: Done invalidate call." % threading.currentThread())
        else:
            log.debug("Path [%s] not found in file table" % status.path)

    def get_property_pages(self, items):

        paths = []
        
        for item in items:
            if self.valid_uri(item.get_uri()):
                path = realpath(unicode(gnomevfs.get_local_path_from_uri(item.get_uri()), "utf-8"))
                paths.append(path)
                self.nautilusVFSFile_table[path] = item

        if len(paths) == 0: return []

        label = rabbitvcs.ui.property_page.PropertyPageLabel().get_widget()
        page = rabbitvcs.ui.property_page.PropertyPage(paths).get_widget()
        
        ppage = nautilus.PropertyPage('RabbitVCS::PropertyPage',
            label,
            page)        
        
        return [ppage]
        

from rabbitvcs.util.contextmenuitems import *

class NautilusContextMenu(MenuBuilder):
    """
    Provides a standard Nautilus context menu (ie. a list of
    "nautilus.MenuItem"s).
    """
    
    signal = "activate"
        
    def make_menu_item(self, item, id_magic):
        return item.make_nautilus_menu_item(id_magic)
    
    def attach_submenu(self, menu_node, submenu_list):
        submenu = nautilus.Menu()
        menu_node.set_submenu(submenu)
        [submenu.append_item(item) for item in submenu_list]
    
    def top_level_menu(self, items):
        return items

class NautilusMainContextMenu(MainContextMenu):
    def get_menu(self):
        return NautilusContextMenu(self.structure, self.conditions, self.callbacks).menu