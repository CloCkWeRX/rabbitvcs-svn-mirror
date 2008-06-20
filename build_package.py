#!/usr/bin/python

import os
import getpass
import sys
import shutil
import glob

VERSION="nautilussvn_0.11-1"
Run = os.system
home = os.path.expanduser("~")

def ReplaceLineInFile(filename, target, subst):
	""" Replaces lines in *filename* containing *target* with *subst*
	"""
	st = open(filename, "r").readlines()
	out = []
	for line in st:
		if target in line:
			line = subst
		out.append(line)
	
	f = open(filename, "w")
	for s in out:
		f.write(s)

if getpass.getuser() != "root":
	print "You need to be root to run this script!"
else:

	path = "%s/nautilussvn_build"%home
	if os.path.exists(path):
		shutil.rmtree(path)
	os.mkdir(path)
	os.chdir(path)

	print "Setting up the output folders..."
	os.makedirs("./nautilussvn/usr/share/doc/nautilussvn")
	os.makedirs("./nautilussvn/DEBIAN")
	os.makedirs("./nautilussvn/usr/lib/nautilus/extensions-1.0/python")

	print "Exporting development data"
	Run("svn export %s/.nautilus/python-extensions/NautilusSvn ./nautilussvn/usr/lib/nautilus/extensions-1.0/python/%s"%(home, VERSION))
	shutil.move("./nautilussvn/usr/lib/nautilus/extensions-1.0/python/%s/README"%VERSION, "./nautilussvn/usr/share/doc/nautilussvn/")
	shutil.move("./nautilussvn/usr/lib/nautilus/extensions-1.0/python/%s/changelog.Debian"%VERSION, "./nautilussvn/usr/share/doc/nautilussvn/")
	shutil.move("./nautilussvn/usr/lib/nautilus/extensions-1.0/python/%s/control"%VERSION, "./nautilussvn/DEBIAN/")
	shutil.move("./nautilussvn/usr/lib/nautilus/extensions-1.0/python/%s/postinst"%VERSION, "./nautilussvn/DEBIAN/")
	shutil.move("./nautilussvn/usr/lib/nautilus/extensions-1.0/python/%s/prerm"%VERSION, "./nautilussvn/DEBIAN/")
	shutil.move("./nautilussvn/usr/lib/nautilus/extensions-1.0/python/%s/copyright"%VERSION, "./nautilussvn/usr/share/doc/nautilussvn/")
	os.remove("./nautilussvn/usr/lib/nautilus/extensions-1.0/python/%s/build_package.py"%VERSION)

	print "Setting up icons"
	os.makedirs( './nautilussvn/usr/share/icons/hicolor/scalable/emblems' )
	files = glob.glob( "./nautilussvn/usr/lib/nautilus/extensions-1.0/python/%s/icons/*"%VERSION )
	for f in files:
		shutil.move(f, "./nautilussvn/usr/share/icons/hicolor/scalable/emblems/%s"%os.path.split(f)[-1])
	shutil.rmtree( "./nautilussvn/usr/lib/nautilus/extensions-1.0/python/%s/icons"%VERSION )

	print "Setting the version in files to", VERSION
	ReplaceLineInFile(	"./nautilussvn/usr/lib/nautilus/extensions-1.0/python/%s/NautilusSvn.py"%VERSION,
						"__version__ = ",
						'__version__ = "%s"\n'%(VERSION.split("_")[-1])
					)

	ReplaceLineInFile(	"./nautilussvn/usr/lib/nautilus/extensions-1.0/python/%s/helper.py"%VERSION,
						'SOURCE_PATH = "/usr/lib/nautilus/extensions-1.0/python',
						'\tSOURCE_PATH = "/usr/lib/nautilus/extensions-1.0/python/%s/"\n'%VERSION
					)

	ReplaceLineInFile(	"./nautilussvn/DEBIAN/postinst",
						'ln -s /usr/lib/nautilus',
						'ln -s /usr/lib/nautilus/extensions-1.0/python/%s/NautilusSvn.py /usr/lib/nautilus/extensions-1.0/python/NautilusSvn.py\n'%VERSION
					)
						

	ReplaceLineInFile(	"./nautilussvn/DEBIAN/control",
						'Version:',
						'Version: %s\n'%(VERSION.split("_")[-1])
					)

	print "Compressing change log"
	Run("gzip -f --best ./nautilussvn/usr/share/doc/nautilussvn/changelog.Debian")

	print "Making .deb"
	Run("chown root:root -R ./nautilussvn")
	Run("chmod 0755 ./nautilussvn/DEBIAN/prerm")
	Run("dpkg-deb --build ./nautilussvn")
	shutil.move("nautilussvn.deb", "%s.deb"%VERSION)

	print "Testing deb"
	Run("lintian %s.deb"%VERSION)
