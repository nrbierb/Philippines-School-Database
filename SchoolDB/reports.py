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
This file contains most of the code used in ajax to create reports.
"""
from datetime import date, timedelta
import exceptions
import logging 
from django.utils import simplejson
from google.appengine.ext import db
import SchoolDB.models 
import SchoolDB.views
import SchoolDB.assistant_classes
import SchoolDB.summaries

class ReportError(exceptions.Exception):
    def __init__(self, args=None):
        self.args = args

#----------------------------------------------------------------------
class StudentAgeReport():

    def __init__(self, params, section):
        """
        Intialize parameters with default values
        """
        date_str = params.get("reference_date",None)
        self.reference_date = SchoolDB.views.convert_form_date(
            date_str, date.today())
        self.section = section
        self.class_year =  params.get('class_year','')
        self.age_calc_type = params.get('age_calc_type', 'schoolyear')
        trim_years_string = params.get('trim_years', 'on')
        self.trim_years = (trim_years_string == "on")
        restrict_years_string = params.get('restrict_years', 'on')
        self.restrict_years = (restrict_years_string == "on")
        self.min_age = int(params.get('min_age', 8))
        self.max_age = int(params.get('max_age', 22))
        # all arrays have Name, Male, Female, Combined as the organization
        # per row
        self.age_counts = [["Younger",0,0,0,0.0,0.0,0.0]]
        self.error = ""
        for i in xrange(self.min_age, self.max_age + 1):
            self.age_counts.append([i,0,0,0,0.0,0.0,0.0])
        self.age_counts.append(["Older",0,0,0,0.0,0.0,0.0])
        self.summary_title = ["Summary",(0,'--'),(0,'--'),(0,'--'),
                              (0,'--'),(0,'--'),(0,'--')]
        self.summary = [["Minimum Age",100,100,100,None,None,None], 
                        ["Maximum Age",0,0,0,None,None,None],
                        ["Median Age",0,0,0,None,None,None],
                        ["Average Age",0,0,0,None,None,None], 
                        ["Number of Students",0,0,0,None,None,None]]

    def _get_age_distribution(self):
        query = SchoolDB.models.Student.all()
        SchoolDB.models.active_student_filter(query)
        if (self.section):
            query.filter("section = ", self.section)
        elif (self.class_year):
            query.filter("organization = ", 
                         SchoolDB.models.getActiveDatabaseUser().get_active_organization())
            query.filter("class_year =", self.class_year)
        else:
            self.error ="No class year or section requested for report"
            return
        for student in query:
            self.summary[4][3] += 1
            student_age = student.age(self.reference_date, self.age_calc_type)
            bucket = None
            if (student_age < self.min_age):
                if (not self.restrict_years):
                    bucket = self.age_counts[0]
            elif (student_age > self.max_age):
                if (not self.restrict_years):
                    bucket = self.age_counts[len(self.age_counts)-1]
            else:
                for bucket in self.age_counts[1:len(self.age_counts)-1]:
                    if (student_age <= bucket[0]):
                        break
            if (bucket):
                if (student.gender == "Male"):
                    bucket[1] += 1
                    self.summary[4][1] += 1
                    self.summary[3][1] += student_age
                    if (self.summary[0][1] > student_age) and (student_age != 0):
                        self.summary[0][1] = student_age
                    if (self.summary[1][1] < student_age):
                        self.summary[1][1] = student_age
                if (student.gender == "Female"):
                    bucket[2] += 1
                    self.summary[4][2] += 1
                    self.summary[3][2] += student_age
                    if ((self.summary[0][2] > student_age) and 
                        (student_age != 0)):
                        self.summary[0][2] = student_age
                    if (self.summary[1][2] < student_age):
                        self.summary[1][2] = student_age
                bucket[3] += 1
                self.summary[3][3] += student_age
                if ((self.summary[0][3] > student_age) and 
                    (student_age != 0)):
                    self.summary[0][3] = student_age
                if (self.summary[1][3] < student_age):
                    self.summary[1][3] = student_age
        for bucket in self.age_counts:
            for i in range(1,4):
                if (self.summary[4][i]):
                    bucket[i+3] = round(100.0*bucket[i] / 
                                        self.summary[4][i] , 1)
                else:
                    bucket[i+3] = 0.0
        self.summary[4][3] = self.summary[4][2] + self.summary[4][1]
        for i in range(1,4):
            if (self.summary[4][i] != 0):
                #truncate to one decimal point
                self.summary[3][i] = \
                    round(self.summary[3][i] / self.summary[4][i], 1)
        return (self.age_counts, self.summary[4][3])

    def _calculate_median(self):
        for i in range(1,4):
            count = 0
            for bucket in self.age_counts[1:len(self.age_counts)-2]:
                count += bucket[i]
                if (count >= (self.summary[4][i] / 2)):
                    self.summary[2][i] = bucket[0]
                    break

    def _trim_list(self, trim_list):
        remove_list = []
        for bucket in trim_list:
            if (bucket[3] == 0):
                remove_list.append(bucket)
            else:
                break
        for bucket in remove_list:
            trim_list.remove(bucket)

    def _trim_years(self):
        """
        If there are ages at the front or end of the array with no
        values in them then trim the array at that end so that it
        starts and ends with a useful value
        """
        #trim front
        self._trim_list(self.age_counts)
        #trim back
        self.age_counts.reverse()
        self._trim_list(self.age_counts)
        self.age_counts.reverse()      

    @staticmethod
    def create_report_table(parameter_dict , primary_object,
                                        secondary_class, secondary_object):
        """ 
        Create the data table, header, and key_list necessary to
        create a report. If there is a primary object it should be a
        section. That means that the report should be done only for
        that section. If not, then a class year should be specified. If
        neither or if either is incorrect, return an error.
        The report contains 3 columns - the age, the count, and the percent
        """
        report_generator = StudentAgeReport(parameter_dict, primary_object)
        report_generator._get_age_distribution()
        report_generator._calculate_median()
        if (report_generator.trim_years):
            report_generator._trim_years()
        #create an empty list for keys (they are not used with this report)
        distribution_keys = ["" for a in report_generator.age_counts]
        distribution_table_description = [('age','string','Age'),
                        ('males', 'number', '# Males'),
                        ('females', 'number', '# Females'),
                        ('total', 'number', '# Total'),
                        ('percent_male', 'number', '% Males'),
                        ('percent_female', 'number', '% Females'),
                        ('percent', 'number', '% Total')]
        if (report_generator.summary[4][3]):
            distribution_table = report_generator.age_counts
            distribution_table.append(report_generator.summary_title)
            distribution_table.extend(report_generator.summary)
            distribution_keys.extend(["","","","","",""])
        else:
            distribution_table = [["No Students",(0,'--'),(0,'--'),(0,'--'),
                              (0,'--'),(0,'--'),(0,'--')]]
        return (distribution_table_description, distribution_table, 
                distribution_keys, report_generator.error)

#----------------------------------------------------------------------

class SchoolRegisterReport():
    """
    A simple report with many fields of information about students of
    a single gender in a single section. While it could almost be generated
    by a standard table select query the class is used for the fields of 
    parent, age and to fix the official column headers.
    """

    def __init__(self, params, section):
        self.section = section
        self.gender = params.get("gender","Male")
        self.class_year = params.get("class_year", None)
        query = SchoolDB.models.Student.all()
        SchoolDB.models.active_student_filter(query)  
        if (self.class_year):
            query.filter('class_year = ', self.class_year)
        if (self.section):
            query.filter('section = ', self.section)
        query.filter('gender = ', self.gender)
        query.order('last_name')
        query.order('first_name')
        self.query = query
    
    def get_single_student_info(self, student):
        """
        Get a list of all required values for a single student
        """
        parents_list = student.get_parents()
        if (len(parents_list) > 0):
            first_parent = parents_list[0]
            parent_name = first_parent.full_name()
        else:
            parent_name = ""
        if (student.birthdate):
            birthdate = student.birthdate.strftime("%m/%d/%Y")
        else:
            birthdate = ""
        if (student.community):
            community = unicode(student.community)
        else:
            community = ""
        if (student.municipality):
            municipality = unicode(student.municipality)
        else:
            municipality = ""
        if (student.province):
            province = unicode(student.province)
        else:
            province = ""
        age_june = student.age(date.today(), "schoolyear")
        age_mar = student.age(date.today(), "endyear")
        student_info = [student.last_name, student.first_name, 
                        student.middle_name, parent_name, 
                        student.address, community,
                        municipality, province,
                        age_june, age_mar, birthdate]
        return student_info

    def build_table(self):
        table_description = [('lastname', 'string', 'Student Last Name'),
                     ('firstname', 'string', 'Student First Name'),
                     ('middlename', 'string', 'Student Middle Name'),
                     ('parentname', 'string', 'Guardian Name'),
                     ('address', 'string', 'Address'),
                     ('barangay', 'string', 'Barangay'),
                     ('municipality', 'string', 'Municipality'),
                     ('province', 'string', 'Province'),
                     ('agejune', 'string', 'Age June'),
                     ('agemarch', 'string', 'Age March'),
                     ('birthday', 'string', 'Date of Birth'),
                     ('remarks', 'string', 'Remarks')]
        table_contents = []
        keys = []
        records_list = []
        for student in self.query:
            table_contents.append(self.get_single_student_info(student))
            keys.append(str(student.key))
        #(sorted_table,sorted_keys) = \
         #SchoolDB.models.sort_table_contents_and_key(
             #table_contents, keys, [(1,False),(0,False)])
        return (table_description, table_contents, keys, "")

    @staticmethod
    def create_report_table(parameter_dict, primary_object,
                                        secondary_class, secondary_object):
        generator = SchoolRegisterReport(parameter_dict, primary_object)
        return (generator.build_table())
    
class SectionListReport:
    """
    Create a simple report for a single section of the students names in
    two columns, the left for males and the right for females
    """
    def __init__(self, params, section):
        self.section = section
        self.students = {"Male":[],"Female":[]}
        self.count =  {"Male":0,"Female":0}
        
    def build_gender_list(self, gender):
        """
        Create a list of the students names for a single gender for
        the specified section
        """
        query = SchoolDB.models.Student.all()
        SchoolDB.models.active_student_filter(query)
        query.filter('section = ', self.section)
        query.filter('gender = ', gender)
        query.order('last_name')
        query.order('first_name')
        for student  in query:
            record = [student.last_name, student.first_name, 
                      student.middle_name]
            self.students[gender].append(record)        
        self.count[gender] = len(self.students[gender])
            
    def fill_list(self, fill_list, length):
        """
        Append empty strings to the end of a list to extend it to
        the specified length. Nothing will be done if the list is the
        same size or longer.
        """
        while (len(fill_list) < length):
            fill_list.append(("","",""))
            
    def build_table(self):
        self.build_gender_list("Male")
        self.build_gender_list("Female")
        self.fill_list(self.students["Male"], self.count["Female"])
        self.fill_list(self.students["Female"], self.count["Male"])
        table_description = [('m_index', 'string', '#'),
                             ('lnmale', 'string', 'MALES: Family'), 
                             ('fnmale', 'string', 'First'),
                             ('mnmale', 'string', 'Middle'),
                             ('fill', 'string', '        '),
                             ('f_index', 'string', '#'),
                             ('lnfemale','string','FEMALES: Family'),
                             ('fnfemale', 'string', 'First'),
                             ('mnfemale', 'string', 'Middle')]
        table_contents = []
        keys = []
        for i in xrange(0, len(self.students["Male"])):
            male = self.students['Male'][i]
            female = self.students['Female'][i]
            male_number = str(i + 1)
            female_number = str(i + 1)
            if (not male[0]):
                male_number = ""
            if (not female[0]):
                female_number = ""
            row = [male_number, male[0],male[1],male[2],"",
                   female_number,female[0],female[1],female[2]]
            table_contents.append(row)
            keys.append("")
        row1 = ["","","","","","",""]
        row2 = ["","# Males:",str(self.count["Male"]),"","","","",""]
        row3 = ["","# Females:",str(self.count["Female"]),"","","","",""]
        row4 = ["","Total:",
               str(self.count["Male"] + self.count["Female"]),"","","","",""]
        table_contents.extend([row1,row2,row3,row4])
        keys.extend(["","","",""])
        return(table_description, table_contents, keys, "")
    
    @staticmethod
    def create_report_table(parameter_dict, primary_object,
                                        secondary_class, secondary_object):
        generator = SectionListReport(parameter_dict, primary_object)
        return (generator.build_table())

#----------------------------------------------------------------------
class StudentRecordCheck:
    """
    A report of necessary fields in a student record that are missing
    or records that are obviously outdated, probably because the
    student has not registered for the current year. Only students with
    errors are shown in the report. This is done by section.
    """
    
    def __init__(self, parameter_table, section):
        self.section = section
        self.table_description = []
        self.table_contents=[]
        self.keys = []
        self.parameter_table_table = parameter_table
        self.report_type = parameter_table.get("report_type", "Missing Fields")
        query = SchoolDB.models.Student.all()
        query.filter("organization = " , 
                SchoolDB.models.getActiveDatabaseUser().get_active_organization())
        if (self.report_type == "No Current Enrollment"):
            #this uses inequality filter so sort must be on same field
            #just skip sort and let the table do it
            active_status_key = \
                        SchoolDB.models.get_active_student_status_key()
            query.filter("student_status = ", active_status_key)
            SchoolDB.models.filter_by_date(query, "before",
                                        "student_status_change_date", 0)
            self.query = query
            return
        elif (self.report_type == "No Section"):
            query.filter('section = ', None)
        else:
            #report type is missing records
            query.filter('section = ', self.section)
        SchoolDB.models.active_student_filter(query)
        query.order('last_name')
        query.order('first_name')
        self.query = query
            
    def build_no_current_enrollment_table(self):
        """
        A simple three column table with last and first name and the
        time of the last status change. This is used to list the
        students who have not reenrolled in the past year and have no
        other status to indicate that they are no longer students.
        """
        self.table_description = [('last_name','string','Last Name'),
                    ('first_name','string','First Name'),
                    ('last_date', 'string','Last Change Date')]
        table_contents = []
        keys = []
        student_status_not_enrolled_key = \
                SchoolDB.models.get_student_status_key_for_name(
                "Not Currently Enrolled")
        for student in self.query:
            keys.append(str(SchoolDB.models.get_key_from_instance(
                student)))
            table_contents.append([student.last_name, 
                                   student.first_name,
                student.student_status_change_date.strftime(
                    "%m/%d/%Y")])
            student.student_status = student_status_not_enrolled_key
            student.put()
        if (len(table_contents)):
            (self.table_contents, self.keys) = \
             SchoolDB.models.sort_table_contents_and_key(
                 table_contents, keys, [(1,False),(0,False)])
        return(self.table_description, self.table_contents, 
               self.keys, "")
        
    def build_no_section_table(self):
        self.table_description = [('last_name','string','Last Name'),
                            ('first_name','string','First Name'),
                            ('class_year','string','Class Year')]
        for student in self.query:
            self.keys.append(str(SchoolDB.models.get_key_from_instance(
                student)))
            self.table_contents.append([student.last_name, 
                                   student.first_name, student.class_year])
        return(self.table_description, self.table_contents, self.keys, "")
        
    def build_missing_info_table(self):   
        self.table_description = [("namel", "string", "Family Name"),
                        ("namef", "string", "First Name"),
                        ("mun", "boolean", "Municipality"),
                        ("bg", "boolean", "Barangay"),
                        ("bd", "boolean", "Birthdate"),
                        ("ed", "boolean", "Enrollment Date"),
                        ("cy", "boolean", "Class Year Date"),
                        ("sd", "boolean", "Section Date"),
                        ("bp", "boolean", "Birth Province"),
                        ("bm", "boolean", "Birth Municipality"),
                        ("bb", "boolean",  "Birth Barangay"),
                        ("es", "boolean", "Elementary School"),
                        ("eg", "boolean", "Elementary Grad Year"),
                        ("ega", "boolean", "Elementary General Avg"),
                        ("ye", "boolean", "Years in Elementary"),
                        ("pg", "boolean", "Parent")]
        for student in self.query:
            missing_fields, missing_count = \
                student.get_missing_fields()
            if (missing_count):
                self.keys.append(str(
                    SchoolDB.models.get_key_from_instance(
                        student)))
                table_entry = [student.last_name, student.first_name]
                for i in ("mun","bg","bd","ed","cy","sd","bp","bm","bb",
                  "es","eg","ega","ye","pg"):
                    table_entry.append(missing_fields[i])           
                self.table_contents.append(table_entry)
        return(self.table_description, self.table_contents, 
               self.keys, "")
    
    @staticmethod
    def create_report_table(parameter_dict, primary_object,
                                        secondary_class, secondary_object):
        generator = StudentRecordCheck(parameter_dict, primary_object)
        report_type = parameter_dict.get("report_type", "Missing Fields")
        if (report_type == "No Current Enrollment"):
            return generator.build_no_current_enrollment_table()
        elif (report_type ==  "No Section"):
            return generator.build_no_section_table()
        else:
            return generator.build_missing_info_table()

#----------------------------------------------------------------------
class Form14Report():
    """
    A top level class the full html page for a form 14. It combines
    html header elements and a table that contains bot extracted and
    computed values. It is a child class of AjaxGetGrade Handler which
    does all of the data extraction.
    """
    
    def __init__(self, parameter_dict, section, achievement_test):
        self.table_header = None
        self.raw_table_data = None
        self.summary_data = None
        self.parameter_dict = parameter_dict
        self.achievement_test = achievement_test
        self.section = section
        self.grading_instances = \
            self.get_achievement_test_grading_instances()
        self.data_columns_count = len(self.grading_instances) + 1
        json_data = self.generate_json_data()
        self.grade_processor = \
            SchoolDB.assistant_classes.AjaxGetGradeHandler(
                section, json_data)
         
    def get_data(self):
        (unused, unused1, self.raw_table_data) = \
            self.grade_processor.create_raw_information()
        self.student_count = len(self.raw_table_data)
        self.number_questions = \
            [self.grading_instances[i].number_questions for i in 
             range(self.data_columns_count - 1)]
        total_questions = sum(self.number_questions)
        self.number_questions.append(total_questions)
        for row in self.raw_table_data:
            total_cnt = sum(row[1:len(row)])
            row.append(total_cnt)
        
    def compute_summary_values(self):
        """
        perform calculations for all summary values at the bottom of the form
        """
        total_raw_scores = [0 for i in range(self.data_columns_count)]
        self.total_cases = [0 for i in range(self.data_columns_count)]
        self.passing_count = [0 for i in range(self.data_columns_count)]
        self.passing_grade = [round(self.number_questions[i] * 0.75) for 
                              i in range(self.data_columns_count)]
        for j in range(self.data_columns_count):
            for i in range(self.student_count):
                total_raw_scores[j] += self.raw_table_data[i][j+1]
                if (self.raw_table_data[i][j+1] > self.passing_grade[j]) :
                    self.passing_count[j] += 1
                if (self.raw_table_data[i][j+1] != 0):
                    self.total_cases[j] += 1
        self.mean_raw_scores = []
        for i in range(self.data_columns_count):
            if (self.total_cases[i]):
                score = round((total_raw_scores[i] / 
                    self.total_cases[i]), 2)
            else:
                score = 0
            self.mean_raw_scores.append(score)
        self.mean_percentage_scores = [round((self.mean_raw_scores[i] / 
            self.number_questions[i]), 2) for i in 
                                  range(self.data_columns_count)]
        self.percent_passing_grade = []
        for i in range(self.data_columns_count):
            if (self.total_cases[i]):
                score = round((float(self.passing_count[i]) / 
                       float(self.total_cases[i])), 2) 
            else:
                score = 0.0
            self.percent_passing_grade.append(score)
        
    def create_table_description(self):
        """
        Create a list of header parameters to be used by the google
        table widget. In addition, create a list of grading instances
        that can be used to get furnter information from the grading
        instances associated with the column.
        """
        table_description = [("name","string","Student Name")]
        index = 0
        for instance in self.grading_instances:
            table_description.append((str(index), "number", 
                     unicode(instance.subject)))
            index += 1
        table_description.append(("total","number","Total"))
        return table_description
    
    def build_report_table(self):
        """
        Build the table to be used in the report. This is an extension of the
        raw data array with the computed values.
        """
        summary_line = ["SUMMARY"] + \
                     [None for i in range(self.data_columns_count)]
        tc_line = ["Total # Cases"] + self.total_cases
        mrs_line = ["Mean Raw Score"] + self.mean_raw_scores
        mps_line = ["Mean Percentage Score"] + self.mean_percentage_scores
        stucnt_line = ["Num Stu Getting 75%"] + self.passing_count
        stpcnt_line = ["% Stu Getting 75%"] + self.percent_passing_grade
        summary_block = [line for line in (summary_line, tc_line,
                                mrs_line, mps_line,stucnt_line,stpcnt_line)]
        full_table_data = self.raw_table_data + summary_block
        table_description = self.create_table_description()
        return table_description, full_table_data
        
    def get_achievement_test_grading_instances(self):
        """
        Return a list of keys of all of the grading instances in the
        achievement test. This is a copy of the code in the ajax class.It
        is used to generate the data in the form used by the
        AjaxGetGradeHandler
        """
        query = SchoolDB.models.GradingInstance.all()
        query.ancestor(self.achievement_test)
        return(query.fetch(20))
    
    def generate_json_data(self):
        instances = [str(instance.key()) for instance in 
                     self.grading_instances]
        json_instances = simplejson.dumps(instances)
        return_data = {"gi_keys":json_instances, 
                       "requested_action":"None",
                       "achievement_test":True}
        return (simplejson.dumps(return_data))
    
    def build_table(self):
        """
        Create the table and header for the report.
        """
        self.get_data()
        self.compute_summary_values()
        table_description, data_table = self.build_report_table()
        keys = [data_table[i][0] for i in range(len(data_table))]
        return table_description, data_table, keys, ""
        
    @staticmethod
    def create_report_table(parameter_dict, primary_object,
                                        secondary_class, secondary_object):
        generator = Form14Report(parameter_dict, primary_object,
                                 secondary_object)
        return (generator.build_table())

#----------------------------------------------------------------------

class SummaryReportBase():
    """
    A base class used to create upper level summary reports. Each child
    class need only define the functions to populate table values
    """
    def __init__(self, parameter_dict, primary_object,
                        secondary_class, secondary_object):
        """
        From the current users organization determine all schools that
        are subordinate to that organization. Build a dictionary keyed
        by the school that contains the current student summary object
        expanded from the blob value stored in the student summary
        instance. The report type is a dictionary with entries that
        define the format of the report.
        """
        self.parameter_dict = parameter_dict
        self.primary_object = primary_object
        self.secondary_class = secondary_object
        self.secondary_object = secondary_object
        self.show_genders = simplejson.loads(parameter_dict.get(
            "show_genders", "false"))
        self.by_class_year = simplejson.loads(parameter_dict.get(
            "by_class_year", "true"))
        self.single_row = simplejson.loads(parameter_dict.get(
            "single_line_per_school", "false"))
        self.requesting_org = SchoolDB.models.getActiveDatabaseUser().get_active_organization()
        self.is_region = (self.requesting_org.classname == "DepEd Region")
        self.is_school = (self.requesting_org.classname == "School")
        if (self.is_school):
            self.schools_list = [self.requesting_org]
        elif self.parameter_dict.has_key("orgs_to_show"):
            school_text_key_list = simplejson.loads(
                self.parameter_dict["orgs_to_show"])
            self.schools_list = [
                SchoolDB.models.get_instance_from_key_string(key_string,
                                SchoolDB.models.School) 
                for key_string in school_text_key_list]
        else:
            #self._get_schools_list()
            self.schools_list = []
        self.values_to_show = []
        if self.parameter_dict.has_key("values_to_show"):
            self.values_to_show = \
                    simplejson.loads(parameter_dict["values_to_show"])
        self.show_division_names = self.is_region
        if (not self.is_school or self.single_row):        
            self.by_class_year = True
                        

    #def _get_schools_list(self):
        #"""
        #Create a "tree" of subordinate orgainzations for schools. If the
        #user is from a deped region then it is a sorted list of divisions
        #each of which has a sorted list of schools. If division, the is
        #just the sorted list of schools in the division. Of course if the
        #user is in a school only that school is reported. The end result is
        #a sorted list that has the tuples (division,school) and boolean
        #"multiple divisions"
        #"""
        #schools_list = []
        #if (top_level_org.classname == "School"):
            #add_school_to_report_list(top_level_org, schools_list)
        #if (top_level_org.classname == "DepEd Division"):
            #add_division_to_report_list(top_level_org, schools_list)
        #if (top_level_org.classname == "DepEd Region"):
            #divisions = top_level_org.get_subordinate_organizations(
                #next_level_only=True)
            #for division in divisions:
                #add_division_to_report_list(division, schools_list)
        #return schools_list
        
    @staticmethod
    def get_report_field_choices():
        return ["# Stu",
            "Balik Aral", 
            "Trans In",
            "Trans Out",
            "Dropped Out",
            "Min Age",
            "Max Age",
            "Avg Age",
            "Median Age"]

    def _get_single_section_summary(self, section_summary, 
                                    add_section_name = False):
        section_data = section_summary.get_data()
        leader_name = ""
        if add_section_name:
            leader_name = section_summary.get_section_name()
        return self._create_summary_block(section_data, leader_name)
    
    def _create_summary_block(self, summary_data, leader_name=""):
        """
        Create an array of values for display in a summary table. This
        returns only the values to insert into the table line, not the
        completely defined table line.
        """
        summary_values = []
        if leader_name:
            summary_values.append(leader_name)
        values_dict = {}
        if self.show_genders:
            #report order
            cols = [2,0,1]
        else:
            cols = [2]
        values_list = []
        for col in cols:
            self._fill_values_dict(values_dict, col, summary_data)
            for value_name in self.values_to_show:
                values_list.append(values_dict[value_name])
        summary_values.extend(values_list)
        return summary_values
    
        
    def _fill_values_dict(self, values_dict, col, section_data):
        """
        Create a dictionary of numeric values keyed by the dsicriptive
        name used in the report header.
        """
        values_dict["# Stu"] = section_data.num_students[col]
        values_dict["Balik Aral"] = section_data.balik_aral[col]
        values_dict["Trans In"] = section_data.transferred_in[col]
        values_dict["Trans Out"] = section_data.transferred_out[col]
        values_dict["Dropped Out"] = section_data.dropped_out[col]
        values_dict["Min Age"] = section_data.min_age[col]
        values_dict["Max Age"] = section_data.max_age[col]
        values_dict["Avg Age"] = section_data.average_age[col]
        values_dict["Median Age"] = section_data.median_age[col]
        
    def _get_information_for_school(self, school):
        """
        Create the table array entry for a single school. If row type
        "single" create on row with all values (for spreadsheet). If
        row type "classyear" create an entry with each year on a different
        row. If row type "section" create a row for each section.
        """
        table_entry = []
        #try:
        info_summary_db_instance = school.student_summary
        info_summary = info_summary_db_instance.get_current_summary()
        section_summaries_list = info_summary.get_section_summaries_list()
        row_leader = []
        if self.is_region:
            row_leader.append(unicode(school.division))
        if (not self.is_school):
            row_leader.append(unicode(school))
        if self.single_row:
            table_row = row_leader           
        class_year_summary_values = []
        for class_year in SchoolDB.choices.ClassYearNames[0:4]:
            class_year_summary_values = []
            if self.by_class_year:
                class_year_summary_values.append(
                    self._create_summary_block(
                    info_summary.get_class_year_summary(class_year,
                                            section_summaries_list)))
            else:
                by_section = True
                for sect in \
                    info_summary.get_sections_by_class_year(class_year,
                                        section_summaries_list, True):
                    class_year_summary_values.append( \
                        self._get_single_section_summary(sect, True))
            if self.single_row:
                #continue to add the years to the single row
                table_row.extend(class_year_summary_values[0])
            else:
                for row_info in class_year_summary_values:
                    table_row = \
                              [row_leader[i] for i in range(len(row_leader))]
                    table_row.append(class_year)
                    table_row.extend(row_info)
                    table_entry.append(table_row)
        if self.single_row:
            table_entry = [table_row]
        #except 
        return table_entry
        
    def _get_table_data(self):
        """
        Build the entire array of all report data values
        """
        table_data = []
        for i in range(len(self.schools_list)):
            school = self.schools_list[i]
            table_data.extend(self._get_information_for_school(school))
        return table_data
            
    def _get_table_description(self):
        """
        Create table headers and the header description depending upon
        options or organizational level. Prepend division name adn
        school name if necessary to identify entries. Expand the table
        line for single line reports and gender based reports.
        """
        table_header_text = []
        values_block = self.values_to_show
        if self.show_division_names:
            table_header_text.append("Division")
        if (len(self.schools_list) > 1):
            table_header_text.append("School")
        if (not self.single_row):
            table_header_text.append("Class Year")
        if (not self.by_class_year):
            table_header_text.append("Section")
        if (self.show_genders):
            combined = [ "C "+name for name in values_block]
            male = [ "M "+name for name in values_block]
            female = [ "F "+name for name in values_block]
            values_block = combined
            values_block.extend(male)
            values_block.extend(female)
        if (self.single_row):
            all_years_block = []
            for year in (1, 2, 3, 4):
                years_block = []
                years_block.extend([ "Yr %d %s" %(year,name) 
                                     for name in values_block])
                all_years_block.extend(years_block)
            values_block = all_years_block
        table_header_text.extend(values_block)
        table_desc = []
        for column_text in table_header_text:
            var_name = column_text.lower().replace(" ", "_")
            table_col_desc = (var_name, "string", column_text)
            table_desc.append(table_col_desc)
        return table_desc
     
    def build_table(self):
        """
        Call the functions to generate the table in appropriate order
        to generete the satandard table build return values
        """
        table_data = self._get_table_data()
        table_desc = self._get_table_description()
        keys = [" " for i in range(len(table_data))]
        return (table_desc, table_data, keys, '')
    
    @staticmethod
    def create_report_table(parameter_dict, primary_object,
                                secondary_class, secondary_object):
        """
        Create a report table for display of summary information about
        one or more schools. The args dict should include the top level
        object's key string (no higher that the users org), flags for ,
        and an ordered list of parameters that will be displayed. There
        should also be flags for single line report for each school,
        class year aggregation, and display of only the combined values
        or values for each gender. Ffnally, the args_dict should
        include a list of schools to be shown unless the user is in a
        school so that only sections will be shown
        """
        generator = StudentSummaryReport(parameter_dict, primary_object,
                                secondary_class, secondary_object)
        return generator.build_table()

#----------------------------------------------------------------------
    
class AchievementTestReport:
    """
    This class builds acheivement test reports from information from
    the achievement test summaries. It designed suppurt upper level
    group reports sith information from multiple schools.
    """
    
    def __init__(self, parameter_dict, primary_object, 
                            secondary_class, secondary_object):
        """
        Initialize the object with values from a dictionary of parameter
        values. 
        """
        SummaryReportBase.__init__(self,
                primary_object, secondary_class, 
                secondary_object)
        self.achievement_test = primary_object
    
    def build_table(self):
        pass
    
    @staticmethod
    def create_report_table(parameter_dict, primary_object,
                                secondary_class, secondary_object):
        """
        Create a summary report of achivement test grades for upper
        level users.
        """
        generator = AchievementTestReport(parameter_dict, 
                                          primary_object, 
                                          secondary_class, 
                                          secondary_object)
        return generator.build_table()
        
#----------------------------------------------------------------------
class StudentSummaryReport(SummaryReportBase):
    """
    This class builds acheivement test reports from information from
    the achievement test summaries. It designed suppurt upper level
    group reports sith information from multiple schools.
    """
    
    def __init__(self, parameter_dict, primary_object, 
                            secondary_class, secondary_object):
        """
        Initialize the object with values from a dictionary of parameter
        values. 
        """
        SummaryReportBase.__init__(self, parameter_dict,
                primary_object, secondary_class, 
                secondary_object)
        self.achievement_test = primary_object
    
    @staticmethod
    def get_report_field_choices():
        return ["# Stu",
            "Balik Aral", 
            "Trans In",
            "Trans Out",
            "Dropped Out",
            "Min Age",
            "Max Age",
            "Avg Age",
            "Median Age"]

    def _fill_values_dict(self, values_dict, col, section_data):
        """
        Create a dictionary of numeric values keyed by the descriptive
        name used in the report header.
        """
        values_dict["# Stu"] = section_data.num_students[col]
        values_dict["Balik Aral"] = section_data.balik_aral[col]
        values_dict["Trans In"] = section_data.transferred_in[col]
        values_dict["Trans Out"] = section_data.transferred_out[col]
        values_dict["Dropped Out"] = section_data.dropped_out[col]
        values_dict["Min Age"] = section_data.min_age[col]
        values_dict["Max Age"] = section_data.max_age[col]
        values_dict["Avg Age"] = section_data.average_age[col]
        values_dict["Median Age"] = section_data.median_age[col]
    
    @staticmethod
    def create_report_table(parameter_dict, primary_object,
                                secondary_class, secondary_object):
        """
        Create a summary report of achivement test grades for upper
        level users.
        """
        generator = StudentSummaryReport(parameter_dict, 
                                          primary_object, 
                                          secondary_class, 
                                          secondary_object)
        return generator.build_table()
        

def get_upper_level_report_common_params(parameter_dict):
    """
    Process the summary report request for parameters common to all
    """
    requested_org = \
        SchoolDB.models.get_instance_from_key_string(
            parameter_dict.get("top_level_org", None))
    if (not requested_org):
        requested_org = \
            SchoolDB.models.getActiveDatabaseUser().get_active_organization()
    if (not requested_org.visible_organization()):
        #if the requested org cannot be viewed just use the users org
        requested_org = \
            SchoolDB.models.getActiveDatabaseUser().get_active_organization()
    schools_list, show_division_names = \
            get_schools_list(requested_org)
    values_to_show = []
    if parameter_dict.has_key("values_to_show"):
        values_to_show = \
                simplejson.loads(parameter_dict["values_to_show"])
    return requested_org, schools_list, \
           values_to_show, show_division_names
     
def add_school_to_report_list(school, report_org_list, 
                              division_name = ""):
    if not division_name:
        hierarchy = \
            SchoolDB.models.MultiLevelDefined.create_org_choice_list(school)
        division_name = hierarchy[1][1]
    report_org_list.append((division_name, school))
        
def add_division_to_report_list(division, report_org_list):
    division_name = unicode(division)
    schools = division.get_subordinate_organizations()
    schools_dict = {}
    for school in schools:
        schools_dict[unicode(school)] = school
    names_list = schools_dict.keys()
    names_list.sort()
    for school_name in names_list:
        add_school_to_report_list(schools_dict[school_name], report_org_list, 
        division_name)

def get_schools_list(top_level_org):
    """
    Create a "tree" of subordinate organizations for schools. If the
    user is from a deped region then it is a sorted list of divisions
    each of which has a sorted list of schools. If division, the is
    just the sorted list of schools in the division. Of course if the
    user is in a school only that school is reported. The end result is
    a sorted list that has the tuples (division,school) and boolean
    "multiple divisions"
    """
    multiple_divisions = False
    schools_list = []
    if (top_level_org.classname == "School"):
        add_school_to_report_list(top_level_org, schools_list)
    if (top_level_org.classname == "DepEd Division"):
        add_division_to_report_list(top_level_org, schools_list)
    if (top_level_org.classname == "DepEd Region"):
        multiple_divisions = True
        divisions = top_level_org.get_subordinate_organizations(
            next_level_only=True)
        for division in divisions:
            add_division_to_report_list(division, schools_list)
    return schools_list, multiple_divisions

