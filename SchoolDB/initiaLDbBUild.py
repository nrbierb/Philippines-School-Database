#!/usr/bin/python
"""
A small file to generate the first objects required to create the database
"""
import sys
sys.path.insert(1,'/home/master/SchoolsDatabase/phSchoolDB/')
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from SchoolDB.models import *

national = National(name = "National DepEd")
national.put()
for name in "Math", "Science", "Filipino", "English", "TLE", "AP"):
    subject = Subject(name=name, organization = national)
    subject.put()
for name in ("Registered" "Dropped Out", "Graduated"):
    status = StudentStatusType(name = name, organization = national, 
                               parent = national)
    status.put()
for name in ("First", "Second","Third","Fourth","Fifth","Sixth","Seventh"):
    period = ClassPeriod(name = name + " Period", organization = national,
                         parent = national)
    period.put()
for name in ("Pilot", "Normal", "Remedial"):
    section_type = SectionType(name = name, organization = national,
                               parent = national)
    section_type.put()
for name in ("School Administrator","Teacher","Database Administrator", 
             "Master"):
    usertype = UserType(name = name)
    usertype.put()
region = Region(name="Region 9")
region.put()
for name in ("Cebu City", "Danue City", "Cebu Province"):
    division = Division(name = name, region = region)
    division.put()
for name in ("Compostela NHS", "Compostela SciTec", "Practice School 2",
             "Practice School 1"):
    school = School(name=school, division = division)
    school.put()
master_person = Administrator(first_name = "Neal", last_name = "Bierbaum", 
                              organization = school, gender = "Male")
master_person.put()
masterDBUser = DatabaseUser(name = "Neal Bierbaum", person = master_persion,
                            organization = school, email="nrbierb@gmail.com",
                            user_type = user_type)
masterDBUser.post_creation()

#now run province, municipality, barangay
#next run sections - use same for Composetela NHS and Practice School 1
#finally run students only for practice school
