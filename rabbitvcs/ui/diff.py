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
from shutil import rmtree
import tempfile

from rabbitvcs import TEMP_DIR_PREFIX
from rabbitvcs.ui import InterfaceNonView
import rabbitvcs.vcs
from rabbitvcs.ui.action import SVNAction
import rabbitvcs.util.helper

from rabbitvcs import gettext
_ = gettext.gettext

class Diff(InterfaceNonView):
    def __init__(self, path1, revision1=None, path2=None, revision2=None, 
            sidebyside=False):
        InterfaceNonView.__init__(self)

        self.vcs = rabbitvcs.vcs.VCS()

        self.path1 = path1
        self.path2 = path2
        self.sidebyside = sidebyside

        self.temp_dir = tempfile.mkdtemp(prefix=TEMP_DIR_PREFIX)

        if path2 is None:
            self.path2 = path1
                
    def launch(self):
        if self.sidebyside:
            self.launch_sidebyside_diff()
        else:
            self.launch_unified_diff()

    def _build_export_path(self, index, revision, path):
        dest = "/tmp/rabbitvcs-%s-%s-%s" % (str(index), str(revision), os.path.basename(path))
        if os.path.exists(dest):
            if os.path.isdir(dest):
                rmtree(dest, ignore_errors=True)
            else:
                os.remove(dest)

        return dest

class SVNDiff(Diff):
    def __init__(self, path1, revision1=None, path2=None, revision2=None,
            sidebyside=False):
        Diff.__init__(self, path1, revision1, path2, revision2, sidebyside)

        self.svn = self.vcs.svn()

        self.revision1 = self.get_revision_object(revision1, "base")
        self.revision2 = self.get_revision_object(revision2, "working")

        self.launch()

    def get_revision_object(self, value, default):
        # If value is a rabbitvcs Revision object, return it
        if hasattr(value, "is_revision_object"):
            return value
        
        # If value is None, use the default
        if value is None:
            return self.svn.revision(default)          

        # If the value is an integer number, return a numerical revision object
        # otherwise, a string revision value has been passed, use that as "kind"
        try:
            value = int(value)
            return self.svn.revision("number", value)
        except ValueError:
            # triggered when passed a string
            return self.svn.revision(value)

    def launch_unified_diff(self):
        """
        Launch diff as a unified diff in a text editor or .diff viewer
        
        """
        
        action = SVNAction(
            self.svn,
            notification=False,
            run_in_thread=False
        )
        
        diff_text = action.run_single(
            self.svn.diff,
            self.temp_dir,
            self.path1,
            self.revision1,
            self.path2,
            self.revision2
        )
        if diff_text is None:
            diff_text = ""

        fh = tempfile.mkstemp("-rabbitvcs-" + str(self.revision1) + "-" + str(self.revision2) + ".diff")
        os.write(fh[0], diff_text)
        os.close(fh[0])
        rabbitvcs.util.helper.open_item(fh[1])
        
    def launch_sidebyside_diff(self):
        """
        Launch diff as a side-by-side comparison using our comparison tool
        
        """

        action = SVNAction(
            self.svn,
            notification=False,
            run_in_thread=False
        )

        if os.path.exists(self.path1) and self.revision1.kind != "base":
            dest1 = self.path1
        else:
            dest1 = self._build_export_path(1, self.revision1, self.path1)
            action.run_single(
                self.svn.export, 
                self.path1, 
                dest1, 
                self.revision1
            )
            action.stop_loader()
    
        if os.path.exists(self.path2) and self.revision2.kind != "base":
            dest2 = self.path2
        else:
            dest2 = self._build_export_path(2, self.revision2, self.path2)
            action.run_single(
                self.svn.export, 
                self.path2, 
                dest2, 
                self.revision2
            )
            action.stop_loader()
    
        rabbitvcs.util.helper.launch_diff_tool(dest1, dest2)


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, args) = main([
        (["-s", "--sidebyside"], {
            "help":     _("View diff as side-by-side comparison"), 
            "action":   "store_true", 
            "default":  False
        })],
        usage="Usage: rabbitvcs diff [url1@rev1] [url2@rev2]"
    )
    
    pathrev1 = rabbitvcs.util.helper.parse_path_revision_string(args.pop(0))
    pathrev2 = (None, None)
    if len(args) > 0:
        pathrev2 = rabbitvcs.util.helper.parse_path_revision_string(args.pop(0))

    SVNDiff(pathrev1[0], pathrev1[1], pathrev2[0], pathrev2[1], sidebyside=options.sidebyside)
