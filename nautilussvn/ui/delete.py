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

from nautilussvn.ui import InterfaceNonView
from nautilussvn.ui.action import VCSAction
import nautilussvn.lib.vcs

from nautilussvn import gettext
_ = gettext.gettext

class Delete(InterfaceNonView):
    """
    This class provides a handler to Delete functionality.
    
    """

    def __init__(self, paths):
        InterfaceNonView.__init__(self)
        self.paths = paths
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()

    def start(self):
    
        # From the given paths, determine which are versioned and which are not
        versioned = []
        unversioned = []
        for path in self.paths:
            if self.vcs.is_versioned(path):
                versioned.append(path)
            elif os.path.exists(path):
                unversioned.append(path)
        
        # If there are unversioned files, confirm that the user wants to
        # delete those.  Default to true.
        result = True
        if unversioned:
            item = None
            if len(unversioned) == 1:
                item = unversioned[0]
            confirm = nautilussvn.ui.dialog.DeleteConfirmation(item)
            result = confirm.run()

        # If the user wants to continue (or there are no unversioned files)
        # remove or delete the given files
        if result:
            if versioned:
                try:
                    self.vcs.remove(versioned, force=True)
                except Exception, e:
                    print str(e)
                    return
            
            if unversioned:
                for path in unversioned:
                    nautilussvn.lib.helper.delete_item(path)
        
if __name__ == "__main__":
    from os import getcwd
    from sys import argv
    
    args = argv[1:]

    # Convert "." to current working directory
    paths = args
    i = 0
    for arg in args:
        paths[i] = arg
        if paths[i] == ".":
            paths[i] = getcwd()
        i += 1
   
    if not paths:
        paths = [getcwd()]

    window = Delete(paths)
    window.register_gtk_quit()
    window.start()
