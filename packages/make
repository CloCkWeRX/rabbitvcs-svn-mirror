#!/usr/bin/python

from optparse import OptionParser
import os, os.path, sys, shutil, re
import tempfile, subprocess, tarfile

import pysvn

CHANGELOG_ENTRY = "Local build via packaging script."
PACKAGE_FILES_SUBDIR = "packages"

COMMANDS = {
    "binary" : 
        {"desc" : "Build a binary package from the current state of the source tree.",
         "method" : "build_current_binary"},
    "source" :
        {"desc" : "Build a source package from the current state of the source tree.",
         "method" : "build_current_source"},
    
#    "official" :
#        {"desc" : "Build an official source and binary from a tarball and current packaging.",
#         "method" : "build_official_package"}
    }

def package_id():
    import rabbitvcs
    package_name = rabbitvcs.package_name()
    package_version = rabbitvcs.package_version()
    return (package_name, package_version)


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
    
    for cmd, info in COMMANDS.items():
        ustr += cmd + ": " + info["desc"] + "\n"
    
    return ustr

class Debian:
    """ A builder for all Debian-like distributions.
    """   
    
    # Distributions to which this class may be applied
    distros = ["debian.*", "ubuntu.*"]

    control_dir = "debian"
    
    def __init__(self, working_copy, build_area, output_dir, distro, name, version):
        self.working_copy = working_copy
        self.build_area = build_area
        self.output_dir = output_dir
        self.distro = distro


        self.name = name
        self.version = version
        self.package_dir_rel = self.name + "-" + self.version        
        self.package_dir = os.path.join(build_area, self.package_dir_rel)
        self.orig_ark = None

    def _copy_source(self):               
        try:
            svn_client = pysvn.Client()
            svn_client.export(self.working_copy, self.package_dir)
            print "Exported SVN working copy."
        except pysvn.ClientError, e:
            shutil.copytree(self.working_copy, self.package_dir)
            print "Copied file tree."
        
    def _compress_orig(self):
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
        
        self.orig_ark = ark_path
        
        print "Archive created: %s" % ark_path
    
    def _debianise(self):
        print "Debianising source... ",
        
        control_dir = os.path.join(self.package_dir,
                                   PACKAGE_FILES_SUBDIR,
                                   distro,
                                   Debian.control_dir)
                                   
        shutil.copytree(control_dir,
                        os.path.join(self.package_dir,
                                     Debian.control_dir))

    def _build_source(self):
        print "Running dpkg-source to create Debian source package..."
        
        retval = subprocess.Popen(
            ["dpkg-source", "-b", self.package_dir, self.orig_ark],
            cwd = self.build_area).wait()
    
    def _build_binary(self, sign = False):
        print "Running debuild to create an unsigned Debian binary package..."
    
        retval = subprocess.Popen(
            ["debuild", "-us", "-uc", "-b"],
            cwd = self.package_dir).wait()
    
    def _copy_results(self):
        # List all non-directory files
        files = os.walk(self.build_area).next()[2]
        [shutil.copy(
            os.path.join(self.build_area, file),
            self.output_dir)                        for file in files]
        
    def build_current_source(self):
        """ Builds a Debian (like) source package from the current state of the
        tree.
        """
        self._copy_source()
        self._compress_orig()
        self._debianise()
        self._build_source()
        self._copy_results()
        
    def build_current_binary(self):
        """ Builds a Debian (like) binary package from the current state of the
        tree.
        """
        self._copy_source()
        self._compress_orig()
        self._debianise()
        self._build_binary()
        self._copy_results()


CLASSES = [Debian]

if __name__ == "__main__":
    
    parser = OptionParser(usage = usage())
    
    parser.add_option("-o", "--output-dir", dest="output_dir",
                      help = "directory for package files")
    
    (options, args) = parser.parse_args()

    output_dir = options.output_dir

    if len(args) < 2:
        parser.error("You must specify a distro and a command!")

    distro = sys.argv[1]
    command = sys.argv[2]
    
    root_dir = os.path.split(os.path.abspath(os.path.dirname(__file__)))[0]
    
    # If no output dir is given, use ".."
    if not output_dir:
        output_dir = os.path.split(root_dir)[0]
    
    temp_dir = None
    
    try:
    
        if os.path.lexists(output_dir) and not os.path.isdir(output_dir):
            print "Output dir already exists, but is not a directory!"
            sys.exit(1)

        if not os.path.lexists(output_dir):
            os.mkdir(output_dir)
        
        print "Output dir: %s" % output_dir
        
        print "Distro: %s" % distro
        
        if distro not in get_distros():
            print "Distro not found!"
        
        print "Command: %s" % command
        
        if command not in COMMANDS.keys():
            print "Command not valid!"
            sys.exit(2)
        
        print "Original working dir: %s" % root_dir
      
        package_name, package_ver = package_id()

        temp_dir = tempfile.mkdtemp(prefix=(package_name+"-"))
        
        print "Using temp dir: %s" % temp_dir

        print "Detected package name: %s, version: %s" % (package_name, package_ver)

        bld_class = None

        for cls in CLASSES:
            for dst in cls.distros:
                regex = re.compile(dst)
                if regex.match(distro):
                    bld_class = cls
                    break
        
        if bld_class is None:
            print "Could not find a builder for that distro!"
            sys.exit(1)

        print "Using build class: %s" % bld_class

        builder = bld_class(root_dir, temp_dir, output_dir, distro, package_name, package_ver)
        
        getattr(builder, COMMANDS[command]["method"])()

        sys.exit(0)
    
    finally: 
        if temp_dir:
            shutil.rmtree(temp_dir)
