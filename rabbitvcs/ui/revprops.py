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

from rabbitvcs.ui.properties import PropertiesBase
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.lib.vcs
from rabbitvcs.lib.log import Log

log = Log("rabbitvcs.ui.revprops")

from rabbitvcs import gettext
_ = gettext.gettext

class SVNRevisionProperties(PropertiesBase):
    def __init__(self, path, revision=None):
        PropertiesBase.__init__(self, path)
        
        self.revision = revision
        self.revision_obj = None
        if self.revision_obj is not None:
            self.revision_obj = self.vcs.revision("number", revision)

        self.load()

    def load(self):
        self.table.clear()
        try:
            self.proplist = self.vcs.revproplist(
                self.get_widget("path").get_text(),
                self.revision_obj
            )
        except Exception, e:
            log.exception(e)
            rabbitvcs.ui.dialog.MessageBox(_("Unable to retrieve properties list"))
            self.proplist = {}
        
        if self.proplist:
            for key,val in self.proplist.items():
                self.table.append([False, key,val.rstrip()])

    def save(self):
        delete_recurse = self.get_widget("delete_recurse").get_active()
        
        for row in self.delete_stack:
            self.vcs.revpropdel(self.path, row[1], self.revision_obj, force=True)

        for row in self.table.get_items():
            result = self.vcs.revpropset(row[1], row[2], self.path,
                             self.revision_obj, force=True)
            
            if result != True:
                msg = _("Error setting property: ") + row[1] + "\n\n" + str(result)
                rabbitvcs.ui.dialog.MessageBox(msg)

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main()
    
    window = SVNRevisionProperties(paths[0])
    window.register_gtk_quit()
    gtk.main()
