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

import os.path
from rabbitvcs import gettext
_ = gettext.gettext

EXT_UTIL_ERROR = _("The output from '%s' was not able to be processed.\n%s")

def create_vcs_instance(path=None, vcs=None):
    """
    Create a VCS instance based on the working copy path
    """

    # Determine the VCS instance based on the vcs parameter
    if vcs:
        if vcs == "svn":
            from rabbitvcs.vcs.svn import SVN
            return SVN()
        elif vcs == "git":
            from rabbitvcs.vcs.git import Git
            git = Git()
            if path:
                repo_path = git.find_repository_path(path)
                git.set_repository(repo_path)
            
            return git

    # Determine the VCS instance based on the path
    if path:
        path_to_check = os.path.realpath(path)
        while path_to_check != "/" and path_to_check != "":
            if os.path.isdir(os.path.join(path_to_check, ".svn")):
                from rabbitvcs.vcs.svn import SVN
                return SVN()
            elif os.path.isdir(os.path.join(path_to_check, ".git")):
                from rabbitvcs.vcs.git import Git
                return Git(path_to_check)
                
            path_to_check = os.path.split(path_to_check)[0]

    from rabbitvcs.vcs.svn import SVN
    return SVN()

class ExternalUtilError(Exception):
    """ Represents an error caused by unexpected output from an external
    program.
    """ 
        
    def __init__(self, program, output):
        """ Initialises the error with the external tool and the unexpected
        output.
        """
        Exception.__init__(self,
                           EXT_UTIL_ERROR % (program, output))
        self.program = program
        self.output = output
