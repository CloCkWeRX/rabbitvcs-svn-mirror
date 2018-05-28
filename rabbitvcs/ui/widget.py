from __future__ import absolute_import
import six
from six.moves import range
#
# This is an extension to the Nautilus file manager to allow better 
# integration with the Subversion source control system.
# 
# Copyright (C) 2006-2008 by Jason Field <jason@jasonfield.com>
# Copyright (C) 2007-2008 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2008-2010 by Adam Plumb <adamplumb@gmail.com>
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
    
import os
import os.path

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Pango
GTK_FILL = Gtk.AttachOptions.FILL
GTK_EXPAND = Gtk.AttachOptions.EXPAND
GTK3 = True
PANGO_ELLIPSIZE_MIDDLE = Pango.EllipsizeMode.MIDDLE
PANGO_ELLIPSIZE_END = Pango.EllipsizeMode.END
HAS_PANGO = True

HAS_GTKSPELL = False
try:
    gi.require_version('GtkSpell', '3.0')
    from gi.repository import GtkSpell
    HAS_GTKSPELL = True
except ImportError:
    pass    

HAS_GTKSOURCEVIEW = False
try:
    gi.require_version('GtkSource', '3.0')
    from gi.repository import GtkSource
    HAS_GTKSOURCEVIEW = True
except ImportError:
    pass

import rabbitvcs.util.helper

from rabbitvcs import gettext
_ = gettext.gettext

from rabbitvcs.util.log import Log
log = Log("rabbitvcs.ui.widget")

from rabbitvcs.ui import STATUS_EMBLEMS

TOGGLE_BUTTON = 'TOGGLE_BUTTON'
TYPE_PATH = 'TYPE_PATH'
TYPE_STATUS = 'TYPE_STATUS'
TYPE_ELLIPSIZED = 'TYPE_ELLIPSIZED'
TYPE_GRAPH = 'TYPE_GRAPH'
TYPE_MARKUP = 'TYPE_MARKUP'
TYPE_HIDDEN = 'TYPE_HIDDEN'

ELLIPSIZE_COLUMN_CHARS = 20

PATH_ENTRY = 'PATH_ENTRY'
SEPARATOR = u'\u2015' * 10

from pprint import pformat
def filter_router(model, iter, column, filters):
    """
    Route filter requests for a table's columns.  This function is called for
    each cell of the table that gets displayed.
    
    @type   model: Gtk.TreeModelFilter or Gtk.TreeModelSort
    @param  model: The TreeModelFilter or Gtk.TreeModelSort instance for our
                   table
    
    @type   iter: Gtk.TreeIter
    @param  iter: The TreeIter instance for the table row being filtered
    
    @type   column: int
    @param  column: The column index of the current item being filtered
    
    @type   filters: list
    @param  filters: A list of dicts used to define how a column should be
        filtered
        
        Note for filters:  Each dict consists of a callback function and user
        data like so:
        
            {
                "callback": self.file_filter,
                "user_data": {
                    "column": 0, //tells the callback what column to filter
                    "base_dir": "/home/workingcopy"
                }
            }
    
    @return    The filtered output defined for the given column
    
    """
    real_model = model.get_model()
    
    real_iter = model.convert_iter_to_child_iter(iter)
    
    row = real_model[real_model.get_path(real_iter)]

    if not filters:
        return row[column]

    for filter in filters:
        filter_column = filter["user_data"]["column"]
        if column == filter_column:
            return filter["callback"](row, column, filter["user_data"])

    return row[column]

def path_filter(row, column, user_data=None):
    """
    A common filter function that is used in many tables.  Changes the displayed
    path to a path relative to the given base_dir (current working directory)
    
    @type   row: Gtk.TreeModelRow
    @param  row: The row that is being filtered
    
    @type   column: int
    @param  column: The column that is being filtered
    
    @type   user_data: dict
    @param  user_data: A dictionary of user_data useful to this function
    
    @rtype  str
    @return A relative path
    
    """
    base_dir = user_data["base_dir"]

    if row[column]:
        relpath = rabbitvcs.util.helper.get_relative_path(base_dir, row[column])
        if relpath == "":
            relpath = os.path.basename(row[column])
        return relpath
    else:
        return row[column] 

def long_text_filter(row, column, user_data=None):
    """
    Uses the format_long_text helper function to trim and prettify some text.
    """
    text = row[column]
    
    cols = user_data["cols"]
    
    
    if text:
        text = rabbitvcs.util.helper.format_long_text(text, cols)
        
    return text

def git_revision_filter(row, column, user_data=None):
    """
    Only show the first six characters of a git revision hash
    """
    
    text = row[column]
    if text:
        if text.startswith("<b>"):
            text = text[3:10]
        else:
            text = text[0:7]

    return text

def translate_filter(row, column, user_data=None):
    """
    Translates text as needed.
    """
    text = row[column]
    if text: return _(text)
    
def compare_items(model, iter1, iter2, user_data=None):

    if not user_data:
        # No column data given => Give up
        return 0

    colnum, coltype = user_data
    
    real_model = model.get_model()
    real_iter1 = model.convert_iter_to_child_iter(iter1)
    real_iter2 = model.convert_iter_to_child_iter(iter2)
    
    value1 = real_model.get_value(real_iter1, colnum)
    value2 = real_model.get_value(real_iter2, colnum)
    
    if value1 == value2:
        return 0
    elif value1 < value2:
        return -1
    else:
        return 1
    
class TableBase:
    def __init__(self, treeview, coltypes, colnames, values=[], filters=None,
                 filter_types=None, callbacks={}, flags={}):
        """
        @type   treeview: Gtk.Treeview
        @param  treeview: The treeview widget to use
        
        @type   coltypes: list
        @param  coltypes: Contains the "type" of each column (i.e. str or int)
        
        @type   colnames: list
        @param  colnames: Contains the name string for each column
        
        @type   values: list
        @param  values: Contains the data to be inserted into the table
        
        @type   filters: list
        @param  filters: A list of dicts used to define how a column should be
            filtered
            
            Note for filters:  Each dict consists of a callback function and user
            data like so:
            
                {
                    "callback": self.file_filter,
                    "user_data": {
                        "column": 0, //tells the callback what column to filter
                        "base_dir": "/home/workingcopy"
                    }
                }
        
        @type   filter_types: list
        @param  filter_types: Contains the filtered "type" of each column.
        
        @type   callbacks: dict
        @param  callbacks: A dict of callbacks to be used.  Some are for signal
            handling while others are useful for other things.
            
        @type   flags: dict
        @param  flags: A dict of flags
        
        FLAGS:
            @type   sortable: boolean
            @param  sortable: whether the columns can be sorted
            
            @type   sort_on: int
            @param  sort_on: the column number to initially sort by
            
            @type   editable: list
            @param  editable: A list of which columns are editable
        
        """
        
        from .renderers.graphcell import CellRendererGraph

        if "sortable" not in flags:
            flags["sortable"] = False
        if "sort_on" not in flags:
            flags["sort_on"] = -1
        if "editable" not in flags:
            flags["editable"] = ()
    
        self.treeview = treeview
        self.selected_rows = []

        # When True, will cause update_selection to reapply the existing content of selected_rows,
        #   rather than the other way around, then set it to False again.
        self._reassert_selection = False
        i = 0
        for name in colnames:
            if coltypes[i] == GObject.TYPE_BOOLEAN:
                cell = Gtk.CellRendererToggle()
                cell.set_property('activatable', True)
                cell.set_property('xalign', 0)
                cell.connect("toggled", self.toggled_cb, i)
                
                colname = ""
                if name != TOGGLE_BUTTON:
                    colname = name
                
                col = Gtk.TreeViewColumn(colname, cell)
                col.set_attributes(cell, active=i)
            elif coltypes[i] == TYPE_PATH:
                # The type should be str but we have to use TYPE_PATH to
                # distinguish from a regular str column
                coltypes[i] = str
                
                # First we create the column, then we create a CellRenderer 
                # instance for the path icon and a CellRenderer instance for
                # the path.  Each is packed into the treeview column
                col = Gtk.TreeViewColumn(name)

                cellpb = Gtk.CellRendererPixbuf()
                cellpb.set_property('xalign', 0)
                cellpb.set_property('yalign', 0)
                col.pack_start(cellpb, False)
                data = None
                if "file-column-callback" in callbacks:
                    data = {
                        "callback": callbacks["file-column-callback"],
                        "column": i
                    }
                else:
                    data = {
                        "callback": rabbitvcs.util.helper.get_node_kind,
                        "column": i
                    }
                col.set_cell_data_func(cellpb, self.file_pixbuf, data)
                
                cell = Gtk.CellRendererText()
                cell.set_property('xalign', 0)
                cell.set_property('yalign', 0)
                col.pack_start(cell, False)
                col.set_attributes(cell, text=i)
            elif coltypes[i] == TYPE_STATUS:
                # Same as for TYPE_PATH
                coltypes[i] = str                
                col = Gtk.TreeViewColumn(name)
                
                cellpb = Gtk.CellRendererPixbuf()
                cellpb.set_property('xalign', 0)
                cellpb.set_property('yalign', 0)
                
                col.pack_start(cellpb, False)
                
                data = None
                
                col.set_cell_data_func(cellpb, self.status_pixbuf, i)
                
                cell = Gtk.CellRendererText()
                cell.set_property('xalign', 0)
                cell.set_property('yalign', 0)
                col.pack_start(cell, False)
                col.set_attributes(cell, text=i)
            elif coltypes[i] == TYPE_HIDDEN:
                coltypes[i] = str
                col = Gtk.TreeViewColumn(name, cell)
                col.set_visible(False)
            elif coltypes[i] == TYPE_ELLIPSIZED:
                coltypes[i] = str
                cell = Gtk.CellRendererText()
                cell.set_property('yalign', 0)
                cell.set_property('xalign', 0)
                if HAS_PANGO:
                    cell.set_property('ellipsize', PANGO_ELLIPSIZE_END)
                    cell.set_property('width-chars', ELLIPSIZE_COLUMN_CHARS)
                col = Gtk.TreeViewColumn(name, cell)
                col.set_attributes(cell, text=i)
            elif coltypes[i] == TYPE_GRAPH:
                coltypes[i] = GObject.TYPE_PYOBJECT
                cell = CellRendererGraph()
                col = Gtk.TreeViewColumn(name, cell)
                col.add_attribute(cell, "graph", i)
            else:
                cell = Gtk.CellRendererText()
                cell.set_property('yalign', 0)
                cell.set_property('xalign', 0)
                if i in flags["editable"]:
                    cell.set_property('editable', True)
                    cell.connect("edited", self.__cell_edited, i)
                
                if coltypes[i] == TYPE_MARKUP:
                    col = Gtk.TreeViewColumn(name, cell, markup=i)
                else:
                    col = Gtk.TreeViewColumn(name, cell, text=i)

                coltypes[i] = GObject.TYPE_STRING

            if flags["sortable"]:
                col.set_sort_column_id(i)

            self.treeview.append_column(col)
            i += 1

        self.data = self.get_store(coltypes)

        self.sorted = None

        # self.sorted == sorted view of data
        # self.filter == filtered data (abs paths -> rel paths)
        # self.data == actual data

        # The filter is there to change the way data is displayed. The data
        # should always be accessed via self.data, NOT self.filter.
        self.filter = self.data.filter_new()
        types = (filter_types and filter_types or coltypes)
        self.filter.set_modify_func(
                        types,
                        filter_router,
                        filters)


		# This runs through the columns, and sets the "compare_items" comparator
        # as needed. Note that the user data tells which column to sort on.
        if flags["sortable"]:
            self.sorted = Gtk.TreeModelSort(self.filter)
            
            self.sorted.set_default_sort_func(compare_items, None)
            
            for idx in range(0, i):
                self.sorted.set_sort_func(idx,
                                          compare_items,
                                          (idx, coltypes[idx]))

            self.sorted.set_sort_column_id(flags["sort_on"], Gtk.SortType.ASCENDING)
            
            self.treeview.set_model(self.sorted)
            
        elif filters:
            self.treeview.set_model(self.filter)
        else:
            self.treeview.set_model(self.data)

        
        if len(values) > 0:
            self.populate(values)
    
        self.set_resizable()

        # Set up some callbacks for all tables to deal with row clicking and
        # selctions
        self.treeview.connect("cursor-changed", self.__cursor_changed_event)
        self.treeview.connect("row-activated", self.__row_activated_event)
        self.treeview.connect("button-press-event", self.__button_press_event)
        self.treeview.connect("button-release-event", self.__button_release_event)
        self.treeview.connect("key-press-event", self.__key_press_event)
        self.treeview.connect("select-cursor-row", self.__row_selected)
        # Necessary for self.selected_rows to remain sane
        self.treeview.connect("select-all", self.__all_selected)
        self.treeview.connect("unselect-all", self.__all_unselected)

        self.callbacks = callbacks
        if self.callbacks:
            self.allow_multiple()

    def _sortedpath(self, real_path):
        """
        Converts a model index (as stored in selected_rows) into a user selection
        path
        """
        if self.sorted:
            path = self.sorted.convert_child_path_to_path(real_path)
        else:
            path = self.filter.convert_child_path_to_path(real_path)
        return path


    def _realpath(self, visible_path):
        """
        Converts a path (ie. row number) that we get from what the user selects
        into a path for the underlying data structure. If the data is not
        sorted, this is trivial; if it is sorted, the sorting model can figure
        it out for us.
        """
        if self.sorted:
            path = self.sorted.convert_path_to_child_path(visible_path)
        else:
            path = self.filter.convert_path_to_child_path(visible_path)
        return path

    def toggled_cb(self, cell, path, column):
        model = self.data
        realpath = self._realpath(path)
        # User has clicked a checkbox on a selected item.
        toggleMulti = realpath[0] in self.selected_rows and len(self.selected_rows) > 1
        model[realpath][column] = not model[realpath][column]
        if "row-toggled" in self.callbacks:
            self.callbacks["row-toggled"](model[realpath], column)

        # Set the state of _all_ selected items to match the new state of the checkbox
        if toggleMulti:
            sel = self.treeview.get_selection()
            for selPath in self.selected_rows:
                model[selPath][column] = model[realpath][column]
                if "row-toggled" in self.callbacks:
                    self.callbacks["row-toggled"](model[selPath], column)
            self._reassert_selection = True

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
        self.reset_selection()
        
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
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

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

    def get_column(self, column):
        return self.treeview.get_column(column)

    def set_column_width(self, column, width=None):
        col = self.treeview.get_column(column)
        if width is not None:
            col.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            col.set_fixed_width(width)
        else:
            col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)

    def update_selection(self):
        selection = self.treeview.get_selection()
        # Will be set if a checkmark is changed while multiple rows
        # selected; user retains their selection after using
        # the new multicheck feature.
        if not self._reassert_selection:
            (liststore, indexes) = selection.get_selected_rows()

            self.reset_selection()

            for tup in indexes:
                self.selected_rows.append(self._realpath(tup)[0])

        else:
            self._reassert_selection = False

            for tup in self.selected_rows:
                path = self._sortedpath(tup);
                selection.select_range(path, path)

    def reset_selection(self):
        self.selected_rows = []

    def get_selected_row_items(self, col):
        items = []
        for row in self.selected_rows:
            items.append(self.data[row][col])
        
        return items

    def get_selected_rows(self):
        return self.selected_rows
        
    def generate_string_from_data(self):
        lines = []
        for row in self.data:
            line = []
            for cell in row:
                line.append(six.text_type(cell))
            lines.append("\t".join(line))
        
        return "\n".join(lines)
        
    def unselect_all(self):
        self.treeview.get_selection().unselect_all()

    def focus(self, row, column):
        treecol = self.treeview.get_column(column)
        self.treeview.set_cursor((row,), treecol)
        self.treeview.grab_focus()

    def __button_press_event(self, treeview, data):
        info = treeview.get_path_at_pos(int(data.x), int(data.y))
        selection = treeview.get_selection()
        
        # If info is none, that means the user is clicking the empty space
        # In that case, unselect everything and update the selected_rows
        if info is None:
            selection.unselect_all()
            self.update_selection()
            return
            
        # this allows us to retain multiple selections with a right-click
        if data.button == 3:
            (liststore, indexes) = selection.get_selected_rows()
            
            # If the mouse click is one of the currently selected rows
            # keep the selection, otherwise, use the new selection
            for index in indexes:
                if index[0] == info[0][0]:
                    return True
            return False

    def __row_activated_event(self, treeview, data, col):
        treeview.grab_focus()
        self.update_selection()
        if "row-activated" in self.callbacks:
            self.callbacks["row-activated"](treeview, data, col)
    
    def __row_selected(self, treeview, started_editing):
        self.update_selection()
        if "row-selected" in self.callbacks:
            self.callbacks["row-selected"](treeview, started_editing)

    # Without these in place, Ctrl+A / Shift+Ctrl+A were not updating
    # self.selected_rows
    def __all_selected(self, treeview):
        treeview.get_selection().select_all()
        self.update_selection()
        if "all-selected" in self.callbacks:
            self.callbacks["all-selected"](treeview, started_editing)

    def __all_unselected(self, treeview):
        treeview.get_selection().unselect_all()
        self.update_selection()
        if "all-unselected" in self.callbacks:
            self.callbacks["all-unselected"](treeview, started_editing)
        
    def __key_press_event(self, treeview, data):
        self.update_selection()
        if "key-event" in self.callbacks:
            self.callbacks["key-event"](treeview, data)

    def __cursor_changed_event(self, treeview):
        self.update_selection()
        if "cursor-changed" in self.callbacks:
            self.callbacks["cursor-changed"](treeview)
        if "mouse-event" in self.callbacks:
            self.callbacks["mouse-event"](treeview)

    def __button_release_event(self, treeview, data):
        self.update_selection()
        if "mouse-event" in self.callbacks:
            self.callbacks["mouse-event"](treeview, data)

    def __cell_edited(self, cell, row, data, column):
        self.update_selection()
        if "cell-edited" in self.callbacks:
            self.callbacks["cell-edited"](cell, row, data, column)

#    def __column_header_clicked(self, column, column_idx):
#        self.data.set_sort_column_id(column_idx, )

    def status_pixbuf(self, column, cell, model, iter, colnum):
        
        path = model.get_path(iter)
    
        real_path = model.convert_path_to_child_path(path)
        
        status = self.data[real_path][colnum]
        
        if status not in list(STATUS_EMBLEMS.keys()):
            status = "error"
             
        icon = "emblem-" + STATUS_EMBLEMS[status]
        
        cell.set_property("icon_name", icon)
        

    def file_pixbuf(self, column, cell, model, iter, data=None):
        stock_id = None
        
        path = model.get_path(iter)
    
        real_path = model.convert_path_to_child_path(path)
            
        if data:
            real_item = self.data[real_path][data["column"]]
            kind = data["callback"](real_item)
            stock_id = Gtk.STOCK_FILE
            if kind == "dir":
                stock_id = Gtk.STOCK_DIRECTORY

        if stock_id is not None:
            cell.set_property("stock_id", stock_id)

class Table(TableBase):
    """
    Generate a flat tree view.
        
    See the TableBase documentation for parameter information

    """
    
    def __init__(self, treeview, coltypes, colnames, values=[], filters=None, 
            filter_types=None, callbacks={}, flags={}):
        TableBase.__init__(self, treeview, coltypes, colnames, values, filters, 
            filter_types, callbacks, flags)
    
    def get_store(self, coltypes):
        return Gtk.ListStore(*coltypes)

    def populate(self, values):
        for row in values:
            self.data.append(row)

class Tree(TableBase):
    """
    Generate a hierarchal tree view.  The structure of "values" should be like:

        values = [
            (["A"], [
                (["C"], None)
            ]),
            (["B"], [
                (["D"], [
                    (["E"], None)
                ])
            ])
        ]
        
        Note that with multiple columns, you add to the list in the first element
        of each tuple.  (i.e. ["A"] becomes ["A", "Z", ... ]
        
    See the TableBase documentation for parameter information

    """
    def __init__(self, treeview, coltypes, colnames, values=[], filters=None, 
            filter_types=None, callbacks={}, flags={}):
        TableBase.__init__(self, treeview, coltypes, colnames, values, filters, 
            filter_types, callbacks, flags={})
    
    def get_store(self, coltypes):
        return Gtk.TreeStore(*coltypes)

    def populate(self, values, parent=None):
        for node in values:
            root = node[0]
            new_root = self.data.append(parent, root)
            if len(node) > 1 and node[1] is not None:
                self.populate(node[1], new_root)
        
class ComboBox:
    def __init__(self, cb, items=None):
    
        self.cb = cb
    
        self.model = Gtk.ListStore(str)
        if items is not None:
            for i in items:
                self.append(i)

        self.cb.set_model(self.model)
        self.cb.set_entry_text_column(0)

        cell = Gtk.CellRendererText()
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
        active = self.cb.get_active_iter()
        return self.model[active][0]
    
    def get_active(self):
        return self.cb.get_active()
    
    def set_active(self, index):
        self.cb.set_active(index)
    
    def set_child_text(self, text):
        self.cb.child.set_text(text)
    
    def set_sensitive(self, val):
        self.cb.set_sensitive(val)

    def set_child_signal(self, signal, callback, userdata=None):
        self.cb.child.connect(signal, callback, userdata)
        
class TextView:
    def __init__(self, widget=None, value="", spellcheck=True):
        if widget is None:
            self.view = Gtk.TextView()
        else:
            self.view = widget
        self.buffer = Gtk.TextBuffer()
        self.view.set_buffer(self.buffer)
        self.buffer.set_text(value)
        
        if HAS_GTKSPELL and spellcheck:
            try:
                GtkSpell.Checker().attach(self.view)
            except Exception as e:
                log.exception(e)
        
    def get_text(self):
        return self.buffer.get_text(
            self.buffer.get_start_iter(), 
            self.buffer.get_end_iter(),
            True
        )
        
    def set_text(self, text):
        self.buffer.set_text(text)

    def append_text(self, text):
        self.buffer.set_text(self.get_text() + text)

class SourceView(TextView):
    def __init__(self, widget=None, value=""):
        if HAS_GTKSOURCEVIEW:
            if widget is None:
                self.view = GtkSourceView.SourceView(self.buffer)
            else:
                self.view = widget
            self.buffer = GtkSourceView.SourceBuffer()
            self.buffer.set_text(value)

            if HAS_GTKSPELL:
                GtkSpell.Spell(self.view)

            self.view.show()
        else:
            TextView.__init__(self, widget, value)

class ProgressBar:
    def __init__(self, pbar):
        if pbar is None:
            self.view = Gtk.ProgressBar()
        else:
            self.view = pbar
        
        self.timer = None
        
    def start_pulsate(self):
        # Set up an interval to make the progress bar pulse
        # The timeout is removed after the log action finishes
        self.timer = GObject.timeout_add(100, self.update)
    
    def stop_pulsate(self):
        if self.timer:
            GObject.source_remove(self.timer)
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

    def __init__(self, container, client, revision=None, 
            url_combobox=None, url_entry=None, url=None, expand=False,
            revision_changed_callback=None):
        """
        @type   container: A Gtk container object (i.e. HBox, VBox, Box)
        @param  container: The container that to add this widget
        
        @type   client: VCS client object
        @param  client: A vcs client instance (i.e. rabbitvcs.vcs.VCS())
        
        @type   revision: int
        @param  revision: A revision number to start with
        
        @type   url_combobox: rabbitvcs.ui.widget.ComboBox
        @param  url_combobox: A repository url combobox

        @type   url_entry: Gtk.Entry
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
        self.revision_changed_callback = revision_changed_callback
        self.revision_change_inprogress = False
        hbox = Gtk.HBox(0, 4)
        
        if self.url_combobox:
            self.url_combobox.cb.connect("changed", self.__on_url_combobox_changed)

        if client.vcs == rabbitvcs.vcs.VCS_GIT:
            self.OPTIONS = [
                _("HEAD"),
                _("Revision"),
                _("Branch")
            ]
        elif client.vcs == rabbitvcs.vcs.VCS_SVN:
            self.OPTIONS = [
                _("HEAD"),
                _("Number")
            ]
            if not client.is_path_repository_url(self.get_url()):
                self.OPTIONS.append(_("Working Copy"))
        
        self.revision_kind_opt = ComboBox(Gtk.ComboBox(), self.OPTIONS)
        self.revision_kind_opt.set_active(0)
        self.revision_kind_opt.cb.connect("changed", self.__revision_kind_changed)
        hbox.pack_start(self.revision_kind_opt.cb, False, False, 0)
        
        self.revision_entry = Gtk.Entry()
        self.revision_entry.connect("changed", self.__revision_entry_changed)
        hbox.pack_start(self.revision_entry, expand, expand, 0)
        
        self.branch_selector = None
        if client.vcs == rabbitvcs.vcs.VCS_GIT:
            self.branch_selector = GitBranchSelector(hbox, client, self.__branch_selector_changed)
            self.branch_selector.hide()
        
        
        self.revision_browse = Gtk.Button()
        revision_browse_image = Gtk.Image()
        revision_browse_image.set_from_stock(Gtk.STOCK_FIND, 1)
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
        from rabbitvcs.ui.log import SVNLogDialog, GitLogDialog
        if self.client.vcs == rabbitvcs.vcs.VCS_GIT:
            GitLogDialog(self.get_url(), ok_callback=self.__log_closed)
        elif self.client.vcs == rabbitvcs.vcs.VCS_SVN:
            SVNLogDialog(self.get_url(), ok_callback=self.__log_closed)
    
    def __log_closed(self, data):
        if data is not None:
            self.revision_kind_opt.set_active(1)
            self.revision_entry.set_text(data)

    def __revision_kind_changed(self, widget):
        self.determine_widget_sensitivity()
        
        if self.revision_changed_callback:
            self.revision_change_inprogress = True
            GObject.timeout_add(400, self.__revision_changed_callback, self)

    def __revision_entry_changed(self, widget):
        if self.revision_changed_callback and not self.revision_change_inprogress:
            self.revision_change_inprogress = True
            GObject.timeout_add(400, self.__revision_changed_callback, self)

    def __revision_changed_callback(self, *args, **kwargs):
        self.revision_change_inprogress = False
        self.revision_changed_callback(*args, **kwargs)

    def __on_url_combobox_changed(self, widget):
        self.determine_widget_sensitivity()

    def determine_widget_sensitivity(self):
        index = self.revision_kind_opt.get_active()
        
        allow_revision_browse = True

        # Default to showing the revision entry
        self.hide_branch_selector()
        
        # Only allow number entry if "Number" is selected
        if index == 1:
            self.revision_entry.set_sensitive(True)
        elif index == 2:
            if self.client.vcs == rabbitvcs.vcs.VCS_GIT:
                self.revision_entry.set_sensitive(True)
                allow_revision_browse = False

                # If showing the "Branch" option, show the branch selector
                self.show_branch_selector()
        else:
            self.revision_entry.set_text("")
            self.revision_entry.set_sensitive(False)

        # Only allow browsing if a URL is provided
        if self.get_url() and allow_revision_browse:
            self.revision_browse.set_sensitive(True)
        else:
            self.revision_browse.set_sensitive(False)
    
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
        @rtype  rabbitvcs.vcs.###.Revision
        @return A rabbitvcs revision object
        
        index=0     HEAD
        index=1     Revision Number
        index=2
            SVN     Working Copy
            Git     Branch Selector
        
        """
        index = self.revision_kind_opt.get_active()
        
        if index == 0:
            return self.client.revision("head")
        elif index == 1:
            if self.client.vcs == rabbitvcs.vcs.VCS_SVN:
                return self.client.revision("number", self.revision_entry.get_text())
            elif self.client.vcs == rabbitvcs.vcs.VCS_GIT:
                return self.client.revision(self.revision_entry.get_text())
        elif index == 2:
            if self.client.vcs == rabbitvcs.vcs.VCS_SVN:
                return self.client.revision("working")
            elif self.client.vcs == rabbitvcs.vcs.VCS_GIT:
                return self.client.revision(self.branch_selector.get_branch())

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

    def show_branch_selector(self):
        if self.branch_selector:
            self.revision_entry.hide()
            self.revision_browse.hide()
            self.branch_selector.show()

    def hide_branch_selector(self):
        if self.branch_selector:
            self.branch_selector.hide()
            self.revision_entry.show()
            self.revision_browse.show()

    def __branch_selector_changed(self, branch):
        self.__revision_entry_changed(self.revision_entry)

class KeyValueTable(Gtk.Table):
    """
    Simple extension of a GTK table to display a two-column table of information
    with labels.
    """
    
    default_col_spacing = 12
    default_row_spacing = 6
        
    def __init__(self, stuff):
        """
        @param stuff: a list of two-element tuples - the first element of the
                      tuple is the key/label, and the second element is the
                      information
        """
        if not stuff or len(stuff) == 0:
            super(KeyValueTable, self).__init__()
        else:
            super(KeyValueTable, self).__init__(len(stuff), 2)
            
            row = 0
            
            for key, value in stuff:
                label_key = Gtk.Label("<b>%s:</b>" % key)
                label_key.set_properties(xalign=0, use_markup=True)
                
                label_value = Gtk.Label("%s" % value)
                if HAS_PANGO:
                    label_value.set_properties(xalign=0,                    \
                                           ellipsize=PANGO_ELLIPSIZE_MIDDLE, \
                                           selectable=True)
                else:
                    label_value.set_properties(xalign=0,selectable=True)
                    
                self.attach(label_key,
                             0,1,
                             row, row+1,
                             xoptions=GTK_FILL)
    
                self.attach(label_value,
                             1,2,
                             row, row+1,
                             xoptions=GTK_FILL|GTK_EXPAND)
                        
                label_key.show()
                label_value.show()
                
                row += 1
        
        self.set_col_spacings(self.default_col_spacing)
        self.set_row_spacings(self.default_row_spacing)

class GitRepositorySelector:
    def __init__(self, container, git, changed_callback=None):
        self.git = git
        self.changed_callback = changed_callback
        
        vbox = Gtk.VBox(False, 4)
        
        # Set up the Repository Line
        label = Gtk.Label(_("Repository:"))
        label.set_size_request(90, -1)
        label.set_justify(Gtk.Justification.LEFT)

        tmp_repos = []
        for item in self.git.remote_list():
            tmp_repos.append(item["name"])
        self.repository_opt = ComboBox(Gtk.ComboBox.new_with_entry(), tmp_repos)
        self.repository_opt.set_active(0)
        self.repository_opt.cb.connect("changed", self.__repository_changed)
        self.repository_opt.cb.set_size_request(175, -1)
        
        hbox = Gtk.HBox(False, 0)
        hbox.pack_start(label, False, False, 0)
        hbox.pack_start(self.repository_opt.cb, False, False, 0)
        vbox.pack_start(hbox, False, False, 0)


        # Set up the Branch line
        label = Gtk.Label(_("Branch:"))
        label.set_size_request(90, -1)
        label.set_justify(Gtk.Justification.LEFT)

        tmp_branches = []
        active_branch_index = 0
        index = 0
        for item in self.git.branch_list():
            tmp_branches.append(item.name)
            
            if item.tracking:
                active_branch_index = index
            
            index += 1
            
        self.branch_opt = ComboBox(Gtk.ComboBox.new_with_entry(), tmp_branches)
        self.branch_opt.set_active(active_branch_index)
        self.branch_opt.cb.connect("changed", self.__branch_changed)
        self.branch_opt.cb.set_size_request(175, -1)
        
        hbox = Gtk.HBox(False, 0)
        hbox.pack_start(label, False, False, 0)
        hbox.pack_start(self.branch_opt.cb, False, False, 0)
        vbox.pack_start(hbox, False, False, 0)
        
        # Set up the Host line
        label = Gtk.Label(_("Host:"))
        label.set_justify(Gtk.Justification.LEFT)
        label.set_size_request(90, -1)
        self.host = Gtk.Label()
        self.host.set_justify(Gtk.Justification.LEFT)
        hbox = Gtk.HBox(False, 0)
        hbox.pack_start(label, False, False, 0)
        hbox.pack_start(self.host, False, False, 0)
        vbox.pack_start(hbox, False, False, 4)

        vbox.show_all()
        container.add(vbox)
        
        self.__update_host()
    
    def __update_host(self):
        repo = self.repository_opt.get_active_text()
        try:
            self.host.set_text(self.git.config_get(("remote", repo), "url").decode("utf-8"))
        except KeyError as e:
            log.error("Missing remote %s config key" % repo)
    
    def __repository_changed(self, repository_opt):
        if self.changed_callback:
            self.changed_callback(repository_opt.get_active_text(), self.branch_opt.get_active_text())
        self.__update_host()
   
    def __branch_changed(self, branch_opt):
        if self.changed_callback:
            self.changed_callback(self.repository_opt.get_active_text(), self.branch_opt.get_active_text())

class GitBranchSelector:
    def __init__(self, container, git, changed_callback=None):
        self.git = git
        self.changed_callback = changed_callback
        
        self.vbox = Gtk.VBox(False, 4)

        tmp_branches = []
        active = 0
        index = 0
        for item in self.git.branch_list():
            tmp_branches.append(item.name)
            if self.git.is_tracking(item.name):
                active = index
            index += 1

        self.branch_opt = ComboBox(Gtk.ComboBox.new_with_entry(), tmp_branches)
        self.branch_opt.set_active(active)
        self.branch_opt.cb.connect("changed", self.__branch_changed)
        self.branch_opt.cb.set_size_request(175, -1)

        hbox = Gtk.HBox(False, 0)
        hbox.pack_start(self.branch_opt.cb, False, False, 0)
        self.vbox.pack_start(hbox, False, False, 0)
        
        self.vbox.show_all()
        container.add(self.vbox)

    def append(self, widget):
        self.vbox.pack_start(widget, False, False, 0)

    def get_branch(self):
        return self.branch_opt.get_active_text()

    def __branch_changed(self, branch_opt):
        pass
    
    def show(self):
        self.vbox.show_all()
    
    def hide(self):
        self.vbox.hide()

class MultiFileTextEditor:
    """
    Edit a set of text/config/ignore files
    """
    
    def __init__(self, container, label, combobox_labels, combobox_paths, show_add_line=True, line_content=""):
        self.container = container
        self.label = label
        self.combobox_labels = combobox_labels
        self.combobox_paths = combobox_paths
        
        self.cache = {}
        
        self.last_path = None
                
        self.combobox = ComboBox(Gtk.ComboBox(), self.combobox_labels)
        self.combobox.cb.connect("changed", self.__combobox_changed)
        self.combobox.cb.set_size_request(175, -1)
        
        self.textview = TextView(Gtk.TextView())

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_shadow_type(Gtk.SHADOW_ETCHED_IN)
        scrolled_window.add(self.textview.view)
        scrolled_window.set_policy(Gtk.POLICY_AUTOMATIC, Gtk.POLICY_AUTOMATIC)
        scrolled_window.set_size_request(320, 150)
        
        vbox = Gtk.VBox(False, 6)
        
        hbox = Gtk.HBox(False, 3)
        combo_label = Gtk.Label(label)
        combo_label.set_alignment(0, 0.5)
        combo_label.set_size_request(130, -1)
        hbox.pack_start(combo_label, False, False, 0)
        hbox.pack_start(self.combobox.cb, True, True, 0)
        vbox.pack_start(hbox, False, False, 0)
        
        if show_add_line:
            hbox = Gtk.HBox(False, 3)
            add_label = Gtk.Label(_("Add line:"))
            add_label.set_alignment(0, 0.5)
            add_label.set_size_request(130, -1)
            self.add_entry = Gtk.Entry()
            self.add_entry.set_text(line_content)
            add_button = Gtk.Button(_("Add"))
            add_button.connect("clicked", self.__add_button_clicked)
            hbox.pack_start(add_label, False, False, 0)
            hbox.pack_start(self.add_entry, True, True, 0)
            hbox.pack_start(add_button, False, False, 0)
            vbox.pack_start(hbox, False, False, 0)
        
        vbox.pack_start(scrolled_window, True, True, 0)
        vbox.show_all()

        self.combobox.set_active(0)

        container.add(vbox)
        
    def __combobox_changed(self, widget):
        index = self.combobox.get_active()
        path = self.combobox_paths[index]

        if not self.last_path:
            self.last_path = path
        
        self.cache[self.last_path] = self.textview.get_text()
        self.last_path = path
        
        self.load_file(path)
    
    def __add_button_clicked(self, widget):
        text = self.add_entry.get_text()
        self.add_line(text)
        self.add_entry.set_text("")
    
    def add_line(self, text):
        current_text = self.textview.get_text()
        if current_text:
            current_text += "\n" + text
        else:
            current_text = text
        
        self.textview.set_text(current_text)
    
    def load_file(self, path):
        if os.path.exists(path):
            fh = open(path, "r")
            self.textview.set_text(fh.read())
            fh.close()
        else:
            self.textview.set_text("")

    def save(self, path=None):
        if path:
            paths = [path]
        else:
            paths = self.combobox_paths

        index = self.combobox.get_active()
        current_path = self.combobox_paths[index]
        self.cache[current_path] = self.textview.get_text()
        
        for tmppath in paths:
            if tmppath in self.cache:
                if not os.path.exists(os.path.dirname(tmppath)):
                    os.mkdir(os.path.dirname(tmppath))

                fh = open(tmppath, "w")
                fh.write(self.cache[tmppath])
                fh.close()
