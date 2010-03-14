# These are the statuses that we might represent with icons
status_unchanged = 'unchanged'
status_changed = 'changed'
status_added = 'added'
status_deleted = 'deleted'
status_ignored = 'ignored'
status_read_only = 'read-only'
status_locked = 'locked'
# Anything we display with that exclamation mark icon
status_complicated = 'complicated'
status_calculating = 'calculating'
status_error = 'error'
 
class GenericStatus:
 
    clean_statuses = ['unchanged']
 
    content_status_map = None
    metadata_status_map = None
 
    def __init__(self, content_status, metadata_status, vcs_type = None):
        # vcs_type may be None for things like error, calculating, etc
        self.vcs = vcs_type
        self.content = vcs_content_status
        self.metadata = vcs_metadata_status
        self.single = self._make_single_status()
 
    def _make_single_status(self):
        """
        Given our text_status and a prop_status, simplify to a single "simple"
        status. If we don't know how to simplify our particular combination of
        status, call it an error.
        """     
        # Content status dominates
        single = self.simple_content_status() or status_error
        if single in GenericStatus.clean_statuses:
            single = self.simple_metadata_status() or status_error

    def simple_content_status(self):
        if self.content_status_map:
            return self.content_status_map.get(self.content)
        
    def simple_metadata_status(self):
        if self.metadata_status_map:
            return self.metadata_status_map.get(self.metadata)