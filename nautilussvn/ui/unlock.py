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

from nautilussvn.ui import InterfaceView, InterfaceNonView
from nautilussvn.ui.add import Add
from nautilussvn.ui.action import VCSAction
import nautilussvn.ui.widget
import nautilussvn.ui.dialog
import nautilussvn.ui.action
import nautilussvn.lib.helper
from nautilussvn.lib.log import Log

log = Log("nautilussvn.ui.unlock")

from nautilussvn import gettext
_ = gettext.gettext

class Unlock(Add):
    def __init__(self, paths):
        InterfaceView.__init__(self, "add", "Add")

        self.window = self.get_widget("Add")
        self.window.set_title(_("Unlock"))

        self.paths = paths
        self.last_row_clicked = None
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()
        self.items = None
        self.statuses = None
        self.files_table = nautilussvn.ui.widget.Table(
            self.get_widget("files_table"), 
            [gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [nautilussvn.ui.widget.TOGGLE_BUTTON, _("Path"), _("Extension")]
        )

        try:
            thread.start_new_thread(self.load, ())
        except Exception, e:
            log.exception()
        
        
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
                nautilussvn.lib.helper.get_file_extension(item.path)
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

        self.action = nautilussvn.ui.action.VCSAction(
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

    #
    # Context Menu Conditions
    #
    
    def condition_delete(self):
        return False

    def condition_ignore_submenu(self):
        return False

class UnlockQuick(InterfaceNonView):
    """
    This class provides a handler to unlock functionality.
    
    """

    def __init__(self, path):
        InterfaceNonView.__init__(self)
        self.path = path
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()

    def start(self):
        self.vcs.unlock(self.path, force=True)
        
if __name__ == "__main__":
    from nautilussvn.ui import main
    (options, paths) = main()
        
    window = Unlock(paths)
    window.register_gtk_quit()
    gtk.main()
