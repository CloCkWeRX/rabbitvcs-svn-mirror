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

class Commit(InterfaceView):
    """
    Provides a user interface for the user to commit working copy
    changes to a repository.  Pass it a list of local paths to commit.
    
    """

    TOGGLE_ALL = False
    SHOW_UNVERSIONED = True
    
    selected_rows = []
    selected_paths = []

    def __init__(self, paths, base_dir=None):
        """
        
        @type  paths:   list of strings
        @param paths:   A list of local paths.
        
        """
        InterfaceView.__init__(self, "commit", "Commit")

        self.paths = paths
        self.base_dir = base_dir
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        self.common = rabbitvcs.lib.helper.get_common_directory(paths)
        self.activated_cache = {}

        if not self.vcs.get_versioned_path(self.common):
            rabbitvcs.ui.dialog.MessageBox(_("The given path is not a working copy"))
            raise SystemExit()

        self.files_table = rabbitvcs.ui.widget.Table(
            self.get_widget("files_table"),
            [gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [rabbitvcs.ui.widget.TOGGLE_BUTTON, _("Path"), _("Extension"), 
                _("Text Status"), _("Property Status")],
            base_dir=base_dir,
            path_entries=[1]
        )
        self.files_table.allow_multiple()
        
        self.message = rabbitvcs.ui.widget.TextView(
            self.get_widget("message")
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

        self.get_widget("status").set_text(_("Loading..."))
        self.items = self.vcs.get_items(self.paths, self.vcs.STATUSES_FOR_COMMIT)

        if len(self.activated_cache) == 0:
            for item in self.items:
                self.activated_cache[item.path] = self.should_item_be_activated(item)

        self.populate_files_table()
        self.get_widget("status").set_text(_("Found %d item(s)") % len(self.items))

    def should_item_be_activated(self, item):
        """
        Determines if a file should be activated or not
        """
        
        if (item.path in self.paths
                or item.is_versioned):
            return True

        return False

    def initialize_activated_cache(self):
        """
        Resets and populates the activated cache based on the existing state
        of the files table.
        
        The activated cache is used to "remember" which items are checked off
        before it populates (and possibly changes) the files table entries
        """
        
        self.activated_cache = {}

        for row in self.files_table.get_items():
            self.activated_cache[row[1]] = row[0]

    @gtk_unsafe
    def populate_files_table(self):
        """
        First clears and then populates the files table based on the items
        retrieved in self.load()
        
        """
        
        self.files_table.clear()

        for item in self.items:
            if item.path in self.activated_cache:
                checked = self.activated_cache[item.path]
            else:
                self.activated_cache[item.path] = self.should_item_be_activated(item)
                checked = self.activated_cache[item.path]
            
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
            self.initialize_activated_cache()
            thread.start_new_thread(self.load, ())
        except Exception, e:
            log.exception(e)

    def show_files_table_popup_menu(self, treeview, data):

        # Build up a list of items to ignore based on the selected rows
        ignore_items = []
        added_ignore_labels = []
        
        # These are ignore-by-filename items
        for index in self.selected_rows:
            item = self.files_table.get_row(index)

            basename = os.path.basename(item[1])
            if basename not in added_ignore_labels:
                ignore_items.append({
                    "label": basename,
                    "signals": {
                        "button-press-event": {
                            "callback": self.on_subcontext_ignore_by_filename_activated, 
                            "args": item[1]
                         }
                     },
                    "condition": {
                        "callback": self.condition_ignore,
                        "args": item[1]
                    }
                })
                added_ignore_labels.append(basename)

        # These are ignore-by-extension items
        for index in self.selected_rows:
            item = self.files_table.get_row(index)
            
            ext_str = "*%s"%item[2]
            if ext_str not in added_ignore_labels:
                ignore_items.append({
                    "label": ext_str,
                    "signals": {
                        "button-press-event": {
                            "callback": self.on_subcontext_ignore_by_fileext_activated, 
                            "args": item[1]
                        }
                    },
                    "condition": {
                        "callback": self.condition_ignore_by_fileext,
                        "args": item
                    }
                })
                added_ignore_labels.append(ext_str)

        # Generate the full context menu
        context_menu = rabbitvcs.ui.widget.ContextMenu([
            {
                "label": _("View Diff"),
                "signals": {
                    "activate": {
                        "callback": self.on_context_diff_activated, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.condition_view_diff,
                    "args": None
                }
            },
            {
                "label": _("Open"),
                "signals": {
                    "activate": {
                        "callback": self.on_context_open_activated, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.condition_open,
                    "args": None
                }
            },
            {
                "label": _("Browse to"),
                "signals": {
                    "activate": {
                        "callback": self.on_context_browse_activated, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": (lambda: True)
                }
            },
            {
                "label": _("Delete"),
                "signals": {
                    "activate": {
                        "callback": self.on_context_delete_activated, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.condition_delete,
                    "args": None
                }
            },
            {
                "label": _("Add"),
                "signals": {
                    "activate": {
                        "callback": self.on_context_add_activated, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.condition_add,
                    "args": None
                }
            },
            {
                "label": _("Revert"),
                "signals": {
                    "activate": {
                        "callback": self.on_context_revert_activated, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.condition_revert,
                    "args": None
                }
            },
            {
                "label": _("Restore"),
                "signals": {
                    "activate": {
                        "callback": self.on_context_restore_activated, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.condition_restore,
                    "args": None
                }
            },
            {
                "label": _("Add to ignore list"),
                'submenu': ignore_items,
                "condition": {
                    "callback": self.condition_ignore,
                    "args": None
                }
            }
        ])
        context_menu.show(data)

    def delete_items(self, widget, data=None):
        if len(self.selected_paths) > 0:
            from rabbitvcs.ui.delete import Delete
            Delete(self.selected_paths).start()
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
                print str(e)

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
                
    def on_files_table_cursor_changed(self, treeview, data=None):
        self.__files_table_event(treeview, data)

    def on_files_table_button_released(self, treeview, data=None):
        self.__files_table_event(treeview, data)

    def on_files_table_key_pressed(self, treeview, data=None):
        selection = treeview.get_selection()
        (liststore, indexes) = selection.get_selected_rows()

        self.selected_rows = []
        self.selected_paths = []
        for tup in indexes:
            self.selected_rows.append(tup[0])
            self.selected_paths.append(self.files_table.get_row(tup[0])[1])

        if gtk.gdk.keyval_name(data.keyval) == "Delete":
            self.delete_items(treeview, data)

    def on_files_table_button_pressed(self, treeview, data=None):
        # this allows us to retain multiple selections with a right-click
        if data.button == 3:
            selection = treeview.get_selection()
            (liststore, indexes) = selection.get_selected_rows()
            return (len(indexes) > 0)

    def on_files_table_row_doubleclicked(self, treeview, event, col):
        treeview.grab_focus()
        treeview.set_cursor(event[0], col, 0)
        treeview_model = treeview.get_model().get_model()
        fileinfo = treeview_model[event[0]]

        rabbitvcs.lib.helper.launch_diff_tool(fileinfo[1])

    def __files_table_event(self, treeview, data=None):
        selection = treeview.get_selection()
        (liststore, indexes) = selection.get_selected_rows()

        self.selected_rows = []
        self.selected_paths = []
        for tup in indexes:
            self.selected_rows.append(tup[0])
            self.selected_paths.append(self.files_table.get_row(tup[0])[1])
            
        if data is not None and data.button == 3:
            self.show_files_table_popup_menu(treeview, data)

    def on_context_add_activated(self, widget, data=None):
        self.action = rabbitvcs.ui.action.VCSAction(
            self.vcs,
            notification=False
        )

        for index in self.selected_rows:
            item = self.files_table.get_row(index)
            path = item[1]
            
            self.action.append(self.vcs.add, path)
            self.action.append(self.files_table.set_row_item, index, 0, True)
        
        self.action.append(self.initialize_activated_cache)
        self.action.append(self.load)
        self.action.start()

    def on_context_revert_activated(self, widget, data=None):
        self.action = rabbitvcs.ui.action.VCSAction(
            self.vcs,
            notification=False
        )

        for index in self.selected_rows:
            item = self.files_table.get_row(index)
            path = item[1]
            
            self.action.append(self.vcs.revert, path)
            self.action.append(self.files_table.set_row_item, index, 0, False)
        
        self.action.append(self.initialize_activated_cache)
        self.action.append(self.load)
        self.action.start()

    def on_context_diff_activated(self, widget, data=None):
        for path in self.selected_paths:
            rabbitvcs.lib.helper.launch_diff_tool(path)

    def on_context_open_activated(self, widget, data=None):
        for path in self.selected_paths:
            rabbitvcs.lib.helper.open_item(path)
        
    def on_context_browse_activated(self, widget, data=None):
        rabbitvcs.lib.helper.browse_to_item(
            self.files_table.get_row(self.selected_rows[0])[1]
        )

    def on_context_delete_activated(self, widget, data=None):
        self.delete_items(widget, data)
            
    def on_subcontext_ignore_by_filename_activated(self, widget, data=None, userdata=None):

        for index in self.selected_rows:
            item = self.files_table.get_row(index)
            prop_name = self.vcs.PROPERTIES["ignore"]
            prop_value = os.path.basename(item[1])
            self.vcs.propset(
                self.base_dir,
                prop_name,
                prop_value
            )
        
        self.initialize_items()
        
    def on_subcontext_ignore_by_fileext_activated(self, widget, data=None, userdata=None):
        for index in self.selected_rows:
            item = self.files_table.get_row(index)
            prop_name = self.vcs.PROPERTIES["ignore"]
            prop_value = "*%s" % item[2]            
            self.vcs.propset(
                self.base_dir,
                prop_name,
                prop_value,
                recurse=True
            )

        self.initialize_items()

    def on_context_restore_activated(self, widget, data=None):
        rabbitvcs.lib.helper.launch_ui_window(
            "update", 
            self.selected_paths,
            return_immmediately=False
        )
        self.initialize_items()
        
    def on_previous_messages_clicked(self, widget, data=None):
        dialog = rabbitvcs.ui.dialog.PreviousMessages()
        message = dialog.run()
        if message is not None:
            self.message.set_text(message)
    
    # Conditions
    
    def condition_add(self, data=None):
        for path in self.selected_paths:
            if self.vcs.is_versioned(path):
                return False
        
        return True
    
    def condition_revert(self, data=None):
        for path in self.selected_paths:
            if not (self.vcs.is_added(path) or
                    self.vcs.is_deleted(path) or
                    self.vcs.is_modified(path)):
                return False
        
        return True

    def condition_view_diff(self, data=None):
        for path in self.selected_paths:
            if self.vcs.is_modified(path):
                return True
        
        return False

    def condition_restore(self, data=None):
        for path in self.selected_paths:
            if self.vcs.is_missing(path):
                return True
        
        return False

    def condition_delete(self, data=None):
        for path in self.selected_paths:
            if self.vcs.is_deleted:
                return True

        return False

    def condition_ignore(self, data=None):
        for path in self.selected_paths:
            if path == self.base_dir:
                return False
        
        return True
    
    def condition_ignore_by_fileext(self, data):
        return os.path.isfile(data[1])

    def condition_open(self, data=None):
        for path in self.selected_paths:
            if not os.path.isfile(path):
                return False
        
        return True

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main()

    window = Commit(paths, options.base_dir)
    window.register_gtk_quit()
    gtk.main()
