#
# test/stage.py
#

import os
from shutil import rmtree
from sys import argv
from optparse import OptionParser

from gittyup.client import GittyupClient
from gittyup.objects import *
from util import touch, change
from gittyup.config import GittyupLocalFallbackConfig, GittyupConfig, GittyupSystemConfig

parser = OptionParser()
parser.add_option("-c", "--cleanup", action="store_true", default=False)
(options, args) = parser.parse_args(argv)

DIR = "config"

if options.cleanup:
    rmtree(DIR, ignore_errors=True)

    print "config.py clean"
else:
    if os.path.isdir(DIR):
        raise SystemExit("This test script has already been run.  Please call this script with --cleanup to start again")

    g = GittyupClient(DIR, create=True)
    c = GittyupLocalFallbackConfig(DIR)
    
    # Create config items
    c.set("core", "filemode", True)
    c.set("core", "repositoryformatversion", 0)

    # Add comments
    c.set_comment("core", "filemode", ["Regular comment"])
    c.set_inline_comment("core", "repositoryformatversion", "inline repo format comment")

    # Create new section/items and then rename them
    c.set("newsection", "newitem", "Val A")
    c.rename_section("newsection", "newsection_RE")    
    c.rename("newsection_RE", "newitem", "newitem_RE")
    c.write()

    del c
    
    c = GittyupLocalFallbackConfig(DIR)

    assert (c.has("newsection_RE", "newitem_RE"))
    assert (c.get_comment("core", "filemode")[0].find("Regular comment") != -1)
    assert (c.get_inline_comment("core", "repositoryformatversion").find("inline repo format comment") != -1)
    
    del c

    c = GittyupConfig("./data/config/config.example")
    
    assert (c.has("diff", "renames"))
    
    del c
    
    c = GittyupSystemConfig()
    c.set("section", "key", "value")
    c.write()

    print "config.py pass"
