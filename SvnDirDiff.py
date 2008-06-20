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
import shutil

import wx
import wx.xrc
from wx.xrc import XRCCTRL, XRCID

from helper import *

#============================================================================== 

class DirDiffApp(wx.App):

	#-------------------------------------------------------------------------- 
	def SetFunc(self, svnFunc, *args, **kwargs):
		self._args = args
		self._kwargs = kwargs
		self._svnFunc = svnFunc

	#-------------------------------------------------------------------------- 
	def OnInit(self):

		path = sys.argv[1]

		res = wx.xrc.EmptyXmlResource()
		xrcpath = GetPath("NautilusSvn.xrc")
		res.Load(xrcpath)
		self.frame = res.LoadFrame(None, "DirDiffFrame")
		self.frame.SetSize((800,500))
		self.frame.Centre()
		self.frame.SetTitle("Directory Diff - %s"%path)
		self.frame.SetIcon(wx.Icon(GetPath("svn.ico"), wx.BITMAP_TYPE_ICO))

		wx.EVT_BUTTON(self.frame, XRCID("OK"), self.OnOK)
		wx.EVT_LISTBOX_DCLICK(self.frame, XRCID("ChangedFiles"), self.OnDiffFile)

		files = {}
		for line in os.popen("svn diff %s"%path).readlines():
			if line[:3] in ["---", "+++"]:
				file = line[4:line.find("(")].strip()
				files[file] = 1

		if not len(files.keys()):
			XRCCTRL(self.frame, "ChangedFiles").Append("No modified files found.")
		else:
			for x in files.keys():
				XRCCTRL(self.frame, "ChangedFiles").Append(x)

		self.SetTopWindow(self.frame)
		self.frame.Show()

		return True

	#--------------------------------------------------------------------------
	def OnDiffFile(self, evt):

		if not CheckDiffTool(): return

		path = XRCCTRL(self.frame, "ChangedFiles").GetStringSelection()

		if path == "No modified files found.":
			return

		c = pysvn.Client()
		entry = c.info(path)

		df = os.popen("svn diff %s"%path).read()
		open("/tmp/tmp.patch", "w").write(df)
		shutil.copy(path, "/tmp")
		x = os.popen("patch --reverse /tmp/%s < /tmp/tmp.patch"%(os.path.split(path)[-1]))
		os.spawnl(os.P_NOWAIT, os.path.join("/usr/bin/", DIFF_TOOL), DIFF_TOOL, path, os.path.join("/tmp/", os.path.split(path)[-1]))

	#-------------------------------------------------------------------------- 
	def OnOK(self, evt):
		self.frame.Close()

#============================================================================== 

app = DirDiffApp(0)
app.MainLoop()
