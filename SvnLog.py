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
import pysvn
import time
import shutil
import tempfile

import wx
import wx.xrc
from wx.xrc import XRCCTRL, XRCID

from helper import *

import threading
import Queue

#============================================================================== 
class MyApp(wx.App):

	#-------------------------------------------------------------------------- 
	def OnInit(self):
		self.res = wx.xrc.EmptyXmlResource()
		xrcpath = GetPath("NautilusSvn.xrc")
		self.res.Load(xrcpath)
		self.frame = self.res.LoadFrame(None, "LogFrame")
		self.frame.SetTitle("Log for %s"%(os.path.split(path)[-1]))
		self.frame.SetIcon(wx.Icon(GetPath("svn.ico"), wx.BITMAP_TYPE_ICO))
		self.frame.Centre()

		self.SetTopWindow(self.frame)

		list = XRCCTRL(self.frame, "LogList")
		text = XRCCTRL(self.frame, "LogText")
		list.InsertColumn(0, "Revision")
		list.InsertColumn(1, "Message")
		list.InsertColumn(2, "User")
		list.InsertColumn(3, "Date")
		list.SetColumnWidth(1, 550)
		list.SetColumnWidth(3, 250)
		self.frame.SetSize((950,300))

		self.frame.Show()

		self._funcQueue = Queue.Queue()

		t = threading.Thread( target=self.GetLogEntries )
		t.start()

		wx.EVT_LIST_ITEM_SELECTED(self.frame, XRCID("LogList"), self.OnItemSelected)
		wx.EVT_LIST_ITEM_ACTIVATED(self.frame, XRCID("LogList"), self.OnItemDoubleClicked)
		wx.EVT_CHECKBOX(self.frame, XRCID("StopOnCopy"), self.OnStopOnCopyChanged)
		wx.EVT_IDLE(self.frame, self.OnIdle)

		self.path = path

		return True

	#--------------------------------------------------------------------------
	def OnIdle( self, evt ):
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
	def AddLogEntry( self, rev, msg, author, time, entry_idx ):
		list = XRCCTRL(self.frame, "LogList")
		idx = list.GetItemCount()
		list.InsertStringItem(idx, "")
		list.SetStringItem(idx, 0, rev )
		list.SetStringItem(idx, 1, msg )
		list.SetStringItem(idx, 2, author )
		list.SetStringItem(idx, 3, time )
		list.SetItemData(idx, entry_idx )

	#--------------------------------------------------------------------------
	def GetLogEntries( self ):

		self.QueueFunc( wx.BeginBusyCursor )

		text = XRCCTRL(self.frame, "LogText")
		c = pysvn.Client()
		c.callback_ssl_server_trust_prompt = self.OnServerTrustPrompt
		c.callback_get_login = self.OnLoginPrompt
		log = c.log(path, discover_changed_paths=False)
		self.entries = []
		for entry in log:
			self.QueueFunc( 
					self.AddLogEntry,
					str(entry["revision"].number),
					entry["message"].split("\n")[0],
					entry["author"],
					time.strftime("%c", time.localtime(entry["date"])),
					log.index(entry) )
			self.entries.append(entry)

		#text.SetValue(self.entries[list.GetItemData(0)]["message"])

		self.QueueFunc( wx.EndBusyCursor )
	
	#--------------------------------------------------------------------------
	def OnServerTrustPrompt(self, trust_dict):
		self._sslDialog = self.res.LoadDialog(self.frame, "CertificateDialog")
		XRCCTRL(self._sslDialog, "Realm").SetLabel(trust_dict["realm"])
		XRCCTRL(self._sslDialog, "Host").SetLabel(trust_dict["hostname"])
		XRCCTRL(self._sslDialog, "Issuer").SetLabel(trust_dict["issuer_dname"])
		XRCCTRL(self._sslDialog, "Valid").SetLabel(trust_dict["valid_from"] + " to " + trust_dict["valid_until"])
		XRCCTRL(self._sslDialog, "Fingerprint").SetLabel(trust_dict["finger_print"])

		EVT_BUTTON(self._sslDialog, XRCID("AcceptOnce"), self.OnServerTrustAcceptOnce)
		EVT_BUTTON(self._sslDialog, XRCID("AcceptForever"), self.OnServerTrustAcceptForever)
		EVT_BUTTON(self._sslDialog, XRCID("Deny"), self.OnServerTrustDeny)

		self._sslDetails = (False, 0, False)
		self._sslDialog.ShowModal()

		return self._sslDetails

	#--------------------------------------------------------------------------
	def OnServerTrustAcceptOnce(self, evt):
		self._sslDetails = (True, 0, False)
		self._sslDialog.Close()

	#--------------------------------------------------------------------------
	def OnServerTrustAcceptForever(self, evt):
		self._sslDetails = (True, 0, True)
		self._sslDialog.Close()

	#--------------------------------------------------------------------------
	def OnServerTrustDeny(self, evt):
		self._sslDetails = (False, 0, False)
		self._sslDialog.Close()

	#--------------------------------------------------------------------------
	def OnLoginPrompt(self, realm, username, may_save):
		self._loginDialog = self.res.LoadDialog(self.frame, "AuthDialog")

		server, prompt = realm[1:].split(">")
		XRCCTRL(self._loginDialog, "Location").SetLabel(server)
		XRCCTRL(self._loginDialog, "Realm").SetLabel(prompt)
		XRCCTRL(self._loginDialog, "Username").SetValue(username)
		XRCCTRL(self._loginDialog, "Password").SetFocus()

		EVT_BUTTON(self._loginDialog, XRCID("OK"), self.OnLoginDetailsOK)

		self._loginDetails = (False, "", "", False)
		self._loginDialog.ShowModal()
		return self._loginDetails 

	#--------------------------------------------------------------------------
	def OnLoginDetailsOK(self, evt):
		username = XRCCTRL(self._loginDialog, "Username").GetValue()
		password = XRCCTRL(self._loginDialog, "Password").GetValue()
		save = XRCCTRL(self._loginDialog, "SaveDetails").GetValue()
		self._loginDetails = (True, str(username), str(password), save)
		self._loginDialog.Close()
	#--------------------------------------------------------------------------
	def OnItemDoubleClicked(self, evt):
		log = XRCCTRL(self.frame, "LogList")
		sel = log.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
		rev = self.entries[log.GetItemData(sel)]["revision"]

		if not CheckDiffTool(): return

		if os.path.isdir(self.path):
			dlg = wx.MessageDialog(self.frame, "NautilusSvn currently only supports diffs for logs on a single file, not on a folder.", style=wx.OK)
			dlg.ShowModal()

		c = pysvn.Client()
		entry = c.info(self.path)

		# Sort out our temporary storage location
		tmppath = tempfile.mkdtemp()
		patch_path = os.path.join( tmppath, "diff.patch" )
		source_path = os.path.join( tmppath, os.path.split(path)[-1] )
		
		# Get our diff results and write it to a temporary file
		df = os.popen('svn diff -r %d "%s"' % (rev.number, path)).read()
		open( patch_path, "w" ).write(df)

		# Now make a copy of our current file
		shutil.copy(path, tmppath)

		# Apply the diff as a reverse patch to get our original file
		x = os.popen( 'patch --reverse "%(source_path)s" < "%(patch_path)s"' % locals() )
		CallDiffTool(path, source_path)

	#--------------------------------------------------------------------------
	def OnStopOnCopyChanged(self, evt):
		list = XRCCTRL(self.frame, "LogList")

		if evt.Checked():
			if hasattr(self, "copyPoint"):
				list.DeleteAllItems()
				for entry in self.entries[:self.copyPoint + 1]:
					idx = list.GetItemCount()
					list.InsertStringItem(idx, "")
					list.SetStringItem(idx, 0, str(entry["revision"].number))
					list.SetStringItem(idx, 1, entry["message"].split("\n")[0])
					list.SetStringItem(idx, 2, entry["author"])
					list.SetStringItem(idx, 3, time.strftime("%c", time.localtime(entry["date"])))
					list.SetItemData(idx, self.entries.index(entry))
		else:
			if hasattr(self, "copyPoint"):
				list.DeleteAllItems()
				for entry in self.entries:
					idx = list.GetItemCount()
					list.InsertStringItem(idx, "")
					list.SetStringItem(idx, 0, str(entry["revision"].number))
					list.SetStringItem(idx, 1, entry["message"].split("\n")[0])
					list.SetStringItem(idx, 2, entry["author"])
					list.SetStringItem(idx, 3, time.strftime("%c", time.localtime(entry["date"])))
					list.SetItemData(idx, self.entries.index(entry))
			else:
				for entry in self.entries:
					for change in entry["changed_paths"]:
						if change["action"] == "A":
							self.copyPoint = self.entries.index(entry)
							rev = change["copyfrom_revision"]

							c = pysvn.Client()
							e = c.info(self.path)

							orig_url = e.url.replace(change["path"], change["copyfrom_path"])

							log = c.log(orig_url, change["copyfrom_revision"])

							for entry in log:
								idx = list.GetItemCount()
								list.InsertStringItem(idx, "")
								list.SetStringItem(idx, 0, str(entry["revision"].number))
								list.SetStringItem(idx, 1, entry["message"].split("\n")[0])
								list.SetStringItem(idx, 2, entry["author"])
								list.SetStringItem(idx, 3, time.strftime("%c", time.localtime(entry["date"])))
								self.entries.append(entry)
								list.SetItemData(idx, self.entries.index(entry))

	#-------------------------------------------------------------------------- 
	def OnItemSelected(self, evt):
		list = XRCCTRL(self.frame, "LogList")
		text = XRCCTRL(self.frame, "LogText")
		item = list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
		entry = self.entries[list.GetItemData(item)]
		text.SetValue(entry["message"])

		for change in entry["changed_paths"]:
			if change["action"] == "A" and change["copyfrom_path"]:
				# We've been copied from somewhere - add that info to the log message.
				font = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)
				font.SetStyle(wx.FONTSTYLE_ITALIC)
				text.SetDefaultStyle(wx.TextAttr(wx.BLACK, font=font))
				text.AppendText("\nCopied from %s"%change["copyfrom_path"])
		self.frame.Update()

#============================================================================== 

path = sys.argv[1]

app = MyApp(0)
app.MainLoop()
