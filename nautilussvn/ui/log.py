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

from __future__ import division
import threading
from datetime import datetime

import pygtk
import gobject
import gtk

from nautilussvn.ui import InterfaceView
from nautilussvn.ui.action import VCSAction
from nautilussvn.ui.dialog import MessageBox
import nautilussvn.ui.widget
import nautilussvn.lib.helper
import nautilussvn.lib.vcs
from nautilussvn.lib.decorators import gtk_unsafe

from nautilussvn import gettext
_ = gettext.gettext

DATETIME_FORMAT = nautilussvn.lib.helper.LOCAL_DATETIME_FORMAT

class Log(InterfaceView):
    """
    Provides an interface to the Log UI
    
    """

    selected_rows = []
    selected_row = []
    
    limit = 100

    def __init__(self, path):
        """
        @type   path: string
        @param  path: A path for which to get log items
        
        """
        
        InterfaceView.__init__(self, "log", "Log")

        self.get_widget("Log").set_title(_("Log - %s") % path)
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()
        
        self.path = path
        self.cache = LogCache()

        self.rev_start = None
        self.rev_max = 1
        self.previous_starts = []
        self.initialize_revision_labels()
        
        self.get_widget("limit").set_text(str(self.limit))
        
        self.revisions_table = nautilussvn.ui.widget.Table(
            self.get_widget("revisions_table"),
            [gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Revision"), _("Author"), 
                _("Date"), _("Message")]
        )
        self.revisions_table.allow_multiple()

        self.paths_table = nautilussvn.ui.widget.Table(
            self.get_widget("paths_table"),
            [gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Action"), _("Path"), 
                _("Copy From Path"), _("Copy From Revision")]
        )

        self.message = nautilussvn.ui.widget.TextView(
            self.get_widget("message")
        )

        self.pbar = nautilussvn.ui.widget.ProgressBar(self.get_widget("pbar"))
        
        self.stop_on_copy = False
        self.load_or_refresh()

    #
    # UI Signal Callback Methods
    #

    def on_destroy(self, widget, data=None):
        self.close()

    def on_cancel_clicked(self, widget, data=None):
        if self.is_loading:
            self.action.set_cancel(True)
            self.pbar.set_text(_("Cancelled"))
            self.pbar.update(1)
            self.set_loading(False)
        else:
            self.close()
        
    def on_ok_clicked(self, widget, data=None):
        if self.is_loading:
            self.action.set_cancel(True)    
        self.close()

    def on_revisions_table_cursor_changed(self, treeview, data=None):
        self.on_revisions_table_event(treeview, data)

    def on_revisions_table_button_released(self, treeview, data=None):
        self.on_revisions_table_event(treeview, data)

    def on_revisions_table_event(self, treeview, data=None):
        selection = treeview.get_selection()
        (liststore, indexes) = selection.get_selected_rows()

        self.selected_rows = []
        for tup in indexes:
            self.selected_rows.append(tup[0])

        if len(self.selected_rows) == 0:
            self.message.set_text("")
            self.paths_table.clear()
            return

        item = self.revision_items[self.selected_rows[0]]

        self.paths_table.clear()
        if len(self.selected_rows) == 1:
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
    
    def load_or_refresh(self):
        if self.cache.has(self.rev_start):
            self.refresh()
        else:
            self.load()
    
    def on_stop_on_copy_toggled(self, widget):
        self.stop_on_copy = self.get_widget("stop_on_copy").get_active()
        if not self.is_loading:
            self.refresh()
    
    def on_refresh_clicked(self, widget):
        self.limit = int(self.get_widget("limit").get_text())
        self.cache.empty()
        self.load()
    
    #
    # Helper methods
    #
          
    def get_selected_revision_numbers(self):
        if len(self.selected_rows) == 0:
            return ""

        revisions = []
        for row in self.selected_rows:
            revisions.append(int(self.revisions_table.get_row(row)[0]))

        revisions.sort()
        return nautilussvn.lib.helper.encode_revisions(revisions)

    def get_selected_revision_number(self):
        if len(self.selected_rows):
            return self.revisions_table.get_row(self.selected_rows[0])[0]
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
        self.pbar.set_text(_("Loading..."))
        
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

        total = len(self.revision_items)
        inc = 1 / total
        fraction = 0
        
        for item in self.revision_items:
            msg = item.message.replace("\n", " ")
            if len(msg) > 80:
                msg = "%s..." % msg[0:80]
        
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
                        self.pbar.update(1)
                        return

            fraction += inc
            self.pbar.update(fraction)
            
        self.check_previous_sensitive()
        self.check_next_sensitive()
        self.set_loading(False)
        self.pbar.set_text(_("Finished"))

    def load(self):
        self.set_loading(True)
        self.pbar.set_text(_("Retrieving Log Information..."))
        self.pbar.start_pulsate()
        
        self.action = VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set(),
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
        self.action.append(self.pbar.stop_pulsate)
        self.action.append(self.refresh)
        self.action.start()

    def set_loading(self, loading):
        self.is_loading = loading

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
    
    def on_cancel_clicked(self, widget, data=None):
        self.hide()
    
    def on_ok_clicked(self, widget, data=None):
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

if __name__ == "__main__":
    from nautilussvn.ui import main
    (options, paths) = main()
            
    window = Log(paths[0])
    window.register_gtk_quit()
    gtk.main()
