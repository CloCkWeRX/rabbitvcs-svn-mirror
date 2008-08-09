#!/usr/bin/env python

# If you didn't know already, this is a Python distutils setup script. It borrows
# heavily from Phatch's (see: http://photobatch.stani.be/).
#
# There's a lot of comments here (on purpose) so people can actually learn from
# this and don't have to figure out everything on their own.
#
# This setup script is used to build distribution specific packages. but if you 
# want to install NautiluSvn directly from this script you do that using:
# - python setup.py install
#
# If before installing you want to see what will be installed you can do that too:
# - python setup.py install --root=testing
#
# This will install everything into ./testing
#
# For more information see: http://docs.python.org/dist/dist.html
#

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

import os
import glob
import subprocess
import re
from distutils.core import setup

#==============================================================================
# Variables
#==============================================================================

# Some descriptive variables
# This will eventually be passed to the setup function, but we already need them
# for doing some other stuff so we have to declare them here.
name='nautilussvn'
version='0.12'
description='Integrated Subversion support for Nautilus'
long_description="""An extension to Nautilus to allow better integration with the Subversion source control system. Similar to the TortoiseSVN project on Windows."""
author='Jason Field'
author_email='jason@jasonfield.com'
url='http://code.google.com/p/nautilussvn'
license='GNU General Public License version 2 or later'

# Variables pointing to directories
icon_theme_directory = '/usr/share/icons/hicolor/' # TODO: does this really need to be hardcoded?
emblems_directory = '%s/scalable/emblems/' % icon_theme_directory 
nautilussvn_directory_name = '%(name)s_%(version)s' % { 'name': name, 'version': version }

# NautilusSvn goes in: /usr/lib/nautilus/extensions-<version>/python/
# We'll use `pkg-config` to find out the extension directory instead of hard-coding it.
# However, this won't guarantee NautilusSvn will actually work (e.g. in the case of 
# API/ABI changes it might not). The variable is read by `pkg-config` from: 
# - /usr/lib/pkgconfig/nautilus-python.pc
python_nautilus_extensions_path = subprocess.Popen(
    ['pkg-config', '--variable=pythondir','nautilus-python'],
    stdout=subprocess.PIPE
).stdout.read().strip()

# The full path to the directory we want to install
nautilussvn_directory = os.path.join(python_nautilus_extensions_path, nautilussvn_directory_name)

#==============================================================================
# Gather all the files that need to be included
#==============================================================================

#-------------------------------------------------------------------------------
# Documentation
#-------------------------------------------------------------------------------
doc_files = [
    ('share/doc/%s' % name, ['README'])
]


#-------------------------------------------------------------------------------
# Source
#-------------------------------------------------------------------------------

# The following dictionary of regular expressions defines what files will be 
# included and which will not.
patterns = {
    'include': [
        '.*py$',
        '.*xrc$',
        'svn.ico'
    ],
    'exclude': [
        'setup.py'
    ]
}

os_files = []

# FIXME: currently we're not using subdirectories (e.g. packages) but in the future
# we probably will. The following statements will need to be rewritten to support this.
files = os.listdir('.')
for file in files:
    include = False
    for pattern in patterns['include']:
        if re.match(pattern, file):
            include = True;
            break;
    
    for pattern in patterns['exclude']:
        if re.match(pattern, file): 
            include = False
            break;
    
    if include == True: os_files.append(file)

# Add the directory
os_files = [(nautilussvn_directory, os_files)]


#-------------------------------------------------------------------------------
# Emblems
#-------------------------------------------------------------------------------
# NOTE: it seems the distutils setup function will eventually just grab the 
# basename, so even though glob returns strings as: './icons/emblem-svnmodified.svg'
# only 'emblem-svnmodified.svg' is eventually installed.
emblem_files = glob.glob('./icons/*.svg')
emblem_files = [(emblems_directory, emblem_files)]


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
    data_files=doc_files + os_files + emblem_files
)

#==============================================================================
# Some post-install stuff
# TODO: this only needs to be done when setup.py is called directly (for example
# debian packages include postinst and prerm files in which this should be done).
#==============================================================================

# We have to call `gtk-update-icon-cache` or else the emblems won't appear.
#~ subprocess.call(['gtk-update-icon-cache', icon_theme_directory])

# Nautilus Python extensions actually need to be in the root of the extensions
# directory so we'll just create a symlink (this actually needs to be a symlink
# because there's path magic in NautilusSvn.py to include other modules).
#~ os.symlink(
    #~ os.path.join(nautilussvn_directory, 'NautilusSvn.py'),
    #~ os.path.join(python_nautilus_extensions_path, 'NautilusSvn.py')
#~ )
