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
from nautilussvn.ui.log import LogDialog
import nautilussvn.ui.widget
import nautilussvn.ui.dialog
import nautilussvn.ui.action
import nautilussvn.lib.helper
import nautilussvn.lib.vcs

from nautilussvn import gettext
_ = gettext.gettext

class Checkout(InterfaceView):
    """
    Provides an interface to check out a working copy.
    
    Pass it the destination path.
    
    """

    def __init__(self, path):
        InterfaceView.__init__(self, "checkout", "Checkout")

        nautilussvn.lib.helper.setcwd(path)

        self.get_widget("Checkout").set_title(_("Checkout - %s") % path)
        
        self.path = path
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()

        self.repositories = nautilussvn.ui.widget.ComboBox(
            self.get_widget("repositories"), 
            nautilussvn.lib.helper.get_repository_paths()
        )
        self.destination = path
        self.get_widget("destination").set_text(path)
        self.complete = False
        
    #
    # UI Signal Callback Methods
    #

    def on_destroy(self, widget):
        self.close()

    def on_cancel_clicked(self, widget):
        self.close()

    def on_ok_clicked(self, widget):
        url = self.get_widget("url").get_text()
        path = self.get_widget("destination").get_text()
        omit_externals = self.get_widget("omit_externals").get_active()
        recursive = self.get_widget("recursive").get_active()
        
        if not url or not path:
            nautilussvn.ui.dialog.MessageBox(_("The repository URL and destination path are both required fields."))
            return

        if path.startswith("file://"):
            path = path[7:]        
        
        revision = self.vcs.revision("head")
        if self.get_widget("revision_number_opt").get_active():
            revision = self.vcs.revision(
                "number",
                number=int(self.get_widget("revision_number").get_text())
            )
    
        self.hide()
        self.action = nautilussvn.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.append(self.action.set_header, _("Checkout"))
        self.action.append(self.action.set_status, _("Running Checkout Command..."))
        self.action.append(nautilussvn.lib.helper.save_repository_path, url)
        self.action.append(
            self.vcs.checkout,
            url,
            path,
            recurse=recursive,
            revision=revision,
            ignore_externals=omit_externals
        )
        self.action.append(self.action.set_status, _("Completed Checkout"))
        self.action.append(self.action.finish)
        self.action.start()

    def on_revision_number_focused(self, widget, data=None):
        if self.complete:
            self.get_widget("revision_number_opt").set_active(True)

    def on_file_chooser_clicked(self, widget, data=None):
        chooser = nautilussvn.ui.dialog.FolderChooser()
        path = chooser.run()
        if path is not None:
            self.get_widget("destination").set_text(path)

    def on_show_log_clicked(self, widget, data=None):
        LogDialog(
            self.get_widget("url").get_text(), 
            ok_callback=self.on_log_closed
        )
    
    def on_log_closed(self, data):
        if data is not None:
            self.get_widget("revision_number_opt").set_active(True)
            self.get_widget("revision_number").set_text(data)
    
    def on_url_changed(self, widget, data=None):
    
        url = self.get_widget("url").get_text()
        tmp = url.replace("//", "/").split("/")[1:]
        append = ""
        prev = ""
        while len(tmp):
            prev = append
            append = tmp.pop()
            if append not in ("trunk", "branches", "tags"):
                break
                
            if append in ("http:", "https:", "file:", "svn:", "svn+ssh:"):
                append = ""
                break
                
        self.get_widget("destination").set_text(
            os.path.join(self.destination, append)
        )
    
        self.complete = False
        if url:
            self.complete = True
        
        self.get_widget("show_log").set_sensitive(self.complete)
        self.get_widget("ok").set_sensitive(self.complete)

if __name__ == "__main__":
    from os import getcwd
    from sys import argv

    args = argv[1:]
    path = getcwd()
    if args:
        if args[0] != ".":
            path = args[0]
            
    window = Checkout(path)
    window.register_gtk_quit()
    gtk.main()
