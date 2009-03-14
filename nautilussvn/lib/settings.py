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

"""

Everything related retrieving and storing configuration keys.

"""

import os

import shutil
import configobj

def get_home_folder():
    """ 
    Returns the location of the hidden folder we use in the home dir.
    This is used for storing things like previous commit messages and
    previously used repositories.
    
    FIXME: This is a copy of the helper module's function, because I can't
    have a circular module reference (helper imports Settings right now).
    
    @rtype:     string
    @return:    The location of our main user storage folder.
    
    """
    
    # Make sure we adher to the freedesktop.org XDG Base Directory 
    # Specifications. $XDG_CONFIG_HOME if set, by default ~/.config 
    xdg_config_home = os.environ.get(
        "XDG_CONFIG_HOME", 
        os.path.join(os.path.expanduser("~"), ".config")
    )
    config_home = os.path.join(xdg_config_home, "nautilussvn")
    
    # Make sure the directories are there
    if not os.path.isdir(config_home):
        # FIXME: what if somebody places a file in there?
        os.makedirs(config_home, 0700)

    return config_home

SETTINGS_FILE = "%s/settings.conf" % get_home_folder()

DEFAULT_SETTINGS = {
    "general": {
        "language": "English",
        "enable_attributes": 1,
        "enable_emblems": 1,
        "enable_recursive": 1
    },
    "external": {
        "diff_tool": "/usr/bin/meld",
        "diff_tool_swap": 0,
        "repo_browser": "firefox"
    },
    "cache": {
        "number_repositories": 30,
        "number_messages": 30
    },
    "logging": {
        "type": "File",
        "level": "Error"
    }
}

class SettingsManager:
    """
    This class provides an shallow interface for the rest of the program to use 
    to interact with our configuration file.
    
    Usage::
    
        Get settings:
            sm = SettingsManager()
            diff_tool = sm.get("external", "diff_tool")
            
        Set settings:
            sm = SettingsManager()
            sm.set("external", "diff_tool", "/usr/bin/meld")
            sm.write()
    """
    
    def __init__(self):
    
        if not os.path.exists(SETTINGS_FILE):
            self.use_default_settings()
            self.write()
    
        self.settings = configobj.ConfigObj(
            SETTINGS_FILE, 
            indent_type="    "
        )

    def get(self, section=None, keyword=None):
        """
        Get the settings for a section and/or keyword
        If no arguments are given, it just returns all settings
        
        @type section:  string
        @param section: A settings section.
        
        @type keyword:  string
        @param keyword: A particular setting in a section.
        
        @rtype:         dictionary or string
        @return:        Either a dictionary or string with setting(s).
        
        """
        
        if section is None:
            return self.settings
            
        if keyword is None:
            return self.settings[section]
        
        returner = ""
        try:
            returner = self.settings[section][keyword]
        except KeyError:
            print "Error: section %s:%s doesn't exist" % (section, keyword)
            
        return returner
        
    def set(self, section, keyword, value=""):
        """
        Set settings for a particular section and keyword

        @type section:  string
        @param section: A settings section.
        
        @type keyword:  string
        @param keyword: A particular setting in a section.
        
        @type value:    string or dictionary
        @param value:   Setting value.

        """
        
        if section not in self.settings:
            self.settings[section] = {}
            
        if value == True:
            value = 1
        elif value == False:
            value = 0
        
        self.settings[section][keyword] = value
            
    def set_comments(self, section, comments=[]):
        """
        Set multi-line comments for a section
        
        @type section:      string
        @param section:     A settings section.
        
        @type comments:     list
        @param comments:    A list of strings.
        
        """

        self.settings.comments[section] = comments
        
    def set_inline_comments(self, section, comments=""):
        """
        Set inline comments for a section
        
        @type section:      string
        @param section:     A settings section.
        
        @type comments:     string
        @param comments:    A single line comment.
        
        """

        self.settings.inline_comments[section] = comments
        
    def write(self):
        """
        Write the settings and comments to the settings file
        
        """
        
        self.settings.write()
        
    def clear(self):
        """
        Clear the settings object so that all sections/keywords are gone
        This function does not write-to-file.  Only clears from memory.
        
        """
        self.settings = configobj.ConfigObj(indent_type="    ")
        self.settings.filename = SETTINGS_FILE

    def use_default_settings(self):
        """
        Specify a set of default settings and write to file.
        Called when there is no settings.conf present.
        
        """
        
        self.settings = configobj.ConfigObj(
            DEFAULT_SETTINGS,
            indent_type="    "
        )
        self.settings.filename = SETTINGS_FILE
    
    def get_default(self, section, keyword):
        """
        Get the default settings for a section and/or keyword
        If no arguments are given, it just returns all settings
        
        @type section:  string
        @param section: A settings section.
        
        @type keyword:  string
        @param keyword: A particular setting in a section.
        
        @rtype:         dictionary or string
        @return:        Either a dictionary or string with setting(s).
        
        """
        
        if section is None:
            return DEFAULT_SETTINGS
            
        if keyword is None:
            return DEFAULT_SETTINGS[section]
        
        returner = None
        try:
            returner = DEFAULT_SETTINGS[section][keyword]
        except KeyError:
            print "Error: section %s:%s doesn't exist" % (section, keyword)
            
        return returner

if __name__ == "__main__":
    pass
