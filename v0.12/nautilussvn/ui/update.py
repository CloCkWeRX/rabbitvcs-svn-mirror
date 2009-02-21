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

from nautilussvn.ui import InterfaceNonView
from nautilussvn.ui.log import LogDialog
from nautilussvn.ui.action import VCSAction
import nautilussvn.ui.widget
import nautilussvn.ui.dialog

from nautilussvn import gettext
_ = gettext.gettext

class Update(InterfaceNonView):
    """
    This class provides an interface to generate an "update".
    Pass it a path and it will start an update, running the notification dialog.  
    There is no glade .
    
    """

    def __init__(self, paths):
        self.paths = paths
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()

    def start(self):
        self.action = VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.append(self.action.set_header, _("Update"))
        self.action.append(self.action.set_status, _("Updating..."))
        for item in self.paths:
            self.action.append(self.vcs.update, item)
        self.action.append(self.action.set_status, _("Completed Update"))
        self.action.append(self.action.finish)
        self.action.start()

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

    window = Update(paths)
    window.register_gtk_quit()
    window.start()
    gtk.main()
