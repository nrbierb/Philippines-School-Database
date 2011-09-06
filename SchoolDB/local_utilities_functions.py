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
Utilities that are normally used as scheduled jobs or called from the 
"Run Utility" web page. 
"""

import cPickle, zlib, datetime, random, logging, csv
import StringIO, codecs, base64
from django.utils import simplejson
from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import db

import SchoolDB.models


def change_parameter(keystr, change_parameters):
    """
    This function is designed to provide simple support for parameter
    change from a task. It depends upon the task creator to select
    instances and the runTask function to iterate through the instances
    calling this function for each one. The function will change a single
    parameter value in an object instance. If the parameter has an
    associated change_date and history, they will be updated as
    appropriate if a date is provided.
    The single argument "change_parameters" is a dictionary keyed with 
    the following values:
    1. changed_parameter
    2. new_value
    3. change_date (arg is an integer for the date ordinal)
    4. date_parameter 
    5. history_parameter
    6. value_is_reference
    If the changed_parameter does not have a history then dictionary 
    entries 3-6 need not be defined.
    """ 
    try:
        obj = SchoolDB.models.get_instance_from_key_string(keystr)
        has_history = (change_parameters.has_key("change_date") and 
            change_parameters.has_key("date_parameter"))
        if has_history:
            prior_date = getattr(obj, 
                    change_parameters["date_parameter"]).toordinal()
            if (prior_date > change_parameters["change_date"]):
                #change occured later than date to be set leave unchanged
                return True
        new_value = change_parameters["new_value"]
        old_value = getattr(obj, 
                        change_parameters["changed_parameter"])
        if change_parameters.get("value_is_reference", False):
            new_value = SchoolDB.models.get_key_from_string(new_value)
            old_value = old_value.key()
        if (new_value == old_value):
            #If the value is already set to new value do nothing
            #This saves time (the history is already idempotent)
            return True
        setattr(obj, change_parameters["changed_parameter"], new_value)
        if has_history:
            change_date = datetime.date.fromordinal(
                change_parameters["change_date"])
            if (change_parameters.has_key("date_parameter")):
                setattr(obj, change_parameters["date_parameter"],
                        change_date)
            if (change_parameters.has_key("history_parameter")):
                history = getattr(obj, 
                            change_parameters["history_parameter"])
                is_reference = change_parameters.get(
                    "value_is_reference", False)
                if (is_reference):
                    string_val = ""
                    ref_val = new_value
                else:
                    string_val = new_value
                    ref_val = None
                history.add_or_change_entry_if_changed(
                    start_date=change_date,
                    info_str=string_val, info_reference= ref_val)
        obj.put()
        return True
    except StandardError, e:
        logging.error("Change_parameter failed on %s '%s': '%s'" 
                      %(obj.class_name, unicode(obj), e))
        return False

def bulk_update_by_task(model_class, filter_parameters, change_parameters,
                        task_name = "Bulk Update", organization = None):
    """
    Change the value of a parameter for all class objects that meet the
    filter specification. This may be used with a parameter that uses an
    associated history. The filtering is done with
    SchoolDB.assistant_classes.QueryMaker object.
    
    The arguments are:
    
    -model_class: The class of the object to be changed.
    
    -filter_parameters: This is a direct pass through to the QueryMaker object.
    See documentation on that class for details.
    
    -change_parameters: a dictionary keyed with the following values
    1. changed_parameter
    2. new_value
    If parameter has associated history:
    3. change_date
    4. date_parameter
    5. history_parameter
    6. value_is_reference
    If the changed_parameter does not have a history then dictionary 
    entries 3-6 need not be defined.
    
    This utility function uses tasks to perform the actions so there is no 
    worry about exceeding the time limit or cousing long wait times for the 
    caller. It also uses the query iterator so there is no worry about the 
    number of instances.
    """
    try:
        result_string = "Nothing queued"
        if (change_parameters.has_key("changed_parameter") and
                 change_parameters.has_key("new_value") and model_class):
            #if these aren't defined do nothing...
            qmkr_desc = SchoolDB.assistant_classes.QueryDescriptor()
            qmkr_desc.set("filters", filter_parameters)
            qmkr_desc.set("return_iterator", True)
            qmkr_desc.set("keys_only", True)
            qmkr_query = SchoolDB.assistant_classes.QueryMaker(
                model_class, qmkr_desc)
            query_iterator, extra_data = qmkr_query.get_objects()
            if query_iterator and query_iterator.count():
                task_generator =SchoolDB.assistant_classes.TaskGenerator(
                    task_name=task_name, function = 
                    "SchoolDB.local_utilities_functions.change_parameter", 
                    function_args=change_parameters, 
                    organization=organization, 
                    query_iterator=query_iterator,
                    instances_per_task=10)
                successful, result_string = task_generator.queue_tasks()
        return result_string
    except StandardError, e:
        result_string = "bulk_update_by_task for %s failed: %s" %(model_class, e)
        logging.error(result_string)
        return result_string

def duplicate_log_entries(logger, text, warning_level = False):
    """
    Add the text as a line on the logger and as an entry in the
    database log.
    """
    logger.add_line(text)
    if warning_level:
        logging.warning(text)
    else:
        logging.info(text)
    
#---------------------------------------------------------------------

def update_student_summary(force = False):
    """
    The utility function called as a scheduled job to perform an update
    on school student summary records.
    """
    try:
        organization = \
            SchoolDB.models.getActiveOrganization()
        if (organization.classname == "School"):
            result = organization.update_student_summary(force)
            return result
        else:
            return "Wrong organization type: " + organization.classname
        #change error type after debugging
    except EOFError, e:
        return "Failed Update Student Summary %s" %e
        
def update_student_summary_by_task(encompassing_organization=None,
                                   force = False):
    """
    Call update_student_summary with logging
    """
    if not(encompassing_organization):
        encompassing_organization = \
            SchoolDB.models.getActiveDatabaseUser().get_active_organization()
    orgs_list = encompassing_organization.get_schools()
    if orgs_list:
        for organization in orgs_list:
            org_keystring = str(organization.key())
            task_name = "Update Student Summary: " + unicode(organization)
            if (force):
                task_name = "Forced " + task_name
            task_generator = SchoolDB.assistant_classes.TaskGenerator(
                task_name = task_name, function=
                "SchoolDB.local_utilities_functions.update_student_summary",
                function_args=force, organization=org_keystring, 
                rerun_if_failed=False)
            task_generator.queue_tasks()

def update_student_summary_utility(logger, encompassing_organization_name="",
                                   force = ""):
    """
    A trivial wrapper for call from utilrequest webpage
    """
    encompassing_organization = None
    if (encompassing_organization_name):
        q = SchoolDB.models.Organization.all()
        q.filter("name =", encompassing_organization_name)
        encompassing_organization = q.get()
    update_student_summary_by_task(encompassing_organization, (force != ""))
    logger.add_line("Queued all")
 
#def update_section_initial_student_counts(logger=None):
    #try:
        #organization = \
            #SchoolDB.models.getActiveOrganization()
        #if (organization.classname == "School"):
            #query = SchoolDB.models.Section.all()
            #query.filter("organization =", organization)
            #query.filter("termination_date =", None)
            #sections = query.fetch(200)
            #for section in sections:
                #section.save_student_count()
                #logging.info("Updated section '%s' students list"
                             #%unicode(section))
            #logging.info("Completed section_prior_list_update for all sections in school '%s'" %unicode(organization))
            #return True
        #else:
            #logging.error("The organization '%s' is not a school so there are no sections to update." %unicode(organization))
            ##It was not successful but should not be run again because it 
            ##will continue to fail.
            #return True
        ##change error type after debugging
    #except EOFError, e:
        #logging.error("Failed Update Student Summary %s" %e)
        #return False

def run_task_for_all_schools_in_organization(logger, task_name_string,
                            task_function_string, organization_name=""):
    """
    Run count_student_class_records across all schools in the region
    using tasks
    """
    schools = SchoolDB.utility_functions.get_schools_in_named_organization(
        organization_name)
    for school in schools:
        org_keystring = str(school.key())
        task_name = task_name_string + ": " + unicode(school)
        logger.add_line(task_name) 
        task_generator = SchoolDB.assistant_classes.TaskGenerator(
            task_name = task_name, function = task_function_string,
            organization=org_keystring, rerun_if_failed=False)
        task_generator.queue_tasks()
    report = "Scheduled '%s' for %d schools." %(task_name_string, len(schools))
    return report

def build_all_student_class_records(logger, organization_name=""):
    """
    Run count_student_class_records across all schools in the named organization
    using tasks
    """
    result = run_task_for_all_schools_in_organization(logger, 
        "Build Student Class Records",
        "SchoolDB.local_utilities_functions.build_all_student_class_records_for_school_task",
        organization_name)
    logger.add_line(result)
    return result

def build_all_student_class_records_for_school_task():
    """
    Create student class records for all students for all classes
    taught by section. This uses tasks to complete a very heavyweight
    action. This would normally only be run once a yera and, in fact,
    should never need to be run. It is only useful when there has failed
    to be an automatic creation at the time of class creation or
    student assignment to a section.
    """
    try:
        school = \
            SchoolDB.models.getActiveOrganization()
        if (school.classname == "School"):
            logging.info("Starting class record creation for school: " + \
                        unicode(school))
            #Create a list of classes taught by section for the current year.
            query = SchoolDB.models.ClassSession.all()
            query.filter("organization =", school.key())
            current_school_year = SchoolDB.models.SchoolYear.school_year_for_date()
            query.filter("school_year = ", current_school_year.key())
            query.filter("students_assigned_by_section = ", True)
            class_sessions = query.fetch(700)
            #perform assign for all classes. Each class_session uses an individual
            #task
            logging.info("%d class sessions found for school year %s" \
                         %(len(class_sessions), unicode(current_school_year)))
            task_function_string = \
                "SchoolDB.models.ClassSession.static_assign_to_all_section_students"
            org_keystring = str(school.key())
            for class_session in class_sessions:
                task_name =  "Create student records for: " + class_session.name
                function_args = 'class_session_keystring = "%s"' \
                              %str(class_session.key())
                task_generator = SchoolDB.assistant_classes.TaskGenerator(
                    task_name = task_name, function = task_function_string,
                    function_args=function_args, organization=org_keystring,
                    rerun_if_failed=False)
                task_generator.queue_tasks()
            return "Completed successfully"
        else:
            report_text = "%s -- wrong organization type: %s" \
                        %(unicode(school), school.classname)
            logging.info(report_text)
            return report_text
    except StandardError, e:
        error_text = "Build All Student Class Records for %s: %s" \
                      %(unicode(school), e)
        logging.error(error_text)
        return error_text

def build_all_student_class_records_for_one_class_session(logger, section_name, 
                subject_name, organization_name = ""):
    class_session = \
                SchoolDB.utility_functions.get_class_session_from_section_and_subject(
                    section_name, subject_name, organization_name)
    if class_session:
        return class_session.assign_to_all_section_students()
    else:
        return False

def count_student_class_records(logger, organization_name=""):
    """
    Run count_student_class_records across all schools in the named organization
    using tasks
    """
    result = run_task_for_all_schools_in_organization(logger, 
        "Count Student Class Records",
        "SchoolDB.local_utilities_functions.count_student_class_records_task",
        organization_name)
    logger.add_line(result)
    return result
    

def count_student_class_records_task():
    """
    Count the number of student records per class session and compare with 
    the number of students in the section.
    """
    try:
        school = \
            SchoolDB.models.getActiveOrganization()
        if (school.classname == "School"):
            section_count = {}
            section_names = {}
            sections_class_sessions = {}
            query = SchoolDB.models.Section.all()
            query.filter("organization =", school)
            #sections = query.fetch(500)
            for section in query:
                q = SchoolDB.models.Student.all()
                SchoolDB.models.active_student_filter(q)
                q.filter("section =", section)
                count = q.count()
                section_count[section.key()] = count
                section_names[section.key()] = unicode(section)
                sections_class_sessions[section.key()] = []
            logging.info("Number of sections: %d" %len(section_count))
            #now get the class sessions
            query = SchoolDB.models.ClassSession.all()
            query.filter("organization =", school)
            current_school_year = SchoolDB.models.SchoolYear.school_year_for_date()
            query.filter("school_year = ", current_school_year.key())
            query.filter("students_assigned_by_section = ", True)
            #class_sessions = query.fetch(700)
            #logging.info("Number of class sessions: %d" %len(class_sessions))
            #perform assign for all classes. Each class_session uses an individual
            #task
            session_count = {}
            session_names = {}
            i = 0
            for class_session in query:
                session_key = class_session.key()
                session_name = class_session.name
                q = SchoolDB.models.StudentsClass.all()
                q.filter("class_session =", session_key)
                count = q.count()
                session_count[session_key] = count
                session_names[session_key] = session_name
                try:
                    section = class_session.section.key()
                    sections_class_sessions[section].append(session_key)
                except db.ReferencePropertyResolveError, e:
                    logging.info("%s reference resolve error: %s" 
                                 %(session_name, e))
            total_student_section_count = 0
            total_student_class_records_count = 0
            logging.info("Student class records check:")
            report_text = ""
            for section in section_count.keys():
                total_student_section_count += section_count[section]
                for session in sections_class_sessions[section]:
                    total_student_class_records_count += session_count[session]
                    report_line = """
        '%s'   '%s'   %d   %d    %d""" %(section_names[section],
                            session_names[session], section_count[section],
                            session_count[session], 
                            section_count[section] - session_count[session])
                    report_text += report_line  
                    if (len(report_text) > 500):
                        logging.info(report_text)
                        report_text = ""
            logging.info(report_text)
            report_text = """
      Correct class count: %d\t\tActual class count: %d\t\t Delta: %d""" \
                        %(len(section_count)*7, len(session_count), 
                          len(section_count)*7 - len(session_count))
            report_text +=  """        
      Correct student record count: %d\t\tActual student record count: %d\t\tDelta: %d"""\
                     %(total_student_section_count * 7, 
                       total_student_class_records_count, 
                       total_student_section_count * 7 - 
                       total_student_class_records_count)
            logging.info(report_text)
            return "Completed successfully"
        else:
            report_text = "%s -- wrong organization type: %s" \
                        %(unicode(school), school.classname)
            logging.info(report_text)
            return report_text
    except StandardError, e:
        logging.info("Failed Count Student Class Records %s" %e)
        return False

def count_student_class_records_task_multitask():
    """
    Count the number of student records per class session and compare with 
    the number of students in the section. This is split into two parts by a task to prevent memory usage problems. This first part gets information about the sections and spawns a task to complete the function.
    """
    school = \
        SchoolDB.models.getActiveOrganization()
    if (school.classname == "School"):
        section_count = {}
        section_names = {}
        query = SchoolDB.models.Section.all()
        query.filter("organization =", school)
        #sections = query.fetch(500)
        for section in query:
            q = SchoolDB.models.Student.all()
            SchoolDB.models.active_student_filter(q)
            q.filter("section =", section)
            count = q.count()
            section_count[section.key()] = count
            section_names[section.key()] = unicode(section)
            #section_data = cPickle.dumps({"section_count":section_count,
                                          #"section_names":section_names})
            #packed_section_data = zlib.compress(section_data)
            #encoded_section_data = base64.b64encode(packed_section_data)
            #school_keystring = str(school.key())
            #task_name = "Count Student Class Records Part B: " + unicode(school)
            #function_args = 'section_information_blob= "%s"' %encoded_section_data 
            #task_generator = SchoolDB.assistant_classes.TaskGenerator(
                #task_name = task_name, function=
                #"SchoolDB.local_utilities_functions.count_student_class_records_task_part_b",
                #function_args=function_args, organization=school_keystring, 
                #rerun_if_failed=False)
            #task_generator.queue_tasks()
            #logging.info("Scheduled Part B. Number of sections: %d" %len(section_count))
            #return True
        #else:
            #report_text = "%s -- wrong organization type: %s" \
                        #%(unicode(school), school.classname)
            #logging.info(report_text)
            #return report_text
    
    #def count_student_class_records_task_part_b(section_information_blob):
        #"""
        #Count the number of student records per class session and compare
        #with the number of students in the section. This is split into two
        #parts by a task to prevent memory usage problems. This second part
        #gets the information about the class sessions and then generates
        #the report.
        #"""
        #school = \
            #SchoolDB.models.getActiveOrganization()
        #unencoded = base64.b64decode(section_information_blob)
        #uncompressed = zlib.decompress(unencoded)
        #section_information = cPickle.loads(uncompressed)
        #section_names = section_information["section_names"]
        #section_count = section_information["section_count"]
        sections_class_sessions = {}
        for section in section_count.keys():
            sections_class_sessions[section] = []
        query = SchoolDB.models.ClassSession.all()
        query.filter("organization =", school)
        current_school_year = SchoolDB.models.SchoolYear.school_year_for_date()
        query.filter("school_year = ", current_school_year.key())
        query.filter("students_assigned_by_section = ", True)
        class_sessions = query.fetch(700)
        logging.info("Number of class sessions: %d" %len(class_sessions))
        #perform assign for all classes. Each class_session uses an individual
        #task
        session_count = {}
        session_names = {}
        i = 0
        for class_session in class_sessions:
            i += 1
            session_key = class_session.key()
            session_name = class_session.name
            q = SchoolDB.models.StudentsClass.all()
            q.filter("class_session =", session_key)
            count = q.count()
            session_count[session_key] = count
            session_names[session_key] = session_name
            try:
                section = class_session.section.key()
                sections_class_sessions[section].append(session_key)
            except db.ReferencePropertyResolveError, e:
                logging.info("%s reference resolve error: %s" 
                             %(session_name, e))
        total_student_section_count = 0
        total_student_class_records_count = 0
        logging.info("Student class records check for %s:" %unicode(school))
        report_text = ""
        for section in section_count.keys():
            total_student_section_count += section_count[section]
            for session in sections_class_sessions[section]:
                total_student_class_records_count += session_count[session]
                report_line = """
        '%s'   '%s'   %d   %d    %d""" %(section_names[section],
                        session_names[session], section_count[section],
                        session_count[session], 
                        section_count[section] - session_count[session])
                report_text += report_line  
                if (len(report_text) > 500):
                    logging.info(report_text)
                    report_text = ""
        logging.info(report_text)
        report_text = """
        Correct class count: %d\t\tActual class count: %d\t\t Delta: %d""" \
                    %(len(section_count)*7, len(session_count), 
                      len(section_count)*7 - len(session_count))
        report_text +=  """        
        Correct student record count: %d\t\tActual student record count: %d\t\tDelta: %d"""\
                 %(total_student_section_count * 7, 
                   total_student_class_records_count, 
                   total_student_section_count * 7 - 
                   total_student_class_records_count)
        logging.info(report_text)
        return "Completed successfully"
    else:
        report_text = "%s -- wrong organization type: %s" \
                    %(unicode(school), school.classname)
        logging.info(report_text)
        return report_text

def fix_student_class_record_count(logger, organization_name = "",
                                   change_database = False):
    """
    Remove incorrect student records for a school using the task
    fix_student_class_record_count_task for each class_session.
    """
    if (not organization_name):
        school = \
            SchoolDB.models.getActiveDatabaseUser().get_active_organization()
    else:
        school = SchoolDB.utility_functions.get_entities_by_name(
            SchoolDB.models.School, organization_name)    
    if not school:
        duplicate_log_entries(logger,"No school named '%s' found." 
                              %organization_name)
        return False
    query = SchoolDB.models.ClassSession.all()
    query.filter("organization =", school)
    current_school_year = SchoolDB.models.SchoolYear.school_year_for_date()
    query.filter("school_year = ", current_school_year.key())
    query.filter("students_assigned_by_section = ", True)
    class_sessions = query.fetch(700)
    duplicate_log_entries(logger,
            "Number of class sessions: %d" %len(class_sessions))
    school_keystring = str(school.key())
    function = \
        "SchoolDB.local_utilities_functions.fix_student_class_record_count_task"
    task_count = 0
    for class_session in class_sessions:
        try:
            task_name = "Fix student class record counts. Section: '%s--%s'" \
                      %(unicode(class_session.section),class_session.name)
            function_args='class_session_keystring="%s", change_database = %s' \
                         %(str(class_session.key()), change_database)
            task_generator = SchoolDB.assistant_classes.TaskGenerator(
                    task_name = task_name, function = function,
                    function_args = function_args, organization= school_keystring,
                    rerun_if_failed = False)
            task_generator.queue_tasks()
        except db.ReferencePropertyResolveError, e:
            duplicate_log_entries(logger,
                "Class session '%s', key '%s' had resolve error '%s'."
                %(unicode(class_session), class_session.key(), e))
        task_count += 1
    duplicate_log_entries(logger, "Scheduled %d tasks" %task_count)
    return True

    
def fix_student_class_record_count_for_one_class_session(logger, section_name, 
                subject_name, organization_name = "", change_database = False):
    class_session = \
                SchoolDB.utility_functions.get_class_session_from_section_and_subject(
                    section_name, subject_name, organization_name)
    if class_session:
        return fix_student_class_record_count_task(str(class_session.key()), 
                                               change_database)
    else:
        return False

def fix_student_class_record_count_task(class_session_keystring, 
                                        change_database = False):
    """
    Perform the task action of testing the class_session for incorrect
    student class records. Bad records are deleted from the database if
    change_database is True. If False, the deletions that would have
    been performed are merely reported.
    """
    class_session = SchoolDB.utility_functions.get_instance_from_key_string(
        class_session_keystring, SchoolDB.models.ClassSession)
    if not class_session:
        logging.warning("No class session provided")
        return False
    section = None
    if class_session.students_assigned_by_section:
        section = class_session.section
    if not section:
        logging.warning("No section for the class session")
        return False
    errors_found = False
    logging.info("Section: %s Class Session: %s" \
                          %(unicode(section),class_session.name))
    query = SchoolDB.models.StudentsClass.all()
    query.filter("class_session =", class_session)
    student_class_records = query.fetch(500)
    students = section.get_students()
    logging.info(
        "Found %d student class records. %d students in section." \
        %(len(student_class_records), len(students)))
    students_dict = {}
    sections_dict = {}
    section_students_dict = {}
    wrong_section_students_dict = {}
    wrong_section_records = []
    bad_status_students_dict= {}
    bad_status_records = []
    duplicate_records_count = 0
    active_status_key = SchoolDB.models.get_active_student_status_key()
    for class_record in student_class_records:
        try:
            student = class_record.get_student()
            if students_dict.has_key(student):
                students_dict[student].append(class_record)
                duplicate_records_count += 1
                errors_found = True
            else:
                students_dict[student] = [class_record]            
            if (student.section.key() != section.key()):
                wrong_section_records.append(class_record)
                wrong_section_students_dict[student] = True
                logging.info("Wrong section. Section: %s   Student: %s"\
                        %(unicode(student.section), unicode(student)))
                errors_found = True
            elif (student.student_status.key() != active_status_key):
                bad_status_records.append(class_record)
                bad_status_students_dict[student] = True
                logging.info("Bad Status:  Student: %s  Status: %s"\
                        %(unicode(student), unicode(student.student_status)))
                errors_found = True
            else:
                section_students_dict[student] = True
        except StandardError, e:
            logging.info("Error: %s '%s'" %(unicode(student), e))
            class_record.remove_record_if_not_yet_used(change_database)
    if (len(wrong_section_students_dict) != 0):
        logging.info("Found %d wrong section students." \
                        %len(wrong_section_students_dict)) 
    section_error_count = len(students) - len(section_students_dict)
    if (section_error_count != 0):
        logging.info(
            "%d more students in section than with records" %section_error_count)
        errors_found = True
    if (duplicate_records_count):
        logging.info("Found %d duplicate records   %d wrong section" \
                    %duplicate_records_count)
    if (len(wrong_section_records)):
        logging.info(
            "Found %d wrong section records, %d wrong section students" \
            %(len(wrong_section_records), len(wrong_section_students_dict)))
        for wrong_section_record in wrong_section_records:
            wrong_section_record.remove_record_if_not_yet_used(change_database)
    if (len(bad_status_records)):
        logging.info(
            "Found %d bad status records, %d bad status students" \
            %(len(bad_status_records), len(bad_status_students_dict)))
        for bad_record in bad_status_records:
            bad_record.remove_record_if_not_yet_used(change_database)
    if not errors_found:
        logging.info("No errors found")
    return True
                                   
#----------------------------------------------------------------------
# Specific limited purpose utilities

def bulk_student_status_change_utility(logger, class_year, 
                        prior_status_name = "Enrolled", 
                        new_status_name="Not Currently Enrolled",
                    prior_status_oldest_change_date = None, 
                    change_date = None, year_end = True,
                    organization=None):
    """
    Change the student status for students of a single class year to
    the status with name "new_status_name" with the date "date". If
    date is none then the end or the beginning of the school year is
    used.The date to determine the school year is adjusted to allow
    this to be used three weeks before or after the actual year.
    """
    duplicate_log_entries(logger,"Starting change of %s student status."
                          %class_year)
    if (not change_date):
        date_adjust = datetime.timedelta(21)
        if year_end:
            test_date = datetime.date.today() - date_adjust
            change_date = \
                SchoolDB.models.SchoolYear.school_year_end_for_date(test_date)
        else:
            test_date = datetime.date.today() + date_adjust
            change_date = \
                 SchoolDB.models.SchoolYear.school_year_start_for_date(
                     test_date)
    prior_student_status_object = SchoolDB.models.get_entities_by_name(
        SchoolDB.models.StudentStatus, prior_status_name)
    new_student_status_object = \
            SchoolDB.models.get_entities_by_name(SchoolDB.models.StudentStatus, new_status_name)
    new_student_status_keystring = str(new_student_status_object.key())
    if (prior_student_status_object and new_student_status_object):
        model_class = SchoolDB.models.Student
        query_filters = [("class_year = ", class_year),
                         ("student_status = ", prior_student_status_object),
                         ("student_status_change_date >", 
                          prior_status_oldest_change_date)
                          ]
        change_parameters = {"changed_parameter":"student_status",
                             "new_value":new_student_status_keystring,
                             "change_date":change_date.toordinal(),
                             "date_parameter":"student_status_change_date",
                             "history_parameter":"student_status_history",
                             "value_is_reference":True}
        bulk_update_by_task(model_class, query_filters, 
                            change_parameters, organization=organization)

def end_of_year_update_school(logger):
    logging.info("Starting stat change")
    for class_year in ["First Year", "Second Year", "Third Year"]:
        bulk_student_status_change_utility(logger, class_year, 
                            prior_status_name = "Enrolled", 
                            new_status_name="Not Currently Enrolled",
                            change_date = datetime.date(2011,3,31))
        logging.info("Called bulk for " + class_year)
    bulk_student_status_change_utility(logger, "Fourth Year", 
                            prior_status_name = "Enrolled", 
                            new_status_name="Graduated",
                            change_date = datetime.date(2011,3,30))
    logging.info("Called bulk for Fourth Year")
    logging.info("All bulk called")

def start_of_year_update_school(logger):
    """
    Set the enrollment date for all students. This should NOT be done on
    the real database
    """
    if (SchoolDB.views.getprocessed().is_real_database):
        looging.info("start_of_year_update_school not allowed for real database")
    logging.info("Starting stat change")
    for class_year in ["First Year", "Second Year", "Third Year"]:
        bulk_student_status_change_utility(logger, class_year, 
                            prior_status_name = "Enrolled", 
                            new_status_name="Enrolled",
                            change_date = datetime.date(2011,6,7))
        logging.info("Called bulk for " + class_year)
    logging.info("All bulk called")

def check_encoding_count(logger):
    """
    Scan all schools to count of students encoded by section. This
    first version just uses the logging to report results.
    This uses logging level warning just to allow it to be easily 
    filtered. It is really just an info message -- not a warning
    """
    duplicate_log_entries(logger,"Beginning encoding count check.", True)
    school_query = SchoolDB.models.School.all()
    enrolled_key = SchoolDB.models.get_entities_by_name(
        SchoolDB.models.StudentStatus, "Enrolled", True)    
    for school in school_query:
        school_name = school.name
        logging.info("----------------- %s --------------" %school_name)
        section_query = SchoolDB.models.Section.all()
        section_query.ancestor(school)
        for section in section_query:
            section_name = section.name
            student_query = SchoolDB.models.Student.all()
            student_query.filter("section =", section.key())
            student_query.filter("student_status =", enrolled_key)
            count = student_query.count()
            logging.info("--%s  %d" %(section_name, count))
            #for student in student_query:
                #if not student.attendance:
                    #logging.info("   ++missing attendance: %s" %unicode(student))
    duplicate_log_entries(logger,"Encoding count check complete.", True)

def find_duplicate_students(logger):
    """
    Build a list of all students in the school with last name, first name, and
    birthday. Sort in same order and look for matches.
    """
    student_list = []
    logging.info("Starting find_duplicate students")
    query = SchoolDB.models.Student.all()
    query.filter("organization =", SchoolDB.models.getActiveOrganization())
    student_list = []
    for student in query:
        if student.birthdate:
            birthday = student.birthdate.toordinal()
        else:
            birthday = 1
        student_list.append([student.last_name, student.first_name, birthday])
    logging.info("Found %d students." %len(student_list))
    list.sort(student_list, key=lambda student:student[2])
    list.sort(student_list, key=lambda student:student[1])
    list.sort(student_list, key=lambda student:student[0])
    student_dict = {}
    matches = {}
    for student in student_list:
        key = student[0]
        if student_dict.has_key(key):
            matches[key] = 1
            student_dict[key].append(student)
        else:
            student_dict[key] = [student]
    sorted_matches = matches.keys()
    list.sort(sorted_matches)
    text = "Found %d matches %d dict entries." %(len(sorted_matches),
                                                       len(student_dict))
    logging.info(text)
    logger.add_line(text)
    logger.add_line('"Last Name","Birthday", "First Name"')
    try:
        for key in sorted_matches:
            logger.add_line('"---","%s","%d"' %(key, len(student_dict[key])))
            for student in student_dict[key]:
                text = '"%s","%s","%d"' %(student[0],
                        student[1],student[2])
                logging.info(text)
                logger.add_line(text)
    except StandardError, e:
        text = "Failed during print Error: %s" %e
        logging.info(text)
        logger.add_line(text)
    logging.info("Completed find_duplicate students")
    logger.add_line("Completed find_duplicate students")   

def get_duplicate_student_info(logger):
    """
    Return two lists of records from a list of student names.
    The first list is the records with "No current enrollment" as the
    status, the second is all other records.
    The student records are selected by query from the "test_list"
    which is inserted in this code uniquely each time this function is
    used. This assures that there is no problem with function argument length
    """
    #example test_list
    #test_list = [["Jones", "Ricky"],["Hendrix","Jimmy"]]
    test_list = []
    not_current_student_list = []
    enrolled_student_list = []
    other_student_list = []
    for name in test_list:
        query = SchoolDB.models.Student.all()
        query.filter("organization =", SchoolDB.models.getActiveOrganization())
        query.filter("last_name =", name[0])
        query.filter("first_name =", name[1])
        students = query.fetch(5)
        for student in students:
            if (not student.student_status):
                other_student_list.append(student)
            elif (student.student_status.name == "Not Currently Enrolled"):
                not_current_student_list.append(student)
            elif (student.student_status.name == "Enrolled"):
                enrolled_student_list.append(student)
            else:
                other_student_list.append(student)
    logging.info("%d not current" %len(not_current_student_list))
    logging.info("%d current" %len(enrolled_student_list))
    logging.info("%d other" %len(other_student_list))
    try:
        logger.add_line('"Last Name", "First Name","Change Date","Year Level"')
        for filtered_list, list_name in (
            (not_current_student_list, "Not Currently Enrolled"),
            (enrolled_student_list, "Currently Enrolled"),
            (other_student_list, "Other Status")):
            text = '"---->","%s"," "," "' %list_name
            logging.info(text)
            logger.add_line('" "," "," "," "')
            logger.add_line(text)
            logger.add_line('" "," "," "," "')
            for student in filtered_list:
                if student.student_status_change_date:
                    change_date = student.student_status_change_date.isoformat()
                else:
                    change_date = "?"
                text = '"%s","%s","%s","%s","%s","%s"' %(student.last_name, 
                        student.first_name, change_date,
                        student.class_year, student.student_status.name,
                        str(student.key()))
                logging.info(text)
                logger.add_line(text)
    except StandardError, e:
        text = "Failed during print Error: %s" %e
        logging.info(text)
        logger.add_line(text)
    text = "Completed get_duplicate_student_info"
    logging.info(text)
    logger.add_line(text)   

def remove_by_key(logger, keylist=[], perform_remove=False):
    """
    This is a dangerous action that will remove all entities that have
    a key in the remove_key_list. If perform_remove is false all
    entities that would be removed will report in the log but nothing
    will actually be removed. This function should be left commented
    out unless needed.
    """
    
    perform_remove=False
    text = "remove_by_key has been disabled in the code to prevent a dangerous mistake. Only the 'fake' removal will be performed to show what would have been deleted. If you need to actually delete some entities then edit the code to comment out these lines."
    logger.add_line(text)
    logging.error(text)    
    if not keylist:
        logger.add_line("Nothing to remove")
        return False
    if perform_remove:
        action_text = "starting"
    else:
        action_text = "simulating"
    text = ">>>remove_by_key %s removal of %d entities" \
         %(action_text,len(keylist))
    logging.info(text)
    logger.add_line(text)
    for key in keylist:
        try:
            entity = \
                   SchoolDB.utility_functions.get_instance_from_key_string(
                       key)
            if entity:
                do_nothing = True #empty value statement for fill
                #dont actually remove!!!
                #entity.remove(perform_remove)
        except StandardError, e:
            text = "Removal of an entity failed. Key: %s Error: %s" \
                 %(key, e)
            logging.info(text)
            logger.add_line(text)            
    if perform_remove:
        text = ">>>remove_by_key removal completed"
    else:
        text = '>>>simulated remove_by_key function completed'
    logging.info(text)
    logger.add_line(text)
    
def section_name_letter_case_cleanup(logger, section_name):
    """
    Change name letter casing to correct format. The students are
    chosen by section name to correct for sloppy teacher entry. This
    will probably be run very rarely because the initial correction is
    now working. Comment out or remove after a year.
    """
    section = SchoolDB.utility_functions.get_entities_by_name(
        SchoolDB.models.Section, section_name)
    change_count = 0
    query = SchoolDB.models.Student.all()
    query.filter("section =", section.key())
    for student in query:
        original_name = unicode(student)
        student.first_name = \
            SchoolDB.utility_functions.clean_up_letter_casing(
                student.first_name)
        student.middle_name = \
               SchoolDB.utility_functions.clean_up_letter_casing(
                   student.middle_name)
        student.last_name = \
               SchoolDB.utility_functions.clean_up_letter_casing(
                   student.last_name)
        #save only if changes
        new_name = unicode(student)
        if (new_name != original_name):
            change_count += 1
            student.put()   
            logging.info("Changed name '%s' to '%s'" \
                         %(original_name, new_name))
    result = "Fixed %d names" %change_count
    logging.info(result)
    logger.add_line(result)
            
def create_new_attendance_record(student_keystring):
    """
    Create a new attendance record for a student.
    """
    try:
        student = SchoolDB.utility_functions.get_instance_from_key_string(
            student_keystring)
        start_date = datetime.date(2011,6,6)
        student.attendance = SchoolDB.models.StudentAttendanceRecord.create(
            parent_entity = student, start_date = start_date)
        student.put()
        return True
    except StandardError, e:
        info = "New attendance record failed %s" %e
        logging.error(info)
        return False

def create_new_attendance_records_utility(logger):
    """
    Generate tasks using the function "create_new_attendance_records"
    to create a new attendance record for every student. This assumes
    that all old attendance records have been deleted. This will work
    across all schools - it is designed for a simple hard replace action
    on a test database. >>Do NOT use on live database!<<
    """
    try:
        logger.add_line("starting creation of attendance records")
        query = SchoolDB.models.Student.all(keys_only=True)
        task_generator = SchoolDB.assistant_classes.TaskGenerator(
        task_name="Create New Attendance Records",
                             function = 
        "SchoolDB.local_utilities_functions.create_new_attendance_record", 
               function_args="", query_iterator=query,
               instances_per_task=10)
        successful, result_string = task_generator.queue_tasks()
        return result_string
    except StandardError, e:
        return "Failed: %s" %e

def generate_sample_grades(count, max_value = 100, round_result=True, 
                           pilot_section=False):
    """
    Use a weibull distribution to generate a sample set of grades. This
    will create count values with a maximum value max value, and, if
    integer_value is true then the grades will be only integer values.
    The value is initially computed without rounding on a 0 -100 basis
    with an offset of 75 so that most will pass. The multiplier is used
    to have a 4% probablility that the result is above 100 which is
    converted to a failing grade by subtracting 2 * the excess above
    100 from 70. Finally it is scaled and, if necessary, converted to
    integer. If pilot section then dstribution is changed to give higher grades
    """
    #for test we may want a standard set of "random" values that can be
    #generated with a fixed seed. Leave the next line commented out normally
    #random.seed(1)
    grades_list = []
    passing_grade = 75.0
    multiplier = 8.0
    weibull_scale_factor = 1.5
    if pilot_section:
        multiplier = 11.0
        weibull_scale_factor = 4.0       
    working_range = 100.0 - passing_grade
    for i in xrange(count):
        wb_value = random.weibullvariate(1.3, weibull_scale_factor) * multiplier
        if (wb_value < working_range):
            raw_grade = passing_grade + wb_value
        elif pilot_section:
            #just innvert the excess -- it keeps the grades high and does
            #not allow failure
            delta = wb_value - working_range
            raw_grade = 100.0 - delta           
        else:
            #convert to failing grade
            delta = wb_value - working_range
            raw_grade = passing_grade - delta
        grade = raw_grade * max_value/100.0
        if (round_result):
            grade = round(grade)
        grades_list.append(grade)
    return grades_list

def generate_artificial_grades(grades_table, grading_instances_list, 
                               round_result = True,  pilot_section = False):
    """
    Emulate the web page in loading the grading table, filling in values,
    and then sending it back. The only real action to be done in this function
    is setting each element of the raw data array to a generated grade.
    """
    #grades_table is a 2D array with the primary index as row (a student)
    #and the secondary index as column (grading_instance) grades
    #generated by grading instance because each gdinst may have a
    #different max value
    rows = len(grades_table)
    cols = len(grades_table[0])
    for gdinst in xrange(cols):
        grades_list = generate_sample_grades(rows, 
                        grading_instances_list[gdinst].number_questions,
                        round_result, pilot_section)    
        for student in xrange(rows):
                grades_table[student][gdinst] = grades_list[student]
    return grades_table
    
def insert_artificial_grades(grading_instances_keys, student_group,
                             grading_instances_owner, achievement_test = False,
                             round_result = True, pilot_section = False):
    """
    Fill in grades with artificial values for test and demonstration.
    This uses the ajax base grade handlers just connected back to back.
    The AjaxGetGradeHandler generates the infomation about the students
    grading entities, fake grades are inserted, and then
    AjaxSetGradeHandler records them. This acts like the web page to
    fill in the values. The grading_instances_keys are list of all
    grading instances to be handeled. The student group is the class
    session or, for achv test, the section. The grading instances owner
    is ether the class session or the achievement test. If
    pilot_section is true then a slightly different grading
    distribution is used to generate somewhat better grades.
    """
    try:
        #generate json to give to the GetGradesHandler
        json_gi_key_strings = simplejson.dumps([str(key) for key in
                                                grading_instances_keys])
        achievement_test_keystr = str(grading_instances_owner.key())
        json_req_data = {"requested_action":"full_package",
                         "achievement_test":achievement_test_keystr,
                         "gi_keys":json_gi_key_strings}
        json_req = simplejson.dumps(json_req_data)                     
        #Use GetGradesHandler to generate the tables
        get_grades_handler = SchoolDB.assistant_classes.AjaxGetGradeHandler(
            student_group, json_req)
        table_header, grading_instances_list, student_keystrs,\
                    student_record_data, grades_table = \
                    get_grades_handler.create_raw_information()
        # all arrays have a first column that is either empty or a name -- strip
        grading_instances_list.pop(0)
        for i in xrange(len(grades_table)):
            grades_table[i].pop(0)
        #process the table to fill in grades with fake grades
        grades_table = generate_artificial_grades(grades_table, 
                        grading_instances_list, round_result, pilot_section)    
        gi_key_strings = [str(gi.key()) for gi in grading_instances_list]
        # use SetGradesHandler to set the grades
        grade_handler = SchoolDB.assistant_classes.AjaxSetGradeHandler(
            student_grouping = student_group, 
            gi_owner = grading_instances_owner,
            gi_key_strings = gi_key_strings,
            student_record_key_strings = student_keystrs,
            grades_table = grades_table,
            student_class_records_table = student_record_data,
            gi_changes = None)
        grade_handler.service_request()
        return len(grades_table)
    except StandardError, e:
        logging.error('insert_artificial_grades failed for section "%s": %s' \
                      %(unicode(student_group), e))
        return 0
    
def fake_at_grades(section_keystr, achievement_test_keystr):
    """
    
    """
    try:
        section = SchoolDB.utility_functions.get_instance_from_key_string(
            section_keystr,SchoolDB.models.Section)
        achievement_test = SchoolDB.utility_functions.get_instance_from_key_string(
            achievement_test_keystr,SchoolDB.models.AchievementTest)
        pilot_section = (section.section_type == 
                         SchoolDB.utility_functions.get_entities_by_name(
                             SchoolDB.models.SectionType, "Pilot"))
        grading_instances = achievement_test.get_grading_instances(section)
        grading_instances_keys = [gi.key() for gi in grading_instances]
        number_graded = insert_artificial_grades(grading_instances_keys = \
                grading_instances_keys,
                student_group=section, grading_instances_owner=achievement_test,
                achievement_test = True, pilot_section = pilot_section)
        if number_graded:
            logging.info( \
                'Fake AppTest grades set %d grades for %d students in section "%s"'
                %(len(grading_instances), number_graded, unicode(section)))
            return number_graded
    except StandardError, e:
        logging.error('fake_at_grades failed for section "%s": %s' \
                      %(unicode(section), e))
        return 0
                             
def fake_gp_grades(class_session_keystr, grading_period_keystr):
    """
    Create fake grades for a single grading period for a single class session.
    """
    try:
        class_session = SchoolDB.utility_functions.get_instance_from_key_string(
            class_session_keystr, SchoolDB.models.ClassSession)
        student_records = class_session.get_student_class_records()
        students = class_session.get_students_from_records(student_records)   
        #create fake data
        student_keystr_array = [str(student.key()) for student in students]
        gp_array = [grading_period_keystr]
        #create fake data
        grades_array = [[gd] for gd in generate_sample_grades(len(students))]
        results_table = {"columns":gp_array, "data":grades_array, 
                         "keys":student_keystr_array}
        gp_handler = SchoolDB.assistant_classes.GradingPeriodGradesHandler(
            class_session = class_session, edit_grading_periods=gp_array,        
                     view_grading_periods=[], students=[], 
                     results_table=results_table)
        gp_handler.set_grades()
        logging.info('Fake GP grades set for %d students in class "%s" for grading period "%s"' \
                     %(len(students), unicode(class_session),
                       unicode(SchoolDB.utility_functions.get_instance_from_key_string(grading_period_keystr))))
        return True
    except StandardError, e:
        logging.error('fake_gp_grades failed for class "%s": %s'\
                      %(unicode(class_session), e))
        return False
        

def create_fake_at_grades(class_year, achievement_test_keystr):
    """
    Create tasks to create fake grades on achievement test for every section 
    in the class year at the school.
    """
    #Confirm that this class year has taken the achievement test
    try:
        achievement_test = SchoolDB.models.get_instance_from_key_string(
            achievement_test_keystr, SchoolDB.models.AchievementTest)
        achievement_test.class_years.index(class_year)
        #will throw exception if class year not in list
        query = SchoolDB.models.Section.all()
        query.filter("class_year =", class_year)
        query.filter("organization =", SchoolDB.models.getActiveOrganization())
        for section in query:
            function_args='section_keystr="%s", achievement_test_keystr="%s"' \
                         %(str(section.key()), achievement_test_keystr)
            task_generator =SchoolDB.assistant_classes.TaskGenerator(
                        task_name="fake_at_grades", function = 
                        "SchoolDB.local_utilities_functions.fake_at_grades", 
                        function_args=function_args, rerun_if_failed=False)
            successful, result_string = task_generator.queue_tasks()
            logging.info("Queued achievement test fake grades for %s",
                         unicode(section))
        logging.info("All fake grades enqueued")
    except ValueError:
            logging.warning(\
                "Achievement test %s was not taken by %s. No action performed." \
                %(unicode(achievement_test), class_year))


def create_fake_gp_grades(class_year, grading_period_name):
    """
    Set fake grades for grading period. This uses a completly different set of software than achievement tests to get and set grades. The two parts are:
    """
    grading_period = SchoolDB.utility_functions.get_entities_by_name(
        SchoolDB.models.GradingPeriod, "First Grading Period")
    grading_period_keystr = str(grading_period.key())
    query = SchoolDB.models.ClassSession.all()
    query.filter("organization =", SchoolDB.models.getActiveOrganization())
    query.filter("class_year =", class_year)
    for class_session in query:
        class_session_keystr = str(class_session.key())
        function_args = 'class_session_keystr="%s", grading_period_keystr="%s"' \
                      %(class_session_keystr, grading_period_keystr)
        task_generator =SchoolDB.assistant_classes.TaskGenerator(
                    task_name="fake_gp_grades", function = 
                    "SchoolDB.local_utilities_functions.fake_gp_grades", 
                    function_args=function_args, rerun_if_failed=False)
        successful, result_string = task_generator.queue_tasks()
        logging.info("Queued grading period fake grades for %s",
                         unicode(class_session))
    logging.info("All fake grades enqueued")
        


def dump_student_info_to_email(logger, class_year, email_address):
    """ 
    Write the basic student information for all students in a class
    year at a school to a csv file and mail as an attachment to the
    email address. This is meant to be used in local applications such
    as prefilled registration forms. The data has only the string
    values not the keys. This is performed as a task so that the 30
    second time limit does not apply. 
    This function is called by the user to set up the task.
    """
    memcache_key = "CSV-Student-Dump-%s-%s-%s" \
        %( SchoolDB.models.getActiveDatabaseUser().get_active_organization_name(),
           class_year, datetime.datetime.now().isoformat())
    memcache.set(memcache_key, "")
    args = 'class_year="%s", email_address="%s", memcache_key="%s", last_count=%d' %(class_year, email_address,memcache_key,0)
    task_generator = SchoolDB.assistant_classes.TaskGenerator(
        task_name = "Dump Student Info to Email", function=
        "SchoolDB.local_utilities_functions.dump_student_info_to_email_task",
        function_args=args, rerun_if_failed=False)
    task_generator.queue_tasks()
    
    
def dump_student_info_to_email_task_ascii(class_year, email_address, memcache_key,
                                    last_count):
    """ Write the basic student information for all students in a class
    year at a school to a csv file and mail as an attachment to the
    email address. This is meant to be used in local applications such
    as prefilled registration forms. The data has only the string
    values not the keys. This is performed as a task so that the 30
    second time limit does not apply.
    This is the task function that actually does the work. It chains itself to perform the scan across all students.
    """
    try:
        csv_file = StringIO.StringIO()
        csv_filename = class_year+"StudentInfo.csv"
        csv_field_names = [
            "first_name", "middle_name", "last_name", "gender", "address",
            "municipality", "barangay", "birthdate", 
            "siblings",
            "p1name", "p1relationship", "p1occupation", "p1cell_phone",
            "p1email",
            "p2name", "p2relationship", "p2occupation", "p2cell_phone",
            "p2email",
            "cell_phone", "email", "student_id", "class_year", "student_major",
            "balik_aral",
            "birth_province", "birth_municipality", "birth_barangay",
            "elementary_school", "elementary_graduation_date",
            "elementary_gpa", "years_in_elementary"]
        
        task_count = 0
        block_size = 30
        writer = csv.DictWriter(csv_file, csv_field_names)
        val_dict = {}        
        if (last_count == 0):
            #create header row
            for s in csv_field_names:
                val_dict[s] = s
            writer.writerow(val_dict)
        query = SchoolDB.models.Student.all()
        query.filter("organization =", SchoolDB.models.getActiveOrganization())
        query.filter("class_year =", class_year)
        SchoolDB.models.active_student_filter(query)
        students = query.fetch(block_size, offset=last_count)
        for student in students:
            for s in csv_field_names:
                val_dict[s] = ""
            val_dict["first_name"]=student.first_name
            val_dict["middle_name"]=student.middle_name
            val_dict["last_name"]=student.last_name
            val_dict["gender"]=student.gender
            val_dict["address"]=unicode(student.address)
            val_dict["municipality"]=unicode(student.municipality)
            val_dict["barangay"]=unicode(student.community)
            val_dict["birthdate"]=unicode(student.birthdate)
            sib_string = ""
            for sibling in student.get_siblings():
                if (sibling.key() != student.key()):
                    sib_string += (unicode(sibling) + ", ")
            val_dict["siblings"]=sib_string
            p_list = student.get_parents()
            if p_list:
                p = p_list[0]
                val_dict["p1name"]=unicode(p)
                val_dict["p1relationship"]=unicode(p.relationship)
                val_dict["p1occupation"]=unicode(p.occupation)
                val_dict["p1cell_phone"]=unicode(p.cell_phone)
                val_dict["p1email"]=unicode(p.email)
            if (len(p_list) > 1):
                p = p_list[1]
                val_dict["p2name"]=unicode(p)
                val_dict["p2relationship"]=unicode(p.relationship)
                val_dict["p2occupation"]=unicode(p.occupation)
                val_dict["p2cell_phone"]=unicode(p.cell_phone)
                val_dict["p2email"]=unicode(p.email)
            val_dict["cell_phone"]=unicode(student.cell_phone)
            val_dict["email"]=unicode(student.email)
            val_dict["student_id"]=unicode(student.student_id)
            val_dict["class_year"]=unicode(student.class_year)
            val_dict["student_major"]=unicode(student.student_major)
            val_dict["birth_province"]= unicode(student.birth_province)
            if student.birth_municipality:
                val_dict["birth_municipality"]=\
                        unicode(student.birth_municipality)
            else:
                val_dict["birth_municipality"]=unicode(student.birth_municipality_other)
            if student.birth_community:
                val_dict["birth_barangay"]=unicode(student.birth_community)
            else:
                val_dict["birth_barangay"]=unicode(student.birth_community_other)
            val_dict["elementary_school"]=unicode(student.elementary_school)
            val_dict["elementary_graduation_date"]=\
                    unicode(student.elementary_graduation_date)
            val_dict["elementary_gpa"]=unicode(student.elementary_gpa)
            val_dict["years_in_elementary"]=unicode(student.years_in_elementary)
            for key,value in val_dict.items():
                if (value == "None"):
                    val_dict[key] = ""
            writer.writerow(val_dict)
            task_count += 1
        memcached_data = memcache.get(memcache_key)
        memcached_data += csv_file.getvalue()
        memcache.set(memcache_key, memcached_data)
        last_count += task_count
        logging.info("Wrote %d student records to memcache. Total count:%d"
                     %(task_count, last_count))
        if (task_count == block_size):
            #Completely filled request. Probably more left so chain
            #another task.
            args = 'class_year="%s", email_address="%s", memcache_key="%s", last_count=%d' \
                 %(class_year, email_address,memcache_key,last_count)
            task_generator = SchoolDB.assistant_classes.TaskGenerator(
                task_name = "Dump Student Info to Email", function=
                "SchoolDB.local_utilities_functions.dump_student_info_to_email_task",
                function_args=args, rerun_if_failed=False)
            task_generator.queue_tasks()             
        if (task_count < block_size):
            # we are at the end. Send email
            logging.info("All completed. Sending mail to %s" %email_address)
            message = mail.EmailMessage(
                sender="Philippines School Database <nrbierb@gmail.com>",
                subject="Requested Student Information for " + class_year)   
            message.to = email_address
            message.body = """
            Here is the information you requested about the %s students
            at %s. 
            The attachment is a csv file that can be opened in a spreadsheet.
            """
            message.attachments = (csv_filename, memcached_data)
            message.send()
            logging.info("Email with file sent to %s" %email_address)
            memcache.delete(memcache_key)
        return True
    except StandardError, e:
        logging.error("Failed to generate requested student csv info to %s: %s"
                      %(email_address, e))
        return False
    
class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

def dump_student_info_to_email_task(class_year, email_address, memcache_key,
                                    last_count):
    """ Write the basic student information for all students in a class
    year at a school to a csv file and mail as an attachment to the
    email address. This is meant to be used in local applications such
    as prefilled registration forms. The data has only the string
    values not the keys. This is performed as a task so that the 30
    second time limit does not apply.
    This is the task function that actually does the work. It chains itself to perform the scan across all students.
    """
    try:
        csv_file = StringIO.StringIO()
        csv_filename = class_year+"StudentInfo.csv"
        csv_field_names = [
            "first_name", "middle_name", "last_name", "gender", "address",
            "municipality", "barangay", "birthdate", 
            "siblings",
            "p1name", "p1relationship", "p1occupation", "p1cell_phone",
            "p1email",
            "p2name", "p2relationship", "p2occupation", "p2cell_phone",
            "p2email",
            "cell_phone", "email", "student_id", "class_year", "student_major",
            "balik_aral",
            "birth_province", "birth_municipality", "birth_barangay",
            "elementary_school", "elementary_graduation_date",
            "elementary_gpa", "years_in_elementary"]
        
        task_count = 0
        block_size = 30
        writer = UnicodeWriter(csv_file, csv_field_names)
        val_dict = {}        
        if (last_count == 0):
            #create header row
            row = []
            for s in csv_field_names:
                row.append(s)
            writer.writerow(row)
        query = SchoolDB.models.Student.all()
        query.filter("organization =", SchoolDB.models.getActiveOrganization())
        query.filter("class_year =", class_year)
        SchoolDB.models.active_student_filter(query)
        students = query.fetch(block_size, offset=last_count)
        for student in students:
            for s in csv_field_names:
                val_dict[s] = ""
            val_dict["first_name"]=student.first_name
            val_dict["middle_name"]=student.middle_name
            val_dict["last_name"]=student.last_name
            val_dict["gender"]=student.gender
            val_dict["address"]=unicode(student.address)
            val_dict["municipality"]=unicode(student.municipality)
            val_dict["barangay"]=unicode(student.community)
            val_dict["birthdate"]=unicode(student.birthdate)
            sib_string = ""
            for sibling in student.get_siblings():
                if (sibling.key() != student.key()):
                    sib_string += (unicode(sibling) + ", ")
            val_dict["siblings"]=sib_string
            p_list = student.get_parents()
            if p_list:
                p = p_list[0]
                val_dict["p1name"]=unicode(p)
                val_dict["p1relationship"]=unicode(p.relationship)
                val_dict["p1occupation"]=unicode(p.occupation)
                val_dict["p1cell_phone"]=unicode(p.cell_phone)
                val_dict["p1email"]=unicode(p.email)
            if (len(p_list) > 1):
                p = p_list[1]
                val_dict["p2name"]=unicode(p)
                val_dict["p2relationship"]=unicode(p.relationship)
                val_dict["p2occupation"]=unicode(p.occupation)
                val_dict["p2cell_phone"]=unicode(p.cell_phone)
                val_dict["p2email"]=unicode(p.email)
            val_dict["cell_phone"]=unicode(student.cell_phone)
            val_dict["email"]=unicode(student.email)
            val_dict["student_id"]=unicode(student.student_id)
            val_dict["class_year"]=unicode(student.class_year)
            val_dict["student_major"]=unicode(student.student_major)
            val_dict["birth_province"]= unicode(student.birth_province)
            if student.birth_municipality:
                val_dict["birth_municipality"]=\
                        unicode(student.birth_municipality)
            else:
                val_dict["birth_municipality"]=unicode(student.birth_municipality_other)
            if student.birth_community:
                val_dict["birth_barangay"]=unicode(student.birth_community)
            else:
                val_dict["birth_barangay"]=unicode(student.birth_community_other)
            val_dict["elementary_school"]=unicode(student.elementary_school)
            val_dict["elementary_graduation_date"]=\
                    unicode(student.elementary_graduation_date)
            val_dict["elementary_gpa"]=unicode(student.elementary_gpa)
            val_dict["years_in_elementary"]=unicode(student.years_in_elementary)
            for key,value in val_dict.items():
                value = value.strip()
                if ((value == "None") or (value == "none")):
                    val_dict[key] = ""
            row = [val_dict[name].strip() for name in csv_field_names]
            writer.writerow(row)
            task_count += 1
        memcached_data = memcache.get(memcache_key)
        memcached_data += csv_file.getvalue()
        memcache.set(memcache_key, memcached_data)
        last_count += task_count
        logging.info("Wrote %d student records to memcache. Total count:%d"
                     %(task_count, last_count))
        if (task_count == block_size):
            #Completely filled request. Probably more left so chain
            #another task.
            args = 'class_year="%s", email_address="%s", memcache_key="%s", last_count=%d' \
                 %(class_year, email_address,memcache_key,last_count)
            task_generator = SchoolDB.assistant_classes.TaskGenerator(
                task_name = "Dump Student Info to Email", function=
                "SchoolDB.local_utilities_functions.dump_student_info_to_email_task",
                function_args=args, rerun_if_failed=False)
            task_generator.queue_tasks()             
        if (task_count < block_size):
            # we are at the end. Send email
            logging.info("All completed. %d students processed.Sending mail to %s" %(last_count, email_address))
            message = mail.EmailMessage(
                sender="Philippines School Database <nrbierb@gmail.com>",
                subject="Requested Student Information for " + class_year)   
            message.to = email_address
            message.body = """
            Here is the information you requested about the %s students
            at %s. This is from version 1.1.
            The attachment is a csv file that can be opened in a spreadsheet.
            """ %(class_year, unicode(SchoolDB.models.getActiveOrganization()))
            message.attachments = (csv_filename, memcached_data)
            message.send()
            logging.info("Email with file sent to %s" %email_address)
            memcache.delete(memcache_key)
        return True
    except StandardError, e:
        logging.error("Failed to generate requested student csv info to %s: %s"
                      %(email_address, e))
        return False

