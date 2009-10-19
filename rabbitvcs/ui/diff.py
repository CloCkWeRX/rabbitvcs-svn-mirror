#
# This is an extension to the Nautilus file manager to allow better 
# integration with the Subversion source control system.
# 
# Copyright (C) 2006-2008 by Jason Field <jason@jasonfield.com>
# Copyright (C) 2007-2008 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2008-2008 by Adam Plumb <adamplumb@gmail.com>
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

import pygtk
import gobject
import gtk
import os
import tempfile

from rabbitvcs import TEMP_DIR_PREFIX
from rabbitvcs.ui import InterfaceNonView
from rabbitvcs.lib.vcs import create_vcs_instance
import rabbitvcs.lib.helper
from rabbitvcs.ui.dialog import MessageBox

from rabbitvcs import gettext
_ = gettext.gettext

class Diff(InterfaceNonView):
    def __init__(self, path1, revision1=None, path2=None, revision2=None):
        InterfaceNonView.__init__(self)

        self.path1 = path1
        self.revision1 = revision1
        self.path2 = path2
        self.revision2 = revision2

        self.temp_dir = tempfile.mkdtemp(prefix=TEMP_DIR_PREFIX)

        if path2 is None:
            self.path2 = path1

class SVNDiff(Diff):
    def __init__(self, path1, revision1=None, path2=None, revision2=None):
        Diff.__init__(self, path1, revision1, path2, revision2)
        vcs = create_vcs_instance()
        
        if self.revision1 is None:
            r1 = vcs.revision("base")
        elif self.revision1 == "HEAD":
            r1 = vcs.revision("head")
        else:
            r1 = vcs.revision("number", number=self.revision1)

        if self.revision2 is None:
            r2 = vcs.revision("working")
        elif self.revision2 == "HEAD":
            r2 = vcs.revision("head")
        else:
            r2 = vcs.revision("number", number=self.revision2)

        diff_text = vcs.diff(
            self.temp_dir,
            self.path1,
            r1,
            self.path2,
            r2
        )
        
        if diff_text == "":
            MessageBox(_("There are no differences"))
        else:
            fh = tempfile.mkstemp("rabbitvcs")
            os.write(fh[0], diff_text)
            os.close(fh[0])
            rabbitvcs.lib.helper.open_item(fh[1])

def parse_path_revision_string(pathrev):
    index = pathrev.rfind("@")
    if index == -1:
        return (pathrev,None)
    else:
        return (pathrev[0:index], pathrev[index+1:])

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, args) = main()
    
    pathrev1 = parse_path_revision_string(args.pop(0))
    pathrev2 = (None, None)
    if len(args) > 0:
        pathrev2 = parse_path_revision_string(args.pop(0))

    SVNDiff(pathrev1[0], pathrev1[1], pathrev2[0], pathrev2[1])
