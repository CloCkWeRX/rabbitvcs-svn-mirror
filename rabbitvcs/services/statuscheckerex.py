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
import os

import rabbitvcs.vcs
import rabbitvcs.vcs.status

from rabbitvcs import gettext
_ = gettext.gettext

from rabbitvcs.util.log import Log
log = Log("rabbitvcs.services.statuschecker")

# from rabbitvcs.services.checkers.simplechecker import StatusChecker
from rabbitvcs.services.checkers.loopedchecker import StatusChecker

class StatusCheckerEx():
    """ A class for performing status checks. """
    
    # All subclasses should override this! This is to be displayed in the
    # settings dialog
    CHECKER_NAME = _("Simple status checker")
    
    def __init__(self):
        """ Initialises status checker. Obviously. """
        self.checker = StatusChecker()

    def check_status(self, path, recurse, summary, *args, **kwargs):
        """ Performs a status check, blocking until the check is done.
        """
        path_status = self.checker.check_status(path, recurse, summary)
        return path_status
    
    def extra_info(self):
        pid1 = self.checker.get_extra_PID()
        mypid = os.getpid()
        return [
                (_("DBUS service memory usage"),
                    "%s KB" % rabbitvcs.util.helper.process_memory(mypid)),
                (_("Checker subprocess memory usage"),
                    "%s KB" % rabbitvcs.util.helper.process_memory(pid1)),
                (_("Checker subprocess PID"), str(pid1)),
                ]
    
    def get_memory_usage(self):
        """ Returns any additional memory of any subprocesses used by this
        checker. In other words, DO NOT return the memory usage of THIS process! 
        """
        return self.checker.get_memory_usage()        

    
    def quit(self):
        # We will exit when the main process does
        self.checker.quit()