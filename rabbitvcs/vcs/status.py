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
        return Status(path, status_unknown)
    
    @staticmethod
    def status_error(path):
        return Status(path, status_error)
    
    @staticmethod
    def status_calc(path):
        return Status(path, status_calculating)
    
    vcs_type = 'generic'
 
    clean_statuses = ['unchanged']
    
    content_status_map = None
    metadata_status_map = None
    
    def __init__(self, path, content, metadata = None, summary = None):
        # own_status is a StatusInfo objects
        # summary is one of the simple enumerations
        self.path = path
        self.content = content
        self.metadata = metadata or content # a bit hackish, but makes sense
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
            single = self.simple_metadata_status() or status_error
        return single

    def simple_content_status(self):
        if self.content_status_map:
            return self.content_status_map.get(self.content)
        else:
            return self.content
        
    def simple_metadata_status(self):
        if self.metadata_status_map:
            return self.metadata_status_map.get(self.metadata)
        else:
            return self.metadata

    def make_summary(self, child_statuses = None):
        if child_statuses:
            self.summary = summarise_statuses(self,
                                              child_statuses)
        else:
            self.summary = self.single
   
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
        
    def __setstate__(self, dict):
        del dict['__type__']
        del dict['__module__']
        self.__dict__ = dict

class SVNStatus(Status):

    vcs_type = 'subversion'
    
    content_status_map = {
        'normal': status_unchanged,
        'added': status_added,
        'missing': status_missing,
        'unversioned': status_unknown,
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


def summarise_statuses(top_dir_status, statuses):
    """ Summarises statuses for directories.
    """    
    summary = status_unknown
    
    status_set = set([st.single for st in statuses])
    
    if not status_set:
        # This indicates a serious deviation from our expected API
        log.debug("Status set for summary is empty!")
        summary = status_error
    
    if status_complicated in status_set:
        summary = status_complicated
    
    elif top_dir_status.single in ["added", "modified", "deleted"]:
        # These take priority over child statuses
        summary = top_dir_status.single
    
    elif len(set(MODIFIED_CHILD_STATUSES) & status_set):
        summary = status_changed
    
    else:
        summary = top_dir_status.single
    
    return summary

STATUS_TYPES = [
    Status,
    SVNStatus
]