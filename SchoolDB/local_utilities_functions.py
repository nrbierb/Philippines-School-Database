import cPickle, zlib, datetime, base64
import logging
import SchoolDB.models

"""
Utilities that are normally used as scheduled jobs or called from the 
"Run Utility" web page. 
"""
#def send_task(task_dict):
    #"""
    #Prepare task for sending by pickling and compressing all parameters.
    #Then add task to queue.
    #"""
    #packed = zlib.compress(cPickle.dumps(task_dict))
    #encoded = base64.b64encode(packed)
    #params_dict = {"task_data":encoded}
    #taskqueue.add(url="/task", params=params_dict) 
    
##----------------------------------------------------------------------
#def queue_tasks(task_name, function, function_args="", 
                #organization = None, instance_keylist = None,
                #query_iterator = None, instances_per_task = 10,
                #rerun_if_failed = True):
    #"""
    #The primary function for creating and queuing tasks. This will create one
    #or more tasks.
    #-task_name, function, and function_args must be specified.
    #-org: The keystring for the org that will be active for the task. If not
     #defined then the caller's organization will be used.
    #-instance_keylist: The list of keys for instances that should be 
      #processed by the function
    #-query_iterator: alternate to the keylist, it uses the keys_only query.
     #Note: only one of the above should be defined
    #-instances per task: if there is an instance_keylist this is the number of
     #instances to be process by a single task. It the total length of the 
     #instance keylist is greater than this then multiple tasks will be queued.
     #"""
    #try:
        #task_dict = {"task_name":task_name, "function":function, 
                     #"args":function_args, "organization":organization,
                     #"rerun_if_failed":rerun_if_failed}
        #task_count = 0
        #if instance_keylist:
            #block_end = instances_per_task - 1
            #while instance_keylist:
                #task_keylist = instance_keylist[0:block_end]
                #task_dict["target_instances"] = task_keylist
                #send_task(task_dict)
                #del instance_keylist[0:block_end]
        #elif query_iterator:
            #keys_blocks = SchoolDB.models.get_blocks_from_iterative_query(
                #query_iterator, instances_per_task)
            #for block in keys_blocks:
                #keystring_block = [str(key) for key in block]
                #task_dict["target_instances"] = keystring_block
                #send_task(task_dict) 
                #task_count += 1
        #else:
            #send_task(task_dict)
            #task_count = 1
        #return "%d tasks successfully enqueued." %task_count
    #except StandardError, e:
        #return ("Failed after enqueueing %d tasks. Error: %s" 
                #%(task_count, e))
                
#----------------------------------------------------------------------

#def bulk_update(model_class, filter_parameters, change_parameters):
    #"""
    #Change the value of a parameter for all class objects that meet the
    #filter specification. This may be used with a parameter that uses an
    #associated history. The filtering is done with
    #SchoolDB.assistant_classes.QueryMaker object.
    
    #The arguments are:
    
    #-model_class: The class of the object to be changed.
    
    #-filter_parameters: This is a direct pass through to the QueryMaker object.
    #See documentation on that class for details.
    
    #-change_parameters: a dictionary keyed with the following values
    #1. changed_parameter
    #2. new_value
    #If parameter has associated history:
    #3. change_date
    #4. date_parameter
    #5. history_parameter
    #6. value_is_reference
    #If the changed_parameter does not have a history then dictionary entries 3-5 
    #need not be defined.
    #"""
    #try:
        #if (change_parameters.has_key("changed_parameter") and
                 #change_parameters.has_key("new_value") and model_class):
            ##if these aren't defined do nothing...
            #qmkr_desc = SchoolDB.assistant_classes.QueryDescriptor()
            #qmkr_desc.set("filters", filter_parameters)
            #qmkr_desc.set("maximum_count", 4000)
            #qmkr_query = SchoolDB.assistant_classes.QueryMaker(
                #model_class, qmkr_desc)
            #object_list = qmkr_query.get_objects()
            #for obj in object_list:
                #setattr(obj, change_parameters["changed_parameter"],
                        #change_parameters["new_value"])
                #if (change_parameters.has_key("change_date")):
                    #if (change_parameters.has_key("date_parameter")):
                        #setattr(obj, change_parameters["date_parameter"],
                                #change_parameters["change_date"])
                    #if (change_parameters.has_key("history_parameter")):
                        #history = getattr(obj, 
                                    #change_parameters["history_parameter"])
                        #is_reference = change_parameters.get(
                            #"value_is_reference", False)
                        #if (is_reference):
                            #string_val = ""
                            #ref_val = change_parameters["new_value"]
                        #else:
                            #string_val = change_parameters["new_value"]
                            #ref_val = None
                        #history.add_or_change_entry_if_changed(
                            #start_date=change_parameters["change_date"],
                            #info_str=string_val, info_reference= ref_val)
                #obj.put()
            #return ("Changed %d %s objects"
                    #%(len(object_list), model_class.classname))
        #else:
            #return ("Unusable args. Nothing changed")
        ##change error type after debugging
    #except EOFError, e:
        #return "Failed Bulk Update: %s" %e

#def bulk_update_utility(logger, model_class, filter_parameters, 
                        #change_parameters):
    #"""
    #Call bulk_update with logging.
    #"""
    #org_name = \
        #SchoolDB.models.getActiveDatabaseUser().get_active_organization_name()
    #org_type = \
        #SchoolDB.models.getActiveDatabaseUser().get_active_organization_type()
    #logger.add_line("Starting Bulk Update on %s %s:" %(org_type,org_name))
    #logger.add_line("Model Class: " + model_class.classname)
    #logger.add_line("Filter Parameters: " + str(filter_parameters))
    #logger.add_line("Change Parameters: " + str(change_parameters))
    #result = bulk_update(model_class, filter_parameters, 
                         #change_parameters)
    #logger.add_line("Result: " + result)
    

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
    
def create_new_attendance_record(student):
    """
    Create a new attendance record for a student.
    """
    try:
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
