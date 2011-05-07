#Copyright 2010,2011 Neal R Bierbaum, Redtreefalcon Software
#This file is part of SchoolsDatabase.

#SchoolsDatabase is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#SchoolsDatabase  is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with SchoolsDatabase.  If not, see <http://www.gnu.org/licenses/>.
"""
Create the localities in the database
"""
import pickle, bz2, optparse, binascii
import os, sys, logging
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')
from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()
from google.appengine.api import users
from google.appengine.ext import db
import SchoolDB.views
import SchoolDB.models

pickle_filename ="/upload_data/localities.bz2"

class Muni():
    def __init__(self, municipality_id, municipality_name, \
                 province_name):
        self.municipality_id = municipality_id
        self.municipality_name = unicode(municipality_name)
        self.province_name = province_name
        self.communitys = []
        
    def add_community(self, community):
        self.communitys.append(unicode(community))

def create_province(province_name):
    db_province = SchoolDB.models.Province(name=province_name)
    #hack to add region VII to Bohol and Cebu
    if ((province_name=="Bohol") or (province_name=="Cebu")):
        db_province.region = SchoolDB.utility_functions.get_entities_by_name(
             SchoolDB.models.Region, "Region VII")
    return db_province.put()

def create_municipality(municipality, province_object, deped_division_name):
    deped_division = SchoolDB.utility_functions.get_entities_by_name(
             SchoolDB.models.Division, deped_division_name)
    deped_division.province = province_object
    deped_division.put()
    db_municpality = SchoolDB.models.Municipality(
        name = municipality.municipality_name, division = deped_division,
        id = municipality.municipality_id, province = province_object)
    db_municpality.put()
    communities = []
    for community_name in municipality.barangays:
        community = SchoolDB.models.Community(parent=db_municpality,
                            name=community_name, municipality=db_municpality)
        communities.append(community)
    db.put(communities)
    #task_generator = SchoolDB.assistant_classes.TaskGenerator(
        #task_name = "Create Communities for %s" %municipality.municipality_name,
        #function = "SchoolDB.utilities.createLocalities.create_communities",        
        #function_args = "communities=%s, municipality_keystr=%s" 
          #%(communities, str(db_municpality.key())),
        #rerun_if_failed = False)
    #task_generator.queue_tasks()
    logging.info("Queued community creation for %d communities in %s" 
                 %(len(communities), municipality.municipality_name))
           
def load_database(data):
    provinces = data.iterkeys()
    target_municipalities = \
            {"Danao City":"Danao City", "Compostela":"Cebu Province", 
             "Liloan":"Cebu Province", "Mandaue City":"Cebu Province", 
             "Cebu City":"Cebu City", "Consolacion":"Cebu Province"}
    for province_name in provinces:
        province_object = create_province(province_name)
        if (province_name == "Cebu"):
            for municipality in data[province_name]:
                if target_municipalities.has_key(municipality.municipality_name):
                    create_municipality(municipality, province_object,
                            target_municipalities[municipality.municipality_name])
    logging.info("Localities load complete.")

def delete_class(class_type):
    found = True
    i=0
    while found:
        q = class_type.all(keys_only=True)
        keys = q.fetch(500)
        found = (len(keys) > 0)
        if found:
            db.delete(keys)
            logging.info("deleted %s %d" %(class_type, len(keys)))

def read_pickle(filename):
    if (os.path.exists(filename)):
        f = bz2.BZ2File(filename, "r")
        data_string = f.read(5000000)
        logging.info("Read file %s. total bytes %d)" %(filename, 
                                                       len(data_string)))
        return pickle.loads(data_string)

def remove_prior():
    delete_class(SchoolDB.models.Province)
    logging.info("deleted Provinces")
    delete_class(SchoolDB.models.Municipality)
    logging.info("deleted Municipalities")
    delete_class(SchoolDB.models.Community)
    logging.info("deleted Communities")

    
#---------------------------------------------------------------------
#The remaining code is called by a task to create the communities            
def create_communities(community_name_list, municipality_keystring): 
    """
    This is a task that will create communities (barangays) associated
    with a municipality
    """
    municipality = SchoolDB.utility_functions.get_instance_from_key_string(
        municipality_keystring, SchoolDB.models.Municipality)
    communities = []
    if municipality:
        for name in community_name_list:
            community = SchoolDB.models.Community(parent=municipality,
                                name=name, municipality=municipality)
            communities.append(community)
    db.put(communities)
    logging.info("Task created %d communities for municipality %s"
                 %(len(communities), unicode(municipality)))
#---------------------------------------------------------------------
                                                   
if __name__ == "__main__":
    p = optparse.OptionParser()
    p.add_option("-r", action="store_true", dest="delete_current")
    p.add_option("-f", action="store", dest="filename")
    p.set_defaults(delete_current=True,
                   filename=pickle_filename)
    opt, args = p.parse_args()
    if (opt.delete_current):
        remove_prior()
    data = read_pickle(opt.filename)    
    load_database(data)
    logging.info("Completed localities creation tasking")
    
            
            
        
    