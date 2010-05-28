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

from os import getcwd

import pygtk
import gobject
import gtk

from rabbitvcs.ui import InterfaceNonView
from rabbitvcs.ui.action import SVNAction
import rabbitvcs.vcs

from rabbitvcs import gettext
_ = gettext.gettext

class SVNIgnore(InterfaceNonView):
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
        @param  glob: True if the path to ignore is a wildcard "glob"
        
        """
        
        InterfaceNonView.__init__(self)
        self.path = path
        self.pattern = pattern
        self.glob = glob
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

    def start(self):
        prop = self.svn.PROPERTIES["ignore"]
        return self.svn.propset(self.path, prop, self.pattern, recurse=self.glob)

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNIgnore
}

def ignore_factory(path, pattern):
    guess = rabbitvcs.vcs.guess(path)
    return classes_map[guess["vcs"]](path, pattern)

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, args) = main(usage="Usage: rabbitvcs ignore <folder> <pattern>")
    
    path = getcwd()
    pattern = ""
    if args:
        if len(args) == 1:
            pattern = args[0]
        else:
            if args[0] != ".":
                path = args[0]
            if "1" in args:
                pattern = args[1]

    window = ignore_factory(path, pattern)
    window.start()
