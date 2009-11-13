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

class Branch(InterfaceView):
    """
    Provides a UI interface to copy/branch/tag items in the repository or
    working copy.
    
    Pass a single path to the class when initializing
    
    """
    
    def __init__(self, path, revision=None):
        InterfaceView.__init__(self, "branch", "Branch")
        
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        
        self.path = path
        self.revision = revision

        repo_paths = rabbitvcs.lib.helper.get_repository_paths()
        self.from_urls = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("from_urls"), 
            repo_paths
        )
        self.to_urls = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("to_urls"), 
            rabbitvcs.lib.helper.get_repository_paths()
        )
        
        if self.vcs.is_path_repository_url(path):
            self.from_urls.set_child_text(path)
        else:
            self.to_urls.set_child_text(path)
                
        self.message = rabbitvcs.ui.widget.TextView(
            self.get_widget("message")
        )

        self.revision_selector = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("revision_container"),
            self.vcs,
            revision=revision,
            url_combobox=self.from_urls,
            expand=True
        )
        
        if (self.revision is None and (self.vcs.has_modified(path) 
                or self.vcs.is_modified(path))):
            self.revision_selector.set_kind_working()

    def on_destroy(self, widget):
        self.close()

    def on_cancel_clicked(self, widget):
        self.close()

    def on_ok_clicked(self, widget):
        src = self.get_widget("from_urls").get_active_text()
        dest = self.get_widget("to_urls").get_active_text()
        
        if dest == "":
            rabbitvcs.ui.dialog.MessageBox(_("You must supply a destination path."))
            return
        
        revision = self.revision_selector.get_revision_object()
        self.hide()
        self.action = rabbitvcs.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.set_log_message(self.message.get_text())
        
        self.action.append(
            rabbitvcs.lib.helper.save_log_message, 
            self.message.get_text()
        )
        
        self.action.append(self.action.set_header, _("Branch/tag"))
        self.action.append(self.action.set_status, _("Running Branch/tag Command..."))
        self.action.append(self.vcs.copy, src, dest, revision)
        self.action.append(self.action.set_status, _("Completed Branch/tag"))
        self.action.append(self.action.finish)
        self.action.start()

    def on_previous_messages_clicked(self, widget, data=None):
        dialog = rabbitvcs.ui.dialog.PreviousMessages()
        message = dialog.run()
        if message is not None:
            self.message.set_text(message)

if __name__ == "__main__":
    from rabbitvcs.ui import main, REVISION_OPT
    (options, args) = main(
        [REVISION_OPT],
        usage="Usage: rabbitvcs branch [url_or_path]"
    )

    window = Branch(args[0], options.revision)
    window.register_gtk_quit()
    gtk.main()
