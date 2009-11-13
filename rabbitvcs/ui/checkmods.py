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

import thread

import pygtk
import gobject
import gtk

from rabbitvcs.ui import InterfaceView
from rabbitvcs.lib.contextmenu import GtkContextMenu, \
    GtkContextMenuCaller, GtkFilesContextMenuConditions
from rabbitvcs.ui.action import VCSAction
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
import rabbitvcs.lib.helper
from rabbitvcs.lib.log import Log
from rabbitvcs.lib.decorators import gtk_unsafe

log = Log("rabbitvcs.ui.checkmods")

from rabbitvcs import gettext
_ = gettext.gettext

gtk.gdk.threads_init()

class CheckForModifications(InterfaceView, GtkContextMenuCaller):
    """
    Provides a way for the user to see what files have been changed on the 
    repository.
    
    """
    
    def __init__(self, paths, base_dir=None):
        InterfaceView.__init__(self, "checkmods", "CheckMods")

        self.paths = paths
        self.base_dir = base_dir
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        self.items = None
        self.files_table = rabbitvcs.ui.widget.FilesTable(
            self.get_widget("files_table"), 
            [gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Path"), _("Extension"), 
                _("Text Status"), _("Property Status"), 
                _("Revision"), _("Author")],
            base_dir=base_dir,
            path_entries=[0],
            callbacks={
                "row-activated":  self.on_files_table_row_activated,
                "mouse-event":   self.on_files_table_mouse_event
            }
        )

        self.initialize_items()

    def on_destroy(self, widget):
        self.close()
        
    def on_close_clicked(self, widget):
        self.close()

    def on_refresh_clicked(self, widget):
        self.initialize_items()

    def on_files_table_row_activated(self, treeview, event, col):
        treeview.grab_focus()
        self.files_table.update_selection()
        paths = self.files_table.get_selected_row_items(0)
        self.diff_remote(paths[0])

    def on_files_table_mouse_event(self, treeview, data=None):
        self.files_table.update_selection()
            
        if data is not None and data.button == 3:
            self.show_files_table_popup_menu(treeview, data)

    #
    # Helper methods
    #

    def initialize_items(self):
        """
        Initializes the file items in a new thread
        """
        
        try:
            thread.start_new_thread(self.load, ())
        except Exception, e:
            log.exception(e)
    
    def load(self):
        gtk.gdk.threads_enter()
        self.get_widget("status").set_text(_("Loading..."))
        gtk.gdk.threads_leave()

        self.items = self.vcs.get_remote_updates(self.paths)
        self.populate_files_table()

        gtk.gdk.threads_enter()
        self.get_widget("status").set_text(_("Found %d item(s)") % len(self.items))
        gtk.gdk.threads_leave()

    def populate_files_table(self):
        gtk.gdk.threads_enter()
        self.files_table.clear()
        gtk.gdk.threads_leave()
        
        for item in self.items:
            revision_number = -1
            author = ""
            if item.entry is not None:
                revision_number = item.entry.revision.number
                author = item.entry.commit_author

            self.files_table.append([
                item.path, 
                rabbitvcs.lib.helper.get_file_extension(item.path),
                item.repos_text_status,
                item.repos_prop_status,
                str(revision_number),
                author
            ])

    def show_files_table_popup_menu(self, treeview, data):
        paths = self.files_table.get_selected_row_items(0)
        conditions = CheckModsContextMenuConditions(self.vcs, paths)
        CheckModsContextMenu(self, data, self.base_dir, self.vcs, paths).show()
     
    def diff_remote(self, path):
        from rabbitvcs.ui.diff import SVNDiff
        
        path_local = path
        path_remote = self.vcs.get_repo_url(path_local)
        
        self.action = VCSAction(
            self.vcs,
            notification=False
        )
        self.action.append(
            SVNDiff,
            path_local, 
            None, 
            path_remote,
            "HEAD"
        )
        self.action.start()
            
class CheckModsContextMenuConditions(GtkFilesContextMenuConditions):
    def __init__(self, vcs_client, paths=[]):
        GtkFilesContextMenuConditions.__init__(self, vcs_client, paths)

    def update(self, data=None):
        return True

    def unified_diff(self, data=None):
        return (self.path_dict["exists"]
            and self.path_dict["length"] == 1)

    def sidebyside_diff(self, data=None):
        return (self.path_dict["exists"]
            and self.path_dict["length"] == 1)

class CheckModsContextMenuCallbacks:
    def __init__(self, caller, base_dir, vcs_client, paths=[]):
        self.caller = caller
        self.base_dir = base_dir
        self.vcs_client = vcs_client
        self.paths = paths

    def update(self, data1=None, data2=None):
        rabbitvcs.lib.helper.launch_ui_window(
            "update", 
            self.paths
        )

    def unified_diff(self, data1=None, data2=None):
        self.caller.diff_remote(self.paths[0])

    def sidebyside_diff(self, data1=None, data2=None):
        from rabbitvcs.ui.diff import SVNDiff
        
        path_local = self.paths[0]
        path_remote = self.vcs_client.get_repo_url(path_local)
        
        self.action = VCSAction(
            self.vcs_client,
            notification=False
        )
        self.action.append(
            SVNDiff,
            path_local, 
            None, 
            path_remote,
            "HEAD",
            side_by_side=True
        )
        self.action.start()

class CheckModsContextMenu:
    def __init__(self, caller, event, base_dir, vcs_client, paths=[]):
        
        self.caller = caller
        self.event = event
        self.paths = paths
        self.base_dir = base_dir
        self.vcs_client = vcs_client
        
        self.conditions = CheckModsContextMenuConditions(self.vcs_client, paths)
        self.callbacks = CheckModsContextMenuCallbacks(
            self.caller, 
            self.base_dir,
            self.vcs_client, 
            paths
        )
        
        self.structure = [
            ("ViewDiff", None),
            ("ViewSideBySideDiff", None),
            ("Separator0", None),
            ("Update", None)
        ]

        self.items = {
            "ViewDiff": {
                "label": _("View unified diff"),
                "icon": "rabbitvcs-diff",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.unified_diff, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.unified_diff
                }
            },
            "ViewSideBySideDiff": {
                "label": _("View side-by-side diff"),
                "icon": None,
                "signals": {
                    "activate": {
                        "callback": self.callbacks.sidebyside_diff, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.sidebyside_diff
                }
            },
            "Separator0": {
                "label": rabbitvcs.ui.widget.SEPARATOR,
                "signals": None,
                "condition": {
                    "callback": (lambda: True)
                }
            },
            "Update": {
                "label": _("Update"),
                "icon": "rabbitvcs-update",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.update, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.update
                }
            }
        }

    def show(self):
        if len(self.paths) == 0:
            return

        context_menu = GtkContextMenu(self.structure, self.items)
        context_menu.show(self.event)

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main()

    window = CheckForModifications(paths, options.base_dir)
    window.register_gtk_quit()
    gtk.main()
