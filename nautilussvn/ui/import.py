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
import nautilussvn.ui.widget
import nautilussvn.ui.dialog
import nautilussvn.lib.helper

from nautilussvn import gettext
_ = gettext.gettext

class Import(InterfaceView):
    def __init__(self, path):
        InterfaceView.__init__(self, "import", "Import")
        
        
        self.get_widget("Import").set_title(_("Import - %s") % path)
        
        self.path = path
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()
        
        if self.vcs.is_in_a_or_a_working_copy(path):
            self.get_widget("repository").set_text(self.vcs.get_repo_url(path))
        
        self.repositories = nautilussvn.ui.widget.ComboBox(
            self.get_widget("repositories"), 
            nautilussvn.lib.helper.get_repository_paths()
        )
        
        self.message = nautilussvn.ui.widget.TextView(
            self.get_widget("message")
        )

    def on_destroy(self, widget):
        self.close()

    def on_cancel_clicked(self, widget):
        self.close()

    def on_ok_clicked(self, widget):
        
        url = self.get_widget("repository").get_text()
        if not url:
            nautilussvn.ui.dialog.MessageBox(_("The repository URL field is required."))
            return
            
        ignore = not self.get_widget("include_ignored").get_active()
        
        self.hide()

        self.action = nautilussvn.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        
        self.action.append(self.action.set_header, _("Import"))
        self.action.append(self.action.set_status, _("Running Import Command..."))
        self.action.append(
            self.vcs.import_, 
            self.path,
            url,
            self.message.get_text(),
            ignore=ignore
        )
        self.action.append(self.action.set_status, _("Completed Import"))
        self.action.append(self.action.finish)
        self.action.start()

    def on_previous_messages_clicked(self, widget, data=None):
        dialog = nautilussvn.ui.dialog.PreviousMessages()
        message = dialog.run()
        if message is not None:
            self.message.set_text(message)

if __name__ == "__main__":
    from os import getcwd
    from sys import argv
    
    args = argv[1:]
    path = getcwd()
    if args:
        if args[0] != ".":
            path = args[0]
            
    window = Import(path)
    window.register_gtk_quit()
    gtk.main()
