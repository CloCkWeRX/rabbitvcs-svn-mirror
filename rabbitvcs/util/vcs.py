import os.path
from os.path import isdir, isfile, realpath, basename

import pysvn

from rabbitvcs.util.log import Log
log = Log("rabbitvcs.util.vcs")


#: A list of statuses which count as modified (for a directory) in 
#: TortoiseSVN emblem speak.
MODIFIED_STATUSES = [
    "added",
    "deleted",
    "replaced",
    "modified",
    "missing"
]

def condense_statuses(path, statuses):
    
    status = "unknown"
    
    status_set = set([statuses[other_path] for other_path in statuses.keys()])
    
    if not status_set:
        # This indicates a serious deviation from our expected API
        status = "error"
    
    elif "error" in status_set:
        status = "error"

    # We need to take special care of directories
    elif isdir(path):
        # These statuses take precedence.
        if "conflicted" in status_set:
            status = "conflicted"
        elif "obstructed" in status_set:
            status = "obstructed"
        
        # The following statuses take precedence over the status
        # of children.
        elif (statuses.has_key(path) and 
                statuses[path] in ["added", "modified", "deleted"]):
            status = statuses[path]
        
        # A directory should have a modified status when any of its children
        # have a certain status (see modified_statuses above). Jason thought up 
        # of a nifty way to do this by using sets and the bitwise AND operator (&).
        elif len(set(MODIFIED_STATUSES) & status_set):
            status = "modified"
            
        elif statuses.has_key(path):
            status = statuses[path]
    
    # If we're not a directory we end up here.
    elif statuses.has_key(path):
        status = statuses[path]
    
    else:
        status = "normal"
        
    return status

def summarize_status_pair(path, statuses):
    
    text_status = "unknown"
    prop_status = "unknown"
    
    text_statuses = {}
    prop_statuses = {}
    
    for other_path in statuses.keys():
        text_statuses[other_path] = statuses[other_path]["text_status"]
        prop_statuses[other_path] = statuses[other_path]["prop_status"]
    
    # If no statuses are returned but we do have a workdir_manager
    # it means that an error occured, most likely a working copy
    # administration area (.svn directory) went missing but it could
    # be pretty much anything.
    if not statuses: 
        # FIXME: figure out a way to make only the directory that
        # is missing display conflicted and the rest unknown.
        text_status = "error"
        prop_status = "error"
    
    else:
        text_status = condense_statuses(path, text_statuses)
        prop_status = condense_statuses(path, prop_statuses)
    
    return {path:
            {"text_status": text_status,
             "prop_status": prop_status}}

def make_single_status(statuses):
    """
    Given a text_status and a prop_status, simplify to a single status.
    """
        
    # Text statuses take priority
    single = statuses["text_status"]
    if single == "normal":
        single = statuses["prop_status"]
        if single == "none":
            single = "normal"
            
    return single

def summarize_status_pair_list(path, statuses):
    
    status_dict = {}
    
    for other_path, text_status, prop_status in statuses:
        status_dict[other_path] = {"text_status" : text_status,
                                   "prop_status" : prop_status}
        
    return summarize_status_pair(path, status_dict)

def summarize_status(path, statuses):
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
    summarised = summarize_status_pair(path, statuses)
    
    summary = make_single_status(summarised[path])
    
    return summary

def is_working_copy(path):
    vcs_client = pysvn.Client()

    if os.path.islink(path):
        path = os.path.realpath(path) 

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
    
    if os.path.islink(path):
        path = os.path.realpath(path) 
    
    if is_working_copy(path):
        return True
    else:
        # info will return nothing for an unversioned file inside a working copy
        vcs_client = pysvn.Client()
        if (is_working_copy(os.path.split(path)[0]) and
                vcs_client.info(path)): 
            return True
            
        return False