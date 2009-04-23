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

"""
Unit tests for the top-level nautilussvn package.

"""

# make sure the current working copy is in sys.path before anything else
from os.path import abspath, dirname, join, normpath
import sys
toplevel = normpath(join(dirname(abspath(__file__)), '..', '..'))
sys.path.insert(0, toplevel)

from unittest import TestCase, main
import nautilussvn


class NautilusSvnTest(TestCase):
    """
    Main NautilusSvn tests.

    """
    def test_package_name(self):
        """Make sure the package name is reported properly."""
        result = nautilussvn.package_name()
        self.assertEqual(result, "nautilussvn")

    def test_package_version(self):
        """Make sure the package version is reported properly."""
        result = nautilussvn.package_version()
        for character in result:
            if not (character.isdigit() or character == '.'):
                self.fail("Not all characters in package version "
                          "'%s' were digits or dots." % result)

    def test_package_identifier(self):
        """Make sure the package identifier is reported properly."""
        result = nautilussvn.package_identifier()
        version = nautilussvn.package_version()
        self.assertEqual(result, "nautilussvn-%s" % version)


if __name__ == "__main__":
    main()
