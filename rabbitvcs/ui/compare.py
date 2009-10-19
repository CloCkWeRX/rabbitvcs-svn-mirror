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
import rabbitvcs.ui.widget
import rabbitvcs.lib.helper
from rabbitvcs.ui.log import LogDialog
from rabbitvcs.ui.action import VCSAction
from rabbitvcs import gettext
_ = gettext.gettext

class Compare(InterfaceView):
    def __init__(self, path1=None, revision1=None, path2=None, revision2=None):
        InterfaceView.__init__(self, "compare", "Compare")
        
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()

        repo_paths = rabbitvcs.lib.helper.get_repository_paths()
        self.first_urls = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("first_urls"), 
            repo_paths
        )
        self.first_urls_browse = self.get_widget("first_urls_browse")

        self.second_urls = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("second_urls"), 
            repo_paths
        )
        self.second_urls_browse = self.get_widget("second_urls_browse")
        
        self.first_revision_opt = self.get_widget("first_revision_opt")
        self.first_revision_number = self.get_widget("first_revision_number")
        self.first_revision_browse = self.get_widget("first_revision_browse")
        self.first_revision_opt.set_active(0)
        
        self.second_revision_opt = self.get_widget("second_revision_opt")
        self.second_revision_number = self.get_widget("second_revision_number")
        self.second_revision_browse = self.get_widget("second_revision_browse")
        self.second_revision_opt.set_active(0)

        self.changes_table = rabbitvcs.ui.widget.Table(
            self.get_widget("changes_table"),
            [gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Path"), _("Change"), _("Property Change")]
        )
        self.changes_table.allow_multiple()
        
        self.pbar = rabbitvcs.ui.widget.ProgressBar(self.get_widget("pbar"))
        
        self.check_ui()
        
        self.is_loading = False

    #
    # UI Signal Callback Methods
    #

    def on_destroy(self, widget):
        self.close()

    def on_close_clicked(self, widget):
        self.close()

    def on_refresh_clicked(self, widget):
        self.load()
    
    def on_first_urls_changed(self, widget, data=None):
        self.check_first_urls()

    def on_second_urls_changed(self, widget, data=None):
        self.check_second_urls()
   
    def on_first_revision_opt_changed(self, widget, data=None):
        self.check_first_revision()

    def on_second_revision_opt_changed(self, widget, data=None):
        self.check_second_revision()

    def on_first_urls_browse_clicked(self, widget, data=None):
        rabbitvcs.lib.helper.launch_repo_browser(
            self.first_urls.get_active_text()
        )

    def on_second_urls_browse_clicked(self, widget, data=None):
        rabbitvcs.lib.helper.launch_repo_browser(
            self.second_urls.get_active_text()
        )

    def on_first_revision_browse_clicked(self, widget, data=None):
        LogDialog(
            self.first_urls.get_active_text(), 
            ok_callback=self.on_first_log_closed
        )

    def on_first_log_closed(self, data):
        if data is not None:
            self.first_revision_opt.set_active(1)
            self.first_revision_number.set_text(data)

    def on_second_revision_browse_clicked(self, widget, data=None):
        LogDialog(
            self.second_urls.get_active_text(), 
            ok_callback=self.on_second_log_closed
        )

    def on_second_log_closed(self, data):
        if data is not None:
            self.second_revision_opt.set_active(1)
            self.second_revision_number.set_text(data)

    #
    # Helper methods
    #
    
    def check_ui(self):
        self.check_first_urls()
        self.check_second_urls()
        self.check_first_revision()
        self.check_second_revision()
    
    def check_first_urls(self):
        status = (self.first_urls.get_active_text() != "")
        
        self.first_revision_browse.set_sensitive(status)
        self.first_urls_browse.set_sensitive(status)
        
    def check_second_urls(self):
        status = (self.second_urls.get_active_text() != "")
        
        self.second_revision_browse.set_sensitive(status)
        self.second_urls_browse.set_sensitive(status)
        
    def check_first_revision(self):
        sensitive = (self.first_revision_opt.get_active() == 1)
        self.first_revision_number.set_sensitive(sensitive)
        self.first_revision_browse.set_sensitive(sensitive)

    def check_second_revision(self):
        sensitive = (self.second_revision_opt.get_active() == 1)
        self.second_revision_number.set_sensitive(sensitive)
        self.second_revision_browse.set_sensitive(sensitive)

    def set_loading(self, loading=True):
        self.is_loading = loading

    def load(self):
        first_rev = self.vcs.revision("head")
        if self.first_revision_opt.get_active() == 1:
            first_rev = self.vcs.revision(
                "number", 
                number=int(self.first_revision_number.get_text())
            )

        second_rev = self.vcs.revision("head")
        if self.second_revision_opt.get_active() == 1:
            second_rev = self.vcs.revision(
                "number", 
                number=int(self.second_revision_number.get_text())
            )

        first_url = self.first_urls.get_active_text()
        second_url = self.second_urls.get_active_text()

        self.set_loading(True)
        self.pbar.set_text(_("Generating Differences..."))
        self.pbar.start_pulsate()

        self.action = VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set(),
            notification=False
        )    

        self.action.append(
            self.vcs.diff_summarize,
            first_url,
            first_rev,
            second_url,
            second_rev
        )
        self.action.append(rabbitvcs.lib.helper.save_repository_path, first_url)
        self.action.append(rabbitvcs.lib.helper.save_repository_path, second_url)
        self.action.append(self.pbar.update, 1)
        self.action.append(self.pbar.set_text, _("Completed"))
        self.action.append(self.set_loading, False)
        self.action.append(self.populate_table)
        self.action.start()

    def populate_table(self):
        # returns a list of dicts(path, summarize_kind, node_kind, prop_changed)
        summary = self.action.get_result(0)

        self.changes_table.clear()
        for item in summary:
            prop_changed = (item["prop_changed"] == 1 and _("Yes") or _("No"))
        
            self.changes_table.append([
                item["path"],
                item["summarize_kind"],
                prop_changed
            ])

def parse_path_revision_string(pathrev):
    index = pathrev.rfind("@")
    if index == -1:
        return (pathrev,None)
    else:
        return (pathrev[0:index], pathrev[index+1:])

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, args) = main()
    
    pathrev1 = parse_path_revision_string(args.pop(0))
    pathrev2 = (None, None)
    if len(args) > 0:
        pathrev2 = parse_path_revision_string(args.pop(0))

    window = Compare(pathrev1[0], pathrev1[1], pathrev2[0], pathrev2[1])
    window.register_gtk_quit()
    gtk.main()
