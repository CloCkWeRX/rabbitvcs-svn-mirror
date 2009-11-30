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
import thread

import pygtk
import gobject
import gtk
from datetime import datetime

from rabbitvcs.ui import InterfaceView
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
import rabbitvcs.lib.helper
import rabbitvcs.lib.vcs
from rabbitvcs.lib.log import Log
from rabbitvcs.lib.decorators import gtk_unsafe

log = Log("rabbitvcs.ui.add")

from rabbitvcs import gettext
_ = gettext.gettext

gtk.gdk.threads_init()

class Browser(InterfaceView):
    def __init__(self, url):
        InterfaceView.__init__(self, "browser", "Browser")

        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        self.url = self.vcs.get_repo_url(url)

        self.urls = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("urls"), 
            rabbitvcs.lib.helper.get_repository_paths()
        )
        if self.url:
            self.urls.set_child_text(self.url)

        self.revision_selector = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("revision_container"),
            self.vcs,
            url_combobox=self.urls
        )

        self.items = []
        self.table = rabbitvcs.ui.widget.Table(
            self.get_widget("items"), 
            [rabbitvcs.ui.widget.TYPE_PATH, gobject.TYPE_INT, 
                gobject.TYPE_INT, gobject.TYPE_STRING, gobject.TYPE_FLOAT], 
            [_("Path"), _("Revision"), _("Size"), _("Author"), _("Date")],
            filters=[{
                "callback": self.file_filter,
                "user_data": {
                    "column": 0
                }
            },{
                "callback": self.size_filter,
                "user_data": {
                    "column": 2
                }
            },{
                "callback": self.date_filter,
                "user_data": {
                    "column": 4
                }
            }],
            filter_types=[gobject.TYPE_STRING, gobject.TYPE_INT, 
                gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING], 
            callbacks={
                "file-column-callback": self.file_column_callback,
                "row-activated": self.on_row_activated
            }
        )

        if url:
            self.load()

    def load(self):
        self.action = rabbitvcs.ui.action.VCSAction(
            self.vcs,
            notification=False
        )
        
        self.action.append(self.vcs.list, self.urls.get_active_text(), recurse=False)
        self.action.append(self.populate_files_table)
        self.action.start()

    @gtk_unsafe
    def populate_files_table(self):
        self.table.clear()
        self.items = self.action.get_result(0)
        self.items[0][0].repos_path = ".."
        self.items.sort(self.sort_files)
        for item,locked in self.items:
            self.table.append([
                item.repos_path,
                item.created_rev.number,
                item.size,
                item.last_author,
                item.time
            ])

    def on_destroy(self, widget):
        self.close()
    
    def on_close_clicked(self, widget):
        self.close()

    def on_refresh_clicked(self, widget):
        self.load()

    def on_row_activated(self, treeview, data, col):
        path = self.table.get_selected_row_items(0)[0]
        if path == "..":
            path = self.url.split("/")[0:-1]
            self.url = "/".join(path)
        else:
            self.url = rabbitvcs.lib.helper.url_join(
                self.urls.get_active_text(), 
                os.path.basename(path)
            )

        self.urls.set_child_text(self.url)
        self.load()

    def file_column_callback(self, filename):
        """
        Determine the node kind (dir or file) from our retrieved items list
        """
        
        for item,locked in self.items:
            if item.repos_path == filename:
                return self.vcs.NODE_KINDS_REVERSE[item.kind]
        return None

    def sort_files(self, x, y):
        """
        Sort the browser listing so that folders are on top and then sort
        alphabetically.

        """
        xkind = self.vcs.NODE_KINDS_REVERSE[x[0].kind]
        ykind = self.vcs.NODE_KINDS_REVERSE[y[0].kind]
        if xkind == "dir" and ykind == "dir":
            return cmp(x[0].repos_path, y[0].repos_path)
        elif xkind == "dir" and ykind == "file":
            return -1
        else:
            return 1

    def file_filter(self, row, column, user_data=None):
        """
        Table filter to just show the basename of the item path
        """
        
        if row[column]:
            return os.path.basename(row[column])

    def size_filter(self, row, column, user_data=None):
        """
        Table filter to convert the item size to a "pretty" filesize
        """
        
        if self.file_column_callback(row[0]) == "file":
            return rabbitvcs.lib.helper.pretty_filesize(row[column])
        else:
            return ""

    def date_filter(self, row, column, user_data=None):
        """
        Table filter to convert the item date to something readable
        """
        
        if row[column]:
            change_time = datetime.fromtimestamp(row[column])
            return change_time.strftime("%Y-%m-%d %H:%M:%S")
        
        return str(row[column])

class BrowserDialog(Browser):
    def __init__(self, path, callback=None):
        """
        Override the normal Browser class so that we can hide the window as we need.
        Also, provide a callback for when the close button is clicked so that we
        can get some desired data.
        """
        Browser.__init__(self, path)
        self.callback = callback
        
    def on_destroy(self, widget):
        pass
    
    def on_close_clicked(self, widget, data=None):
        self.hide()
        if self.callback is not None:
            path = self.urls.get_active_text()
            selected = self.table.get_selected_row_items(0)
            if len(selected) > 0:
                path = rabbitvcs.lib.helper.url_join(
                    path,
                    os.path.basename(selected[0])
                )
            self.callback(path)

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, url) = main(
        usage="Usage: rabbitvcs browser [url]"
    )

    window = Browser(url[0])
    window.register_gtk_quit()
    gtk.main()
