from generic import Generic

import shutil, subprocess, os.path, sys

ERROR_USCAN = """\
Error: uscan failed to download the upstream archive.

This will cause major problems if you try to upload anything to (eg.) a PPA or
the Debian archives, since the MD5 hash will not match. Therefore, it is a fatal
error.

If you have not yet uploaded an official tarball, just do it and don't complain.
"""

class Debian(Generic):
    """ A builder for all Debian-like distributions.
    """   
        
    # Distributions to which this class may be applied
    distros = ["debian.*", "ubuntu.*"]

    control_dir = "debian"
    
    def __init__(self, *args, **kwargs):
        Generic.__init__(self, *args, **kwargs)
        
        self.pbuilder = (kwargs.has_key('use_pbuilder') and
                         kwargs['use_pbuilder'])
        
        self.ppa = (kwargs.has_key('ppa') and
                    kwargs['ppa'])
        
        self.orig_ark = None
        self.orig_ark_name = self.name + "_" + self.version + ".orig.tar.gz"
       
    def _debianise(self):
        print "Debianising source... "
       
        control_dir = os.path.join(self.package_dir,
                                   Generic.PACKAGE_FILES_SUBDIR,
                                   self.distro,
                                   Debian.control_dir)
        
        shutil.copytree(control_dir,
                        os.path.join(self.package_dir,
                                     Debian.control_dir))
    
    def _common_prebuild(self, get_archive=False):
        self._copy_source()

        if get_archive:
            print " +++ Running uscan to download upstream archive +++ "
            distro_dir = os.path.join(self.package_dir,
                                      Generic.PACKAGE_FILES_SUBDIR,
                                      self.distro)
            downloaded = subprocess.call(["uscan",
                                          "--destdir", self.build_area,
                                          "--download-current"],
                                         cwd=distro_dir,
                                         stdout=sys.stdout,
                                         stderr=sys.stderr) == 0
            if downloaded:
                self.orig_ark = os.path.join(self.build_area,
                                             self.orig_ark_name)
                assert os.path.exists(self.orig_ark)
            else:
                sys.exit(ERROR_USCAN)
            
        if not (self.orig_ark and os.path.exists(self.orig_ark)):
            self.orig_ark = self._compress(self.orig_ark_name)
        
        self._debianise()

    def _build_source(self):
        print "Running dpkg-source to create Debian source package..."
        
        retval = subprocess.call(
            ["dpkg-source", "-b", self.package_dir, self.orig_ark],
            cwd = self.build_area)
    
    def _build_binary_pdebuild(self, sign = False):
        print "Running pdebuild to create an unsigned Debian binary package..."
        
        retval = subprocess.call(
            ["pdebuild", "--buildresult", self.build_area],
            cwd = self.package_dir)
        
    
    def _build_binary_debuild(self, sign = False):
        print "Running debuild to create an unsigned Debian binary package..."
    
        retval = subprocess.call(
            ["debuild", "-us", "-uc", "-b"],
            cwd = self.package_dir)
    
    def _build_ppa_source(self):
        print "Running debuild to create a signed Debian source package..."
        
        retval = subprocess.call(
            ["debuild", "-S"],
            cwd = self.package_dir)
    
    def _build_binary(self, sign = False):
        if self.pbuilder:
            self._build_binary_pdebuild(sign)
        else:
            self._build_binary_debuild(sign)
    
    def build_official_package(self):
        self._common_prebuild(get_archive=True)
        # self._build_source()
        self._build_binary_pdebuild(sign=True)
        self._copy_results()
    
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

    def build_ppa_source(self):
        """ Builds a source package for the PPA.
        """
        self._common_prebuild(get_archive=True)
        self._build_ppa_source()
        self._copy_results()
