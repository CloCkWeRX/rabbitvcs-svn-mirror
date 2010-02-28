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
Very simple status checking class. Useful when you can't get any of the others
to work, or you need to prototype things. 
"""

import rabbitvcs.lib.vcs

from rabbitvcs import gettext
_ = gettext.gettext

from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.services.statuschecker")

def status_error(path):
    """
    Create a pysvn-like status object that indicates an error.
    """
    status = (path, "error", "error")
    return status

class StatusChecker():
    """ A class for performing status checks. """
    
    # All subclasses should override this! This is to be displayed in the
    # settings dialog
    CHECKER_NAME = _("Simple status checker")
    
    def __init__(self):
        """ Initialises status checker. Obviously. """
        self.vcs_client = rabbitvcs.lib.vcs.create_vcs_instance()

    def check_status(self, path, recurse, summary):
        """ Performs a status check, blocking until the check is done.
        
        The returned status data can have two forms. If a summary is requested,
        it is:
        
            (status list, summarised dict)
            
        ...where the list is of the form
        
            [(path1, text_status1, prop_status1), (path2, ...), ...]
            
        ...and the dict is:
        
            {path: {"text_status": text_status,
                    "prop_status": prop_status}}
        
        If no summary is requested, the return value is just the status list.
        """
        
        try:
            status_list = self.vcs_client.status(path, recurse=recurse)
            statuses = [(status.path,
                         str(status.text_status),
                         str(status.prop_status)) 
                        for status in status_list]
        except Exception:
            statuses = [status_error(path)]
        
        if summary:
            statuses = (statuses,
                        rabbitvcs.util.vcs.summarize_status_pair_list(path,
                                                                      statuses))

        return statuses
    