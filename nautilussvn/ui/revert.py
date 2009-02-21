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
from nautilussvn.ui.add import Add
from nautilussvn.ui.action import VCSAction
import nautilussvn.ui.widget
import nautilussvn.ui.dialog
import nautilussvn.ui.action
import nautilussvn.lib.helper

from nautilussvn import gettext
_ = gettext.gettext

class Revert(Add):
    def __init__(self, paths):
        InterfaceView.__init__(self, "add", "Add")

        self.window = self.get_widget("Add")
        self.window.set_title(_("Revert"))

        self.paths = paths
        self.last_row_clicked = None
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()
        self.items = None
        self.statuses = self.vcs.STATUSES_FOR_REVERT
        self.files_table = nautilussvn.ui.widget.Table(
            self.get_widget("files_table"), 
            [gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [nautilussvn.ui.widget.TOGGLE_BUTTON, _("Path"), _("Extension")]
        )

        try:
            thread.start_new_thread(self.load, ())
        except Exception, e:
            print str(e)
                    
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
        
        self.action.append(self.action.set_header, _("Revert"))
        self.action.append(self.action.set_status, _("Running Revert Command..."))
        self.action.append(self.vcs.revert, items, recurse=True)
        self.action.append(self.action.set_status, _("Completed Revert"))
        self.action.append(self.action.finish)
        self.action.start()

    #
    # Context Menu Conditions
    #
    
    def condition_delete(self):
        return False

    def condition_ignore_submenu(self):
        return False

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

    window = Revert(paths)
    window.register_gtk_quit()
    gtk.main()
