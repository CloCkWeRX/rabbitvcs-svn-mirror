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

import os
import thread

import gnomevfs
import pygtk
import gobject
import gtk
import os
import tempfile
import shutil

from nautilussvn.ui import InterfaceView
from nautilussvn.ui.action import VCSAction
import nautilussvn.ui.widget
import nautilussvn.ui.dialog
import nautilussvn.lib
import nautilussvn.lib.helper
from nautilussvn.lib.helper import get_common_directory
from nautilussvn.lib.log import Log

log = Log("nautilussvn.ui.createpatch")

from nautilussvn import gettext
_ = gettext.gettext

gtk.gdk.threads_init()

class CreatePatch(InterfaceView):
    """
    Provides a user interface for the user to create a Patch file
    
    """

    TOGGLE_ALL = False
    SHOW_UNVERSIONED = False

    def __init__(self, paths):
        """
        
        @type  paths:   list of strings
        @param paths:   A list of local paths.
        
        """
        InterfaceView.__init__(self, "createpatch", "CreatePatch")

        self.paths = paths
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()
        self.common = nautilussvn.lib.helper.get_common_directory(paths)

        if not self.vcs.get_versioned_path(self.common):
            nautilussvn.ui.dialog.MessageBox(_("The given path is not a working copy"))
            raise SystemExit()

        self.files_table = nautilussvn.ui.widget.Table(
            self.get_widget("files_table"),
            [gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [nautilussvn.ui.widget.TOGGLE_BUTTON, _("Path"), _("Extension"), 
                _("Text Status"), _("Property Status")],
        )
        self.last_row_clicked = None
        
        self.items = None
        try:
            thread.start_new_thread(self.load, ())
        except Exception, e:
            log.exception()

    #
    # Helper functions
    # 

    def load(self):
        gtk.gdk.threads_enter()
        self.get_widget("status").set_text(_("Loading..."))
        self.items = filter(lambda item: self.vcs.is_versioned(item.path),
                            self.vcs.get_items(self.paths, self.vcs.STATUSES_FOR_COMMIT))    
        self.populate_files_from_original()
        self.get_widget("status").set_text(_("Found %d item(s)") % len(self.items))
        gtk.gdk.threads_leave()
    
    def refresh_row_status(self):
        status = self.get_last_status()
        self.files_table.get_row(self.last_row_clicked)[3] =  status
        
        # Files newly marked as deleted should be checked off
        if status == self.vcs.STATUS["deleted"]:
            self.files_table.get_row(self.last_row_clicked)[0] = True
        
        # Ignored/Normal files should not be shown
        index = 0
        for item in self.files_table.get_items():
            if (self.vcs.is_normal(item[1]) or
                    self.vcs.is_ignored(item[1])):
                self.files_table.remove(index)
                del self.items[index]
                index -= 1
            index += 1
    
    def get_last_path(self):
        return self.files_table.get_row(self.last_row_clicked)[1]
    
    def get_last_status(self):
        path = self.get_last_path()
        
        text_status = None
        try:
            text_status = self.vcs.status(path)[0].text_status
        except Exception, e:
            print str(e)

        return text_status

    def populate_files_from_original(self):
        self.files_table.clear()

        for item in self.items:
            checked = True
            
            # Some types of files should not be checked off
            if (not item.is_versioned 
                    or item.text_status == self.vcs.STATUS["missing"]):
                checked = False
            
            if self.SHOW_UNVERSIONED or item.is_versioned:
                self.files_table.append([
                    checked,
                    item.path, 
                    nautilussvn.lib.helper.get_file_extension(item.path),
                    item.text_status,
                    item.prop_status
                ])
    
    def choose_patch_path(self):
        path = ""
        
        dialog = gtk.FileChooserDialog(
            _("Create Patch"),
            None,
            gtk.FILE_CHOOSER_ACTION_SAVE,(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                          gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_current_folder_uri(
            gnomevfs.get_uri_from_local_path(get_common_directory(self.paths))
        )
        response = dialog.run()
        
        if response == gtk.RESPONSE_OK:
            path = dialog.get_filename()
            
        dialog.destroy()
        
        return path

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
        
        path = self.choose_patch_path()
        if not path:
            self.close()
            return
      
        ticks = len(items)*2
        self.action = nautilussvn.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.set_pbar_ticks(ticks)
        self.action.append(self.action.set_header, _("Create Patch"))
        self.action.append(self.action.set_status, _("Creating Patch File..."))
        
        def create_patch_action(patch_path, patch_items, base_dir):
            fileObj = open(patch_path,"w")
            
            # PySVN takes a path to create its own temp files...
            temp_dir = tempfile.mkdtemp(prefix=nautilussvn.TEMP_DIR_PREFIX)
            
            os.chdir(base_dir)
           
            # Add to the Patch file only the selected items
            for item in patch_items:
                rel_path = nautilussvn.lib.helper.get_relative_path(base_dir, item)
                diff_text = self.vcs.diff(temp_dir, rel_path)
                fileObj.write(diff_text)
    
            fileObj.close()            
        
            # Note: if we don't want to ignore errors here, we could define a
            # function that logs failures.
            shutil.rmtree(temp_dir, ignore_errors = True)
        
        self.action.append(create_patch_action, path, items, self.common)
        
        self.action.append(self.action.set_status, _("Patch File Created"))
        self.action.append(self.action.finish)
        self.action.start()
        
        # TODO: Open the diff file (meld is going to add support in a future version :()
        # nautilussvn.lib.helper.launch_diff_tool(path)
        
    def on_toggle_show_all_toggled(self, widget, data=None):
        self.TOGGLE_ALL = not self.TOGGLE_ALL
        for row in self.files_table.get_items():
            row[0] = self.TOGGLE_ALL
            

    def on_toggle_show_unversioned_toggled(self, widget, data=None):
        self.SHOW_UNVERSIONED = not self.SHOW_UNVERSIONED
        self.populate_files_from_original()
    
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
                        "label": _("View Diff"),
                        "signals": {
                            "activate": {
                                "callback": self.on_context_diff_activated, 
                                "args": fileinfo
                            }
                        },
                        "condition": self.condition_view_diff
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
                    },
                    {
                        "label": _("Delete"),
                        "signals": {
                            "activate": {
                                "callback": self.on_context_delete_activated, 
                                "args": fileinfo
                            }
                        },
                        "condition": self.condition_delete
                    },
                    {
                        "label": _("Add"),
                        "signals": {
                            "activate": {
                                "callback": self.on_context_add_activated, 
                                "args": fileinfo
                            }
                        },
                        "condition": self.condition_add
                    },
                    {
                        "label": _("Revert"),
                        "signals": {
                            "activate": {
                                "callback": self.on_context_revert_activated, 
                                "args": fileinfo
                            }
                        },
                        "condition": self.condition_revert
                    },
                    {
                        "label": _("Restore"),
                        "signals": {
                            "activate": {
                                "callback": self.on_context_restore_activated, 
                                "args": fileinfo
                            }
                        },
                        "condition": self.condition_restore
                    },
                    {
                        "label": _("Add to ignore list"),
                        'submenu': [
                            {
                                "label": os.path.basename(fileinfo[1]),
                                "signals": {
                                    "activate": {
                                        "callback": self.on_subcontext_ignore_by_filename_activated, 
                                        "args": fileinfo
                                     }
                                 },
                                "condition": (lambda: True)
                            },
                            {
                                "label": "*%s"%fileinfo[2],
                                "signals": {
                                    "activate": {
                                        "callback": self.on_subcontext_ignore_by_fileext_activated, 
                                        "args": fileinfo
                                    }
                                },
                                "condition": self.condition_ignore_by_fileext
                            }
                        ],
                        "condition": (lambda: True)
                    }
                ])
                context_menu.show(event)

    def on_files_table_row_doubleclicked(self, treeview, event, col):
        treeview.grab_focus()
        treeview.set_cursor(event[0], col, 0)
        treeview_model = treeview.get_model()
        fileinfo = treeview_model[event[0]]
        
        nautilussvn.lib.helper.launch_diff_tool(fileinfo[1])

    def on_context_add_activated(self, widget, data=None):
        self.vcs.add(data[1])
        self.files_table.get_row(self.last_row_clicked)[0] = True
        self.refresh_row_status()

    def on_context_revert_activated(self, widget, data=None):
        self.vcs.revert(data[1])
        self.refresh_row_status()

    def on_context_diff_activated(self, widget, data=None):
        nautilussvn.lib.helper.launch_diff_tool(data[1])

    def on_context_open_activated(self, widget, data=None):
        nautilussvn.lib.helper.open_item(data[1])
        
    def on_context_browse_activated(self, widget, data=None):
        nautilussvn.lib.helper.browse_to_item(data[1])

    def on_context_delete_activated(self, widget, data=None):
        if self.vcs.is_versioned(data[1]):
            self.vcs.remove(data[1], force=True)
            self.refresh_row_status()
        else:
            confirm = nautilussvn.ui.dialog.DeleteConfirmation(data[1])
            
            if confirm.run():
                nautilussvn.lib.helper.delete_item(data[1])
                self.files_table.remove(self.last_row_clicked)
            
    def on_subcontext_ignore_by_filename_activated(self, widget, data=None):
        prop_name = self.vcs.PROPERTIES["ignore"]
        prop_value = os.path.basename(data[1])

        if self.vcs.propset(data[1], prop_name, prop_value):
            self.refresh_row_status()
        
    def on_subcontext_ignore_by_fileext_activated(self, widget, data=None):
        prop_name = self.vcs.PROPERTIES["ignore"]
        prop_value = "*%s" % data[2]
        
        if self.vcs.propset(data[1], prop_name, prop_value):
            self.refresh_row_status()

    def on_context_restore_activated(self, widget, data=None):
        nautilussvn.lib.helper.launch_ui_window(
            "update", 
            [data[1]],
            return_immmediately=False
        )
        self.refresh_row_status()
        
    
    # Conditions
    
    def condition_add(self):
        return (
            self.get_last_status() in [
                self.vcs.STATUS["unversioned"]
            ]
        )
    
    def condition_revert(self):
        return (
            self.get_last_status() in [
                self.vcs.STATUS["added"],
                self.vcs.STATUS["deleted"],
                self.vcs.STATUS["modified"]
            ]
        )

    def condition_view_diff(self):
        return (
            self.get_last_status() in [
                self.vcs.STATUS["modified"]
            ]
        )

    def condition_restore(self):
        return (
            self.get_last_status() in [
                self.vcs.STATUS["missing"]
            ]
        )

    def condition_delete(self):
        return (
            self.get_last_status() not in [
                self.vcs.STATUS["deleted"]
            ]
        )
    
    def condition_ignore_by_fileext(self):
        return os.path.isfile(self.get_last_path())

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
        
    window = CreatePatch(paths)
    window.register_gtk_quit()
    gtk.main()
