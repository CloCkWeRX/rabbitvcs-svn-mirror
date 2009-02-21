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
from nautilussvn.ui.action import VCSAction
import nautilussvn.lib.vcs

from nautilussvn import gettext
_ = gettext.gettext

class Cleanup(InterfaceNonView):
    """
    This class provides a handler to the Cleanup window view.
    The idea is that it displays a large folder icon with a label like
    "Please Wait...".  Then when it finishes cleaning up, the label will 
    change to "Finished cleaning up /path/to/folder"
    
    """

    def __init__(self, path):
        InterfaceNonView.__init__(self)
        self.path = path
        nautilussvn.lib.helper.setcwd(path)
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()

    def start(self):
        self.action = VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        
        self.action.append(self.action.set_header, _("Cleanup"))
        self.action.append(self.action.set_status, _("Cleaning Up..."))
        self.action.append(self.vcs.cleanup, self.path)
        self.action.append(self.action.set_status, _("Completed Cleanup"))
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
            
    window = Cleanup(path)
    window.register_gtk_quit()
    window.start()
    gtk.main()
