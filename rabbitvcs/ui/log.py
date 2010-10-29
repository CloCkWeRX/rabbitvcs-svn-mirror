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

from __future__ import division
import threading
from datetime import datetime

import os.path
import pygtk
import gobject
import gtk

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.action import SVNAction, GitAction
from rabbitvcs.ui.dialog import MessageBox
from rabbitvcs.util.contextmenu import GtkContextMenu
from rabbitvcs.util.contextmenuitems import *
import rabbitvcs.ui.widget
import rabbitvcs.util.helper
import rabbitvcs.vcs
from rabbitvcs.util.decorators import gtk_unsafe

from rabbitvcs import gettext
_ = gettext.gettext

DATETIME_FORMAT = rabbitvcs.util.helper.LOCAL_DATETIME_FORMAT

REVISION_LABEL = _("Revision")

def revision_grapher(history):
    """
    Expects a list of revision items like so:
    [
        {"commit": "...", "parents": ["...", "..."]}
    ]
    
    Output can be put directly into the CellRendererGraph
    """
    items = []
    revisions = []
    last_lines = []
    color = "#d3b9d3"
    for item in history:
        commit = item["commit"]
        parents = item["parents"]

        if commit not in revisions:
            revisions.append(commit)

        index = revisions.index(commit)
        next_revisions = revisions[:]
        
        parents_to_add = []
        for parent in parents:
            if parent not in next_revisions:
                parents_to_add.append(parent)
        
        next_revisions[index:index+1] = parents_to_add

        lines = []
        for i, revision in enumerate(revisions):
            if revision in next_revisions:
                lines.append((i, next_revisions.index(revision), color))
            elif revision == commit:
                for parent in parents:
                    lines.append((i, next_revisions.index(parent), color))

        node = (index, "#a9f9d2")

        items.append((item, node, last_lines, lines))
        revisions = next_revisions
        last_lines = lines

    return items

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
        self.vcs = rabbitvcs.vcs.VCS()
        
        self.path = path
        self.cache = LogCache()

        self.rev_first = None
        self.rev_start = None
        self.rev_end = None
        self.rev_max = 1
        self.previous_starts = []
        self.initialize_revision_labels()
        self.revision_number_column = 0
        
        self.get_widget("limit").set_text(str(self.limit))

        self.message = rabbitvcs.ui.widget.TextView(
            self.get_widget("message")
        )

        self.stop_on_copy = False

    #
    # UI Signal Callback Methods
    #

    def on_destroy(self, widget, data=None):
        self.destroy()

    def on_close_clicked(self, widget, data=None):
        if self.is_loading:
            self.action.set_cancel(True)
            self.action.stop()
            self.set_loading(False)

        self.close()
    
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
        rabbitvcs.util.helper.launch_diff_tool(*paths)

    def on_revisions_table_mouse_event(self, treeview, data=None):
        if len(self.revisions_table.get_selected_rows()) == 0:
            self.message.set_text("")
            self.paths_table.clear()
            return

        if data is not None and data.button == 3:
            self.show_revisions_table_popup_menu(treeview, data)

        self.paths_table.clear()
        self.message.set_text("")

        self.update_revision_message()             


    #
    # Paths table callbacks
    #

    def on_paths_table_row_activated(self, treeview, data=None, col=None):
        rev_item = self.revision_items[self.revisions_table.get_selected_rows()[0]]
        path_item = self.paths_table.get_row(self.paths_table.get_selected_rows()[0])[1]
        url = self.root_url + path_item
        self.view_diff_for_path(url, rev_item.revision.number, sidebyside=True)

    def on_paths_table_mouse_event(self, treeview, data=None):
        if data is not None and data.button == 3:
            self.show_paths_table_popup_menu(treeview, data)
    
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
            revisions.append(int(self.revisions_table.get_row(row)[self.revision_number_column]))

        revisions.sort()
        return rabbitvcs.util.helper.encode_revisions(revisions)

    def get_selected_revision_number(self):
        if len(self.revisions_table.get_selected_rows()):
            return self.revisions_table.get_row(self.revisions_table.get_selected_rows()[0])[self.revision_number_column]
        else:
            return ""
    
    def set_start_revision(self, rev):
        self.get_widget("start").set_text(str(rev))

    def set_end_revision(self, rev):
        self.get_widget("end").set_text(str(rev))

    def initialize_revision_labels(self):
        self.set_start_revision(_("N/A"))
        self.set_end_revision(_("N/A"))

    def set_loading(self, loading):
        self.is_loading = loading


class SVNLog(Log):
    def __init__(self, path):
        Log.__init__(self, path)
                
        self.svn = self.vcs.svn()

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
                "mouse-event":      self.on_paths_table_mouse_event,
                "row-activated":    self.on_paths_table_row_activated
            },
            flags={
                "sortable": True, 
                "sort_on": 1
            }
        )

        self.initialize_root_url()
        self.load_or_refresh()

    def initialize_root_url(self):
        action = SVNAction(
            self.svn,
            notification=False,
            run_in_thread=False
        )
        
        self.root_url = action.run_single(
            self.svn.get_repo_root_url,
            self.path
        )

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
        
        if not self.rev_first:
            self.rev_first = self.rev_start
        
        self.cache.set(self.rev_start, self.revision_items)
        
        # The first time the log items return, the rev_start will be as large
        # as it will ever be.  So set this to our maximum revision.
        if self.rev_start > self.rev_max:
            self.rev_max = self.rev_start
        
        self.set_start_revision(self.rev_start)
        self.set_end_revision(self.rev_end)

        for item in self.revision_items:
            msg = rabbitvcs.util.helper.format_long_text(item["message"], 80)
            
            author = _("(no author)")
            if hasattr(item, "author"):
                author = item["author"]

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
        
        self.action = SVNAction(
            self.svn,
            notification=False
        )        

        start = self.svn.revision("head")
        if self.rev_start:
            start = self.svn.revision("number", number=self.rev_start)

        self.action.append(
            self.svn.log, 
            self.path,
            revision_start=start,
            limit=self.limit+1,
            discover_changed_paths=True
        )
        self.action.append(self.refresh)
        self.action.start()

    def edit_revprop(self, prop_name, prop_value, callback=None):

        failure = False
        url = self.svn.get_repo_url(self.path)

        self.action = SVNAction(
            self.svn,
            notification=False
        )

        for row in self.revisions_table.get_selected_rows():
            item = self.revision_items[row]
            self.action.append(
                self.svn.revpropset,
                prop_name,
                prop_value,
                url,
                self.svn.revision("number", item.revision.number)
            )
            
            callback(row, prop_value)
        
        self.action.start()

    def on_log_message_edited(self, index, val):
        self.revision_items[index]["message"] = val
        self.revisions_table.set_row_item(index, 3, val)
        self.message.set_text(val)

    def on_author_edited(self, index, val):
        self.revision_items[index]["author"] = val
        self.revisions_table.set_row_item(index, 1, val)

    def update_revision_message(self):
        combined_paths = []
        subitems = []
               
        for selected_row in self.revisions_table.get_selected_rows():
            item = self.revision_items[selected_row]
            
            if len(self.revisions_table.get_selected_rows()) == 1:
                self.message.set_text(item["message"])
            else:
                indented_message = item["message"].replace("\n","\n\t")
                self.message.append_text(
					"%s %s:\n\t%s\n" % (REVISION_LABEL,
                                        str(item.revision.number),
                                        indented_message))
            if item.changed_paths is not None:
                for subitem in item.changed_paths:
                    
                    copyfrom_rev = ""
                    if hasattr(subitem.copyfrom_revision, "number"):
                        copyfrom_rev = subitem.copyfrom_revision.number
                    
                    if subitem.path not in combined_paths:
                        combined_paths.append(subitem.path)
                        
                        subitems.append([
                            subitem.action,
                            subitem.path,
                            subitem.copyfrom_path,
                            copyfrom_rev
                        ])

        subitems.sort(lambda x, y: cmp(x[1],y[1]))
        for subitem in subitems:
            self.paths_table.append([
                subitem[0],
                subitem[1],
                subitem[2],
                subitem[3]
            ])

    def show_revisions_table_popup_menu(self, treeview, data):
        revisions = []
        for row in self.revisions_table.get_selected_rows():
            line = {
                "revision": self.svn.revision("number", number=self.revision_items[row].revision.number),
                "author": self.revision_items[row]["author"],
                "message": self.revision_items[row]["message"]
            }
            if self.revision_items[row+1]:
                line["next_revision"] = self.svn.revision("number", number=self.revision_items[row+1].revision.number)
            
            revisions.append(line)
            
        LogTopContextMenu(self, data, self.path, revisions).show()

    def show_paths_table_popup_menu(self, treeview, data):
        revisions = []
        for row in self.revisions_table.get_selected_rows():
            revisions.append({
                "revision": self.svn.revision("number", number=self.revision_items[row].revision.number),
                "author": self.revision_items[row]["author"],
                "message": self.revision_items[row]["message"]
            })
        
        # If we don't do this, we actually get the revisions in reverse order
        # (usually, always?). Don't worry about non-numeric revisions (eg.
        # HEAD), since we explicitly construct them above with a number
        revisions.sort(key=lambda item: item["revision"].value)
        
        paths = []
        for row in self.paths_table.get_selected_rows():
            paths.append(self.paths_table.get_row(row)[1])
        
        SVNLogBottomContextMenu(self, data, paths, revisions).show()

    def on_previous_clicked(self, widget):
        self.rev_start = self.previous_starts.pop()
        self.load_or_refresh()
                    
    def on_next_clicked(self, widget):
        self.previous_starts.append(self.rev_start)
        self.rev_start = self.rev_end - 1

        if self.rev_start < 1:
            self.rev_start = 1

        self.load_or_refresh()

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

    def view_diff_for_path(self, url, latest_revision_number, earliest_revision_number=None, sidebyside=False):
        from rabbitvcs.ui.diff import diff_factory

        if earliest_revision_number == None:
            earliest_revision_number = latest_revision_number
        
        self.action = SVNAction(
            self.svn,
            notification=False
        )
        self.action.append(
            diff_factory,
            url, 
            earliest_revision_number - 1,
            url, 
            latest_revision_number,
            sidebyside=sidebyside
        )
        self.action.start()

class GitLog(Log):
    def __init__(self, path):
        Log.__init__(self, path)
        
        self.git = self.vcs.git(path)
        self.limit = 500
        
        self.revision_number_column = 1

        self.revisions_table = rabbitvcs.ui.widget.Table(
            self.get_widget("revisions_table"),
            [rabbitvcs.ui.widget.TYPE_GRAPH, gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Graph"), _("Revision"), _("Author"), 
                _("Date"), _("Message")],
            filters=[{
                "callback": rabbitvcs.ui.widget.git_revision_filter,
                "user_data": {
                    "column": 1
                }
            }],
            callbacks={
                "mouse-event":   self.on_revisions_table_mouse_event
            }
        )

        self.paths_table = rabbitvcs.ui.widget.Table(
            self.get_widget("paths_table"),
            [gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Action"), _("Path")],
            callbacks={
                "mouse-event":      self.on_paths_table_mouse_event,
                "row-activated":    self.on_paths_table_row_activated
            },
            flags={
                "sortable": True, 
                "sort_on": 1
            }
        )
        self.start_point = 0
        self.load_or_refresh()

    #
    # Log-loading callback methods
    #
    
    def refresh(self):
        """
        Refresh the items in the main log table that shows Revision/Author/etc.
        
        """
        
        self.revisions_table.clear()
        self.message.set_text("")
        self.paths_table.clear()
        
        # Make sure the int passed is the order the log call was made
        self.revision_items = self.action.get_result(0)
        
        self.set_start_revision(self.revision_items[0]["commit"][:7])
        self.set_end_revision(self.revision_items[-1]["commit"][:7])

        grapher = revision_grapher(self.revision_items)
        max_columns = 1
        for (item, node, in_lines, out_lines) in grapher:
            if max_columns < len(out_lines):
                max_columns = len(out_lines)

        graph_column = self.revisions_table.get_column(0)
        cell = graph_column.get_cell_renderers()[0]
        self.revisions_table.set_column_width(0, 16*max_columns)

        for (item, node, in_lines, out_lines) in grapher:
            msg = rabbitvcs.util.helper.format_long_text(item["message"], 80)
            
            author = _("(no author)")
            if "committer" in item:
                author = item["committer"]
                pos = author.find("<")
                if pos != -1:
                    author = author[0:pos-1]

            commit_date = datetime.strptime(item["commit_date"][0:-6], "%a %b %d %H:%M:%S %Y")
            self.revisions_table.append([
                (node, in_lines, out_lines),
                item["commit"],
                author,
                rabbitvcs.util.helper.format_datetime(commit_date),
                msg
            ])

        self.check_previous_sensitive()
        self.check_next_sensitive()
        self.set_loading(False)
    
    def load(self):
        self.set_loading(True)

        self.action = GitAction(
            self.git,
            notification=False,
            run_in_thread=False
        )        

        self.action.append(
            self.git.log,
            path=self.path,
            skip=self.start_point,
            limit=self.limit+1
        )
        self.action.append(self.refresh)
        self.action.run()

    def update_revision_message(self):
        combined_paths = []
        subitems = []
        
        for selected_row in self.revisions_table.get_selected_rows():
            item = self.revision_items[selected_row]

            if len(self.revisions_table.get_selected_rows()) == 1:
                self.message.set_text(item["message"])
            else:
                indented_message = item["message"].replace("\n","\n\t")
                self.message.append_text(
					"%s %s:\n\t%s\n" % (REVISION_LABEL,
                                        item["commit"][:7],
                                        indented_message))

            if item["changed_paths"]:
                for subitem in item["changed_paths"]:
                    
                    if subitem["path"] not in combined_paths:
                        combined_paths.append(subitem["path"])
                        
                        change = "+%s/-%s" % (subitem["additions"], subitem["removals"])
                        subitems.append([
                            change,
                            subitem["path"]
                        ])

        subitems.sort(lambda x, y: cmp(x[1],y[1]))
        for subitem in subitems:
            self.paths_table.append([
                subitem[0],
                subitem[1]
            ])

    def show_revisions_table_popup_menu(self, treeview, data):
        revisions = []
        for row in self.revisions_table.get_selected_rows():
            line = {
                "revision": self.git.revision(self.revision_items[row]["commit"]),
                "author": self.revision_items[row]["author"],
                "message": self.revision_items[row]["message"]
            }
            try:
                line["next_revision"] = self.git.revision(self.revision_items[row+1]["commit"])
            except IndexError,e:
                pass
                
            revisions.append(line)
            
        LogTopContextMenu(self, data, self.path, revisions).show()

    def show_paths_table_popup_menu(self, treeview, data):
        return

    def on_previous_clicked(self, widget):
        self.start_point -= self.limit
        if self.start_point < 0:
            self.start_point = 0
        self.load_or_refresh()
                    
    def on_next_clicked(self, widget):
        self.start_point += self.limit
        self.load()

    def check_previous_sensitive(self):
        sensitive = (self.start_point > 0)
        self.get_widget("previous").set_sensitive(sensitive)

    def check_next_sensitive(self):
        sensitive = True
        if len(self.revision_items) <= self.limit:
            sensitive = False

        self.get_widget("next").set_sensitive(sensitive)

    def view_diff_for_path(self, url, latest_revision_number, earliest_revision_number=None, sidebyside=False):
        pass

class SVNLogDialog(SVNLog):
    def __init__(self, path, ok_callback=None, multiple=False):
        """
        Override the normal SVNLog class so that we can hide the window as we need.
        Also, provide a callback for when the OK button is clicked so that we
        can get some desired data.
        """
        SVNLog.__init__(self, path)
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

class GitLogDialog(GitLog):
    def __init__(self, path, ok_callback=None, multiple=False):
        """
        Override the normal GitLog class so that we can hide the window as we need.
        Also, provide a callback for when the OK button is clicked so that we
        can get some desired data.
        """
        GitLog.__init__(self, path)
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


class MenuViewDiffWorkingCopy(MenuItem):
    identifier = "RabbitVCS::View_Diff_Working_Copy"
    label = _("View diff against working copy")
    icon = "rabbitvcs-diff"

class MenuViewDiffPreviousRevision(MenuItem):
    identifier = "RabbitVCS::View_Diff_Previous_Revision"
    label = _("View diff against previous revision")
    icon = "rabbitvcs-diff"

class MenuViewDiffRevisions(MenuItem):
    identifier = "RabbitVCS::View_Diff_Revisions"
    label = _("View diff between revisions")
    icon = "rabbitvcs-diff"

class MenuCompareWorkingCopy(MenuItem):
    identifier = "RabbitVCS::Compare_Working_Copy"
    label = _("Compare with working copy")
    icon = "rabbitvcs-compare"

class MenuComparePreviousRevision(MenuItem):
    identifier = "RabbitVCS::Compare_Previous_Revision"
    label = _("Compare with previous revision")
    icon = "rabbitvcs-compare"

class MenuCompareRevisions(MenuItem):
    identifier = "RabbitVCS::Compare_Revisions"
    label = _("Compare revisions")
    icon = "rabbitvcs-compare"

class MenuShowChangesPreviousRevision(MenuItem):
    # This is for the revs list
    identifier = "RabbitVCS::Show_Changes_Previous_Revision"
    label = _("Show changes against previous revision")
    icon = "rabbitvcs-changes"
    
class MenuShowChangesRevisions(MenuItem):
    # This is for the revs list
    identifier = "RabbitVCS::Show_Changes_Revisions"
    label = _("Show changes between revisions")
    icon = "rabbitvcs-changes"

class MenuUpdateToThisRevision(MenuItem):
    identifier = "RabbitVCS::Update_To_This_Revision"
    label = _("Update to this revision")
    tooltip = _("Update the selected path to this revision")
    icon = "rabbitvcs-update"

class MenuEditAuthor(MenuItem):
    identifier = "RabbitVCS::Edit_Author"
    label = _("Edit author...")

class MenuEditAuthor(MenuItem):
    identifier = "RabbitVCS::Edit_Author"
    label = _("Edit author...")

class MenuEditLogMessage(MenuItem):
    identifier = "RabbitVCS::Edit_Log_Message"
    label = _("Edit log message...")

class MenuEditRevisionProperties(MenuItem):
    identifier = "RabbitVCS::Edit_Revision_Properties"
    label = _("Edit revision properties...")
    icon = gtk.STOCK_EDIT

class LogTopContextMenuConditions:
    def __init__(self, vcs, path, revisions):
        self.vcs = vcs
        self.path = path
        self.revisions = revisions
        self.guess = self.vcs.guess(path)
        
    def view_diff_working_copy(self, data=None):
        return (len(self.revisions) == 1)

    def view_diff_previous_revision(self, data=None):
        item = self.revisions[0]["revision"]
        return (item.value > 1 and len(self.revisions) == 1)

    def view_diff_revisions(self, data=None):
        return (len(self.revisions) > 1)
        
    def compare_working_copy(self, data=None):
        return (len(self.revisions) == 1) 

    def compare_previous_revision(self, data=None):
        item = self.revisions[0]["revision"]
        return (item.value > 1 and len(self.revisions) == 1)

    def compare_revisions(self, data=None):
        return (len(self.revisions) > 1)

    def show_changes_previous_revision(self, data=None):
        item = self.revisions[0]["revision"]
        return (self.guess["vcs"] == "svn" and item.value > 1 and len(self.revisions) == 1)

    def show_changes_revisions(self, data=None):
        return (self.guess["vcs"] == "svn" and len(self.revisions) > 1)

    def update_to_this_revision(self, data=None):
        return (self.guess["vcs"] == "svn" and len(self.revisions) == 1)

    def checkout(self, data=None):
        return (self.guess["vcs"] == "svn" and len(self.revisions) == 1)

    def branch_tag(self, data=None):
        return (self.guess["vcs"] == "svn" and len(self.revisions) == 1)

    def export(self, data=None):
        return (self.guess["vcs"] == "svn" and len(self.revisions) == 1)

    def edit_author(self, data=None):
        return self.guess["vcs"] == "svn"

    def edit_log_message(self, data=None):
        return self.guess["vcs"] == "svn"

    def edit_revision_properties(self, data=None):
        return (self.guess["vcs"] == "svn" and len(self.revisions) == 1)

    def separator(self, data=None):
        return self.guess["vcs"] == "svn"

class LogTopContextMenuCallbacks:
    def __init__(self, caller, vcs, path, revisions):
        self.caller = caller
        self.vcs = vcs
        self.svn = self.vcs.svn()
        self.path = path
        self.revisions = revisions
        
    def view_diff_working_copy(self, widget, data=None):
        rabbitvcs.util.helper.launch_ui_window("diff", ["%s@%s" % (self.path, self.revisions[0]["revision"].value)])

    def view_diff_previous_revision(self, widget, data=None):
        rabbitvcs.util.helper.launch_ui_window("diff", [
            "%s@%s" % (self.path, self.revisions[0]["revision"].value),
            "%s@%s" % (self.path, self.revisions[0]["next_revision"].value)
        ])

    def view_diff_revisions(self, widget, data=None):
        path_older = self.path
        if self.vcs.guess(self.path) == rabbitvcs.vcs.VCS_SVN:
            path_older = self.vcs.svn.get_repo_url(self.path)
    
        rabbitvcs.util.helper.launch_ui_window("diff", [
            "%s@%s" % (path_older, self.revisions[1]["revision"].value),
            "%s@%s" % (self.path, self.revisions[0]["revision"].value)
        ])

    def compare_working_copy(self, widget, data=None):
        path_older = self.path
        if self.vcs.guess(self.path) == rabbitvcs.vcs.VCS_SVN:
            path_older = self.vcs.svn.get_repo_url(self.path)
    
        rabbitvcs.util.helper.launch_ui_window("diff", [
            "%s@%s" % (path_older, self.revisions[0]["revision"].value),
            "%s" % (self.path)
        ])

    def compare_previous_revision(self, widget, data=None):
        rabbitvcs.util.helper.launch_ui_window("diff", [
            "-s",
            "%s@%s" % (self.path, self.revisions[0]["revision"].value),
            "%s@%s" % (self.path, self.revisions[0]["next_revision"].value)
        ])

    def compare_revisions(self, widget, data=None):
        path_older = self.path
        if self.vcs.guess(self.path) == rabbitvcs.vcs.VCS_SVN:
            path_older = self.vcs.svn.get_repo_url(self.path)
    
        rabbitvcs.util.helper.launch_ui_window("diff", [
            "-s",
            "%s@%s" % (path_older, self.revisions[1]["revision"].value),
            "%s@%s" % (self.path, self.revisions[0]["revision"].value)
        ])

    def show_changes_previous_revision(self, widget, data=None):
        from rabbitvcs.ui.changes import Changes
        rev_first = self.revisions[0]["revision"].value
        rev_last = rev_first - 1
        path = self.svn.get_repo_url(self.path)

        # FIXME: why does this have the opposite sense to the callback from the
        # paths list?
        Changes(
            path, 
            rev_last, 
            path, 
            rev_first
        )

    def show_changes_revisions(self, widget, data=None):
        from rabbitvcs.ui.changes import Changes
        rev_first = self.revisions[0]["revision"].value
        rev_last = self.revisions[-1]["revision"].value
        path = self.svn.get_repo_url(self.path)

        # FIXME: why does this have the opposite sense to the callback from the
        # paths list?
        Changes(
            path, 
            rev_last, 
            path, 
            rev_first
        )

    def update_to_this_revision(self, widget, data=None):
        action = SVNAction(
            self.svn
        )

        action.append(action.set_header, _("Update To Revision"))
        action.append(action.set_status, _("Updating..."))
        action.append(
            self.svn.update, 
            self.path,
            revision=self.svn.revision("number", self.revisions[0]["revision"].value),
            recurse=True,
            ignore_externals=False
        )
        action.append(action.set_status, _("Completed Update"))
        action.append(action.finish)
        action.start()
        
    def checkout(self, widget, data=None):
        from rabbitvcs.ui.checkout import Checkout
        url = self.svn.get_repo_url(self.path)
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

    def edit_revision_properties(self, widget, data=None):
        from rabbitvcs.ui.revprops import SVNRevisionProperties
        url = self.svn.get_repo_url(self.path)
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
        
        @param  path: The loaded path
        @type   path: string
        
        @param  revisions: The selected revisions
        @type   revisions: list of rabbitvcs.vcs.Revision object
        
        """        
        self.caller = caller
        self.event = event
        self.path = path
        self.revisions = revisions
        self.vcs = rabbitvcs.vcs.VCS()

        self.conditions = LogTopContextMenuConditions(
            self.vcs, 
            self.path, 
            self.revisions
        )
        
        self.callbacks = LogTopContextMenuCallbacks(
            self.caller,
            self.vcs, 
            self.path,
            self.revisions
        )

        # The first element of each tuple is a key that matches a
        # ContextMenuItems item.  The second element is either None when there
        # is no submenu, or a recursive list of tuples for desired submenus.
        self.structure = [
            (MenuViewDiffWorkingCopy, None),
            (MenuViewDiffPreviousRevision, None),
            (MenuViewDiffRevisions, None),
            (MenuCompareWorkingCopy, None),
            (MenuComparePreviousRevision, None),
            (MenuCompareRevisions, None),
            (MenuShowChangesPreviousRevision, None),
            (MenuShowChangesRevisions, None),
            (MenuSeparator, None),
            (MenuUpdateToThisRevision, None),
            (MenuCheckout, None),
            (MenuBranchTag, None),
            (MenuExport, None),
            (MenuSeparator, None),
            (MenuEditAuthor, None),
            (MenuEditLogMessage, None),
            (MenuEditRevisionProperties, None)
        ]
        
    def show(self):
        if len(self.revisions) == 0:
            return

        context_menu = GtkContextMenu(self.structure, self.conditions, self.callbacks)
        context_menu.show(self.event)


class SVNLogBottomContextMenuConditions:
    def __init__(self, vcs, paths, revisions):
        self.vcs = vcs
        self.paths = paths
        self.revisions = revisions

    def view_diff_working_copy(self, data=None):
        return False

    def view_diff_previous_revision(self, data=None):
        item = self.revisions[0]["revision"]
        return (item.value > 1 and len(self.revisions) == 1)

    def view_diff_revisions(self, data=None):
        return (len(self.paths) == 1 and len(self.revisions) > 1)

    def compare_working_copy(self, data=None):
        return False

    def compare_previous_revision(self, data=None):
        item = self.revisions[0]["revision"]
        return (item.value > 1 and len(self.revisions) == 1)

    def compare_revisions(self, data=None):
        return (len(self.paths) == 1 and len(self.revisions) > 1)

    def show_changes_previous_revision(self, data=None):
        item = self.revisions[0]["revision"]
        return (item.value > 1 and len(self.revisions) == 1)

    def show_changes_revisions(self, data=None):
        return (len(self.paths) == 1 and len(self.revisions) > 1)

    def _open(self, data=None):
        return True

    def annotate(self, data=None):
        return (len(self.paths) == 1)

    def separator(self, data=None):
        return True

class SVNLogBottomContextMenuCallbacks:
    def __init__(self, caller, vcs, paths, revisions):
        self.caller = caller
        self.vcs = vcs
        self.svn = self.vcs.svn()
        self.paths = paths
        self.revisions = revisions

    def view_diff_previous_revision(self, widget, data=None):
        rev = self.revisions[0]["revision"].value
        path_item = self.paths[0]
        url = self.caller.root_url + path_item
        self.caller.view_diff_for_path(url, rev)

    def view_diff_revisions(self, widget, data=None):
        rev_first = self.revisions[0]["revision"].value - 1
        rev_last = self.revisions[-1]["revision"].value
        path_item = self.paths[0]
        url = self.caller.root_url + path_item
        self.caller.view_diff_for_path(url, latest_revision_number=rev_last,
                                       earliest_revision_number=rev_first)

    def compare_previous_revision(self, widget, data=None):
        rev = self.revisions[0]["revision"].value
        path_item = self.paths[0]
        url = self.caller.root_url + path_item
        self.caller.view_diff_for_path(url, rev, sidebyside=True)
    
    def compare_revisions(self, widget, data=None):
        earliest_rev = self.revisions[0]["revision"].value
        latest_rev = self.revisions[-1]["revision"].value
        path_item = self.paths[0]
        url = self.caller.root_url + path_item
        self.caller.view_diff_for_path(url,
                                        latest_rev,
                                        sidebyside=True,
                                        earliest_revision_number=earliest_rev)

    def show_changes_previous_revision(self, widget, data=None):
        rev_first = self.revisions[0]["revision"].value - 1
        rev_last = rev_first - 1
        path_item = self.paths[0]
        url = self.caller.root_url + path_item

        from rabbitvcs.ui.changes import Changes
        Changes(
            url, 
            rev_first, 
            url, 
            rev_last
        )
    
    def show_changes_revisions(self, widget, data=None):
        rev_first = self.revisions[0]["revision"].value - 1
        rev_last = self.revisions[-1]["revision"].value
        path_item = self.paths[0]
        url = self.caller.root_url + path_item

        from rabbitvcs.ui.changes import Changes
        Changes(
            url, 
            rev_first, 
            url, 
            rev_last
        )

    def _open(self, widget, data=None):
        self.action = SVNAction(
            self.svn,
            notification=False
        )

        # This allows us to open multiple files at once
        dests = []
        for path in self.paths:
            url = self.caller.root_url + path
            dest = "/tmp/rabbitvcs-" + str(self.revisions[0]["revision"].value) + "-" + os.path.basename(path)
            self.action.append(
                self.svn.export,
                url,
                dest,
                revision=self.revisions[0]["revision"]
            )
            dests.append(dest)
        
        for dest in dests:
            self.action.append(rabbitvcs.util.helper.open_item, dest)
            
        self.action.start()

    def annotate(self, widget, data=None):
        url = self.caller.root_url + self.paths[0]

        from rabbitvcs.ui.annotate import Annotate
        Annotate(url, self.revisions[0]["revision"].value)

class SVNLogBottomContextMenu:
    """
    Defines context menu items for a table with files
    
    """
    def __init__(self, caller, event, paths, revisions):
        """    
        @param  caller: The calling object
        @type   caller: object
        
        @param  base_dir: The curent working directory
        @type   base_dir: string
        
        @param  paths: The selected paths
        @type   paths: list

        @param  revision: The selected revision
        @type   revision: rabbitvcs.vcs.Revision object
        
        """        
        self.caller = caller
        self.event = event
        self.paths = paths
        self.revisions = revisions
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

        self.conditions = LogBottomContextMenuConditions(
            self.vcs, 
            self.paths, 
            self.revisions
        )
        
        self.callbacks = LogBottomContextMenuCallbacks(
            self.caller,
            self.vcs, 
            self.paths,
            self.revisions
        )

        # The first element of each tuple is a key that matches a
        # ContextMenuItems item.  The second element is either None when there
        # is no submenu, or a recursive list of tuples for desired submenus.
        self.structure = [
            (MenuViewDiffRevisions, None),
            (MenuViewDiffPreviousRevision, None),
            (MenuComparePreviousRevision, None),
            (MenuCompareRevisions, None),
            (MenuShowChangesPreviousRevision, None),
            (MenuShowChangesRevisions, None),
            (MenuSeparator, None),
            (MenuOpen, None),
            (MenuAnnotate, None)
        ]
        
    def show(self):
        if len(self.paths) == 0:
            return

        context_menu = GtkContextMenu(self.structure, self.conditions, self.callbacks)
        context_menu.show(self.event)

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNLog,
    rabbitvcs.vcs.VCS_GIT: GitLog
}

dialogs_map = {
    rabbitvcs.vcs.VCS_SVN: SVNLogDialog,
    rabbitvcs.vcs.VCS_GIT: GitLogDialog
}

def log_factory(path):
    guess = rabbitvcs.vcs.guess(path)
    return classes_map[guess["vcs"]](path)

def log_dialog_factory(path, ok_callback=None, multiple=False):
    guess = rabbitvcs.vcs.guess(path)
    return dialogs_map[guess["vcs"]](path, ok_callback, multiple)

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs log [url_or_path]")
            
    window = log_factory(paths[0])
    window.register_gtk_quit()
    gtk.main()
