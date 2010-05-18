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

import os.path

import pygtk
import gobject
import gtk

from rabbitvcs.ui import InterfaceNonView
from rabbitvcs.ui.action import VCSAction
from rabbitvcs.ui.dialog import MessageBox, OneLineTextChange
import rabbitvcs.vcs

from rabbitvcs import gettext
_ = gettext.gettext

class Rename(InterfaceNonView):
    def __init__(self, path):
        InterfaceNonView.__init__(self)

        self.vcs = rabbitvcs.vcs.create_vcs_instance()
        
        self.path = path
        (self.dir, self.filename) = os.path.split(self.path)
        
        dialog = OneLineTextChange(_("Rename"), _("New Name:"), self.filename)
        (result, new_filename) = dialog.run()

        if result != gtk.RESPONSE_OK:
            self.close()
            return
       
        if not new_filename:
            MessageBox(_("The new name field is required"))
            return
        
        new_path = os.path.join(self.dir, new_filename)
        
        self.action = rabbitvcs.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        
        self.action.append(self.action.set_header, _("Rename"))
        self.action.append(self.action.set_status, _("Running Rename Command..."))
        self.action.append(
            self.vcs.move, 
            self.path,
            new_path
        )
        self.action.append(self.action.set_status, _("Completed Rename"))
        self.action.append(self.action.finish)
        self.action.start()
        
if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs rename [path]")
            
    window = Rename(paths[0])
    window.register_gtk_quit()
    gtk.main()
