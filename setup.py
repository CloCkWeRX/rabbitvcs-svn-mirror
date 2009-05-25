#!/usr/bin/env python

# If you didn't know already, this is a Python distutils setup script. It borrows
# heavily from Phatch's (see: http://photobatch.stani.be/).
#
# There's a lot of comments here (on purpose) so people can actually learn from
# this and don't have to figure out everything on their own.
#
# This setup script is used to build distribution specific packages.
#
# For more information see: http://docs.python.org/dist/dist.html
#

# TODO: this all feels just a little too shell scripty, refactoring it later 
# might be a good idea.

# NOTES:
# System-wide directories:
# NautilusSvn goes in: /usr/lib/nautilus/extensions-<version>/python/
# Scalable emblems go in: /usr/share/icons/hicolor/scalable/emblems
#
# User-specific directories:
# NautilusSvn goes in: ~/.nautilus/python-extensions/
# Scalable emblems go in: ~/.icons/hicolor/scalable
#
# Common directories
# See: http://standards.freedesktop.org/basedir-spec/basedir-spec-0.6.html
# Configuration information goes in: ~/.config/nautilussvn/
# Data goes in: ~/.local/share/nautilussvn

import sys
import os
import os.path
import subprocess
from distutils.core import setup

#==============================================================================
# Variables
#==============================================================================

# Some descriptive variables
# This will eventually be passed to the setup function, but we already need them
# for doing some other stuff so we have to declare them here.
name                = "nautilussvn"
version             = "0.12"
description         = "Integrated Subversion support for Nautilus"
long_description    = """An extension to Nautilus to allow better integration with the Subversion source control system. Similar to the TortoiseSVN project on Windows."""
author              = "Bruce van der Kooij"
author_email        = "brucevdkooij@gmail.com"
url                 = "http://code.google.com/p/nautilussvn"
license             = "GNU General Public License version 2 or later"

#==============================================================================
# Paths
#==============================================================================

# NautilusSvn goes in: /usr/lib/nautilus/extensions-<version>/python/
# We'll use `pkg-config` to find out the extension directory instead of hard-coding it.
# However, this won't guarantee NautilusSvn will actually work (e.g. in the case of 
# API/ABI changes it might not). The variable is read by `pkg-config` from: 
# - /usr/lib/pkgconfig/nautilus-python.pc
python_nautilus_extensions_path = subprocess.Popen(
    ["pkg-config", "--variable=pythondir","nautilus-python"],
    stdout=subprocess.PIPE
).stdout.read().strip()

# Some distros don't actually return anything useful from the command
# above (pkg-config), so let's make sure we have something.
# TODO: maybe Fedora's package is called python-nautilus?
if python_nautilus_extensions_path == "":
    python_nautilus_extensions_path = "/usr/lib/nautilus/extensions-2.0/python"

icon_theme_directory = "/usr/share/icons/hicolor" # TODO: does this really need to be hardcoded?
locale_directory = "/usr/share/locale"

#==============================================================================
# Helper functions
#==============================================================================

def include_by_pattern(directory, directory_to_install, pattern):
    files_to_include = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(pattern):
                files_to_include.append((
                    root.replace(directory, directory_to_install),
                    [os.path.join(root, file)]
                ))
    return files_to_include

#==============================================================================
# Gather all the files that need to be included
#==============================================================================

# Packages
packages = []
for root, dirs, files in os.walk("nautilussvn"):
    if "__init__.py" in files:
        packages.append(root.replace(os.path.sep, "."))
        
# Nautilus extension
nautilus_extension = [(
    python_nautilus_extensions_path, 
    ["nautilussvn/lib/extensions/nautilus/NautilusSvn.py"]
)]

# Command-line tool
command_line_tool = [(
    "/usr/bin",
    ["bin/nautilussvn"]
)]

# Translation
translations = include_by_pattern("nautilussvn/locale", locale_directory, ".mo")

# Icons
icons = include_by_pattern("nautilussvn/data/icons/hicolor", icon_theme_directory, ".svg")

# Update notifier
update_notifier = [("/usr/share/nautilussvn", [
    "packages/ubuntu/debian/nautilussvn-restart-required.update-notifier",
    "packages/ubuntu/debian/do-nautilussvn-restart-nautilus"
])]

# Documentation
documentation = [("/usr/share/doc/nautilussvn", [
# The README file is empty, and causes lintian errors if left in.
#    "README",
    "AUTHORS",
    "MAINTAINERS",
    "CREDITS",
    "THANKS"
])]

#==============================================================================
# Ready to install
#==============================================================================

# Calling the setup function will actually install NautilusSvn and also creates 
# an .egg-info file in /usr/lib/python<version>/site-packages/ or 
# /usr/share/python-support/nautilussvn when generating a Debian package.
dist = setup(
    # The following arguments will be included in the .egg.info file,
    # for a list of available arguments and their descriptions see:
    # - http://docs.python.org/dist/module-distutils.core.html
    name=name,
    version=version,
    description=description,
    long_description=long_description,
    author=author,
    author_email=author_email,
    url=url,
    license=license,

    # There are actually several arguments that are used to install files:
    # - py_modules: installs specific modules to site-packages
    # - packages: install complete packages (directories with an __init__.py
    #   file) into site-packages
    # - data_files: any file you want, anywhere you want it
    packages=packages,
    include_package_data=True,
    package_data={
        "nautilussvn": [
            # Include our Glade UI files right into the package
            "ui/glade/*.glade"
        ]
    },
    data_files=nautilus_extension + command_line_tool + translations + icons + documentation + update_notifier
)

#
# Post installation
#

# Make sure the icon cache is deleted and recreated
if sys.argv[1] == "install":
    print "Running gtk-update-icon-cache"
    
    subprocess.Popen(
        ["gtk-update-icon-cache", icon_theme_directory], 
        stdout=subprocess.PIPE
    ).communicate()[0]
