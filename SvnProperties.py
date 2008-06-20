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

from helper import *

#============================================================================== 
class MyApp(wx.App):

	#-------------------------------------------------------------------------- 
	def OnInit(self):
		res = wx.xrc.EmptyXmlResource()
		xrcpath = GetPath("NautilusSvn.xrc")
		res.Load(xrcpath)
		self.frame = res.LoadFrame(None, "Properties")
		self.frame.SetTitle("Properties for %s"%(os.path.split(path)[-1]))
		self.frame.SetIcon(wx.Icon(GetPath("svn.ico"), wx.BITMAP_TYPE_ICO))
		self.frame.Centre()

		self.prop_edit = res.LoadDialog( self.frame, "PropertyEditor" )
		self.prop_edit.SetIcon(wx.Icon(GetPath("svn.ico"), wx.BITMAP_TYPE_ICO))
		self.prop_edit.Centre()

		self.SetTopWindow(self.frame)
		self.frame.Show()

		c = pysvn.Client()
		XRCCTRL( self.frame, "Path" ).SetValue( c.info( path ).url )

		wx.EVT_BUTTON( self.frame, XRCID("Add"), self.OnAdd )
		wx.EVT_BUTTON( self.frame, XRCID("Delete"), self.OnDelete )
		wx.EVT_BUTTON( self.frame, XRCID("Edit"), self.OnEdit )
		wx.EVT_BUTTON( self.prop_edit, XRCID("OK"), self.OnOK )
		wx.EVT_BUTTON( self.prop_edit, XRCID("Cancel"), self.OnCancel )

		self.UpdatePropList()

		return True
	
	#--------------------------------------------------------------------------
	def OnAdd( self, evt ):
		self.prop_edit.SetTitle( "Adding new property to %s"%path)

		XRCCTRL( self.prop_edit, "Property" ).Enable()
		XRCCTRL( self.prop_edit, "Property" ).SetValue( "" )
		XRCCTRL( self.prop_edit, "Value" ).SetValue( "" )

		self.prop_edit.Fit()

		self.prop_edit.ShowModal()

	#--------------------------------------------------------------------------
	def OnDelete( self, evt ):
		list = XRCCTRL( self.frame, "PropList" )
		item = list.GetItem( list.GetFirstSelected(), 0 )
		prop = item.GetText()

		c = pysvn.Client()
		c.propdel( prop, path )

		self.UpdatePropList()

	#--------------------------------------------------------------------------
	def OnEdit( self, evt ):
		list = XRCCTRL( self.frame, "PropList" )
		prop = list.GetItem( list.GetFirstSelected(), 0 ).GetText()
		value = list.GetItem( list.GetFirstSelected(), 1 ).GetText()
		self.prop_edit.SetTitle( "Editing %s"%prop)

		XRCCTRL( self.prop_edit, "Property" ).Disable()
		XRCCTRL( self.prop_edit, "Property" ).SetValue( prop )
		XRCCTRL( self.prop_edit, "Value" ).SetValue( value )

		self.prop_edit.ShowModal()

	#--------------------------------------------------------------------------
	def UpdatePropList( self ):
		list = XRCCTRL( self.frame, "PropList" )
		list.ClearAll()
		list.InsertColumn( 0, "Property", width=150 )
		list.InsertColumn( 1, "Value", width=500 )

		c = pysvn.Client()
		for url, prop in c.proplist( path ):
			for k in prop.keys():
				list.Append( (k, prop[k]) )

	#--------------------------------------------------------------------------
	def OnOK( self, evt ):
		prop = XRCCTRL( self.prop_edit, "Property" ).GetValue()
		value = XRCCTRL( self.prop_edit, "Value" ).GetValue()
		c = pysvn.Client()
		try:
			c.propset( prop, value, path )
		except pysvn.ClientError, e:
			dlg = wx.MessageDialog( self.prop_edit, str(e), "NautilusSvn", wx.OK|wx.ICON_ERROR )
			dlg.ShowModal()
		self.UpdatePropList()
		self.prop_edit.Close()
	
	#--------------------------------------------------------------------------
	def OnCancel( self, evt ):
		self.prop_edit.Close()

#============================================================================== 

path = sys.argv[1]
path = path.replace( '"', '' )

if os.path.isdir(path):
	basedir = path
else:
	basedir = os.path.split(path)[0]

app = MyApp(0)
app.MainLoop()
