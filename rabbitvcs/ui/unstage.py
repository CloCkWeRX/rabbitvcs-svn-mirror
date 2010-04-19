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

import thread

import pygtk
import gobject
import gtk

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.add import Add
import rabbitvcs.ui.action
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
import rabbitvcs.util.helper
from rabbitvcs.util.log import Log
import rabbitvcs.vcs.git

log = Log("rabbitvcs.ui.stage")

from rabbitvcs import gettext
_ = gettext.gettext

class GitUnstage(Add):
    def __init__(self, paths, base_dir):
        InterfaceView.__init__(self, "add", "Add")

        self.window = self.get_widget("Add")
        self.window.set_title(_("Stage"))

        self.paths = paths
        self.base_dir = base_dir
        self.last_row_clicked = None
        self.git = rabbitvcs.vcs.git.Git(paths[0])
        self.items = None
        self.files_table = rabbitvcs.ui.widget.Table(
            self.get_widget("files_table"), 
            [gobject.TYPE_BOOLEAN, rabbitvcs.ui.widget.TYPE_PATH,
                gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [rabbitvcs.ui.widget.TOGGLE_BUTTON, _("Path"), _("Extension"), 
                _("Status")],
            callbacks={
                "row-activated":  self.on_files_table_row_activated,
                "mouse-event":   self.on_files_table_mouse_event,
                "key-event":     self.on_files_table_key_event
            }
        )

        self.initialize_items()

    def load(self):
        gtk.gdk.threads_enter()
        self.get_widget("status").set_text(_("Loading..."))
        items = self.git.get_items(self.paths)
        self.items = []
        
        for item in items:
            if not item.is_staged:
                continue

            self.items.append(item)
                
        self.populate_files_table()
        self.get_widget("status").set_text(_("Found %d item(s)") % len(self.items))

        gtk.gdk.threads_leave()

    def populate_files_table(self):
        self.files_table.clear()
        for item in self.items:
            self.files_table.append([
                True, 
                item.path, 
                rabbitvcs.util.helper.get_file_extension(item.path),
                item.content
            ])
                    
    def on_ok_clicked(self, widget):
        items = self.files_table.get_activated_rows(1)
        if not items:
            self.close()
            return
        self.hide()

        self.action = rabbitvcs.ui.action.GitAction(
            self.git,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        
        self.action.append(self.action.set_header, _("Unstage"))
        self.action.append(self.action.set_status, _("Running Unstage Command..."))
        for item in items:
            self.action.append(self.git.unstage, [item])
        self.action.append(self.action.set_status, _("Completed Unstage"))
        self.action.append(self.action.finish)
        self.action.start()

class GitStageQuiet:
    def __init__(self, paths):
        self.git = rabbitvcs.vcs.VCS(paths[0])
        self.action = rabbitvcs.ui.action.GitAction(
            self.git,
            run_in_thread=False
        )
        
        self.action.append(self.git.unstage, paths)
        self.action.run()

if __name__ == "__main__":
    from rabbitvcs.ui import main, BASEDIR_OPT
    (options, paths) = main(
        [BASEDIR_OPT],
        usage="Usage: rabbitvcs unstage [path1] [path2] ..."
    )

    window = GitUnstage(paths, options.base_dir)
    window.register_gtk_quit()
    gtk.main()
