import os.path
from os.path import isdir, isfile, realpath, basename

import pysvn

from rabbitvcs.util.log import Log
log = Log("rabbitvcs.util.vcs")

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