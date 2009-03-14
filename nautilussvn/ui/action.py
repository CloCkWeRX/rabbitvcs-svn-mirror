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

from __future__ import division
import threading

import pygtk
import gobject
import gtk

from nautilussvn.ui import InterfaceView
import nautilussvn.ui.widget
import nautilussvn.ui.dialog
import nautilussvn.lib
import nautilussvn.lib.vcs
import nautilussvn.lib.helper
from nautilussvn.lib.decorators import gtk_unsafe

from nautilussvn import gettext
_ = gettext.gettext

gtk.gdk.threads_init()

class Notification(InterfaceView):
    """
    Provides an interface to handle the Notification UI.
    
    """
    
    def __init__(self, callback_cancel=None, visible=True):
        """
        @type   callback_cancel: def
        @param  callback_cancel: A method to call when cancel button is clicked.
        
        @type   visible: boolean
        @param  visible: Show the notification window.  Defaults to True.
        
        """
        
        InterfaceView.__init__(self, "notification", "Notification")
        
        if visible:
            self.show()
    
        self.table = nautilussvn.ui.widget.Table(
            self.get_widget("table"),
            [gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Action"), _("Path"), _("Mime Type")]
        )
        
        self.pbar = nautilussvn.ui.widget.ProgressBar(
            self.get_widget("pbar")
        )
        self.pbar.start_pulsate()
        
        self.callback_cancel = callback_cancel
        self.canceled = False
        self.finished = False
            
    def on_destroy(self, widget):
        self.close()
    
    def on_cancel_clicked(self, widget):

        if self.canceled or self.finished:
            self.close();

        if self.callback_cancel is not None:
            self.callback_cancel()

        self.canceled = True
        
    def on_ok_clicked(self, widget):
        self.close()

    def toggle_ok_button(self, sensitive):
        gtk.gdk.threads_enter()
        self.finished = True
        self.get_widget("ok").set_sensitive(sensitive)
        gtk.gdk.threads_leave()
            
    def append(self, entry):
        gtk.gdk.threads_enter()
        self.table.append(entry)
        self.table.scroll_to_bottom()
        gtk.gdk.threads_leave()
    
    def get_title(self):
        return self.get_widget("Notification").get_title()
    
    def set_title(self, title):
        gtk.gdk.threads_enter()
        self.get_widget("Notification").set_title(title)
        gtk.gdk.threads_leave()
        
    def set_header(self, header):
        self.set_title(header)
        gtk.gdk.threads_enter()
        self.get_widget("action").set_markup(
            "<span font_size=\"xx-large\"><b>%s</b></span>" % header
        )
        gtk.gdk.threads_leave()

    def focus_on_ok_button(self):
        self.get_widget("ok").grab_focus()

class VCSAction(threading.Thread):
    """
    Provides a central interface to handle vcs actions & callbacks.
    Loads UI elements that require user interaction.
    
    """
    
    def __init__(self, client, register_gtk_quit=False, notification=True):
        threading.Thread.__init__(self)
        
        self.message = _("Empty Message")
        
        self.client = client
        self.client.set_callback_cancel(self.cancel)
        self.client.set_callback_notify(self.notify)
        self.client.set_callback_get_log_message(self.get_log_message)
        self.client.set_callback_get_login(self.get_login)
        self.client.set_callback_ssl_server_trust_prompt(self.get_ssl_trust)
        self.client.set_callback_ssl_client_cert_password_prompt(self.get_ssl_password)
        
        self.queue = nautilussvn.lib.FunctionQueue()
        
        self.login_tries = 0
        self.cancel = False

        self.notification = Notification(
            callback_cancel=self.set_cancel,
            visible=notification
        )
        
        self.pbar_ticks = None
        self.pbar_ticks_current = -1
        
        # Tells the notification window to do a gtk.main_quit() when closing
        # Is used when the script is run from a command line
        if register_gtk_quit:
            self.notification.register_gtk_quit()

    def set_pbar_ticks(self, num):
        """
        Set the total number of ticks to represent in the progress bar.
        Each time the notify method is called, update the pbar fraction.
        If this function isn't called, the progress bar just pulsates.
        
        @type   num: integer
        @param  num: The number of ticks in the progress bar.
        """
        
        self.pbar_ticks = num
    
    def set_header(self, header):
        self.notification.set_header(header)
    
    def cancel(self):
        """
        PySVN calls this callback method frequently to see if the user wants
        to cancel the action.  If self.cancel is True, then it will cancel
        the action.  If self.cancel is False, it will continue.
        
        """
        
        return self.cancel

    def set_cancel(self, cancel=True):
        """
        Used as a callback function by the Notification UI.  When the cancel
        button is clicked, it sets self.cancel to True, and the cancel callback
        method returns True.
        
        """
        
        self.cancel = cancel
        self.queue.cancel_queue()
    
    def notify(self, data):
        """
        This method is called every time the VCS function wants to tell us
        something.  It passes us a dictionary of useful information.  When
        this method is called, it appends some useful data to the notifcation
        window.
        
        TODO: We need to implement this in a more VCS-agnostic way, since the
        supplied data dictionary is pysvn-dependent.  I'm going to implement
        something in lib/vcs/svn.py soon.
        
        """

        if self.pbar_ticks is not None:
            self.pbar_ticks_current += 1
            frac = self.pbar_ticks_current / self.pbar_ticks
            if frac > 1:
                frac = 1
            self.notification.pbar.update(frac)
        
        try:
            action = self.client.NOTIFY_ACTIONS[data["action"]]
        except:
            action = data["action"]
            
        self.notification.append([
            action,
            data["path"],
            data["mime_type"]
        ])
        
        if data["action"] in self.client.NOTIFY_ACTIONS_COMPLETE:
            self.notification.append(
                ["", "Revision %s" % data["revision"].number, ""]
            )
    
    def finish(self, message=None):
        """
        This is called when the final notifcation message has been received,
        or it is called manually when no final notification message is expected.
        
        It sets the current "status", and enables the OK button to allow
        the user to leave the window.
        
        @type   message: string
        @param  message: A message to show the user.
        
        """

        self.notification.append(
            ["", _("Finished"), ""]
        )
        self.notification.focus_on_ok_button()
        title = self.notification.get_title()
        self.notification.set_title(_("%s - Finished") % title)
        self.set_status(message)
        self.notification.pbar.stop_pulsate()
        self.notification.pbar.update(1)
        self.notification.toggle_ok_button(True)
    
    def get_log_message(self):
        """
        A callback method that retrieves a supplied log message.
        
        Returns a list where the first element is True/False.  Returning true
        tells the action to continue, false tells it to cancel.  The second
        element is the log message, which is specified by self.message.
        self.message is set by calling the self.set_log_message() method from
        the UI interface class.
        
        @rtype:  (boolean, string)
        @return: (True=continue/False=cancel, log message)
        
        """
        
        return True, self.message.encode("utf-8")
    
    def get_login(self, realm, username, may_save):
        """
        A callback method that requests a username/password to login to a 
        password-protected repository.  This method runs the Authentication
        dialog, which provides a username, password, and saving widget.  The
        dialog returns a tuple, which is returned directly to the VCS caller.
        
        If the login fails greater than three times, cancel the action.
        
        The dialog must be called from within a threaded block, otherwise it
        will not be responsive.
        
        @type   realm:      string
        @param  realm:      The realm of the repository.
        
        @type   username:   string
        @param  username:   Username passed by the vcs caller.
        
        @type   may_save:   boolean
        @param  may_save:   Whether or not the authentication can be saved.
        
        @rtype:             (boolean, string, string, boolean)
        @return:            (True=continue/False=cancel, username,password, may_save)
        
        """
    
        if self.login_tries >= 3:
            return (False, "", "", False)
    
        gtk.gdk.threads_enter()
        dialog = nautilussvn.ui.dialog.Authentication(
            realm,
            may_save
        )
        result = dialog.run()
        gtk.gdk.threads_leave()
        
        if result is not None:
            self.login_tries += 1
        
        return result
    
    def get_ssl_trust(self, data):
        """
        A callback method that requires the user to either accept or deny
        a certificate from an ssl secured repository.  It opens a dialog that
        shows the user information about the ssl certificate and then gives
        them the option of denying, accepting, or accepting once.

        The dialog must be called from within a threaded block, otherwise it
        will not be responsive.

        @type   data:   dictionary
        @param  data:   A dictionary with SSL certificate info.
        
        @rtype:         (boolean, int, boolean)
        @return:        (True=Accept/False=Deny, number of accepted failures, remember)
        
        """
    
        ACCEPTED_FAILURES = 3
    
        gtk.gdk.threads_enter()

        if not data:
            return (False, 0, False)

        dialog = nautilussvn.ui.dialog.Certificate(
            data["realm"],
            data["hostname"],
            data["issuer_dname"],
            data["valid_from"],
            data["valid_until"],
            data["finger_print"]
        )
        result = dialog.run()
        gtk.gdk.threads_leave()

        if result == 0:
            #Deny
            return (False, 0, False)
        elif result == 1:
            #Accept Once
            return (True, 0x8, False)
        elif result == 2:
            #Accept Forever
            return (True, 0x8, True)

    def get_ssl_password(self, realm, may_save):
        """
        A callback method that is used to get an ssl certificate passphrase.
        
        The dialog must be called from within a threaded block, otherwise it
        will not be responsive.       

        @type   realm:      string
        @param  realm:      The certificate realm.
        
        @type   may_save:   boolean
        @param  may_save:   Whether or not the passphrase can be saved.
        
        @rtype:             (boolean, string, boolean)
        @return:            (True=continue/False=cancel, password, may save)
        
        """
        
        gtk.gdk.threads_enter()
        dialog = nautilussvn.ui.dialog.CertAuthentication(
            realm,
            may_save
        )
        result = dialog.run()
        gtk.gdk.threads_leave()

        return result
        
    def set_log_message(self, message):
        """
        Set this action's log message from the UI interface.  self.message
        is referred to when the VCS does the get_log_message callback.
        
        @type   message: string
        @param  message: Set a log message.
        
        """
        
        self.message = message
    
    @gtk_unsafe
    def set_status(self, message):
        """
        Set the current status of the VCS action.  Currently, this method
        is called at the beginning and end of each action, to display what is
        going on.  Currently, it just appends the status message to the 
        notification window.  In the future, I may set up a progress bar
        and put the status message there.
        
        @type   message: string
        @param  message: A status message.
        
        """
        
        if message is not None:
            self.notification.get_widget("status").set_text(message)
    
    def append(self, func, *args, **kwargs):
        """
        Append a function call to the action queue.
        
        """
        
        self.queue.append(func, *args, **kwargs)
    
    def get_result(self, index):
        """
        Retrieve the result of a single function call by specifying the order
        in which the function was in the queue.
        
        @type   index: int
        @param  index: The queue index
        
        """
        
        return self.queue.get_result(index)
    
    def callback_queue_exception(self, e):
        self.notification.append(
            ["", str(e), ""]
        )
        self.finish()
    
    def run(self):
        """
        The central method that drives this class.  It runs the before and 
        after methods, as well as the main vcs method.
        
        """
        
        self.queue.set_exception_callback(self.callback_queue_exception)
        self.queue.start()
