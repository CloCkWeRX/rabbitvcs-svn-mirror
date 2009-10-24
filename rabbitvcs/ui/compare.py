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
import rabbitvcs.ui.widget
import rabbitvcs.lib.helper
from rabbitvcs.ui.log import LogDialog
from rabbitvcs.ui.action import VCSAction
from rabbitvcs.ui.dialog import MessageBox
from rabbitvcs import gettext
_ = gettext.gettext

class Compare(InterfaceView):
    selected_rows = []

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

        if path1 is not None:
            self.first_urls.set_child_text(path1)
        if revision1 is not None:
            self.first_revision_opt.set_active(1)
            self.first_revision_number.set_text(str(revision1))

        if path2 is not None:
            self.second_urls.set_child_text(path2)
        elif path1 is not None:
            self.second_urls.set_child_text(path1)
            
        if revision2 is not None:
            self.second_revision_opt.set_active(1)
            self.second_revision_number.set_text(str(revision2))

        self.changes_table = rabbitvcs.ui.widget.Table(
            self.get_widget("changes_table"),
            [gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Path"), _("Change"), _("Property Change")]
        )

        self.check_ui()

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
        self.check_refresh_button()

    def on_second_urls_changed(self, widget, data=None):
        self.check_second_urls()
        self.check_refresh_button()
   
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

    def on_changes_table_cursor_changed(self, treeview, data=None):
        self.on_changes_table_event(treeview, data)

    def on_changes_table_button_released(self, treeview, data=None):
        self.on_changes_table_event(treeview, data)

    def on_changes_table_event(self, treeview, data=None):
        selection = treeview.get_selection()
        (liststore, indexes) = selection.get_selected_rows()

        self.selected_rows = []
        for tup in indexes:
            self.selected_rows.append(tup[0])

        if data is not None and data.button == 3:
            self.show_changes_table_popup_menu(treeview, data)

    #
    # Helper methods
    #
    
    def get_first_revision(self):
        rev = self.vcs.revision("head")
        if self.first_revision_opt.get_active() == 1:
            rev = self.vcs.revision(
                "number", 
                number=int(self.first_revision_number.get_text())
            )
        return rev
    
    def get_second_revision(self):
        rev = self.vcs.revision("head")
        if self.second_revision_opt.get_active() == 1:
            rev = self.vcs.revision(
                "number", 
                number=int(self.second_revision_number.get_text())
            )
        return rev

    def show_changes_table_popup_menu(self, treeview, data):
        context_menu = rabbitvcs.ui.widget.ContextMenu([
            {
                "label": _("Open from %s") % str(self.get_first_revision()),
                "signals": {
                    "activate": {
                        "callback": self.on_context_open_first,
                        "args": None
                    }
                },
                "condition": self.condition_show_open_first_revision
            },
            {
                "label": _("Open from %s") % str(self.get_second_revision()),
                "signals": {
                    "activate": {
                        "callback": self.on_context_open_second,
                        "args": None
                    }
                },
                "condition": self.condition_show_open_second_revision
            },
            {
                "label": _("View unified diff"),
                "signals": {
                    "activate": {
                        "callback": self.on_context_view_diff,
                        "args": None
                    }
                },
                "condition": self.condition_view_diff
            },
            {
                "label": _("Show changes"),
                "signals": {
                    "activate": {
                        "callback": self.on_context_show_changes,
                        "args": None
                    }
                },
                "condition": self.condition_show_changes
            }
        ])
        if context_menu.get_num_items() > 0:
            context_menu.show(data)
    
    def check_ui(self):
        self.check_first_urls()
        self.check_second_urls()
        self.check_first_revision()
        self.check_second_revision()
        self.check_refresh_button()
    
    def can_first_browse_urls(self):
        return (self.first_urls.get_active_text() != "")
    
    def can_first_browse_revisions(self):
        return (
            self.can_first_browse_urls()
            and (self.first_urls.get_active_text() != "")
        )
    
    def can_second_browse_urls(self):
        return (self.second_urls.get_active_text() != "")
    
    def can_second_browse_revisions(self):
        return (
            self.can_second_browse_urls()
            and (self.second_urls.get_active_text() != "")
        )
    
    def check_refresh_button(self):
        can_click_refresh = (
            self.can_first_browse_urls()
            and self.can_second_browse_urls()
        )
        
        self.get_widget("refresh").set_sensitive(can_click_refresh)
    
    def check_first_urls(self):
        can_browse_urls = self.can_first_browse_urls()
        can_browse_revisions = self.can_first_browse_revisions()
        
        self.first_revision_browse.set_sensitive(can_browse_urls)
        self.first_urls_browse.set_sensitive(can_browse_revisions)
        
    def check_second_urls(self):
        can_browse_urls = self.can_second_browse_urls()
        can_browse_revisions = self.can_second_browse_revisions()
        
        self.second_revision_browse.set_sensitive(can_browse_urls)
        self.second_urls_browse.set_sensitive(can_browse_revisions)
        
    def check_first_revision(self):
        can_type_number = (self.first_revision_opt.get_active() == 1)
        can_browse_revisions = self.can_first_browse_revisions()
        
        self.first_revision_number.set_sensitive(can_type_number)
        self.first_revision_browse.set_sensitive(can_browse_revisions)

    def check_second_revision(self):
        can_type_number = (self.second_revision_opt.get_active() == 1)
        can_browse_revisions = self.can_second_browse_revisions()
        
        self.second_revision_number.set_sensitive(can_type_number)
        self.second_revision_browse.set_sensitive(can_browse_revisions)

    def load(self):
        first_url = self.first_urls.get_active_text()
        first_rev = self.get_first_revision()
        second_rev = self.get_second_revision()        
        second_url = self.second_urls.get_active_text()

        self.action = VCSAction(
            self.vcs,
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

    def open_item_from_revision(self, url, revision, dest):
        self.action = VCSAction(
            self.vcs,
            notification=False
        )
        self.action.append(
            self.vcs.export,
            url,
            dest,
            revision=revision
        )
        self.action.append(rabbitvcs.lib.helper.open_item, dest)
        self.action.start()
        
    #
    # Changes table context menu callbacks
    #

    def on_context_open_first(self, widget, data=None):
        url = self.vcs.get_repo_url(self.first_urls.get_active_text())
        path = url + "/" + self.changes_table.get_row(self.selected_rows[0])[0]
        rev = self.get_first_revision()
        dest = "/tmp/rabbitvcs-" + str(rev) + "-" + os.path.basename(path)
        self.open_item_from_revision(path, rev, dest)

    def on_context_open_second(self, widget, data=None):
        url = self.vcs.get_repo_url(self.second_urls.get_active_text())
        path = url + "/" + self.changes_table.get_row(self.selected_rows[0])[0]
        rev = self.get_second_revision()
        dest = "/tmp/rabbitvcs-" + str(rev) + "-" + os.path.basename(path)
        self.open_item_from_revision(path, rev, dest)

    def on_context_view_diff(self, widget, data=None):
        from rabbitvcs.ui.diff import SVNDiff
        url = self.vcs.get_repo_url(self.first_urls.get_active_text())
        url += "/" + self.changes_table.get_row(self.selected_rows[0])[0]
        
        rev1 = self.get_first_revision()
        rev2 = self.get_second_revision()

        self.action = VCSAction(
            self.vcs,
            notification=False
        )
        self.action.append(
            SVNDiff,
            url, 
            (rev1.value and rev1.value or "HEAD"), 
            url, 
            (rev2.value and rev2.value or "HEAD")
        )
        self.action.start()

    def on_context_show_changes(self, widget, data=None):
        url = self.vcs.get_repo_url(self.second_urls.get_active_text())
        path = url + "/" + self.changes_table.get_row(self.selected_rows[0])[0]

        rev1 = self.get_first_revision()
        dest1 = "/tmp/rabbitvcs-" + str(rev1) + "-" + os.path.basename(path)
        rev2 = self.get_second_revision()
        dest2 = "/tmp/rabbitvcs-" + str(rev2) + "-" + os.path.basename(path)

        self.action = VCSAction(
            self.vcs,
            notification=False
        )
        self.action.append(
            self.vcs.export,
            path,
            dest1,
            revision=rev1
        )
        self.action.append(
            self.vcs.export,
            path,
            dest2,
            revision=rev2
        )
        self.action.append(
            rabbitvcs.lib.helper.launch_diff_tool, 
            dest1,
            dest2
        )
        self.action.start()
        
    #
    # Changes table condition callbacks
    #

    def condition_show_open_first_revision(self):
        return (
            len(self.selected_rows) == 1
        )
    
    def condition_show_open_second_revision(self):
        return (
            len(self.selected_rows) == 1 
            and str(self.get_first_revision()) != str(self.get_second_revision())
        )

    def condition_view_diff(self):
        return (
            len(self.selected_rows) == 1
        )

    def condition_show_changes(self):
        return (
            len(self.selected_rows) == 1
        )

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, args) = main()
    
    pathrev1 = rabbitvcs.lib.helper.parse_path_revision_string(args.pop(0))
    pathrev2 = (None, None)
    if len(args) > 0:
        pathrev2 = rabbitvcs.lib.helper.parse_path_revision_string(args.pop(0))

    window = Compare(pathrev1[0], pathrev1[1], pathrev2[0], pathrev2[1])
    window.register_gtk_quit()
    gtk.main()
