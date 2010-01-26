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

import rabbitvcs.ui
import rabbitvcs.lib.vcs

class PropertyPage(rabbitvcs.ui.GladeWidgetWrapper):
    
    glade_filename = "property_page"
    glade_id = "property_page"
    
    def __init__(self, paths):
        rabbitvcs.ui.GladeWidgetWrapper.__init__(self)
        self.paths = paths
        self.vcs_client = rabbitvcs.lib.vcs.create_vcs_instance()
        self.get_widget("information").set_text("\n".join(paths))        
    

class PropertyPageLabel(rabbitvcs.ui.GladeWidgetWrapper):
    glade_filename = "property_page"
    glade_id = "property_page_label"    