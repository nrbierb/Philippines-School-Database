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
Model and supporting classes and functions to maintain data summaries
and make reports for upper levels of users.
"""
from google.appengine.ext import db
import datetime, logging, pickle
import SchoolDB.assistant_classes
import SchoolDB.models 

class AchievementTestInstanceStatistics():
    """
    A summary of information about an achievement test for a single
    subject for a single section
    """
    def __init__(self, subject_keystr, section_keystr, class_year):
        self.subject = subject_keystr
        self.section = section_keystr
        self.class_year = class_year
        self.combined_statistics = \
            SchoolDB.assistant_classes.StatisicalResults()
        self.male_statistics = SchoolDB.assistant_classes.StatisicalResults()
        self.female_statistics = \
            SchoolDB.assistant_classes.StatisicalResults()

    def set_results(self, combined_results, male_results, female_results):
        """
        Generate the statistical information for the three statistical 
        result object from the matching list of grades
        """
        summaries = (self.combined_statistics, self.male_statistics, 
                     self.female_statistics)
        for i, values in enumerate([combined_results, male_results, 
                                    female_results]):
            summaries[i].set_information(values)

    def valid(self):
        """
        Test that at least the combined values are valid
        """
        return (self.combined_statistics.valid)

    def aggregate_information_from_multiple_results(self,
                                                    instance_statistics_list):
        total_count = len(instance_statistics_list)
        valid_count = 0
        if (total_count == 0):
            valid_count = 0
        elif (total_count == 1):
            instance = instance_statistics_list[1]
            if (instance.valid()):
                valid_count = 1
                self.combined_statistics = instance.combined_statistics
                self.male_statistics = instance.male_statistics
                self.female_statistics = instance.female_statistics
                valid_count = 1
            else:
                valid_count = 0
        else:
            combined_list = [instance.combined_statistics for instance in 
                             instance_statistics_list]
            male_list = [instance.male_statistics for instance in 
                         instance_statistics_list]
            female_list = [instance.female_statistics for instance in 
                           instance_statistics_list]
            combined = SchoolDB.assistant_classes.StatisicalResults()
            male = SchoolDB.assistant_classes.StatisicalResults()
            female = SchoolDB.assistant_classes.StatisicalResults()
            total_count, valid_count = \
                       combined.aggregate_information_from_multiple_results(
                           combined_list)
            male.aggregate_information_from_multiple_results(male_list)
            female.aggregate_information_from_multiple_results(female_list)
            self.combined_statistics = combined
            self.male_statistics = male
            self.female_statistics = female
        return total_count, valid_count

class AchievementTestSummary(
    SchoolDB.assistant_classes.InformationContainer):
    """
    Store all statistical information about the test grades and provide
    supporting functions for access.
    """
    def __init__(self, version_id=1):
        """
        Initialize all data for statistical summaries. This will create a
        CoreAchievementTestRollup instance for each section in the class years
        for each subject. 
        """
        SchoolDB.assistant_classes.InformationContainer.__init__(
            self, version_id)
        self.by_class_year = {} #sets of ati_statistics_set
        self.by_subject = {} #sets of ati_statistics_set
        self.by_section = {} #sets of ati_statistics_set
        self.sections_by_year = {} #sets of section keystrings
        self.subjects_by_year = {}
        self.section_names = {}
        self.subject_names = {}
        self.class_year_by_section = {}
        self.ati_statistics_list = []

    def add_year_and_subject(self, classyear_name, subject_keystr):
        """
        Create a set of statistics for a classyear and subject. This will
        do nothing if these statistics already exist.
        """
        if (not self.get_ati_statistics_set_for_class_year_and_subject(
            classyear_name, subject_keystr)):
            self._create_classyear(classyear_name)
            self._create_subject(subject_keystr)
            self.subjects_by_year[classyear_name].add(subject_keystr)
            for section_keystr in self.sections_by_year[classyear_name]:
                ati_statistics = AchievementTestInstanceStatistics(
                    subject_keystr, section_keystr, classyear_name)
                self.ati_statistics_list.append(ati_statistics)
                self.by_subject[subject_keystr].add(ati_statistics)
                self.by_section[section_keystr].add(ati_statistics)
                self.by_class_year[classyear_name].add(ati_statistics)

    def _has_subject(self, subject_keystr):
        return self.by_subject.has_key(subject_keystr)

    def _has_classyear(self, classyear_name):
        return self.by_class_year.has_key(classyear_name)

    def _has_section(self, section_keystr):
        return self.by_section.has_key(section_keystr)

    def _create_classyear(self, classyear_name, section = None):
        """
        Create all structures and data needed to work with a classyear.
        This may be called repeatedly -- it does nothing if the year
        has already been created.
        """
        if not self._has_classyear(classyear_name):
            self.by_class_year[classyear_name] = set()
            self.subjects_by_year[classyear_name] = set()
            organization = \
                SchoolDB.models.getActiveDatabaseUser().get_active_organization_key()
            self.sections_by_year[classyear_name] = set()
            query = SchoolDB.models.Section.all(keys_only=True)
            query.filter("organization =", organization)
            query.filter("class_year =", classyear_name)
            query.filter("termination_date =", None)
            keys = query.fetch(1000)
            for section_key in keys:
                section_keystr = str(section_key)
                self.sections_by_year[classyear_name].add(section_keystr)
                section = db.get(section_key)
                self.section_names[section_keystr] = unicode(section)
                self.class_year_by_section[section_keystr] = classyear_name
                self.by_section[section_keystr] = set()
        elif (section and not self.section_names.has_key(
            str(section.key()))):
            section_keystr = str(section.key())
            self.sections_by_year[classyear_name].add(section_keystr)
            self.section_names[section_keystr] = unicode(section)
            self.class_year_by_section[section_keystr] = classyear_name
            self.by_section[section_keystr] = set()

    def _create_subject(self, subject_keystr):
        """
        Create all structures and data needed to work with at subject.
        This may be called repeatedly -- it does nothing if the subject
        has already been created.
        """
        if not self._has_subject(subject_keystr):
            self.by_subject[subject_keystr] = set()
            subject = \
                    SchoolDB.utility_functions.get_instance_from_key_string(subject_keystr)
            self.subject_names[subject_keystr] = unicode(subject)


    def get_ati_statistics_set_for_class_year_and_subject(self, class_year, 
                                                          subject_keystr):
        """
        Get an ati_statistics_set for a subject and a class year. This
        should return a set of all ati_statistics instances for
        sections in the class year for the subject. If the class year or subject do
        not exist create them.
        """
        #always call these functions. Nothing will be done if they already exist
        self._create_classyear(class_year)
        self._create_subject(subject_keystr)
        return self.by_class_year[class_year].intersection(
            self.by_subject[subject_keystr])

    def aggregate_ati_statistics_set_for_class_year_and_subject(self,
                                                class_year, subject_keystr):
        ati_statistics_list = \
            list(self.get_ati_statistics_set_for_class_year_and_subject(
                                class_year, subject_keystr))
        aggregated_statistics = AchievementTestInstanceStatistics(
            subject_keystr, "", class_year)
        total_count, valid_count = \
            aggregated_statistics.aggregate_information_from_multiple_results(
                       ati_statistics_list)
        return aggregated_statistics, total_count, valid_count

    def get_ati_statistics_for_section_and_subject(self, section_keystr, 
                                                   subject_keystr):
        """
        Get the ati_statistics for a single section and subject.
        """
        ati_statistics = None
        try:
            #there should always be an entry for the section, but if not,
            #try the build of the class year and section
            if (not self.class_year_by_section.has_key(section_keystr)):
                section = \
                SchoolDB.utility_functions.get_instance_from_key_string(
                    section_keystr)
                if section:
                    class_year = section.class_year
                    self._create_classyear(class_year, section)
                    self._create_subject(subject_keystr)
                logging.info(
                    "Achievement test summary needed to rebuild class year data for class year %s, section %s" 
                    %(class_year, unicode(section)))
            class_year = self.class_year_by_section[section_keystr]
            if set_contains(self.subjects_by_year[class_year], 
                            subject_keystr):
                ati_statistics_set = \
                            self.by_section[section_keystr].intersection(
                            self.by_subject[subject_keystr])
                if (len(ati_statistics_set)):
                    ati_statistics = ati_statistics_set.pop()
        except StandardError, e:
            logging.warning(
                "get_ati_statistics_for_section_and_subject failed: %s" %e)
        return ati_statistics

    def set_ati_statistics_for_class_and_subject(self, section_keystr,
                subject_keystr, combined_results, male_results, 
                female_results):
        """
        Set the statistics in the core ati_statistics instance that represents the
        specified subject and section. Each of the results is a list of the 
        grades for the specified group.
        """
        ati_statistics= self.get_ati_statistics_for_section_and_subject(
            section_keystr, subject_keystr)
        if ati_statistics:
            logging.info("setting ati stat %s" %ati_statistics)
            ati_statistics.set_results(combined_results, male_results, 
                                       female_results)
        logging.info("set complete")

#------------------------------------------------------------------
def set_contains(check_set, value):
    """
    A simple function to determine if the value is in the set.
    """
    test_set = set([value])
    result_set = check_set.intersection(test_set)
    return (len(result_set) > 0)


                    
#------------------------------------------------------------------
#Supporting classes for the summary model classes

class StudentSchoolSectionDict(
    SchoolDB.assistant_classes.InformationContainer):
    """
    A simple class that is a dictionary keyed by the section key. Each
    value is a tuple (section_summary_current(boolean) and
    section_summary (StudentSectionSummary key). It packs and unpacks
    automatically. Rather a pain to use but it assures that value in
    the adatabase instance is always an up-to-date blob.
    """
    def __init__(self, version_id = 1):
        SchoolDB.assistant_classes.InformationContainer.__init__(
            self, version_id)
        self.the_dict ={}
        
    @staticmethod
    def create(version_id = 1):
        dict_object = StudentSchoolSectionDict(version_id)
        return dict_object.put_data(dict_object)
    
    @staticmethod
    def add_section(section_dict_data, section_key, 
                    section_summary_key, is_current=False):
        sect_dict = StudentSchoolSectionDict.get_data(section_dict_data)
        sect_dict.the_dict[section_key] = (section_summary_key,
                                                 is_current)
        return sect_dict.put_data()
    
    @staticmethod
    def get_section_keys(section_dict_data):
        sect_dict = StudentSchoolSectionDict.get_data(section_dict_data)       
        return sect_dict.the_dict.keys()
    
    @staticmethod
    def get_section_summary(section_dict_data, section_key):
        sect_dict = StudentSchoolSectionDict.get_data(section_dict_data)
        (section_summary_key, is_current) = \
         sect_dict.the_dict.get(section_key, (None, False))
        return section_summary_key

    @staticmethod
    def get_all_summaries(section_dict_data):
        sect_dict = StudentSchoolSectionDict.get_data(section_dict_data)
        values_list = sect_dict.the_dict.values()
        summaries_list = [value[0] for value in values_list]
        return summaries_list

    @staticmethod
    def get_section_is_current(section_dict_data, section_key):
        sect_dict = StudentSchoolSectionDict.get_data(section_dict_data)
        (section_summary_key, is_current) = \
         sect_dict.the_dict.get(section_key, (None, True))
        return is_current    
    
    @staticmethod
    def mark_status(section_dict_data, section_key, is_current=True):
        sect_dict = StudentSchoolSectionDict.get_data(section_dict_data)
        was_current = True
        if sect_dict.the_dict.has_key(section_key):
            (section_summary_key, was_current) = \
             sect_dict.the_dict[section_key]
            sect_dict.the_dict[section_key] = \
                     (section_summary_key, is_current)
        if (was_current != is_current):
            return sect_dict.put_data()
    
    @staticmethod
    def get_is_current(section_dict_data):
        """
        Scan the entire dict for a section that is not current.
        If any found return false.
        """
        sect_dict = StudentSchoolSectionDict.get_data(section_dict_data)
        for value in sect_dict.the_dict.values():
            if not value[1]:
                return False
        return True
        
    @staticmethod
    def get_all_summaries_not_current(section_dict_data):
        """
        Return a list of all section summary keys that are out of date
        """
        not_current_list = []
        sect_dict = StudentSchoolSectionDict.get_data(section_dict_data)
        for value in sect_dict.the_dict.values():
            if not value[1]:
                not_current_list.append(value[0])
        return not_current_list
        
class StudentSectionSummaryData(
    SchoolDB.assistant_classes.InformationContainer):
    """
    """
    def __init__(self, version_id = 1):
        SchoolDB.assistant_classes.InformationContainer.__init__(
            self, version_id)
        self.initialize()

    def initialize(self):
        """
        The object is only created once but often reinitialized. This
        will create all values during initial object creation and simply
        reinitialize at later times.
        """
        self.record_is_current = False
        self.num_students = [0,0,0]
        self.balik_aral = [0,0,0]
        self.transferred_in = [0,0,0]
        self.transferred_out = [0,0,0]
        self.dropped_out = [0,0,0]
        self.min_age = [100,100,100]
        self.max_age = [0,0,0]
        self.median_age = [0, 0, 0]
        self.average_age = [0.0, 0.0, 0.0]
        #The age calculations are similar to the calculations done for the
        #the age report but with some unnecessary variables stripped.
        self.max_value = 30
        # all arrays have Name, Male, Female, 
        #Combined as the organization per row
    
    def initialize_status_tests(self, student_designation_names):
        """
        Compute values to be used by the tests for student status. These
        precomputed values make the actual tests more efficient.
        """
        designation_key_dict = {}
        for name in student_designation_names:
            designation_key_dict[name] = \
                SchoolDB.utility_functions.get_entities_by_name(
                    SchoolDB.models.SpecialDesignation, name, key_only=True)
        start_date, end_date = \
            SchoolDB.models.SchoolYear.school_year_start_and_end_dates(
            date=datetime.date.today(), include_prior_break=False)
        return {"designation_key_dict":designation_key_dict, 
                "start_date":start_date, "end_date":end_date}
        
    def get_student_designations(self, student, student_designation_names,
                                 testinfo):
        """
        A combination of tests that are most efficiently done together.
        They use the precomputed values of year time and the instance
        key for the designation type. The designation instance keys
        """
        history = student.special_designation_history
        students_designation_dict = {}
        for name in student_designation_names:
            students_designation_dict[name] = False
        if history:
            designation_keys, changed_during_year = \
                history.get_value_at_end_of_school_year(ref_date=None, 
                            period_start_date=testinfo["start_date"],
                            period_end_date=testinfo["end_date"])
            if designation_keys:
                for name in student_designation_names:
                    key = testinfo["designation_key_dict"].get(name, None)
                    try:
                        if key:
                            index = designation_keys.index(key)
                            students_designation_dict[name] = \
                                        changed_during_year[index]
                    except ValueError:
                        pass
        return students_designation_dict
            
    def get_other_enrollment_status(self, section, status_name, testinfo):
        """
        The students with these statuses are not enrolled but are of
        interest for the year. Only those whose status has changed
        within the current year are of interest. A tuple of
        (male_count, female_count, and total_count) is returned
        """
        query = SchoolDB.models.Student.all(keys_only = True)
        query.filter("section = ", section)
        query.filter("student_status = ", 
                     SchoolDB.models.get_student_status_key_for_name(
                         status_name))
        #show only those that have happened this school year
        #>>>>To Be Done: filter results of query for end of year
        SchoolDB.utility_functions.filter_by_date(query, "after",
            "student_status_change_date", 0, testinfo["start_date"])
        all_students = query.count()
        query.filter("gender = ", "Male")
        male = query.count()
        female = all_students - male
        return (male, female, all_students)

    def update_student_information(self, section):
        """
        Read each student record for the section to get the individual
        information and incrementally build the summary.
        """
        self.initialize()
        student_designation_names = ["Balik Aral", "Transferred In"]
        testinfo = self.initialize_status_tests(student_designation_names)
        col_female = 1
        col_male = 0
        col_all_students = 2
        age_sum = [0,0,0]
        age_list = [[],[],[]]
        query = SchoolDB.models.Student.all(keys_only=True)
        SchoolDB.models.active_student_filter(query)
        query.filter("section = ", section)
        keys = query.fetch(1000)
        students = db.get(keys)
        for student in students:
            #Add individual student to the set of information.
            #Each record will only increment appropriate summary values.
            #No information is kept by student
            if (student.gender == "Male") :
                col_index = col_male
            else:
                col_index = col_female
            self.num_students[col_index] += 1
            #logging.info(unicode(student))
            special_designation_dict = \
                            self.get_student_designations(student, 
                                    student_designation_names, testinfo)
            if (special_designation_dict.get("Balik Aral", False)):
                self.balik_aral[col_index] += 1
            if (special_designation_dict.get("Transferred In", False)):
                self.transferred_in[col_index] += 1 
            student_age = student.age(datetime.date.today(), "schoolyear")
            age_sum[col_index] += student_age
            if (student_age != 0):
                age_list[col_index].append(student_age)
            if (student_age > self.max_age[col_index]):
                self.max_age[col_index] = student_age
            if ((student_age < self.min_age[col_index]) and
                (student_age > 7)):
                #Assure that records with no birthday do not interfere
                self.min_age[col_index] = student_age
        #perform special query for other students that are not active
        self.dropped_out[col_male], self.dropped_out[col_female],\
        self.dropped_out[col_all_students] = \
        self.get_other_enrollment_status(section, "Dropped Out", testinfo)
        self.transferred_out[col_male], self.transferred_out[col_female],\
        self.transferred_out[col_all_students] = \
        self.get_other_enrollment_status(section, "Transferred Out", testinfo)
        #compute combined gender values
        self.num_students[col_all_students] = self.num_students[col_male] + \
            self.num_students[col_female]
        self.min_age[col_all_students] = self.min_age[col_male]
        if (self.min_age[col_all_students] > self.min_age[col_female]):
            self.min_age[col_all_students] = self.min_age[col_female]
        self.max_age[col_all_students] = self.max_age[col_male]
        if (self.max_age[col_all_students] < self.max_age[col_female]):
            self.max_age[col_all_students] = self.max_age[col_female]
        self.balik_aral[col_all_students] = self.balik_aral[col_male] +\
            self.balik_aral[col_female]
        self.transferred_in[col_all_students] = \
            self.transferred_in[col_male] + self.transferred_in[col_female]
        for col in (col_male, col_female):
            age_list[col].sort()
            count = len(age_list[col])
            if (count):
                self.average_age[col] = round(age_sum[col] / count, 1)
                self.median_age[col] = age_list[col][int (count / 2)]
        age_list[0].extend(age_list[1])
        count = len(age_list[0])
        if count:
            age_list[0].sort()
            self.average_age[col_all_students] =  round((age_sum[col_male] + 
                            age_sum[col_female]) / count, 1)
            self.median_age[col_all_students] = age_list[0][int (count / 2)]
        self.record_is_current= True
        
    def is_current(self):
        return self.record_is_current
    
    def mark_needs_update(self):
        self.record_is_current = False
        
    