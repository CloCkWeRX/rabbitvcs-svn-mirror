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

import os

import pygtk
import gobject
import gtk

from nautilussvn.ui import InterfaceView
from nautilussvn.ui.log import LogDialog
from nautilussvn.ui.action import VCSAction
import nautilussvn.ui.widget
from nautilussvn.ui.dialog import MessageBox
import nautilussvn.lib.helper
import nautilussvn.lib.vcs

from nautilussvn import gettext
_ = gettext.gettext

class Annotate(InterfaceView):
    """
    Provides a UI interface to annotate items in the repository or
    working copy.
    
    Pass a single path to the class when initializing
    
    """
    
    def __init__(self, path):
        if os.path.isdir(path):
            MessageBox(_("Cannot annotate a directory"))
            raise SystemExit()
            return
            
        InterfaceView.__init__(self, "annotate", "Annotate")

        nautilussvn.lib.helper.setcwd(path)

        self.get_widget("Annotate").set_title(_("Annotate - %s") % path)
        
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()
        
        self.path = path
        self.pbar = nautilussvn.ui.widget.ProgressBar(self.get_widget("pbar"))
        self.get_widget("from").set_text(str(1))
        self.get_widget("to").set_text("HEAD")        

        self.table = nautilussvn.ui.widget.Table(
            self.get_widget("table"),
            [gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Line"), _("Revision"), _("Author"), 
                _("Date"), _("Text")],
        )
        self.table.allow_multiple()
        
        self.is_loading = False
        self.load()
        
    def on_destroy(self, widget):
        self.close()
        
    def on_close_clicked(self, widget):
        self.close()

    def on_refresh_clicked(self, widget):
        self.load()

    def on_from_show_log_clicked(self, widget, data=None):
        LogDialog(self.path, ok_callback=self.on_from_log_closed)
    
    def on_from_log_closed(self, data):
        if data is not None:
            self.get_widget("from").set_text(data)

    def on_to_show_log_clicked(self, widget, data=None):
        LogDialog(self.path, ok_callback=self.on_to_log_closed)
    
    def on_to_log_closed(self, data):
        if data is not None:
            self.get_widget("to").set_text(data)


    #
    # Helper methods
    #
    
    def load(self):
        from_rev_num = self.get_widget("from").get_text().lower()
        to_rev_num = self.get_widget("to").get_text().lower()
        
        if not from_rev_num.isdigit():
            MessageBox(_("The from revision field must be an integer"))
            return
             
        from_rev = self.vcs.revision("number", number=int(from_rev_num))
        
        to_rev = self.vcs.revision("head")
        if to_rev_num.isdigit():
            to_rev = self.vcs.revision("number", number=int(to_rev_num))

        self.set_loading(True)
        self.pbar.set_text(_("Generating Annotation..."))
        self.pbar.start_pulsate()
        
        self.action = VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set(),
            notification=False
        )    

        self.action.append(
            self.vcs.annotate,
            self.path,
            from_rev,
            to_rev
        )
        self.action.append(self.pbar.update, 1)
        self.action.append(self.pbar.set_text, _("Completed"))
        self.action.append(self.set_loading, False)
        self.action.append(self.populate_table)
        self.action.start()
    
    def set_loading(self, loading=True):
        self.is_loading = loading

    def populate_table(self):
        blamedict = self.action.get_result(0)

        self.table.clear()
        for item in blamedict:
        
            date = item["date"].replace("T", " ")[0:-8]
        
            self.table.append([
                item["number"],
                item["revision"].number,
                item["author"],
                date,
                item["line"]
            ])

if __name__ == "__main__":
    from os import getcwd
    from sys import argv
    
    args = argv[1:]
    path = getcwd()
    if args:
        if args[0] != ".":
            path = args[0]
            
    window = Annotate(path)
    window.register_gtk_quit()
    gtk.main()
