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

import os.path
from time import sleep

import gtk

from rabbitvcs.ui.action import VCSAction
from rabbitvcs.lib.vcs import create_vcs_instance
from rabbitvcs.lib.log import Log
from rabbitvcs import gettext
from rabbitvcs.lib.settings import SettingsManager
import rabbitvcs.lib.helper

log = Log("rabbitvcs.ui.commit")
_ = gettext.gettext

settings = SettingsManager()

import rabbitvcs.services
from rabbitvcs.services.cacheservice import StatusCacheStub as StatusCache

SEPARATOR = u'\u2015' * 10

class GtkContextMenu:
    """
    Provides a standard Gtk Context Menu class used for all context menus
    in gtk dialogs/windows.
    
    """
    def __init__(self, structure, items):
        """
        @param  structure: Menu structure
        @type   structure: list
        
        @param  items: Menu items
        @type   items: dict
        
        Note on "structure". The menu structure is defined in a list of tuples 
        of two elements each.  The first element is a key that matches a key in 
        "items".  The second element is either None (if there is no submenu) or 
        a list of tuples if there is a submenu.  The submenus are generated 
        recursively.  FYI, this is a list of tuples so that we retain the 
        desired menu item order (dicts do not retain order)
        
            Example:
            [
                (key, [
                    (submenu_key, None),
                    (submenu_key, None)
                ]),
                (key, None),
                (key, None)
            ]

        Note on "items".  This is a dict that looks like the following.
        
            {
                "identifier": "RabbitVCS::Identifier",
                "label": "",
                "tooltip": "",
                "icon": "",
                "signals": {
                    "activate": {
                        "callback": None,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": (lambda: True),
                    "args": None
                }
            }
            
        """
        self.view = gtk.Menu()
        self.num_items = 0
        is_last = False
        is_first = True
        index = 0
        length = len(structure)
        for key,submenu_keys in structure:
            is_last = (index + 1 == length)
            
            if key not in items:
                continue
            
            item = items[key]

            # If the item is a separator, don't show it if this is the first
            # or last item, or if the previous item was a separator.
            if (item["label"] == SEPARATOR and
                    (is_first or is_last or previous_label == SEPARATOR)):
                index += 1
                continue
        
            condition = item["condition"]
            if condition.has_key("args"):
                if condition["callback"](condition["args"]) is False:
                    continue
            else:
                if condition["callback"]() is False:
                    continue
            
            action = gtk.Action(item["label"], item["label"], None, None)
            
            if item.has_key("icon") and item["icon"] is not None:
                action.set_icon_name(item["icon"])
    
            menuitem = action.create_menu_item()
            if item.has_key("signals") and item["signals"] is not None:
                for signal, info in item["signals"].items():
                    menuitem.connect(signal, info["callback"], info["args"])

            # Making the seperator insensitive makes sure nobody
            # will click it accidently.
            if (item["label"] == rabbitvcs.lib.contextmenu.SEPARATOR): 
                menuitem.set_property("sensitive", False)
            
            if submenu_keys is not None:
                submenu = GtkContextMenu(submenu_keys, items)
                menuitem.set_submenu(submenu.get_widget())
            
            self.num_items += 1
            self.view.add(menuitem)

            # The menu item above has just been added, so we can note that
            # we're no longer on the first menu item.  And we'll keep
            # track of this item so the next iteration can test if it should
            # show a separator or not
            is_first = False
            previous_label = item["label"]
            index += 1
        
    def show(self, event):        
        self.view.show_all()
        self.view.popup(None, None, None, event.button, event.time)

    def get_num_items(self):
        return self.num_items
        
    def get_widget(self):
        return self.view

class GtkContextMenuCaller:
    """
    Provides an abstract interface to be inherited by dialogs/windows that call
    a GtkContextMenu.  Allows us to have a standard common set of methods we can
    call from the callback object.
    """
    
    def __init__(self):
        pass
    
    def reload_treeview(self):
        pass

    def reload_treeview_threaded(self): 
        pass

class ContextMenuCallbacks:
    """
    The base class for context menu callbacks.  This is inheritied by
    sub-classes.
    """
    def __init__(self, caller, base_dir, vcs_client, paths=[]):
        """        
        @param  caller: The calling object
        @type   caller: RabbitVCS extension
        
        @param  base_dir: The curent working directory
        @type   base_dir: string

        @param  vcs_client: The vcs client to be used
        @type   vcs_client: rabbitvcs.lib.vcs.create_vcs_instance()
        
        @param  paths: The selected paths
        @type   paths: list
        
        """  
        self.caller = caller
        self.base_dir = base_dir
        self.vcs_client = vcs_client
        self.paths = paths
        
    def debug_shell(self, widget, data1=None, data2=None):
        """
        
        Open up an IPython shell which shares the context of the extension.
        
        See: http://ipython.scipy.org/moin/Cookbook/EmbeddingInGTK
        
        """
        import gtk
        from rabbitvcs.debug.ipython_view import IPythonView
        
        window = gtk.Window()
        window.set_size_request(750,550)
        window.set_resizable(True)
        window.set_position(gtk.WIN_POS_CENTER)
        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        ipython_view = IPythonView()
        ipython_view.updateNamespace(locals())
        ipython_view.set_wrap_mode(gtk.WRAP_CHAR)
        ipython_view.show()
        scrolled_window.add(ipython_view)
        scrolled_window.show()
        window.add(scrolled_window)
        window.show()
    
    def refresh_status(self, widget, data1=None, data2=None):
        """
        Refreshes an item status, which is actually just invalidate.
        """
        
        self.debug_invalidate(menu_item)
    
    def debug_revert(self, widget, data1=None, data2=None):
        client = pysvn.Client()
        for path in self.paths:
            client.revert(path, recurse=True)
        
    def debug_invalidate(self, widget, data1=None, data2=None):
        rabbitvcs_extension = self.caller
        nautilusVFSFile_table = rabbitvcs_extension.nautilusVFSFile_table
        for path in self.paths:
            log.debug("callback_debug_invalidate() called for %s" % path)
            if path in nautilusVFSFile_table:
                nautilusVFSFile_table[path].invalidate_extension_info()
    
    def debug_add_emblem(self, widget, data1=None, data2=None):
        def add_emblem_dialog():
            from subprocess import Popen, PIPE
            command = ["zenity", "--entry", "--title=RabbitVCS", "--text=Emblem to add:"]
            emblem = Popen(command, stdout=PIPE).communicate()[0].replace("\n", "")
            
            rabbitvcs_extension = self.caller
            nautilusVFSFile_table = rabbitvcs_extension.nautilusVFSFile_table
            for path in self.paths:
                if path in nautilusVFSFile_table:
                    nautilusVFSFile_table[path].add_emblem(emblem)
            return False
            
        gobject.idle_add(add_emblem_dialog)
    
    # End debugging callbacks

    def checkout(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("checkout", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)
    
    def update(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("update", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def commit(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("commit", ["--base-dir=" + self.base_dir] + self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def add(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("add", self.paths)
        # self.caller.rescan_after_process_exit(proc, self.paths)
        self.caller.execute_after_process_exit(proc)

    def checkmods(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("checkmods", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def delete(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("delete", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def revert(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("revert", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)

    def diff(self, widget, data1=None, data2=None):
        rabbitvcs.lib.helper.launch_diff_tool(*self.paths)

    def changes(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("changes", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)
    
    def show_log(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("log", self.paths)
        self.caller.execute_after_process_exit(proc)

    def rename(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("rename", self.paths)
        self.caller.execute_after_process_exit(proc)

    def createpatch(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("createpatch", self.paths)
        self.caller.execute_after_process_exit(proc)
    
    def applypatch(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("applypatch", self.paths)
        self.caller.rescan_after_process_exit(proc, self.paths)
    
    def properties(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("properties", self.paths)
        self.caller.execute_after_process_exit(proc)

    def about(self, widget, data1=None, data2=None):
        rabbitvcs.lib.helper.launch_ui_window("about")
        
    def settings(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("settings")
        self.caller.reload_settings(proc)

    def ignore_by_filename(self, widget, data1=None, data2=None):
        for path in self.paths:
            prop_name = self.vcs_client.PROPERTIES["ignore"]
            prop_value = os.path.basename(path)
            self.vcs_client.propset(
                self.base_dir,
                prop_name,
                prop_value
            )

    def ignore_by_file_extension(self, widget, data1=None, data2=None):
        prop_name = self.vcs_client.PROPERTIES["ignore"]
        prop_value = "*%s" % rabbitvcs.lib.helper.get_file_extension(self.paths[0])            
        self.vcs_client.propset(
            self.base_dir,
            prop_name,
            prop_value,
            recurse=True
        )

    def lock(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("lock", self.paths)
        self.caller.execute_after_process_exit(proc)

    def branch(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("branch", self.paths)
        self.caller.execute_after_process_exit(proc)

    def switch(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("switch", self.paths)
        self.caller.execute_after_process_exit(proc)

    def merge(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("merge", self.paths)
        self.caller.execute_after_process_exit(proc)

    def _import(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("import", self.paths)
        self.caller.execute_after_process_exit(proc)

    def export(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("export", self.paths)
        self.caller.execute_after_process_exit(proc)

    def updateto(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("updateto", self.paths)
        self.caller.execute_after_process_exit(proc)
    
    def resolve(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("resolve", self.paths)
        self.caller.execute_after_process_exit(proc)
        
    def annotate(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("annotate", self.paths)
        self.caller.execute_after_process_exit(proc)

    def unlock(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("unlock", self.paths)
        self.caller.execute_after_process_exit(proc)
        
    def create_repository(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("create", self.paths)
        self.caller.execute_after_process_exit(proc)
    
    def relocate(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("relocate", self.paths)
        self.caller.execute_after_process_exit(proc)

    def cleanup(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("cleanup", self.paths)
        self.caller.execute_after_process_exit(proc)

    def restore(self, widget, data1=None, data2=None):
        proc = rabbitvcs.lib.helper.launch_ui_window("update", self.paths)
        self.caller.execute_after_process_exit(proc)

    def _open(self, widget, data1=None, data2=None):
        pass
    
    def browse_to(self, widget, data1=None, data2=None):
        pass

class ContextMenuConditions:
    """
    Provides a standard interface to checking conditions for menu items.
    
    This class should never be instantied directly, rather the narrowly defined
    FileManagerContextMenuConditions and GtkFilesContextMenuConditions classes
    should be called.
    
    """    
    def __init__(self):
        pass

    def generate_path_dict(self, paths):
        self.path_dict = {}
        self.path_dict["length"] = len(paths)

        checks = {
            "is_dir"                        : os.path.isdir,
            "is_file"                       : os.path.isfile,
            "exists"                        : os.path.exists,
            "is_working_copy"               : self.vcs_client.is_working_copy,
            "is_in_a_or_a_working_copy"     : self.vcs_client.is_in_a_or_a_working_copy,
            "is_versioned"                  : self.vcs_client.is_versioned,
            "is_normal"                     : lambda path: self.statuses[path]["text_status"] == "normal" and self.statuses[path]["prop_status"] == "normal",
            "is_added"                      : lambda path: self.statuses[path]["text_status"] == "added",
            "is_modified"                   : lambda path: self.statuses[path]["text_status"] == "modified" or self.statuses[path]["prop_status"] == "modified",
            "is_deleted"                    : lambda path: self.statuses[path]["text_status"] == "deleted",
            "is_ignored"                    : lambda path: self.statuses[path]["text_status"] == "ignored",
            "is_locked"                     : lambda path: self.statuses[path]["text_status"] == "locked",
            "is_missing"                    : lambda path: self.statuses[path]["text_status"] == "missing",
            "is_conflicted"                 : lambda path: self.statuses[path]["text_status"] == "conflicted",
            "is_obstructed"                 : lambda path: self.statuses[path]["text_status"] == "obstructed",
            "has_unversioned"               : lambda path: "unversioned" in self.text_statuses,
            "has_added"                     : lambda path: "added" in self.text_statuses,
            "has_modified"                  : lambda path: "modified" in self.text_statuses or "modified" in self.prop_statuses,
            "has_deleted"                   : lambda path: "deleted" in self.text_statuses,
            "has_ignored"                   : lambda path: "ignored" in self.text_statuses,
            "has_locked"                    : lambda path: "locked" in self.text_statuses,
            "has_missing"                   : lambda path: "missing" in self.text_statuses,
            "has_conflicted"                : lambda path: "conflicted" in self.text_statuses,
            "has_obstructed"                : lambda path: "obstructed" in self.text_statuses
        }

        # Each path gets tested for each check
        # If a check has returned True for any path, skip it for remaining paths
        for path in paths:
            for key, func in checks.items():
                if not self.statuses.has_key(path):
                    self.path_dict[key] = False
                elif key not in self.path_dict or self.path_dict[key] is not True:
                    self.path_dict[key] = func(path)

    def checkout(self, data=None):
        return (self.path_dict["length"] == 1 and
                self.path_dict["is_dir"] and
                not self.path_dict["is_working_copy"])
                
    def update(self, data=None):
        return (self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"] and
                not self.path_dict["is_added"])
                        
    def commit(self, data=None):
        if self.path_dict["is_in_a_or_a_working_copy"]:
            if (self.path_dict["is_added"] or
                    self.path_dict["is_modified"] or
                    self.path_dict["is_deleted"] or
                    not self.path_dict["is_versioned"]):
                return True
            elif (self.path_dict["is_dir"]):
                return True
        return False
        
    def diff(self, data=None):
        if self.path_dict["length"] == 2:
            return True
        elif (self.path_dict["length"] == 1 and
                self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_modified"]):
            return True        
        return False

    def changes(self, data=None):
        return (self.path_dict["is_in_a_or_a_working_copy"] and
            self.path_dict["is_versioned"] and 
            self.path_dict["length"] in (1,2))
        
    def show_log(self, data=None):
        return (self.path_dict["length"] == 1 and
                self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"] and
                not self.path_dict["is_added"])
        
    def add(self, data=None):
        if (self.path_dict["is_dir"] and
                self.path_dict["is_in_a_or_a_working_copy"]):
            return True
        elif (not self.path_dict["is_dir"] and
                self.path_dict["is_in_a_or_a_working_copy"] and
                not self.path_dict["is_versioned"]):
            return True
        return False

    def checkmods(self, data=None):
        return (self.path_dict["is_working_copy"] or
            self.path_dict["is_versioned"])

    def add_to_ignore_list(self, data=None):
        return self.path_dict["is_versioned"]
        
    def rename(self, data=None):
        return (self.path_dict["length"] == 1 and
                self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"] and
                not self.path_dict["is_added"])
        
    def delete(self, data=None):
        # FIXME: This should be False for the top-level WC folder
        return self.path_dict["is_versioned"]
        
    def revert(self, data=None):
        if self.path_dict["is_in_a_or_a_working_copy"]:
            if (self.path_dict["is_added"] or
                    self.path_dict["is_modified"] or
                    self.path_dict["is_deleted"]):
                return True
            else:
                if (self.path_dict["is_dir"] and
                        (self.path_dict["has_added"] or
                        self.path_dict["has_modified"] or
                        self.path_dict["has_deleted"] or
                        self.path_dict["has_missing"])):
                    return True
        return False
        
    def annotate(self, data=None):
        return (self.path_dict["length"] == 1 and
                not self.path_dict["is_dir"] and
                self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"] and
                not self.path_dict["is_added"])
        
    def properties(self, data=None):
        return (self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"])

    def createpatch(self, data=None):
        if self.path_dict["is_in_a_or_a_working_copy"]:
            if (self.path_dict["is_added"] or
                    self.path_dict["is_modified"] or
                    self.path_dict["is_deleted"] or
                    not self.path_dict["is_versioned"]):
                return True
            elif (self.path_dict["is_dir"] and
                    (self.path_dict["has_added"] or
                    self.path_dict["has_modified"] or
                    self.path_dict["has_deleted"] or
                    self.path_dict["has_unversioned"] or
                    self.path_dict["has_missing"])):
                return True
        return False
    
    def applypatch(self, data=None):
        if self.path_dict["is_in_a_or_a_working_copy"]:
            return True
        return False
    
    def add_to_ignore_list(self, data=None):
        return (self.path_dict["is_in_a_or_a_working_copy"] and
                not self.path_dict["is_versioned"])

    def ignore_by_filename(self, data=None):
        return (self.path_dict["is_in_a_or_a_working_copy"] and
                not self.path_dict["is_versioned"])
    
    def ignore_by_file_extension(self, data=None):
        return (self.path_dict["is_in_a_or_a_working_copy"] and
                not self.path_dict["is_versioned"])

    def lock(self, data=None):
        return self.path_dict["is_versioned"]

    def branch(self, data=None):
        return self.path_dict["is_versioned"]

    def relocate(self, data=None):
        return self.path_dict["is_versioned"]

    def switch(self, data=None):
        return self.path_dict["is_versioned"]

    def merge(self, data=None):
        return self.path_dict["is_versioned"]

    def _import(self, data=None):
        return (self.path_dict["length"] == 1 and
                not self.path_dict["is_in_a_or_a_working_copy"])

    def export(self, data=None):
        return (self.path_dict["length"] == 1)
   
    def update_to(self, data=None):
        return (self.path_dict["length"] == 1 and
                self.path_dict["is_versioned"] and 
                self.path_dict["is_in_a_or_a_working_copy"])
    
    def resolve(self, data=None):
        return (self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"] and
                self.path_dict["is_conflicted"])
            
    def create(self, data=None):
        return (self.path_dict["length"] == 1 and
                not self.path_dict["is_in_a_or_a_working_copy"])

    def unlock(self, data=None):
        return (self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"] and
                self.path_dict["has_locked"])

    def cleanup(self, data=None):
        return self.path_dict["is_versioned"]

    def browse_to(self, data=None):
        return self.path_dict["exists"]
    
    def _open(self, data=None):
        return self.path_dict["is_file"]
    
    def restore(self, data=None):
        return self.path_dict["has_missing"]

    def update(self, data=None):
        return (self.path_dict["is_in_a_or_a_working_copy"] and
                self.path_dict["is_versioned"] and
                not self.path_dict["is_added"])

class GtkFilesContextMenuCallbacks(ContextMenuCallbacks):
    """
    A callback class created for GtkFilesContextMenus.  This class inherits from
    the standard ContextMenuCallbacks class and overrides some methods.
    """
    def __init__(self, caller, base_dir, vcs_client, paths=[]):
        """        
        @param  caller: The calling object
        @type   caller: RabbitVCS extension
        
        @param  base_dir: The curent working directory
        @type   base_dir: string

        @param  vcs_client: The vcs client to be used
        @type   vcs_client: rabbitvcs.lib.vcs.create_vcs_instance()
        
        @param  paths: The selected paths
        @type   paths: list
        
        """  
        ContextMenuCallbacks.__init__(self, caller, base_dir, vcs_client, paths)

    def _open(self, widget, data1=None, data2=None):
        for path in self.paths:
            rabbitvcs.lib.helper.open_item(path)
    
    def browse_to(self, widget, data1=None, data2=None):
        rabbitvcs.lib.helper.browse_to_item(self.paths[0])

    def add(self, widget, data1=None, data2=None):
        self.action = VCSAction(
            self.vcs_client,
            notification=False
        )
        
        for path in self.paths:
            self.action.append(self.vcs_client.add, path)
        
        self.action.append(self.caller.reload_treeview_threaded)
        self.action.start()

    def delete(self, widget, data1=None, data2=None):
        if len(self.paths) > 0:
            from rabbitvcs.ui.delete import Delete
            Delete(self.paths).start()
            sleep(1) # sleep so the items can be fully deleted before init
            self.caller.reload_treeview()

    def ignore_by_filename(self, widget, data1=None, data2=None):
        for path in self.paths:
            prop_name = self.vcs_client.PROPERTIES["ignore"]
            prop_value = os.path.basename(path)
            self.vcs_client.propset(
                self.base_dir,
                prop_name,
                prop_value
            )
        
        self.caller.reload_treeview()

    def ignore_by_file_extension(self, widget, data1=None, data2=None):
        for path in self.paths:
            prop_name = self.vcs_client.PROPERTIES["ignore"]
            prop_value = "*%s" % rabbitvcs.lib.helper.get_file_extension(path)            
            self.vcs_client.propset(
                self.base_dir,
                prop_name,
                prop_value,
                recurse=True
            )

        self.caller.reload_treeview()

    def revert(self, widget, data1=None, data2=None):
        self.action = VCSAction(
            self.vcs_client,
            notification=False
        )

        for path in self.paths:
            self.action.append(self.vcs_client.revert, path, recurse=False)
        
        self.action.append(self.caller.reload_treeview_threaded)
        self.action.start()

    def restore(self, widget, data1=None, data2=None):
        self.action = VCSAction(
            self.vcs_client,
            notification=False
        )

        for path in self.paths:
            self.action.append(self.vcs_client.update, path, recurse=True)
        
        self.action.append(self.caller.reload_treeview_threaded)
        self.action.start()
    
    def update(self, data1=None, data2=None):
        rabbitvcs.lib.helper.launch_ui_window(
            "update", 
            self.paths
        )
    
    def unlock(self, data1=None, data2=None):
        from rabbitvcs.ui.unlock import UnlockQuick
        unlock = UnlockQuick(self.paths)
        unlock.start()
        
        self.caller.reload_treeview()
    
    def show_log(self, data1=None, data2=None):
        from rabbitvcs.ui.log import LogDialog
        LogDialog(self.vcs_client.get_repo_url(self.paths[0]))


class GtkFilesContextMenuConditions(ContextMenuConditions):
    """
    Sub-class for ContextMenuConditions for our dialogs.  Allows us to override 
    some generic condition methods with condition logic more suitable 
    to the dialogs.
    
    """
    def __init__(self, vcs_client, paths=[]):
        """    
        @param  vcs_client: The vcs client to be used
        @type   vcs_client: rabbitvcs.lib.vcs.create_vcs_instance()
        
        @param  paths: The selected paths
        @type   paths: list
        
        """
        self.vcs_client = vcs_client
        self.statuses = {}
        for path in paths:
            statuses_tmp = self.vcs_client.status(path)
            for status in statuses_tmp:
                self.statuses[status.path] = {
                    "text_status": self.vcs_client.STATUS_REVERSE[status.text_status],
                    "prop_status": self.vcs_client.STATUS_REVERSE[status.prop_status]
                }

        self.text_statuses = [self.statuses[key]["text_status"] for key in self.statuses.keys()]
        self.prop_statuses = [self.statuses[key]["prop_status"] for key in self.statuses.keys()]

        self.generate_path_dict(paths)
        
    def delete(self, data=None):
        return self.path_dict["exists"]

class GtkFilesContextMenu:
    """
    Defines context menu items for a table with files
    
    """
    def __init__(self, caller, event, base_dir, paths=[], 
            conditions=None, callbacks=None):
        """    
        @param  caller: The calling object
        @type   caller: RabbitVCS extension
        
        @param  base_dir: The curent working directory
        @type   base_dir: string
        
        @param  paths: The selected paths
        @type   paths: list
        
        @param  conditions: The conditions class that determines menu item visibility
        @kind   conditions: ContextMenuConditions
        
        @param  callbacks: The callbacks class that determines what actions are taken
        @kind   callbacks: ContextMenuCallbacks
        
        """        
        self.caller = caller
        self.event = event
        self.paths = paths
        self.base_dir = base_dir
        self.vcs_client = create_vcs_instance()

        self.conditions = conditions
        if self.conditions is None:
            self.conditions = GtkFilesContextMenuConditions(self.vcs_client, paths)

        self.callbacks = callbacks
        if self.callbacks is None:
            self.callbacks = GtkFilesContextMenuCallbacks(
                self.caller, 
                self.base_dir,
                self.vcs_client, 
                paths
            )
            
        (ignore_items, ignore_list_keys) = get_ignore_list_items(paths, self.conditions, self.callbacks)

        # The first element of each tuple is a key that matches a
        # ContextMenuItems item.  The second element is either None when there
        # is no submenu, or a recursive list of tuples for desired submenus.
        self.structure = [
            ("Diff", None),
            ("Unlock", None),
            ("Show_Log", None),
            ("Open", None),
            ("BrowseTo", None),
            ("Delete", None),
            ("Revert", None),
            ("Restore", None),
            ("Add", None),
            ("AddToIgnoreList", ignore_list_keys)
        ]
    
        self.items = ContextMenuItems(self.conditions, self.callbacks, ignore_items).get_items()
    
    def show(self):
        if len(self.paths) == 0:
            return

        context_menu = GtkContextMenu(self.structure, self.items)
        context_menu.show(self.event)

class MainContextMenuCallbacks(ContextMenuCallbacks):
    """
    The callback class used for the main context menu.  This inherits from
    and overrides the ContextMenuCallbacks class.
    
    """   
    def __init__(self, caller, base_dir, vcs_client, paths=[]):
        """        
        @param  caller: The calling object
        @type   caller: RabbitVCS extension
        
        @param  base_dir: The curent working directory
        @type   base_dir: string

        @param  vcs_client: The vcs client to be used
        @type   vcs_client: rabbitvcs.lib.vcs.create_vcs_instance()
        
        @param  paths: The selected paths
        @type   paths: list
        
        """  
        ContextMenuCallbacks.__init__(self, caller, base_dir, vcs_client, paths)

class MainContextMenuConditions(ContextMenuConditions):
    """
    Sub-class for ContextMenuConditions used for file manager extensions.  
    Allows us to override some generic condition methods with condition logic 
    more suitable to the dialogs.
    
    """
    def __init__(self, vcs_client, paths=[]):
        """    
        @param  vcs_client: The vcs client to be used
        @type   vcs_client: rabbitvcs.lib.vcs.create_vcs_instance()
        
        @param  paths: The selected paths
        @type   paths: list
        
        """   

        self.vcs_client = vcs_client
        self.status_cache = StatusCache()
        
        self.statuses = {}
        for path in paths:
            # FIXME: possibly this should be a checker, not a cache?
            self.statuses.update(self.status_cache.check_status(path,
                                                                recurse=True))

        self.text_statuses = [self.statuses[key]["text_status"] for key in self.statuses.keys()]
        self.prop_statuses = [self.statuses[key]["prop_status"] for key in self.statuses.keys()]
        
        self.generate_path_dict(paths)

class MainContextMenu:
    """
    Defines and composes the main context menu.

    """
    def __init__(self, caller, base_dir, paths=[], 
            conditions=None, callbacks=None):
        """    
        @param  caller: The calling object
        @type   caller: RabbitVCS extension
        
        @param  base_dir: The curent working directory
        @type   base_dir: string
        
        @param  paths: The selected paths
        @type   paths: list
        
        @param  conditions: The conditions class that determines menu item visibility
        @kind   conditions: ContextMenuConditions
        
        @param  callbacks: The callbacks class that determines what actions are taken
        @kind   callbacks: ContextMenuCallbacks
        
        """        
        self.caller = caller
        self.paths = paths
        self.base_dir = base_dir
        self.vcs_client = create_vcs_instance()
        
        self.conditions = conditions
        if self.conditions is None:
            self.conditions = MainContextMenuConditions(self.vcs_client, paths)

        self.callbacks = callbacks
        if self.callbacks is None:
            self.callbacks = MainContextMenuCallbacks(
                self.caller, 
                self.base_dir,
                self.vcs_client, 
                paths
            )
            
        (ignore_list, ignore_list_keys) = get_ignore_list_items(paths, self.conditions, self.callbacks)

        # The first element of each tuple is a key that matches a
        # ContextMenuItems item.  The second element is either None when there
        # is no submenu, or a recursive list of tuples for desired submenus.        
        self.structure = [
            ("Debug", [
                ("Bugs", None),
                ("Debug_Shell", None),
                ("Refresh_Status", None),
                ("Debug_Revert", None),
                ("Debug_Invalidate", None),
                ("Debug_Add_Emblem", None)
            ]),
            ("Checkout", None),
            ("Update", None),
            ("Commit", None),
            ("RabbitVCS", [
                ("CheckForModifications", None),
                ("Diff", None),
                ("ShowChanges", None),
                ("Show_Log", None),
                ("Separator0", None),
                ("Add", None),
                ("AddToIgnoreList", ignore_list_keys),
                ("Separator1", None),
                ("UpdateToRevision", None),
                ("Rename", None),
                ("Delete", None),
                ("Revert", None),
                ("Resolve", None),
                ("Relocate", None),
                ("GetLock", None),
                ("Unlock", None),
                ("Cleanup", None),
                ("Separator2", None),
                ("Export", None),
                ("Create_Repository", None),
                ("Import", None),
                ("Separator3", None),
                ("BranchTag", None),
                ("Switch", None),
                ("Merge", None),
                ("Separator4", None),
                ("Annotate", None),
                ("Separator5", None),
                ("CreatePatch", None),
                ("ApplyPatch", None),
                ("Properties", None),
                ("Separator6", None),
                ("Help", None),
                ("Settings", None),
                ("About", None)
            ])
        ]

        self.items = ContextMenuItems(self.conditions, self.callbacks, ignore_list).get_items()

    def get_menu(self):
        return (self.structure, self.items)

class ContextMenuItems:
    """
    Defines all context menu items in one large dict.  There is only level of
    menu items defined because the structure and composition of the actual menu
    is created separately.
    
    """
    def __init__(self, conditions, callbacks, items_to_append=None):
        """    
        @param  conditions: The conditions class that determines menu item visibility
        @kind   conditions: ContextMenuConditions
        
        @param  callbacks: The callbacks class that determines what actions are taken
        @kind   callbacks: ContextMenuCallbacks
        
        @param  items_to_append: Further menu items to add
        @kind   items_to_append: dict
        
        """   
        self.conditions = conditions
        self.callbacks = callbacks
        self.items_to_append = items_to_append
        
        # The following dictionary defines the complete contextmenu
        self.items = {
            "Debug": {
                "identifier": "RabbitVCS::Debug",
                "label": _("Debug"),
                "tooltip": "",
                "icon": "rabbitvcs-monkey",
                "signals": {
                    "activate": {
                        "callback": None,
                        "args": None
                    }
                },
                "condition": {
                    "callback": (lambda: settings.get("general", "show_debug"))
                }
            },
            "Bugs": {
                "identifier": "RabbitVCS::Bugs",
                "label": _("Bugs"),
                "tooltip": "",
                "icon": "rabbitvcs-bug",
                "signals": {
                    "activate": {
                        "callback": None,
                        "args": None
                    }
                },
                "condition": {
                    "callback": (lambda: True)
                }
            },
            "Debug_Shell": {
                "identifier": "RabbitVCS::Debug_Shell",
                "label": _("Open Shell"),
                "tooltip": "",
                "icon": "gnome-terminal",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.debug_shell,
                        "args": None
                    }
                },
                "condition": {
                    "callback": (lambda: True)
                }
            },
            "Refresh_Status": {
                "identifier": "RabbitVCS::Refresh_Status",
                "label": _("Refresh Status"),
                "tooltip": "",
                "icon": "rabbitvcs-refresh",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.refresh_status,
                        "args": None
                    }
                },
                "condition": {
                    "callback": (lambda: True)
                }
            },
            "Debug_Revert": {
                "identifier": "RabbitVCS::Debug_Revert",
                "label": _("Debug Revert"),
                "tooltip": _("Reverts everything it sees"),
                "icon": "rabbitvcs-revert",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.debug_revert,
                        "args": None
                    }
                },
                "condition": {
                    "callback": (lambda: True)
                }
            },
            "Debug_Invalidate": {
                "identifier": "RabbitVCS::Debug_Invalidate",
                "label": _("Invalidate"),
                "tooltip": _("Force an invalidate_extension_info() call"),
                "icon": "rabbitvcs-clear",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.debug_invalidate,
                        "args": None
                    }
                },
                "condition": {
                    "callback": (lambda: True)
                }
            },
            "Debug_Add_Emblem": {
                "identifier": "RabbitVCS::Debug_Add_Emblem",
                "label": _("Add Emblem"),
                "tooltip": _("Add an emblem"),
                "icon": "rabbitvcs-emblems",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.debug_add_emblem,
                        "args": None
                    }
                },
                "condition": {
                    "callback": (lambda: True)
                }
            },
            "Checkout": {
                "identifier": "RabbitVCS::Checkout",
                "label": _("Checkout"),
                "tooltip": _("Check out a working copy"),
                "icon": "rabbitvcs-checkout",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.checkout,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.checkout
                }
            },
            "Update": {
                "identifier": "RabbitVCS::Update",
                "label": _("Update"),
                "tooltip": _("Update a working copy"),
                "icon": "rabbitvcs-update",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.update,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.update
                }
            },
            "Commit": {
                "identifier": "RabbitVCS::Commit",
                "label": _("Commit"),
                "tooltip": _("Commit modifications to the repository"),
                "icon": "rabbitvcs-commit",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.commit,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.commit
                }
            },
            "RabbitVCS": {
                "identifier": "RabbitVCS::RabbitVCS",
                "label": _("RabbitVCS"),
                "tooltip": "",
                "icon": "rabbitvcs",
                "signals": {
                    "activate": {
                        "callback": None,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": (lambda: True)
                }
            },
            "CheckForModifications": {
                "identifier": "RabbitVCS::CheckForModifications",
                "label": _("Check for Modifications..."),
                "tooltip": _("Check for modifications made to the repository"),
                "icon": "rabbitvcs-checkmods",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.checkmods,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.checkmods
                }
            },
            "Diff": {
                "identifier": "RabbitVCS::Diff",
                "label": _("View Diff"),
                "tooltip": _("View the modifications made to a file"),
                "icon": "rabbitvcs-diff",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.diff,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.diff
                }
            },
            "ShowChanges": {
                "identifier": "RabbitVCS::ShowChanges",
                "label": _("Show Changes..."),
                "tooltip": _("Show changes between paths and revisions"),
                "icon": "rabbitvcs-changes",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.changes,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.changes
                }
            },
            "Show_Log": {
                "identifier": "RabbitVCS::Show_Log",
                "label": _("Show Log"),
                "tooltip": _("Show a file's log information"),
                "icon": "rabbitvcs-show_log",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.show_log,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.show_log
                }
            },
            "Add": {
                "identifier": "RabbitVCS::Add",
                "label": _("Add"),
                "tooltip": _("Schedule an item to be added to the repository"),
                "icon": "rabbitvcs-add",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.add,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.add
                }
            },
            "AddToIgnoreList": {
                "identifier": "RabbitVCS::AddToIgnoreList",
                "label": _("Add to ignore list"),
                "tooltip": "",
                "icon": None,
                "signals": {}, 
                "condition": {
                    "callback": self.conditions.add_to_ignore_list
                }
            },
            "UpdateToRevision": {
                "identifier": "RabbitVCS::UpdateToRevision",
                "label": _("Update to revision..."),
                "tooltip": _("Update a file to a specific revision"),
                "icon": "rabbitvcs-update",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.updateto,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.update_to
                }
            },
            "Rename": {
                "identifier": "RabbitVCS::Rename",
                "label": _("Rename..."),
                "tooltip": _("Schedule an item to be renamed on the repository"),
                "icon": "rabbitvcs-rename",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.rename,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.rename
                }
            },
            "Delete": {
                "identifier": "RabbitVCS::Delete",
                "label": _("Delete"),
                "tooltip": _("Schedule an item to be deleted from the repository"),
                "icon": "rabbitvcs-delete",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.delete,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.delete
                }
            },
            "Revert": {
                "identifier": "RabbitVCS::Revert",
                "label": _("Revert"),
                "tooltip": _("Revert an item to its unmodified state"),
                "icon": "rabbitvcs-revert",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.revert,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.revert
                }
            },
            "Resolve": {
                "identifier": "RabbitVCS::Resolve",
                "label": _("Resolve"),
                "tooltip": _("Mark a conflicted item as resolved"),
                "icon": "rabbitvcs-resolve",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.resolve,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.resolve
                }
            },
            "Restore": {
                "identifier": "RabbitVCS::Restore",
                "label": _("Restore"),
                "tooltip": _("Restore a missing item"),
                "signals": {
                    "activate": {
                        "callback": self.callbacks.update, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.update
                }
            },
            "Relocate": {
                "identifier": "RabbitVCS::Relocate",
                "label": _("Relocate..."),
                "tooltip": _("Relocate your working copy"),
                "icon": "rabbitvcs-relocate",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.relocate,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.relocate
                }
            },
            "GetLock": {
                "identifier": "RabbitVCS::GetLock",
                "label": _("Get Lock..."),
                "tooltip": _("Locally lock items"),
                "icon": "rabbitvcs-lock",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.lock,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.lock
                }
            },
            "Unlock": {
                "identifier": "RabbitVCS::Unlock",
                "label": _("Release Lock..."),
                "tooltip": _("Release lock on an item"),
                "icon": "rabbitvcs-unlock",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.unlock,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.unlock
                }
            },
            "Cleanup": {
                "identifier": "RabbitVCS::Cleanup",
                "label": _("Cleanup"),
                "tooltip": _("Clean up working copy"),
                "icon": "rabbitvcs-cleanup",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.cleanup,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.cleanup
                }
            },
            "Export": {
                "identifier": "RabbitVCS::Export",
                "label": _("Export"),
                "tooltip": _("Export a working copy or repository with no versioning information"),
                "icon": "rabbitvcs-export",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.export,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.export
                }
            },
            "Create_Repository": {
                "identifier": "RabbitVCS::Create_Repository",
                "label": _("Create Repository here"),
                "tooltip": _("Create a repository in a folder"),
                "icon": "rabbitvcs-run",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.create_repository,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.create
                }
            },
            "Import": {
                "identifier": "RabbitVCS::Import",
                "label": _("Import"),
                "tooltip": _("Import an item into a repository"),
                "icon": "rabbitvcs-import",
                "signals": {
                    "activate": {
                        "callback": self.callbacks._import,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions._import
                }
            },
            "BranchTag": {
                "identifier": "RabbitVCS::BranchTag",
                "label": _("Branch/tag..."),
                "tooltip": _("Copy an item to another location in the repository"),
                "icon": "rabbitvcs-branch",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.branch,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.branch
                }
            },
            "Switch": {
                "identifier": "RabbitVCS::Switch",
                "label": _("Switch..."),
                "tooltip": _("Change the repository location of a working copy"),
                "icon": "rabbitvcs-switch",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.switch,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.switch
                }
            },
            "Merge": {
                "identifier": "RabbitVCS::Merge",
                "label": _("Merge..."),
                "tooltip": _("A wizard with steps for merging"),
                "icon": "rabbitvcs-merge",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.merge,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.merge
                }
            },
            "Annotate": {
                "identifier": "RabbitVCS::Annotate",
                "label": _("Annotate..."),
                "tooltip": _("Annotate a file"),
                "icon": "rabbitvcs-annotate",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.annotate,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.annotate
                }
            },
            "CreatePatch": {
                "identifier": "RabbitVCS::CreatePatch",
                "label": _("Create Patch..."),
                "tooltip": _("Creates a unified diff file with all changes you made"),
                "icon": "rabbitvcs-createpatch",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.createpatch,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.createpatch
                }
            },
            "ApplyPatch": {
                "identifier": "RabbitVCS::ApplyPatch",
                "label": _("Apply Patch..."),
                "tooltip": _("Applies a unified diff file to the working copy"),
                "icon": "rabbitvcs-applypatch",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.applypatch,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.applypatch
                }
            },
            "Properties": {
                "identifier": "RabbitVCS::Properties",
                "label": _("Properties"),
                "tooltip": _("View the properties of an item"),
                "icon": "rabbitvcs-properties",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.properties,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": self.conditions.properties
                }
            },
            "Help": {
                "identifier": "RabbitVCS::Help",
                "label": _("Help"),
                "tooltip": _("View help"),
                "icon": "rabbitvcs-help",
                "signals": {
                    "activate": {
                        "callback": None,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": (lambda: False)
                }
            },
            "Settings": {
                "identifier": "RabbitVCS::Settings",
                "label": _("Settings"),
                "tooltip": _("View or change RabbitVCS settings"),
                "icon": "rabbitvcs-settings",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.settings,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": (lambda: True)
                }
            },
            "About": {
                "identifier": "RabbitVCS::About",
                "label": _("About"),
                "tooltip": _("About RabbitVCS"),
                "icon": "rabbitvcs-about",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.about,
                        "args": None
                    }
                }, 
                "condition": {
                    "callback": (lambda: True)
                }
            },
            "Open": {
                "identifier": "RabbitVCS::Open",
                "label": _("Open"),
                "tooltip": _("Open a file"),
                "icon": gtk.STOCK_OPEN,
                "signals": {
                    "activate": {
                        "callback": self.callbacks._open, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions._open
                }
            },
            "BrowseTo": {
                "identifier": "RabbitVCS::BrowseTo",
                "label": _("Browse to"),
                "tooltip": _("Browse to a file or folder"),
                "icon": gtk.STOCK_HARDDISK,
                "signals": {
                    "activate": {
                        "callback": self.callbacks.browse_to, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.browse_to
                }
            }
        }
        
        for i in (0,1,2,3,4,5,6,7,8,9):
            key = "Separator" + str(i)
            self.items[key] = {
                "identifier": "RabbitVCS::" + key,
                "label": SEPARATOR,
                "tooltip": "",
                "icon": None,
                "signals": {}, 
                "condition": {
                    "callback": (lambda: True)
                }
            }
        
        if self.items_to_append is not None:
            for key,val in self.items_to_append.items():
                self.items[key] = val

    def get_items(self):
        return self.items

def get_ignore_list_items(paths, conditions, callbacks):
    """
    Build up a list of items to ignore based on the selected paths

    @param  paths: The selected paths
    @type   paths: list
    
    @param  conditions: The conditions class that determines menu item visibility
    @kind   conditions: ContextMenuConditions
    
    @param  callbacks: The callbacks class that determines what actions are taken
    @kind   callbacks: ContextMenuCallbacks

    """
    ignore_items = {}
    ignore_list_keys = []
    
    # Used to weed out duplicate menu items
    added_ignore_labels = []
    
    # These are ignore-by-filename items
    ignorebyfilename_index = 0
    for path in paths:
        basename = os.path.basename(path)
        if basename not in added_ignore_labels:
            key = "IgnoreByFileName%s" % str(ignorebyfilename_index)
            ignore_items[key] = {
                "identifier": "RabbitVCS::%s" % key,
                "label": basename,
                "tooltip": _("Ignore item by filename"),
                "icon": None,
                "signals": {
                    "button-press-event": {
                        "callback": callbacks.ignore_by_filename, 
                        "args": path
                     }
                 },
                "condition": {
                    "callback": conditions.ignore_by_filename,
                    "args": path
                }
            }
            added_ignore_labels.append(basename)
            ignorebyfilename_index += 1
            ignore_list_keys.append((key, None))

    # These are ignore-by-extension items
    ignorebyfileext_index = 0
    for path in paths:
        extension = rabbitvcs.lib.helper.get_file_extension(path)
        
        ext_str = "*%s"%extension
        if ext_str not in added_ignore_labels:
            key = "IgnoreByFileExt%s" % str(ignorebyfileext_index)
            ignore_items[key] = {
                "identifier": "RabbitVCS::%s" % key,
                "label": ext_str,
                "tooltip": _("Ignore item by file extension"),
                "icon": None,
                "signals": {
                    "button-press-event": {
                        "callback": callbacks.ignore_by_file_extension, 
                        "args": path
                    }
                },
                "condition": {
                    "callback": conditions.ignore_by_file_extension,
                    "args": (path, extension)
                }
            }
            added_ignore_labels.append(ext_str)
            ignorebyfileext_index += 1
            ignore_list_keys.append((key, None))

    return (ignore_items, ignore_list_keys)
