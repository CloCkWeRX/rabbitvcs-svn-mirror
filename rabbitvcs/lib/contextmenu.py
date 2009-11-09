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
import rabbitvcs.lib.helper

log = Log("rabbitvcs.ui.commit")
_ = gettext.gettext

import rabbitvcs.services
from rabbitvcs.services.cacheservice import StatusCacheStub as StatusCache

SEPARATOR = u'\u2015' * 10

class GtkContextMenu:
    """
    Provides a standard Gtk Context Menu class used for all context menus
    in gtk dialogs/windows.
    
    """
    def __init__(self, menu):
        if menu is None:
            return
        
        self.view = gtk.Menu()
        self.num_items = 0
        is_last = False
        is_first = True
        index = 0
        length = len(menu)
        for item in menu:
            is_last = (index + 1 == length)

            # If the item is a separator, don't show it if this is the first
            # or last item, or if the previous item was a separator.
            if (item["label"] == SEPARATOR and
                    (is_first or is_last or previous_label == SEPARATOR)):
                index += 1
                continue
        
            condition = item["condition"]
            if "args" in condition:
                if condition["callback"](condition["args"]) is False:
                    continue
            else:
                if condition["callback"]() is False:
                    continue
            
            action = gtk.Action(item["label"], item["label"], None, None)
            
            if "icon" in item and item["icon"] is not None:
                action.set_icon_name(item["icon"])
    
            menuitem = action.create_menu_item()
            if "signals" in item and item["signals"] is not None:
                for signal, info in item["signals"].items():
                    menuitem.connect(signal, info["callback"], info["args"])
            
            if "submenu" in item:
                submenu = GtkContextMenu(item["submenu"])
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
                try:
                    if key not in self.path_dict or self.path_dict[key] is not True:
                        self.path_dict[key] = func(path)
                except KeyError, e:
                    # KeyError will be generated for files that don't exist
                    self.path_dict[key] = False

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

    def compare(self, data=None):
        if self.path_dict["length"] == 2:
            return True
        elif (self.path_dict["length"] == 1 and
                self.path_dict["is_in_a_or_a_working_copy"]):
            return True
        return False
        
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

class FileManagerContextMenuConditions(ContextMenuConditions):
    """
    Sub-class for ContextMenuConditions used for file manager extensions.  
    Allows us to override some generic condition methods with condition logic 
    more suitable to the dialogs.
    
    """
    def __init__(self, vcs_client, paths=[]):
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

class GtkFilesContextMenuConditions(ContextMenuConditions):
    """
    Sub-class for ContextMenuConditions for our dialogs.  Allows us to override 
    some generic condition methods with condition logic more suitable 
    to the dialogs.
    
    """
    def __init__(self, vcs_client, paths=[]):
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

class GtkFilesContextMenuCallbacks:
    def __init__(self, caller, base_dir, vcs_client, paths=[]):
        self.caller = caller
        self.base_dir = base_dir
        self.vcs_client = vcs_client
        self.paths = paths
            
    def view_diff(self, widget, data1=None, data2=None):
        rabbitvcs.lib.helper.launch_diff_tool(*self.paths)
    
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

class GtkFilesContextMenu:
    """
    Defines context menu items for a table with files
    
    """
    def __init__(self, caller, event, base_dir, paths=[], 
            conditions=None, callbacks=None):
        
        if len(paths) == 0:
            return
        
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

        # Build up a list of items to ignore based on the selected rows
        ignore_items = []
        added_ignore_labels = []
        
        # These are ignore-by-filename items
        for path in self.paths:
            basename = os.path.basename(path)
            if basename not in added_ignore_labels:
                ignore_items.append({
                    "label": basename,
                    "icon": None,
                    "signals": {
                        "button-press-event": {
                            "callback": self.callbacks.ignore_by_filename, 
                            "args": path
                         }
                     },
                    "condition": {
                        "callback": self.conditions.ignore_by_filename,
                        "args": path
                    }
                })
                added_ignore_labels.append(basename)

        # These are ignore-by-extension items
        for path in self.paths:
            extension = rabbitvcs.lib.helper.get_file_extension(path)
            
            ext_str = "*%s"%extension
            if ext_str not in added_ignore_labels:
                ignore_items.append({
                    "label": ext_str,
                    "icon": None,
                    "signals": {
                        "button-press-event": {
                            "callback": self.callbacks.ignore_by_file_extension, 
                            "args": path
                        }
                    },
                    "condition": {
                        "callback": self.conditions.ignore_by_file_extension,
                        "args": (path, extension)
                    }
                })
                added_ignore_labels.append(ext_str)

        # Generate the full context menu
        context_menu = GtkContextMenu([
            {
                "label": _("View Diff"),
                "icon": "rabbitvcs-diff",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.view_diff, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.diff,
                    "args": None
                }
            },
            {
                "label": _("Remove Lock"),
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
            {
                "label": _("Show log"),
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
            {
                "label": _("Open"),
                "icon": gtk.STOCK_OPEN,
                "signals": {
                    "activate": {
                        "callback": self.callbacks._open, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions._open,
                    "args": None
                }
            },
            {
                "label": _("Browse to"),
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
            },
            {
                "label": _("Delete"),
                "icon": "rabbitvcs-delete",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.delete, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.delete,
                    "args": None
                }
            },
            {
                "label": _("Add"),
                "icon": "rabbitvcs-add",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.add, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.add,
                    "args": None
                }
            },
            {
                "label": _("Revert"),
                "icon": "rabbitvcs-revert",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.revert, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.revert,
                    "args": None
                }
            },
            {
                "label": _("Restore"),
                "signals": {
                    "activate": {
                        "callback": self.callbacks.restore, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.restore,
                    "args": None
                }
            },
            {
                "label": _("Update"),
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
            {
                "label": _("Add to ignore list"),
                'submenu': ignore_items,
                "condition": {
                    "callback": self.conditions.add_to_ignore_list,
                    "args": None
                }
            }
        ])
        context_menu.show(self.event)
