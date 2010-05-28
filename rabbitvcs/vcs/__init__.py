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

from rabbitvcs.util.log import Log
log = Log("rabbitvcs.vcs")

EXT_UTIL_ERROR = _("The output from '%s' was not able to be processed.\n%s")

VCS_SVN = 'svn'
VCS_GIT = 'git'
VCS_DUMMY = 'Unknown'

def guess(path):
    # Determine the VCS instance based on the path
    if path:
        path_to_check = os.path.realpath(path)
        while path_to_check != "/" and path_to_check != "":
            if os.path.isdir(os.path.join(path_to_check, ".svn")):
                cache = {
                    "vcs": VCS_SVN,
                    "repo_path": path_to_check
                }
                return cache

            elif os.path.isdir(os.path.join(path_to_check, ".git")):
                cache = {
                    "vcs": VCS_GIT,
                    "repo_path": path_to_check
                }
                return cache
                
            path_to_check = os.path.split(path_to_check)[0]
            
    return {
        "vcs": VCS_DUMMY,
        "repo_path": path
    }

class VCS:
    clients = {}
    path_vcs_map = {}
    
    def __init__(self):
        pass
    
    def dummy(self):
        if VCS_DUMMY in self.clients:
            return self.clients[VCS_DUMMY]
        else:
            from rabbitvcs.vcs.dummy import Dummy
            self.clients[VCS_DUMMY] = Dummy()
            return self.clients[VCS_DUMMY]
    
    def svn(self):
        if VCS_SVN in self.clients:
            return self.clients[VCS_SVN]
        else:
            try:
                from rabbitvcs.vcs.svn import SVN
                self.clients[VCS_SVN] = SVN()
                return self.clients[VCS_SVN]
            except Exception, e:
                log.debug("Unable to load SVN module: %s" % e)
                self.clients[VCS_SVN] = self.dummy()
                return self.clients[VCS_SVN]

    def git(self, path=None, is_repo_path=False):
        if VCS_GIT in self.clients:
            git = self.clients[VCS_GIT]

            if path:
                if is_repo_path:
                    git.set_repository(path)
                else:
                    repo_path = git.find_repository_path(path)
                    git.set_repository(repo_path)

            return git
        else:
            try:
                from rabbitvcs.vcs.git import Git
                git = Git()

                if path:
                    if is_repo_path:
                        git.set_repository(path)
                    else:
                        repo_path = git.find_repository_path(path)
                        git.set_repository(repo_path)
                
                self.clients[VCS_GIT] = git
                return self.clients[VCS_GIT]
            except Exception, e:
                log.debug("Unable to load Git module: %s" % e)
                self.clients[VCS_GIT] = self.dummy()
                return self.clients[VCS_GIT]

    def client(self, path, vcs=None):
        # Determine the VCS instance based on the vcs parameter
        if vcs:
            if vcs == VCS_SVN:
                return self.svn()
            elif vcs == VCS_GIT:
                return self.git(path)

        guess = self.guess(path)
        if guess["vcs"] == VCS_GIT:
            return self.git(guess["repo_path"], is_repo_path=False)
        else:
            return self.svn()
    
    def guess(self, path):
        if path and path in self.path_vcs_map:
            return self.path_vcs_map[path]

        choice = guess(path)
        self.path_vcs_map[path] = choice
        return choice
    
    # Methods that call client methods

    def statuses(self, path, recurse=True):
        client = self.client(path)
        return client.statuses(path, recurse)
    
    def status(self, path, summarize=True):
        client = self.client(path)
        return client.status(path, summarize)

    def is_working_copy(self, path):
        client = self.client(path)
        return client.is_working_copy(path)

    def is_in_a_or_a_working_copy(self, path):
        client = self.client(path)
        ret = client.is_in_a_or_a_working_copy(path)
        return ret

    def is_versioned(self, path):
        client = self.client(path)
        return client.is_versioned(path)
    
    def is_locked(self, path):
        client = self.client(path)
        return client.is_locked(path)

    def get_items(self, paths, statuses=[]):
        client = self.client(paths[0])
        return client.get_items(paths, statuses)

    def statuses_for_commit(self, paths):
        client = self.client(paths[0])
        return client.STATUSES_FOR_COMMIT

    def statuses_for_revert(self, paths):
        client = self.client(paths[0])
        return client.STATUSES_FOR_REVERT

def create_vcs_instance(path=None, vcs=None):
    """
    Create a VCS instance based on the working copy path
    """
    return VCS()

def guess_vcs(path):
    vcs = VCS()
    return vcs.guess(path)

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
