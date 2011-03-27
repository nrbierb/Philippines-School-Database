import sys
import unittest
import itertools
from datetime import date, timedelta
sys.path.insert(1,'/home/master/SchoolsDatabase/mysite/')
from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()
from appengine_django.models import BaseModel
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from SchoolDB import choices, models, student_attendance
from xml.dom import minidom


#class TestModel(db.Model):
    #"""
    #A simple model used for testing. It has not direct use in the database
    #so it may be deleted without damage to any information in the database.
    #"""
    #name = db.StringProperty(required=True)
    #history1 = db.ReferenceProperty(History,
                                    #collection_name="history1")
    #history2 = db.ReferenceProperty(History,
                                    #collection_name="history2")
    #history3 = db.ReferenceProperty(History,
                                    #collection_name="history3")
   
    #@staticmethod
    #def create(instance_name):
        #instance = TestModel(name = instance_name)
        #instance.put()
        #instance.post_creation()
        #return instance
    
    #def post_creation(self):
        #self.history1 = History.create(self,"H1")
        #self.history2 = History.create(self,"H2", True)
        #self.history3 = History.create(self,"H3", False, True)
        #self.put()
        
    #def remove(self):
        #print "++++++++++++++"
        #try:
            #h = self.history1
            #print ">> %s deleting %s [%s]" %(self.name,  
                            #h.attribute_name, unicode(h))
            #h.remove()
        #except Exception, e:
            #print e
        #try:
            #h = self.history2
            #print ">> %s deleting %s [%s]" %(self.name,  
                            #h.attribute_name, unicode(h))
            #h.remove()
        #except Exception, e:
            #print e
        #try:
            #h = self.history3
            #print ">> %s deleting %s [%s]" %(self.name,  
                            #h.attribute_name, unicode(h))
            #h.remove()
        #except Exception, e:
            #print e
        #self.delete()
        
    #def __unicode__(self):
        #return self.name
    

#class NumberedText():
    #def __init__(self,text,start=1,format="%03d"):
        #self.text = text
        #self.next_num = itertools.count(start)
        #self.full_format = "%s" + format
    #def next(self):
        #return self.full_format %(self.text, self.next_num.next())

#class NewDate():
    #def __init__(self, start_date = (2005,1,1), increment = 1):
        #self.day = start_date[2]
        #self.month = start_date[1]
        #self.year = itertools.count(start_date[0])
        #self.days = range(1,28,increment)
        #self.months = range(1,12)
          
    #def next_iterator(self):
        #for y in self.year:
            #for m in self.months:
                #for d in self.days:
                    #yield date(y, m, d)
        #return
    #@staticmethod
    #def create( start_date = (2008,1,1), increment = 5):
        #new_date = NewDate(start_date, increment)
        #return new_date.next_iterator()

#def reference_ok(reference_value):
    #test_key = reference_value.key()
    #val = db.get(test_key)
    #return (val != None)
    

#def create_named_test_models(base_name, count):
    #models = []
    #name_gen = NumberedText(base_name)
    #for name in xrange(count):
        #models.append(TestModel.create(name_gen.next()))
    #return models
            
#def delete_named_test_models(base_name, count):
    #test_model_name_start = base_name + "TM_0"
    #test_model_name_end = base_name + "TM_999"
    #test_model_query = TestModel.all()
    #test_model_query.filter("name > ", test_model_name_start)
    #test_model_query.filter("name < ", test_model_name_end)
    #for test_model in test_model_query:
        #test_model.delete()

#def clean_histories():
    #no_owner = []
    #qh = History.all()
    #owner = None
    #for history in qh:
        #print history

if __name__ == '__main__':
    #models = create_named_test_models("t",3)
    #txtit = NumberedText("text ")
    #dateit = NewDate.create()
    #m1 = models[0]
    #m1_name = unicode(models[0])
    #h1 = m1.history1
    #h2 = m1.history2
    #h3 = m1.history3
    #h1.add_entry(dateit.next(), txtit.next())
    #p = h1.get_entries_tuples_list()
    #print p
    #h1.add_entry(dateit.next(), txtit.next())
    #p = unicode(h1)
    #print p
    #d1 = dateit.next()
    #delta = timedelta(2)
    #d2 = d1 - delta
    #h1.add_entry(d1, txtit.next())
    #h1.add_entry(d2, txtit.next())
    #p = h1.get_entries_tuples_list()
    #print p
    #h2.add_entry(dateit.next(),"",models[1])
    #p = unicode(h2)
    #print p
    #h3.add_entry(dateit.next(), txtit.next())
    #h3.add_entry(dateit.next(), txtit.next())
    #h3.add_entry(dateit.next(), txtit.next())
    #h3.end_entry(1, dateit.next())
    #print h3.get_entries_tuples_list(True)
    #print h1.get_entries_tuples_list()
    #print "-----------------------------------"
    #query_string = 'SELECT * FROM TestModel ORDER BY name'
    #q1 =db.GqlQuery(query_string)
    #m1 = q1.get()
    #print m1.history1.get_entries_tuples_list()
    #print m1.history3.entry_count()
    #print "-++++++++---+++++++++++------------"
    #m1.remove()
    #print "-----------------------------------"
    #qt = TestModel.all()
    #models = qt.fetch(50)
    #print "==== deleting %d test models" %qt.count()
    #for model in models:
        #print unicode(model)
        #model.remove()
    #qh = History.all()
    #qe = HistoryEntry.all()
    #print "Final %d TM %d History %d History entries" \
          #%(qt.count(), qh.count(), qe.count())
    #for history in qh:
        #print history.entry_count()
    

    q = models.Student.all()
    students = q.fetch(100)
    print unicode(students[0])
    students[0].remove()
    
    
    
                    
    
        
    