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

import os
import gettext as _gettext
from locale import getdefaultlocale

version = "0.12-beta1"
APP_NAME = "NautilusSvn"
TEMP_DIR_PREFIX = "nsvn-"
LOCALE_DIR = "%s/locale" % os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(LOCALE_DIR):
    LOCALE_DIR = "/usr/share/locale"

langs = []
language = os.environ.get('LANGUAGE', None)
if language:
    langs += language.split(":")
if getdefaultlocale()[0] != None: 
    langs += [getdefaultlocale()[0]]

_gettext.bindtextdomain(APP_NAME, LOCALE_DIR)
_gettext.textdomain(APP_NAME)

gettext = _gettext.translation(APP_NAME, LOCALE_DIR, languages=langs, fallback=True)


def package_name():
    """
    Report the application name in a form appropriate for building
    package files.

    """
    return APP_NAME.lower()


def package_version():
    """
    Report the version number of the application, minus any name
    extensions.

    """
    app_version = version.split('-')[0]
    # TODO: sanity-check app_version: make sure it's just digits and dots
    return app_version


def package_identifier():
    """
    Return a package identifier suitable for use in a package file.

    """
    return "%s-%s" % (package_name(), package_version())
