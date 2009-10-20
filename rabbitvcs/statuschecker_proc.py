#
# Copyright (C) 2009 Jason Heeris <jason.heeris@gmail.com>
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
Convenience script for performing status checks in a separate process. This
script is NOT meant to be run from the command line - the results are sent over
stdout as a byte stream (ie. the pickled results of the status check).

At present the byte stream result of a pickle IS, in fact, ASCII data.
"""

import cPickle
import sys
from UserDict import UserDict

import pysvn

import rabbitvcs.util.locale

from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.statuschecker_proc")

PICKLE_PROTOCOL = cPickle.HIGHEST_PROTOCOL

def Main(path, recurse):
    """
    Perform a VCS status check on the given path (recursive as indicated). The
    results will be pickled and sent as a byte stream over stdout.
    """
    vcs_client = pysvn.Client()
    # NOTE: we cannot pickle status_list directly. It needs to be processed
    # here.
    try:
        status_list = vcs_client.status(path, recurse=recurse)
        statuses = [(status.path, str(status.text_status), str(status.prop_status)) 
                    for status in status_list]
    except Exception, e:
        statuses = [status_error(path)]
    
    cPickle.dump(statuses,
                 sys.stdout,
                 protocol=PICKLE_PROTOCOL)

def status_error(path):
    """
    Create a pysvn-like status object that indicates an error.
    """
    status = UserDict()
    status.path = path
    status.text_status = "error"
    status.prop_status = "error"
    return status

if __name__ == '__main__':
    # I have deliberately avoided rigourous input checking since this script is
    # only designed to be called from our extension code.
   
    rabbitvcs.util.locale.initialize_locale()

    # This may be problematic, because I'm not sure how pipes work if the locale
    # is different. I tried to use a pickle, but performance was terrible.
    path = unicode(sys.argv[1], "utf-8")
    recurse = (sys.argv[2] == "True")
    # (path, recurse) = cPickle.load(sys.stdin)
    
    log.debug("SCP path: %s" % path)
    
    Main(path, recurse)