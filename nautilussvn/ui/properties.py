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
import nautilussvn.ui.widget
import nautilussvn.ui.dialog
import nautilussvn.lib.vcs
from nautilussvn.lib.helper import setcwd

from nautilussvn import gettext
_ = gettext.gettext

class Properties(InterfaceView):
    """
    Provides an interface to add/edit/delete properties on versioned
    items in the working copy.
    
    """

    selected_row = None
    selected_rows = []

    def __init__(self, path):
        InterfaceView.__init__(self, "properties", "Properties")

        setcwd(path)

        self.path = path
        self.delete_stack = []
        
        self.get_widget("Properties").set_title(
            _("Properties - %s") % path
        )
        
        self.get_widget("path").set_text(path)
        
        self.table = nautilussvn.ui.widget.Table(
            self.get_widget("table"),
            [gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Name"), _("Value")]
        )
        self.table.allow_multiple()
        
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()
        self.proplist = self.vcs.proplist(path)
        
        for key,val in self.proplist.items():
            self.table.append([key,val.rstrip()])

    def on_destroy(self, widget):
        gtk.main_quit()

    def on_cancel_clicked(self, widget):
        gtk.main_quit()

    def on_ok_clicked(self, widget):
        self.save()
        gtk.main_quit()
    
    def save(self):
        for row in self.delete_stack:
            self.vcs.propdel(self.path, row[0])

        for row in self.table.get_items():
            self.vcs.propset(self.path, row[0], row[1], overwrite=True)
        
    def on_new_clicked(self, widget):
        dialog = nautilussvn.ui.dialog.Property()
        name,value = dialog.run()
        if name is not None:
            self.table.append([name,value])
    
    def on_edit_clicked(self, widget):
        (name,value) = self.get_selected_name_value()
        dialog = nautilussvn.ui.dialog.Property(name, value)
        name,value = dialog.run()
        if name is not None:
            self.set_selected_name_value(name, value)
    
    def on_delete_clicked(self, widget, data=None):
        if not self.selected_rows:
            return
            
        for i in self.selected_rows:
            row = self.table.get_row(i)
            self.delete_stack.append([row[0],row[1]])
            
        self.table.remove_multiple(self.selected_rows)
    
    def set_selected_name_value(self, name, value):
        self.table.set_row(self.selected_rows[0], [name,value])
        
    def get_selected_name_value(self):
        returner = None
        if self.selected_rows is not None:
            returner = self.table.get_row(self.selected_rows[0])
        return returner

    def on_table_cursor_changed(self, treeview, data=None):
        self.on_table_event(treeview)
    
    def on_table_button_released(self, treeview, data=None):
        self.on_table_event(treeview)
    
    def on_table_event(self, treeview):
        selection = treeview.get_selection()
        (liststore, indexes) = selection.get_selected_rows()
        self.selected_rows = []
        for tup in indexes:
            self.selected_rows.append(tup[0])

        length = len(self.selected_rows)
        if length == 0:
            self.get_widget("edit").set_sensitive(False)
            self.get_widget("delete").set_sensitive(False)
        elif length == 1:
            self.get_widget("edit").set_sensitive(True)
            self.get_widget("delete").set_sensitive(True)
        else:
            self.get_widget("edit").set_sensitive(False)
            self.get_widget("delete").set_sensitive(True)


if __name__ == "__main__":
    from os import getcwd
    from sys import argv
    
    args = argv[1:]
    path = getcwd()
    if args:
        if args[0] != ".":
            path = args[0]
            
    window = Properties(path)
    window.register_gtk_quit()
    gtk.main()
