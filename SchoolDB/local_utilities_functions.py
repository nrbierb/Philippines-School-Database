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

import cPickle, zlib, datetime, random, logging, csv, StringIO, codecs
from django.utils import simplejson
from google.appengine.api import mail
from google.appengine.api import memcache

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

#----------------------------------------------------------------------

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
 
def update_section_initial_student_counts(logger=None):
    try:
        organization = \
            SchoolDB.models.getActiveOrganization()
        if (organization.classname == "School"):
            query = SchoolDB.models.Section.all()
            query.filter("organization =", organization)
            query.filter("termination_date =", None)
            sections = query.fetch(200)
            for section in sections:
                section.save_student_count()
                logging.info("Updated section '%s' students list"
                             %unicode(section))
            logging.info("Completed section_prior_list_update for all sections in school '%s'" %unicode(organization))
            return True
        else:
            logging.error("The organization '%s' is not a school so there are no sections to update." %unicode(organization))
            #It was not successful but should not be run again because it 
            #will continue to fail.
            return True
        #change error type after debugging
    except EOFError, e:
        logging.error("Failed Update Student Summary %s" %e)
        return False
                    
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
                            prior_status_name = "Not Currently Enrolled", 
                            new_status_name="Enrolled",
                            change_date = datetime.date(2011,3,31))
        logging.info("Called bulk for " + class_year)
    bulk_student_status_change_utility(logger, "Fourth Year", 
                            prior_status_name = "Enrolled", 
                            new_status_name="Graduated",
                            change_date = datetime.date(2011,3,30))
    logging.info("Called bulk for Fourth Year")
    logging.info("All bulk called")
                            
    
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

