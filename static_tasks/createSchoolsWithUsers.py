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
Create the school environment with schools, sections, classrooms, and a 
basic set of users
"""
from datetime import date
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

def create_schools():
    schools = {}
    for desc in (
        ("Liloan Practice HS",
         SchoolDB.utility_functions.get_entities_by_name(
             SchoolDB.models.Division,"Cebu Province", ), 
         SchoolDB.utility_functions.get_entities_by_name(
             SchoolDB.models.Municipality, "Liloan")),
        ("Danao City Practice HS",
         SchoolDB.utility_functions.get_entities_by_name(
             SchoolDB.models.Division,"Danao City", ), 
         SchoolDB.utility_functions.get_entities_by_name(
             SchoolDB.models.Municipality, "Danao City")), 
        ("Cebu City Practice HS",
         SchoolDB.utility_functions.get_entities_by_name(
             SchoolDB.models.Division,"Cebu Province", ), 
         SchoolDB.utility_functions.get_entities_by_name(
             SchoolDB.models.Municipality, "Cebu City")), 
        ("Compostela Practice HS",
         SchoolDB.utility_functions.get_entities_by_name(
             SchoolDB.models.Division,"Cebu Province", ), 
         SchoolDB.utility_functions.get_entities_by_name(
             SchoolDB.models.Municipality, "Compostela"))):
        schools[desc[0]] = (SchoolDB.models.School(name=desc[0], 
                        division = desc[1], municipality = desc[2]))
    db.put(schools.values())
    logging.info("Completed Schools creation")
    return schools

def create_users(schools):
    #compostela master
    master_person = SchoolDB.models.Teacher(first_name = "Neal", 
        last_name = "Bierbaum-CM", organization = schools["Compostela Practice HS"],
                gender = "Male")
    master_person.put()
    usertype = SchoolDB.utility_functions.get_entities_by_name(
        SchoolDB.models.UserType,"Master")
    masterDBUser = SchoolDB.models.DatabaseUser(first_name = "Neal",
                                last_name = "Bierbaum", 
                                person = master_person,
                                organization = schools["Compostela Practice HS"], 
                                email="nrbierbcm@gmail.com",
                                user_type = usertype)
    masterDBUser.post_creation()
    #liloan master
    master_person = SchoolDB.models.Teacher(first_name = "Neal", 
        last_name = "Bierbaum-LA", organization = schools["Liloan Practice HS"],
                gender = "Male")
    master_person.put()
    usertype = SchoolDB.utility_functions.get_entities_by_name(
        SchoolDB.models.UserType,"Master")
    masterDBUser = SchoolDB.models.DatabaseUser(first_name = "Neal",
                                last_name = "Bierbaum", 
                                person = master_person,
                                organization = schools["Liloan Practice HS"], 
                                email="nrbierb@gmail.com",
                                user_type = usertype)
    masterDBUser.post_creation()
    #danao master
    master_person = SchoolDB.models.Teacher(first_name = "Neal", 
        last_name = "Bierbaum-DN", organization = schools["Danao City Practice HS"],
                gender = "Male")
    master_person.put()
    usertype = SchoolDB.utility_functions.get_entities_by_name(
        SchoolDB.models.UserType,"Master")
    masterDBUser = SchoolDB.models.DatabaseUser(first_name = "Neal",
                                last_name = "Bierbaum", 
                                person = master_person,
                                organization = schools["Danao City Practice HS"], 
                                email="nrbierbdn@gmail.com",
                                user_type = usertype)
    masterDBUser.post_creation()
    #Cebu City master
    master_person = SchoolDB.models.Teacher(first_name = "Neal", 
        last_name = "Bierbaum-CC", organization = schools["Cebu City Practice HS"],
                gender = "Male")
    master_person.put()
    usertype = SchoolDB.utility_functions.get_entities_by_name(
        SchoolDB.models.UserType,"Master")
    masterDBUser = SchoolDB.models.DatabaseUser(first_name = "Neal",
                                last_name = "Bierbaum", 
                                person = master_person,
                                organization = schools["Cebu City Practice HS"], 
                                email="nrbierbcc@gmail.com",
                                user_type = usertype)
    masterDBUser.post_creation()
    region7 = SchoolDB.utility_functions.get_entities_by_name(
                                    SchoolDB.models.Region, "Region VII")
    #Region 7 master
    master_person = SchoolDB.models.Administrator(first_name = "Neal", 
        last_name = "Bierbaum-R7", organization = region7,
                gender = "Male")
    master_person.put()
    usertype = SchoolDB.utility_functions.get_entities_by_name(
        SchoolDB.models.UserType,"Master")
    masterDBUser = SchoolDB.models.DatabaseUser(first_name = "Neal",
                                last_name = "Bierbaum", 
                                person = master_person,
                                organization = region7, 
                                email="nrbierbr7@gmail.com",
                                user_type = usertype)
    masterDBUser.post_creation()    
    teacher = SchoolDB.models.Teacher(first_name = "A", middle_name = "Db", 
            last_name = "Tester", organization = schools["Liloan Practice HS"])
    teacher.put()
    usertype = SchoolDB.utility_functions.get_entities_by_name(
        SchoolDB.models.UserType,"Teacher")
    teacher_user = SchoolDB.models.DatabaseUser(first_name = "A", 
                                middle_name = "Db", 
                                last_name = "Tester", 
                                person=teacher, 
                                organization = schools["Liloan Practice HS"],
                                email = "ph.db.tester@gmail.com", 
                                user_type = usertype)
    teacher_user.post_creation()
    teacher = SchoolDB.models.Teacher(first_name = "A", 
                    middle_name = "Practice", 
                     last_name = "TeacherCmpstla", 
                     organization = schools["Compostela Practice HS"])
    teacher.put()
    teacher_user = SchoolDB.models.DatabaseUser(first_name = "A", 
                                middle_name = "Practice", 
                                last_name = "TeacherCmpstla", 
                                person=teacher, 
                                organization = schools["Compostela Practice HS"],
                                email = "ph.db.cnhs.teacher@gmail.com", 
                                user_type = usertype)
    teacher_user.post_creation()
    teacher = SchoolDB.models.Teacher(first_name = "Demo", 
                      last_name = "Teacher1", 
                     organization = schools["Liloan Practice HS"])
    teacher.put()
    teacher_user = SchoolDB.models.DatabaseUser(first_name = "Demo", 
                      last_name = "Teacher1", 
                                person=teacher, 
                                organization = schools["Liloan Practice HS"],
                                email = "pi.demo.teacher1@gmail.com", 
                                user_type = usertype)
    teacher_user.post_creation()
    teacher = SchoolDB.models.Teacher(first_name = "Demo", 
                      last_name = "Teacher2", 
                     organization = schools["Danao Practice HS"])
    teacher.put()
    teacher_user = SchoolDB.models.DatabaseUser(first_name = "Demo", 
                      last_name = "Teacher2", 
                                person=teacher, 
                                organization = schools["Danao Practice HS"],
                                email = "pi.demo.teacher2@gmail.com", 
                                user_type = usertype)
    teacher_user.post_creation()
    teacher = SchoolDB.models.Teacher(first_name = "Demo", 
                      last_name = "Teacher3", 
                     organization = schools["Cebu City Practice HS"])
    teacher.put()
    teacher_user = SchoolDB.models.DatabaseUser(first_name = "Demo", 
                      last_name = "Teacher3", 
                                person=teacher, 
                                organization = schools["Cebu City Practice HS"],
                                email = "pi.teacher3@gmail.com", 
                                user_type = usertype)
    teacher_user.post_creation()
    #Region 7 user
    usertype = SchoolDB.utility_functions.get_entities_by_name(
        SchoolDB.models.UserType,"UpperLevelDbAdministrator")
    admin = SchoolDB.models.Administrator(first_name = "Admin", 
                    middle_name = "For", 
                     last_name = "Region7", 
                     organization = region7)
    admin.put()
    admin_user = SchoolDB.models.DatabaseUser(first_name = "Admin", 
                                middle_name = "For", 
                                last_name = "Region7", 
                                person=admin, 
                                organization = region7,
                                email = "pi.db.region7@gmail.com", 
                                user_type = usertype)
    admin_user.post_creation()

    logging.info("Created users")

def create_sections(schools):
    for school in (
        #Lilo An 6, 5, 4, 4 
        (schools["Liloan Practice HS"],
         (("Red", "Blue", "Green", "Orange", "White", "Yellow"),
          ("Gold","Silver","Bronze","Copper","Aluminum"),
          ("East","West","North","South"),
          ("Laugh","Whistle","Sing","Shout"))),       
        #Danau 4, 4, 3, 3
        (schools["Danao City Practice HS"],
        (("Up", "Down", "Left", "Right"),
         ("Earth", "Air", "Fire", "Water"),
         ("Whale", "Dolphin", "Shark"),
         ("Sun", "Moon", "Stars"))),
        #Cebu City 5, 5, 4, 3
        (schools["Cebu City Practice HS"],
         (("Red", "Blue", "Green", "Orange", "White", "Yellow"),
          ("Gold","Silver","Bronze","Copper","Aluminum"),
          ("North","South", "East","West"),
          ("Laugh","Whistle","Sing", "Shout"))),    
        #Compostela
        (schools["Compostela Practice HS"],
         (("Gold", "Aluminum", "Bronze", "Copper", "Krypton", "Lead",
           "Mercury", "Neon", "Nickel", "Silver", "Tin", "Zinc"), 
          ("Rose", "Carnation", "Cattleya", "Dahlia", "Daisy", "Jasmine", "Orchid",
           "Sampaguita", "Santan", "Tulip"), 
          ("Rizal", "Agoncillo", "Aguinaldo", "Aquino", "Bonifacio", "Del Pilar", 
           "Jacinto", "Mabini", "Quezon"),
          ("Diamond", "Amethyst", "Emerald", "Garnet", "Jade", "Jasper", 
           "Ruby", "Sapphire", "Topaz")))):
        create_sections_for_school(school)

def create_sections_for_school(school_info):
    """
    Create the sections for the school
    """    
    school = school_info[0]
    school_name = school.name
    section_names = school_info[1]
    sections = []
    rooms = []
    pilot_type = SchoolDB.utility_functions.get_entities_by_name(
             SchoolDB.models.SectionType, "Pilot")
    regular_type = SchoolDB.utility_functions.get_entities_by_name(
             SchoolDB.models.SectionType, "Regular")
    year_names = ("First Year", "Second Year", "Third Year", "Fourth Year")
    room_number = 0
    section_count = 0
    rooms = []
    for i in range(4):
        section_count += len(section_names[i])
    #create all classrooms for school
    for i in range(1, section_count+1):
        room_name = "#%d" %i
        rooms.append(SchoolDB.models.Classroom(parent=school, 
                            organization=school, name=room_name,
                            active=True))
    db.put(rooms)
    logging.info("Created %d classrooms for %s" 
                 %(section_count, school_name))
    for i in range(4):
        year_name = year_names[i]
        #first section in the list for the year will be a pilot section
        section_type = pilot_type
        for section_name in section_names[i]:
            #create the section
            sections.append(SchoolDB.models.Section(parent=school, 
                        name=section_name, section_type=section_type,
                        organization=school, classroom=rooms[room_number],
                        class_year=year_name))
            room_number += 1
            section_type = regular_type
        logging.info("Initialized %d sections for school %s class year %s" 
                     %(len(section_names), school_name, year_name))
    db.put(sections)
    logging.info("Created %d sections for school %s" 
                 %(section_count, school_name))
    
#now run province, municipality, barangay
#next run sections - use same for Composetela NHS and Practice School 1
#finally run students only for practice school
if __name__ == "__main__":
    logging.info("Starting school creation")
    schools = create_schools()
    users = create_users(schools)
    create_sections(schools)
    logging.info("School creation complete")
