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

from rabbitvcs.ui import InterfaceView, InterfaceNonView
from rabbitvcs.ui.add import Add
from rabbitvcs.ui.action import VCSAction
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
import rabbitvcs.lib.helper
from rabbitvcs.lib.log import Log

log = Log("rabbitvcs.ui.unlock")

from rabbitvcs import gettext
_ = gettext.gettext

class Unlock(Add):
    def __init__(self, paths, base_dir):
        InterfaceView.__init__(self, "add", "Add")

        self.window = self.get_widget("Add")
        self.window.set_title(_("Unlock"))

        self.paths = paths
        self.base_dir = base_dir
        self.last_row_clicked = None
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        self.items = None
        self.statuses = None
        self.files_table = rabbitvcs.ui.widget.Table(
            self.get_widget("files_table"), 
            [gobject.TYPE_BOOLEAN, rabbitvcs.ui.widget.TYPE_PATH, 
                gobject.TYPE_STRING], 
            [rabbitvcs.ui.widget.TOGGLE_BUTTON, _("Path"), _("Extension")],
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

        self.initialize_items()
        
        
    #
    # Helpers
    #

    def load(self):
        gtk.gdk.threads_enter()
        self.get_widget("status").set_text(_("Loading..."))
        self.items = self.vcs.get_items(self.paths, self.statuses)
        self.populate_files_table()
        gtk.gdk.threads_leave()
    
    def populate_files_table(self):
        found = 0
        for item in self.items:
            if item.text_status in (self.vcs.STATUS["unversioned"], self.vcs.STATUS["ignored"]):
                continue
                
            if not self.vcs.is_locked(item.path):
                continue
        
            self.files_table.append([
                True, 
                item.path, 
                rabbitvcs.lib.helper.get_file_extension(item.path)
            ])
            found += 1
            
        self.get_widget("status").set_text(_("Found %d item(s)") % found)
    
    #
    # UI Signal Callbacks
    #
             
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
        
        self.action.append(self.action.set_header, _("Unlock"))
        self.action.append(self.action.set_status, _("Running Unlock Command..."))
        for item in items:
            self.action.append(self.vcs.unlock, item, force=True)
        self.action.append(self.action.set_status, _("Completed Unlock"))
        self.action.append(self.action.finish)
        self.action.start()

class UnlockQuick(InterfaceNonView):
    """
    This class provides a handler to unlock functionality.
    
    """

    def __init__(self, paths):
        InterfaceNonView.__init__(self)
        self.path = paths
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()

    def start(self):
        for path in self.paths:
            self.vcs.unlock(self.paths, force=True)
        
if __name__ == "__main__":
    from rabbitvcs.ui import main, BASEDIR_OPT
    (options, paths) = main(
        [BASEDIR_OPT],
        usage="Usage: rabbitvcs unlock [path1] [path2] ..."
    )
        
    window = Unlock(paths, options.base_dir)
    window.register_gtk_quit()
    gtk.main()
