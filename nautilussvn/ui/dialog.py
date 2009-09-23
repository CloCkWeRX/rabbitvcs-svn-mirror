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

from gettext import gettext as _
import os.path

import pygtk
import gobject
import gtk

from nautilussvn.ui import InterfaceView
import nautilussvn.ui.widget
import nautilussvn.lib.helper

GLADE = 'dialogs'

class PreviousMessages(InterfaceView):
    def __init__(self):
        InterfaceView.__init__(self, GLADE, "PreviousMessages")

        self.message = nautilussvn.ui.widget.TextView(
            self.get_widget("prevmes_message")
        )

        self.message_table = nautilussvn.ui.widget.Table(
            self.get_widget("prevmes_table"),
            [gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Date"), _("Message")]
        )
        self.entries = nautilussvn.lib.helper.get_previous_messages()
        if self.entries is None:
            return None
        
        for entry in self.entries:
            tmp = entry[1]
            if len(tmp) > 80:
                tmp = "%s..." % tmp[0:80]
        
            self.message_table.append([entry[0],tmp])
        
        if len(self.entries) > 0:
            self.message.set_text(self.entries[0][1])
        
    def run(self):
    
        if self.entries is None:
            return None
    
        returner = None
        self.dialog = self.get_widget("PreviousMessages")
        result = self.dialog.run()
        if result == 1:
            returner = self.message.get_text()
        
        self.dialog.destroy()

        return returner

    def on_prevmes_table_button_pressed(self, treeview, event):
        pathinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
        if pathinfo is not None:
            path, col, cellx, celly = pathinfo
            treeview.grab_focus()
            treeview.set_cursor(path, col, 0)
            self.message.set_text(self.entries[path[0]][1])
        
class FolderChooser:
    def __init__(self):
        self.dialog = gtk.FileChooserDialog(_("Select a Folder"), 
            None, 
            gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, 
            (gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,
                gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        self.dialog.set_default_response(gtk.RESPONSE_OK)

    def run(self):
        returner = None
        result = self.dialog.run()
        if result == gtk.RESPONSE_OK:
            returner = self.dialog.get_uri()
        self.dialog.destroy()
        return returner
        
class Certificate(InterfaceView):
    """
    Provides a dialog to accept/accept_once/deny an ssl certificate
    
    """
    
    def __init__(self, realm="", host="", 
            issuer="", valid_from="", valid_until="", fingerprint=""):
            
        InterfaceView.__init__(self, GLADE, "Certificate")
        
        self.get_widget("cert_realm").set_label(realm)
        self.get_widget("cert_host").set_label(host)
        self.get_widget("cert_issuer").set_label(issuer)
        to_str = _("to")
        self.get_widget("cert_valid").set_label(
            "%s %s %s" % (valid_from, to_str, valid_until)
        )
        self.get_widget("cert_fingerprint").set_label(fingerprint)
        
    def run(self):
        """
        Returns three possible values:
        
            - 0   Deny
            - 1   Accept Once
            - 2   Accept Forever
            
        """
        
        self.dialog = self.get_widget("Certificate")
        result = self.dialog.run()
        self.dialog.destroy()
        return result
        
class Authentication(InterfaceView):
    def __init__(self, realm="", may_save=True):
        InterfaceView.__init__(self, GLADE, "Authentication")
        
        self.get_widget("auth_realm").set_label(realm)
        self.get_widget("auth_save").set_sensitive(may_save)
        
    def run(self):
        returner = None
        self.dialog = self.get_widget("Authentication")
        result = self.dialog.run()
        
        login = self.get_widget("auth_login").get_text()
        password = self.get_widget("auth_password").get_text()
        save = self.get_widget("auth_save").get_active()
        self.dialog.destroy()
        
        if result == 1:
            return (True, login, password, save)
        else:
            return (False, "", "", False)

class CertAuthentication(InterfaceView):
    def __init__(self, realm="", may_save=True):
        InterfaceView.__init__(self, GLADE, "CertAuthentication")
        
        self.get_widget("certauth_realm").set_label(realm)
        self.get_widget("certauth_save").set_sensitive(may_save)
        
    def run(self):
        self.dialog = self.get_widget("CertAuthentication")
        result = self.dialog.run()
        
        password = self.get_widget("certauth_password").get_text()
        save = self.get_widget("certauth_save").get_active()
        self.dialog.destroy()
        
        if result == 1:
            return (True, password, save)
        else:
            return (False, "", False)
        
class Property(InterfaceView):
    def __init__(self, name="", value="", recurse=True):
        InterfaceView.__init__(self, GLADE, "Property")
        
        self.save_name = name
        self.save_value = value
        
        self.name = self.get_widget("property_name")
        self.name.set_text(name)
        
        self.value = nautilussvn.ui.widget.TextView(
            self.get_widget("property_value"), 
            value
        )
        
        self.recurse = self.get_widget("property_recurse")
        self.recurse.set_active(recurse)
        
    def run(self):
        self.dialog = self.get_widget("Property")
        result = self.dialog.run()
        
        if result == 1:
            self.save()
        
        self.dialog.destroy()
        return (self.save_name, self.save_value, self.recurse.get_active())
    
    def save(self):
        self.save_name = self.name.get_text()
        self.save_value = self.value.get_text()
        self.save_recurse = self.recurse.get_active()

class FileChooser:
    def __init__(self, title=_("Select a File"), folder=None):
        self.dialog = gtk.FileChooserDialog(title, 
            None, 
            gtk.FILE_CHOOSER_ACTION_OPEN, 
            (gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,
                gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        if folder is not None:
            self.dialog.set_current_folder(folder)
        self.dialog.set_default_response(gtk.RESPONSE_OK)

    def run(self):
        returner = None
        result = self.dialog.run()
        if result == gtk.RESPONSE_OK:
            returner = self.dialog.get_uri()
        self.dialog.destroy()
        return returner
        
class Confirmation(InterfaceView):
    def __init__(self, message=_("Are you sure you want to continue?")):
        InterfaceView.__init__(self, GLADE, "Confirmation")
        self.get_widget("confirm_message").set_text(message)
        
    def run(self):
        dialog = self.get_widget("Confirmation")
        result = dialog.run()
        
        dialog.destroy()
        
        return result
        
class MessageBox(InterfaceView):
    def __init__(self, message):
        InterfaceView.__init__(self, GLADE, "MessageBox")
        self.get_widget("messagebox_message").set_text(message)

        dialog = self.get_widget("MessageBox")
        dialog.run()
        dialog.destroy()

class DeleteConfirmation(InterfaceView):
    def __init__(self, path=None):
        InterfaceView.__init__(self, GLADE, "DeleteConfirmation")
        
        if path:
            path = "\"%s\"" % os.path.basename(path)
        else:
            path = _("the selected item(s)")
            
        msg = self.get_widget("message").get_label().replace("%item%", path)
        self.get_widget("message").set_label(msg)
        
    def run(self):
        dialog = self.get_widget("DeleteConfirmation")
        result = dialog.run()
        
        dialog.destroy()
        
        return result
