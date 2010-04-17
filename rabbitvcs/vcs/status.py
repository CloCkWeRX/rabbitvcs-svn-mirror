
import os.path
import unittest

from rabbitvcs import gettext
_ = gettext.gettext

# These are the statuses that we might represent with icons
status_unchanged = 'unchanged'
status_changed = 'changed'
status_added = 'added'
status_deleted = 'deleted'
status_ignored = 'ignored'
status_read_only = 'read-only'
status_locked = 'locked'
status_unknown = 'unknown'
# Specifically: this means something IN A WORKING COPY but not added
status_unversioned = 'unversioned'
status_missing = 'missing'
status_replaced = 'replaced'
# "complicated" = anything we display with that exclamation mark icon
status_complicated = 'complicated'
status_calculating = 'calculating'
status_error = 'error'

MODIFIED_CHILD_STATUSES = [
    status_changed,
    status_added,
    status_deleted,
    status_missing,
    status_replaced
]

class Status(object):

    @staticmethod
    def status_unknown(path):
        return Status(path, status_unknown, summary = status_unknown)
    
    @staticmethod
    def status_error(path):
        return Status(path, status_error, summary = status_error)
    
    @staticmethod
    def status_calc(path):
        return Status(path, status_calculating, summary = status_calculating)
    
    vcs_type = 'generic'
 
    clean_statuses = ['unchanged']
    
    content_status_map = None
    metadata_status_map = None
    
    def __init__(self, path, content, metadata = None, summary = None):
        self.path = path
        self.content = content
        self.metadata = metadata
        self.single = self._make_single_status()
        self.summary = summary
 
    def _make_single_status(self):
        """
        Given our text_status and a prop_status, simplify to a single "simple"
        status. If we don't know how to simplify our particular combination of
        status, call it an error.
        """     
        # Content status dominates
        single = self.simple_content_status() or status_error
        if single in Status.clean_statuses:
            if self.metadata:
                single = self.simple_metadata_status() or status_error
        return single

    def simple_content_status(self):
        if self.content_status_map:
            return self.content_status_map.get(self.content)
        else:
            return self.content
        
    def simple_metadata_status(self):
        if self.metadata and self.metadata_status_map:
            return self.metadata_status_map.get(self.metadata)
        else:
            return self.metadata

    def make_summary(self, child_statuses = []):
        """ Summarises statuses for directories.
        """    
        summary = status_unknown
        
        status_set = set([st.single for st in child_statuses])
        
        if not status_set:
            self.summary = self.single
        
        if status_complicated in status_set:
            self.summary = status_complicated
        elif self.single in ["added", "modified", "deleted"]:
            # These take priority over child statuses
            self.summary = self.single        
        elif len(set(MODIFIED_CHILD_STATUSES) & status_set):
            self.summary = status_changed
        else:
            self.summary = self.single
        
        return summary
    
    def is_versioned(self):
        return self.single is not status_unversioned
            
    def is_modified(self):
        # This may need to be more sophisticated... eg. is read-only modified?
        # Unknown? etc... 
        return self.single is not status_unchanged
    
    def has_modified(self):
        # Includes self being modified!
        return self.summary is not status_unchanged    
    
    def __repr__(self):
        return "<%s %s (%s) %s/%s>" % (_("RabbitVCS status for"),
                                        self.path,
                                        self.vcs_type,
                                        self.content,
                                        self.metadata)

    def __getstate__(self):
        attrs = self.__dict__.copy()
        attrs['__type__'] = type(self).__name__
        attrs['__module__'] = type(self).__module__
        return attrs
        
    def __setstate__(self, state_dict):
        del state_dict['__type__']
        del state_dict['__module__']
        self.__dict__ = state_dict

class SVNStatus(Status):

    vcs_type = 'subversion'
    
    content_status_map = {
        'normal': status_unchanged,
        'added': status_added,
        'missing': status_missing,
        'unversioned': status_unversioned,
        'deleted': status_deleted,
        'replaced': status_changed,
        'modified': status_changed,
        'merged': status_changed,
        'conflicted': status_complicated,
        'ignored': status_ignored,
        'obstructed': status_complicated,
        # FIXME: is this the best representation of 'externally populated'?
        'external': status_unchanged,
        'incomplete': status_complicated
    }
    
    metadata_status_map = {
        'normal': status_unchanged,
        'none': status_unchanged,
        'modified': status_changed
        }
    
#external - an unversioned path populated by an svn:external property
#incomplete - a directory doesn't contain a complete entries list
    
    def __init__(self, pysvn_status):
        # There is a potential problem here: I'm pretty sure that PySVN statuses
        # do NOT have translatable representations, so this will always come out
        # to be 'normal', 'modified' etc
        super(SVNStatus, self).__init__(
            pysvn_status.path,
            content=str(pysvn_status.text_status),
            metadata=str(pysvn_status.prop_status))

class GitStatus(Status):

    vcs_type = 'git'
    
    content_status_map = {
        'normal': status_unchanged,
        'added': status_added,
        'missing': status_missing,
        'untracked': status_unversioned,
        'removed': status_deleted,
        'modified': status_changed,
        'renamed': status_changed,
        'ignored': status_ignored
    }
    
    metadata_status_map = {
        'normal': status_unchanged,
        None: status_unchanged
    }
    
    is_staged = False

    def __init__(self, gittyup_status):
        super(GitStatus, self).__init__(
            gittyup_status.path,
            content=str(gittyup_status.identifier),
            metadata=None)
        
        self.is_staged = gittyup_status.is_staged

STATUS_TYPES = [
    Status,
    SVNStatus,
    GitStatus
]

class TestStatusObjects(unittest.TestCase):
    
    base = "/path/to/test"
        
    children = [
        os.path.join(base, chr(x)) for x in range(97,123) 
                ]
    
    def testsingle_clean(self):
        status = Status(self.base, status_unchanged)
        self.assertEqual(status.single, status_unchanged)
        
    def testsingle_changed(self):
        status = Status(self.base, status_changed)
        self.assertEqual(status.single, status_changed)
        
    def testsingle_propclean(self):
        status = Status(self.base, status_unchanged, status_unchanged)
        self.assertEqual(status.single, status_unchanged)

    def testsingle_propchanged(self):
        status = Status(self.base, status_unchanged, status_changed)
        self.assertEqual(status.single, status_changed)
        
    def testsummary_clean(self):
        top_status = Status(self.base, status_unchanged)
        child_sts = [Status(path, status_unchanged) for path in self.children]
        top_status.make_summary(child_sts)
        self.assertEqual(top_status.summary, status_unchanged)

    def testsummary_changed(self):
        top_status = Status(self.base, status_unchanged)
        child_sts = [Status(path, status_unchanged) for path in self.children]
        
        child_sts[1] = Status(child_sts[1].path, status_changed)
        
        top_status.make_summary(child_sts)
        self.assertEqual(top_status.summary, status_changed)

    def testsummary_added(self):
        top_status = Status(self.base, status_unchanged)
        child_sts = [Status(path, status_unchanged) for path in self.children]
        
        child_sts[1] = Status(child_sts[1].path, status_added)
        
        top_status.make_summary(child_sts)
        self.assertEqual(top_status.summary, status_changed)

    def testsummary_complicated(self):
        top_status = Status(self.base, status_unchanged)
        child_sts = [Status(path, status_unchanged) for path in self.children]
        
        child_sts[1] = Status(child_sts[1].path, status_complicated)
        
        top_status.make_summary(child_sts)
        self.assertEqual(top_status.summary, status_complicated)

    def testsummary_propchange(self):
        top_status = Status(self.base, status_unchanged)
        child_sts = [Status(path, status_unchanged) for path in self.children]
        
        child_sts[1] = Status(child_sts[1].path,
                              status_unchanged,
                              status_changed)
        
        top_status.make_summary(child_sts)
        self.assertEqual(top_status.summary, status_changed)

    def testsummary_bothchange(self):
        top_status = Status(self.base, status_unchanged)
        child_sts = [Status(path, status_unchanged) for path in self.children]
        
        child_sts[1] = Status(child_sts[1].path,
                              status_complicated,
                              status_changed)
        
        top_status.make_summary(child_sts)
        self.assertEqual(top_status.summary, status_complicated)

    def testsummary_topadded(self):
        top_status = Status(self.base, status_added)
        child_sts = [Status(path, status_unchanged) for path in self.children]
        
        child_sts[1] = Status(child_sts[1].path, status_changed, status_changed)
        
        top_status.make_summary(child_sts)
        self.assertEqual(top_status.summary, status_added)
    
if __name__ == "__main__":
    unittest.main()
