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

import os.path

try:
    import gtkspell
    HAS_GTKSPELL = True
except ImportError:
    HAS_GTKSPELL = False

try:
    import gtksourceview
    HAS_GTKSOURCEVIEW = True
except ImportError:
    HAS_GTKSOURCEVIEW = False

import rabbitvcs.lib.helper

from rabbitvcs import gettext
_ = gettext.gettext

from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.ui.widget")

TOGGLE_BUTTON = 'TOGGLE_BUTTON'
PATH_ENTRY = 'PATH_ENTRY'
SEPARATOR = u'\u2015' * 10

from pprint import pformat

def path_filter(model, iter, column, user_data):
    base_dir = user_data["base_dir"]
    path_entries = user_data["path_entries"]
    
    data = model.get_model().get_value(
                model.convert_iter_to_child_iter(iter),
                column)

    if column in path_entries:
        relpath = rabbitvcs.lib.helper.get_relative_path(base_dir, data)
        if relpath == "":
            relpath = os.path.basename(data)
        return relpath
    else:
        return data 

class Table:
    def __init__(self, treeview, coltypes, colnames, values=[], base_dir=None, path_entries=[]):
        # The list given as "path_entries" should contain the 0-indexed
        # positions of the path columns, so that the can be expressed relative
        # to "base_dir".
        
    
        self.treeview = treeview
        self.selected_rows = []

        i = 0       
        for name in colnames:
            if name == TOGGLE_BUTTON:
                cell = gtk.CellRendererToggle()
                cell.set_property('activatable', True)
                cell.connect("toggled", self.toggled_cb, i)
                col = gtk.TreeViewColumn("", cell)
                col.set_attributes(cell, active=i)  
            else:
                cell = gtk.CellRendererText()
                cell.set_property('yalign', 0)
                col = gtk.TreeViewColumn(name, cell)
                col.set_attributes(cell, text=i)

            self.treeview.append_column(col)
            i += 1
        
        self.data = gtk.ListStore(*coltypes)
        
        # self.filter == filtered data (abs paths -> rel paths)
        # self.data == actual data
        
        # The filter is there to change the way data is displayed. The data
        # should always be accessed via self.data, NOT self.filter.
        self.filter = self.data.filter_new()
        
        user_data = {"base_dir" : base_dir,
                     "path_entries" : path_entries}
        self.filter.set_modify_func(
                        coltypes,
                        path_filter,
                        user_data)
        
        self.treeview.set_model(self.filter)
                        
        for row in values:
            self.data.append(row)
        
        self.set_resizable()

    def toggled_cb(self, cell, path, column):
        model = self.data
        model[path][column] = not model[path][column]

    def append(self, row):
        self.data.append(row)

    def remove(self, index):
        model = self.data
        del model[index]

    def remove_multiple(self, rows):
        i = 0
        for row in rows:
            rm_index = row
            if i > 0:
                rm_index -= 1
            
            self.remove(rm_index)
            i += 1     

    def get_items(self):
        return self.data

    def clear(self):
        self.data.clear()
        
    def get_row(self, index):
        model = self.data
        return model[index]
    
    def set_row(self, index, row):
        model = self.data
        model[index] = row
    
    def set_row_item(self, row, column, val):
        model = self.data
        model[row][column] = val
    
    def allow_multiple(self):
        self.treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        
    def get_activated_rows(self, column=None):
        returner = []
        for row in self.data:
            if row[0]:
                item = row
                if column is not None:
                    item = row[column]
                
                returner.append(item)
                
        return returner
    
    def scroll_to_bottom(self):
        bottom = len(self.get_items()) - 1
        self.treeview.scroll_to_cell(bottom)

    def set_resizable(self, resizable=True):
        for col in self.treeview.get_columns():
            col.set_resizable(resizable)

    def set_column_width(self, column, width=None):
        col = self.treeview.get_column(column)
        if width is not None:
            col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            col.set_fixed_width(width)
        else:
            col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)

    def update_selection(self):
        selection = self.treeview.get_selection()
        (liststore, indexes) = selection.get_selected_rows()

        self.selected_rows = []
        for tup in indexes:
            self.selected_rows.append(tup[0])

    def get_selected_row_items(self, col):
        items = []
        for row in self.selected_rows:
            items.append(self.data[row][col])
        
        return items

    def get_selected_rows(self):
        return self.selected_rows

class ComboBox:
    def __init__(self, cb, items=None):
    
        self.cb = cb
    
        self.model = gtk.ListStore(str)
        if items is not None:
            for i in items:
                self.append(i)

        self.cb.set_model(self.model)

        if type(self.cb) == gtk.ComboBoxEntry:
            self.cb.set_text_column(0)
        elif type(self.cb) == gtk.ComboBox:
            cell = gtk.CellRendererText()
            self.cb.pack_start(cell, True)
            self.cb.add_attribute(cell, 'text', 0)

    def append(self, item):
        self.model.append([item])
        
    def set_active_from_value(self, value):
        index = 0
        for entry in self.model:
            if entry[0] == value:
                self.cb.set_active(index)
                return
            index += 1
    
    def get_active_text(self):
        return self.cb.get_active_text()
    
    def get_active(self):
        return self.cb.get_active()
    
    def set_active(self, index):
        self.cb.set_active(index)
    
    def set_child_text(self, text):
        self.cb.child.set_text(text)
    
    def set_sensitive(self, val):
        self.cb.set_sensitive(val)
        
class TextView:
    def __init__(self, widget=None, value=""):
        if widget is None:
            self.view = gtk.TextView()
        else:
            self.view = widget
        self.buffer = gtk.TextBuffer()
        self.view.set_buffer(self.buffer)
        self.buffer.set_text(value)
        
        if HAS_GTKSPELL:
            gtkspell.Spell(self.view)
        
    def get_text(self):
        return self.buffer.get_text(
            self.buffer.get_start_iter(), 
            self.buffer.get_end_iter()
        )
        
    def set_text(self, text):
        self.buffer.set_text(text)

class SourceView(TextView):
    def __init__(self, widget=None, value=""):
        if HAS_GTKSOURCEVIEW:
            if widget is None:
                self.view = gtksourceview.SourceView(self.buffer)
            else:
                self.view = widget
            self.buffer = gtksourceview.SourceBuffer()
            self.buffer.set_text(value)

            if HAS_GTKSPELL:
                gtkspell.Spell(self.view)

            self.view.show()
        else:
            TextView.__init__(self, widget, value)

class ProgressBar:
    def __init__(self, pbar):
        if pbar is None:
            self.view = gtk.ProgressBar()
        else:
            self.view = pbar
        
        self.timer = None
        
    def start_pulsate(self):
        # Set up an interval to make the progress bar pulse
        # The timeout is removed after the log action finishes
        self.timer = gobject.timeout_add(100, self.update)
    
    def stop_pulsate(self):
        if self.timer:
            gobject.source_remove(self.timer)
        self.timer = None

    def update(self, fraction=None):
        if fraction:
            if self.timer is not None:
                self.stop_pulsate()
                 
            if fraction > 1:
                fraction = 1
            self.view.set_fraction(fraction)
            return False
        else:
            self.view.pulse()
            return True

    def set_text(self, text):
        self.view.set_text(text)

class RevisionSelector:
    """
    Provides a standard way to generate a revision object from the UI.
    
    """
    OPTIONS = [
        _("HEAD"),
        _("Number"),
        _("Working Copy")
    ]

    def __init__(self, container, client, revision=None, 
            url_combobox=None, url_entry=None, url=None, expand=False):
        """
        @type   container: A gtk container object (i.e. HBox, VBox, Box)
        @param  container: The container that to add this widget
        
        @type   client: VCS client object
        @param  client: A vcs client instance (i.e. rabbitvcs.lib.vcs.create_vcs_instance())
        
        @type   revision: int
        @param  revision: A revision number to start with
        
        @type   url_combobox: rabbitvcs.ui.widget.ComboBox
        @param  url_combobox: A repository url combobox

        @type   url_entry: gtk.Entry
        @param  url_entry: A repository url entry
        
        @type   url: str
        @param  url: A repository url string
        
        Note: The url fields are required for use with the log browser.  It can
                be excluded.

        """
        self.client = client
        self.revision = revision
        self.url_combobox = url_combobox
        self.url_entry = url_entry
        self.url = url
    
        hbox = gtk.HBox(0, 4)
        
        self.revision_kind_opt = ComboBox(gtk.ComboBox(), self.OPTIONS)
        self.revision_kind_opt.set_active(0)
        self.revision_kind_opt.cb.connect("changed", self.__revision_kind_changed)
        hbox.pack_start(self.revision_kind_opt.cb, False, False, 0)
        
        self.revision_entry = gtk.Entry()
        hbox.pack_start(self.revision_entry, expand, expand, 0)
        
        self.revision_browse = gtk.Button()
        revision_browse_image = gtk.Image()
        revision_browse_image.set_from_stock(gtk.STOCK_FIND, 1)
        revision_browse_image.show()
        self.revision_browse.add(revision_browse_image)
        self.revision_browse.connect("clicked", self.__revision_browse_clicked)
        hbox.pack_start(self.revision_browse, False, False, 0)

        if self.revision is not None:
            self.set_kind_number(revision)
        else:
            self.set_kind_head()
        
        self.revision_kind_opt.cb.show()
        self.revision_entry.show()
        self.revision_browse.show()
        hbox.show()
        
        container.add(hbox)
    
    def __revision_browse_clicked(self, widget):
        from rabbitvcs.ui.log import LogDialog
        LogDialog(
            self.get_url(), 
            ok_callback=self.__log_closed
        )
    
    def __log_closed(self, data):
        if data is not None:
            self.revision_kind_opt.set_active(1)
            self.revision_entry.set_text(data)

    def __revision_kind_changed(self, widget):
        self.determine_widget_sensitivity()            
    
    def determine_widget_sensitivity(self):
        index = self.revision_kind_opt.get_active()

        # Only allow number entry if "Number" is selected
        if index == 1:
            self.revision_entry.set_sensitive(True)
        else:
            self.revision_entry.set_text("")
            self.revision_entry.set_sensitive(False)

        # Only allow browsing if a URL is provided
        if self.get_url() == "":
            self.revision_browse.set_sensitive(False)
        else:
            self.revision_browse.set_sensitive(True)
    
    def get_url(self):
        if self.url_combobox:
            return self.url_combobox.get_active_text()
        elif self.url_entry:
            return self.url_entry.get_text()
        elif self.url:
            return self.url
        else:
            return ""

    def set_url(self, url):
        self.url = url

    def get_revision_object(self):
        """
        @rtype  rabbitvcs.lib.vcs.###.Revision
        @return A rabbitvcs revision object
        
        """
        index = self.revision_kind_opt.get_active()
        
        if index == 0:
            return self.client.revision("head")
        elif index == 1:
            return self.client.revision("number", self.revision_entry.get_text())
        elif index == 2:
            return self.client.revision("working")

    def set_kind_head(self):
        self.revision_kind_opt.set_active(0)
        self.determine_widget_sensitivity()

    def set_kind_number(self, number=None):
        self.revision_kind_opt.set_active(1)
        if number is not None:
            self.revision_entry.set_text(str(number))
        self.determine_widget_sensitivity()

    def set_kind_working(self):
        self.revision_kind_opt.set_active(2)
        self.determine_widget_sensitivity()

class FilesTable(Table):
    def __init__(self, treeview, coltypes, colnames, values=[], 
            base_dir=None, path_entries=[], callbacks={}):

        Table.__init__(self, treeview, coltypes, colnames, values, 
            base_dir, path_entries)
            
        self.callbacks = callbacks
        
        treeview.connect("cursor-changed", self.__cursor_changed_event)
        treeview.connect("row-activated", self.__row_activated_event)
        treeview.connect("button-press-event", self.__button_press_event)
        treeview.connect("button-release-event", self.__button_release_event)
        treeview.connect("key-press-event", self.__key_press_event)
        self.allow_multiple()
    
    def __button_press_event(self, treeview, data):
        # this allows us to retain multiple selections with a right-click
        if data.button == 3:
            selection = treeview.get_selection()
            (liststore, indexes) = selection.get_selected_rows()
            return (len(indexes) > 0)

    def __row_activated_event(self, treeview, data, col):
        if "row-activated" in self.callbacks:
            self.callbacks["row-activated"](treeview, data, col)
        
    def __key_press_event(self, treeview, data):
        if "key-event" in self.callbacks:
            self.callbacks["key-event"](treeview, data)

    def __cursor_changed_event(self, treeview):
        if "mouse-event" in self.callbacks:
            self.callbacks["mouse-event"](treeview)

    def __button_release_event(self, treeview, data):
        if "mouse-event" in self.callbacks:
            self.callbacks["mouse-event"](treeview, data)
