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
from nautilussvn.ui.action import VCSAction
import nautilussvn.lib.vcs
import nautilussvn.ui.widget
import nautilussvn.lib.helper

from nautilussvn import gettext
_ = gettext.gettext

class Merge(InterfaceView):
    def __init__(self, path):
        InterfaceView.__init__(self, "merge", "Merge")
        
        
        self.assistant = self.get_widget("Merge")
        
        self.path = path
        
        self.page = self.assistant.get_nth_page(0)
        
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()
        
        if not self.vcs.has_merge2():
            self.get_widget("mergetype_range_opt").set_sensitive(False)
            self.get_widget("mergetype_tree_opt").set_active(True)
            self.get_widget("mergeoptions_only_record").set_active(False)
            
        self.assistant.set_page_complete(self.page, True)
        self.assistant.set_forward_page_func(self.on_forward_clicked)
        
        self.repo_paths = nautilussvn.lib.helper.get_repository_paths()
        
        # Keeps track of which stages should be marked as complete
        self.type = None
    #
    # Assistant UI Signal Callbacks
    #

    def on_destroy(self, widget):
        self.close()
    
    def on_cancel_clicked(self, widget):
        self.close()
    
    def on_close_clicked(self, widget):
        self.close()

    def on_apply_clicked(self, widget):
        self.merge()
    
    def on_test_clicked(self, widget):
        self.merge(test=True)            

    def merge(self, test=False):
        if self.type is None:
            return
        
        if test:
            startcmd = _("Running Merge Test")
            endcmd = _("Completed Merge Test")
        else:
            startcmd = _("Running Merge Command")
            endcmd = _("Completed Merge")
            self.hide()

        recursive = self.get_widget("mergeoptions_recursive").get_active()
        ignore_ancestry = self.get_widget("mergeoptions_ignore_ancestry").get_active()
        
        record_only = False
        if self.vcs.has_merge2():
            record_only = self.get_widget("mergeoptions_only_record").get_active()

        action = VCSAction(self.vcs, register_gtk_quit=self.gtk_quit_is_set())
        action.append(action.set_header, _("Merge"))
        action.append(action.set_status, startcmd)
        
        args = ()
        kwargs = {}
        
        if self.type == "range":
            url = self.get_widget("mergerange_from_url").get_text()
            head_revision = self.vcs.get_revision(self.path)
            revisions = self.get_widget("mergerange_revisions").get_text()
            revisions = revisions.lower().replace("head", str(head_revision))

            ranges = []
            for r in revisions.split(","):
                if r.find("-") != -1:
                    (low, high) = r.split("-")
                else:
                    low = r
                    high = r

                # Before pysvn v1.6.3, there was a bug that required the ranges 
                # tuple to have three elements, even though only two were used
                # Fixed in Pysvn Revision 1114
                if (self.vcs.interface == "pysvn" and self.vcs.is_version_less_than((1,6,3,0))):
                    ranges.append((
                        self.vcs.revision("number", number=int(low)),
                        self.vcs.revision("number", number=int(high)),
                        None
                    ))
                else:
                    ranges.append((
                        self.vcs.revision("number", number=int(low)),
                        self.vcs.revision("number", number=int(high)),
                    ))
            
            # Build up args and kwargs because some args are not supported
            # with older versions of pysvn/svn
            args = (
                self.vcs.merge_ranges,
                url,
                ranges,
                self.vcs.revision("head"),
                self.path
            )
            kwargs = {
                "notice_ancestry": (not ignore_ancestry),
                "dry_run":          test
            }
            if record_only:
                kwargs["record_only"] = record_only

        elif self.type == "tree":
            from_url = self.get_widget("mergetree_from_url").get_text()
            from_revision = self.vcs.revision("head")
            if self.get_widget("mergetree_from_revision_number_opt").get_active():
                from_revision = self.vcs.revision(
                    "number",
                    number=int(self.get_widget("mergetree_from_revision_number").get_text())
                )
            to_url = self.get_widget("mergetree_to_url").get_text()
            to_revision = self.vcs.revision("head")
            if self.get_widget("mergetree_to_revision_number_opt").get_active():
                to_revision = self.vcs.revision(
                    "number",
                    number=int(self.get_widget("mergetree_to_revision_number").get_text())
                )

            # Build up args and kwargs because some args are not supported
            # with older versions of pysvn/svn
            args = (
                self.vcs.merge_trees,
                from_url,
                from_revision,
                to_url,
                to_revision,
                self.path
            )
            kwargs = {
                "recurse": recursive
            }
        
        if len(args) > 0:
            action.append(*args, **kwargs) 
                       
        action.append(action.set_status, endcmd)
        action.append(action.finish)
        action.start()

    def on_prepare(self, widget, page):
        self.page = page
        
        current = self.assistant.get_current_page()
        if current == 1:
            self.on_mergerange_prepare()
        elif current == 2:
            self.on_mergebranch_prepare()
        elif current == 3:
            self.on_mergetree_prepare()
        elif current == 4:
            self.on_mergeoptions_prepare()

    def on_forward_clicked(self, widget):
        current = self.assistant.get_current_page()
        if current == 0:
            if self.get_widget("mergetype_range_opt").get_active():
                next = 1
                self.type = "range"
            elif self.get_widget("mergetype_tree_opt").get_active():
                next = 3
                self.type = "tree"
        else:
            next = 4
        
        return next

    #
    # Step 2a: Merge a Range of Revisions
    #
    
    def on_mergerange_prepare(self):
        if not hasattr(self, "mergerange_repos"):
            self.mergerange_repos = nautilussvn.ui.widget.ComboBox(
                self.get_widget("mergerange_from_urls"), 
                self.repo_paths
            )
            self.get_widget("mergerange_working_copy").set_text(self.path)
        
        self.mergerange_check_ready()
        
    def on_mergerange_show_log1_clicked(self, widget):
        LogDialog(
            self.get_widget("mergerange_from_url").get_text(),
            ok_callback=self.on_mergerange_log1_closed, 
            multiple=True
        )
    
    def on_mergerange_log1_closed(self, data):
        self.get_widget("mergerange_revisions").set_text(data)

    def on_mergerange_from_url_changed(self, widget):
        self.mergerange_check_ready()

    def on_mergerange_revisions_changed(self, widget):
        self.mergerange_check_ready()

    def mergerange_check_ready(self):
        ready = True
        if self.get_widget("mergerange_from_url").get_text() == "":
            ready = False

        self.assistant.set_page_complete(self.page, ready)

        allow_log = False
        if self.get_widget("mergerange_from_url").get_text():
            allow_log = True        
        self.get_widget("mergerange_show_log1").set_sensitive(allow_log)

    #
    # Step 2b: Reintegrate a Branch
    #

    def on_mergebranch_prepare(self):
        if not hasattr(self, "mergebranch_repos"):
            self.mergebranch_repos = nautilussvn.ui.widget.ComboBox(
                self.get_widget("mergebranch_from_urls"), 
                self.repo_paths
            )
            self.get_widget("mergebranch_working_copy").set_text(self.path)

    def on_mergebranch_show_log1_clicked(self, widget):
        LogDialog(self.path)

    def on_mergebranch_show_log2_clicked(self, widget):
        LogDialog(self.path)
        
    def on_mergebranch_from_url_changed(self, widget):
        self.mergebranch_check_ready()
    
    def mergebranch_check_ready(self):
        ready = True
        if self.get_widget("mergebranch_from_url").get_text() == "":
            ready = False

        self.assistant.set_page_complete(self.page, ready)

    #
    # Step 2c: Merge two different trees
    #
    
    def on_mergetree_prepare(self):
        if not hasattr(self, "mergetree_from_repos"):
            self.mergetree_from_repos = nautilussvn.ui.widget.ComboBox(
                self.get_widget("mergetree_from_urls"), 
                self.repo_paths
            )
            self.mergetree_to_repos = nautilussvn.ui.widget.ComboBox(
                self.get_widget("mergetree_to_urls"), 
                self.repo_paths
            )
            self.get_widget("mergetree_working_copy").set_text(self.path)

    def on_mergetree_from_show_log_clicked(self, widget):
        LogDialog(
            self.path,
            ok_callback=self.on_mergetree_from_show_log_closed, 
            multiple=False
        )

    def on_mergetree_from_show_log_closed(self, data):
        self.get_widget("mergetree_from_revision_number").set_text(data)
        self.get_widget("mergetree_from_revision_number_opt").set_active(True)

    def on_mergetree_to_show_log_clicked(self, widget):
        LogDialog(
            self.path,
            ok_callback=self.on_mergetree_to_show_log_closed, 
            multiple=False
        )

    def on_mergetree_to_show_log_closed(self, data):
        self.get_widget("mergetree_to_revision_number").set_text(data)
        self.get_widget("mergetree_to_revision_number_opt").set_active(True)

    def on_mergetree_working_copy_show_log_clicked(self, widget):
        LogDialog(self.path)
        
    def on_mergetree_from_revision_number_focused(self, widget, data):
        self.get_widget("mergetree_from_revision_number_opt").set_active(True)

    def on_mergetree_to_revision_number_focused(self, widget, data):
        self.get_widget("mergetree_to_revision_number_opt").set_active(True)

    def on_mergetree_from_url_changed(self, widget):
        self.mergetree_check_ready()

    def on_mergetree_to_url_changed(self, widget):
        self.mergetree_check_ready()

    def mergetree_check_ready(self):
        ready = True
        if self.get_widget("mergetree_from_url").get_text() == "":
            ready = False
        if self.get_widget("mergetree_to_url").get_text() == "":
            ready = False

        self.assistant.set_page_complete(self.page, ready)
 
    #
    # Step 3: Merge Options
    #
    
    def on_mergeoptions_prepare(self):
        self.assistant.set_page_complete(self.page, True)

if __name__ == "__main__":
    from nautilussvn.ui import main
    (options, paths) = main()
            
    window = Merge(paths[0])
    window.register_gtk_quit()
    gtk.main()
