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

from rabbitvcs.ui import InterfaceView
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
import rabbitvcs.lib.helper
import rabbitvcs.lib.vcs
from rabbitvcs.lib.log import Log

log = Log("rabbitvcs.ui.add")

from rabbitvcs import gettext
_ = gettext.gettext

gtk.gdk.threads_init()

class Add(InterfaceView):
    """
    Provides an interface for the user to add unversioned files to a
    repository.  Also, provides a context menu with some extra functionality.
    
    Send a list of paths to be added
    
    """

    TOGGLE_ALL = True

    def __init__(self, paths, base_dir=None):
        InterfaceView.__init__(self, "add", "Add")
        
        self.paths = paths
        self.base_dir = base_dir
        self.last_row_clicked = None
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        self.items = []
        self.statuses = [self.vcs.STATUS["unversioned"], self.vcs.STATUS["obstructed"]]
        self.files_table = rabbitvcs.ui.widget.Table(
            self.get_widget("files_table"), 
            [gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [rabbitvcs.ui.widget.TOGGLE_BUTTON, _("Path"), _("Extension")],
            base_dir=base_dir,
            path_entries=[1]
        )

        try:
            thread.start_new_thread(self.load, ())
        except Exception, e:
            log.exception(e)

    #
    # Helpers
    #

    def load(self):
        gtk.gdk.threads_enter()
        self.get_widget("status").set_text(_("Loading..."))
        self.items = self.vcs.get_items(self.paths, self.statuses)
        self.populate_files_table()
        self.get_widget("status").set_text(_("Found %d item(s)") % len(self.items))
        gtk.gdk.threads_leave()

    def populate_files_table(self):
        self.files_table.clear()
        for item in self.items:
            self.files_table.append([
                True, 
                item.path, 
                rabbitvcs.lib.helper.get_file_extension(item.path)
            ])
    
    #
    # UI Signal Callbacks
    #
    
    def on_destroy(self, widget):
        self.close()
        
    def on_cancel_clicked(self, widget):
        self.close()

    def on_ok_clicked(self, widget):
        items = self.files_table.get_activated_rows(1)
        if not items:
            self.close()
            return

        self.hide()

        self.action = rabbitvcs.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.append(self.action.set_header, _("Add"))
        self.action.append(self.action.set_status, _("Running Add Command..."))
        self.action.append(self.vcs.add, items)
        self.action.append(self.action.set_status, _("Completed Add"))
        self.action.append(self.action.finish)
        self.action.start()

    def on_select_all_toggled(self, widget):
        self.TOGGLE_ALL = not self.TOGGLE_ALL
        for row in self.files_table.get_items():
            row[0] = self.TOGGLE_ALL

    def on_files_table_button_pressed(self, treeview, event=None, user_data=None):
        if event.button == 3:
            pathinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
            if pathinfo is not None:
                path, col, cellx, celly = pathinfo
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                
                treeview_model = treeview.get_model().get_model()
                fileinfo = treeview_model[path]

                self.last_row_clicked = path[0]
                
                context_menu = rabbitvcs.ui.widget.ContextMenu([{
                        "label": _("Open"),
                        "signals": {
                            "activate": {
                                "callback": self.on_context_open_activated, 
                                "args": fileinfo
                            }
                        },
                        "condition": {
                            "callback": self.condition_open
                        }
                    },{
                        "label": _("Browse to"),
                        "signals": {
                            "activate": {
                                "callback": self.on_context_browse_activated, 
                                "args": fileinfo
                            }
                        },
                        "condition": {
                            "callback": self.condition_browseto
                        }
                    },{
                        "label": _("Delete"),
                        "signals": {
                            "activate": {
                                "callback": self.on_context_delete_activated, 
                                "args": fileinfo
                            }
                        },
                        "condition": {
                            "callback": self.condition_delete
                        }
                    },{
                        "label": _("Add to ignore list"),
                        'submenu': [{
                                "label": os.path.basename(fileinfo[1]),
                                "signals": {
                                    "button-press-event": {
                                        "callback": self.on_subcontext_ignore_by_filename_activated, 
                                        "args": fileinfo
                                     }
                                 },
                                "condition": {
                                    "callback": (lambda: True)
                                }
                            },
                            {
                                "label": "*%s"%fileinfo[2],
                                "signals": {
                                    "button-press-event": {
                                        "callback": self.on_subcontext_ignore_by_fileext_activated, 
                                        "args": fileinfo
                                    }
                                },
                                "condition": {
                                    "callback": (lambda: True)
                                }
                            }
                        ],
                        "condition": {
                            "callback": self.condition_ignore_submenu
                        }
                    }
                ])
                context_menu.show(event)
                
    def on_context_open_activated(self, widget, data=None):
        rabbitvcs.lib.helper.open_item(data[1])
        
    def on_context_browse_activated(self, widget, data=None):
        rabbitvcs.lib.helper.browse_to_item(data[1])

    def on_context_delete_activated(self, widget, data=None):
        confirm = rabbitvcs.ui.dialog.DeleteConfirmation(data[1])
        
        if confirm.run():
            rabbitvcs.lib.helper.delete_item(data[1])
            self.files_table.remove(self.last_row_clicked)

    def on_subcontext_ignore_by_filename_activated(self, widget, data=None, userdata=None):
        prop_name = self.vcs.PROPERTIES["ignore"]
        prop_value = os.path.basename(userdata[1])
        
        if self.vcs.propset(self.base_dir, prop_name, prop_value):
            self.files_table.remove(self.last_row_clicked)
        
    def on_subcontext_ignore_by_fileext_activated(self, widget, data=None):
        prop_name = self.vcs.PROPERTIES["ignore"]
        prop_value = "*%s" % userdata[2]
        
        if self.vcs.propset(self.base_dir, prop_name, prop_value, recurse=True, userdata=None):
            # Ignored/Normal files should not be shown
            index = 0
            for item in self.files_table.get_items():
                if (self.vcs.is_normal(item[1]) or
                        self.vcs.is_ignored(item[1])):
                    self.files_table.remove(index)
                    del self.items[index]
                    index -= 1
                index += 1
            
    #
    # Context Menu Conditions
    #
    
    def condition_delete(self, data=None):
        return True
    
    def condition_ignore_submenu(self, data=None):
        return True

    def condition_open(self, data=None):
        path = self.files_table.get_row(self.last_row_clicked)[1]
        return os.path.isfile(path)

    def condition_browseto(self, data=None):
        path = self.files_table.get_row(self.last_row_clicked)[1]
        return os.path.exists(path)

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main()

    window = Add(paths, options.base_dir)
    window.register_gtk_quit()
    gtk.main()
