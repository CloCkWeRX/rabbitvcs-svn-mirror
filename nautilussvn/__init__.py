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

import gettext as _gettext
from os import environ
from locale import getdefaultlocale

version = "0.12-dev"
APP_NAME = "NautilusSvn"
LOCALE_DIR = "locale"

langs = []
language = environ.get('LANGUAGE', None)
if language:
	langs += language.split(":")
langs += [getdefaultlocale()[0]]

_gettext.bindtextdomain(APP_NAME, LOCALE_DIR)
_gettext.textdomain(APP_NAME)

gettext = _gettext.translation(APP_NAME, LOCALE_DIR, languages=langs, fallback=True)

