#
# This is an extension to the Nautilus file manager to allow better 
# integration with the Subversion source control system.
# 
# Copyright (C) 2006-2008 by Jason Field <jason@jasonfield.com>
# Copyright (C) 2007-2008 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2008-2008 by Adam Plumb <adamplumb@gmail.com>
# 
# NautilusSvn is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# NautilusSvn is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with NautilusSvn;  If not, see <http://www.gnu.org/licenses/>.
#

import os

import pygtk
import gobject
import gtk

from nautilussvn.ui import InterfaceView
import nautilussvn.ui.widget
import nautilussvn.ui.dialog
import nautilussvn.lib.settings
import nautilussvn.lib.helper

from nautilussvn import gettext
_ = gettext.gettext

class Settings(InterfaceView):
    def __init__(self):
        """
        Provides an interface to the settings library.
        """
    
        InterfaceView.__init__(self, "settings", "Settings")

        self.settings = nautilussvn.lib.settings.SettingsManager()
        
        self.language = nautilussvn.ui.widget.ComboBox(
            self.get_widget("language"), 
            [_("English")]
        )
        self.language.set_active_from_value(
            self.settings.get("general", "language")
        )
        self.get_widget("enable_attributes").set_active(
            int(self.settings.get("general", "enable_attributes"))
        )
        self.get_widget("enable_emblems").set_active(
            int(self.settings.get("general", "enable_emblems"))
        )
        self.get_widget("enable_recursive").set_active(
            int(self.settings.get("general", "enable_recursive"))
        )
        self.get_widget("show_debug").set_active(
            int(self.settings.get("general","show_debug"))
        )
        self.get_widget("diff_tool").set_text(
            self.settings.get("external", "diff_tool")
        )
        self.get_widget("diff_tool_swap").set_active(
            int(self.settings.get("external", "diff_tool_swap"))
        )
        self.get_widget("repo_browser").set_text(
            str(self.settings.get("external", "repo_browser"))
        )
        self.get_widget("cache_number_repositories").set_text(
            str(self.settings.get("cache", "number_repositories"))
        )
        self.get_widget("cache_number_messages").set_text(
            str(self.settings.get("cache", "number_messages"))
        )
        
        self.logging_type = nautilussvn.ui.widget.ComboBox(
            self.get_widget("logging_type"), 
            ["None", "Console", "File", "Both"]
        )
        val = self.settings.get("logging", "type")
        if not val:
            val = "Console"
        self.logging_type.set_active_from_value(val)

        self.logging_level = nautilussvn.ui.widget.ComboBox(
            self.get_widget("logging_level"), 
            ["Debug", "Info", "Warning", "Error", "Critical"]
        )
        val = self.settings.get("logging", "level")
        if not val:
            val = "Debug"
        self.logging_level.set_active_from_value(val)

    def on_destroy(self, widget):
        gtk.main_quit()

    def on_cancel_clicked(self, widget):
        gtk.main_quit()

    def on_ok_clicked(self, widget):
        self.save()
        gtk.main_quit()
    
    def on_apply_clicked(self, widget):
        self.save()

    def save(self):
        self.settings.set(
            "general", "language", 
            self.get_widget("language").get_active_text()
        )
        self.settings.set(
            "general", "enable_attributes",
            self.get_widget("enable_attributes").get_active()
        )
        self.settings.set(
            "general", "enable_emblems",
            self.get_widget("enable_emblems").get_active()
        )
        self.settings.set(
            "general", "enable_recursive",
            self.get_widget("enable_recursive").get_active()
        )
        self.settings.set(
            "general", "show_debug",
            self.get_widget("show_debug").get_active()
        )
        self.settings.set(
            "external", "diff_tool",
            self.get_widget("diff_tool").get_text()
        )
        self.settings.set(
            "external", "diff_tool_swap",
            self.get_widget("diff_tool_swap").get_active()
        )
        self.settings.set(
            "external", "repo_browser",
            self.get_widget("repo_browser").get_text()
        )
        self.settings.set(
            "cache", "number_repositories",
            self.get_widget("cache_number_repositories").get_text()
        )
        self.settings.set(
            "cache", "number_messages",
            self.get_widget("cache_number_messages").get_text()
        )
        self.settings.set(
            "logging", "type",
            self.logging_type.get_active_text()
        )
        self.settings.set(
            "logging", "level",
            self.logging_level.get_active_text()
        )
        self.settings.write()

    def on_external_diff_tool_browse_clicked(self, widget):
        chooser = nautilussvn.ui.dialog.FileChooser(
            _("Select a program"), "/usr/bin"
        )
        path = chooser.run()
        path = path.replace("file://", "")
        if path is not None:
            self.get_widget("diff_tool").set_text(path)

    def on_external_repo_browser_browse_clicked(self, widget):
        chooser = nautilussvn.ui.dialog.FileChooser(
            _("Select a program"), "/usr/bin"
        )
        path = chooser.run()
        path = path.replace("file://", "")
        if path is not None:
            self.get_widget("repo_browser").set_text(path)

    def on_cache_clear_repositories_clicked(self, widget):
        confirmation = nautilussvn.ui.dialog.Confirmation(
            _("Are you sure you want to clear your repository paths?")
        )
        if confirmation.run() == 1:
            path = nautilussvn.lib.helper.get_repository_paths_path()
            fh = open(path, "w")
            fh.write("")
            fh.close()
            nautilussvn.ui.dialog.MessageBox(_("Repository paths cleared"))

    def on_cache_clear_messages_clicked(self, widget):
        confirmation = nautilussvn.ui.dialog.Confirmation(
            _("Are you sure you want to clear your previous messages?")
        )
        if confirmation.run() == 1:
            path = nautilussvn.lib.helper.get_previous_messages_path()
            fh = open(path, "w")
            fh.write("")
            fh.close()
            nautilussvn.ui.dialog.MessageBox(_("Previous messages cleared"))

    def on_cache_clear_authentication_clicked(self, widget):
        confirmation = nautilussvn.ui.dialog.Confirmation(
            _("Are you sure you want to clear your authentication information?")
        )
        if confirmation.run() == 1:
            home_dir = nautilussvn.lib.helper.get_user_path()
            subpaths = [
                '/.subversion/auth/svn.simple',
                '/.subversion/auth/svn.ssl.server',
                '/.subversion/auth/svn.username'
            ]
            for subpath in subpaths:
                path = "%s%s" % (home_dir, subpath)
                if os.path.exists(path):
                    files = os.listdir(path)
                    for filename in files:
                        filepath = "%s/%s" % (path, filename)
                        os.remove(filepath)

            nautilussvn.ui.dialog.MessageBox(_("Authentication information cleared"))
                

if __name__ == "__main__":
    window = Settings()
    window.register_gtk_quit()
    gtk.main()
