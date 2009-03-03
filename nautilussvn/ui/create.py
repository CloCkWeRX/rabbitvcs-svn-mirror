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

import os
import subprocess

import nautilussvn.ui.dialog

from nautilussvn import gettext
_ = gettext.gettext

class Create:
    """
    Provides an interface to create a vcs repository
    """
    
    # TODO: This class in massively Subversion-biased.  In the future, we'll
    # need to refactor to make it platform-agnostic
    
    # Also, might want to just launch a terminal window instead of this
    def __init__(self, path):
    
    
        if not os.path.isdir(path):
            os.makedirs(path)
        
        # Let svnadmin return a bad value if a repo already exists there
        ret = subprocess.call(["/usr/bin/svnadmin", "create", path])
        if ret == 0:
            nautilussvn.ui.dialog.MessageBox(_("Repository successfully created"))
        else:
            nautilussvn.ui.dialog.MessageBox(_("There was an error creating the repository.  Make sure the given folder is empty."))
        
if __name__ == "__main__":
    from os import getcwd
    from sys import argv
    
    args = argv[1:]
    path = getcwd()
    if args:
        if args[0] != ".":
            path = args[0]
            
    Create(path)
