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

import pysvn
import os
import sys
import wx
import wx.xrc
from wx.xrc import XRCCTRL, XRCID

from SvnMessageBox import *
from helper import *

#============================================================================== 
class MyApp(wx.App):

	#-------------------------------------------------------------------------- 
	def OnInit(self):
		res = wx.xrc.EmptyXmlResource()
		xrcpath = GetPath("NautilusSvn.xrc")
		res.Load(xrcpath)
		self.frame = res.LoadFrame(None, "CheckoutFrame")

		self.SetTopWindow(self.frame)
		self.frame.Fit()
		x,y = self.frame.GetSize()
		x = max(x, 800)
		self.frame.SetSize((x,y))
		self.frame.SetIcon(wx.Icon(GetPath("svn.ico"), wx.BITMAP_TYPE_ICO))
		self.frame.Centre()
		self.frame.Show()

		self.checkoutValid = False
		
		XRCCTRL(self.frame, "LocalPath").SetValue(sys.argv[1])

		wx.EVT_BUTTON(self.frame, XRCID("FindURL"), self.OnFindURL)
		wx.EVT_BUTTON(self.frame, XRCID("FindRevision"), self.OnFindRevision)
		wx.EVT_BUTTON(self.frame, XRCID("FindLocalPath"), self.OnFindLocalPath)
		wx.EVT_BUTTON(self.frame, XRCID("Checkout"), self.OnCheckout)

		file_path = GetPath(".repos_paths")
		if os.path.exists(file_path):
			paths = [x.strip() for x in open(file_path, "r").readlines()]
			for p in paths:
				XRCCTRL(self.frame, "URL").Append(p)

		return True

	#--------------------------------------------------------------------------
	def OnFindURL(self, evt):
		url = XRCCTRL(self.frame, "URL").GetValue()
		os.spawnl(os.P_NOWAIT, "/usr/bin/firefox", "firefox", url)

	#--------------------------------------------------------------------------
	def OnFindRevision(self, evt):
		url = XRCCTRL(self.frame, "URL").GetValue()
		os.spawnl(os.P_NOWAIT, "/usr/bin/python", "python", GetPath("SvnLog.py"), "%s"%url)

	#--------------------------------------------------------------------------
	def OnFindLocalPath(self, evt):
		dlg = wx.DirDialog(self.frame)
		if dlg.ShowModal() == wx.ID_OK:
			XRCCTRL(self.frame, "LocalPath").SetValue(dlg.GetPath())

	#--------------------------------------------------------------------------
	def OnCheckout(self, evt):
		self.remotePath = XRCCTRL(self.frame, "URL").GetValue()
		self.localPath = os.path.expanduser(XRCCTRL(self.frame, "LocalPath").GetValue())
		self.revision = XRCCTRL(self.frame, "Revision").GetValue()
		self.checkoutValid = True

		self.frame.Close()

#============================================================================== 
# First pop up the commit dialog

app = MyApp(0)
app.MainLoop()

if app.checkoutValid:
	remotePath = app.remotePath
	localPath = app.localPath
	revision = app.revision

	del app

	app = MessageBoxApp(0)
	if revision.lower() == "head":
		app.SetFunc("checkout", remotePath, localPath, revision=pysvn.Revision(pysvn.opt_revision_kind.head))
	else:
		app.SetFunc("checkout", remotePath, localPath, revision=pysvn.Revision(pysvn.opt_revision_kind.number, revision))
	app.MainLoop()
