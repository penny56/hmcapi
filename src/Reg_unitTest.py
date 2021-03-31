'''
Created on Oct 11, 2018

@author: mayijie
'''

import unittest
from Reg_unitTestCases import *

CONFIG_FILE = 'Reg_config.cfg'

class DPMRegression(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        reg_parseArgs()
        reg_loadConfig()
        constructHMCConnection()


    @classmethod
    def tearDownClass(cls):
        destructHMCConnection()

    # No.1 create partition in Advanced mode
    def test_case_CreatePartition(self):
        print "Start test case: create partition ..."
        self.assertEqual(1, tc_createPartition())

    
    #
    def test_case_AddVNic(self):
        print "Start test case: add vNic ..."
        self.assertEqual(1, tc_addVnic())
        
        
    # No.2 Dynamic changes of partition resource and general settings
    def test_case_DynamicChangePartitionResource(self):
        print "Start test case: dynamic change partition resource ..."
        self.assertEqual(1, tc_DynamicChangePartitionResource())
    
    
    # No.3 Add FCP storage group to a newly created partition
    def test_case_AttachFCPStorageGroup(self):
        print "Start test case: attach FCP storage group ..."
        self.assertEqual(1, tc_AttachFCPStorageGroup())


    # No.4 Modify FCP storage group
    def test_case_ModifyFCPStorageGroup(self):
        print "Start test case: modify FCP storage group ..."
        self.assertEqual(1, tc_ModifyFCPStorageGroup())
        
    
    # No. 5 Detach FCP storage group
    def test_case_DetachFCPStorageGroup(self):
        print "Start test case: detach FCP storage group ..."
        self.assertEqual(1, tc_DetachFCPStorageGroup())
        

    # No.6 Attach FICON 
    def test_case_AttachFICONStorageGroup(self):
        print "Start test case: attach FICON storage group ..."
        self.assertEqual(1, tc_AttachFICONStorageGroup())
        
        
    # No.7 Detach FICON storage group
    def test_case_DetachFICONStorageGroup(self):
        print "Start test case: detach FICON storage group ..."
        self.assertEqual(1, tc_DetachFICONStorageGroup())