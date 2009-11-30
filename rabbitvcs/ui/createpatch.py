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

import os
import thread

import gnomevfs
import pygtk
import gobject
import gtk
import os
import tempfile
import shutil

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.action import VCSAction
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.lib
import rabbitvcs.lib.helper
from rabbitvcs.lib.helper import get_common_directory
from rabbitvcs.lib.log import Log
from rabbitvcs.ui.commit import Commit

log = Log("rabbitvcs.ui.createpatch")

from rabbitvcs import gettext
_ = gettext.gettext

gtk.gdk.threads_init()

class CreatePatch(Commit):
    """
    Provides a user interface for the user to create a Patch file
    
    """

    def __init__(self, paths, base_dir):
        """
        
        @type  paths:   list of strings
        @param paths:   A list of local paths.
        
        """
        InterfaceView.__init__(self, "commit", "Commit")

        # Modify the Commit window to what we need for Create Patch
        window = self.get_widget("Commit")
        window.set_title(_("Create Patch"))
        window.resize(640, 400)
        self.get_widget("commit_to_box").hide()
        self.get_widget("add_message_box").hide()

        self.paths = paths
        self.base_dir = base_dir
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        self.common = rabbitvcs.lib.helper.get_common_directory(paths)
        self.activated_cache = {}

        if not self.vcs.get_versioned_path(self.common):
            rabbitvcs.ui.dialog.MessageBox(_("The given path is not a working copy"))
            raise SystemExit()

        self.files_table = rabbitvcs.ui.widget.Table(
            self.get_widget("files_table"),
            [gobject.TYPE_BOOLEAN, rabbitvcs.ui.widget.TYPE_PATH, 
                gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [rabbitvcs.ui.widget.TOGGLE_BUTTON, _("Path"), _("Extension"), 
                _("Text Status"), _("Property Status")],
            filters=[{
                "callback": rabbitvcs.ui.widget.path_filter,
                "user_data": {
                    "base_dir": base_dir,
                    "column": 1
                }
            }],
        )
        self.files_table.allow_multiple()
        
        self.items = None
        self.initialize_items()

    #
    # Helper functions
    # 

    def choose_patch_path(self):
        path = ""
        
        dialog = gtk.FileChooserDialog(
            _("Create Patch"),
            None,
            gtk.FILE_CHOOSER_ACTION_SAVE,(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                          gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_current_folder_uri(
            gnomevfs.get_uri_from_local_path(get_common_directory(self.paths))
        )
        response = dialog.run()
        
        if response == gtk.RESPONSE_OK:
            path = dialog.get_filename()
            
        dialog.destroy()
        
        return path

    #
    # Event handlers
    #
        
    def on_ok_clicked(self, widget, data=None):
        items = self.files_table.get_activated_rows(1)
        self.hide()
        
        if len(items) == 0:
            self.close()
            return
        
        path = self.choose_patch_path()
        if not path:
            self.close()
            return
      
        ticks = len(items)*2
        self.action = rabbitvcs.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.set_pbar_ticks(ticks)
        self.action.append(self.action.set_header, _("Create Patch"))
        self.action.append(self.action.set_status, _("Creating Patch File..."))
        
        def create_patch_action(patch_path, patch_items, base_dir):
            fileObj = open(patch_path,"w")
            
            # PySVN takes a path to create its own temp files...
            temp_dir = tempfile.mkdtemp(prefix=rabbitvcs.TEMP_DIR_PREFIX)
            
            os.chdir(base_dir)
           
            # Add to the Patch file only the selected items
            for item in patch_items:
                rel_path = rabbitvcs.lib.helper.get_relative_path(base_dir, item)
                diff_text = self.vcs.diff(temp_dir, rel_path)
                fileObj.write(diff_text)
    
            fileObj.close()            
        
            # Note: if we don't want to ignore errors here, we could define a
            # function that logs failures.
            shutil.rmtree(temp_dir, ignore_errors = True)
        
        self.action.append(create_patch_action, path, items, self.common)
        
        self.action.append(self.action.set_status, _("Patch File Created"))
        self.action.append(self.action.finish)
        self.action.start()
        
        # TODO: Open the diff file (meld is going to add support in a future version :()
        # rabbitvcs.lib.helper.launch_diff_tool(path)

if __name__ == "__main__":
    from rabbitvcs.ui import main, BASEDIR_OPT
    (options, paths) = main(
        [BASEDIR_OPT],
        usage="Usage: rabbitvcs createpatch [path1] [path2] ..."
    )
        
    window = CreatePatch(paths, options.base_dir)
    window.register_gtk_quit()
    gtk.main()
