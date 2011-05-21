#!/usr/bin/python
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
Program to build student and parent records for demo and practice databases
"""
import re, csv, logging, random, optparse
import sys, codecs, os, bz2, cPickle, binascii
from datetime import date
from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()
from appengine_django.models import BaseModel
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
import SchoolDB.views
import SchoolDB
student_data_compressed_pickle = \
"""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"""

def get_data_table():
    bin_data = binascii.a2b_base64(student_data_compressed_pickle)
    b = binascii.crc32(bin_data)
    pickle_data = bz2.decompress(bin_data)
    data_table = cPickle.loads(pickle_data)
    return data_table

def convert_date(text_val):    
    parts = re.findall(r'\d+',text_val)
    if not len(parts):
        #empty value
        return None
    else:
        year = int(parts[0])
    return date(year, int(parts[1]), int(parts[2]))

class TableValuesGenerator():
    """
    Return a set of representative values from a sample csv file for a student
    and a parent. These need to be combined with computed values from other functions to yield the full set of values to create the student and parent.
    """
    def __init__(self):
        self.data_table = {}
        
    def read_csv_file (self, csv_file):
        """
        Process the csv file with student sample data directly.
        """
        dict_reader = csv.DictReader(csv_file)
        #create the dict to be used for sample data
        data_row = dict_reader.next()
        converted_row = self.prepare_data_row(data_row)
        for key in converted_row.keys():
            self.data_table[key] = [converted_row[key]]
        for data_row in dict_reader:
            converted_row = self.prepare_data_row(data_row)
            for key in converted_row.keys():
                self.data_table[key].append(converted_row[key])
        logging.info("Loaded %d rows." 
                     %len(self.data_table["Male first name"]))
        
    def load_pickled_data(self):
        """
        Use the preprocessed data stored as a compressed pickle in 
        studentSampleData.py
        """
        self.data_table = get_data_table()
        logging.info("Loaded %d rows." 
                     %len(self.data_table["Male first name"]))
            
    def prepare_data_row(self, data_row):
        """
        Convert values in row to correct data form.
        """
        for col_name in ("First Year birthday", "Second Year birthday", 
                         "Third Year birthday", "Fourth Year birthday"):
            data_row[col_name] = convert_date(data_row[col_name])
        return data_row
    
    def create_table_values_dict(self, class_year):
        """
        Return a set of values as a dict that can be used to build a student_record.
        """
        values = {}
        values["gender"] = random.choice(["Male","Female"])
        first_name_gender = values["gender"] + " first name"
        middle_name_gender = values["gender"] + " middle name"
        values["first_name"] = random.choice(
            self.data_table[first_name_gender])
        values["middle_name"] = random.choice(
            self.data_table[middle_name_gender])
        values["last_name"] = random.choice(
            self.data_table["last name"])
        class_year_birthday = class_year + " birthday"
        values["birthdate"] = str(date.toordinal(random.choice(
            self.data_table[class_year_birthday])))
        values["relationship"] = random.choice(
            self.data_table["relationship"])
        p_gender = "Male"
        if (values["relationship"] == "Mother"):
            p_gender = "Female"
        values["parent_first_name"] = random.choice(
            self.data_table[p_gender + " first name"])
        values["parent_middle_name"] = random.choice(
            self.data_table[p_gender + " middle name"])
        values["occupation"] = random.choice(
            self.data_table[p_gender + " occupations"])
        return values

class SchoolData():
    """
    Get the information about the school to create the students for it.
    The information includes:
    School organization
    Municipality
    Province
    Baranguay choices
    Sections
    """    
    def __init__(self, school_name):
        """
        """
        self.school_name = school_name
        self.school = SchoolDB.utility_functions.get_entities_by_name(
            SchoolDB.models.School, school_name)
        if (not self.school):
            logging.error('"%s" is not a valid school name' %school_name)
            exit(-1)
        self.municipality = self.school.municipality
        self.province = self.municipality.province
        query = SchoolDB.models.Community.all(keys_only=True)
        query.filter("municipality =", self.municipality)
        self.communities = query.fetch(100)
        query = SchoolDB.models.Section.all()
        query.filter("organization =", self.school)
        self.sections = query.fetch(100)
        
    def get_sections(self):
        return self.sections
    
    def get_school(self):
        return self.school
    
    def create_school_values_dict(self, section):
        """
        Create a value dictionary for all items based upon the school.
        """
        class_year = section.class_year
        community = random.choice(self.communities)
        data = {"province":str(self.province.key()), 
                "municipality":str(self.municipality.key()),
                "community":str(community),
                "section":str(section.key()), 
                "class_year":class_year}
        return data
    
class ValuesDictGenerator:
    """
    The creator of the complete values dictionary that will be used to
    create the student. This includes all logic for the arbitrary
    generation of student data other than that created from the csv
    table.
    """
    def __init__(self, csv_values_generator, school_data_generator):
        """
        
        """
        self.csv_values_generator = csv_values_generator
        self.school_data_generator = school_data_generator
        self.majors_list = self.create_majors_list()
        self.special_values_dict = self.create_special_designation_dict()
        #set arbitrary change date for everything        
        self.change_date = str(date.toordinal(date(2010,6,10)))
        
    def create_complete_values_dict(self, section):
        """
        """
        self.section = section
        self.class_year = section.class_year
        self.values_dict = self.csv_values_generator.create_table_values_dict(
            self.class_year)
        self.values_dict.update(
            self.school_data_generator.create_school_values_dict(
                section))
        #for now set the birth location information the same as the
        #current
        self.values_dict["birth_province"] = self.values_dict["province"]
        self.values_dict["birth_municipality"] = self.values_dict["municipality"]
        self.values_dict["birth_community"] = self.values_dict["community"]
        #all initial student status is enrolled
        self.values_dict["student_status"] = \
            str(SchoolDB.utility_functions.get_entities_by_name(
                SchoolDB.models.StudentStatus, "Enrolled").key())
        self.values_dict["student_status_change_date"] = self.change_date
        self.values_dict["class_year_change_date"] = self.change_date
        self.values_dict["section_change_date"] = self.change_date
        self.values_dict["years_in_elementary"] = str(6.0)
        if (random.random() > 0.8):
            self.values_dict["years_in_elementary"] = str(7.0)
        self.values_dict["elementary_gpa"] = str(random.randrange(70,100))
        self.values_dict["elementary_school"] = \
            unicode(SchoolDB.utility_functions.get_instance_from_key_string(
                self.values_dict["municipality"])) + " Elementary School"
        self.set_class_year_dependant_values()
        self.set_low_probability_values()
        return self.values_dict

    def set_class_year_dependant_values(self):
        """
        Set dict values that are different depending upon class year
        """
        base_elementary_graduation_date = date.toordinal(date(2010,3,30))
        base_change_date = date.toordinal(date(2010,6,15))
        self.values_dict["student_major"] = random.choice(self.majors_list)
        if (self.class_year == "First Year"):
            offset = 0
        elif (self.class_year == "Second Year"):
            offset = -365
        elif (self.class_year == "Third Year"):
            offset = -730
        else:
            offset = -1095
        self.values_dict["elementary_graduation_date"] = \
            str(base_elementary_graduation_date + offset)
        self.values_dict["student_major_change_date"] = \
            str(base_change_date + offset)
    
    def set_low_probability_values(self):
        """
        Set values that are only rarely set
        """
        self.values_dict["special_designation"] = ""
        self.values_dict["special_designation_change_date"] = self.change_date
        self.values_dict["transfer_school"] = ""
        self.values_dict["transfer_direction"] = "In"
        self.values_dict["transfer_date"] = self.change_date
        if (random.random() > 0.9):
            #set a value
            test_val = random.random()
            if (test_val < 0.45):
                self.values_dict["transfer_school"] = "Other Municipality School"
                self.values_dict["special_designation"] = \
                    self.special_values_dict["Transfered In"]
            elif (test_val > 0.6):
                self.values_dict["special_designation"] = \
                    self.special_values_dict["Balik Aral"]
            else:
                self.values_dict["special_designation"] = \
                    self.special_values_dict["Repeater"]

    def create_majors_list(self):
        query = SchoolDB.models.StudentMajor.all()
        majors = query.fetch(20)
        majors_list = [str(major.key()) for major in majors]
        return majors_list
    
    def create_special_designation_dict(self):
        d_dict = {}
        for val in ("Balik Aral", "Repeater", "Transfered In"):
            d_dict[val] = \
                  str(SchoolDB.utility_functions.get_entities_by_name(
                      SchoolDB.models.SpecialDesignation, val).key())
        return d_dict

def create_student_tasks(values_creator, school_data, students_per_section):
    sections = school_data.get_sections()
    count = 0
    logging.info("Starting task generation")
    for section in sections:
        #create student_count students for each section by a single task 
        #for each student
        for i in range(students_per_section):
            values_dict = values_creator.create_complete_values_dict(
                section)
            task_generator = SchoolDB.assistant_classes.TaskGenerator(
                task_name = "Create Student %s:%s" \
                %(unicode(section),values_dict["last_name"]),
                function = "SchoolDB.utilities.createStudents.create_student",
                function_args = "values_dict = %s" %values_dict,
                organization = str(school_data.get_school().key()),
                rerun_if_failed = False)
            task_generator.queue_tasks()
            count += 1
    return count

def local_create_students(values_creator, school_data, 
                                       students_per_section):
    """
    Call the create_student function directly in this code. Will not
    work with large numbers of students but useful for testing.
    """
    sections = school_data.get_sections()
    count = 0
    for section in sections:
        #create student_count students for each section by a single task 
        #for each student
        for i in xrange(students_per_section):
            values_dict = values_creator.create_complete_values_dict(
                section)
            create_student(values_dict)
            count += 1
    return count

#---------------------------------------------------------------------
#The remaining code is called by a task to actually create a student

class StudentCreator:
    """
    This class creates a student, parent, family, histories, and attendance
    record.
    """
    def __init__(self, values_dict):
        self.values_dict = values_dict
        self.section = SchoolDB.utility_functions.get_instance_from_key_string(
            values_dict["section"])
        self.organization = self.section.organization
        self.class_year = self.section.class_year
        self.family = None
        self.student = None
                        
    def create_parent_and_family(self):
        """
        Create a parent with the same last name as the student. Try to find an
        existing parent with the same last name for a fraction of the students
        to create multiple families.
        """
        try:
            self.family = None
            if (random.random() < 0.05):   
                query = SchoolDB.models.Student.all(keys_only=True)
                query.filter("organization = ", self.organization)
                query.filter("last_name =", self.values_dict["last_name"])
                students = query.fetch(20)
                if students:
                    student_key = random.choice(students)
                    self.family = db.get(student_key).family
            if (not self.family):
                self.family = SchoolDB.models.Family(
                    name=self.values_dict["last_name"])
                self.family.put()
                parent = SchoolDB.models.ParentOrGuardian(
                    first_name = self.values_dict["parent_first_name"],
                    middle_name = self.values_dict["parent_middle_name"],
                    last_name = self.values_dict["last_name"],
                    occupation = self.values_dict["occupation"],
                    relationship = self.values_dict["relationship"],
                    contact_order = "First",
                    family = self.family)
                parent.put()
        except StandardError, e:
            logging.error("Failed to create parent %s: %s" \
                          %(values_dict["last_name"], e))
            
    def create_student_entity(self):
        """
        Create the student database entity. Associated entities are created in
        other functions. The parent and family entities must already be created.
        """
        try:
            self.student = SchoolDB.models.Student(
                first_name = self.values_dict["first_name"],
                middle_name = self.values_dict["middle_name"],
                last_name = self.values_dict["last_name"],
                gender = self.values_dict["gender"],
                birthdate = date.fromordinal(int(self.values_dict["birthdate"])),
                elementary_school = self.values_dict["elementary_school"],
                elementary_graduation_date = date.fromordinal(int(self.values_dict[
                    "elementary_graduation_date"])),
                elementary_gpa = float(self.values_dict["elementary_gpa"]),
                years_in_elementary = float(self.values_dict["years_in_elementary"]),
                organization = self.organization,
                family = self.family,
                province = SchoolDB.utility_functions.get_instance_from_key_string(
                    self.values_dict["province"], SchoolDB.models.Province),
                municipality = \
                  SchoolDB.utility_functions.get_instance_from_key_string(
                      self.values_dict["municipality"],SchoolDB.models.Municipality),
                community = \
                  SchoolDB.utility_functions.get_instance_from_key_string(
                      self.values_dict["community"], SchoolDB.models.Community),
                birth_province = \
                  SchoolDB.utility_functions.get_instance_from_key_string(
                      self.values_dict["birth_province"],SchoolDB.models.Province),
                birth_municipality = \
                  SchoolDB.utility_functions.get_instance_from_key_string(
                      self.values_dict["birth_municipality"], 
                      SchoolDB.models.Municipality),
                birth_community = \
                  SchoolDB.utility_functions.get_instance_from_key_string(
                      self.values_dict["birth_community"], SchoolDB.models.Community),
                student_status = \
                  SchoolDB.utility_functions.get_instance_from_key_string(
                      self.values_dict["student_status"], 
                      SchoolDB.models.StudentStatus),
                student_status_change_date = date.fromordinal(int(self.values_dict[
                    "student_status_change_date"])),
                class_year = self.class_year,
                class_year_change_date = date.fromordinal(int(self.values_dict[
                    "class_year_change_date"])),
                section = self.section,
                section_change_date = date.fromordinal(int(self.values_dict[
                    "section_change_date"])))
            if (self.values_dict["student_major"]):
                self.student.student_major = \
                  SchoolDB.utility_functions.get_instance_from_key_string(
                      self.values_dict["student_major"], SchoolDB.models.StudentMajor)
                self.student.student_major_change_date = date.fromordinal(int(
                    self.values_dict["student_major_change_date"]))
            if (self.values_dict["special_designation"]):
                self.student.special_designation = \
                  SchoolDB.utility_functions.get_instance_from_key_string(
                      self.values_dict["special_designation"], 
                      SchoolDB.models.SpecialDesignation)
                self.student.student_major_change_date = date.fromordinal(int(
                    self.values_dict["special_designation_change_date"]))
            if (self.values_dict["transfer_school"]):
                self.student.transfer_school = self.values_dict["transfer_school"]
                self.student.transfer_direction = self.values_dict[
                    "transfer_direction"],
                self.student.transfer_date = date.fromordinal(int(self.values_dict[
                    "transfer_date"]))
            self.student.put()
            self.student.update_my_histories()
            self.student.attendance = SchoolDB.models.StudentAttendanceRecord.create(
                parent_entity = self.student, 
                start_date = self.student.class_year_change_date)
            self.student.put()
            logging.info("Created student %s" %unicode(self.student))
            return self.student
        except AssertionError, e:
            logging.error("Failed to create student %s: %s" \
                          %(self.values_dict["last_name"], e))
            return False             
        
def create_student(values_dict):
    """
    Create a student as a single task. The values dict contains all
    needed values. This is a complex action.
    """
    logging.info("Beginning student creation")
    student_creator = StudentCreator(values_dict)
    student_creator.create_parent_and_family()
    result = student_creator.create_student_entity()
    return result

def create_pickle_file(data_table):
    """
    A function to create an encoded vesion of a compressed pickle of
    the data_table generated from the csv file. The contents of the
    resulting file /tmp/data will be copied into the file
    studentSampleData.py so that no external file need be read when
    performing the build on the net.
    """
    s = bz2.compress(cPickle.dumps(values_generator.data_table))
    st = binascii.b2a_base64(s)
    f = open("/tmp/data",'w')
    f.write(st)
    f.close()
    
#---------------------------------------------------------------------
#function for web call to build
def create_students_for_school(logger, school_name, 
                               students_per_section = 20):
    """
    This performs the full action. It is meant to be called from the web interface.
    """
    if (not school_name):
        error = "No school name. Exiting."
        logger.add_line(error)
        exit(-1)
    values_generator = TableValuesGenerator()
    values_generator.load_pickled_data()
    logging.info("Starting to load school data for " +school_name)
    school_data = SchoolData(school_name)
    logging.info("School data loaded")
    all_values_creator = ValuesDictGenerator(values_generator, school_data)
    student_count = create_student_tasks(all_values_creator, school_data, 
                                         students_per_section)
    message = "Tasks to create %d students have been queued." %student_count
    logging.info(message)
    logger.add_line(message)

    

if __name__ == '__main__':
    p = optparse.OptionParser()
    p.add_option("-r", "--school", action="store", dest="school_name")
    p.add_option("-f", "--csv_file", action="store", dest="csv_filename")
    p.add_option("-n", "--students_per_section", action="store",
                 type="int", dest="students_per_section")
    p.set_defaults(students_per_section=20)
    opt, args = p.parse_args()
    if (not opt.school_name):
        logging.error("No school name. Exiting.")
        exit(-1)
    csv_file = open(opt.csv_filename,'r')
    logging.info("Opened " + opt.csv_filename)
    values_generator = TableValuesGenerator(csv_file)
    school_data = SchoolData(opt.school_name)
    all_values_creator = ValuesDictGenerator(values_generator, school_data)
    #student_count = create_student_tasks(all_values_creator, school_data, 
                                       #opt.students_per_section)
    student_count = local_create_students(all_values_creator, school_data, 
                                       opt.students_per_section)
    logging.info("Tasks to create %d students have been queued." %student_count)

        
    
