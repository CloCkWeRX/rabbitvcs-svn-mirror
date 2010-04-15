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

"""
Concrete VCS implementation for Git functionality.
"""

import os.path

from gittyup.client import GittyupClient
import gittyup.objects

from rabbitvcs.util.helper import abspaths

import rabbitvcs.vcs
import rabbitvcs.vcs.status
from rabbitvcs.util.log import Log

log = Log("rabbitvcs.vcs.git")

from rabbitvcs import gettext
_ = gettext.gettext

class Git:
    STATUS = {
        "normal":       gittyup.objects.NormalStatus,
        "added":        gittyup.objects.AddedStatus,
        "renamed":      gittyup.objects.RenamedStatus,
        "removed":      gittyup.objects.RemovedStatus,
        "modified":     gittyup.objects.ModifiedStatus,
        "killed":       gittyup.objects.KilledStatus,
        "untracked":    gittyup.objects.UntrackedStatus,
        "missing":      gittyup.objects.MissingStatus
    }
    
    STATUS_REVERSE = {
        gittyup.objects.NormalStatus:       "normal",
        gittyup.objects.AddedStatus:        "added",
        gittyup.objects.RenamedStatus:      "renamed",
        gittyup.objects.RemovedStatus:      "removed",
        gittyup.objects.ModifiedStatus:     "modified",
        gittyup.objects.KilledStatus:       "killed",
        gittyup.objects.UntrackedStatus:    "untracked",
        gittyup.objects.MissingStatus:      "missing"
    }

    STATUSES_FOR_COMMIT = [
        STATUS["untracked"],
        STATUS["missing"]
    ]

    def __init__(self, repo=None):
        self.vcs = "git"
        self.interface = "gittyup"
        if repo:
            self.client = GittyupClient(repo)
        else:
            self.client = GittyupClient()
    
    def set_repository(self, path):
        self.client.set_repository(path)

    def get_repository(self):
        return self.client.get_repository(path)

    def find_repository_path(self, path):
        return self.client.find_repository_path(path)
    
    #
    # Status Methods
    #
    
    def statuses(self, path):
        """
        Generates a list of GittyupStatus objects for the specified file.
        
        @type   path: string
        @param  path: The file to look up.  If the file is a directory, it will
            return a recursive list of child path statuses
        
        """

        gittyup_statuses = self.client.status(path)

        if not len(gittyup_statuses):
            return [rabbitvcs.vcs.status.Status.status_unknown(path)]
        else:
            statuses = []
            for st in gittyup_statuses:
                # gittyup returns status paths relative to the repository root
                # so we need to convert the path to an absolute path
                st.path = self.client.get_absolute_path(st.path)
                statuses.append(rabbitvcs.vcs.status.GitStatus(st))
            return statuses
    
    def status(self, path, summarize=True):

        all_statuses = self.statuses(path)

        if summarize:
            path_status = (st for st in all_statuses if st.path == path).next()
            path_status.make_summary(all_statuses)
        else:
            path_status = all_statuses[0]

        return path_status
    
    def is_working_copy(self, path):
        if (os.path.isdir(path) and
                os.path.isdir(os.path.join(path, ".git"))):
            return True
        return False

    def is_in_a_or_a_working_copy(self, path):
        if self.is_working_copy(path):
            return True

        return (self.find_repository_path(os.path.split(path)[0]) != "")

    def is_versioned(self, path):
        if self.is_working_copy(path):
            return True
        else:
            st = self.client.status(path)
            try:
                if (st[0].path == self.client.get_absolute_path(path) and
                        st[0].identifier != "untracked"):
                    return True
            except Exception:
                return False

            return False

    def is_locked(self, path):
        return False

    def get_items(self, paths, statuses=[]):
        """
        Retrieves a list of files that have one of a set of statuses
        
        @type   paths:      list
        @param  paths:      A list of paths or files.
        
        @type   statuses:   list
        @param  statuses:   A list of statuses.
        
        @rtype:             list
        @return:            A list of GittyupStatus objects.
        
        """

        if paths is None:
            return []
        
        items = []
        st = self.status()
        for path in abspaths(paths):
            for st_item in st:
                if statuses and st_item not in statuses:
                    continue

                items.append(st_item)

        return items

    #
    # Action Methods
    #
    
    def stage(self, paths):
        """
        Stage files to be committed or tracked
        
        @type   paths: list
        @param  paths: A list of files
        
        """
        
        return self.client.stage(paths)
    
    def stage_all(self):
        """
        Stage all files in a repository to be committed or tracked
        
        """
        
        return self.client.stage_all()
    
    def unstage(self, paths):
        """
        Unstage files so they are not committed or tracked
        
        @type   paths: list
        @param  paths: A list of files
        
        """
        
        return self.client.unstage(paths)
    
    def unstage_all(self):
        """
        Unstage all files so they are not committed or tracked
        
        @type   paths: list
        @param  paths: A list of files
        
        """
        
        return self.client.unstage_all()
    
    def branch(self, name, commit_sha=None, track=False):
        """
        Create a new branch
        
        @type   name: string
        @param  name: The name of the new branch
        
        @type   commit_sha: string
        @param  commit_sha: A commit sha to branch from.  If None, branches
                    from head
        
        @type   track: boolean
        @param  track: Whether or not to track the new branch, or just create it
        
        """
        
        return self.client.branch(name, commit_sha, track)
    
    def branch_delete(self, name):
        """
        Delete a branch
        
        @type   name: string
        @param  name: The name of the branch
        
        """
        
        return self.client.branch_delete(name)
        
    def branch_rename(self, old_name, new_name):
        """
        Rename a branch

        @type   old_name: string
        @param  old_name: The name of the branch to be renamed

        @type   new_name: string
        @param  new_name: The name of the new branch

        """

        return self.client.branch_rename(old_name, new_name)
        
    def branch_list(self):
        """
        List all branches
        
        """
        
        return self.client.branch_list()
        
    def checkout(self, paths=[], tree_sha=None, commit_sha=None):
        """
        Checkout a series of paths from a tree or commit.  If no tree or commit
        information is given, it will check out the files from head.  If no
        paths are given, all files will be checked out from head.
        
        @type   paths: list
        @param  paths: A list of files to checkout
        
        @type   tree_sha: string
        @param  tree_sha: The sha of a tree to checkout

        @type   commit_sha: string
        @param  commit_sha: The sha of a commit to checkout

        """
        
        return self.client.checkout(paths, tree_sha, commit_sha)
        
    def clone(self, host, path, bare=False, origin="origin"):
        """
        Clone a repository
        
        @type   host: string
        @param  host: The url of the git repository
        
        @type   path: string
        @param  path: The path to clone to
        
        @type   bare: boolean
        @param  bare: Create a bare repository or not
        
        @type   origin: string
        @param  origin: Specify the origin of the repository

        """
        
        return self.client.clone(host, path, bare, origin)
        
    def commit(self, message, parents=None, committer=None, commit_time=None, 
            commit_timezone=None, author=None, author_time=None, 
            author_timezone=None, encoding=None, commit_all=False):
        """
        Commit staged files to the local repository
        
        @type   message: string
        @param  message: The log message
        
        @type   parents: list
        @param  parents: A list of parent SHAs.  Defaults to head.
        
        @type   committer: string
        @param  committer: The person committing.  Defaults to 
            "user.name <user.email>"
        
        @type   commit_time: int
        @param  commit_time: The commit time.  Defaults to time.time()
        
        @type   commit_timezone: int
        @param  commit_timezone: The commit timezone.  
            Defaults to (-1 * time.timezone)
        
        @type   author: string
        @param  author: The author of the file changes.  Defaults to 
            "user.name <user.email>"
            
        @type   author_time: int
        @param  author_time: The author time.  Defaults to time.time()
        
        @type   author_timezone: int
        @param  author_timezone: The author timezone.  
            Defaults to (-1 * time.timezone)
        
        @type   encoding: string
        @param  encoding: The encoding of the commit.  Defaults to UTF-8.
        
        @type   commit_all: boolean
        @param  commit_all: Stage all changed files before committing
        
        """
        
        return self.client.commit(message, parents, committer, commit_time,
            commit_timezone, author, author_time, author_timezone, encoding,
            commit_all)

    def remove(self, paths):
        """
        Remove path from the repository.  Also deletes the local file.
        
        @type   paths: list
        @param  paths: A list of paths to remove
        
        """
        
        return self.client.remove(paths)
    
    def move(self, source, dest):
        """
        Move a file within the repository
        
        @type   source: string
        @param  source: The source file
        
        @type   dest: string
        @param  dest: The destination.  If dest exists as a directory, source
            will be added as a child.  Otherwise, source will be renamed to
            dest.
            
        """
        
        return self.client.move(source, dest)
        
    def pull(self, repository="origin", refspec="master"):
        """
        Fetch objects from a remote repository and merge with the local 
            repository
            
        @type   repository: string
        @param  repository: The name of the repository
        
        @type   refspec: string
        @param  refspec: The branch name to pull from
        
        """
        
        return self.client.pull(self, repository, refspec)

    def push(self, repository="origin", refspec="master"):
        """
        Push objects from the local repository into the remote repository
            and merge them.
            
        @type   repository: string
        @param  repository: The name of the repository
        
        @type   refspec: string
        @param  refspec: The branch name to pull from
        
        """

        return self.client.push(self, repository, refspec)

    def fetch(self, host):
        """
        Fetch objects from a remote repository.  This will not merge the files
        into the local working copy, use pull for that.
        
        @type   host: string
        @param  host: The git url from which to fetch
        
        """
        
        return self.client.fetch(host)

    def remote_add(self, host, origin="origin"):
        """
        Add a remote repository
        
        @type   host: string
        @param  host: The git url to add
        
        @type   origin: string
        @param  origin: The name to give to the remote repository
        
        """
        
        return self.client.remote_add(host, origin)
        
    def remote_delete(self, origin="origin"):
        """
        Remove a remote repository
        
        @type   origin: string
        @param  origin: The name of the remote repository to remove

        """
        
        return self.client.remote_delete(origin)
        
    def remote_list(self):
        """
        Return a list of the remote repositories
        
        @rtype  list
        @return A list of dicts with keys: remote, url, fetch
            
        """
        
        return self.client.remote_list()
        
    def tag(self, name, message, tagger=None, tag_time=None, tag_timezone=None,
            tag_object=None, track=False):
        """
        Create a tag object
        
        @type   name: string
        @param  name: The name to give the tag
        
        @type   message: string
        @param  message: A log message
        
        @type   tagger: string
        @param  tagger: The person tagging.  Defaults to 
            "user.name <user.email>"
        
        @type   tag_time: int
        @param  tag_time: The tag time.  Defaults to time.time()
        
        @type   tag_timezone: int
        @param  tag_timezone: The tag timezone.  
            Defaults to (-1 * time.timezone)
        
        @type   tag_object: string
        @param  tag_object: The object to tag.  Defaults to HEAD
        
        @type   track: boolean
        @param  track: Whether or not to track the tag
        
        """
        
        return self.client.tag(name, message, tagger, tag_time, tag_timezone,
                tag_object, track)

    def tag_delete(self, name):
        """
        Delete a tag
        
        @type   name: string
        @param  name: The name of the tag to delete
        
        """
        
        return self.client.tag_delete(name)

    def tag_list(self):
        """
        Return a list of Tag objects
        
        """
        
        return self.client.tag_list()


    def log(self):
        """
        Returns a revision history list
        
        """
        
        return self.client.log()
