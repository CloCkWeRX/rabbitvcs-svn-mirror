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
from rabbitvcs.ui.log import LogDialog
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
import rabbitvcs.lib.helper
import rabbitvcs.lib.vcs

from rabbitvcs import gettext
_ = gettext.gettext

class Checkout(InterfaceView):
    """
    Provides an interface to check out a working copy.
    
    Pass it the destination path.
    
    """

    def __init__(self, path=None, url=None, revision=None):
        InterfaceView.__init__(self, "checkout", "Checkout")


        self.get_widget("Checkout").set_title(_("Checkout - %s") % path)
        
        self.path = path
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()

        self.repositories = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("repositories"), 
            rabbitvcs.lib.helper.get_repository_paths()
        )

        self.revision_selector = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("revision_container"),
            self.vcs,
            revision=revision,
            url_combobox=self.repositories,
            expand=True
        )
        
        self.destination = rabbitvcs.lib.helper.get_user_path()
        if path is not None:
            self.destination = path
            self.get_widget("destination").set_text(path)
        
        if url is not None:
            self.repositories.set_child_text(url)
        
        self.complete = False
        self.check_form()
        
    #
    # UI Signal Callback Methods
    #

    def on_destroy(self, widget):
        self.close()

    def on_cancel_clicked(self, widget):
        self.close()

    def on_ok_clicked(self, widget):
        url = self.repositories.get_active_text()
        path = self.get_widget("destination").get_text()
        omit_externals = self.get_widget("omit_externals").get_active()
        recursive = self.get_widget("recursive").get_active()
        
        if not url or not path:
            rabbitvcs.ui.dialog.MessageBox(_("The repository URL and destination path are both required fields."))
            return

        if path.startswith("file://"):
            path = path[7:]
        
        path = os.path.normpath(path)
        revision = self.revision_selector.get_revision_object()
    
        self.hide()
        self.action = rabbitvcs.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.append(self.action.set_header, _("Checkout"))
        self.action.append(self.action.set_status, _("Running Checkout Command..."))
        self.action.append(rabbitvcs.lib.helper.save_repository_path, url)
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

    def on_file_chooser_clicked(self, widget, data=None):
        chooser = rabbitvcs.ui.dialog.FolderChooser()
        path = chooser.run()
        if path is not None:
            self.get_widget("destination").set_text(path)

    def on_repositories_changed(self, widget, data=None):
        url = self.repositories.get_active_text()
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
        
        self.check_form()

    def on_destination_changed(self, widget, data=None):
        self.check_form()

    def on_repo_chooser_clicked(self, widget, data=None):
        rabbitvcs.lib.helper.launch_repo_browser(self.repositories.get_active_text())

    def check_form(self):
        self.complete = True
        if self.repositories.get_active_text() == "":
            self.complete = False
        if self.get_widget("destination").get_text() == "":
            self.complete = False
        
        self.get_widget("ok").set_sensitive(self.complete)
        self.revision_selector.determine_widget_sensitivity()

if __name__ == "__main__":
    from rabbitvcs.ui import main, REVISION_OPT
    (options, args) = main(
        [REVISION_OPT],
        usage="Usage: rabbitvcs checkout [url]"
    )
    
    window = Checkout(args[0], revision=options.revision)
    window.register_gtk_quit()
    gtk.main()
