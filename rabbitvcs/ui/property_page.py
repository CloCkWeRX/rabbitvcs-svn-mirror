#
# This is an extension to the Nautilus file manager to allow better 
# integration with the Subversion source control system.
# 
# Copyright (C) 2010 by Jason Heeris <jason.heeris@gmail.com>
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

import gtk

import rabbitvcs.ui
import rabbitvcs.lib.vcs
from rabbitvcs.services.checkerservice import StatusCheckerStub as StatusChecker
from rabbitvcs.ui import STATUS_EMBLEMS
from rabbitvcs.util.vcs import make_single_status

from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.ui.property_page")

class PropertyPage(rabbitvcs.ui.GladeWidgetWrapper):
    
    glade_filename = "property_page"
    glade_id = "property_page"
    
    def __init__(self, paths, vcs = None):
        rabbitvcs.ui.GladeWidgetWrapper.__init__(self)
        self.paths = paths
        self.vcs_client = vcs or rabbitvcs.lib.vcs.create_vcs_instance()
        
        self.info_pane = self.get_widget("property_page") 
        
        if len(paths) == 1:
            file_info = FileInfoPane(paths[0], self.vcs_client)
            self.info_pane.pack_start(file_info.get_widget(),
                                      expand=False,
                                      fill=True)
        
    
class FileInfoPane(rabbitvcs.ui.GladeWidgetWrapper):

    glade_filename = "property_page"
    glade_id = "file_info_table"
    
    def __init__(self, path, vcs = None):
        rabbitvcs.ui.GladeWidgetWrapper.__init__(self)
        
        self.vcs = vcs or rabbitvcs.lib.vcs.create_vcs_instance()
        self.checker = StatusChecker() 
               
        self.get_widget("file_name").set_text(os.path.basename(path))
        
        #FIXME: I'm not sure where this should actually come from
        vcstype = "none"
        if self.vcs.is_in_a_or_a_working_copy(path):
            vcstype = "subversion"
        
        self.get_widget("vcs_type").set_text(vcstype)
        
        self.get_widget("remote_url").set_text(self.vcs.get_repo_url(path))

        status = self.checker.check_status(path,
                                       recurse = False, 
                                       invalidate = False,
                                       summary = False)

        single_status = make_single_status(status[path])        
        text_status = status[path]["text_status"]
        prop_status = status[path]["prop_status"]
        
        self.get_widget("content_status").set_text(text_status)
        self.get_widget("prop_status").set_text(prop_status)
        

        self.set_icon_from_status(self.get_widget("content_status_icon"),
                                                  text_status)

        self.set_icon_from_status(self.get_widget("prop_status_icon"),
                                                  prop_status)

        self.set_icon_from_status(self.get_widget("vcs_icon"),
                                  single_status, gtk.ICON_SIZE_DIALOG)
        
    def set_icon_from_status(self, icon, status, size=gtk.ICON_SIZE_BUTTON):
        if status in STATUS_EMBLEMS:
            icon.set_from_icon_name("emblem-" + STATUS_EMBLEMS[status], size)

class PropertyPageLabel(rabbitvcs.ui.GladeWidgetWrapper):
    glade_filename = "property_page"
    glade_id = "property_page_label"    