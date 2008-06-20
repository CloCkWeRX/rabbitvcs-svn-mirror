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
import shutil

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
		self.frame = res.LoadFrame(None, "CommitFrame")
		self.frame.SetTitle("Committing %s"%(os.path.split(path)[-1]))
		self.frame.SetIcon(wx.Icon(GetPath("svn.ico"), wx.BITMAP_TYPE_ICO))
		self.frame.SetSize((800,600))
		self.frame.Centre()

		self.SetTopWindow(self.frame)
		self.frame.Show()

		self.commitMessage = None

		wx.EVT_BUTTON(self.frame, XRCID("Commit"), self.OnCommit)
		wx.EVT_LISTBOX_DCLICK(self.frame, XRCID("ChangedFiles"), self.OnDiffFile)

		list = XRCCTRL(self.frame, "ChangedFiles")
		c = pysvn.Client()

		status_dict = {	pysvn.wc_status_kind.modified : "Modified : ",
						pysvn.wc_status_kind.added: 	"Added : ",
						pysvn.wc_status_kind.deleted: 	"Deleted : ",
						pysvn.wc_status_kind.replaced: 	"Replaced : ",
						}

		for st in c.status(path):
			if st.text_status in status_dict:
				list.Append(status_dict[st.text_status] + st.path.split(basedir)[-1])

		return True

	#--------------------------------------------------------------------------
	def OnDiffFile(self, evt):
		path = XRCCTRL(self.frame, "ChangedFiles").GetStringSelection()
		if not "Modified" in path:
			return

		path = path[len("Modified : ") + 1:]
		path = os.path.join(basedir, path)

		c = pysvn.Client()
		entry = c.info(path)

		df = os.popen("svn diff %s"%path).read()
		open("/tmp/tmp.patch", "w").write(df)
		shutil.copy(path, "/tmp")
		x = os.popen("patch --reverse /tmp/%s < /tmp/tmp.patch"%(os.path.split(path)[-1]))
		os.spawnl(os.P_NOWAIT, os.path.join("/usr/bin/", DIFF_TOOL), DIFF_TOOL, path, os.path.join("/tmp/", os.path.split(path)[-1]))

	#-------------------------------------------------------------------------- 
	def OnCommit(self, evt):
		ctrl = XRCCTRL(self.frame, "Message")
		self.commitMessage = ctrl.GetValue()
		self.frame.Close()

#============================================================================== 
# First pop up the commit dialog

path = sys.argv[1]

if os.path.isdir(path):
	basedir = path
else:
	basedir = os.path.split(path)[0]

app = MyApp(0)
app.MainLoop()

# Then actually commit the data if we have a commit message
if app.commitMessage:
	msg = app.commitMessage
	del app

	app = MessageBoxApp(0)
	app.SetFunc("checkin", path, msg)
	app.MainLoop()
