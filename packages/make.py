#!/usr/bin/python

from optparse import OptionParser
import os, os.path, sys, shutil
import tempfile


commands = {
    "binary" : "Build a binary package from the current state of the source tree.",
    "source" : "Build a source package from the current state of the source tree.",
    "official" : "Build an official source and binary from a tarball and current packaging.",
}

def get_distros(basepath = None):
    if not basepath:
        basepath = os.path.dirname(__file__)
    
    dirs = os.walk(basepath).next()[1]
    
    # Remove hidden dirs
    dirs = [dir for dir in dirs if not dir.startswith(".")]
    
    return dirs

def usage():
    ustr = "usage: %prog distro command [options]\n\n"
    
    ustr += "Detected distros are: " + ", ".join(get_distros())
    
    ustr += "\n\n"
    
    ustr += "Available commands are:\n"
    
    for cmd, desc in commands.items():
        ustr += cmd + ": " + desc + "\n"
    
    return ustr

class DebianLike:
    
    def __init__(self, packagedir, workarea, name, version):
        self.packagedir = packagedir
        self.workarea = workarea
        self.name = name
        self.version = version
        
    def build_quick(self):
        print "Copying source tree..."
        dirname = self.name + "-" + self.version
        shutil.copytree(self.packagedir, os.path.join(
                                            self.workarea,
                                            dirname))        

if __name__ == "__main__":
    
    print "WARNING! This script is unfinished! Do not use!"
    sys.exit(1)
    
    parser = OptionParser(usage = usage())
    
    (options, args) = parser.parse_args()

    if len(args) < 2:
        parser.error("You must specify a distro and a command!")

    distro = sys.argv[1]
    command = sys.argv[2]
    
    root_dir = os.path.split(os.path.abspath(os.path.dirname(__file__)))[0]
    
    print "Distro: %s" % distro
    
    if distro not in get_distros():
        print "Distro not found!"
    
    print "Command: %s" % command
    
    if command not in commands.keys():
        print "Command not valid!"

    print "Using root dir: %s" % root_dir

    temp_dir = tempfile.mkdtemp(prefix="nsvn-")
    
    print "Using temp dir: %s" % temp_dir

    import nautilussvn
    packageid = nautilussvn.package_identifier()
    
    package_name, package_ver = packageid.split("-", 1)

    print "Detected package name: %s, version: %s" % (package_name, package_ver)

    dbuilder = DebianLike(root_dir, temp_dir, package_name, package_ver)
    dbuilder.build_quick()
