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

UI layer.

"""

import os

import pygtk
import gobject
import gtk
import gtk.glade

from nautilussvn import APP_NAME, LOCALE_DIR

class InterfaceView:
    """
    Every ui window should inherit this class and send it the "self"
    variable, the glade filename (without the extension), and the id of the
    main window widget.
    
    When calling from the __main__ area (i.e. a window is opened via CLI,
    call the register_gtk_quit method to make sure the main app quits when
    the app is destroyed or finished.
    
    """
    
    def __init__(self, filename, id):
        path = "%s/glade/%s.glade" % (
            os.path.dirname(os.path.realpath(__file__)), 
            filename
        )
        gtk.glade.bindtextdomain(APP_NAME, LOCALE_DIR)
        gtk.glade.textdomain(APP_NAME)
        self.tree = gtk.glade.XML(path, id, APP_NAME)
        self.tree.signal_autoconnect(self)
        self.id = id
        self.do_gtk_quit = False
        
    def get_widget(self, id):
        return self.tree.get_widget(id)
        
    def hide(self):
        self.get_widget(self.id).set_property('visible', False)
        
    def show(self):
        self.get_widget(self.id).set_property('visible', True)
    
    def close(self):
        window = self.get_widget(self.id)
        if window is not None:
            window.destroy()
        if self.do_gtk_quit:
            gtk.main_quit()
            
    def register_gtk_quit(self):
        self.do_gtk_quit = True
    
    def gtk_quit_is_set(self):
        return self.do_gtk_quit
        
class InterfaceNonView:
    """
    Provides a way for an interface to handle quitting, etc without having
    to have a visible interface.
    
    """
    
    def __init__(self, ):
        self.do_gtk_quit = False

    def close(self):
        if self.do_gtk_quit:
            gtk.main_quit()
            
    def register_gtk_quit(self):
        self.do_gtk_quit = True
    
    def gtk_quit_is_set(self):
        return self.do_gtk_quit

def main():
    from os import getcwd
    from sys import argv
    from optparse import OptionParser
    from nautilussvn.lib.helper import get_common_directory
    
    parser = OptionParser()
    parser.add_option("--base-dir")
    (options, args) = parser.parse_args(argv)
    
    # Convert "." to current working directory
    paths = args[1:]
    for i in range(0, len(paths)):
        if paths[i] == ".":
            paths[i] = getcwd()
        
    if not paths:
        paths = [getcwd()]
        
    if not options.base_dir: 
        options.base_dir = get_common_directory(paths)
        
    return (options, paths)
    
