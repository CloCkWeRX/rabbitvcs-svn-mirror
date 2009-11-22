import os, os.path, shutil, subprocess, fnmatch
import pysvn

class Generic(object):

    PACKAGE_FILES_SUBDIR = "packages"

    distros = ["generic"]
    
    def __init__(self, working_copy, build_area, output_dir, distro, name, version, **kawrgs):
        self.working_copy = working_copy
        self.build_area = build_area
        self.output_dir = output_dir
        self.distro = distro
        self.name = name
        self.version = version
        self.package_dir_rel = self.name + "-" + self.version        
        self.package_dir = os.path.join(build_area, self.package_dir_rel)

    def _copy_source(self):               
        try:
            svn_client = pysvn.Client()
            svn_client.export(self.working_copy, self.package_dir)
            print "Exported SVN working copy."
        except pysvn.ClientError:
            shutil.copytree(self.working_copy, self.package_dir)
            print "Copied file tree."

    def _compress(self, ark_name = None):
        if not ark_name:
            ark_name = self.name + "-" + self.version + ".tar.gz"
        
        ark_path = os.path.join(self.build_area, ark_name)

        print "Creating orig archive... ",

        retval = subprocess.call(
                    ["tar", "-czf", ark_path, self.package_dir_rel],
                    cwd = self.build_area)

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
            raise RuntimeError("Failed to create orig archive!")

        assert os.path.isfile(ark_path)
        
        print "Archive created: %s" % ark_path
        
        return ark_path

    def _copy_results(self, match = "*"):
        # List all non-directory files
        files = fnmatch.filter(os.walk(self.build_area).next()[2], match)
        
        [shutil.copy(
            os.path.join(self.build_area, fl),
            # fl,
            self.output_dir) \
                for fl in files]

    def build_current_source(self):
        self._copy_source()
        self._compress()
        self._copy_results("*.tar.gz")
