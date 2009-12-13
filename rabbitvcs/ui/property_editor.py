#
# This is an extension to the Nautilus file manager to allow better 
# integration with the Subversion source control system.
# 
# Copyright (C) 2009 by Jason Heeris <jason.heeris@gmail.com>
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

"""
A note to anyone intending to work on this in the future... This dialog is
designed to be as stateless as possible. That is, all the information about
properties being changed, deleted, added, etc. should be kept in the SVN admin
system, not in this dialog. SVN should be keeping track of this info, not us!

To this effect, changes are applied immediately... no saving lists of changes to
apply later, no trying to keep track of what was done recursively and what
wasn't; just do the work and make sure the UI is sensible.
"""

import os.path

import pygtk
import gobject
import gtk
import gnomevfs

from rabbitvcs.ui import InterfaceView
from rabbitvcs.lib.contextmenu import GtkContextMenuCaller
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.lib.vcs
from rabbitvcs.lib.helper import format_text_with_linebreaks
from rabbitvcs.lib.vcs.svn import Revision
from rabbitvcs.lib.log import Log

log = Log("rabbitvcs.ui.property_editor")

from rabbitvcs import gettext
_ = gettext.gettext


def wrapped_label_size_allocate_callback(gtklabel, allocation):
    # gtklabel.set_size_request(allocation.width, -1)
    pass
    
class PropEditor(InterfaceView, GtkContextMenuCaller):
    '''
    User interface for the property editor.
    
    The UI is basically an "instant update" editor, that is as soon as you add a
    property in the dialog, it is actually added in the WC. Each row has a
    context menu available to perform other actions.
    '''


    def __init__(self, path):
        '''
        Initialises the UI.
        '''
        InterfaceView.__init__(self, "propedit", "Properties")
        
        self.path = path
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        
        self.get_widget("wc_text").set_text(gnomevfs.get_uri_from_local_path(os.path.realpath(path)))
        self.get_widget("remote_uri_text").set_text(self.vcs.get_repo_url(path))
        
        self.get_widget("apply_note").connect("size-allocate", wrapped_label_size_allocate_callback)
        
        self.table = rabbitvcs.ui.widget.Table(
            self.get_widget("table"),
            [gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Name"), _("Value"), _("Reserved"), _("Status")]
        )
        self.table.allow_multiple()
        
        self.load_properties()
        
        print "Property editor for %s" % path
    
    def load_properties(self):
        self.table.clear()
        
        try:
            local_props = self.vcs.proplist(self.path)
            base_props = self.vcs.proplist(self.path, rev=Revision("base").primitive())
                        
        except Exception, e:
            print e
            log.exception(e)
            rabbitvcs.ui.dialog.MessageBox(_("Unable to retrieve properties list"))
            self.proplist = []
        
        local_propnames = set(local_props.keys())
        base_propnames = set(base_props.keys())
                
        for propname in (local_propnames | base_propnames):
            
            if propname in (local_propnames & base_propnames):
                
                if local_props[propname] == base_props[propname]:
                    self.table.append([propname,
                                       format_text_with_linebreaks(local_props[propname]),
                                       "N/A",
                                       "unchanged"])
                
                else:
                    self.table.append([propname,
                                       format_text_with_linebreaks(local_props[propname]),
                                       "N/A",
                                       "value changed"])
            
            elif propname in local_propnames:
                self.table.append([propname,
                                   format_text_with_linebreaks(local_props[propname]),
                                   "N/A",
                                   "property added"])
            
            elif propname in base_propnames:
                self.table.append([propname,
                                   format_text_with_linebreaks(base_props[propname]),
                                   "N/A",
                                   "property deleted"])

    def on_destroy(self, widget):
        self.close()
        
    def on_close_clicked(self, widget):
        """
        Simply closes the dialog. No confirmation is needed, since changes to
        properties are performed instantly.
        """
        self.close()

    def on_refresh_clicked(self, widget):
        self.load_properties()

    def on_new_clicked(self, widget):
        dialog = rabbitvcs.ui.dialog.Property()
        name,value,recurse = dialog.run()
        
        if name:
            print "Added %s: %s (%s)" % (name, value, recurse)

    def on_edit_clicked(self, widget):
        (recurse,name,value) = self.get_selected_name_value()
        dialog = rabbitvcs.ui.dialog.Property(name, value)
        name,value,recurse = dialog.run()
        if name:
            print "Edited %s: %s (%s)" % (name, value, recurse)


if __name__ == "__main__":
    # These are some dumb tests before I add any functionality.
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs propedit [url_or_path]")
    
    paths = ["/home/jason/Software/svntest/svntest/one.txt"]
    
    window = PropEditor(paths[0])
    window.register_gtk_quit()
    gtk.main()
