import os, os.path, shutil, subprocess
import pysvn

PACKAGE_FILES_SUBDIR = "packages"

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
                                   self.distro,
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
