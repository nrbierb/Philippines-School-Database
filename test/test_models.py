#!/usr/bin/env python
#coding:utf-8
# Author:   --<>
# Purpose: 
# Created: 07/27/2009


import sys
import unittest
from datetime import date
sys.path.insert(1,'/home/master/SchoolsDatabase/ph-school-db/')
from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()
from appengine_django.models import BaseModel
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from SchoolDB.choices import *
from SchoolDB.models import *


class TestModel(db.Model):
    """
    A simple model used for testing. It has not direct use in the database
    so it may be deleted without damage to any information in the database.
    """
    name = db.StringProperty(required=True)
    history1 = db.ReferenceProperty(History,
                                    collection_name="history1")
    history2 = db.ReferenceProperty(History,
                                    collection_name="history2")
    
    @staticmethod
    def new_testmodel(instance_name):
        instance = TestModel(name = instance_name)
        instance.put()
        instance.post_creation()
        return instance
    
    def post_creation(self):
        self.history1 = History.new_history(self,"H1")
        self.history2 = History.new_history(self,"H2", True)
        self.put()
        
    def delete(self):
        self.history1.delete()
        self.history2.delete()
        db.delete(self)
 
def generate_test_model_names(base_name, count):
    names = []
    for i in xrange(1,(count+1)):
        name = "%sTM_%3d" %(base_name, i)
        names.append(name)
    return names

def create_named_test_models(base_name, count):
    names = generate_test_model_names(base_name, count)
    models = []
    for name in names:
        models.append(TestModel.new_testmodel(name))
    return models
            
def delete_named_test_models(base_name, count):
    test_model_name_start = base_name + "TM_0"
    test_model_name_end = base_name + "TM_999"
    test_model_query = TestModel.all()
    test_model_query.filter("name > ", test_model_name_start)
    test_model_query.filter("name < ", test_model_name_end)
    for test_model in test_model_query:
        test_model.delete()

class testSchoolDbModels(unittest.TestCase):
    def setUp(self):
        """
        Log into database. 
        Then create 10 instances of TestModel in the database
        with the names modelTM_001 ...
        """
        # For now, do nothing
        create_named_test_models("model",1)
        
    def tearDown(self):
        q = db.Query(TestModel)
        count = q.count()
        #for instance in q.fetch(100):
            #try:
                #instance.delete()
            #except :
                #x = None
        
    def testCreateModels(self):
        """
        Create 10 instances of TestModel in the database
        with the names modelTM_001 ...
        """
        "test model creation"
        #q = db.GqlQuery("SELECT * FROM History")
        #count = q.count()
        #for instance in q:
            #instance.delete()
        #q = db.GqlQuery("SELECT * FROM History WHERE attribute_name = 'H2'")
        #count = q.count()
        #for instance in q.fetch(500):
            #instance.delete()       
        q = db.Query(TestModel)
        count = q.count()
        self.assertEqual(count, 1)
        
    #def testHistoryCounts(self):
        #"test history counts"
        #q = db.GqlQuery("SELECT * FROM History WHERE attribute_name = 'H1'")
        #count = q.count()        
        #self.assertEqual(count, 1) 
        
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(testSchoolDbModels))
    return suite

if __name__ == '__main__':
    #unittest.main()
    print sys.path
    unittest.TextTestRunner(verbosity=2).run(suite())

