#==============================================================================
""" Copyright Jason Field 2006

    This file is part of NautilusSvn.

    NautilusSvn is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    NautilusSvn is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with NautilusSvn; if not, write to the Free Software
    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""
#==============================================================================

import sys
import os
import threading
import pysvn
import wx
import wx.xrc
import Queue
from wx.xrc import XRCCTRL, XRCID

from helper import *

#============================================================================== 

class MessageBoxApp(wx.App):
    """ Displays a box which monitors the return messages from SVN and displays
        them for the user.

        Note that the QueueFunc system is used below to allow the GUI to update
        in a thread-safe manner.
    """

    #-------------------------------------------------------------------------- 
    def SetFunc(self, svnFunc, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._svnFunc = svnFunc

    #-------------------------------------------------------------------------- 
    def OnInit(self):
        self.res = wx.xrc.EmptyXmlResource()
        xrcpath = GetPath("NautilusSvn.xrc")
        self.res.Load(xrcpath)
        self.frame = self.res.LoadFrame(None, "MessageFrame")
        self.frame.SetSize((550,300))
        self.frame.SetIcon(wx.Icon(GetPath("svn.ico"), wx.BITMAP_TYPE_ICO))
        self.frame.Centre()

        XRCCTRL(self.frame, "OK").Enable(False)

        wx.EVT_IDLE(self.frame, self.OnMainIdle)
        wx.EVT_BUTTON(self.frame, XRCID("OK"), self.OnOK)

        self.SetTopWindow(self.frame)
        self.frame.Show()

        self._funcQueue = Queue.Queue()
        self._threadStarted = False
        self._thread = threading.Thread(target=self.ThreadProc)
        self._gotDetails = threading.Event()
        self._gotSSL = threading.Event()
        self._inErrorState = False
        
        return True

    #-------------------------------------------------------------------------- 
    def OnOK(self, evt):
        """ OK button message handler
        """
        self.frame.Close()

    #--------------------------------------------------------------------------
    def OnGetLoginDetails(self, realm, username, may_save):
        """ This is the hook point if the SVN server requires a login. Since
            this can happen outside of the main GUI thread, we need to use our
            message queue to open up a dialog prompt for the user.
        """
        if self._inErrorState:
            if self._loginDialog:
                self._loginDialog.Close()
            return (False, "", "", False)

        self._gotDetails.clear()
        self.QueueFunc(self.GetLoginDetails, realm, username, may_save)
        self._gotDetails.wait()
        return self._loginDetails

    #--------------------------------------------------------------------------
    def GetLoginDetails(self, realm, username, may_save):
        """ Shows a dialog prompting the user for login details.
        """

        self._loginDialog = self.res.LoadDialog(self.frame, "AuthDialog")

        server, prompt = realm[1:].split(">")
        XRCCTRL(self._loginDialog, "Location").SetLabel(server)
        XRCCTRL(self._loginDialog, "Realm").SetLabel(prompt)
        XRCCTRL(self._loginDialog, "Username").SetValue(username)
        XRCCTRL(self._loginDialog, "Password").SetFocus()

        wx.EVT_BUTTON(self._loginDialog, XRCID("OK"), self.OnLoginDetailsOK)

        self._loginDialog.Fit()
        self._loginDialog.ShowModal()
        self._loginDetails = (False, "", "", False)
        self._gotDetails.set()

    #--------------------------------------------------------------------------
    def OnLoginDetailsOK(self, evt):
        """ OK button handler for the Login details page.
        """
        username = XRCCTRL(self._loginDialog, "Username").GetValue()
        password = XRCCTRL(self._loginDialog, "Password").GetValue()
        save = XRCCTRL(self._loginDialog, "SaveDetails").GetValue()
        self._loginDetails = (True, str(username), str(password), save)
        self._loginDialog.Close()
        self._gotDetails.set()

    #--------------------------------------------------------------------------
    def OnServerTrustPrompt(self, trust_dict):
        """ This is the hook point if the server provides a certificate that we
            don't already know about.
        """
        self._gotSSL.clear()
        self._sslDetails = (False, 0, False)
        self.QueueFunc(self.GetServerTrustDetails, trust_dict)
        self._gotSSL.wait()
        return self._sslDetails

    #--------------------------------------------------------------------------
    def GetServerTrustDetails(self, trust_dict):
        """ Pops up a dialog showing the user details of the certificate that
            they need to approve.
        """
        self._sslDialog = self.res.LoadDialog(self.frame, "CertificateDialog")
        XRCCTRL(self._sslDialog, "Realm").SetLabel(trust_dict["realm"])
        XRCCTRL(self._sslDialog, "Host").SetLabel(trust_dict["hostname"])
        XRCCTRL(self._sslDialog, "Issuer").SetLabel(trust_dict["issuer_dname"])
        XRCCTRL(self._sslDialog, "Valid").SetLabel(trust_dict["valid_from"] + " to " + trust_dict["valid_until"])
        XRCCTRL(self._sslDialog, "Fingerprint").SetLabel(trust_dict["finger_print"])

        wx.EVT_BUTTON(self._sslDialog, XRCID("AcceptOnce"), self.OnServerTrustAcceptOnce)
        wx.EVT_BUTTON(self._sslDialog, XRCID("AcceptForever"), self.OnServerTrustAcceptForever)
        wx.EVT_BUTTON(self._sslDialog, XRCID("Deny"), self.OnServerTrustDeny)

        self._sslDialog.ShowModal()

    #--------------------------------------------------------------------------
    def OnServerTrustAcceptOnce(self, evt):
        """ Handle the Server Certificate dialog 'Accept Once' button.
        """
        self._sslDetails = (True, 0, False)
        self._gotSSL.set()
        self._sslDialog.Close()

    #--------------------------------------------------------------------------
    def OnServerTrustAcceptForever(self, evt):
        """ Handle the Server Certificate dialog 'Accept Forever' button.
        """
        self._sslDetails = (True, 0, True)
        self._gotSSL.set()
        self._sslDialog.Close()

    #--------------------------------------------------------------------------
    def OnServerTrustDeny(self, evt):
        """ Handle the Server Certificate dialog 'Deny' button.
        """
        self._sslDetails = (False, 0, False)
        self._gotSSL.set()
        self._sslDialog.Close()

    #-------------------------------------------------------------------------- 
    def ThreadProc(self):
        """ Thread function that handles firing off request to the SVN server
            outside of the main GUI thread.
        """
        c = pysvn.Client()
        c.callback_notify = self.OnSvnNotify
        c.callback_get_login = self.OnGetLoginDetails
        c.callback_ssl_server_trust_prompt = self.OnServerTrustPrompt
        list = XRCCTRL(self.frame, "Messages")
        # Fire off our function call
        try:
            getattr(c, self._svnFunc)(*self._args, **self._kwargs)
            self.QueueFunc(list.AppendText, "Done.\n")
            XRCCTRL(self.frame, "OK").Enable()
        except Exception, e:
            # Print exceptions to the log window
            self.QueueFunc(list.AppendText, "Error : " + str(e) + "\n")
            self.QueueFunc(self.SetErrorState)
            XRCCTRL(self.frame, "OK").Enable()

    #--------------------------------------------------------------------------
    def SetErrorState(self):
        """ Handles errors coming back from the Subversion server
        """
        self._inErrorState = True

    #-------------------------------------------------------------------------- 
    def OnMainIdle(self, evt):
        """ Idle handler for the GUI. We use it to fire off functions that have
            been requested by interactions with the SVN server.
        """
        if not self._threadStarted:
            self._thread.start()
            self._threadStarted = True

        if not self._funcQueue.empty():
            fx = self._funcQueue.get()
            fx[0](*fx[1], **fx[2])

            evt.RequestMore()

    #-------------------------------------------------------------------------- 
    def QueueFunc(self, func, *args, **kwargs):
        """ Adds a function to the idle processing queue.
        """
        self._funcQueue.put((func, args, kwargs))
        wx.WakeUpIdle()

    #-------------------------------------------------------------------------- 
    def OnSvnNotify( self, event ):
        """ We got a notification message from the SVN server.
        """
        list = XRCCTRL(self.frame, "Messages")
        action_dict = {
                        pysvn.wc_notify_action.update_update:        "Updating",
                        pysvn.wc_notify_action.update_completed:    "Completed",
                        pysvn.wc_notify_action.update_add:            "Adding",
                        pysvn.wc_notify_action.update_delete:        "Deleting",

                        pysvn.wc_notify_action.restore:                "Restoring",

                        pysvn.wc_notify_action.commit_added:        "Sending new file",
                        pysvn.wc_notify_action.commit_deleted:        "Deleting",
                        pysvn.wc_notify_action.commit_modified:        "Sending changes to",
                        }

        if event["action"] in action_dict:
            self.QueueFunc(list.AppendText, "%s %s\n"%(action_dict[event["action"]], event["path"]))
            self.QueueFunc(list.Refresh)

        self.frame.Refresh()

#============================================================================== 
