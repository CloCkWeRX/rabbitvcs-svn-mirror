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
from nautilussvn.ui.log import LogDialog
from nautilussvn.ui.action import VCSAction
import nautilussvn.ui.widget
import nautilussvn.ui.dialog
from nautilussvn.lib.helper import setcwd

from nautilussvn import gettext
_ = gettext.gettext

class UpdateToRevision(InterfaceView):
    """
    This class provides an interface to update a working copy to a specific
    revision.  It has a glade .
    
    """

    def __init__(self, path):
        InterfaceView.__init__(self, "update", "Update")
        setcwd(path)
        self.path = path
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()

    def on_destroy(self, widget):
        self.close()

    def on_cancel_clicked(self, widget):
        self.close()

    def on_ok_clicked(self, widget):

        revision = self.vcs.revision("head")
        if self.get_widget("revision_number_opt").get_active():
            revision = self.vcs.revision(
                "number",
                number=int(self.get_widget("revision_number").get_text())
            )
        recursive = self.get_widget("recursive").get_active()
        omit_externals = self.get_widget("omit_externals").get_active()

        self.action = VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        
        self.action.append(self.action.set_header, _("Update To Revision"))
        self.action.append(self.action.set_status, _("Updating..."))
        self.action.append(
            self.vcs.update, 
            self.path,
            revision=revision,
            recurse=recursive,
            ignore_externals=omit_externals
        )
        self.action.append(self.action.set_status, _("Completed Update"))
        self.action.append(self.action.finish)
        self.action.start()

    def on_revision_number_focused(self, widget, data=None):
        self.get_widget("revision_number_opt").set_active(True)

    def on_show_log_clicked(self, widget, data=None):
        LogDialog(self.path, ok_callback=self.on_log_closed)
    
    def on_log_closed(self, data):
        if data is not None:
            self.get_widget("revision_number_opt").set_active(True)
            self.get_widget("revision_number").set_text(data)

if __name__ == "__main__":
    from os import getcwd
    from sys import argv

    args = argv[1:]
    path = getcwd()
    if args:
        if args[0] != ".":
            path = args[0]
            
    window = UpdateToRevision(path)
    window.register_gtk_quit()
    gtk.main()
