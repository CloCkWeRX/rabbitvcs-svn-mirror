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

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.checkout import Checkout
from rabbitvcs.ui.dialog import MessageBox
from rabbitvcs.ui.action import VCSAction
import rabbitvcs.lib.helper

from rabbitvcs import gettext
_ = gettext.gettext

class Export(Checkout):
    def __init__(self, path=None, revision=None):
        Checkout.__init__(self, path, url=None, revision=revision)
        
        self.get_widget("Checkout").set_title(_("Export - %s") % path)
        
        # If the given path is a working copy, then export FROM the path
        # Otherwise export TO the path
        if self.vcs.is_in_a_or_a_working_copy(path):
            self.repositories.set_child_text(path)
            self.get_widget("destination").set_text("")
        else:
            self.repositories.set_child_text("")
            self.get_widget("destination").set_text(path)

    def on_ok_clicked(self, widget):
        url = self.repositories.get_active_text()
        path = self.get_widget("destination").get_text()
        omit_externals = self.get_widget("omit_externals").get_active()
        recursive = self.get_widget("recursive").get_active()

        if not url or not path:
            MessageBox(_("The repository URL and destination path are both required fields."))
            return
        
        if url.startswith("file://"):
            url = url[7:]
        
        # Cannot do:
        # url = os.path.normpath(url)
        # ...in general, since it might be eg. an http URL. Doesn't seem to
        # affect pySvn though.
        
        if path.startswith("file://"):
            path = path[7:]
        
        path = os.path.normpath(path)
        
        revision = self.vcs.revision("head")
        if self.get_widget("revision_number_opt").get_active():
            revision = self.vcs.revision(
                "number",
                number=int(self.get_widget("revision_number").get_text())
            )
    
        self.hide()
        self.action = VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        
        self.action.append(self.action.set_header, _("Export"))
        self.action.append(self.action.set_status, _("Running Export Command..."))
        self.action.append(rabbitvcs.lib.helper.save_repository_path, url)
        self.action.append(
            self.vcs.export,
            url,
            path,
            force=True,
            recurse=recursive,
            revision=revision,
            ignore_externals=omit_externals
        )
        self.action.append(self.action.set_status, _("Completed Export"))
        self.action.append(self.action.finish)
        self.action.start()
        
if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main()
            
    window = Export(paths[0], revision=options.revision)
    window.register_gtk_quit()
    gtk.main()
