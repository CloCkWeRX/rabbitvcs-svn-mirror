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

import os.path

import pygtk
import gobject
import gtk

from nautilussvn.ui import InterfaceView
from nautilussvn.ui.action import VCSAction
from nautilussvn.ui.dialog import MessageBox
import nautilussvn.lib.vcs
from nautilussvn.lib.helper import setcwd

from nautilussvn import gettext
_ = gettext.gettext

class Rename(InterfaceView):
    def __init__(self, path):
        InterfaceView.__init__(self, "rename", "Rename")
        
        setcwd(path)
        
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()
        
        self.path = path
        (self.dir, self.filename) = os.path.split(self.path)
        
        self.get_widget("new_name").set_text(self.filename)
        
    def on_destroy(self, widget):
        self.close()

    def on_cancel_clicked(self, widget):
        self.close()

    def on_ok_clicked(self, widget):
        
        new_name = self.get_widget("new_name").get_text()
        if not new_name:
            MessageBox(_("The new name field is required"))
            return
        
        new_path = os.path.join(self.dir, new_name)
        
        self.hide()
        self.action = nautilussvn.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        
        self.action.append(self.action.set_header, _("Rename"))
        self.action.append(self.action.set_status, _("Running Rename Command..."))
        self.action.append(
            self.vcs.move, 
            self.path,
            new_path,
            force=True
        )
        self.action.append(self.action.set_status, _("Completed Rename"))
        self.action.append(self.action.finish)
        self.action.start()
        
if __name__ == "__main__":
    from os import getcwd
    from sys import argv
    
    args = argv[1:]
    path = getcwd()
    if args:
        if args[0] != ".":
            path = args[0]
            
    window = Rename(path)
    window.register_gtk_quit()
    gtk.main()
