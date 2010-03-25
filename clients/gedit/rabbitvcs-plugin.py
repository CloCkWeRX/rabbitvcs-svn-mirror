#
# This is a Gedit plugin to allow for RabbitVCS integration in the Gedit
# text editor.
# 
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

from gettext import gettext as _

import os
import gtk
import gedit

import rabbitvcs.util.helper
from rabbitvcs.vcs import create_vcs_instance
from rabbitvcs.util.contextmenu import GtkFilesContextMenuConditions, \
    GtkFilesContextMenuCallbacks, MainContextMenu, MainContextMenuCallbacks, \
    MenuBuilder
from rabbitvcs.util.contextmenuitems import *

# Menu item example, insert a new item in the Tools menu
ui_str = """<ui>
  <menubar name="MenuBar">
    <menu name="ToolsMenu" action="Tools">
      <placeholder name="RabbitVCSMenu">
        <menuitem name="RabbitVCS::Commit" action="RabbitVCS::Commit" />
        <menuitem name="RabbitVCS::Update" action="RabbitVCS::Update" />
        <menuitem name="RabbitVCS::Checkout" action="RabbitVCS::Checkout" />
        <menu name="RabbitVCS::RabbitVCS" action="RabbitVCS::RabbitVCS">
            <menu name="RabbitVCS::Diff_Menu" action="RabbitVCS::Diff_Menu">
                <menuitem name="RabbitVCS::Diff" action="RabbitVCS::Diff" />
                <menuitem name="RabbitVCS::Diff_Previous_Revision" action="RabbitVCS::Diff_Previous_Revision" />
                <menuitem name="RabbitVCS::Diff_Multiple" action="RabbitVCS::Diff_Multiple" />
                <menuitem name="RabbitVCS::Compare_Tool" action="RabbitVCS::Compare_Tool" />
                <menuitem name="RabbitVCS::Compare_Tool_Previous_Revision" action="RabbitVCS::Compare_Tool_Previous_Revision" />
                <menuitem name="RabbitVCS::Compare_Tool_Multiple" action="RabbitVCS::Compare_Tool_Multiple" />
                <menuitem name="RabbitVCS::Show_Changes" action="RabbitVCS::Show_Changes" />
            </menu>
            <menuitem name="RabbitVCS::Show_Log" action="RabbitVCS::Show_Log" />
            <menuitem name="RabbitVCS::Repo_Browser" action="RabbitVCS::Repo_Browser" />
            <menuitem name="RabbitVCS::Check_For_Modifications" action="RabbitVCS::Check_For_Modifications" />
            <separator />
            <menuitem name="RabbitVCS::Add" action="RabbitVCS::Add" />
            <menu name="RabbitVCS::Add_To_Ignore_List" action="RabbitVCS::Add_To_Ignore_List">
                <menuitem name="RabbitVCS::Ignore_By_Filename" action="RabbitVCS::Ignore_By_Filename" />
                <menuitem name="RabbitVCS::Ignore_By_File_Extension" action="RabbitVCS::Ignore_By_File_Extension" />
            </menu>
            <separator />
            <menuitem name="RabbitVCS::Update_To_Revision" action="RabbitVCS::Update_To_Revision" />
            <menuitem name="RabbitVCS::Rename" action="RabbitVCS::Rename" />
            <menuitem name="RabbitVCS::Delete" action="RabbitVCS::Delete" />
            <menuitem name="RabbitVCS::Revert" action="RabbitVCS::Revert" />
            <menuitem name="RabbitVCS::Resolve" action="RabbitVCS::Resolve" />
            <menuitem name="RabbitVCS::Relocate" action="RabbitVCS::Relocate" />
            <menuitem name="RabbitVCS::Get_Lock" action="RabbitVCS::Get_Lock" />
            <menuitem name="RabbitVCS::Unlock" action="RabbitVCS::Unlock" />
            <menuitem name="RabbitVCS::Cleanup" action="RabbitVCS::Cleanup" />
            <menuitem name="RabbitVCS::Annotate" action="RabbitVCS::Annotate" />
            <separator />
            <menuitem name="RabbitVCS::Export" action="RabbitVCS::Export" />
            <menuitem name="RabbitVCS::Create_Repository" action="RabbitVCS::Create_Repository" />
            <menuitem name="RabbitVCS::Import" action="RabbitVCS::Import" />
            <separator />
            <menuitem name="RabbitVCS::Branch_Tag" action="RabbitVCS::Branch_Tag" />
            <menuitem name="RabbitVCS::Switch" action="RabbitVCS::Switch" />
            <menuitem name="RabbitVCS::Merge" action="RabbitVCS::Merge" />
            <separator />
            <menuitem name="RabbitVCS::Apply_Patch" action="RabbitVCS::Apply_Patch" />
            <menuitem name="RabbitVCS::Create_Patch" action="RabbitVCS::Create_Patch" />
            <menuitem name="RabbitVCS::Properties" action="RabbitVCS::Properties" />
            <separator />
            <menuitem name="RabbitVCS::Settings" action="RabbitVCS::Settings" />
            <menuitem name="RabbitVCS::About" action="RabbitVCS::About" />
        </menu>
      </placeholder>
    </menu>
  </menubar>
</ui>
"""
class RabbitVCSWindowHelper:

    _menu_paths = [
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::Commit",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::Update",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::Checkout",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Diff_Menu",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Diff_Menu/RabbitVCS::Diff",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Diff_Menu/RabbitVCS::Diff_Previous_Revision",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Diff_Menu/RabbitVCS::Diff_Multiple",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Diff_Menu/RabbitVCS::Compare_Tool",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Diff_Menu/RabbitVCS::Compare_Tool_Previous_Revision",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Diff_Menu/RabbitVCS::Compare_Tool_Multiple",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Diff_Menu/RabbitVCS::Show_Changes",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Show_Log",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Repo_Browser",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Check_For_Modifications",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Add",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Add_To_Ignore_List",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Add_To_Ignore_List/RabbitVCS::Ignore_By_Filename",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Add_To_Ignore_List/RabbitVCS::Ignore_By_File_Extension",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Update_To_Revision",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Rename",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Delete",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Revert",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Resolve",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Get_Lock",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Unlock",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Cleanup",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Annotate",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Export",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Create_Repository",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Import",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Branch_Tag",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Switch",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Merge",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Apply_Patch",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Create_Patch",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Properties",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::Settings",
        "/MenuBar/ToolsMenu/RabbitVCSMenu/RabbitVCS::RabbitVCS/RabbitVCS::About"
    ]

    _default_base_dir = os.path.expanduser("~")

    def __init__(self, plugin, window):
        self._window = window
        self._plugin = plugin
        self.base_dir = self._default_base_dir
        self._menubar_menu = None

        # Insert menu items
        self._insert_menu()

    def deactivate(self):
        # Remove any installed menu items
        self._remove_menu()

        self._window = None
        self.base_dir = None
        self._plugin = None
        self._menubar_menu = None
        self._action_group = None

    def _insert_menu(self):
        # Get the GtkUIManager
        manager = self._window.get_ui_manager()

        self._menubar_menu = GeditMenu(self, self.base_dir, [self._get_document_path()])
        
        self._action_group = gtk.ActionGroup("RabbitVCSActions")
        self._action_group = self._menubar_menu.get_action_group(self._action_group)

        # Insert the action group
        manager.insert_action_group(self._action_group, 0)

        # Merge the UI
        self._ui_id = manager.add_ui_from_string(ui_str)

    def _remove_menu(self):
        # Get the GtkUIManager
        manager = self._window.get_ui_manager()

        # Remove the ui
        manager.remove_ui(self._ui_id)

        # Remove the action group
        manager.remove_action_group(self._action_group)

        # Make sure the manager updates
        manager.ensure_update()

    def update_ui(self):
        self.update_base_dir()
        
        document = self._window.get_active_document()
        self._action_group.set_sensitive(document != None)
        if document != None:
            manager = self._window.get_ui_manager()
            manager.get_widget("/MenuBar/ToolsMenu/RabbitVCSMenu").set_sensitive(True)
            
            self._menubar_menu.set_paths([self._get_document_path()])
            self._determine_menu_sensitivity([self._get_document_path()])

    def connect_view(self, view, id_name):
        handler_id = view.connect("populate-popup", self.on_view_populate_popup)
        view.set_data(id_name, [handler_id])

    def on_view_populate_popup(self, view, menu):
        separator = gtk.SeparatorMenuItem()
        menu.append(separator)
        separator.show()

        context_menu = GeditMainContextMenu(self, self.base_dir, [self._get_document_path()]).get_menu()
        for context_menu_item in context_menu:
            menu.append(context_menu_item)

    def _get_document_path(self):
        document = self._window.get_active_document()
        path = self.base_dir
        
        if document:
            tmp_path = document.get_uri_for_display()
            if os.path.exists(tmp_path):
                path = tmp_path

        return path

    def update_base_dir(self):
        document = self._window.get_active_document()
        if document:
            path = document.get_uri_for_display()
            if os.path.exists(path):
                self.base_dir = os.path.dirname(path)
        else:
            self.base_dir = self._default_base_dir

        self._menubar_menu.set_base_dir(self.base_dir)

    def _determine_menu_sensitivity(self, paths):
        self._menubar_menu.update_conditions(paths)
        
        manager = self._window.get_ui_manager()
        for menu_path in self._menu_paths:
            widget = manager.get_widget(menu_path)
            self._menubar_menu.update_action(widget.get_related_action())

    # Menu activate handlers
    def reload_settings(self, proc):
        self.update_ui()

    def rescan_after_process_exit(self, proc, paths):
        self.update_ui()

    def execute_after_process_exit(self, proc):
        self.update_ui()

    def reload_treeview(self):
        self.update_ui()
    
    def reload_treeview_threaded(self):
        self.update_ui()

class RabbitVCSPlugin(gedit.Plugin):
    def __init__(self):
        gedit.Plugin.__init__(self)
        self._instances = {}
        self.id_name = "RabbitVCSContextMenuID"

    def activate(self, window):
        self._instances[window] = RabbitVCSWindowHelper(self, window)

        handler_ids = []
        for signal in ('tab-added', 'tab-removed'):
            method = getattr(self, 'on_window_' + signal.replace('-', '_'))
            handler_ids.append(window.connect(signal, method))
        window.set_data(self.id_name, handler_ids)

        for view in window.get_views():
            self._instances[window].connect_view(view, self.id_name)

    def deactivate(self, window):
        widgets = [window] + window.get_views()
        for widget in widgets:
            handler_ids = widget.get_data(self.id_name)
            if handler_ids is not None:
                for handler_id in handler_ids:
                    widget.disconnect(handler_id)
                widget.set_data(self.id_name, None)

        self._instances[window].deactivate()
        del self._instances[window]

    def update_ui(self, window):
        self._instances[window].update_ui()

    def on_window_tab_added(self, window, tab):
        self._instances[window].connect_view(tab.get_view(), self.id_name)
    
    def on_window_tab_removed(self, window, tab):
        pass


class MenuIgnoreByFilename(MenuItem):
    identifier = "RabbitVCS::Ignore_By_Filename"
    label = _("Ignore by File Name")
    tooltip = _("Ignore item by filename")

class MenuIgnoreByFileExtension(MenuItem):
    identifier = "RabbitVCS::Ignore_By_File_Extension"
    label = _("Ignore by File Extension")
    tooltip = _("Ignore item by extension")

class GeditMenuBuilder(object):
    """
    Generalised menu builder class. Subclasses must provide:
    
    make_menu_item(self, item, id_magic) - create the menu item for whatever
    toolkit (usually this should be just call a  convenience method on the
    MenuItem instance).
    
    attach_submenu(self, menu_node, submenu_list) - given a list of whatever
    make_menu_item(...) returns, create a submenu and attach it to the given
    node.
    
    top_level_menu(self, items) - in some circumstances we need to treat the top
    level menu differently (eg. Nautilus, because Xenu said so). This processes
    a list of menu items returned by make_menu_item(...) to create the overall
    menu.  
    """
    
    def __init__(self, structure, conditions, callbacks, action_group):
        """
        @param  structure: Menu structure
        @type   structure: list
                
        Note on "structure". The menu structure is defined in a list of tuples 
        of two elements each.  The first element is a class - the MenuItem
        subclass that defines the menu interface (see below).
        
        The second element is either None (if there is no submenu) or a list of
        tuples if there is a submenu.  The submenus are generated recursively. 
        FYI, this is a list of tuples so that we retain the desired menu item
        order (dicts do not retain order)
        
            Example:
            [
                (MenuClassOne, [
                    (MenuClassOneSubA,
                    (MenuClassOneSubB
                ]),
                (MenuClassTwo,
                (MenuClassThree
            ]
            
        """

        self.action_group = action_group

        for item_class in structure:
            
            item = item_class(conditions, callbacks)

            default_name = MenuItem.make_default_name(item.identifier)            
            action = gtk.Action(item.identifier, item.label, item.tooltip, item.icon)
            
            if item.icon:
                action.set_icon_name(item.icon)
           
            if item.signals:
                for signal, info in item.signals.items():
                    action.connect(signal, info["callback"], info["args"])
            
            action.set_property("visible", item.show())
            
            action.set_data("item", item)
             
            self.action_group.add_action(action)

    def _get_function(self, object, name):
        
        function = None
        
        if hasattr(object, name):
            
            attr = getattr(object, name)
            if callable(attr):
                function = attr
        
        return function
        
class GeditMenu:
    def __init__(self, caller, base_dir, paths):
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
        
        self.conditions = GtkFilesContextMenuConditions(self.vcs_client, self.paths)

        self.callbacks = GtkFilesContextMenuCallbacks(
            self.caller, 
            self.base_dir,
            self.vcs_client, 
            self.paths
        )

        self.structure = [
            MenuCheckout,
            MenuUpdate,
            MenuCommit,
            MenuRabbitVCS,
            MenuDiffMenu, 
            MenuDiff,
            MenuDiffPrevRev,
            MenuDiffMultiple,
            MenuCompareTool,
            MenuCompareToolPrevRev,
            MenuCompareToolMultiple,
            MenuShowChanges,
            MenuShowLog,
            MenuRepoBrowser,
            MenuCheckForModifications,
            MenuAdd,
            MenuAddToIgnoreList, 
            MenuUpdateToRevision,
            MenuRename,
            MenuDelete,
            MenuRevert,
            MenuResolve,
            MenuRelocate,
            MenuGetLock,
            MenuUnlock,
            MenuCleanup,
            MenuExport,
            MenuCreateRepository,
            MenuImport,
            MenuBranchTag,
            MenuSwitch,
            MenuMerge,
            MenuAnnotate,
            MenuCreatePatch,
            MenuApplyPatch,
            MenuProperties,
            MenuHelp,
            MenuSettings,
            MenuAbout,
            MenuIgnoreByFilename,
            MenuIgnoreByFileExtension
        ]

    def set_paths(self, paths):
        self.paths = paths
        self.conditions.paths = paths
        self.callbacks.paths = paths

    def set_base_dir(self, base_dir):
        self.base_dir = base_dir
        self.callbacks.base_dir = base_dir
        self.conditions.base_dir = base_dir

    def get_action_group(self, action_group):
        return GeditMenuBuilder(self.structure, self.conditions, self.callbacks, action_group).action_group
    
    def update_conditions(self, paths):
        self.conditions.generate_statuses(paths)
        self.conditions.generate_path_dict(paths)
    
    def update_action(self, action):
        action.set_property("visible", action.get_data("item").show())

class GeditContextMenu(MenuBuilder):
    """
    Provides a standard gtk context menu (ie. a list of
    "gtk.MenuItem"s).
    """

    signal = "activate"
        
    def make_menu_item(self, item, id_magic):
        return item.make_gtk_menu_item(id_magic)
    
    def attach_submenu(self, menu_node, submenu_list):
        submenu = gtk.Menu()
        menu_node.set_submenu(submenu)
        [submenu.append(item) for item in submenu_list]
    
    def top_level_menu(self, items):
        return items

class GeditMainContextMenu(MainContextMenu):
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
            self.conditions = GtkFilesContextMenuConditions(self.vcs_client, paths)

        self.callbacks = callbacks
        if self.callbacks is None:
            self.callbacks = MainContextMenuCallbacks(
                self.caller, 
                self.base_dir,
                self.vcs_client, 
                paths
            )
            
        ignore_items = get_ignore_list_items(paths)

        # The first element of each tuple is a key that matches a
        # ContextMenuItems item.  The second element is either None when there
        # is no submenu, or a recursive list of tuples for desired submenus.        
        self.structure = [
            (MenuDebug, [
                (MenuBugs, None),
                (MenuDebugShell, None),
                (MenuRefreshStatus, None),
                (MenuDebugRevert, None),
                (MenuDebugInvalidate, None),
                (MenuDebugAddEmblem, None)
            ]),
            (MenuCheckout, None),
            (MenuUpdate, None),
            (MenuCommit, None),
            (MenuRabbitVCS, [
                (MenuDiffMenu, [
                    (MenuDiff, None),
                    (MenuDiffPrevRev, None),
                    (MenuDiffMultiple, None),
                    (MenuCompareTool, None),
                    (MenuCompareToolPrevRev, None),
                    (MenuCompareToolMultiple, None),
                    (MenuShowChanges, None),
                ]),
                (MenuShowLog, None),
                (MenuRepoBrowser, None),
                (MenuCheckForModifications, None),
                (MenuSeparator, None),
                (MenuAdd, None),
                (MenuAddToIgnoreList, ignore_items),
                (MenuSeparator, None),
                (MenuUpdateToRevision, None),
                (MenuRename, None),
                (MenuDelete, None),
                (MenuRevert, None),
                (MenuResolve, None),
                (MenuRelocate, None),
                (MenuGetLock, None),
                (MenuUnlock, None),
                (MenuCleanup, None),
                (MenuSeparator, None),
                (MenuExport, None),
                (MenuCreateRepository, None),
                (MenuImport, None),
                (MenuSeparator, None),
                (MenuBranchTag, None),
                (MenuSwitch, None),
                (MenuMerge, None),
                (MenuSeparator, None),
                (MenuAnnotate, None),
                (MenuSeparator, None),
                (MenuCreatePatch, None),
                (MenuApplyPatch, None),
                (MenuProperties, None),
                (MenuSeparator, None),
                (MenuHelp, None),
                (MenuSettings, None),
                (MenuAbout, None)
            ])
        ]
        
    def get_menu(self):
        return GeditContextMenu(self.structure, self.conditions, self.callbacks).menu
