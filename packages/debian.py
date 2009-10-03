from generic import Generic

import shutil, subprocess, os.path

class Debian(Generic):
    """ A builder for all Debian-like distributions.
    """   
    
    # Distributions to which this class may be applied
    distros = ["debian.*", "ubuntu.*"]

    control_dir = "debian"
    
    def __init__(self, *args, **kwargs):
        Generic.__init__(self, *args, **kwargs)
        self.orig_ark = None
        self.orig_ark_name = self.name + "_" + self.version + ".orig.tar.gz"
       
    def _debianise(self):
        print "Debianising source... ",
        
        control_dir = os.path.join(self.package_dir,
                                   Generic.PACKAGE_FILES_SUBDIR,
                                   self.distro,
                                   Debian.control_dir)
                                   
        shutil.copytree(control_dir,
                        os.path.join(self.package_dir,
                                     Debian.control_dir))
    
    def _common_prebuild(self):
        self._copy_source()
        self.orig_ark = self._compress(self.orig_ark_name)
        self._debianise()

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
        
    def build_current_source(self):
        """ Builds a Debian (like) source package from the current state of the
        tree.
        """
        self._common_prebuild()
        self._build_source()
        self._copy_results()
        
    def build_current_binary(self):
        """ Builds a Debian (like) binary package from the current state of the
        tree.
        """
        self._common_prebuild()
        self._build_binary()
        self._copy_results("*.deb")
