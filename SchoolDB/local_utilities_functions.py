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

import cPickle, zlib, datetime, base64
import logging
import SchoolDB.models


def change_parameter(obj, change_parameters):
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
    If parameter has associated history:
    3. change_date
    4. date_parameter
    5. history_parameter
    6. value_is_reference
    If the changed_parameter does not have a history then dictionary entries 3-5 
    need not be defined. 
    """ 
    try:
        setattr(obj, change_parameters["changed_parameter"],
            change_parameters["new_value"])
        if (change_parameters.has_key("change_date")):
            if (change_parameters.has_key("date_parameter")):
                setattr(obj, change_parameters["date_parameter"],
                        change_parameters["change_date"])
            if (change_parameters.has_key("history_parameter")):
                history = getattr(obj, 
                            change_parameters["history_parameter"])
                is_reference = change_parameters.get(
                    "value_is_reference", False)
                if (is_reference):
                    string_val = ""
                    ref_val = change_parameters["new_value"]
                else:
                    string_val = change_parameters["new_value"]
                    ref_val = None
                history.add_or_change_entry_if_changed(
                    start_date=change_parameters["change_date"],
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
    If the changed_parameter does not have a history then dictionary entries 3-5 
    need not be defined.
    
    This utility function uses tasks to perform the actions so there is no 
    worry about exceeding the time limit or cousing long wait times for the 
    caller. It also uses the query iterator so there is no worry about the 
    number of instances.
    """
    try:
        if (change_parameters.has_key("changed_parameter") and
                 change_parameters.has_key("new_value") and model_class):
            #if these aren't defined do nothing...
            qmkr_desc = SchoolDB.assistant_classes.QueryDescriptor()
            qmkr_desc.set("filters", filter_parameters)
            qmkr_desc.set("return_iterator", True)
            qmkr_desc.set("keys_only", True)
            qmkr_query = SchoolDB.assistant_classes.QueryMaker(
                model_class, qmkr_desc)
            query_iterator = qmkr_query.get_objects()
            if query_iterator:
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

#----------------------------------------------------------------------

def update_student_summary(force = False):
    """
    The utility function called as a scheduled job to perform an update
    on school student summary records. The caller must belong to a school
    organization.
    """
    try:
        organization = \
            SchoolDB.models.getActiveDatabaseUser().get_active_organization()
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
            task_generator = SchoolDB.assistant_classes.TaskGenerator(
                task_name="Update Student Summary", function=
                "SchoolDB.local_utilities_functions.update_student_summary",
                function_args=force, organization=org_keystring)
            task_generator.queue_tasks()

def update_student_summary_utility(logger, encompassing_organization=None,
                                   force = False):
    """
    A trivial wrapper for call from utilrequest webpage
    """
    update_student_summary_by_task(encompassing_organization, force)
    logger.add_line("Queued all")
    
#----------------------------------------------------------------------
# Specific limited purpose utilities

def bulk_student_status_change_utilty(logger, class_year, 
                    prior_status_name, prior_status_oldest_change_date, 
                    new_status_name, change_date = None, year_end = True,
                    organization=None):
    """
    Change the student status for students of a single class year to
    the status with name "new_status_name" with the date "date". If
    date is none then the end or the beginning of the school year is
    used.The date to determine the school year is adjusted to allow
    this to be used three weeks before or after the actual year.
    """
    logger.add_line("Starting change of student status.")
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
            SchoolDB.models.get_entities_by_name(SchoolDB.models.StudentStatus, new_status_name)[0]
    if (prior_student_status_object and new_student_status_object):
        model_class = SchoolDB.models.Student
        query_filters = [("class_year = ", class_year),
                         ("student_status = ", prior_student_status_object),
                         ("student_status_change_date >", 
                          prior_status_oldest_change_date)
                          ]
        change_parameters = {"changed_parameter":"student_status",
                             "new_value":new_student_status_object,
                             "change_date":change_date,
                             "date_parameter":"student_status_change_date",
                             "history_parameter":"student_status_history",
                             "value_is_reference":True}
        bulk_update_by_task(model_class, query_filters, 
                            change_parameters, organization=organization)
    
def create_new_attendance_record(student_keystring):
    """
    Create a new attendance record for a student.
    """
    try:
        student = SchoolDB.utility_functions.get_instance_from_key_string(
            student_keystring)
        start_date = datetime.date(2011,1,1)
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
    across all schools - it is desiged for a simple hard replace action
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
