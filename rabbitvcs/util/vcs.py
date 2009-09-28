import os.path
from os.path import isdir, isfile, realpath, basename

import pysvn

#: A list of statuses which count as modified (for a directory) in 
#: TortoiseSVN emblem speak.
MODIFIED_STATUSES = [
    "added",
    "deleted",
    "replaced",
    "modified",
    "missing"
]

def get_summarized_status(path, statuses):
    """
    This is a helper function to figure out the textual representation 
    for a set of statuses. In TortoiseSVN speak a directory is
    regarded as modified when any of its children are either added, 
    deleted, replaced, modified or missing so you can quickly see if 
    your working copy has local changes.
    
    This function accounts for both file and property statuses.
    
    @type   path:   list
    @param  path:   A dict of {path : {"text_status" : [...],
                                       "prop_status" : [...]} entries
    """
    
    text_statuses = set([statuses[key]["text_status"] for key in statuses.keys()])
    prop_statuses = set([statuses[key]["prop_status"] for key in statuses.keys()])
    
    all_statuses = text_statuses | prop_statuses
    
    # If no statuses are returned but we do have a workdir_manager
    # it means that an error occured, most likely a working copy
    # administration area (.svn directory) went missing but it could
    # be pretty much anything.
    if not statuses: 
        # FIXME: figure out a way to make only the directory that
        # is missing display conflicted and the rest unknown.
        return "error"

    if "client_error" in all_statuses:
        return "error"

    # We need to take special care of directories
    if isdir(path):
        # These statuses take precedence.
        if "conflicted" in text_statuses: return "conflicted"
        if "obstructed" in text_statuses: return "obstructed"
        
        # The following statuses take precedence over the status
        # of children.
        if (statuses.has_key(path) and 
                statuses[path]["text_status"] in ["added", "modified", "deleted"]):
            return statuses[path]["text_status"]
        
        # A directory should have a modified status when any of its children
        # have a certain status (see modified_statuses above). Jason thought up 
        # of a nifty way to do this by using sets and the bitwise AND operator (&).
        if len(set(MODIFIED_STATUSES) & all_statuses):
            return "modified"
    
    # If we're not a directory we end up here.
    if statuses.has_key(path): return statuses[path]["text_status"]
    return "normal"

def is_working_copy(path):
    vcs_client = pysvn.Client()

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
                vcs_client.info(path) and
                isdir(os.path.join(path, ".svn"))):
            return True
        return False
    except Exception, e:
        return False
    
def is_in_a_or_a_working_copy(path):
    return is_working_copy(path) or is_working_copy(os.path.split(path)[0])

def is_versioned(path):
    if is_working_copy(path):
        return True
    else:
        # info will return nothing for an unversioned file inside a working copy
        vcs_client = pysvn.Client()
        if (is_working_copy(os.path.split(path)[0]) and
                vcs_client.info(path)): 
            return True
            
        return False
