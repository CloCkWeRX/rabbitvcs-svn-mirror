#!/usr/bin/python

from optparse import OptionParser
import os, os.path, sys, shutil
import tempfile, subprocess, tarfile

import pysvn

CHANGELOG_ENTRY = "Local build via packaging script."
PACKAGE_FILES_SUBDIR = "packages"


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

class Debian:
    
    control_dir = "debian"
    
    def __init__(self, working_copy, build_area, distro, name, version):
        self.working_copy = working_copy
        self.build_area = build_area
        self.distro = distro

        self.name = name
        self.version = version
        self.package_dir_rel = self.name + "-" + self.version        
        self.package_dir = os.path.join(build_area, self.package_dir_rel)
                        
    def copy_source(self):               
        try:
            svn_client = pysvn.Client()
            svn_client.export(self.working_copy, self.package_dir)
            print "Exported SVN working copy."
        except pysvn.ClientError, e:
            shutil.copytree(self.working_copy, self.package_dir)
            print "Copied file tree."
        
    def prepare_orig(self):
        ark_name = self.name + "_" + self.version + ".orig.tar.gz"
        ark_path = os.path.join(self.build_area, ark_name)

        print "Creating orig archive... ",

        retval = subprocess.Popen(
                    ["tar", "-czf", ark_path, self.package_dir_rel],
                    cwd = self.build_area).wait()

        # This doesn't work: uses absolute paths unless we chdir
        # ark = tarfile.open(
        #         os.path.join(self.build_area, ark_name),
        #         mode = "w:gz")
        # ark.add(self.package_dir)
        # ark.close()

        if retval == 0:
            print "Done."
        else:
            print "Failed!"
            raise RuntimeException("Failed to create orig archive!")

        assert os.path.isfile(ark_path)
        
        print "Archive created: %s" % ark_path
    
    def debianise(self):
        print "Debianising source... ",
        
        control_dir = os.path.join(self.package_dir,
                                   PACKAGE_FILES_SUBDIR,
                                   distro,
                                   Debian.control_dir)
                                   
        shutil.copytree(control_dir,
                        os.path.join(self.package_dir,
                                     Debian.control_dir))
        

if __name__ == "__main__":
    
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

    dbuilder = Debian(root_dir, temp_dir, distro, package_name, package_ver)
    
    dbuilder.copy_source()
    dbuilder.prepare_orig()
    dbuilder.debianise()
