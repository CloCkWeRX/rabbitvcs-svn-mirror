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

import thread

import pygtk
import gobject
import gtk

from nautilussvn.ui import InterfaceView
from nautilussvn.ui.action import VCSAction
from nautilussvn.ui.log import LogDialog
import nautilussvn.ui.widget
import nautilussvn.ui.dialog
import nautilussvn.lib.vcs
import nautilussvn.lib.helper

from nautilussvn import gettext
_ = gettext.gettext

gtk.gdk.threads_init()

class Lock(InterfaceView):
    """
    Provides an interface to lock any number of files in a working copy.
    
    """

    TOGGLE_ALL = False

    def __init__(self, paths):
        """
        @type:  paths: list
        @param: paths: A list of paths to search for versioned files
        
        """
        
        InterfaceView.__init__(self, "lock", "Lock")

        self.paths = paths
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()

        self.files_table = nautilussvn.ui.widget.Table(
            self.get_widget("files_table"),
            [gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING], 
            [nautilussvn.ui.widget.TOGGLE_BUTTON, _("Path"), _("Extension"), 
                _("Locked")],
        )
        self.last_row_clicked = None

        self.message = nautilussvn.ui.widget.TextView(
            self.get_widget("message")
        )

        self.items = None
        try:
            thread.start_new_thread(self.load, ())
        except Exception, e:
            print str(e)

    #
    # Helper functions
    # 
    
    def refresh_row_status(self):
        row = self.files_table.get_row(self.last_row_clicked)
        
        locked = ""
        if self.vcs.is_locked(row[1]):
            locked = _("Yes")

        row[3] = locked

    def load(self):
        gtk.gdk.threads_enter()
        self.get_widget("status").set_text(_("Loading..."))
        self.items = self.vcs.get_items(self.paths)
        self.populate_files_table()
        self.get_widget("status").set_text(_("Found %d item(s)") % len(self.items))
        gtk.gdk.threads_leave()

    def populate_files_table(self):
        for item in self.items:
        
            locked = ""
            if self.vcs.is_locked(item.path):
                locked = _("Yes")
            if not self.vcs.is_versioned(item.path):
                continue
        
            self.files_table.append([
                False, 
                item.path, 
                nautilussvn.lib.helper.get_file_extension(item.path),
                locked
            ])
            
    #
    # UI Signal Callbacks
    #
    
    def on_destroy(self, widget):
        self.close()
        
    def on_cancel_clicked(self, widget, data=None):
        self.close()
        
    def on_ok_clicked(self, widget, data=None):
        steal_locks = self.get_widget("steal_locks").get_active()
        items = self.files_table.get_activated_rows(1)
        if not items:
            self.close()
            return

        message = self.message.get_text()
        
        self.hide()

        self.action = nautilussvn.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        
        self.action.append(self.action.set_header, _("Get Lock"))
        self.action.append(self.action.set_status, _("Running Lock Command..."))
        self.action.append(nautilussvn.lib.helper.save_log_message, message)
        for path in items:
            self.action.append(
                self.vcs.lock, 
                path,
                message,
                force=steal_locks
            )
        self.action.append(self.action.set_status, _("Completed Lock"))
        self.action.append(self.action.finish)
        self.action.start()
    
    def on_select_all_toggled(self, widget, data=None):
        self.TOGGLE_ALL = not self.TOGGLE_ALL
        for row in self.files_table.get_items():
            row[0] = self.TOGGLE_ALL

    def on_files_table_button_pressed(self, treeview, event):
        pathinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
        if pathinfo is not None:
            path, col, cellx, celly = pathinfo
            treeview.grab_focus()
            treeview.set_cursor(path, col, 0)
            treeview_model = treeview.get_model()
            fileinfo = treeview_model[path]
            
            if event.button == 3:
                self.last_row_clicked = path
                context_menu = nautilussvn.ui.widget.ContextMenu([
                    {
                        "label": _("Remove Lock"),
                        "signals": {
                            "activate": {
                                "callback": self.on_context_remove_lock_activated, 
                                "args": fileinfo
                            }
                        },
                        "condition": self.condition_remove_lock
                    },
                    {
                        "label": _("View Diff"),
                        "signals": {
                            "activate": {
                                "callback": self.on_context_diff_activated, 
                                "args": fileinfo
                            }
                        },
                        "condition": self.condition_diff
                    },
                    {
                        "label": _("Show log"),
                        "signals": {
                            "activate": {
                                "callback": self.on_context_log_activated, 
                                "args": fileinfo
                            }
                        },
                        "condition": (lambda: True)
                    },
                    {
                        "label": _("Open"),
                        "signals": {
                            "activate": {
                                "callback": self.on_context_open_activated, 
                                "args": fileinfo
                            }
                        },
                        "condition": self.condition_open
                    },
                    {
                        "label": _("Browse to"),
                        "signals": {
                            "activate": {
                                "callback": self.on_context_browse_activated, 
                                "args": fileinfo
                            }
                        },
                        "condition": (lambda: True)
                    }
                ])
                context_menu.show(event)

    def on_files_table_row_doubleclicked(self, treeview, event, col):
        pass

    def on_previous_messages_clicked(self, widget, data=None):
        dialog = nautilussvn.ui.dialog.PreviousMessages()
        message = dialog.run()
        if message is not None:
            self.message.set_text(message)

    #
    # Context menu signal callbacks
    #

    def on_context_log_activated(self, widget, data=None):
        LogDialog(data[1])

    def on_context_diff_activated(self, widget, data=None):
        nautilussvn.lib.helper.launch_diff_tool(data[1])

    def on_context_open_activated(self, widget, data=None):
        nautilussvn.lib.helper.open_item(data[1])
        
    def on_context_browse_activated(self, widget, data=None):
        nautilussvn.lib.helper.browse_to_item(data[1])

    def on_context_remove_lock_activated(self, widget, data=None):
        from nautilussvn.ui.unlock import UnlockQuick
        unlock = UnlockQuick(data[1])
        unlock.start()
        self.refresh_row_status()

    #
    # Context menu conditions
    #

    def condition_diff(self):
        path = self.files_table.get_row(self.last_row_clicked)[1]
        return self.vcs.is_modified(path)
    
    def condition_remove_lock(self):
        path = self.files_table.get_row(self.last_row_clicked)[1]
        return self.vcs.is_locked(path)
    
    def condition_open(self):
        path = self.files_table.get_row(self.last_row_clicked)[1]
        return os.path.isfile(path)
    
if __name__ == "__main__":
    from os import getcwd
    from sys import argv
    
    args = argv[1:]

    # Convert "." to current working directory
    paths = args
    i = 0
    for arg in args:
        paths[i] = arg
        if paths[i] == ".":
            paths[i] = getcwd()
        i += 1
   
    if not paths:
        paths = [getcwd()]

    window = Lock(paths)
    window.register_gtk_quit()
    gtk.main()
