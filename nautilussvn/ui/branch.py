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
import nautilussvn.ui.widget
import nautilussvn.ui.dialog
import nautilussvn.ui.action
import nautilussvn.lib.helper
import nautilussvn.lib.vcs

from nautilussvn import gettext
_ = gettext.gettext

class Branch(InterfaceView):
    """
    Provides a UI interface to copy/branch/tag items in the repository or
    working copy.
    
    Pass a single path to the class when initializing
    
    """
    
    def __init__(self, path):
        InterfaceView.__init__(self, "branch", "Branch")
        
        
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()
        
        self.path = path
        url = self.vcs.get_repo_url(path)
        
        self.get_widget("from_url").set_text(url)
        self.get_widget("to_url").set_text(url)
        
        self.message = nautilussvn.ui.widget.TextView(
            self.get_widget("message")
        )
        self.urls = nautilussvn.ui.widget.ComboBox(
            self.get_widget("to_urls"), 
            nautilussvn.lib.helper.get_repository_paths()
        )
        
        if self.vcs.has_modified(path) or self.vcs.is_modified(path):
            self.tooltips = gtk.Tooltips()
            self.tooltips.set_tip(
                self.get_widget("from_revision_number_opt"),
                _("There have been modifications to your working copy.  If you copy from the HEAD revision you will lose your changes.")
            )
            self.set_revision_number_opt_active()
            self.get_widget("from_revision_number").set_text(
                str(self.vcs.get_revision(path))
            )

    def on_destroy(self, widget):
        self.close()

    def on_cancel_clicked(self, widget):
        self.close()

    def on_ok_clicked(self, widget):
        src = self.get_widget("from_url").get_text()
        dest = self.get_widget("to_url").get_text()
        
        if dest == "":
            nautilussvn.ui.dialog.MessageBox(_("You must supply a destination path."))
            return
        
        revision = None
        if self.get_widget("from_head_opt").get_active():
            revision = self.vcs.revision("head")
        elif self.get_widget("from_revision_number_opt").get_active():
            rev_num = self.get_widget("from_revision_number").get_text()
            
            if rev_num == "":
                nautilussvn.ui.dialog.MessageBox(_("The from revision field is required."))
                return
            
            revision = self.vcs.revision("number", number=rev_num)
        elif self.get_widget("from_working_copy_opt").get_active():
            src = self.path
            revision = self.vcs.revision("working")

        if revision is None:
            nautilussvn.ui.dialog.MessageBox(_("Invalid revision information"))
            return

        self.hide()
        self.action = nautilussvn.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.set_log_message(self.message.get_text())
        
        self.action.append(
            nautilussvn.lib.helper.save_log_message, 
            self.message.get_text()
        )
        
        self.action.append(self.action.set_header, _("Branch/tag"))
        self.action.append(self.action.set_status, _("Running Branch/tag Command..."))
        self.action.append(self.vcs.copy, src, dest, revision)
        self.action.append(self.action.set_status, _("Completed Branch/tag"))
        self.action.append(self.action.finish)
        self.action.start()
                
    def on_from_revision_number_focused(self, widget, data=None):
        self.set_revision_number_opt_active()
        
    def set_revision_number_opt_active(self):
        self.get_widget("from_revision_number_opt").set_active(True)

    def on_previous_messages_clicked(self, widget, data=None):
        dialog = nautilussvn.ui.dialog.PreviousMessages()
        message = dialog.run()
        if message is not None:
            self.message.set_text(message)
            
    def on_show_log_clicked(self, widget, data=None):
        LogDialog(self.path, ok_callback=self.on_log_closed)
    
    def on_log_closed(self, data):
        if data is not None:
            self.get_widget("from_revision_number_opt").set_active(True)
            self.get_widget("from_revision_number").set_text(data)

if __name__ == "__main__":
    from nautilussvn.ui import main
    (options, paths) = main()

    window = Branch(paths[0])
    window.register_gtk_quit()
    gtk.main()
