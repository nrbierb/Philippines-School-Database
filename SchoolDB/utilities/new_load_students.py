"""
Load a csv file with student records in csv form into the database.
"""
import csv, sys, codecs, os, bz2, cPickle
from datetime import date
#sys.path.insert(1,'/home/master/SchoolsDatabase/phSchoolDB/')
from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()
from appengine_django.models import BaseModel
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from SchoolDB.models import *

line_number = 1
prior_family_id = ""
prior_family = None
#csv_filename = "/home/master/SchoolsDatabase/phSchoolDB/upload_data/students3mid.csv"
#pickle_filename = "/home/master/SchoolsDatabase/phSchoolDB/upload_data/students.pbz"
#csv_filename = "/upload_data/students3mid.csv"
def get_object(class_name, search_name):
    search_name = search_name.strip()
    q = class_name.all()
    q.filter("name =", search_name)
    object = q.get()
    if ((object == None) and (len(search_name) > 0)):
        print "                   Not Found: '%s'"\
              %search_name
    return object

def get_person(class_name, first_name, middle_name, last_name):
    q = class_name.all()
    q.filter("first_name =", first_name)
    q.filter("middle_name =", middle_name)
    q.filter("last_name =", last_name)
    object = q.get()
    return object

def convert_name(name):
    """
    Split a persons name into three parts: first, middle, and last.
    Assume that the first field is the first name, the second the middle
    name, and the last fields the last name and perhaps something like
    "Jr."
    """
    name = process_string(name)
    name_parts = name.split()
    if (len(name_parts) > 3):
        name_parts = name.split(" ", 2)
    if ((len(name_parts) == 3) and name_parts[2].endswith("r.")) :
        name_parts[1] += name_parts[2]
        name_parts.pop()
    if (len(name_parts) == 2):
        name_parts.insert(1,"")
    if (len(name_parts) == 1):
        name_parts = ["--","",name_parts[0]]
    if (len(name_parts) == 0):
        name_parts = ["", "", ""]
    return name_parts

def convert_date(text_val):    
    parts = re.findall(r'\d+',text_val)
    if not len(parts):
        #empty value
        return None
    else:
        year = int(parts[0])
    return date(year, int(parts[1]), int(parts[2]))

def elmentary_gd_processing(text_val):
    #might be a year, a 0 or a blank
    if (text_val == "" or text_val == "0"):
        gd_date = None
    else:
        gd_year = int(text_val)
        gd_date = date(gd_year,4,1)
    return gd_date

def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')

def process_string(val):
#    return val.strip()
    uval = unicode(val.strip())
    return uval.encode('utf-8')

def read_file(file_name):
    """
    Open the csv file, then use a csv DictReader to convert to
    a list of dictionaries, one per line
    """
    #f = codecs.open(file_name,'r','utf-8')
    #reader = csv.DictReader(utf_8_encoder(f))
    f = open(file_name,'r')
    reader = csv.DictReader(f)
    lines = []
    for line in reader:
        lines.append(line)
    f.close()
    return lines

def build_parent(record, family):
    first_name_val,middle_name_val,last_name_val = convert_name(
            record["single_column_parent_name"])
    parent = ParentOrGuardian(
    first_name = first_name_val,
    middle_name = middle_name_val,
    last_name = last_name_val,
    occupation = record["parent.occupation"].strip(),
    primary_contact = True,
    family = family)
    return parent.put()

def get_family(first_name, middle_name, last_name):
    """
    Get the family for the student
    """
    student = get_person(Student, first_name, middle_name, last_name)
    if student:
        family = student.family
    return family

def setup_family(last_name, record):
    global prior_family_id, prior_family
    family_id = record["family_id"]
    if (family_id == prior_family_id):
        family = prior_family
    else:
        family = Family(name = last_name)
        family.put()
        build_parent(record, family)
        prior_family = family
        prior_family_id = family_id
    return family       
    
def build_student_status_history(student, record):
    #set initial enrollment last year
    student.student_status = get_object(StudentStatus,"Enrolled")
    student.student_status_change_date = convert_date(
        record["student_status_change_date"])
    student.student_status_history.add_entry(
        student.student_status_change_date, "", student.student_status)
    if (record["student_status"] != "Enrolled"):
        student.student_status = get_object(StudentStatus, record["student_status"])
        if record["action_date"]:
            student.student_status_change_date = convert_date(
                record["action_date"])
        else:
            #unknown date, just use middle of school year
            student.student_status_change_date = convert_date("10/10/2009")
        student.student_status_history.add_entry(
            student.student_status_change_date, "", student.student_status)

def build_class_year_history(student, record):
    student.class_year_change_date = convert_date(
            record["student_status_change_date"])
    student.class_year = record["class_year"].strip()
    student.class_year_history.add_entry(
        student.class_year_change_date, student.class_year)
    
def build_section_history(student,record):
    student.section = get_object(Section,record["section"])
    student.section_change_date = convert_date(
            record["student_status_change_date"])
    if student.section:
        student.section_history.add_entry(
            student.section_change_date, "",student.section)
    
def build_special_designation_history(student, record):
    des_obj = None
    if (record["balik_aral"] == "True"):
        des_obj = get_object(SpecialDesignation, "Balik Aral")
    elif (record["repeater"] == "True"):
        des_obj = get_object(SpecialDesignation, "Repeater")
    elif (record["transfer_in"] == "True"):
        des_obj = get_object(SpecialDesignation, "Transfered In")
    if (des_obj):
        student.special_designation_history.add_entry(convert_date(
            record["student_status_change_date"]),"",des_obj)
        student.special_designation = get_object(SpecialDesignation, 
                                                 "------")
        student.special_designation_change_date = convert_date("03/31/2010")
        student.special_designation_history.add_entry(
            student.special_designation_change_date, "",
            student.special_designation)
def build_transfer_history(student, record):
    name = ""
    if (record["transfer_to"] != ""):
        name = record["transfer_to"]
        direction = "Out"
    elif (record["transfer_from"] != ""):
        name = record["transfer_from"]
        direction = "In"
    if name:
        transfer_rec = StudentTransfer.create(name, student)
        transfer_rec.direction = direction
        transfer_rec.put()
        student.transfer_history.add_entry(convert_date(
                record["action_date"]), "", transfer_rec)
        student.transfer_school_name = name
        student.transfer_direction = direction
        student.transfer_date = convert_date(record["action_date"])
        
def load_database(record, school):
    """
    Create the complete record for a student and insert into database.
    This will create the student record, a parent record, and several
    history records. 
    """
    student = Student(
        first_name = process_string(record["first_name"]),
        middle_name = process_string(record["middle_name"]),
        last_name = process_string(record["last_name"]),
        gender = record["gender"],
        birthdate = convert_date(record["birthdate"]),
        address = process_string(record["address"]),
        landline_phone = record["landline_phone"].strip(),
        cell_phone = record["cellphone"].strip(),
        elementary_school = process_string(record["elementary_school"]),
        elementary_graduation_date = elmentary_gd_processing(record[
            "elementary_graduation_date"]),
        elementary_gpa = float(record["elementary_gpa"]),
        years_in_elementary = float(record["years_in_elementary"]),
        organization = school,
        family = setup_family(record["last_name"], record),
        province = get_object(Province,record["province"]),
        municipality = get_object(Municipality,record["municipality"]),
        community = get_object(Community,record["community"]),
        student_status = get_object(StudentStatus,"Enrolled"),
        birth_province = get_object(Province,record["birth_province"]))
    obj = get_object(Municipality,record["birth_municipality"])
    student.birth_municipality = obj
    if (obj == None):
        student.birth_municipality_other = \
               process_string(record["birth_municipality"])
    obj = get_object(Community,record["birth_community"])
    student.birth_community = obj
    if (obj == None):
        student.birth_community_other = \
               process_string(record["birth_community"])
    student.put()
    #build all histories 
    student.post_creation(school)
    #now update the histories
    build_student_status_history(student, record)
    build_class_year_history(student, record)
    build_section_history(student,record)
    build_special_designation_history(student, record)
    build_transfer_history(student, record)
    student.put()
    return student
 
def delete_all_students_in_school(school):
    """
    Fully delete all students of the chosen school This is done >>only<<
    during testing.
    """
    q = Student.all()
    q.filter("organization =", school)
    for student in q:
        name = unicode(student)
        student.remove()
        print "Removed " + name
        sys.stdout.flush()

def csv_read(csv_filename):
    records = read_file(csv_filename)
    return records

def process_data(data, start_index, stop_index):
    school_name = "Compostela National High School"
    school = get_object(School, school_name)
    if (not school):
        print "ERROR: UNKNOWN SCHOOL: " + school_name
        sys.exit(-1)
    delete_all_students_in_school(school)
    print("Remove students completed.")
    #return
    max = len(data)
    if ((stop_index > max) or (stop_index == 0)):
        stop_index = max
    if (start_index < 1):
        start_index = 1
    record_count = 0
    for i  in xrange(start_index-1, stop_index): 
        try:
            student = load_database(data[i], school)
        except StandardError, e:
            print "Error line#: %d > %s" %(i + 2, str(e))
        record_count += 1
        print "Created student#: %d  Line#: %d  Name: %s" \
              %(i + 1, i + 2, unicode(student))
        sys.stdout.flush()
    print "Completed. Added %d records." %record_count

def write_pickle(filename, pickle_filename):
    data = csv_read(filename)
    compressed = bz2.compress(cPickle.dumps(data))
    f = open(pickle_filename, 'w')
    f.write(compressed)
    f.close()
    print "completed pickle"

def read_pickle(pickle_filename):
    f = bz2.BZ2File(pickle_filename, "r")
    data_string = f.read(10000000)
    print len(data_string)
    data = cPickle.loads(data_string)
    print len(data)
    data = csv_read()
    return data

def load_student_records(logger, pickle_filename="", 
                         start_index=0, stop_index=0):
    if (not pickle_filename):
        print "usage: load_student_records file_name, start_index, stop_index"
    else:
        data = read_pickle(pickle_filename)
        print "Read %s. Expanded size = %d" %(pickle_filename, len(data))
        process_data(data, start_index, stop_index)

if __name__ == '__main__':
    csv_filename = sys.argv[1]
    pickle_filename = sys.argv[2]
    write_pickle(csv_filename, pickle_filename)
    #if (len (sys.argv) > 3):
        #start_index = int(sys.argv[2])
        #stop_index = int(sys.argv[3])
    #elif (len (sys.argv) > 1):
        #start_index = 1
        #stop_index = int(sys.argv[2])
    #else:
        #start_index = 0
        #stop_index = 1000        
    #data = read_pickle()
    #process_data(data, start_index, stop_index)
    
