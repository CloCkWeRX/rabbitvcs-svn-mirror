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

from UserDict import UserDict

import pysvn

from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.services.statuschecker")

def status_error(path):
    """
    Create a pysvn-like status object that indicates an error.
    """
    status = (path, "error", "error")
    return status

class StatusChecker():
    
    def __init__(self):
        self.vcs_client = pysvn.Client()

    def check_status(self, path, recurse):
        log.debug("Checking: %s" % path)
        try:
            status_list = self.vcs_client.status(path, recurse=recurse)
            statuses = [(status.path, str(status.text_status), str(status.prop_status)) 
                        for status in status_list]
        except Exception, e:
            statuses = [status_error(path)]
        
        return statuses
    