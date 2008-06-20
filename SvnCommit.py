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
import time
import re

#============================================================================== 
class MyApp( wx.App ):

	#-------------------------------------------------------------------------- 
	def OnInit( self ):
		self.res = wx.xrc.EmptyXmlResource()
		xrcpath = GetPath( "NautilusSvn.xrc" )
		self.res.Load( xrcpath )
		self.frame = self.res.LoadFrame( None, "CommitFrame" )
		self.frame.SetTitle( "Committing %s"%( os.path.split( path )[-1] ) )
		self.frame.SetIcon( wx.Icon( GetPath( "svn.ico" ), wx.BITMAP_TYPE_ICO ) )
		self.frame.SetSize( ( 800,600 ) )
		self.frame.Centre()

		self.SetTopWindow( self.frame )
		self.frame.Show()

		self.commitMessage = None

		wx.EVT_BUTTON( self.frame, XRCID( "Commit" ), self.OnCommit )
		wx.EVT_BUTTON( self.frame, XRCID( "PreviousMessages" ), self.OnPreviousMessages )
		wx.EVT_LISTBOX_DCLICK( self.frame, XRCID( "ChangedFiles" ), self.OnDiffFile )

		list = XRCCTRL( self.frame, "ChangedFiles" )
		c = pysvn.Client()

		status_dict = {	pysvn.wc_status_kind.modified : "Modified : ",
						pysvn.wc_status_kind.added: 	"Added : ",
						pysvn.wc_status_kind.deleted: 	"Deleted : ",
						pysvn.wc_status_kind.replaced: 	"Replaced : ",
						}

		self.paths = []
		for st in c.status( path ):
			if st.text_status in status_dict:
				self.paths.append( st.path )
				index = list.Append( status_dict[st.text_status] + st.path.split( basedir )[-1] )
				list.Check( index, True )

		return True

	#--------------------------------------------------------------------------
	def OnDiffFile( self, evt ):
		""" Double click handler for the log list. Launches the diff program.
		"""
		path = XRCCTRL( self.frame, "ChangedFiles" ).GetStringSelection()
		if not "Modified" in path:
			return

		path = path[len( "Modified : " ) + 1:]
		path = os.path.join( basedir, path )

		c = pysvn.Client()
		entry = c.info( path )

		df = os.popen( 'svn diff "%s"' % path 	).read()
		open( "/tmp/tmp.patch", "w" ).write( df )
		shutil.copy( path, "/tmp" )
		x = os.popen( 'patch --reverse "/tmp/%s" < /tmp/tmp.patch' % ( os.path.split( path )[-1] ) )
		os.spawnl( os.P_NOWAIT, os.path.join( "/usr/bin/", DIFF_TOOL ), DIFF_TOOL, path, os.path.join( "/tmp/", os.path.split( path )[-1] ) )

	#-------------------------------------------------------------------------- 
	def OnCommit( self, evt ):
		""" Commit button handler.
		"""

		ctrl = XRCCTRL( self.frame, "Message" )
		self.commitMessage = ctrl.GetValue()
		# If the user doesn't supply a commit message we will just use the string
		# "Empty message" since pysvn doesn't accept an empty string see:
		#	 pysvn._pysvn_2_5.ClientError: callback_get_log_message required
		if not self.commitMessage:
			self.commitMessage = "Empty message"

		list = XRCCTRL( self.frame, "ChangedFiles" )
		self.paths = [ path for i,path in enumerate(self.paths) if list.IsChecked(i) ] 

		self.frame.Close()

	#--------------------------------------------------------------------------
	def OnPreviousMessages( self, evt ):
		dlg = self.res.LoadDialog( None, "CommitMessagesDialog" )

		list = XRCCTRL( dlg, "MessageList" )
		msg = XRCCTRL( dlg, "Message" )

		dlg.SetSize( (700,300) )
		w = list.GetSizeTuple()[0]

		list.InsertColumn(0, "Date", width=200)
		list.InsertColumn(1, "Message", width=500)
		
		plm = os.path.join( GetHomeFolder(), "previous_log_messages" )
		if not os.path.exists( plm ):
			dlg = wx.MessageDialog( self.frame, "There are no previous messages to view", "NautilusSvn", wx.OK|wx.ICON_INFORMATION )
			dlg.ShowModal()
			return

		lines = open( plm, "r" ).readlines()

		# Grab all of the entries
		cur_entry = ""
		entries = []
		date = None
		msg = ""
		for line in lines:
			m = re.compile(r"-- ([\d:]+ [\d\.]+) --").match(line)
			if m:
				cur_entry = m.groups()[0]
				if date:
					entries.append( (date, msg) )
					msg = ""
				date = cur_entry
			else:
				msg += line

		entries.reverse()

		self.previous_messages = entries

		for date,msg in entries:
			list.Append( [ date, msg ] )

		wx.EVT_LIST_ITEM_SELECTED( dlg, XRCID("MessageList"), self.OnPreviousMessageChanged )
		wx.EVT_BUTTON( dlg, XRCID("OK"), self.OnPreviousMessageDone )
		wx.EVT_WINDOW_CREATE( dlg, self.OnPreviousMessagesCreate )

		self.dlg = dlg
				
		if dlg.ShowModal() == wx.ID_OK:
			XRCCTRL( self.frame, "Message" ).SetValue( dlg.message )

	#--------------------------------------------------------------------------
	def OnPreviousMessagesCreate( self, evt ):
		""" We'll use the create handler to set the list column widths.
		"""
		list = XRCCTRL( self.dlg, "MessageList" )
		w = list.GetSizeTuple()[0]
		list.SetColumnWidth( 0, w * 0.33 )
		list.SetColumnWidth( 1, w * 0.66 )

	#--------------------------------------------------------------------------
	def OnPreviousMessageDone( self, evt ):
		XRCCTRL( self.frame, "Message" ).SetValue( XRCCTRL( self.dlg, "Message").GetValue() )
		self.dlg.Destroy()

	#--------------------------------------------------------------------------
	def OnPreviousMessageChanged( self, evt ):
		
		list = XRCCTRL( self.dlg, "MessageList" )
		msg = XRCCTRL( self.dlg, "Message" )

		msg.SetValue( self.previous_messages[ list.GetFirstSelected() ][1] )

#============================================================================== 
# First pop up the commit dialog

path = sys.argv[1]

if os.path.isdir( path ):
	basedir = path
else:
	basedir = os.path.split( path )[0]

app = MyApp( 0 )
app.MainLoop()

# Then actually commit the data if we have a commit message
# TODO: this if statement doesn't matter anymore since a commitMessage is always set
if app.commitMessage:
	msg = app.commitMessage
	paths = app.paths
	del app

	# Sort out the current time string
	t = time.strftime( "%H:%M:%S %d.%m.%Y" )

	# Store the commit message for later
	f = open( os.path.join( GetHomeFolder(), "previous_log_messages" ), "a+" )
	s = """\
-- %(t)s --
%(msg)s
"""%( locals() )

	f.write( s )
	f.close()

	app = MessageBoxApp( 0 )
	app.SetFunc( "checkin", paths, msg )
	app.MainLoop()

