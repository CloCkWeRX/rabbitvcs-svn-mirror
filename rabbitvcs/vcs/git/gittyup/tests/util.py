#
# util.py
#

import os

def touch(fname, times = None):
    with file(fname, 'a'):
        os.utime(fname, times)

def change(path):
    f = open(path, "a")
    f.write("1")
    f.close()
