#a
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

from __future__ import division
import threading
from datetime import datetime

import os.path
import pygtk
import gobject
import gtk

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.action import VCSAction
from rabbitvcs.ui.dialog import MessageBox
from rabbitvcs.lib.contextmenu import GtkContextMenu
from rabbitvcs.lib.contextmenuitems import MenuItem, MenuSeparator
import rabbitvcs.ui.widget
import rabbitvcs.lib.helper
import rabbitvcs.lib.vcs
from rabbitvcs.lib.decorators import gtk_unsafe

from rabbitvcs import gettext
_ = gettext.gettext

DATETIME_FORMAT = rabbitvcs.lib.helper.LOCAL_DATETIME_FORMAT

class Log(InterfaceView):
    """
    Provides an interface to the Log UI
    
    """

    selected_rows = []
    selected_row = []
    paths_selected_rows = []
    
    limit = 100

    def __init__(self, path):
        """
        @type   path: string
        @param  path: A path for which to get log items
        
        """
        
        InterfaceView.__init__(self, "log", "Log")

        self.get_widget("Log").set_title(_("Log - %s") % path)
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        
        self.path = path
        self.cache = LogCache()

        self.rev_start = None
        self.rev_max = 1
        self.previous_starts = []
        self.initialize_revision_labels()
        
        self.get_widget("limit").set_text(str(self.limit))
        
        self.revisions_table = rabbitvcs.ui.widget.Table(
            self.get_widget("revisions_table"),
            [gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Revision"), _("Author"), 
                _("Date"), _("Message")],
            callbacks={
                "mouse-event":   self.on_revisions_table_mouse_event
            }
        )

        self.paths_table = rabbitvcs.ui.widget.Table(
            self.get_widget("paths_table"),
            [gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Action"), _("Path"), 
                _("Copy From Path"), _("Copy From Revision")],
            callbacks={
                "mouse-event":   self.on_paths_table_mouse_event
            }
        )

        self.message = rabbitvcs.ui.widget.TextView(
            self.get_widget("message")
        )

        self.stop_on_copy = False
        self.root_url = self.vcs.get_repo_root_url(self.path)
        self.load_or_refresh()

    #
    # UI Signal Callback Methods
    #

    def on_destroy(self, widget, data=None):
        self.close()

    def on_close_clicked(self, widget, data=None):
        if self.is_loading:
            self.action.set_cancel(True)
            self.action.stop()
            self.set_loading(False)

        self.close()

    def on_previous_clicked(self, widget):
        self.rev_start = self.previous_starts.pop()
        self.load_or_refresh()
                    
    def on_next_clicked(self, widget):
        self.override_limit = True
        self.previous_starts.append(self.rev_start)
        self.rev_start = self.rev_end - 1

        if self.rev_start < 1:
            self.rev_start = 1

        self.load_or_refresh()
    
    def on_stop_on_copy_toggled(self, widget):
        self.stop_on_copy = self.get_widget("stop_on_copy").get_active()
        if not self.is_loading:
            self.refresh()
    
    def on_refresh_clicked(self, widget):
        self.limit = int(self.get_widget("limit").get_text())
        self.cache.empty()
        self.load()

    #
    # Revisions table callbacks
    #

    def on_revisions_table_row_activated(self, treeview, event, col):
        paths = self.revisions_table.get_selected_row_items(1)
        rabbitvcs.lib.helper.launch_diff_tool(*paths)

    def on_revisions_table_mouse_event(self, treeview, data=None):
        if len(self.revisions_table.get_selected_rows()) == 0:
            self.message.set_text("")
            self.paths_table.clear()
            return

        if data is not None and data.button == 3:
            self.show_revisions_table_popup_menu(treeview, data)

        item = self.revision_items[self.revisions_table.get_selected_rows()[0]]

        self.paths_table.clear()
        if len(self.revisions_table.get_selected_rows()) == 1:
            self.message.set_text(item.message)
            
            if item.changed_paths is not None:
                for subitem in item.changed_paths:
                    
                    copyfrom_rev = ""
                    if hasattr(subitem.copyfrom_revision, "number"):
                        copyfrom_rev = subitem.copyfrom_revision.number
                    
                    self.paths_table.append([
                        subitem.action,
                        subitem.path,
                        subitem.copyfrom_path,
                        copyfrom_rev
                    ])    
            
        else:
            self.message.set_text("")

    def show_revisions_table_popup_menu(self, treeview, data):
        revisions = []
        for row in self.revisions_table.get_selected_rows():
            revisions.append({
                "revision": self.vcs.revision("number", number=self.revision_items[row].revision.number),
                "author": self.revision_items[row].author,
                "message": self.revision_items[row].message
            })
            
        LogTopContextMenu(self, data, self.path, revisions).show()

    #
    # Paths table callbacks
    #

    def on_paths_table_row_activated(self, treeview, data=None, col=None):
        rev_item = self.revision_items[self.revisions_table.get_selected_rows()[0]]
        path_item = self.paths_table.get_row(self.paths_table.get_selected_rows()[0])[1]
        url = self.root_url + path_item
        self.view_diff_for_path(url, rev_item.revision.number)

    def on_paths_table_mouse_event(self, treeview, data=None):
        if data is not None and data.button == 3:
            self.show_paths_table_popup_menu(treeview, data)

    def show_paths_table_popup_menu(self, treeview, data):
        structure = [
            ("ViewDiffPrevRev", None),
            ("ShowChangesPrevRev", None),
            ("Separator0", None),
            ("Open", None),
            ("Annotate", None)
        ]
    
        items = {
            "ViewDiffPrevRev": {
                "label": _("View diff against previous revision"),
                "signals": {
                    "activate": {
                        "callback": self.on_paths_context_diff_previous,
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.condition_diff_previous
                }
            },
            "ShowChangesPrevRev": {
                "label": _("Show changes from previous revision"),
                "signals": {
                    "activate": {
                        "callback": self.on_paths_context_show_changes,
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.condition_diff_previous
                }
            },
            "Separator0": {
                "label": rabbitvcs.ui.widget.SEPARATOR,
                "signals": None,
                "condition": {
                    "callback": (lambda: True)
                }
            },
            "Open": {
                "label": _("Open"),
                "icon": gtk.STOCK_OPEN,
                "signals": {
                    "activate": {
                        "callback": self.on_paths_context_open,
                        "args": None
                    }
                },
                "condition": {
                    "callback": (lambda: True)
                }
            },
            "Annotate": {
                "label": _("Annotate"),
                "icon": "rabbitvcs-annotate",
                "signals": {
                    "activate": {
                        "callback": self.on_paths_context_annotate,
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.condition_paths_annotate
                }
            }
        }
        menu = GtkContextMenu(structure, items)
        menu.show(data)
    
    #
    # Helper methods
    #

    def load_or_refresh(self):
        if self.cache.has(self.rev_start):
            self.refresh()
        else:
            self.load()
          
    def get_selected_revision_numbers(self):
        if len(self.revisions_table.get_selected_rows()) == 0:
            return ""

        revisions = []
        for row in self.revisions_table.get_selected_rows():
            revisions.append(int(self.revisions_table.get_row(row)[0]))

        revisions.sort()
        return rabbitvcs.lib.helper.encode_revisions(revisions)

    def get_selected_revision_number(self):
        if len(self.revisions_table.get_selected_rows()):
            return self.revisions_table.get_row(self.revisions_table.get_selected_rows()[0])[0]
        else:
            return ""

    def check_previous_sensitive(self):
        sensitive = (self.rev_start < self.rev_max)
        self.get_widget("previous").set_sensitive(sensitive)

    def check_next_sensitive(self):
        sensitive = True
        if self.rev_end == 1:
            sensitive = False
        if len(self.revision_items) <= self.limit:
            sensitive = False

        self.get_widget("next").set_sensitive(sensitive)
    
    def set_start_revision(self, rev):
        self.get_widget("start").set_text(str(rev))

    def set_end_revision(self, rev):
        self.get_widget("end").set_text(str(rev))

    def initialize_revision_labels(self):
        self.set_start_revision(_("N/A"))
        self.set_end_revision(_("N/A"))

    #
    # Log-loading callback methods
    #
    
    def refresh(self):
        """
        Refresh the items in the main log table that shows Revision/Author/etc.
        
        """
        
        self.revision_items = []
        self.revisions_table.clear()
        self.message.set_text("")
        self.paths_table.clear()
        
        if self.rev_start and self.cache.has(self.rev_start):
            self.revision_items = self.cache.get(self.rev_start)
        else:
            # Make sure the int passed is the order the log call was made
            self.revision_items = self.action.get_result(0)
        
        # Get the starting/ending point from the actual returned revisions
        self.rev_start = self.revision_items[0].revision.number
        self.rev_end = self.revision_items[-1].revision.number
        
        self.cache.set(self.rev_start, self.revision_items)
        
        # The first time the log items return, the rev_start will be as large
        # as it will ever be.  So set this to our maximum revision.
        if self.rev_start > self.rev_max:
            self.rev_max = self.rev_start
        
        self.set_start_revision(self.rev_start)
        self.set_end_revision(self.rev_end)

        for item in self.revision_items:
            msg = rabbitvcs.lib.helper.format_long_text(item.message, 80)
            
            author = _("(no author)")
            if hasattr(item, "author"):
                author = item.author

            self.revisions_table.append([
                item.revision.number,
                author,
                datetime.fromtimestamp(item.date).strftime(DATETIME_FORMAT),
                msg
            ])

            # Stop on copy after adding the item to the table
            # so the user can look at the item that was copied
            if self.stop_on_copy:
                for path in item.changed_paths:
                    if path.copyfrom_path is not None:
                        return
            
        self.check_previous_sensitive()
        self.check_next_sensitive()
        self.set_loading(False)

    def load(self):
        self.set_loading(True)
        
        self.action = VCSAction(
            self.vcs,
            notification=False
        )        

        start = self.vcs.revision("head")
        if self.rev_start:
            start = self.vcs.revision("number", number=self.rev_start)

        self.action.append(
            self.vcs.log, 
            self.path,
            revision_start=start,
            limit=self.limit+1,
            discover_changed_paths=True
        )
        self.action.append(self.refresh)
        self.action.start()

    def set_loading(self, loading):
        self.is_loading = loading

    #
    # Context menu item callbacks
    #



    def on_paths_context_diff_previous(self, widget, data=None):
        rev_item = self.revision_items[self.revisions_table.get_selected_rows()[0]]
        path_item = self.paths_table.get_row(self.paths_table.get_selected_rows()[0])[1]
        url = self.root_url + path_item
        self.view_diff_for_path(url, rev_item.revision.number)
    
    def on_paths_context_show_changes(self, widget, data=None):
        rev_item = self.revision_items[self.revisions_table.get_selected_rows()[0]]
        path_item = self.paths_table.get_row(self.paths_table.get_selected_rows()[0])[1]
        url = self.root_url + path_item

        from rabbitvcs.ui.changes import Changes
        Changes(
            url, 
            rev_item.revision.number-1, 
            url, 
            rev_item.revision.number
        )

    def on_paths_context_open(self, widget, data=None):
        rev_item = self.revision_items[self.revisions_table.get_selected_rows()[0]]
        revision = self.vcs.revision("number", number=rev_item.revision.number)
        self.action = VCSAction(
            self.vcs,
            notification=False
        )

        # This allows us to open multiple files at once
        dests = []
        for row in self.paths_table.get_selected_rows():
            path = self.root_url + self.paths_table.get_row(row)[1]
            dest = "/tmp/rabbitvcs-" + str(rev_item.revision.number) + "-" + os.path.basename(path)
            self.action.append(
                self.vcs.export,
                path,
                dest,
                revision=revision
            )
            dests.append(dest)
        
        for dest in dests:
            self.action.append(rabbitvcs.lib.helper.open_item, dest)
            
        self.action.start()

    def on_paths_context_annotate(self, widget, data=None):
        rev_item = self.revision_items[self.revisions_table.get_selected_rows()[0]]
        path_item = self.paths_table.get_row(self.paths_table.get_selected_rows()[0])[1]
        url = self.root_url + path_item

        from rabbitvcs.ui.annotate import Annotate
        Annotate(url, rev_item.revision.number)
        
    #
    # Context menu item conditions for being visible
    #
    

    def condition_paths_annotate(self):
        return (len(self.revisions_table.get_selected_rows()) == 1)

    #
    # Other helper methods
    #

    def view_diff_for_path(self, url, revision_number):
        from rabbitvcs.ui.diff import SVNDiff

        self.action = VCSAction(
            self.vcs,
            notification=False
        )
        self.action.append(
            SVNDiff,
            url, 
            revision_number-1, 
            url, 
            revision_number
        )
        self.action.start()

    def edit_revprop(self, prop_name, prop_value, callback=None):

        failure = False
        url = self.vcs.get_repo_url(self.path)

        self.action = VCSAction(
            self.vcs,
            notification=False
        )

        for row in self.revisions_table.get_selected_rows():
            item = self.revision_items[row]
            self.action.append(
                self.vcs.revpropset,
                prop_name,
                prop_value,
                url,
                self.vcs.revision("number", item.revision.number)
            )
            
            callback(row, prop_value)
        
        self.action.start()

    def on_log_message_edited(self, index, val):
        self.revision_items[index].message = val
        self.revisions_table.set_row_item(index, 3, val)
        self.message.set_text(val)

    def on_author_edited(self, index, val):
        self.revision_items[index].author = val
        self.revisions_table.set_row_item(index, 1, val)

class LogDialog(Log):
    def __init__(self, path, ok_callback=None, multiple=False):
        """
        Override the normal Log class so that we can hide the window as we need.
        Also, provide a callback for when the OK button is clicked so that we
        can get some desired data.
        """
        Log.__init__(self, path)
        self.ok_callback = ok_callback
        self.multiple = multiple
        
    def on_destroy(self, widget):
        pass
    
    def on_close_clicked(self, widget, data=None):
        self.hide()
        if self.ok_callback is not None:
            if self.multiple == True:
                self.ok_callback(self.get_selected_revision_numbers())
            else:
                self.ok_callback(self.get_selected_revision_number())

class LogCache:
    def __init__(self, cache={}):
        self.cache = cache
    
    def set(self, key, val):
        self.cache[key] = val
    
    def get(self, key):
        return self.cache[key]
    
    def has(self, key):
        return (key in self.cache)
    
    def empty(self):
        self.cache = {}

class MenuViewDiffWC(MenuItem):
    identifier = "RabbitVCS::View_Diff_WC"
    label = _("View diff against working copy")

class MenuViewDiffPrevRev(MenuItem):
    identifier = "RabbitVCS::View_Diff_Prev_Rev"
    label = _("View diff against previous revision")

class MenuViewDiffRevs(MenuItem):
    identifier = "RabbitVCS::View_Diff_Revs"
    label = _("View diff between revisions")

class MenuShowChangesRevs(MenuItem):
    identifier = "RabbitVCS::Show_Changes_Revs"
    label = _("Show changes between revisions")

class MenuUpdateTo(MenuItem):
    identifier = "RabbitVCS::Update_To"
    label = _("Update to revision...")
    icon = "rabbitvcs-update_to"

class MenuCheckout(MenuItem):
    identifier = "RabbitVCS::Checkout"
    label = _("Checkout")
    icon = "rabbitvcs-checkout"

class MenuBranchTag(MenuItem):
    identifier = "RabbitVCS::Branch_Tag"
    label = _("Branch/tag...")    
    icon = "rabbitvcs-branch"

class MenuExport(MenuItem):
    identifier = "RabbitVCS::Export"
    label = _("Export...")
    icon = "rabbitvcs-export"
    
class MenuEditAuthor(MenuItem):
    identifier = "RabbitVCS::Edit_Author"
    label = _("Edit author...")

class MenuEditAuthor(MenuItem):
    identifier = "RabbitVCS::Edit_Author"
    label = _("Edit author...")

class MenuEditLogMessage(MenuItem):
    identifier = "RabbitVCS::Edit_Log_Message"
    label = _("Edit log message...")

class MenuEditRevProps(MenuItem):
    identifier = "RabbitVCS::Edit_Rev_Props"
    label = _("Edit revision properties...")
    icon = gtk.STOCK_EDIT

class LogTopContextMenuConditions:
    def __init__(self, vcs_client, path, revisions):
        self.vcs_client = vcs_client
        self.path = path
        self.revisions = revisions
        
    def view_diff_wc(self, data=None):
        return (len(self.revisions) == 1)

    def view_diff_prev_rev(self, data=None):
        item = self.revisions[0]["revision"]
        return (item.value > 1 and len(self.revisions) == 1)

    def view_diff_revs(self, data=None):
        return (len(self.revisions) == 2)

    def show_changes_revs(self, data=None):
        return (len(self.revisions) == 2)

    def update_to(self, data=None):
        return (len(self.revisions) == 1)

    def checkout(self, data=None):
        return (len(self.revisions) == 1)

    def branch_tag(self, data=None):
        return (len(self.revisions) == 1)

    def export(self, data=None):
        return (len(self.revisions) == 1)

    def edit_author(self, data=None):
        return True

    def edit_log_message(self, data=None):
        return True

    def edit_rev_props(self, data=None):
        return (len(self.revisions) == 1)

    def separator(self, data=None):
        return True

class LogTopContextMenuCallbacks:
    def __init__(self, caller, vcs_client, path, revisions):
        self.caller = caller
        self.vcs_client = vcs_client
        self.path = path
        self.revisions = revisions
        
    def view_diff_wc(self, widget, data=None):
        from rabbitvcs.ui.diff import SVNDiff
        self.action = VCSAction(
            self.vcs_client,
            notification=False
        )
        self.action.append(
            SVNDiff,
            self.path, 
            self.revisions[0]["revision"]
        )
        self.action.start()

    def view_diff_prev_rev(self, widget, data=None):
        from rabbitvcs.ui.diff import SVNDiff

        item = self.revisions[0]["revision"]
        self.action = VCSAction(
            self.vcs_client,
            notification=False
        )
        self.action.append(
            SVNDiff,
            self.path, 
            item.value-1, 
            self.path, 
            item.value
        )
        self.action.start()
        
    def view_diff_revs(self, widget, data=None):
        from rabbitvcs.ui.diff import SVNDiff
        
        item1 = self.revisions[0]["revision"]
        item2 = self.revisions[1]["revision"]
        
        self.action = VCSAction(
            self.vcs_client,
            notification=False
        )
        self.action.append(
            SVNDiff,
            self.vcs_client.get_repo_url(self.path), 
            item2, 
            self.path, 
            item1
        )
        self.action.start()

    def show_changes_revs(self, widget, data=None):
        from rabbitvcs.ui.changes import Changes
        item1 = self.revisions[0]["revision"]
        item2 = self.revisions[1]["revision"]
        path = self.vcs_client.get_repo_url(self.path)

        Changes(
            path, 
            item2, 
            path, 
            item1
        )

    def update_to(self, widget, data=None):
        from rabbitvcs.ui.updateto import UpdateToRevision
        UpdateToRevision(self.path, self.revisions[0]["revision"].value)
        
    def checkout(self, widget, data=None):
        from rabbitvcs.ui.checkout import Checkout
        url = self.vcs_client.get_repo_url(self.path)
        Checkout(url=url, revision=self.revisions[0]["revision"].value).show()

    def branch_tag(self, widget, data=None):
        from rabbitvcs.ui.branch import Branch
        Branch(self.path, revision=self.revisions[0]["revision"].value).show()

    def export(self, widget, data=None):
        from rabbitvcs.ui.export import Export
        Export(self.path, revision=self.revisions[0]["revision"].value).show()

    def edit_author(self, widget, data=None):
        message = ""
        if len(self.revisions) == 1:
            author = self.revisions[0]["author"]

        from rabbitvcs.ui.dialog import TextChange
        dialog = TextChange(_("Edit author"), author)
        (result, new_author) = dialog.run()

        if result == gtk.RESPONSE_OK:
            self.caller.edit_revprop("svn:author", new_author, self.caller.on_author_edited)

    def edit_log_message(self, widget, data=None):
        message = ""
        if len(self.revisions) == 1:
            message = self.revisions[0]["message"]

        from rabbitvcs.ui.dialog import TextChange
        dialog = TextChange(_("Edit log message"), message)
        (result, new_message) = dialog.run()

        if result == gtk.RESPONSE_OK:
            self.caller.edit_revprop("svn:log", new_message, self.caller.on_log_message_edited)

    def edit_rev_props(self, widget, data=None):
        from rabbitvcs.ui.revprops import SVNRevisionProperties
        url = self.vcs_client.get_repo_url(self.path)
        SVNRevisionProperties(url, self.revisions[0]["revision"].value)

class LogTopContextMenu:
    """
    Defines context menu items for a table with files
    
    """
    def __init__(self, caller, event, path, revisions=[]):
        """    
        @param  caller: The calling object
        @type   caller: object
        
        @param  base_dir: The curent working directory
        @type   base_dir: string
        
        @param  paths: The selected paths
        @type   paths: list
        
        """        
        self.caller = caller
        self.event = event
        self.path = path
        self.revisions = revisions
        self.vcs_client = rabbitvcs.lib.vcs.create_vcs_instance()

        self.conditions = LogTopContextMenuConditions(
            self.vcs_client, 
            self.path, 
            self.revisions
        )
        
        self.callbacks = LogTopContextMenuCallbacks(
            self.caller,
            self.vcs_client, 
            self.path,
            self.revisions
        )

        # The first element of each tuple is a key that matches a
        # ContextMenuItems item.  The second element is either None when there
        # is no submenu, or a recursive list of tuples for desired submenus.
        self.structure = [
            (MenuViewDiffWC, None),
            (MenuViewDiffPrevRev, None),
            (MenuViewDiffRevs, None),
            (MenuShowChangesRevs, None),
            (MenuSeparator, None),
            (MenuUpdateTo, None),
            (MenuCheckout, None),
            (MenuBranchTag, None),
            (MenuExport, None),
            (MenuSeparator, None),
            (MenuEditAuthor, None),
            (MenuEditLogMessage, None),
            (MenuEditRevProps, None)
        ]
        
    def show(self):
        if len(self.revisions) == 0:
            return

        context_menu = GtkContextMenu(self.structure, self.conditions, self.callbacks)
        context_menu.show(self.event)


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs log [url_or_path]")
            
    window = Log(paths[0])
    window.register_gtk_quit()
    gtk.main()
