#!/usr/bin/python2.5
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
A small file to generate the first objects required to create the database
"""
import sys, logging
import datetime
sys.path.insert(1,'/home/master/SchoolsDatabase/phSchoolDB/')
from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()
from appengine_django.models import BaseModel
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
import SchoolDB.views
import SchoolDB

def initial_build():
    national = SchoolDB.models.National(name = "National DepEd")
    national.put()
    pending_entities = []
    for name in ("Math", "Science", "Filipino", "English", "TLE", 
                 "AP","Values", "MAPEH"):
        pending_entities.append(SchoolDB.models.Subject(name=name,
                            organization = national, parent = national))
    db.put(pending_entities)
    logging.info("Created subjects")
    pending_entities = []
    for name in ("Culinary Arts", "Dressmaking", "Electricity and Electronics",
                 "Information Technology (I.T.)", "Metalworking"):
        pending_entities.append(SchoolDB.models.StudentMajor(name=name,
                            organization = national, parent = national))
    db.put(pending_entities)
    logging.info("Created majors")
    pending_entities = []
    for name in ("Dropped Out", "Graduated", "Transferred Out"):
        pending_entities.append(SchoolDB.models.StudentStatus(name = name,
                                organization = national,parent = national))
        pending_entities.append(SchoolDB.models.StudentStatus(
            name = "Enrolled", active_student=True, default_choice=True,
            organization = national,parent = national))
    db.put(pending_entities)
    logging.info("Created statuses")
    pending_entities = []
    for name in ("Balik Aral", "Transferred In", "Repeater", "----"):
        pending_entities.append(SchoolDB.models.SpecialDesignation(name = name,
                                organization = national,parent = national))
    db.put(pending_entities)
    logging.info("Created special designations")
    section_types = []
    for name in ("Pilot", "Regular", "Remedial"):
        section_types.append(SchoolDB.models.SectionType(name = name, 
                        organization = national, parent = national))
    db.put(section_types)
    logging.info("Created section type")    
    pending_entities = []
    pending_entities.append(SchoolDB.models.SchoolYear(name = "2010-2011", 
                             start_date = datetime.date(2010,6,13),
                             end_date = datetime.date(2011,6,3), 
                             organization = national, parent = national))
    pending_entities.append(SchoolDB.models.SchoolYear(name = "2011-2012", 
                             start_date = datetime.date(2011,6,6),
                             end_date = datetime.date(2012,3,30), 
                             organization = national, parent = national))
    db.put(pending_entities)
    logging.info("Created school years")
    pending_entities = []
    for p in [("First",7,30,8,30),("Second",8,30,9,30),
                ("Third",9,30,10,30),("Fourth",10,30,11,30),
                ("Fifth",11,30,12,30),("Lunch",12,30,13,30),
                ("Sixth",13,30,14,30),("Seventh",14,30,15,30),
                ("Eighth",15,30,16,30)]:
        period = SchoolDB.models.ClassPeriod(name = p[0] + " Period",
                             organization = national, parent= national)
        try:
            period.start_time = datetime.time(p[1],p[2])
            period.end_time = datetime.time(p[3],p[4])
        except:
            pass
        pending_entities.append(period)
    db.put(pending_entities)
    logging.info("Created class periods")
    region = SchoolDB.models.Region(name="Region VII",
                                    area_name = "Central Visayas")
    region.put()
    
    divisions = []
    for name in ("Cebu City", "Danao City", "Cebu Province"):
        divisions.append(SchoolDB.models.Division(name = name,
                                                        region = region))
    db.put(divisions)
    logging.info("Created divisions")
    
#now run province, municipality, barangay
#next run sections - use same for Composetela NHS and Practice School 1
#finally run students only for practice school
if __name__ == "__main__":
    logging.info("Starting initial database build")
    initial_build()
    logging.info("Build complete")
    
    