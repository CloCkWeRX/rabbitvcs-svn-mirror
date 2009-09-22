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

import os.path

import pygtk
import gobject
import gtk
import os
import commands

from nautilussvn.ui import InterfaceNonView
from nautilussvn.ui.action import VCSAction
import nautilussvn.lib.vcs
from nautilussvn.lib.log import Log

log = Log("nautilussvn.ui.applypatch")

from nautilussvn import gettext
_ = gettext.gettext

class ApplyPatch(InterfaceNonView):
    """
    This class provides a handler to the apply patch functionality.
    
    """

    def __init__(self, paths):
        InterfaceNonView.__init__(self)
        self.paths = paths
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()
        self.common = nautilussvn.lib.helper.get_common_directory(paths)

    def choose_patch_path(self):
        path = None
        
        dialog = gtk.FileChooserDialog(
            _("Apply Patch"),
            None,
            gtk.FILE_CHOOSER_ACTION_OPEN,(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                          gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            path = dialog.get_filename()
        
        dialog.destroy()
        
        return path
    
    def choose_patch_dir(self):
        dir = None
        
        dialog = gtk.FileChooserDialog(
                    _("Apply Patch To Directory..."),
                    None,
                    gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                     gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        
        response = dialog.run()
        
        if response == gtk.RESPONSE_OK:
            dir = dialog.get_filename()
            
        dialog.destroy()
        
        return dir
    
    def start(self):
    
        path = self.choose_patch_path()
        # If empty path, means we've cancelled
        if not path:
            return
        
        base_dir = self.choose_patch_dir()
        if not base_dir:
            return        
        
        ticks = 2
        self.action = nautilussvn.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.set_pbar_ticks(ticks)
        self.action.append(self.action.set_header, _("Apply Patch"))
        self.action.append(self.action.set_status, _("Applying Patch File..."))
        self.action.append(self.vcs.apply_patch, path, base_dir)
        self.action.append(self.action.set_status, _("Patch File Applied"))
        self.action.append(self.action.finish)
        self.action.start()
    
if __name__ == "__main__":
    from nautilussvn.ui import main
    (options, paths) = main()

    window = ApplyPatch(paths)
    window.register_gtk_quit()
    window.start()
    gtk.main()
    
