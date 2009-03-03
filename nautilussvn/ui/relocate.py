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

import pygtk
import gobject
import gtk

from nautilussvn.ui import InterfaceView
from nautilussvn.ui.action import VCSAction
from nautilussvn.ui.dialog import MessageBox
import nautilussvn.lib.vcs
import nautilussvn.lib.helper

from nautilussvn import gettext
_ = gettext.gettext

class Relocate(InterfaceView):
    """
    Interface to relocate your working copy's repository location.
    
    """

    def __init__(self, path):
        """
        @type   path: string
        @param  path: A path to a local working copy
        
        """
        
        InterfaceView.__init__(self, "relocate", "Relocate")
        

        self.path = path
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()
        
        repo = self.vcs.get_repo_url(self.path)
        self.get_widget("from_url").set_text(repo)
        self.get_widget("to_url").set_text(repo)
        
        self.repositories = nautilussvn.ui.widget.ComboBox(
            self.get_widget("to_urls"), 
            nautilussvn.lib.helper.get_repository_paths()
        )

    def on_destroy(self, widget):
        self.close()

    def on_cancel_clicked(self, widget):
        self.close()

    def on_ok_clicked(self, widget):
    
        from_url = self.get_widget("from_url").get_text()
        to_url = self.get_widget("to_url").get_text()
    
        if not from_url or not to_url:
            MessageBox(_("The from and to url fields are both required."))
            return
    
        self.hide()

        self.action = VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        
        self.action.append(self.action.set_header, _("Relocate"))
        self.action.append(self.action.set_status, _("Running Relocate Command..."))
        self.action.append(
            self.vcs.relocate, 
            from_url,
            to_url,
            self.path
        )
        self.action.append(self.action.set_status, _("Completed Relocate"))
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
            
    window = Relocate(path)
    window.register_gtk_quit()
    gtk.main()
