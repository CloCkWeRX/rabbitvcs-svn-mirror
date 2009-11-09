'''
Created on 31/10/2009

@author: jason
'''
import unittest
import os.path
import time
import shutil
import tempfile

import pysvn

import rabbitvcs
import rabbitvcs.services.statuscache
import rabbitvcs.util.vcs
import rabbitvcs.util.locale

rabbitvcs.util.locale.initialize_locale()

class SummarizeTest(unittest.TestCase):

    # FIXME: replace this with a suitable test repo. I recommend a local one,
    # since it will be checked out and deleted for EVERY SINGLE TEST.
    SVN_TEST_REPO = "svn+ssh://localhost/home/jason/Software/svn/svntest"     
    SVN_WC_NAME = "test_checkout"
    TIMEOUT = 0.2
    
    vcs_client = pysvn.Client()
    status_cache = rabbitvcs.services.statuscache.StatusCache()
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix=(rabbitvcs.TEMP_DIR_PREFIX))
        self.wc = os.path.join(self.temp_dir, self.SVN_WC_NAME)
        self.vcs_client.checkout(self.SVN_TEST_REPO, self.wc)

    def tearDown(self):
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)

    def get_actual_status(self):
        statuses = None
        while not statuses or statuses[self.wc]["text_status"] == "calculating":
            statuses = self.status_cache.check_status(self.wc, recurse=False)
            time.sleep(self.TIMEOUT)
        return statuses

    def change_status(self, statuses, status_type, value, idx = 0):
        # We're cheating here: instead of modifying the files in the WC, we're
        # just changing the values in the dict. It's easier, but we still need
        # the files to actually exist because the utility functions need to
        # check whether they're dirs or not.
        
        subpaths = statuses.keys()
        subpaths.remove(self.wc)
        
        self.failIf(len(subpaths) == 0, "No items in working copy!")
        
        testpath = subpaths[idx]
        statuses[testpath][status_type] = value
        return statuses

    def status_summary_change_test(self, status_type, value, result):
        orig_st = self.get_actual_status()
        statuses = self.change_status(orig_st, status_type, value)
        summary = rabbitvcs.util.vcs.summarize_status(self.wc, statuses)
        self.failUnless(summary == result)

    def status_summary_change_test_both(self, text_status, prop_status, result):
        orig_st = self.get_actual_status()
        statuses = self.change_status(orig_st, "text_status", text_status)
        statuses = self.change_status(orig_st, "prop_status", prop_status, idx=1)
        summary = rabbitvcs.util.vcs.summarize_status(self.wc, statuses)
        self.failUnless(summary == result)

    def testSummaryClean(self):
        statuses = self.get_actual_status()
        summary = rabbitvcs.util.vcs.summarize_status(self.wc, statuses)
        self.failUnless(summary == "normal")

    def testSummaryTextChangeAdded(self):
        self.status_summary_change_test("text_status", "added", "modified")      

    def testSummaryTextChangeConflicted(self):
        self.status_summary_change_test("text_status", "conflicted", "conflicted")

    def testSummaryTextChangeObstructed(self):
        self.status_summary_change_test("text_status", "obstructed", "obstructed")

    def testSummaryPropChange(self):
        self.status_summary_change_test("prop_status", "modified", "modified")
        
    def testSummaryBothChange(self):
        self.status_summary_change_test_both("modified", "modified", "modified")
    
    def testSummaryBothConflicted(self):
        self.status_summary_change_test_both("conflicted", "modified", "conflicted")

    def testSummaryBothObstructed(self):
        self.status_summary_change_test_both("obstructed", "modified", "obstructed")

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testStatusSummary']
    unittest.main()