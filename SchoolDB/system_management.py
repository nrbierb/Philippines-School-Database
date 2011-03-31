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
import SchoolDB.assistant_classes

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
    def __init__(self, school, school_year, start_date, end_date, 
                 process_step, process_data): 
        self.school = school 
        self.school_year = school_year 
        self.process_step = process_step 
        self.process_data = process_data 
        self.sessions_request_array = []
        self.conflict_array = []
        self.initial_request_array = []
        self.start_date = start_date
        self.end_date = end_date
    #------Step One functions-------
    def _process_initial_request(self):
        """
        The initial request is a json list of requested classes by
        subject and class year. Expand this into a 2D array with a row
        for each individual class session requested (i.e., expand
        requested class across sections). Compare with existing classes
        and remove matches. Finally, create a table of classes to be
        created, another of classes that already exist so will not
        be created, and a dictionary of other statistics.
        """
        sessions_request_array = self.create_requested_array()
        self.filter_conflicts(sessions_request_array)
        create_table, conflicts_table = self.create_tables()
        statistics = self.create_statistics()
        response_dict={"create_table":create_table, 
                       "conflicts_table":conflicts_table,
                       "statistics":statistics}
        return response_dict
        
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
            query.filter("class_year=", class_year_name)
            query.filter("organization =", \
                SchoolDB.models.getActiveDatabaseUser().get_active_organization())
            query.filter("termination date = ", None)
            classroom_sections[index] = query.fetch(100)
        for initial_row in self.initial_request_array:
            section_list = classroom_sections[row[0]]
            subject = SchoolDB.models.get_instance_from_key_string(row[1])
            class_session_name = unicode(subject).title + "-" + row[3]
            for section in section_list:
                session_row = [unicode(section), str(section.key()),
                    unicode(subject), str(subject.key()),
                    unicode(section.classroom), 
                    str(section.classroom.key()), class_session_name]
                sessions_request_array(session_row)
        return sessions_request_array
                            
    def _search_for_conflicts(self, sessions_request_array):
        """
        Search the classes for the school and school year for classes
        with subject and section that already exist. These are
        conflicts and should not be created again.
        """
        #get all class sessions already created for the school_year
        query = SchoolDB.models.ClassSession()
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
        filtered_list = []
        conflict_list = []
        for row in sessions_request_array:
            compare_key = row[1] + row[3]
            if filter_dict.has_key(compare_key):
                #the row in the conflict array only needs the names
                #to display
                c_row = [row[2],row[0]]
                self.conflict_array.append(c_row)
            else:
                self.sessions_request_array.append(row)
                
    def _estimate_numbers(self):
        pass
    
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
        pass
    
    def _create_action_display_table(self):
        pass
    
    def _create_class_sessions(self):
        pass

    def _create_tasks(self):
        pass

    def process_request(self):
        """
        Choose process function based upon the step in the process
        """
        if (self.process_step == 1):
            self._process_initial_request()
        elif (self.process_step == 2):
            self._process_final_request()
        else:
            return None
    
    
    @staticmethod
    def manage_creation(school, class_year, argsDict):
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
        creator = BulkClassSessionsCreator(school, school_year, start_date, 
                            stop_date,process_step, process_data)
        return creator.process_request()
        
    