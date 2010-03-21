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

class StatusInfo(object):

    vcs_type = 'generic'
 
    clean_statuses = ['unchanged']
    
    content_status_map = None
    metadata_status_map = None
 
    def __init__(self, content_status, metadata_status = None):
        # vcs_type may be None for things like error, calculating, etc
        self.content = content_status
        self.metadata = metadata_status
        self.single = self._make_single_status()
 
    def _make_single_status(self):
        """
        Given our text_status and a prop_status, simplify to a single "simple"
        status. If we don't know how to simplify our particular combination of
        status, call it an error.
        """     
        # Content status dominates
        single = self.simple_content_status() or status_error
        if single in StatusInfo.clean_statuses:
            single = self.simple_metadata_status() or status_error
        return single

    def simple_content_status(self):
        if self.content_status_map:
            return self.content_status_map.get(self.content)
        
    def simple_metadata_status(self):
        if self.metadata_status_map:
            return self.metadata_status_map.get(self.metadata)
    
    def __repr__(self):
        return "<%s (%s) %s/%s>" % (_("RabbitVCS status"),
                                    self.vcs_type,
                                    self.content,
                                    self.metadata)

class Status(object):
    
    @staticmethod
    def status_error(path):
        return Status(path, StatusInfo(status_error, status_error))
    
    def __init__(self, path, own_status):
        self.path = path
        self.own_status = own_status

    def __repr__(self):
        return "<%s %s>" % (_("RabbitVCS status for"), self.path)

class StatusSummary(object):
    
    def __init__(self, own, summary):
        self.own = own
        self.summary = summary
        
    def __repr__(self):
        return "<%s %s (%s)>" % (_("RabbitVCS status summary for"),
                            self.single_status.path,
                            self.summary)
        
class SVNStatusInfo(StatusInfo):
    
    vcs_type = 'subversion'
    
    content_status_map = {
        'normal': status_unchanged,
    }
    
    metadata_status_map = {
        'normal': status_unchanged,
        'none': status_unchanged
        }
        
    def __init__(self, pysvn_status):
        # There is a potential problem here: I'm pretty sure that PySVN statuses
        # do NOT have translatable representations, so this will always come out
        # to be 'normal', 'modified' etc
        super(SVNStatus, self).__init__(
            # path=pysvn_status.path,
            content_status=str(pysvn_status.text_status),
            metadata_status=str(pysvn_status.prop_status))

class SVNStatus(Status):
    
    def __init__(self, pysvn_status):
        super(SVNStatus, self).__init__(
            pysvn_status.path,
            pysvn_status)


def summarise_statuses(top_dir, top_dir_status, statuses):
    """ Summarises statuses for directories.
    """    
    assert top_dir_status.path == top_dir, "Incorrect top level status"
    
    summary = status_unknown
    
    status_set = set([st.single for st in statuses])
    
    if not status_set:
        # This indicates a serious deviation from our expected API
        summary = status_error
    
    if status_complicated in status_set:
        summary = status_complicated
    
    elif own_status.single in ["added", "modified", "deleted"]:
        # These take priority over child statuses
        summary = own_status.single
    
    elif len(set(MODIFIED_CHILD_STATUSES) & status_set):
        summary = status_changed
    
    else:
        summary = own_status.single
    
    return StatusSummary(top_dir_status, summary)