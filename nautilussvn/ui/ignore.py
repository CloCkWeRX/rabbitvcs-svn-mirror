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

from nautilussvn.ui import InterfaceNonView
from nautilussvn.ui.action import VCSAction
import nautilussvn.lib.vcs

from nautilussvn import gettext
_ = gettext.gettext

class Ignore(InterfaceNonView):
    """
    This class provides a handler to Ignore functionality.
    
    """

    def __init__(self, path, pattern, glob=False):
        """
        @type   path: string
        @param  path: The path to apply the ignore keyword to
        
        @type   pattern: string
        @param  pattern: Ignore items with the given pattern
        
        @type   glob: boolean
        @param  glob: True iff the path to ignore is a wildcard "glob"
        
        """
        
        InterfaceNonView.__init__(self)
        self.path = path
        self.pattern = pattern
        self.vcs = nautilussvn.lib.vcs.create_vcs_instance()

    def start(self):
        prop = self.vcs.PROPERTIES["ignore"]
        return self.vcs.propset(self.path, prop, self.pattern, recurse=glob)
        
if __name__ == "__main__":
    from os import getcwd
    from sys import argv
    
    args = argv[1:]
    path = getcwd()
    pattern = ""
    if args:
        if args[0] != ".":
            path = args[0]
        if "1" in args:
            pattern = args[1]
            
    window = Ignore(path, pattern)
    window.register_gtk_quit()
    window.start()
