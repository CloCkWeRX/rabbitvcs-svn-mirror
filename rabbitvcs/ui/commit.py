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

import os
import thread

import pygtk
import gobject
import gtk
from time import sleep

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.action import VCSAction
from rabbitvcs.lib.contextmenu import GtkFilesContextMenu, GtkContextMenuCaller
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.lib
import rabbitvcs.lib.helper
from rabbitvcs.lib.log import Log
from rabbitvcs.lib.decorators import gtk_unsafe

log = Log("rabbitvcs.ui.commit")

from rabbitvcs import gettext
_ = gettext.gettext

gtk.gdk.threads_init()

class Commit(InterfaceView, GtkContextMenuCaller):
    """
    Provides a user interface for the user to commit working copy
    changes to a repository.  Pass it a list of local paths to commit.
    
    """

    TOGGLE_ALL = False
    SHOW_UNVERSIONED = True

    def __init__(self, paths, base_dir=None, message=None):
        """
        
        @type  paths:   list of strings
        @param paths:   A list of local paths.
        
        """
        InterfaceView.__init__(self, "commit", "Commit")

        self.paths = paths
        self.base_dir = base_dir
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        self.common = rabbitvcs.lib.helper.get_common_directory(paths)

        if not self.vcs.get_versioned_path(self.common):
            rabbitvcs.ui.dialog.MessageBox(_("The given path is not a working copy"))
            raise SystemExit()

        self.files_table = rabbitvcs.ui.widget.Table(
            self.get_widget("files_table"),
            [gobject.TYPE_BOOLEAN, rabbitvcs.ui.widget.TYPE_PATH, 
                gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [rabbitvcs.ui.widget.TOGGLE_BUTTON, _("Path"), _("Extension"), 
                _("Text Status"), _("Property Status")],
            filters=[{
                "callback": rabbitvcs.ui.widget.path_filter,
                "user_data": {
                    "base_dir": base_dir,
                    "column": 1
                }
            }],
            callbacks={
                "row-activated":  self.on_files_table_row_activated,
                "mouse-event":   self.on_files_table_mouse_event,
                "key-event":     self.on_files_table_key_event
            }
        )
        self.files_table.allow_multiple()
        
        self.message = rabbitvcs.ui.widget.TextView(
            self.get_widget("message"),
            (message and message or "")
        )
        self.get_widget("to").set_text(
            self.vcs.get_repo_url(self.common)
        )

        self.items = None
        self.initialize_items()
        
    #
    # Helper functions
    # 

    def load(self):
        """
          - Gets a listing of file items that are valid for the commit window.
          - Determines which items should be "activated" by default
          - Populates the files table with the retrieved items
          - Updates the status area        
        """

        gtk.gdk.threads_enter()
        self.get_widget("status").set_text(_("Loading..."))
        gtk.gdk.threads_leave()

        self.items = self.vcs.get_items(self.paths, self.vcs.STATUSES_FOR_COMMIT)

        gtk.gdk.threads_enter()
        self.populate_files_table()
        self.get_widget("status").set_text(_("Found %d item(s)") % len(self.items))
        gtk.gdk.threads_leave()

    def reload_treeview(self):
        self.initialize_items()

    def reload_treeview_threaded(self):
        self.load()

    def should_item_be_activated(self, item):
        """
        Determines if a file should be activated or not
        """
        
        if (item.path in self.paths
                or item.is_versioned):
            return True

        return False

    def populate_files_table(self):
        """
        First clears and then populates the files table based on the items
        retrieved in self.load()
        
        """
        
        self.files_table.clear()
        for item in self.items:
            checked = self.should_item_be_activated(item)
            
            self.files_table.append([
                checked,
                item.path, 
                rabbitvcs.lib.helper.get_file_extension(item.path),
                item.text_status,
                item.prop_status
            ])

    def initialize_items(self):
        """
        Initializes the activated cache and loads the file items in a new thread
        """
        
        try:
            thread.start_new_thread(self.load, ())
        except Exception, e:
            log.exception(e)

    def show_files_table_popup_menu(self, treeview, data):
        paths = self.files_table.get_selected_row_items(1)
        GtkFilesContextMenu(self, data, self.base_dir, paths).show()

    def delete_items(self, widget, data=None):
        paths = self.files_table.get_selected_row_items(1)
        if len(paths) > 0:
            from rabbitvcs.ui.delete import Delete
            Delete(paths).start()
            sleep(1) # sleep so the items can be fully deleted before init
            self.initialize_items()
            
    #
    # Event handlers
    #
    
    def on_destroy(self, widget):
        self.close()
        
    def on_cancel_clicked(self, widget, data=None):
        self.close()
        
    def on_ok_clicked(self, widget, data=None):
        items = self.files_table.get_activated_rows(1)
        self.hide()

        if len(items) == 0:
            self.close()
            return

        added = 0
        for item in items:
            try:
                if self.vcs.status(item, recurse=False)[0].text_status == self.vcs.STATUS["unversioned"]:
                    self.vcs.add(item)
                    added += 1
            except Exception, e:
                log.exception(e)

        ticks = added + len(items)*2

        self.action = rabbitvcs.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.set_pbar_ticks(ticks)
        self.action.append(self.action.set_header, _("Commit"))
        self.action.append(self.action.set_status, _("Running Commit Command..."))
        self.action.append(
            rabbitvcs.lib.helper.save_log_message, 
            self.message.get_text()
        )
        self.action.append(self.vcs.commit, items, self.message.get_text())
        self.action.append(self.action.set_status, _("Completed Commit"))
        self.action.append(self.action.finish)
        self.action.start()
        
    def on_key_pressed(self, widget, data):
        if (data.state & (gtk.gdk.SHIFT_MASK | gtk.gdk.CONTROL_MASK) and 
                gtk.gdk.keyval_name(data.keyval) == "Return"):
            self.on_ok_clicked(widget)
            return True
            
    def on_toggle_show_all_toggled(self, widget, data=None):
        self.TOGGLE_ALL = not self.TOGGLE_ALL
        for row in self.files_table.get_items():
            row[0] = self.TOGGLE_ALL
            
    def on_toggle_show_unversioned_toggled(self, widget, data=None):
        self.SHOW_UNVERSIONED = not self.SHOW_UNVERSIONED

        if self.SHOW_UNVERSIONED:
            self.initialize_activated_cache()
            self.populate_files_table()
        else:
            index = 0
            for row in self.files_table.get_items():
                if not self.vcs.is_versioned(row[1]):
                    self.files_table.remove(index)
                    index -= 1
                index += 1

    def on_files_table_row_activated(self, treeview, event, col):
        paths = self.files_table.get_selected_row_items(1)
        rabbitvcs.lib.helper.launch_diff_tool(*paths)

    def on_files_table_key_event(self, treeview, data=None):
        if gtk.gdk.keyval_name(data.keyval) == "Delete":
            self.delete_items(treeview, data)

    def on_files_table_mouse_event(self, treeview, data=None):
        if data is not None and data.button == 3:
            self.show_files_table_popup_menu(treeview, data)

    def on_previous_messages_clicked(self, widget, data=None):
        dialog = rabbitvcs.ui.dialog.PreviousMessages()
        message = dialog.run()
        if message is not None:
            self.message.set_text(message)

if __name__ == "__main__":
    from rabbitvcs.ui import main, BASEDIR_OPT
    (options, paths) = main(
        [BASEDIR_OPT, (["-m", "--message"], {"help":"add a commit log message"})],
        usage="Usage: rabbitvcs commit [path1] [path2] ..."
    )

    window = Commit(paths, options.base_dir, message=options.message)
    window.register_gtk_quit()
    gtk.main()
