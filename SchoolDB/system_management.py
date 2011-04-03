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
This file contains classes that perform major system actions.
"""
from datetime import date, timedelta
import exceptions
import logging 
from django.utils import simplejson
from google.appengine.ext import db
import SchoolDB.models 
import SchoolDB.assistant_classes
import SchoolDB.utility_functions

class BulkClassSessionsCreator:
    """
    This class is created by an ajax request. It is used to create
    multiple class sessions for the current school year for one or more
    subjects and class_years. The class sessions are those which are
    taught by section. Class sessions are created by default for all
    sections in the class year. The creation is a two step process.
    First the administrative user defines the subjects and class years
    for the class sessions. This is sent via an Ajax request to create
    an instance of this class and use it to perform the initial
    analysis and then return via an Ajax response a table of proposed
    class sessions and some further information. Second, after the user
    reviews and perhaps edits the table it is returned again via Ajax
    to create another instance of this object which initiates the tasks
    to perform the creation of the class sessions and s student record
    of the class for each student in it. For a large school and many
    classes this might create 10000 or more database entities.
    """
    def __init__(self, start_date, end_date, 
                 process_step, process_data): 
        self.school = SchoolDB.models.getActiveDatabaseUser().get_active_organization()
        self.school_year = \
            SchoolDB.models.SchoolYear.school_year_for_date(date.today())
        self.start_date = start_date
        self.end_date = end_date
        self.process_step = process_step 
        self.process_data = process_data
        self.sections_dict = {}
        self.sessions_request_array = []
        self.conflict_array = []
        self.initial_request_array = []
        self.num_class_sessions = 0
        self.num_student_records = 0
        
    #------Step One functions-------
    def _process_initial_request(self):
        """
        The initial request is a json list of requested classes by
        subject and class year. Expand this into a 2D array with a row
        for each individual class session requested (i.e., expand
        requested class across sections). Compare with existing classes
        and remove matches. Finally, create a table of classes to be_
        created, another of classes that already exist so will not
        be created, and a dictionary of other statistics.
        """
        sessions_request_array = self._create_requested_array()
        self._filter_conflicts(sessions_request_array)
        request_table, conflicts_table = self._create_tables()
        other_info = self._create_other_info()
        response_dict={"request_table":request_table, 
                       "conflicts_table":conflicts_table,
                       "other_info":other_info}
        #>>>>>>>>>>>>for now,short circuit the return
        self._patch_steps()
        return request_table, conflicts_table, other_info
        
    def _create_requested_array(self):
        """
        A step one action to expand the initial request to an array of
        requested class sessions. The initial request is a 2d array.
        Each row has 1.index for class year 2.keystring for the subject
        3.class session name suffix. Expand each entry to all sections
        for the class year and return an array with the section name
        and key, the subject name and key, the classroom name and key,
        and the expanded class name.
        """
        self.initial_request_array = simplejson.loads(self.process_data)
        classroom_sections = [[],[],[],[]]
        sessions_request_array = []
        index=0
        for class_year_name in SchoolDB.models.get_class_years_only():
            query = SchoolDB.models.Section.all()
            query.filter("class_year = ", class_year_name)
            query.filter("organization = ", \
                SchoolDB.models.getActiveDatabaseUser().get_active_organization())
            classroom_sections[index] = query.fetch(100)
            index += 1
        for initial_row in self.initial_request_array:          
            section_list = classroom_sections[initial_row[0]]
            subject = SchoolDB.models.get_instance_from_key_string(
                initial_row[1])
            subject_name = unicode(subject)
            subject_keystr = str(subject.key())
            class_session_name = "%s-%s" %(unicode(subject), initial_row[2])
            for section in section_list:
                if (section.termination_date == None):
                    section_keystr = str(section.key())
                    if not self.sections_dict.has_key(section_keystr):
                        classroom = section.classroom
                        if (classroom != None):
                            classroom_keystr = str(classroom.key())
                            classroom_name = unicode(classroom)
                        else:
                            classroom_keystr = ""
                            classroom_name = ""
                        self.sections_dict[section_keystr] = \
                        {"section":section, "section_name":unicode(section),
                         "classroom_name":classroom_name,
                         "classroom_keystr":classroom_keystr}
                    session_row = \
                        [self.sections_dict[section_keystr]["section_name"],
                        section_keystr,subject_name, subject_keystr,
                        self.sections_dict[section_keystr]["classroom_name"], 
                        self.sections_dict[section_keystr]["classroom_keystr"],
                        class_session_name]
                    sessions_request_array.append(session_row)
        return sessions_request_array
                            
    def _filter_conflicts(self, sessions_request_array):
        """
        Search the classes for the school and school year for classes
        with subject and section that already exist. These are
        conflicts and should not be created again.
        """
        #get all class sessions already created for the school_year
        query = SchoolDB.models.ClassSession.all()
        query.filter("organization =", \
                SchoolDB.models.getActiveDatabaseUser().get_active_organization())
        query.filter("school_year =", self.school_year)
        current_class_sessions = query.fetch(1000)
        #use dictionary hashing to simplify matching
        filter_dict = {}
        for session in current_class_sessions:
            section_keystr = str(session.section.key())
            subject_keystr = str(session.subject.key())
            filter_dict[section_keystr+subject_keystr] = session
        for row in sessions_request_array:
            compare_key = row[1] + row[3]
            if filter_dict.has_key(compare_key):
                #the row in the conflict array only needs the names
                #to display
                c_row = [row[2],row[0]]
                self.conflict_array.append(c_row)
            else:
                self.sessions_request_array.append(row)
                
    def _create_tables(self):
        """
        Create complete tables from the sessions_request_array and the
        conflict array. These tables are returned in json format ready
        for upload.
        """
        request_table_description = [('section_name', 'string', 'Section'),
                            ('section_key', 'string', 'Section Key'),
                            ('subject_name', 'string', 'Subject'),
                            ('subject_key', 'string', 'Subject Key'),
                            ('classroom_name', 'string', 'Classroom'),
                            ('classroom_key', 'string', 'Classroom Key'),
                            ('sesssion_name', 'string', 'Class Name')]
        request_table = SchoolDB.utility_functions.make_table(
            request_table_description, self.sessions_request_array)
        conflict_table_description = [('subject_name','string','Subject'),
                                       ('section_name', 'string','Section')]
        conflict_table = SchoolDB.utility_functions.make_table(
            conflict_table_description, self.conflict_array)
        return request_table,conflict_table
    
    def _patch_steps(self):
        """
        A temporary connection to simplify coding for now.
        >>>>>>>>Remove this when possible<<<<<<
        """
        self._create_class_sessions()
        
    def _create_other_info(self):
        """
        Aggregate other information into a json dict.
        """
        num_class_sessions, num_student_records = \
                          self._estimate_numbers()
        other_info = {"school_year":str(self.school_year.key()),
                      "school_name":str(unicode(self.school)),
                      "start_date":self.start_date,
                      "end_date":self.end_date,
                      "num_class_sessions":num_class_sessions,
                      "num_class_records":num_student_records}
        return other_info
    
    def _estimate_numbers(self):
        """
        Compute the number of classes and class records to be created
        to report to the user at the end of step 1.
        """
        for keystr, section_info in self.sections_dict.iteritems():
            #get the number of student in the section
            query = SchoolDB.models.Student.all()
            query.filter("section =", section_info["section"])
            section_info["num_students"] = query.count(500)
        num_class_sessions = len(self.sessions_request_array)
        num_student_records = 0
        for row in self.sessions_request_array:
            num_student_records += \
                self.sections_dict[row[1]]["num_students"]
        return num_class_sessions, num_student_records
                    
    #------Step Two functions-------
    def _process_final_request(self):
        """
        The final request is a table of classes to be created with all
        parameters defined. This table is either the same or an edited
        version of the table returned by the initial request. Again
        test for and remove any conflicts with existing classes because
        the user may have edited the table in a way that has recreated
        some of these requests. Then create all of the classes and
        student class records with a cascading series of tasks. The
        total number of tasks created may be in the hundreds so this is
        a VERY heavyweight action -- probably the single most expensive
        task to be performed!
        """
        self.start_date = SchoolDB.utility_functions.convert_form_date(
            self.process_data["start_date"])
        self.end_date = SchoolDB.utility_functions.convert_form_date(
            self.process_data["start_date"])
        self._convert_input_table()
        if self._validate_parameters():
            self._build_create_array()
            self._create_class_sessions()
            
        pass    
    def _convert_input_table(self):
        """
        Convert the ajax return table into the same form as the
        sessions_request_array in Step 1.
        """
        pass
    
    def _validate_parameters(self):
        """
        Confirm that start_dates and end dates are within the school year.
        Confirm that all sections are in the school.
        Remove any conflicts.
        """
        pass
    
    def _build_create_array(self):
        pass

    def _create_class_sessions(self):
        """
        Create an individual task to create a class session for each
        row in the sessions_request_array. Each class session will
        manage its own student class records creation
        """
        school_year_keystring = str(self.school_year.key())
        #dt = SchoolDB.utility_functions.convert_form_date(self.start_date)
        start_date = self.start_date.toordinal()
        #dt = SchoolDB.utility_functions.convert_form_date(self.end_date)
        end_date = self.end_date.toordinal()
        if len(self.sessions_request_array):
            for row in self.sessions_request_array:
                task_name = "Create %s Section: %s" %(row[6], row[0])
                function = "SchoolDB.models.ClassSession.create_if_necessary"
                function_args = "name='%s', subject_keystring='%s', section_keystring='%s',start_date='%s', end_date='%s', school_year_keystring='%s', classroom_is_section_classroom = True" \
                %(row[6],row[3], row[1], start_date, end_date, 
                  school_year_keystring)            
                creation_task = SchoolDB.assistant_classes.TaskGenerator(
                    task_name=task_name, function=function, 
                    function_args=function_args, rerun_if_failed=False)
                creation_task.queue_tasks()
            return True
        else:
            logging.warning("Requested class session creation but there were no class sessions to be created")
        return False
            
    def process_request(self):
        """
        Choose process function based upon the step in the process
        """
        if (self.process_step == 1):
            return self._process_initial_request()
        elif (self.process_step == 2):
            return self._process_final_request()
        else:
            return None
    
    
    @staticmethod
    def manage_creation(school_year, argsDict):
        """
        Creating class sessions is a two step process. The initial
        request includes an array describing which classes are to be
        created. The response is a table with information about the
        classes to be created. The second request is the possibly
        edited table of classes that should be created. This is used to
        actually perform the creation. Each request contains a flag to
        indicate the step and the data contents.
        """
        process_step = argsDict["process_step"]
        process_data = argsDict["process_data"]
        start_date = argsDict["start_date"]
        end_date = argsDict["end_date"]
        creator = BulkClassSessionsCreator(school_year, start_date, 
                            end_date, process_step, process_data)
        return creator.process_request()
        
    