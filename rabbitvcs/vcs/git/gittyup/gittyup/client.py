#
# client.py
#

import os
import re
import shutil
from time import time, timezone

import dulwich.errors
import dulwich.repo
import dulwich.objects
from dulwich.pack import Pack
from dulwich.index import commit_index, write_index_dict, SHA1Writer

from gittyup.exceptions import *
import gittyup.util
from gittyup.objects import *
from gittyup.config import GittyupLocalFallbackConfig
from gittyup.command import GittyupCommand

TZ = -1 * timezone
ENCODING = "UTF-8"

DULWICH_COMMIT_TYPE = 1
DULWICH_TREE_TYPE = 2
DULWICH_BLOB_TYPE = 3
DULWICH_TAG_TYPE = 4

def notify(output):
    print "Notify: ---%s---" % output

class GittyupClient:
    def __init__(self, path=None, create=False):
        if path:
            try:
                self.repo = dulwich.repo.Repo(os.path.realpath(path))
                self._load_config()
            except dulwich.errors.NotGitRepository:
                if create:
                    self.initialize_repository(path)
                else:
                    raise NotRepositoryError()
        else:
            self.repo = None

    #
    # Start Private Methods
    #

    def _initialize_index(self):
        index_path = self.repo.index_path()
        f = open(index_path, "wb")
        try:
            f = SHA1Writer(f)
            write_index_dict(f, {})
        finally:
            f.close()

    def _get_index(self):
        if self.repo.has_index() == False:
            self._initialize_index()
        
        return self.repo.open_index()
    
    def _get_tree_at_head(self):
        try:
            tree = self.repo.tree(self.repo.commit(self.repo.head()).tree)
        except KeyError, e:
            tree = dulwich.objects.Tree()

        return tree

    def _get_working_tree(self):
        return self.repo.tree(commit_index(self.repo.object_store, self._get_index()))
    
    def _read_directory_tree(self, path):
        paths = []
        for root, dirs, filenames in os.walk(path, topdown=True):
            try:
                dirs.remove(".git")
            except ValueError:
                pass

            for filename in filenames:
                paths.append(self._get_relative_path(os.path.join(root, filename)))
        
        return sorted(paths)

    def _get_repository_path(self, path):
        path_to_check = os.path.realpath(path)
        while path_to_check != "/" and path_to_check != "":
            if os.path.isdir(os.path.join(path_to_check, ".git")):
                return path_to_check
            
            path_to_check = os.path.split(path_to_check)[0]
        
        return None

    def _get_relative_path(self, path):
        return gittyup.util.relativepath(os.path.realpath(self.repo.path), path)      
    
    def _get_absolute_path(self, path):
        return os.path.join(self.repo.path, path)      

    def _get_blob_from_file(self, path):
        file = open(path, "rb")
        try:
            blob = dulwich.objects.Blob.from_string(file.read())
        finally:
            file.close()
        
        return blob

    def _write_blob_to_file(self, path, blob):
        dirname = os.path.dirname(path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
    
        file = open(path, "wb")
        try:
            file.write(blob.get_data())
        finally:
            file.close()

    def _load_config(self):
        self.config = GittyupLocalFallbackConfig(self.repo.path)

    def _get_config_user(self):
        try:
            config_user_name = self.config.get("user", "name")
            config_user_email = self.config.get("user", "email")
            return "%s <%s>" % (config_user_name, config_user_email)
        except KeyError:
            return None
    
    def _write_packed_refs(self, refs):
        packed_refs_str = ""
        for ref,sha in refs.items():
            packed_refs_str = "%s %s\n" % (sha, ref)
        
        fd = open(os.path.join(self.repo.controldir(), "packed-refs"), "wb")
        fd.write(packed_refs_str)
        fd.close()
    
    #
    # Start Public Methods
    #
    
    def initialize_repository(self, path, bare=False):
        real_path = os.path.realpath(path)
        if not os.path.isdir(real_path):
            os.mkdir(real_path)

        if bare:
            self.repo = dulwich.repo.Repo.init_bare(real_path)
        else:
            self.repo = dulwich.repo.Repo.init(real_path)
            
        self._load_config()

        self.config.set_section("core", {
            "logallrefupdates": "true",
            "filemode": "true",
            "base": "false",
            "logallrefupdates": "true"
        })

    def set_repository(self, path):
        try:
            self.repo = dulwich.repo.Repo(os.path.realpath(path))
            self._load_config()
        except dulwich.errors.NotGitRepository:
            raise NotRepositoryError()

    def track(self, name):
        self.repo.refs["HEAD"] = "ref: %s" % name

    def is_tracking(self, name):
        return (self.repo.refs["HEAD"] == "ref: %s" % name)

    def tracking(self):
        return self.repo.refs["HEAD"][5:]
    
    def stage(self, paths):
        tree = self._get_tree_at_head()
        index = self._get_index()
        
        if isinstance(paths, str):
            paths = [paths]

        for path in paths:
            relative_path = self._get_relative_path(path)
            absolute_path = self._get_absolute_path(path)
            blob = self._get_blob_from_file(path)
            
            if relative_path in index:
                (ctime, mtime, dev, ino, mode, uid, gid, size, blob_id, flags) = index[relative_path]
            else:
                (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(path)
                flags = 0

            index[relative_path] = (ctime, mtime, dev, ino, mode, uid, gid, size, blob.id, flags)
            index.write()

            self.repo.object_store.add_object(blob)
    
    def stage_all(self):
        index = self._get_index()
        for status in self.status():
            if status in [AddedStatus, RemovedStatus, ModifiedStatus]:
                self.stage(self._get_absolute_path(status.path))

            if status == MissingStatus:
                del index[status.path]
                index.write()           

    def unstage(self, paths):
        index = self._get_index()
        tree = self._get_tree_at_head()

        if isinstance(paths, str):
            paths = [paths]
        
        for path in paths:
            relative_path = self._get_relative_path(path)
            if relative_path in index:
                if relative_path in tree:
                    (ctime, mtime, dev, ino, mode, uid, gid, size, blob_id, flags) = index[relative_path]
                    (mode, blob_id) = tree[relative_path]
                    index[relative_path] = (ctime, mtime, dev, ino, mode, uid, gid, size, blob_id, flags)
                else:
                    del index[relative_path]
            else:
                if relative_path in tree:
                    index[relative_path] = (0, 0, 0, 0, tree[relative_path][0], 0, 0, 0, tree[relative_path][1], 0)

        index.write()
    
    def unstage_all(self):
        index = self._get_index()
        for status in self.status():
            self.unstage(self._get_absolute_path(status.path))
    
    def get_staged(self):
        staged = []
        tree = self._get_tree_at_head()
        index = self._get_index()
        if len(tree) > 0:
            for item in index.changes_from_tree(self.repo.object_store, tree.id):
                ((old_name, new_name), (old_mode, new_mode), (old_sha, new_sha)) = item

                if new_name:
                    staged.append(new_name)
                if old_name and old_name != new_name:
                    staged.append(old_name)

        return staged

    def is_staged(self, path):
        relative_path = self._get_relative_path(path)
        return (relative_path in self.get_staged())
    
    def branch(self, name, commit_sha=None, track=False):
        if commit_sha:
            try:
                commit = self.repo.commit(commit_sha)
            except AssertionError:
                raise NotCommitError(commit_sha)
        else:
            commit = self.repo.commit(self.repo.head())

        self.repo.refs["refs/heads/%s" % name] = commit.id
        
        if track:
            self.track("refs/heads/%s" % name)
        
        return commit.id

    def branch_delete(self, name):
        ref_name = "refs/heads/%s" % name
        refs = self.repo.get_refs()
        if ref_name in refs:
            if self.is_tracking(ref_name):
                self.track("refs/heads/master")
        
            del self.repo.refs[ref_name]

    def branch_rename(self, old_name, new_name):
        old_ref_name = "refs/heads/%s" % old_name
        new_ref_name = "refs/heads/%s" % new_name
        refs = self.repo.get_refs()
        if old_ref_name in refs:
            self.repo.refs[new_ref_name] = self.repo.refs[old_ref_name]
            if self.is_tracking(old_ref_name):
                self.track(new_ref_name)
            
            del self.repo.refs[old_ref_name]

    def branch_list(self):
        refs = self.repo.get_refs()
        branches = []
        for ref,branch_sha in refs.items():
            if ref.startswith("refs/heads"):
                branch = Branch(ref[11:], branch_sha, self.repo[branch_sha])
                branches.append(branch)
        
        return branches

    def checkout(self, paths=[], tree_sha=None, commit_sha=None):
        tree = None
        if tree_sha:
            try:
                tree = self.repo.tree(tree_sha)
            except AssertionError:
                raise NotTreeError(tree_sha)
        elif commit_sha:
            try:
                commit = self.repo.commit(commit_sha)
                tree = commit.tree
            except AssertionError:
                raise NotCommitError(commit_sha)

        if not tree:
            tree = self._get_tree_at_head()

        relative_paths = []
        for path in paths:
            relative_paths = self._get_relative_path(path)

        index = self._get_index()
        for (name, mode, sha) in self.repo.object_store.iter_tree_contents(tree.id):
            if name in relative_paths or len(paths) == 0:
                blob = self.repo.get_blob(sha)
                absolute_path = self._get_absolute_path(name)
                self._write_blob_to_file(absolute_path, blob)                

                (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(absolute_path)
                index[name] = (ctime, mtime, dev, ino, mode, uid, gid, size, blob.id, 0)
    
    def clone(self, host, path, bare=False, origin="origin"):
        self.initialize_repository(path, bare)
        self.remote_add(host, origin)
        refs = self.fetch(host)

        if bare: return

        # Checkout the cloned repository into the local repository
        obj = self.repo.commit(refs["HEAD"])
        self.checkout(tree_sha=obj.tree)

        # Set up refs so the local repository can track the remote repository
        ref_key = "refs/remotes/%s/master" % origin
        self._write_packed_refs({
            ref_key: refs["refs/heads/master"]
        })
        self.repo.refs["HEAD"] = refs["HEAD"]
        self.repo.refs["refs/heads/master"] = refs["refs/heads/master"]
        self.repo.refs[ref_key] = refs["HEAD"]

        # Set config information

        self.config.set_section('branch "master"', {
            "remote": origin,
            "merge": "refs/heads/master"
        })
        self.config.write()   
    
    def commit(self, message, parents=None, committer=None, commit_time=None, 
            commit_timezone=None, author=None, author_time=None, 
            author_timezone=None, encoding=None, commit_all=False):

        if commit_all:
            self.stage_all()

        commit = dulwich.objects.Commit()
        commit.message = message
        commit.tree = commit_index(self.repo.object_store, self._get_index())

        initial_commit = False
        try:
            commit.parents = (parents and parents or [self.repo.head()])
        except KeyError:
            # The initial commit has no parent
            initial_commit = True
            pass

        config_user = self._get_config_user()
        if config_user is None:
            if committer is None:
                raise ValueError("The committing person has not been specified")
            if author is None:
                raise ValueError("The author has not been specified")

        commit.committer = (committer and committer or config_user)
        commit.commit_time = (commit_time and commit_time or int(time()))
        commit.commit_timezone = (commit_timezone and commit_timezone or TZ)
        
        commit.author = (author and author or config_user)
        commit.author_time = (author_time and author_time or int(time()))
        commit.author_timezone = (author_timezone and author_timezone or TZ)        
        
        commit.encoding = (encoding and encoding or ENCODING)
        
        self.repo.object_store.add_object(commit)
        
        self.repo.refs[self.tracking()] = commit.id
        
        if initial_commit:
            self.track("refs/heads/master")

        return commit.id
    
    def remove(self, paths):
        if isinstance(paths, str):
            paths = [paths]

        index = self._get_index()
        
        for path in paths:
            relative_path = self._get_relative_path(path)
            if relative_path in index:
                del index[relative_path]
                os.remove(path)

        index.write()        
    
    def move(self, source, dest):
        index = self._get_index()
        relative_source = self._get_relative_path(source)
        relative_dest = self._get_relative_path(dest)

        # Get a list of affected files so we can update the index
        source_files = []
        if os.path.isdir(source):
            for name in index:
                if name.startswith(relative_source):
                    source_files.append(name)
        else:
            source_files.append(self._get_relative_path(source))

        # Rename the affected index entries
        for source_file in source_files:
            new_path = source_file.replace(relative_source, relative_dest)            
            if os.path.isdir(dest):
                new_path = os.path.join(new_path, os.path.basename(source_file))

            index[new_path] = index[source_file]
            del index[source_file]

        index.write()
        
        # Actually move the file/folder
        shutil.move(source, dest)

    def pull(self, repository="origin", refspec="master"):
        cmd = ["git", "pull", repository, refspec]
        try:
            (status, stdout, stderr) = GittyupCommand(cmd, cwd=self.repo.path).execute()
        except GittyupCommandError, e:
            print e
    
    def fetch(self, host):
        client, host_path = gittyup.util.get_transport_and_path(host)

        graphwalker = self.repo.get_graph_walker()
        f, commit = self.repo.object_store.add_pack()
        refs = client.fetch_pack(host_path, self.repo.object_store.determine_wants_all, 
                          graphwalker, f.write, notify)

        commit()
        
        return refs
    
    def remote_add(self, host, origin="origin"):
        self.config.set("remote \"%s\"" % origin, "fetch", "+refs/heads/*:refs/remotes/%s/*" % origin)
        self.config.set("remote \"%s\"" % origin, "url", host)
        self.config.write()
    
    def remote_delete(self, origin="origin"):
        self.config.remove_section("remote \"%s\"" % origin)
        self.config.write()
    
    def remote_list(self):
        ret = []
        for section, values in self.config.get_all():
            if section.startswith("remote"):
                m = re.match("^remote \"(.*?)\"$", section)
                if m:
                    ret.append({
                        "remote": m.group(1),
                        "url": values["url"],
                        "fetch": values["fetch"]
                    })

        return ret
    
    def tag(self, name, message, tagger=None, tag_time=None, tag_timezone=None,
            tag_object=None, track=False):
            
        tag = dulwich.objects.Tag()
        
        config_user = self._get_config_user()

        if config_user is None:
            if tagger is None:
                raise ValueError("The tagging person has not been specified")
        
        tag.name = name
        tag.message = message
        tag.tagger = (tagger and tagger or config_user)
        tag.tag_time = (tag_time and tag_time or int(time()))
        tag.tag_timezone = (tag_timezone and tag_timezone or TZ)
        
        if tag_object is None:
            tag_object = (DULWICH_COMMIT_TYPE, self.repo.head())

        tag.set_object(tag_object)

        self.repo.object_store.add_object(tag)
        
        self.repo.refs["refs/tags/%s" % name] = tag.id
        
        if track:
            self.track("refs/tags/%s" % name)
        
        return tag.id
    
    def tag_delete(self, name):
        ref_name = "refs/tags/%s" % name
        refs = self.repo.get_refs()
        if ref_name in refs:
            del self.repo.refs[ref_name]
    
    def tag_list(self):
        refs = self.repo.get_refs()
        tags = []
        for ref,tag_sha in refs.items():
            if ref.startswith("refs/tags"):
                tag = Tag(tag_sha, self.repo[tag_sha])
                tags.append(tag)
        
        return tags
    
    def status(self):
        tree = self._get_tree_at_head()
        index = self._get_index()
        paths = self._read_directory_tree(self.repo.path)
        
        statuses = []
        tracked_paths = set(index)
        if len(tree) > 0:
            for (name, mode, sha) in self.repo.object_store.iter_tree_contents(tree.id):
                if name in tracked_paths:
                    absolute_path = self._get_absolute_path(name)
                    if os.path.exists(absolute_path):
                        # Cached, determine if modified or not                        
                        blob = self._get_blob_from_file(absolute_path)
                        if blob.id == index[name][8]:
                            statuses.append(NormalStatus(name))
                        else:
                            statuses.append(ModifiedStatus(name))
                    else:
                        # Missing
                        statuses.append(MissingStatus(name))
                    
                    tracked_paths.remove(name)
                else:
                    # Removed
                    statuses.append(RemovedStatus(name))

                try:
                    paths.remove(name)
                except ValueError:
                    pass

        for name in tracked_paths:
            # Added
            statuses.append(AddedStatus(name))
            try:
                paths.remove(name)
            except ValueError:
                pass

        # Find untrackedfiles
        for path in paths:
            statuses.append(UntrackedStatus(path))

        return statuses
    
    def log(self):
        try:
            return self.repo.revision_history(self.repo.head())
        except dulwich.errors.NotCommitError:
            raise NotCommitError()
            return None
