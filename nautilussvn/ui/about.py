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

import os.path
import string

import pygtk
import gobject
import gtk

import nautilussvn
from nautilussvn.ui import InterfaceView
import nautilussvn.ui.widget
import pysvn
import configobj

from nautilussvn import gettext
_ = gettext.gettext

class About(InterfaceView):
    """
    This class provides an interface to the About window.
    
    Displays:
    
      - Authors/Credits
      - Version Information
      - Links
    
    """

    def __init__(self):
        InterfaceView.__init__(self, "about", "About")
        
        doc_path = "/usr/share/doc/nautilussvn"
        if not os.path.exists(doc_path):
            # Assumes the user is running NautilusSvn through an svn checkout
            # and the doc files are two directories up (from nautilussvn/ui).
            doc_path = os.path.dirname(os.path.realpath(__file__)).split('/')
            doc_path = '/'.join(doc_path[:-2])
        
        authors_path = os.path.join(doc_path, "AUTHORS")
        thanks_path = os.path.join(doc_path, "THANKS")
        
        authors = open(authors_path, "r").read()
        thanks = open(thanks_path, "r").read()
        
        self.get_widget("authors").set_text(authors)
        thanks_widget = nautilussvn.ui.widget.TextView(
            self.get_widget("thanks"),
            thanks
        )
        
        versions = []
        versions.append("NautilusSvn - %s" % str(nautilussvn.version))
        versions.append("Subversion - %s" % string.join(map(str,pysvn.svn_version), "."))
        versions.append("Pysvn - %s" % string.join(map(str,pysvn.version), "."))
        versions.append("ConfigObj - %s" % str(configobj.__version__))
        
        self.get_widget("versions").set_text("\n".join(versions))

    def on_destroy(self, widget):
        self.close()

    def on_close_clicked(self, widget):
        self.close()
        
if __name__ == "__main__":
    window = About()
    window.register_gtk_quit()
    gtk.main()
