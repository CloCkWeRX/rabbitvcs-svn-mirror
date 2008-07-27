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

import os

# Set to True to add emblems to version controlled files showing their status
ENABLE_EMBLEMS = True

# Set to True to add author and revision attributes to files, which are then
# visible via columns in Nautilus
ENABLE_ATTRIBUTES = True

# Tool that should be used for diffs
DIFF_TOOL = "meld"

# The path to the folder containing all of our source files.
SOURCE_PATH = os.path.dirname(os.path.realpath(__file__))

# Set to True to enable recursive status checks. This might be slow when using
# a remote repository over a slow connection.
RECURSIVE_STATUS = True

# Set to True to swap the order of old and new versions of files in diff tool
# Default is False, new version at left and old one at right
SWAP = False

#==============================================================================

# A useful macro that's used all over the shop.
def GetPath(path):
	""" This function is a helper for the other files so that they can find the
		resource files etc. that they require.
	"""
	return os.path.join(SOURCE_PATH, path)

def GetHomeFolder():
	""" Returns the location of the hidden folder we use in the home dir.
		This is used for storing things like previous commit messages and
		previously used repositories.
	"""
	fldr = os.path.abspath( os.path.expanduser("~/.nautilussvn") )
	if not os.path.exists( fldr ):
		os.mkdir( fldr )
	return fldr

# Checks that the defined diff tool exists. If not, let the user know.
def CheckDiffTool():
	if not os.path.exists(os.path.join("/usr/bin", DIFF_TOOL)):
		
		import gtk
		dlg = gtk.MessageDialog(buttons=gtk.BUTTONS_OK)

		msg = "The diff tool set in %s does not exist.\n\nEither install %s, or update helper.py to point to the correct tool you'd like to use.."%(GetPath("helper.py"),DIFF_TOOL)
		dlg.set_markup(msg)
		def OnResponse(widget, event):
			dlg.destroy()
		dlg.connect("response", OnResponse)
		dlg.set_property("title", "NautilusSvn")
		dlg.run()
		return False
	else:
		return True

def CallDiffTool(lhs, rhs, rev=-1):
	if SWAP:   (lhs, rhs) = (rhs, lhs)
	if rev == -1:
		os.spawnl(os.P_NOWAIT, os.path.join("/usr/bin/", DIFF_TOOL), DIFF_TOOL, lhs, rhs)
	else:
		os.spawnl(os.P_NOWAIT, os.path.join("/usr/bin/", DIFF_TOOL), DIFF_TOOL, lhs, rhs, rev)

