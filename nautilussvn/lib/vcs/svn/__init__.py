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

"""

Concrete VCS implementation for Subversion functionality.

"""

import traceback
import os.path
from os.path import isdir, isfile, dirname

import pysvn

from nautilussvn.lib.helper import abspaths
from nautilussvn.lib.decorators import timeit
from nautilussvn.lib.log import Log

log = Log("nautilussvn.lib.vcs.svn")

from nautilussvn import gettext
_ = gettext.gettext

class SVN:
    """
    
    """
    
    STATUS = {
        "none"          : pysvn.wc_status_kind.none,
        "unversioned"   : pysvn.wc_status_kind.unversioned,
        "normal"        : pysvn.wc_status_kind.normal,
        "added"         : pysvn.wc_status_kind.added,
        "missing"       : pysvn.wc_status_kind.missing,
        "deleted"       : pysvn.wc_status_kind.deleted,
        "replaced"      : pysvn.wc_status_kind.replaced,
        "modified"      : pysvn.wc_status_kind.modified,
        "merged"        : pysvn.wc_status_kind.merged,
        "conflicted"    : pysvn.wc_status_kind.conflicted,
        "ignored"       : pysvn.wc_status_kind.ignored,
        "obstructed"    : pysvn.wc_status_kind.obstructed,
        "external"      : pysvn.wc_status_kind.external,
        "incomplete"    : pysvn.wc_status_kind.incomplete
    }
    
    STATUS_REVERSE = {
        pysvn.wc_status_kind.none:          "none",
        pysvn.wc_status_kind.unversioned:   "unversioned",
        pysvn.wc_status_kind.normal:        "normal",
        pysvn.wc_status_kind.added:         "added",
        pysvn.wc_status_kind.missing:       "missing",
        pysvn.wc_status_kind.deleted:       "deleted",
        pysvn.wc_status_kind.replaced:      "replaced",
        pysvn.wc_status_kind.modified:      "modified",
        pysvn.wc_status_kind.merged:        "merged",
        pysvn.wc_status_kind.conflicted:    "conflicted",
        pysvn.wc_status_kind.ignored:       "ignored",
        pysvn.wc_status_kind.obstructed:    "obstructed",
        pysvn.wc_status_kind.external:      "external",
        pysvn.wc_status_kind.incomplete:    "incomplete"
    }

    STATUSES_FOR_COMMIT = [
        STATUS["unversioned"],
        STATUS["added"],
        STATUS["deleted"],
        STATUS["replaced"],
        STATUS["modified"],
        STATUS["missing"],
        STATUS["obstructed"]
    ]

    STATUSES_FOR_REVERT = [
        STATUS["missing"],
        STATUS["added"],
        STATUS["modified"],
        STATUS["deleted"]
    ]

    PROPERTIES = {
        "executable":   "svn:executable",
        "mime-type":    "svn:mime-type",
        "ignore":       "svn:ignore",
        "keywords":     "svn:keywords",
        "eol-style":    "svn:eol-style",
        "externals":    "svn:externals",
        "special":      "svn:special"
    }
    
    NOTIFY_ACTIONS = {
        pysvn.wc_notify_action.add:                     _("Added"),
        pysvn.wc_notify_action.copy:                    _("Copied"),
        pysvn.wc_notify_action.delete:                  _("Deleted"),
        pysvn.wc_notify_action.restore:                 _("Restored"),
        pysvn.wc_notify_action.revert:                  _("Reverted"),
        pysvn.wc_notify_action.failed_revert:           _("Failed Revert"),
        pysvn.wc_notify_action.resolved:                _("Resolved"),
        pysvn.wc_notify_action.skip:                    _("Skipped"),
        pysvn.wc_notify_action.update_delete:           _("Deleted"),
        pysvn.wc_notify_action.update_add:              _("Added"),
        pysvn.wc_notify_action.update_update:           _("Updated"),
        pysvn.wc_notify_action.update_completed:        _("Completed"),
        pysvn.wc_notify_action.update_external:         _("External"),
        pysvn.wc_notify_action.status_completed:        _("Completed"),
        pysvn.wc_notify_action.status_external:         _("External"),
        pysvn.wc_notify_action.commit_modified:         _("Modified"),
        pysvn.wc_notify_action.commit_added:            _("Added"),
        pysvn.wc_notify_action.commit_deleted:          _("Copied"),
        pysvn.wc_notify_action.commit_replaced:         _("Replaced"),
        pysvn.wc_notify_action.commit_postfix_txdelta:  _("Changed"),
        pysvn.wc_notify_action.annotate_revision:       _("Annotated"),
        pysvn.wc_notify_action.locked:                  _("Locked"),
        pysvn.wc_notify_action.unlocked:                _("Unlocked"),
        pysvn.wc_notify_action.failed_lock:             _("Failed Lock"),
        pysvn.wc_notify_action.failed_unlock:           _("Failed Unlock")
    }
    
    NOTIFY_ACTIONS_COMPLETE = [
        pysvn.wc_notify_action.status_completed,
        pysvn.wc_notify_action.update_completed        
    ]
    
    NOTIFY_STATES = {
        pysvn.wc_notify_state.inapplicable:             _("Inapplicable"),
        pysvn.wc_notify_state.unknown:                  _("Unknown"),
        pysvn.wc_notify_state.unchanged:                _("Unchanged"),
        pysvn.wc_notify_state.missing:                  _("Missing"),
        pysvn.wc_notify_state.obstructed:               _("Obstructed"),
        pysvn.wc_notify_state.changed:                  _("Changed"),
        pysvn.wc_notify_state.merged:                   _("Merged"),
        pysvn.wc_notify_state.conflicted:               _("Conflicted")
    }
    
    REVISIONS = {
        "unspecified":      pysvn.opt_revision_kind.unspecified,
        "number":           pysvn.opt_revision_kind.number,
        "date":             pysvn.opt_revision_kind.date,
        "committed":        pysvn.opt_revision_kind.committed,
        "previous":         pysvn.opt_revision_kind.previous,
        "working":          pysvn.opt_revision_kind.working,
        "head":             pysvn.opt_revision_kind.head
    }
    
    DEPTHS_FOR_CHECKOUT = { 
        "Recursive": True, 
        "Not Recursive": False 
    }
        
    #: This variable is used to maintain a status cache. Paths function as keys
    #: and every item in the cache has all the statuses for all the items below
    #: it, though the last item is always the status for the path. 
    #: 
    #: It might look like:::
    #:  
    #:     status_cache = {
    #:        "/foo/bar/baz": [<PysvnStatus u'baz'>]
    #:        "/foo/bar": [<PysvnStatus u'baz'>, <PysvnStatus u'bar'>, ]
    #:        "/foo": [<PysvnStatus u'foo'>, <PysvnStatus u'bar'>, <PysvnStatus u'baz'>]
    #:     }
    #:
    #: It is shared over all instances. Don't ask me why though, I don't 
    #: understand how it works myself.
    #:
    status_cache = {}
    
    def __init__(self):
        self.client = pysvn.Client()
        self.interface = "pysvn"
    
    def status(self, path, recurse=True):
        """
        
        Look up the status for path.
        
        """
        
        try:
            return self.client.status(path, recurse=recurse)
        except pysvn.ClientError:
            # TODO: uncommenting these might not be a good idea
            #~ traceback.print_exc()
            #~ log.exception("Exception occured in SVN.status() for %s" % path)
            return [pysvn.PysvnStatus({
                "text_status": pysvn.wc_status_kind.none,
                "prop_status": pysvn.wc_status_kind.none,
                "path": os.path.abspath(path)
            })]
    
    #~ @timeit
    def status_with_cache(self, path, invalidate=False, recurse=True):
        """
        
        Look up the status for path.
        
        If invalidate is set to False this function will look to see if a 
        status for the requested path is available in the cache and if so
        return that. Otherwise it will bypass the cache entirely.
        
        @type   path: string
        @param  path: A path pointing to an item (file or directory).
        
        @type   invalidate: boolean
        @param  invalidate: Whether or not the cache should be bypassed.

        @type   recurse: boolean
        @param  recurse: Should status recurse or not
        
        @rtype:        list of PysvnStatus
        @return:       A list of statuses for the given path, with the status
                       for the path being the first item in the list.
        
        """

        if (not invalidate and path in self.status_cache):
            return self.status_cache[path]  

        # The cache was bypassed or does not contain the requested path.
        statuses = self.status(path, recurse=recurse)
        
        # Empty out all the caches
        for status in statuses:
            current_path = os.path.join(path, status.data["path"].encode("utf-8"))
            while current_path != "/":
                self.status_cache[current_path] = []
                current_path = os.path.split(current_path)[0]
        
        # Fill them back up
        for status in statuses:
            current_path = os.path.join(path, status.data["path"].encode("utf-8"))
            while current_path != "/":
                if current_path not in self.status_cache: break;
                self.status_cache[current_path].append(status)
                current_path = os.path.split(current_path)[0]
        
        return self.status_cache[path]
        
    #
    # is
    #
    
    def is_working_copy(self, path):
        try:
            # when a versioned directory is removed and replaced with a
            # non-versioned directory (one that doesn't have a working copy
            # administration area, or .svn directory) you can't do a status 
            # call on that item itself (results in an exception).
            # 
            # Note that this is not a conflict, it's more of a corruption. 
            # And it's associated with the status "obstructed". The only
            # way to make sure that we're dealing with a working copy
            # is by verifying the SVN administration area exists.
            if (isdir(path) and
                    self.client.info(path) and
                    isdir(os.path.join(path, ".svn"))):
                return True
            return False
        except Exception, e:
            # FIXME: ClientError client in use on another thread
            #~ log.debug("EXCEPTION in is_working_copy(): %s" % str(e))
            return False
        
    def is_in_a_or_a_working_copy(self, path):
        return self.is_working_copy(path) or self.is_working_copy(os.path.split(path)[0])
        
    def is_versioned(self, path):
        if self.is_working_copy(path):
            return True
        else:
            # info will return nothing for an unversioned file inside a working copy
            if (self.is_working_copy(os.path.split(path)[0]) and
                    self.client.info(path)): 
                return True
                
            return False
    
    def is_status(self, path, text_status):
        try:
            status = self.status_with_cache(path, recurse=False)[-1]
        except Exception, e:
            log.exception("is_status exception for %s" % path)
            return False
        
        if status.data["text_status"] == text_status:
            return True
        
        if status.data["prop_status"] == text_status:
            return True
        
        return False

    def is_versioned(self, path):
        if self.is_working_copy(path):
            return True
        else:
            # info will return nothing for an unversioned file inside a working copy
            if (self.is_working_copy(os.path.split(path)[0]) and
                    self.client.info(path)): 
                return True
                
            return False
    
    def is_normal(self, path):
        return self.is_status(path, pysvn.wc_status_kind.normal)
    
    def is_added(self, path):
        return self.is_status(path, pysvn.wc_status_kind.added)
        
    def is_modified(self, path):
        return self.is_status(path, pysvn.wc_status_kind.modified)
    
    def is_deleted(self, path):
        return self.is_status(path, pysvn.wc_status_kind.deleted)
        
    def is_ignored(self, path):
        return self.is_status(path, pysvn.wc_status_kind.ignored)
    
    def is_locked(self, path):
        is_locked = False
        try:
            is_locked = self.client.info2(path, recurse=False)[0][1].lock is not None
        except pysvn.ClientError, e:
            return False
            #log.exception("is_locked exception for %s" % path)
            
        return is_locked

    def is_conflicted(self, path):
        return self.is_status(path, pysvn.wc_status_kind.conflicted)

    def is_missing(self, path):
        return self.is_status(path, pysvn.wc_status_kind.missing)

    def is_obstructed(self, path):
        return self.is_status(path, pysvn.wc_status_kind.obstructed)
        
    #
    # has
    #
    
    def has_status(self, path, text_status):
        try:
            statuses = self.status_with_cache(path, recurse=True)[:-1]
        except Exception, e:
            log.exception("has_status exception for %s" % path)
            return False
        
        for status in statuses:
            if status.data["text_status"] == text_status:
                return True
            if status.data["prop_status"] == text_status:
                return True
                
        return False
        
    def has_unversioned(self, path):
        return self.has_status(path, pysvn.wc_status_kind.unversioned)
    
    def has_added(self, path):
        return self.has_status(path, pysvn.wc_status_kind.added)
                
    def has_modified(self, path):
        return self.has_status(path, pysvn.wc_status_kind.modified)

    def has_deleted(self, path):
        return self.has_status(path, pysvn.wc_status_kind.deleted)

    def has_ignored(self, path):
        return self.has_status(path, pysvn.wc_status_kind.ignored)

    def has_locked(self, path):
        try:
            infos = self.client.info2(path)
        except:
            #log.exception("has_locked exception for %s" % path)
            return False

        for info in infos:
            if info[1].lock is not None:
                return True
        
        return False        

    def has_conflicted(self, path):
        return self.has_status(path, pysvn.wc_status_kind.conflicted)

    def has_missing(self, path):
        return self.has_status(path, pysvn.wc_status_kind.missing)

    def has_obstructed(self, path):
        return self.has_status(path, pysvn.wc_status_kind.obstructed)
        
    #
    # provides information for ui
    #
    
    def get_items(self, paths, statuses=[]):
        """
        Retrieves a list of files that have one of a set of statuses
        
        @type   paths:      list
        @param  paths:      A list of paths or files.
        
        @type   statuses:   list
        @param  statuses:   A list of pysvn.wc_status_kind statuses.
        
        @rtype:             list
        @return:            A list of PysvnStatus objects.
        
        """

        if paths is None:
            return []
        
        items = []
        for path in abspaths(paths):
            try:
                st = self.status(path)
            except Exception, e:
                log.exception("get_items exception")
                continue

            for st_item in st:
                if statuses and st_item.text_status not in statuses \
                  and st_item.prop_status not in statuses:
                    continue

                items.append(st_item)

        return items
        
    def get_repo_url(self, path):
        """
        Retrieve the repository URL for the given working copy path
        
        @type   path:   string
        @param  path:   A working copy path.
        
        @rtype:         string
        @return:        A repository URL.
        
        """
        
        # If the given path is not part of a working copy, keep trying the
        # parent path to see if it is part of a working copy
        path = self.get_versioned_path(os.path.abspath(path))
        if not path:
            return ""
        
        info = self.client.info(path)
        returner = ""
        try:
            returner = info["url"]
        except Exception, e:
            log.exception("Exception in svn.py get_repo_url() for %s" % path)

        return returner
    
    def get_revision(self, path):
        """
        Retrieve the current revision number for a path
        
        @type   path:   string
        @param  path:   A working copy path.
        
        @rtype:         integer
        @return:        A repository revision.
        
        """
    
        info = self.client.info(path)
        
        returner = None
        try:
            returner = info["revision"].number
        except KeyError, e:
            log.exception("KeyError exception in svn.py get_revision() for %s" % path)
        except AttributeError, e:
            log.exception("AttributeError exception in svn.py get_revision() for %s" % path)
        
        return returner
    
    #
    # properties
    #
    
    def get_versioned_path(self, path):
        """
        Generates a safe path to use with the prop* functions.
        If the given path is unversioned, go to the next path up.

        @type   path:   string
        @param  path:   A file or directory path.
        
        @rtype:         string
        @return:        A prop* function-safe path.

        """

        path_to_check = path
        path_to_use = None
        while path_to_check != "/" and path_to_check != "":
            if self.is_versioned(path_to_check):
                path_to_use = path_to_check
                return path_to_use

            path_to_check = os.path.split(path_to_check)[0]

        return path_to_use
        
    def propset(self, path, prop_name, prop_value, overwrite=False):
        """
        Adds an svn property to a path.  If the item is unversioned,
        add a recursive property to the parent path
        
        @type   path: string
        @param  path: A file or directory path.
        
        @type   prop_name: string
        @param  prop_name: An svn property name.
        
        @type   prop_value: string
        @param  prop_value: An svn property value/pattern.
        
        """

        path = self.get_versioned_path(path)
        if overwrite:
            props = prop_value
        else:
            props = self.propget(path, prop_name)
            props = "%s%s" % (props, prop_value)
        
        returner = False
        try:
            self.client.propset(
                prop_name, 
                props, 
                path, 
                recurse=True
            )
            returner = True
        except pysvn.ClientError, e:
            log.exception("pysvn.ClientError exception in svn.py propset() for %s" % path)
        except TypeError, e:
            log.exception("TypeError exception in svn.py propset() %s" % path)
            
        return returner
        
    def proplist(self, path):
        """
        Retrieves a dictionary of properties for a path.
        
        @type   path:   string
        @param  path:   A file or directory path.
        
        @rtype:         dictionary
        @return:        A dictionary of properties.
        
        """
        
        returner = self.client.proplist(path)
        if returner:
            returner = returner[0][1]
        else:
            returner = {}
            
        return returner
        
    def propget(self, path, prop_name):
        """
        Retrieves a dictionary of the prop_value of the given
        path and prop_name
        
        @type   path:       string
        @param  path:       A file or directory path.
        
        @type   prop_name:  string or self.PROPERTIES
        @param  prop_name:  An svn property name.
        
        @rtype:             dictionary
        @return:            A dictionary where the key is the path, the value 
                            is the prop_value.
        
        """

        path = self.get_versioned_path(path)
        try:
            returner = self.client.propget(
                prop_name,
                path,
                recurse=True
            )
        except pysvn.ClientError, e:
            log.exception("pysvn.ClientError exception in svn.py propget() for %s" % path)
            return ""
        
        try:
            returner = returner[path]
        except KeyError, e:
            returner = ""
            
        return returner
        
    def propdel(self, path, prop_name):
        """
        Removes a property from a given path
        
        @type   path: string
        @param  path: A file or directory path.
        
        @type   prop_name: string or self.PROPERTIES
        @param  prop_name: An svn property name.
        
        """
        
        path = self.get_versioned_path(path)
        
        returner = False
        try:
            self.client.propdel(
                prop_name,
                path,
                recurse=True
            )
            returner = True
        except pysvn.ClientError, e:
            log.exception("pysvn.ClientError exception in svn.py propdel() for %s" % path)
        except TypeError, e:
            log.exception("TypeError exception in svn.py propdel() %s" % path)
        
        return returner
    
    #
    # callbacks
    #
    
    def set_callback_cancel(self, func):
        self.client.callback_cancel = func
    
    def callback_cancel(self):
        if hasattr(self.client, "callback_cancel"):
            self.client.callback_cancel()

    def set_callback_notify(self, func):
        self.client.callback_notify = func
    
    def set_callback_get_log_message(self, func):
        self.client.callback_get_log_message = func
        
    def set_callback_get_login(self, func):
        self.client.callback_get_login = func
    
    def set_callback_ssl_server_trust_prompt(self, func):
        self.client.callback_ssl_server_trust_prompt = func
    
    def set_callback_ssl_client_cert_password_prompt(self, func):
        self.client.callback_ssl_client_cert_password_prompt = func
    
    #
    # revision
    #
    
    def revision(self, kind, date=None, number=None):
        """
        Create a revision object usable by pysvn
        
        @type   kind:   string
        @param  kind:   An svn.REVISIONS keyword.
        
        @type   date:   integer
        @param  date:   Used for kind=date, in the form of UNIX TIMESTAMP (secs).
        
        @type   number: integer
        @param  number: Used for kind=number, specifies the revision number.
        
        @rtype:         pysvn.Revision object
        @return:        A pysvn.Revision object.
        
        """
        
        # TODO: Don't use kwargs for date/number, just accept a "value" as a
        #       regular arg
        
        try:
            pysvn_obj = self.REVISIONS[kind]
        except KeyError, e:
            log.exception("pysvn.ClientError exception in svn.py revision()")
            return None
        
        returner = None
        if kind == "date":
            if date is None:
                log.exception("In svn.py revision(),kind = date, but date not given")
                return None
            
            returner = pysvn.Revision(pysvn_obj, date)
        
        elif kind == "number":
            if number is None:
                print "In svn.py revision(),kind = number, but number not given"
                return None
        
            returner = pysvn.Revision(pysvn_obj, number)
        
        else:
            returner = pysvn.Revision(pysvn_obj)
        
        return returner
        
    #
    # actions
    #
    
    def add(self, *args, **kwargs):
        """
        Add files or directories to the repository
        
        @type   paths: list
        @param  paths: A list of files/directories.
        
        @type   recurse: boolean
        @param  recurse: Recursively add a directory's children
        
        """
        
        return self.client.add(*args, **kwargs)
    
    def copy(self, *args, **kwargs):
        """
        Copy files/directories from src to dest.  src or dest may both be either
        a local path or a repository URL.  revision is a pysvn.Revision object.
        
        @type   src: string
        @param  src: Source URL or path.
        
        @type   dest: string
        @param  dest: Destination URL or path.
        
        @type   revision: pysvn.Revision object
        @param  revision: A pysvn.Revision object.
        
        """

        return self.client.copy(*args, **kwargs)
    
    def checkout(self, *args, **kwargs):
        
        """
        Checkout a working copy from a vcs repository
        
        @type   url: string
        @param  url: A repository url.
        
        @type   path: string
        @param  path: A local destination for the working copy.
        
        @type   recurse: boolean
        @param  recurse: Whether or not to run a recursive checkout.
        
        @type   ignore_externals: boolean
        @param  ignore_externals: Whether or not to ignore externals.
        
        """
        
        return self.client.checkout(*args, **kwargs)
    
    def cleanup(self, *args, **kwargs):
        """
        Clean up a working copy.
        
        @type   path: string
        @param  path: A local working copy path.
        
        """
        
        return self.client.cleanup(*args, **kwargs)
        
    def revert(self, *args, **kwargs):
        """
        Revert files or directories so they are unversioned
        
        @type   paths: list
        @param  paths: A list of files/directories.
        
        """
        
        return self.client.revert(*args, **kwargs)

    def commit(self, *args, **kwargs):
        """
        Commit a list of files to the repository.
        
        @type   paths: list
        @param  paths: A list of files/directories.
        
        @type   log_message: string
        @param  log_message: A commit log message.
        
        @type   recurse: boolean
        @param  recurse: Whether or not to recurse into sub-directories.
        
        @type   keep_locks: boolean
        @param  keep_locks: Whether or not to keep locks on commit.
        
        """

        return self.client.checkin(*args, **kwargs)
    
    def log(self, *args, **kwargs):
        """
        Retrieve log items for a given path in the repository
        
        @type   url_or_path: string
        @param  url_or_path: Path for which to get log items for
        
        @type   revision_start: pysvn.Revision
        @param  revision_start: Most recent revision.  Defaults to HEAD
        
        @type   revision_end: pysvn.Revision
        @param  revision_end: Oldest revision.  Defaults to rev 0.
        
        @type   limit: int
        @param  limit: The maximum number of items to return.  Defaults to 0.
        
        """
        
        return self.client.log(*args, **kwargs)

    def export(self, *args, **kwargs):
        
        """
        Export files from either a working copy or repository into a local
        path without versioning information.
        
        @type   src_url_or_path: string
        @param  src_url_or_path: A repository url.
        
        @type   dest_path: string
        @param  dest_path: A local destination for the working copy.
        
        @type   revision: pysvn.Revision
        @param  revision: The revision to retrieve from the repository.
        
        @type   recurse: boolean
        @param  recurse: Whether or not to run a recursive checkout.
        
        @type   ignore_externals: boolean
        @param  ignore_externals: Whether or not to ignore externals.
        
        """
        
        return self.client.export(*args, **kwargs)

    def import_(self, *args, **kwargs):
        
        """
        Import an unversioned file or directory structure into a repository.
        
        @type   path: string
        @param  path: An unversioned file or directory structure
        
        @type   url: string
        @param  url: A repository location to put the imported files
        
        @type   log_message: string
        @param  log_message: Log message to use for commit
        
        @type   ignore: boolean
        @param  ignore: Disregard svn:ignore props
        
        """
        
        return self.client.import_(*args, **kwargs)

    def lock(self, *args, **kwargs):
        
        """
        Lock a url or path.
        
        @type   url_or_path: string
        @param  url_or_path: A url or path to lock
        
        @type   lock_comment: string
        @param  lock_comment: A log message to go along with the lock.

        @type   force: boolean
        @param  force: Steal the locks of others if they exist.
        
        """
        
        return self.client.lock(*args, **kwargs)

    def relocate(self, *args, **kwargs):
        
        """
        Relocate the working copy from from_url to to_url for path
        
        @type   from_url: string
        @param  from_url: A url to relocate from
        
        @type   to_url: string
        @param  to_url: A url to relocate to

        @type   path: string
        @param  path: The path of the local working copy
        
        """
        
        return self.client.relocate(*args, **kwargs)
        
    def move(self, *args, **kwargs):
        
        """
        Schedule a file to be moved around the repository
        
        @type   src_url_or_path: string
        @param  src_url_or_path: A url/path to move from
        
        @type   dest_url_or_path: string
        @param  dest_url_or_path: A url/path to move to

        @type   force: boolean
        @param  force: Force renaming, despite conflicts. Defaults to false.
        
        """
        
        return self.client.move(*args, **kwargs)

    def remove(self, *args, **kwargs):
        
        """
        Schedule a file to be removed from the repository
        
        @type   url_or_path: string
        @param  url_or_path: A url/path to remove

        @type   force: boolean
        @param  force: Force renaming, despite conflicts. Defaults to false.

        @type   keep_local: boolean
        @param  keep_local: Keep the local copy (don't just delete it)        
                
        """
        
        return self.client.remove(*args, **kwargs)

    def revert(self, *args, **kwargs):
        """
        Revert files or directories from the repository
        
        @type   paths: list
        @param  paths: A list of files/directories.
        
        @type   recurse: boolean
        @param  recurse: Recursively add a directory's children
        
        """
        
        return self.client.revert(*args, **kwargs)

    def resolve(self, *args, **kwargs):
        """
        Mark conflicted files as resolved
        
        @type   path: string
        @param  path: A local path to resolve
        
        @type   recurse: boolean
        @param  recurse: Recursively add a directory's children
        
        """
        
        return self.client.resolved(*args, **kwargs)

    def switch(self, *args, **kwargs):
        """
        Switch the working copy to another repository source.
        
        @type   path: string
        @param  path: A local path to a working copy
        
        @type   url: string
        @param  url: The repository location to switch to
        
        @type   revision: pysvn.Revision
        @param  revision: The revision of the repository to switch to (Def:HEAD)
        
        """
        
        return self.client.switch(*args, **kwargs)

    def unlock(self, *args, **kwargs):
        """
        Unlock locked files.
        
        @type   path: string
        @param  path: A local path to resolve
        
        @type   force: boolean
        @param  force: If locked by another user, unlock it anyway.
        
        """
        
        return self.client.unlock(*args, **kwargs)

    def update(self, *args, **kwargs):
        """
        Update a working copy.
        
        @type   path: string
        @param  path: A local path to update
        
        @type   recurse: boolean
        @param  recurse: Update child folders recursively
        
        @type   revision: pysvn.Revision
        @param  revision: Revision to update to (Def: HEAD)
        
        @type   ignore_externals: boolean
        @param  ignore_externals: Ignore external items
        
        """
        
        return self.client.update(*args, **kwargs)

    def annotate(self, *args, **kwargs):
        """
        Get the annotate results for the given file and revision range.
        
        @type   url_or_path: string
        @param  url_or_path: A url or local path
                
        @type   from_revision: pysvn.Revision
        @param  from_revision: Revision from (def: 1)
        
        @type   to_revision: pysvn.Revision
        @param  to_revision: Revision to (def: HEAD)
                
        """
        
        return self.client.annotate(*args, **kwargs)

    def merge_ranges(self, *args, **kwargs):
        """
        Merge a range of revisions.
        
        @type   source: string
        @param  source: A repository location
        
        @type   ranges_to_merge: list of tuples
        @param  ranges_to_merge: A list of revision ranges to merge
        
        @type   peg_revision: pysvn.Revision
        @param  peg_revision: Indicates which revision in sources is valid.
        
        @type   target_wcpath: string
        @param  target_wcpath: Target working copy path
        
        @type   notice_ancestry: boolean
        @param  notice_ancestry: unsure
        
        @type   force: boolean
        @param  force: unsure
        
        @type   dry_run: boolean
        @param  dry_run: Do a test/dry run or not
        
        @type   record_only: boolean
        @param  record_only: unsure
        
        TODO: Will firm up the parameter documentation later
        
        """

        return self.client.merge_peg2(*args, **kwargs)
    
    def has_merge2(self):
        """
        Tests whether the user has a later version of pysvn/svn installed
        with more merge features
        """
        return hasattr(self.client, "merge_peg2")

    def merge_trees(self, *args, **kwargs):
        """
        Merge two trees into one.

        @type   url_or_path1: string
        @param  url_or_path1: From WC/URL location

        @type   revision1: pysvn.Revision
        @param  revision1: Indicates the revision of the URL/Path

        @type   url_or_path2: string
        @param  url_or_path2: To WC/URL location

        @type   revision2: pysvn.Revision
        @param  revision2: Indicates the revision of the URL/Path
        
        @type   local_path: string
        @param  local_path: Target working copy path
        
        @type   force: boolean
        @param  force: unsure
        
        @type   recurse: boolean
        @param  recurse: Merge children recursively
        
        @type   record_only: boolean
        @param  record_only: unsure
        
        TODO: Will firm up the parameter documentation later
        
        """

        return self.client.merge(*args, **kwargs)

    def diff(self, *args, **kwargs):
        """
        Returns the diff text between the base code and the working copy.
        
        @type   tmp_path: string
        @param  tmp_path: Temporal path to store the diff
        
        @type   url_or_path: string
        @param  url_or_path: From WC/URL location
        
        @type   revision1: pysvn.Revision
        @param  revision1: Indicates the revision of the URL/Path (def: pysvn.Revision( opt_revision_kind.base ))
        
        @type   url_or_path2: string
        @param  url_or_path2: From WC/URL location
        
        @type   revision2: pysvn.Revision
        @param  revision2: Indicates the revision of the URL/Path (def: pysvn.Revision( opt_revision_kind.working ))
        
        @type   recurse: boolean
        @param  recurse: Whether or not to recurse into sub-directories. (def: True)
        
        @type   ignore_ancestry: boolean
        @param  ignore_ancestry: Whether or not to recurse into sub-directories. (def: False)
        
        @type   diff_deleted: boolean
        @param  diff_deleted: Whether or not to recurse into sub-directories. (def: True)
        
        @type   ignore_content_type: boolean
        @param  ignore_content_type: Whether or not to recurse into sub-directories. (def: False)
        
        """
        
        return self.client.diff(*args, **kwargs)
    
    def is_version_less_than(self, version):
        """
        @type   version: tuple
        @param  version: A version tuple to compare pysvn's version to
        """
        
        if version[0] > pysvn.version[0]:
            return True
        
        if ((version[0] == pysvn.version[0])
                and (version[1] > pysvn.version[1])):
            return True
        
        if ((version[0] == pysvn.version[0])
                and (version[1] == pysvn.version[1])
                and (version[2] > pysvn.version[2])):
            return True
       
        if ((version[0] == pysvn.version[0])
                and (version[1] == pysvn.version[1])
                and (version[2] == pysvn.version[2])
                and (version[3] > pysvn.version[3])):
            return True
        
        return False

    def is_version_greater_than(self, version):
        """
        @type   version: tuple
        @param  version: A version tuple to compare pysvn's version to
        """
        
        if version[0] < pysvn.version[0]:
            return True
        
        if ((version[0] == pysvn.version[0])
                and (version[1] < pysvn.version[1])):
            return True
        
        if ((version[0] == pysvn.version[0])
                and (version[1] == pysvn.version[1])
                and (version[2] < pysvn.version[2])):
            return True
       
        if ((version[0] == pysvn.version[0])
                and (version[1] == pysvn.version[1])
                and (version[2] == pysvn.version[2])
                and (version[3] < pysvn.version[3])):
            return True
        
        return False
