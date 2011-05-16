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
Primary file internet direct view pages. It makes extensive use of the
Django web software.
"""
import binascii

import os, urlparse, sys, re, datetime
import cPickle, zlib, base64
from datetime import date, datetime
import logging
import exceptions
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.db import djangoforms
from django import http
from django import shortcuts
from django.contrib.admin import widgets
from django.contrib.formtools.preview import FormPreview
from django import forms
from django import core
import django.template
from django.utils import simplejson
from django.utils import text
from django.utils.safestring import mark_safe
from SchoolDB.models import *
import SchoolDB.ajax
import SchoolDB.choices
import SchoolDB.reports
import SchoolDB.assistant_classes
import SchoolDB.local_utilities_functions
import SchoolDB.system_management
from SchoolDB.local_utilities_functions import bulk_student_status_change_utilty
from SchoolDB.local_utilities_functions import update_student_summary_utility
from SchoolDB.utilities.empty_database import empty_database
from SchoolDB.utilities import load_students
from SchoolDB.utilities.low_level_utils import delete_student
from SchoolDB.utilities.update_database_user_types \
     import update_database_user_types
from SchoolDB.utilities.convert_histories import convert_histories
from SchoolDB.utilities.add_student_major_history import \
     add_student_major_history, clear_student_major_histories, \
     assign_student_majors_for_test_database
from SchoolDB.utilities.create_schooldays import create_schooldays
from SchoolDB.utilities.createStudents import create_students_for_school
from SchoolDB.utilities.replace_histories import replace_histories

import SchoolDB.utilities
result_string = ""
__http_request__ = None
__processed_request__ = None
__revision_id__ = \
"Version: 1--0-13 " + datetime.now().strftime("%m/%d/%y %I:%M%p")

def validate_user(request, auto_task=False):
    """
    The decorator used before all url actions to determine action based
    upon the user making the request. First it tests if a user has
    logged in and if not redirects to a login page. If the user has
    logged in then the account information is queried from the database
    for the registered users. If the logged in user cannot be found in
    the DatabaseUser records then there is an immediate return of a 505
    permission denied page. If the record is present then the class of
    the user is fetched to determine the permissions which are compared
    to the permission required for the access to this page. If the
    user's class does not permit the action then a slightly different
    505 page is returned to show that that particular action is not
    allowed. Only if all tests are passed will the actual url handler
    function be called.
    """
    
    #get logged in user
    user = users.get_current_user()
    if (not user):
    # There should always be a logged in user because "login: required"
    # is set in the app.yaml file but still confirm and redirect if
    # necessary
        response = http.HttpResponseForbidden("Must be logged in to use")
        return response
    query = db.Query(SchoolDB.models.DatabaseUser)
    query.filter("user = ", user)
    current_user = query.get()
    if ((not current_user) and (not users.is_current_user_admin())):
        raise ProhibitedUserError, user
    #tasks from cron jobs and task queues may only be run by admins
    if (auto_task and not users.is_current_user_admin()):
        raise ProhibitedUserError, user        
    SchoolDB.models.setActiveDatabaseUser(current_user)
    user_type = SchoolDB.models.getActiveDatabaseUser().get_active_user_type()
    #if the current user is admin then do not check permissions - an
    # admin user can go everywhere without restriction
    initrequest(request)
    if (not users.is_current_user_admin()):
        #Unpack the permissions information to prepare for use
        user_type.prepare_for_use()
        #check for legal url as the very first action. This allows an
        #empty "404" response to be sent without anything else sent or set
        if (not user_type.legal_url(request.path)):
            #this will end all further processing of the request
            raise ProhibitedURLError, request.path
        #allowable time difference 2 hours between logins
        too_long, minutes_since_last = \
                current_user.check_time_since_last_access()
        #for now, bypass
        too_long = False
        if too_long:
            #This will send error page and abort further processing
            return_prompt_for_login("Not used in ", minutes_since_last)
    #do not update access time for ajax or auto_tasks--update requires
    #expensive data write so only use on page requests
    if (not (request.is_ajax() or auto_task)):
        current_user.update_last_access_time()
    
def return_prompt_for_login(problem_string, minutes_since_last):
    """
    To do... meant to log person out and require new login. Would work only 
    with 2 level login.
    """
    pass

def validate_action(target_action, error_report_function, 
                    target_class = None, target_object = None):
    """
    Confirm the the requested action is allowed. The results are
    dependent upon both the class and the instance to be acted upon. If
    the action is some form of Edit but the user may only view the
    instance or class then return view_only True.
    """
    #if users.is_current_user_admin():
        ##the developer always has automatic permission
        #return (True,False)
    user_type = SchoolDB.models.getActiveDatabaseUser().get_active_user_type()
    legal_action = user_type.action_ok(target_action, target_class)
    view_only = False
    if (not legal_action and (target_action != "View")
        and target_class):
        view_only = user_type.action_ok("View", target_class)
    if (not legal_action and not view_only):
        raise ClassActionProhibitedError (target_action, target_class, 
                                          error_report_function)
    if (target_object):
        legal_action = user_type.action_ok(target_action, target_class, 
                                          target_object)
        if (not legal_action and (target_action != "View")):
            view_only = user_type.action_ok("View", target_class, target_object)
    if (not legal_action and not view_only):
        raise InstanceActionProhibitedError ((target_action, 
                error_report_function, target_class, target_object, "Not allowed for this user"))    
    return (legal_action, view_only)

def prompt_for_login(minutes_since_last):
    #for now...
    pass

def prompt_for_failed_login():
    #for now...
    pass

def check_login():
    #for now...
    return True

def create_standard_params_dict(title_suffix, url_name,
                                javascript_code = "",
                                submit_action = None,
                                breadcrumb_title = None,
                                full_title = None,
                                page_path_action = "Pop"):
    global __revision_id__
    if (not submit_action):
        submit_action = url_name
    if (getprocessed()):
        title_prefix = getprocessed().requested_action
    else:
        title_prefix = ""
    if (not breadcrumb_title):
        breadcrumb_title = title_suffix
    if (full_title):
        # if a full title has already been built use that as the 
        # suffix and clear out the prefix and bridge
        title_suffix = full_title
        title_prefix = ""
        title_bridge = ""
    param_dict = {"revision_id":__revision_id__, "school_name":
                  SchoolDB.models.getActiveDatabaseUser().get_active_organization_name(),
                  "title_prefix":title_prefix, "title_suffix":title_suffix,
                  "title_bridge":" a ",
                  'url_name':url_name, 
                  'submit_action':submit_action,
                  "breadcrumbs":generate_breadcrumb_line(),
                  "javascript_code":javascript_code,
                  "page_path_action":page_path_action}
    active_db_user = SchoolDB.models.getActiveDatabaseUser()
    if (active_db_user.get_active_user()):
        param_dict["username"] = active_db_user.get_active_user_name()
        param_dict["usertype"] = unicode(
            active_db_user.get_active_user_type())
        param_dict["personname"] = unicode(
            active_db_user.get_active_person())
    return param_dict

def showStatic(request, page_name, title_suffix, 
               extra_params = None,
               page_path_action = "Push",
               perform_mapping = True):
    try:
        validate_user(request)
        if perform_mapping:
            page_name = map_page_to_usertype(page_name)
        template_name = page_name + ".html"    
        params = create_standard_params_dict(title_suffix=title_suffix, 
            url_name=template_name, 
            page_path_action= page_path_action)
        params["title_prefix"] = ""
        if extra_params:
            params.update(extra_params)
        return shortcuts.render_to_response(template_name, params)
    except ProhibitedError, e:
        return e.response


def showStaticTop(request, page_name, title_suffix, extra_params = {},
                  page_path_action = "Index"):
        logout_url = users.create_logout_url("http://www.google.com")
        extra_params["logout_url"] = logout_url
        return showStatic(request = request, page_name = page_name, 
                          title_suffix = title_suffix, 
                          extra_params = extra_params,
                          page_path_action=page_path_action)
#def showIndex(request):
    #try:
        #validate_user(request)
        #title = "%s Home Page" \
              #%getActiveDatabaseUser().get_active_organization()
        #showStaticTop(request, "index", title)
        ##home_page = SchoolDB.models.getActiveDatabaseUser().get_active_user_type().home_page
        ##if not home_page:
            ##home_page = "adminhome"
        ##return showStaticTop(request, home_page, "Main Menu")
    #except ProhibitedError, e:
        #return e.response

#def showSpecialInformation(request):
    #try:
        #validate_user(request)
        #special_info_page = SchoolDB.models.getActiveDatabaseUser().get_active_user_type().special_info_page
        #if not special_info_page:
            #special_info_page = "othertypes"
        #return showStaticTop(request, special_info_page, 
                             #"Special Information")
    #except ProhibitedError, e:
        #return e.response

def showIndex(request):
    try:
        validate_user(request)
        return showStaticTop(request, "index", "Main Page", 
                             page_path_action="Index")
    except ProhibitedError, e:
        return e.response
    
def showMaint(request):
    return showStatic(request, "maint", "Special Information", 
                      page_path_action="Push")

def showAdmin(request):
    """
    'admin' is a special url that allows the master user to access any page without remapping. The url is of the form "admin/realurl"
    """
    if (users.is_current_user_admin()):
        splitpath  = request.path.split("/")
        real_path = splitpath[2]
        result = showStatic(request, real_path, "Admin Remap", 
                   perform_mapping = False)
        return result
    else:
        raise ProhibitedURLError
    
def showDynamic(request):
    """
    This is a direct redirect by the next page value in the cookie.
    It is used by the "Cancel and "Finish" button actions.
    """
    try:
        validate_user(request)
        return_page = get_return_page_from_cookie()
        return_page = map_page_to_usertype(return_page)
        return http.HttpResponseRedirect(return_page)
    except ProhibitedError, e:
        return e.response

#def showAdminHome(request):
    #return showStaticTop(request, "adminhome", "Admin Home")

#def showSchoolHome(request):
    #return showStaticTop(request, "schoolhome", "My School")

#def showStudentHome(request):
    #return showStaticTop(request, "studenthome", "My School")

#def showUpperLevelHome(request):
    ##Hack for name <<<<<<<<<<fix>>>>>>>>>
    #return showStaticTop(request, "upperlevelhome", "Region VII")

#def showUpperLevelAdminHome(request):
    ##Hack for name <<<<<<<<<<fix>>>>>>>>>
    #return showStaticTop(request, "upperlevel_adminhome", "Region VII")
    
#def showOtherTypes(request):
    #return showStatic(request, "othertypes", "Special Information")

#def showSchoolMaint(request):
    #return showStatic(request, "school_maint", "Special Information")

#def showSchoolAdminMaint(request):
    #return showStatic(request, "schooladmin_maint", "Special Information")

def showOtherWork(request):
    return showStatic(request, "otherwork", "Other Work")

def showChooseReport(request):
    return showStatic(request, "choose_report", 
                      "Choose a Report Type")
    
def showChooseCustomReport(request):
    return showStatic(request, "choose_custom_report", 
                      "Choose a Custom Report")

def showChooseErrorReport(request):
    return showStatic(request, "choose_error_report", 
                      "Choose an Error Report Type")

def showCalendar(request):
    return showStatic(request, "calendar", "School Calendar")

def showGradebookEntriesCalendar(request):
    return showStatic(request, "gradebook_entries_calendar",
                      "Gradebook Entries Calendar")

def standardShowAction(request, classname, formname, title_suffix,
                       template = "generic", page_path_action = 
                       "Pop", extra_params = None, full_title = "",
                        perform_mapping = False):
    try:
        validate_user(request)
        if perform_mapping:
            classname = map_page_to_usertype(classname)
            formname = map_form_to_usertype(formname)
        req_action = getprocessed().requested_action
        if (req_action == "Save"):
            req_object = getprocessed().current_instance
        else:
            req_object = getprocessed().requested_instance
        legal_action, view_ok = validate_action(req_action,
                        return_error_page, classname, req_object)
        #try just presenting the view instead
        if ((not legal_action) and view_ok):
            getprocessed().requested_action = "View"
        form, javascript_code = buildForm(formname) 
        params = create_standard_params_dict(
            title_suffix=title_suffix, url_name=classname,
            javascript_code= javascript_code, 
            page_path_action=page_path_action,
            full_title=full_title,
        )
        params['form'] = form
        if extra_params:
            params.update(extra_params)
        form.modify_params(params)
        return showForm(template=template, form=form,
                    page_path_action=page_path_action, 
                    params=params)
    except ProhibitedError, e:
        return e.response

def specialShowAction(instance, requested_action, classname, 
                      formname, title_suffix,
                       template = "generic", 
                       page_path_action="Pop", 
                       extra_params = None):
    try:
        getprocessed().requested_instance = instance
        getprocessed().requested_action = requested_action
        getprocessed().selection_key_valid = True
        if (instance):
            getprocessed().selection_key = str(instance.key())
        else:
            getprocessed().selection_key = ""
        form, javascript_code = buildForm(formname) 
        params = create_standard_params_dict(title_suffix, classname,
                                             javascript_code)
        params['form'] = form
        if extra_params:
            params.update(extra_params)
        form.modify_params(params)
        return showForm(template=template, form=form,
                page_path_action="NoAction", extra_params=params)
    except ProhibitedError, e:
        return e.response

    
def showPerson(request):
    return standardShowAction(request, "person", PersonForm, "Person",
                    "person", "Pop", 
                    {'show_title':True, 'show_gender':True,
                     'show_community':True, 'show_municipality':True})

def showTeacher(request):
    return standardShowAction(request, "teacher", TeacherForm, "Teacher",
                              "teacher", "Pop", 
                {'show_title':True, 'show_gender':True,
                 'show_community':True, 'show_municipality':True})

def showMyChoices(request):
    return standardShowAction(request, "teacher", MyChoicesForm, "My Choices",
                              "my_choices", "Pop")

def showStudent(request):
    return standardShowAction(request, "student", StudentForm, "Student",
                              "student", "Pop", 
                {'show_title':False, 'show_gender':True,'show_community':True,
                               'show_municipality':True})

def showParentOrGuardian(request):
    """
    Create a popup window with the parent form.
    """
    return standardShowAction(request, "parent_or_guardian",
                              ParentOrGuardianForm, 
            "Parent or Guardian","parent_or_guardian", "NoAction", 
            {'show_title':True, 'show_gender':True,
             'show_community':True,'show_municipality':True,
             "fixed_return_url":"/static_pages/close_window.html"})  

def showAdministrator(request):
    return standardShowAction(request, "administrator", AdministratorForm, 
                "Administrator","administrator", "Pop", 
                {'show_title':True, 'show_gender':False,
                 'show_community':False})  

def showGradingEvent(request):
    return standardShowAction(request, "grading_event",
                              GradingInstanceForm, 
            "Gradebook Entry","grading_instance", "FixedUrl",
            {"fixed_return_url":"/static_pages/close_window.html"})  

def showAchievementTest(request):
    return standardShowAction(request, "achievement_test", 
                              AchievementTestForm, "Achievement Test",
                              'achievement_test')
def showSection(request):
    return standardShowAction(request, "section", SectionForm, "Section",
                              'section')

def showSchool(request):
    return standardShowAction(request, "school", SchoolForm, "School",
                              "school")

def showMunicipality(request):
    return standardShowAction(request, "municipality", MunicipalityForm, 
                              "Municipality", "municipality")

def showCommunity(request):
    return standardShowAction(request, "community", CommunityForm, 
                              "Barangay", "community")

def showRegion(request):
    return standardShowAction(request, "region", RegionForm, "Region",
                              "region")

def showProvince(request):
    return standardShowAction(request, "province", ProvinceForm, "Province",
                              "province")

def showDivision(request):
    return standardShowAction(request, "division", DivisionForm, "Division",
                              "division")

def showContact(request):
    return standardShowAction(request, "contact", ContactForm,
                    "Contact", "contact", "FixedUrl",
            {"fixed_return_url":"/static_pages/close_window.html"})

def showStudentEmergency(request):
    return showStatic(request, "underconstruction", 
                      "Student Emergency Information")

def showClassroom(request):
    return standardShowAction(request, "classroom", ClassroomForm, 
                              "Classroom", "classroom")
def showClassSession(request):
    return standardShowAction(request, "class_session", ClassSessionForm,
                              "Class Sessions", "class_session")

def showClassPeriod(request):
    return standardShowAction(request, "class_period", ClassPeriodForm,
                              "Class Period")

def showGradingInstance(request):
    return standardShowAction(request, "grading_instance",
                              GradingInstanceForm, "Grading Instance",
                              "grading_instance")

def showSchoolDay(request):
    return standardShowAction(request, "school_day", SchoolDayForm,
                              "School Day", "school_day")

def showGrades(request):
    return standardShowAction(request, "grade", GradesForm, "Grades",
                              "grades")

def showAchievementTestGrades(request):
    return standardShowAction(request, "achievement_test",
                    AchievementTestGradesForm, "Achievement Test Grades",
                    "achievement_test_grades")

def showGradingPeriodResults(request):
    return standardShowAction(request, "grading_period_results",
                              GradingPeriodResultsForm, "Grading Period Grades",
                              "grading_period_results")

#revert for moment
def showDatabaseUser(request):
    return standardShowAction(request, "master_database_user", 
                              MasterDatabaseUserForm, 
                              "Database User", "generic")

#def showMasterDatabaseUser(request):
    #return standardShowAction(request, "master_database_user", 
                              #MasterDatabaseUserForm, 
                              #"Database User", "generic")

#def showDatabaseUser(request):
    #return standardShowAction(request, "database_user", 
                              #StandardDatabaseUserForm,
                              #"Database User", "generic",
                              #perform_mapping = True)
def showUserType(request):
    return standardShowAction(request, "user_type", UserTypeForm,
                              "User Type", "generic")

def showSchoolYear(request):
    return standardShowAction(request, "school_year", SchoolYearForm,
                              "School Year", "generic")

def showGradingPeriod(request):
    return standardShowAction(request, "grading_period", 
                              GradingPeriodForm, "Grading Period", "generic")

def showSubject(request):
    return standardShowAction(request, "subject", SubjectForm, 
                              "Subject", "generic")
def showSectionType(request):
    return standardShowAction(request, "section_type", SectionTypeForm, 
                              "Section Type", "generic")

def showStudentMajor(request):
    return standardShowAction(request, "student_major", StudentMajorForm, 
                              "Student Major", "generic")

def showSpecialDesignation(request):
    return standardShowAction(request, "special_designation", 
                              SpecialDesignationForm, 
                              "Special Designation", "generic")

def showStudentStatus(request):
    return standardShowAction(request, "student_status",
                              StudentStatusForm, 
                              "Student Status", "generic")

def showSchoolDayType(request):
    return standardShowAction(request, "school_day_type",
                              SchoolDayTypeForm, 
                              "School Day Type", "generic")

def showVersionedTextManager(request):
    return standardShowAction(request, "versioned_text_manager",
                               VersionedTextManagerForm, "Text Manager",
                              "versioned_text_manager","versioned_text")

def showVersionedText(request):
    return standardShowAction(request, "versioned_text",
                               VersionedTextForm, "Text Page",
                              "versioned_text")

def showEnterGrades(request):
    return standardShowAction(request, "enter_grades",  GradesForm,
                              "Enter Grades", "entergrades", "/grades")

def showCreateClassSessions(request):
    return standardShowAction(request, "create_class_sessions",  
                              CreateClassSessionsForm,
                              "Create Many Classes", "create_class_sessions")

def showStudentSummary(request):
    return standardShowAction(request, "student_summary", 
                              StudentSummaryForm, "Student Summary",
                              "upper_level_summary")
def showAchievementTestSummary(request):
    return standardShowAction(request, "achievment_test_summary", 
                              AchievementTestSummaryForm, 
                              "Achievement Test Summary",
                              "upper_level_summary")
def showGenerateGrades(request):
    return standardShowAction(request, "generate_grades", GenerateGradesForm, 
                              "Generate Fake Grades", "generate_grades")

def showAssignStudents(request):
    """
    Use the type of the class session to determine which type of 
    student assignment form should be presented. Then call the
    correct show action.
    """
    #validation must be done early to obtain filled processed information
    validate_user(request)
    #requested instance will be set during selection
    class_session = getprocessed().requested_instance
    #current_instance set in page itself
    if not class_session:
        class_session = getprocessed().current_instance
    if (class_session and (not class_session.students_assigned_by_section)):
        return standardShowAction(request, "assign_students",
                                  AssignStudentsForm, "Assign Students",
                                  "assign_students", "Push")
    else:
        #if there is no class session this form will display an error
        #message so it is always safe to call
        return standardShowAction(request, "assign_students",
                              AssignSectionStudentsForm, "Assign Students",
                              "assign_section_students","Push")

def showMyWork(request):
    return standardShowAction(request, "my_work",  MyWorkForm,
                              "My Work", "my_work", "Push", 
                              full_title = "My Work Page")

def showChoose(request):
    """
    The choose form presents an instance selection table similar to the
    bottom part of the select form. It is used when all selection
    parameters are already known. Each different type of choose page
    has its own custom ajax selection generator.
    """
    try:
        validate_user(request)
        splitpath  = request.path.split("/")
        choose_type = splitpath[2]
        choose_action = "View"
        if (choose_type == "section_students"):
            #Only the section head can edit but all can view
            section = SchoolDB.models.get_instance_from_key_string(
                getprocessed().values.get("users_section", None), 
                SchoolDB.models.Section)
            if (not section):
                raise RequestError, "Unknown Section"
            if (section.user_is_section_head()):
                choose_action = "Edit"
            else:
                choose_action = "View"
            form_title = "Section " + section.name + " Students"
            breadcrumb_title = "Section Students"
            chosen_object_class = "student"
            choose_object_class = "section"
        elif (choose_type == "class_session_students"):
            class_session = SchoolDB.models.get_instance_from_key_string(
                getprocessed().selection_key, SchoolDB.models.ClassSession)
            if (not class_session):
                raise RequestError, "Unknown Class"
            form_title = "Class " + class_session.name + " Students"
            choose_action = "View"
            breadcrumb_title = "Class Students"
            chosen_object_class = "student"
            choose_object_class = "class_session"
        elif (choose_type == "section_classes"):
            section = SchoolDB.models.get_instance_from_key_string(
                getprocessed().values.get("users_section", None), 
                SchoolDB.models.Section)
            if (not section):
                raise RequestError, "Unknown Section"
            form_title = "Section " + section.name + " Class Schedule"
            breadcrumb_title = "Section Class Schedule"
            chosen_object_class = "class_session"
            choose_object_class = "section"
        else:
            raise http.Http404 
        (legal_action, view_only) = validate_action(choose_action, 
                                                    return_error_page, 
                                                    chosen_object_class)
        form = ChooseForm(choose_type, choose_object_class, choose_action)
        javascript_generator = SchoolDB.assistant_classes.JavascriptGenerator()
        form.generate_javascript_code(javascript_generator)
        javascript_code = javascript_generator.get_final_code()
        params = create_standard_params_dict(title_suffix=form_title, 
            url_name=request.path, javascript_code=javascript_code,
            page_path_action = "Push", breadcrumb_title=breadcrumb_title,
            submit_action ='/' + chosen_object_class)
        form.modify_params(params)
    except ProhibitedError, e:
        return e.response
    return showForm("choose.html", form, "my_work", params)

def showReports(request):
    """
    The common entry point for all reports. Use the second part of
    the url to determine the report type and then call the 
    appropriate form class. The default return location is the
    top level but this may be changed dynamically by the form
    """
    splitpath  = request.path.split("/")
    report_type = splitpath[2]
    report_template = report_type + "_report"
    #The second field of "standardShowAction" is used here for the
    #"class" to be used in user action validation. For now, it is
    #difficult to add further explicit reports to the user type so
    #all reports meant for the school will simply be designated
    #"school_report". This is not a long term correct approach but
    #is functional for now.
    if (report_type == "attendance"):
        formname = AttendanceReportForm
        report_title = "Attendance Report"
    elif (report_type == "student_age"):
        formname = StudentAgeReportForm
        report_title = "Student Age Distribution Report"
    elif (report_type == "section_list"):
        formname = SectionListReportForm
        report_title = "Section List"
    elif (report_type == "student_record_check"):
        formname = StudentRecordsCheckForm
        report_title = 'Student Record Check'
    elif(report_type == "section_grading_period_grades"):
        formname = SectionGradingPeriodGradesForm
        report_title = "Section Grading Period Grades Report"
    elif (report_type == "form1"):
        formname = Form1ReportForm
        report_title = 'Form 1'
    elif (report_type == "form2"):
        formname = Form2ReportForm
        report_title = 'Form 2'
    elif (report_type == "form14"):
        formname = Form14ReportForm
        report_title = 'Form 14'
    else:
        #Unknown report type. Return 404 page.
        raise http.Http404
    return standardShowAction(request, "school_report", formname, 
                        report_title, report_template)           
    
def processAjaxRequest(request):
    """
    A common entry point for all Ajax requests. The ajax actions are
    defined in ajax.py. No further Ajax code in this file.
    """
    try:
        validate_user(request)
        server = SchoolDB.ajax.AjaxServer(request)
        return server.process_request()
    except ProhibitedError, e:
        return e.response        

#def showTest(request):
    #return standardShowAction(request, "testobject", TestForm,
                              #"Select", "select", "adminhome")

def showAttendance(request):
    """
    Create and process attendance forms. This is different from other forms
    because it is not associated with a particular instance of a database object
    and neither reads nor creates one. In addition, all of the fields are
    generated by other python code with an AttendanceTableCreator object and the
    data is returned only within the hidden field attendance_data. Thus much of
    the code is unique to this form and action. The students that are displayed
    in the form are all members of a single section. This section must be
    identified in the original request.
    """
    try:
        validate_user(request)
        req_action = getprocessed().requested_action
        validate_action(req_action,return_error_page,"attendance")
        if ( req_action == "Save"):
            #This will perform all processing of the data and return a redirect
            #to a different web page
            return AttendanceForm.process_response()
        elif ((req_action == "Edit") or 
              (req_action == "View") or
              (req_action == "Select")):
            #This is the initial request so it must have a section and 
            #the section must exist for the school
            section = getprocessed().requested_instance
            if ((not section) or (section.kind() != "StudentGrouping")):
                return AttendanceForm.error_no_section()
            section_name = unicode(section)
            if (not section.has_students()):
                return AttendanceForm.error_no_students(section_name)
            data_values = {"section":str(section.key()),
                           "section_name":section_name,
                           "state":"Exists",
                           "requested_action":"Save",
                           "redirect_page":"index"}
            attendance_form = AttendanceForm(data=data_values or None)
            params = {'form':attendance_form, 'url_name':'attendance',
                'title_name':'Attendance', 'school_name':
                SchoolDB.models.getActiveDatabaseUser().get_active_organization_name(), 
                'section':section_name,
                "username":SchoolDB.models.getActiveDatabaseUser().get_active_user_name()}
            return respond("attendance.html", params)
        else:
            return respond("")
    except ProhibitedError, e:
        return e.response

def showHistory(request):
    """
    Show a form with a list of history entries for a specific object 
    and history type
    """
    try:
        validate_user(request)
        parent_object = getprocessed().requested_instance
        field_name = getprocessed().values["field_name"]
        if (not parent_object):
            history_entries = [{'end_date': '-----', 'start_date': '-----', 
            'value': u'No information for %s. The form has not been saved yet.' 
                                %getprocessed().values["display_name"]}]
            title_suffix = " Not Available"
        else:
            history = get_history_field(parent_object, field_name)
            if (not history):
                history_entries = [{'end_date': '-----', 'start_date': '-----', 
                'value': u'No history yet. The form has not been saved with a value for %s.' 
                                    %getprocessed().values["display_name"]}]
            else:
                history_entries = history.get_entries_dict_list()
            title_suffix = getprocessed().values["display_name"] + \
                             " History: " + unicode(parent_object)
        params = create_standard_params_dict(title_suffix, "")
        params["title_prefix"] = ""
        params["title_bridge"] = ""
        params["requested_action"] = "View"
        params["history_entries"] = history_entries
        return respond("history", params)
    except ProhibitedError, e:
        return e.response

def get_history_field(parent_object, field_name):
    """
    A really dumb and difficult to keep up to date way of
    getting the history field from the name. I can't find
    another way right now to get a parameter from the object with a 
    variable name -- just the "." notation. So... this ugly
    hack for the moment. Needs change!
    """
    if (field_name == "student_status"):
        return parent_object.student_status_history
    elif (field_name == "class_year"):
        return parent_object.class_year_history
    elif (field_name == "section"):
        return parent_object.section_history
    elif (field_name == "student_major"):
        return parent_object.student_major_history
    elif (field_name == "other_activities"):
        return parent_object.other_activities_history
    elif (field_name == "special_designation"):
        return parent_object.special_designation_history
    elif (field_name == "ranking"):
        return parent_object.ranking_history
    elif (field_name == "teacher"):
        return parent_object.teacher_history
    else:
        return None
#----------------------------------------------------------------------

def showSelectDialog(request):
    """
    Create the select service network page. It uses a url organized as
    "select"/class_name/page_type/return_url/title. The default
    page_type is "full", the default return_url is the class_name, and
    the default title is "Work With a " + class_name. Thus for standard
    create/edit/view of a class the url only needs to be
    "select"/class_name.
    """
    try:
        validate_user(request)
        getprocessed().requested_action = "Select"
        splitpath  = request.path.split("/")
        length = len(splitpath)
        select_type = splitpath[1]
        title_prefix = None
        if (select_type == "initialselect"):
            select_template = "select_short"
            template_requested_action = "Further Selection"
            title_prefix = "Select a "
        else:
            select_template = "select_full"
            template_requested_action = "Create"
        if (length == 2):
            return http.HttpResponseNotFound(
                "No type to select. Check request address")
        select_class_name = splitpath[2]
        return_url = "/" + select_class_name
        title = ""
        if (length > 3):
            #If there is more than one level of selection left
            #the the action is "Further Selection". If not then
            #the action will be performed upon the selected object
            #so the action will be "Edit".
            return_url = "/" + splitpath[3]
            template_requested_action = "Edit"
            if (return_url.count("-") > 0):
                return_url = return_url.replace("-","/")
                template_requested_action = "Further Selection"
        if (length > 4):
            full_title = splitpath[4].replace("-"," ")
            title_prefix = ""
        else:
            full_title = ""
        select_class_form = \
                          get_form_from_class_name(select_class_name)
        if (not select_class_form):
            error_text = '"' + select_class_name + \
                       '" is not a valid selection type.'
            return http.HttpResponseNotFound(error_text)
        #assume selection will want edit to get action choices. Check view_only
        #on return to determine if the choices should be displayed
        (legal_action, view_only) = validate_action("Edit", 
                                return_error_page, select_class_name)
        if (view_only):
            select_template = "select_short"
            template_requested_action = "View"
            title_prefix = "View a "        
        form = SelectForm(select_class=select_class_form, 
                          select_class_name=select_class_name,
                          title_prefix = title_prefix,
                          submit_action=return_url, 
                          view_only=view_only,
                          title=full_title)
        javascript_generator = \
                    SchoolDB.assistant_classes.JavascriptGenerator()
        form.generate_javascript_code(javascript_generator)
        javascript_generator.add_javascript_params ({
            "template_requested_action":template_requested_action})
        javascript_code = javascript_generator.get_final_code()
        params = create_standard_params_dict(title, 
            url_name = "/select/"+select_class_name+return_url, 
            javascript_code = javascript_code,
            submit_action = return_url, 
            breadcrumb_title ="Select",
            full_title = full_title,
            page_path_action="Push")
        params["template_requested_action"] = template_requested_action
    except ProhibitedError, e:
        return e.response
    return showForm(select_template, form,
                    "index", params)

#----------------------------------------------------------------------
def showDataBrowser(request):
    """
    Create the select service network page. It uses a url organized as
    "select"/class_name/page_type/return_url/title. The default
    page_type is "full", the default return_url is the class_name, and
    the default title is "Work With a " + class_name. Thus for standard
    create/edit/view of a class the url only needs to be
    "select"/class_name.
    """
    try:
        validate_user(request)
        getprocessed().requested_action = "Select"
        splitpath  = request.path.split("/")
        length = len(splitpath)
        select_type = splitpath[1]
        select_template = "databrowser"
        template_requested_action = "View"
        title_prefix = "Custom Report For "
        if (length == 2):
            return http.HttpResponseNotFound(
                "No type to browse. Check request address")
        select_class_name = splitpath[2]
        return_url = "/" + select_class_name
        title = "Custom Report Information"
        if (length > 3):
            return_url = "/" +splitpath[3].replace("-","/")
        if (length > 4):
            title = splitpath[4].replace("-"," ")
        select_class_form = \
                          get_form_from_class_name(select_class_name)
        if (not select_class_form):
            error_text = '"' + select_class_name + \
                       '" is not a valid selection type.'
            return http.HttpResponseNotFound(error_text)
        form = DatabrowserForm(select_class=select_class_form, 
                          select_class_name=select_class_name,
                          title_prefix = title_prefix,
                          submit_action=return_url)
        javascript_generator = \
                    SchoolDB.assistant_classes.JavascriptGenerator()
        form.generate_javascript_code(javascript_generator)
        javascript_code = javascript_generator.get_final_code()
        params = create_standard_params_dict(title_suffix=title, 
            url_name="/custom_report/" + select_class_name + return_url,
            javascript_code=javascript_code, submit_action=return_url, 
            breadcrumb_title = "Custom Report", page_path_action="Push")
        params["template_requested_action"] = template_requested_action
    except ProhibitedError, e:
        return e.response
    return showForm(select_template, form,
                    "index", params)

def createBrowserFieldsTables(browsed_class_name):
    """
    Create the two tables for the selection of display fields for the
    browser. The first table, browse_field_choices, lists all of the
    object data fields that may be displayed, the second,
    browse_fields_selected just an empty list as a receiver of the
    users choices.
    """
    browsed_class = SchoolDB.models.get_model_class_from_name(browsed_class_name)
    field_names = browsed_class.get_field_names()
    field_choices_table = SchoolDB.gviz_api.DataTable(
        ("field","string","Field Choices"))
    field_choices_table.LoadData(field_names)
    field_choices_descriptor = "(%s)" %field_choices_table.ToJSon()
    selected_fields_table = SchoolDB.gviz_api.DataTable(
        ("field","string","Selected Fields"))
    selected_fields_table.LoadData([])
    selected_fields_descriptor = "(%s)" %selected_fields_table.ToJSon()
    return (field_choices_descriptor, selected_fields_descriptor)
    
#----------------------------------------------------------------------
def runTask(request):
    """
    Perform a task from a task queue. This has not been sent by a human
    user and only expects a 200 response for success, not a full web page.
    The primary values in the task request are:
    'organization': If present, the organization that will be set for the
        active user. If not present, the current org for the user. 
    'task_name': Name of task used in logging records.
    'target_instances': A list of entity keys to be processed by the function.
    'function': The function to be run
    'args': further arguments for the function
    All values for innstances are keystrings and all are converted to 
    actual instances prior to use. If invalid, they are ignored.
    """
    successful = False
    try:
        #validate_user(request, auto_task=True)
        #must have task_data so just raise error and report if not there
        task_data = request.POST["task_data"]
        unencoded = base64.b64decode(task_data)
        uncompressed = zlib.decompress(unencoded)
        task_dict = cPickle.loads(uncompressed)
        task_name = task_dict.get("task_name", "Unnamed Task")
        rerun_if_failed = False
        #The task is normally not run via a database user. Use the
        #user identified in the initial tasking instead.
        task_initiator_keystr = task_dict.get("task_initiator", None)
        task_initiator = \
                SchoolDB.utility_functions.get_instance_from_key_string(
                   task_initiator_keystr, DatabaseUser)
        SchoolDB.models.setActiveDatabaseUser(task_initiator)
        if getActiveDatabaseUser():
            username = getActiveDatabaseUser().get_active_user_name()
        else:
            username = "None"
        logging.info("Started task: '%s' User: %s" %(task_name, username))
        #put here only for testing 
        validate_user(request, auto_task=True)
        if (task_dict.has_key("function")):
            # if no function is given then there is nothing to do
            function = task_dict["function"]
            if task_dict.has_key("organization"):
                org_keystring = task_dict["organization"]
                org = SchoolDB.models.get_instance_from_key_string(
                    org_keystring, SchoolDB.models.Organization)
                SchoolDB.models.setActiveOrganization(org)
            instance_keys = task_dict.get("target_instances", None)
            args = task_dict.get("args",None)
            rerun_if_failed = task_dict.get("rerun_if_failed", True)
            target_instance = None
            logging.info("Running task: '%s', function: %s" 
                         %(task_name, function))
            try:
                if (instance_keys):
                    completely_successful = True
                    for target_key in instance_keys:
                        target_instance = \
                            get_instance_from_key_string(target_key)
                        if target_instance:
                            #confirm that the instance really exists before
                            #acting on it
                            command = "%s('%s', %s)" \
                                    %(function, target_key, args)
                            action_desc = \
                                "Task: %s on %s. Function: %s Args: '%s'" \
                                %(task_name, unicode(target_instance),
                                  function, args)
                            logging.info("Called " + action_desc)
                            successful = eval(command)
                            if not successful:
                                logging.error("Failed: " + action_desc)
                                completely_successful = False
                        else:
                            logging.error("Failed: invalid key.")
                            completely_successful = False
                    #report success only if none have failed
                    successful = completely_successful
                else:
                    #No target instances used with this command
                    command = "%s(%s)" %(function, args)
                    action_desc = \
                        "Task: %s Function: %s Args: '%s'" \
                        %(task_name, function, args)
                    logging.info("Called " + action_desc)
                    successful = eval(command)
                    if not successful:
                        logging.error("Failed: " + action_desc)
            except StandardError, e:
                logging.error("Task %s:Failed to run command. Error: %s"  
                              %(task_name, e))
        else:
            #no function defined -- nothing to do
            logging.error("Task '%s' had no function." %task_name)
    except StandardError, e:
        logging.error("Failed to complete task '%s': %s" %(task_name,e))
    if ((not rerun_if_failed) and (not successful)):
        logging.error("Task '%s' failed but should not be rerun", task_name)
    if (successful or not (rerun_if_failed)):
        #if should not be rerun if it failed then always return success
        result = 200
    else:
        result = 500
    response = http.HttpResponse()
    response.status_code = result
    return response
    
#----------------------------------------------------------------------
def runUtil(request):
    """
    Perform remote commands directly for database initialization
    or maintenance. This may only be done by an administrator.
    """
    try:
        validate_user(request, auto_task=True)
        logger = ResultLogger()
        if (getprocessed().values.has_key("util")):
            function = getprocessed().values["util"]
        else:
            params_dict = create_standard_params_dict(
                "Request Utility","utilrequest", 
                page_path_action="Push")
            params_dict.update({"value_right_btn":"Run", 
                        "title_right_btn":"Click to run the function"})
            return shortcuts.render_to_response("utilrequest.html", 
                    params_dict)
        args_str = ""
        if (getprocessed().values.has_key("args")):
            args_str = getprocessed().values["args"]
        logger.clear_lines()
        command = "%s(logger, %s)" %(function, 
                                     getprocessed().values.get("args",""))
        logger.add_line("Called '%s'" %command)
        try:
            result = eval(command)
        except StandardError, e:
            logger.add_line("Failed to run command: %s" %e)
        params = create_standard_params_dict(
            title_suffix="Utility Response", 
            url_name="utilresponse", page_path_action="Pop")
        params["command"] = command
        logger.add_line("-------------------------------------------------")
        logger.add_line(">>>Util response complete<<<")
        params["result"] = logger.text()
    except ProhibitedError, e:
        return e.response
    return shortcuts.render_to_response("utilresponse.html", params)   

#----------------------------------------------------------------------

def buildForm(class_form):
    data_values = {}
    req_action = getprocessed().requested_action
    instance_string = ""
    if (req_action == "Save"):
        data_values = getprocessed().values
    elif (((req_action == "Edit") 
           or (req_action == "View"))
          and (getprocessed().selection_key_valid)):
        instance = getprocessed().requested_instance
        value_names = class_form.element_names
        current_form = class_form
        while current_form.parent_form:
            current_form = current_form.parent_form
            value_names.extend(current_form.element_names)
        instance_string = getprocessed().selection_key
        school_name = SchoolDB.models.getActiveDatabaseUser().get_active_organization_name()
        data_values = {"object_instance":instance_string, 
                       "state":"Exists",
                       "school_name":school_name,
                       "usertype":SchoolDB.models.getActiveDatabaseUser().get_active_user_type}
        if (req_action == "Edit"):
            data_values["requested_action"] = "Save"
        else:
            data_values["requested_action"] = "Ignore"
        for name in value_names:
            data_values[name] = convert_to_field_value(instance, name)
        class_form.add_extras(instance, data_values)
        class_form.initialize(data_values)
    class_form.process_request(data_values)
    form = class_form(data=data_values or None)
    javascript_generator = \
            SchoolDB.assistant_classes.JavascriptGenerator(instance_string)
    form.generate_javascript_code(javascript_generator)
    if (req_action == "View"):
        javascript_generator.add_read_only()
    javascript_code = javascript_generator.get_final_code()
    form.generate_choices()
    return form, javascript_code


#----------------------------------------------------------------------

def showForm(template, form, page_path_action, params, 
             reload_form_type = None):
    """
    Create or edit a model instance. 
    """
    req_action = getprocessed().requested_action
    if ((req_action != "Save") and
        (req_action != "Ignore")):
        return respond(template, params)
    elif ((req_action == "Save") and
          form.is_valid()):
        errors = form.errors
        if not (errors):
            try:
                instance = form.save(getprocessed().current_instance)
                if (instance and (not getprocessed().current_instance)):
                    instance.post_creation()
                if (instance):
                    instance.form_data_post_processing()
                    return_action = form.generate_custom_return(instance)
                    if (return_action):
                        return return_action
            except ValueError, err:
                errors['__all__'] = unicode(err)
        if errors:
            return respond(template, params)
    return_page = get_return_page_from_cookie()
    return_page = map_page_to_usertype(return_page)
    if (return_page != "NoReturnPage"):
        return http.HttpResponseRedirect(return_page)
    else:
        return None

#----------------------------------------------------------------------
def respond(template, params=None):
    """
    Helper to render a response, passing standard stuff to the response.
    Args:
      template: The template name; '.html' is appended automatically.
      params: A dict giving the template parameters; modified in-place.

    Returns:
      Whatever render_to_response(template, params) returns.

    Raises:
      Whatever render_to_response(template, params) raises.
    """
    if params is None:
        params = {}
    if not template.endswith('.html'):
        template += '.html'
    return shortcuts.render_to_response(template, params)

#----------------------------------------------------------------------

class BaseStudentDBForm(forms.Form):
    """
    The form from which all other project forms are derived. This form
    provides the several hidden form fields to store the common
    information. It also defines a standard method of loading the
    original instances values into the form at the start and extracting
    the values at the end for save.
    """
    object_instance = forms.CharField(required=False, 
                                      widget=forms.HiddenInput,
                                      initial = "NOTSET")
    state = forms.CharField(required=False, widget=forms.HiddenInput,
                            initial = "New")
    requested_action = forms.CharField(required=False, 
                        widget=forms.HiddenInput, initial = "Create")
    selection_key = forms.CharField(required=False, 
                                      widget=forms.HiddenInput,
                                      initial = "NOTSET")
    element_names = []
    parent_form = None

    def set_values_from_form(self, instance):
        element_names = self.create_value_names_list()
        for name in element_names:
            try:
                if name_is_in_model(instance, name):
                    value = convert_to_instance_value(instance, name, 
                                            self.cleaned_data[name])
                    instance.__setattr__(name,value)
            except ValueError, err:                
                db.errors['__all__'] = unicode(err)
                continue

    def create_value_names_list(self):
        value_names = self.element_names
        current_form = type(self)
        while current_form.parent_form:
            current_form = current_form.parent_form
            value_names.extend(current_form.element_names)
        return value_names

    def create_new_instance(self):
        pass

    def save(self, instance):
        try:
            if not instance:        
                instance = self.create_new_instance()
            self.set_values_from_form(instance)
            if instance:
                instance.put()
                #ins = School(instance)
                #instance.post_creation()
        except ValueError, err:
            db.errors['__all__'] = unicode(err)
        return instance

    def generate_choices(self):
        pass

    def modify_params(self, param_dict):
        pass

    def generate_custom_return(self, instance):
        return None
    
    @staticmethod
    def process_request(data):
        pass

    @staticmethod
    def generate_javascript_code(javascript_generator):
        pass

    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        pass

    @staticmethod
    def initialize(data):
        pass

    @staticmethod
    def add_extras(instance, data):
        pass

    @staticmethod
    def initialize_form_params(select_form):
        pass

#----------------------------------------------------------------------

class PersonForm(BaseStudentDBForm):
    first_name = forms.CharField(required=True,max_length=40,
                widget=forms.TextInput(attrs={'size':15, 
                            "class":"person_name required entry-field"}))
    middle_name = forms.CharField(required=False,max_length=40,
                widget=forms.TextInput(attrs={'size':10, 
                                    "class":"person_name entry-field"}))
    last_name = forms.CharField(required=True,max_length=40,
                widget=forms.TextInput(attrs={'size':20,
                            "class":"person_name required entry-field"}))
    gender = forms.ChoiceField(required=False,
            choices=(("Male","Male"), ("Female","Female")), initial="Female")
    title = forms.CharField(required=False,max_length=25,
            widget=forms.TextInput(attrs={'size':15,
                        "class":"person_title entry-field entry-field"}))
    municipality_name = forms.CharField(required=False, 
                label="Municipality",
                widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    municipality = forms.CharField(required=False, 
                                   widget=forms.HiddenInput)
    community_name = forms.CharField(required=False, label="Barangay",
                widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    community = forms.CharField(required=False, 
                               widget=forms.HiddenInput)
    address = forms.CharField(required=False,
                    max_length=1000, widget=forms.Textarea(
                    attrs={'cols':50, 'rows':3, 'class':'entry-field'}))
    cell_phone = forms.CharField(required=False,max_length=15,
                    widget=forms.TextInput(attrs={"size":12,
                                    "class":"phone_number entry-field"}))
    landline_phone = forms.CharField(required=False,max_length=15,
                    widget=forms.TextInput(attrs={"size":12,
                                                "class":"entry-field"}))
    email = forms.EmailField(required=False,
                    widget=forms.TextInput(attrs={"size":25,
                                    "class":"phone_number entry-field"}))
    other_contact_info = forms.CharField(required=False,
                        max_length=1000, widget=forms.Textarea( 
                        attrs={'cols':50, 'rows':2, 'class':'entry-field'}))
    element_names = ['first_name', 'middle_name', 'last_name', 'gender',
                     'title', 'municipality', 'community', 'address', 
                     'cell_phone', 
                     'landline_phone', 'email', 'other_contact_info']
    parent_form = BaseStudentDBForm


    def create_new_instance(self):
        instance = SchoolDB.models.Person(
            first_name = self.cleaned_data["first_name"],
            last_name = self.cleaned_data["last_name"])
        return instance

    @staticmethod
    def initialize(data):
        initialize_fields([("municipality", "municipality_name"),
                           ("community", "community_name")], data)

    def generate_javascript_code(self, javascript_generator):
        muni = javascript_generator.add_autocomplete_field(
            class_name = "municipality", 
            field_name = "id_municipality_name",
            key_field_name = "id_municipality")
        
        bgy = javascript_generator.add_autocomplete_field(
            class_name = "community", 
            field_name = "id_community_name",
            key_field_name = "id_community")
        bgy.add_dependency(muni, True)
        return javascript_generator
    
    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        javascript_generator.add_javascript_params ({
            "fieldName":"Family Name"})
        select_field.add_extra_params({
            "extra_fields":"first_name|middle_name",
            "format": "last_name_only",
            "leading_value_field":"last_name"})

#----------------------------------------------------------------------  

class TeacherForm(PersonForm):

    primary_subject_name = forms.CharField(required=False, label="Primary Subject",
            widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    primary_subject = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")
    secondary_subject_name = forms.CharField(required=False, label="Secondary Subject",
            widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    secondary_subject = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")
    paygrade = forms.CharField(required=False,
            widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    other_information = forms.CharField(required=False, max_length=1000,
                                label="Other Information:",
                                widget=forms.Textarea(attrs={
                                    'cols':50, 'rows':2, 'class':'entry-field'}))
    element_names = ["primary_subject", "secondary_subject", "paygrade", 
                     "other_information"]
    parent_form = PersonForm

    def create_new_instance(self):
        return SchoolDB.models.Teacher(
            first_name = self.cleaned_data["first_name"],
            last_name = self.cleaned_data["last_name"])

    def generate_javascript_code(self, javascript_generator):
        self.parent_form.generate_javascript_code(self,
                                                  javascript_generator)
        prim_subject =  javascript_generator.add_autocomplete_field(
                    class_name="subject", field_name="id_primary_subject_name",
                    key_field_name="id_primary_subject")
        prim_subject.add_extra_params({"use_class_query":"!true!"})
        sec_subject = javascript_generator.add_autocomplete_field(          
                    class_name="subject", field_name="id_secondary_subject_name",
                    key_field_name="id_secondary_subject")
        sec_subject.add_extra_params({"use_class_query":"!true!"})
        pygd = javascript_generator.add_autocomplete_field(
            class_name = "paygrade", field_name = "id_paygrade")
        pygd.set_local_choices_list(SchoolDB.choices.TeacherPaygrade)
        return javascript_generator

    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        javascript_generator.add_javascript_params ({
            "fieldName":"Teacher's Family Name"})
        select_field.add_extra_params({
            "extra_fields":"first_name|middle_name",
            "format": "last_name_only",
            "leading_value_field":"last_name"})
        
    @staticmethod
    def initialize(data):
        TeacherForm.parent_form.initialize(data)
        initialize_fields([("primary_subject", "primary_subject_name"),
                           ("secondary_subject","secondary_subject_name")],
                          data)
   
#----------------------------------------------------------------------

class MyChoicesForm(BaseStudentDBForm):
    """
    An extension of the teacher form to add new fields for choice of 
    classes and sections to show on My Work Page. Both sets of choices are
    kept in a single list in the DatabaseUser instance associated with
    the teacher
    """
    section_name = forms.CharField(required = False, label = "Section:",
            widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    section = forms.CharField(required=False)
    interested_sections = forms.CharField(required = False, 
                                              widget=forms.HiddenInput)  
    class_session_name = forms.CharField(required = False, 
            widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    class_session = forms.CharField(required=False, 
                               widget=forms.HiddenInput)
    interested_classes = forms.CharField(required = False, 
                                              widget=forms.HiddenInput)
    parent_form = BaseStudentDBForm
    
    def __init__(self, data):
        try:
            self.database_user = \
                SchoolDB.models.get_instance_from_key_string(data["object_instance"])
            self.sections_list = []
            self.classes_list = []
            if self.database_user:
                self.get_my_lists()
                self.teacher = self.database_user.person
                if (not self.teacher):
                    logging.warning("No teacher for " + \
                                    unicode(self.database_user))
            else:
                logging.error("No database user for My Choices Form")
        except Exception, e:
            logging.error("Major exception: %s" %e)

    def get_my_lists(self):
        """
        Get the lists of "my sections" and "my classes" from
        teachers associated data record
        """
        self.sections_list = \
            self.database_user.get_interesting_instances_class_list(
                SchoolDB.models.Section)
        self.classes_list = \
            self.database_user.get_interesting_instances_class_list(
                SchoolDB.models.ClassSession)
        
    def modify_params(self, params):
        params["title_prefix"] = ""
        params["title_bridge"] = ""
        params["submit_action"] = "my_work"
        
    def generate_javascript_code(self, javascript_generator):
        active_user_key = \
                str(SchoolDB.models.getActiveDatabaseUser().get_active_user().key())
        active_person_key = \
                str(SchoolDB.models.getActiveDatabaseUser().get_active_person().key())
        sect = javascript_generator.add_autocomplete_field(
            class_name = "section")
        cls = javascript_generator.add_autocomplete_field(
            class_name = "class_session")
        cls.add_extra_params({"extra_fields": "teacher|class_period"})
        javascript_generator.add_javascript_params ({
            "database_user":active_user_key, "teacher":active_person_key})
            

#----------------------------------------------------------------------

class ParentOrGuardianForm(PersonForm):

    relationship = forms.ChoiceField(required=False,
                    choices=SchoolDB.choices.convert_to_form_choice_list(
                                         SchoolDB.choices.Relationship))
    occupation = forms.CharField(required=False, widget=
                                 forms.TextInput(attrs={'class':'entry-field'}))
    contact_order = forms.ChoiceField(required=False,
                        choices=SchoolDB.choices.convert_to_form_choice_list(
                                          SchoolDB.choices.ContactOrder))
    family = forms.CharField(required=False, widget=forms.HiddenInput,
                             initial="NOTSET")
    element_names = ["relationship", "occupation","contact_order","family"]
    parent_form = PersonForm

    def create_new_instance(self):
        return SchoolDB.models.ParentOrGuardian(
            first_name = self.cleaned_data["first_name"],
            last_name = self.cleaned_data["last_name"])

#----------------------------------------------------------------------

class AdministratorForm(PersonForm):
    
    organization_name = forms.CharField(required=True, 
                label="Organization*:",
                widget=forms.TextInput(attrs={
                    'class':'autofill entry-field required'}))
    organization = forms.CharField(required=False, 
                               widget=forms.HiddenInput)
    position = forms.CharField(required=False)
    element_names = ["position", "organization"]
    parent_form = PersonForm

    def create_new_instance(self):
        return SchoolDB.models.Administrator(
            first_name = self.cleaned_data["first_name"],
            last_name = self.cleaned_data["last_name"],
            organization = SchoolDB.models.get_key_from_string(
            self.cleaned_data["organization"]))

    
    def generate_javascript_code(self, javascript_generator):
        org = javascript_generator.add_autocomplete_field(
            class_name = "organization")
    
    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        javascript_generator.add_javascript_params ({
            "fieldName":"Administrator's Family Name"})
        select_field.add_extra_params({
            "extra_fields":"first_name|middle_name|organization",
            "format": "last_name_only",
            "leading_value_field":"last_name"})

    @staticmethod
    def initialize(data):
        initialize_fields([("organization", "organization_name")], data)

#----------------------------------------------------------------------  
class StudentForm(PersonForm):

    birthdate = forms.DateField(required=False,
        widget=forms.DateInput(format="%m/%d/%Y",                    
            attrs={"class":"date-mask entry-field",
                "title":"This is an important field for reports. The calendar will start with a date 14 years ago.You can use the year and month buttons to quickly set the right date"
}))
    family = forms.CharField(required=False, widget=forms.HiddenInput,
                             initial="NOTSET")
    siblings_initial_val = forms.CharField(required=False,
                                           widget=forms.HiddenInput)
    parents_initial_val = forms.CharField(required=False, 
                                          widget=forms.HiddenInput)
    student_id = forms.CharField(required=False, label="Student Id:")
    #-------These fields about elementary school are normally hidden-----
    birth_community_name = forms.CharField(required=False,
                            label="Birth Barangay:",
                            widget=forms.TextInput(attrs={
                                'class':'autofill entry-field'}))    
    birth_community = forms.CharField(required=False, 
                                   widget=forms.HiddenInput)
    birth_community_other = forms.CharField(required = False, 
                                label="Birth Barangay (Not In List):")
    birth_municipality_name = forms.CharField(required=False,
                                label="Birth Municipality:",
                                widget=forms.TextInput(attrs={
                                    'class':'autofill entry-field'}))    
    birth_municipality = forms.CharField(required=False, 
                                   widget=forms.HiddenInput)
    birth_municipality_other = forms.CharField(required = False,
                            label= "Birth Municipality (Not In List):")
    birth_province_name = forms.CharField(required=False,
                                label="Birth Province:",
                                widget=forms.TextInput(attrs={
                                    'class':'autofill entry-field'}))    
    birth_province = forms.CharField(required=False, 
                                   widget=forms.HiddenInput)
    birth_other_country = forms.CharField(required = False,
                            label= "Birth Other Country:")
    elementary_school = forms.CharField(required = False,
                label="Elementary School:",
                    widget=forms.TextInput(attrs={'class':'entry-field'}))
    elementary_gpa = forms.FloatField(required = False,
                label = "Elementary General Average:",  
                widget=forms.TextInput(
                attrs={'class':'entry-field numeric-field'}))
    elementary_graduation_date = forms.DateField(required=False,
                label = "Elementary Graduation Date:",
                widget=forms.DateInput(format="%m/%d/%Y",
                attrs={"class":"date-mask popup-calendar entry-field"}))
    #to do
    #elementary_graduation_date = forms.IntegerField(required=False,
                #label = "Elementary Graduation Date:", 
                #widget=forms.TextInput(
                #attrs={"class":"year-mask entry-field"}))
    years_in_elementary = forms.FloatField(required = False,
                    label = "Years in Elementary School:", 
                    widget=forms.TextInput(
                    attrs={'class':'entry-field numeric-field'}))
    #-------End hidden childhood fields------
    #-------These fields about transfer are normally hidden------
    transfer_school_name = forms.CharField(required = False,
                label="School:",
                    widget=forms.TextInput(attrs={'class':'entry-field',
                                                  'size':'40'}))
    transfer_direction= forms.ChoiceField(required=False,
                    label = "Transfer In/Out:",
                    choices=(("In","In"), ("Out","Out")), initial="In")
    transfer_date = forms.DateField(required=False, label = "Date",
                widget=forms.DateInput(format="%m/%d/%Y", attrs={"size":12,
           "class":"date-mask popup-calendar history-datefield entry-field"}))
    transfer_history = forms.CharField(required=False, widget=
                                      forms.HiddenInput, initial="NOTSET")
    transfer_other_info = forms.CharField(required=False, 
                    label='Further Information',
                    max_length=1000, widget=forms.Textarea(
                    attrs={'cols':50, 'rows':3, 'class':'entry-field'}))
    #------End hidden transfer fields-----
    student_status_name = forms.CharField(required=False, 
                            label = "Enrollment Status:*",
                    widget=forms.TextInput(attrs={'class':
                        'autofill required history-entry entry-field'}))
    student_status = forms.CharField(required=True, 
                                   widget=forms.HiddenInput)
    student_status_change_date = forms.DateField(required=True, 
            widget=forms.DateInput(format="%m/%d/%Y", attrs={"size":12,
            "class":"date-mask popup-calendar history-datefield required entry-field"}))
    student_status_history = forms.CharField(required=False, 
                                widget=forms.HiddenInput, initial="NOTSET")
    section = forms.CharField(required=False, 
                              widget=forms.HiddenInput)
    class_year = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class':'autofill history-entry entry-field'}))
    class_year_change_date = forms.DateField(required=False, 
                    widget=forms.DateInput(format="%m/%d/%Y",
                                           attrs={"size":12,
                    "class":"date-mask popup-calendar history-datefield entry-field"}))
    class_year_history = forms.CharField(required=False, 
                            widget=forms.HiddenInput, initial="NOTSET")
    section_name = forms.CharField(required=False, label="Section",
            widget=forms.TextInput(attrs={
                        'class':'autofill history-entry entry-field'}))
    section_change_date = forms.DateField(required=False, 
                widget=forms.DateInput(format="%m/%d/%Y", attrs={"size":12,
           "class":"date-mask popup-calendar history-datefield entry-field"}))
    section_history = forms.CharField(required=False, widget=
                                      forms.HiddenInput, initial="NOTSET")
    section = forms.CharField(required=False, 
                              widget=forms.HiddenInput)
    student_major_name = forms.CharField(required=False, 
                            label = "Student Major",
                    widget=forms.TextInput(attrs={'class':
                        'autofill history-entry entry-field'}))
    student_major = forms.CharField(required=False, 
                                   widget=forms.HiddenInput)
    student_major_change_date = forms.DateField(required=False, 
            widget=forms.DateInput(format="%m/%d/%Y", attrs={"size":12,
            "class":"date-mask popup-calendar history-datefield entry-field"}))
    student_major_history = forms.CharField(required=False, 
                                widget=forms.HiddenInput, initial="NOTSET")
    other_activities = forms.CharField(required=False, 
                        widget=forms.TextInput(attrs={
                            "readonly":"readonly","class":"entry-field"}))
    other_activities_history = forms.CharField(required=False, 
                            widget=forms.HiddenInput,initial="NOTSET")
    special_designation_name = forms.CharField(required=False, 
            label="Student<br/>Designation:", widget=forms.TextInput(attrs={
                        'class':'autofill history-entry entry-field'}))
    special_designation_change_date = forms.DateField(required=False, 
        widget=forms.DateInput(format="%m/%d/%Y", attrs={"size":12,
        "class":"date-mask popup-calendar history-datefield entry-field"}))
    special_designation_history = forms.CharField(required=False, widget=
                                      forms.HiddenInput, initial="NOTSET")
    special_designation = forms.CharField(required=False, 
                              widget=forms.HiddenInput)
    ranking = forms.CharField(required=False, 
                              widget=forms.TextInput(attrs={"size":20, 
                                    "class":"history-entry entry-field"}))
    ranking_change_date = forms.DateField(required=False, 
                widget=forms.DateInput(format="%m/%d/%Y", attrs={"size":12, 
         "class":"date-mask popup-calendar history-datefield entry-field"}))
    ranking_history = forms.CharField(required=False, 
                                      widget=forms.HiddenInput)
    element_names = ["birthdate", "family", "birth_community",
                     "birth_community_other", "birth_municipality",
                     "birth_municipality_other","birth_province",
                     "birth_other_country",
                     "elementary_school","elementary_gpa",
                     "elementary_graduation_date", "years_in_elementary",
                     "student_status", "student_status_change_date",
                     "student_status_history",
                     "class_year", "class_year_change_date",
                     "class_year_history",
                     "section", "section_change_date", "section_history",
                     "student_major", "student_major_change_date", 
                     "student_major_history",
                     "other_activities", "other_activities_history",
                     "ranking", "ranking_change_date", "ranking_history",
                     "special_designation", 
                     "special_designation_change_date",
                     "special_designation_history",
                     "transfer_school_name","transfer_direction",
                     "transfer_other_info","transfer_date",
                     "transfer_history"]
    parent_form = PersonForm

    def create_new_instance(self):
        return SchoolDB.models.Student(
            first_name = self.cleaned_data["first_name"],
            last_name = self.cleaned_data["last_name"])
    
    def save(self, instance):
        """
        Perform a standard save action. Then, if a section is set, mark
        the section to require an update.
        """
        saved_instance = BaseStudentDBForm.save(self, instance)
        if (saved_instance and saved_instance.section):
            saved_instance.section.student_info_changed(saved_instance)
        return saved_instance

    def modify_params(self, param_dict):
        for name_tuple in (("student_status", "Enrollment Status","*"),
                           ("class_year", "Class Year", ""),
                           ("section","Section", ""),
                           ("student_major","Student Major", ""),
                           ("ranking","Ranking", ""),
                           ("special_designation", 
                            "Student<br/>Designation", "")):
            add_history_field_params(param_dict, name_tuple)
    
    @staticmethod
    def add_extras(instance, data):
        """
        Load information about the siblings and the parents into two
        json formatted fields for use by javascript in the page to fill
        in the siblings and the parents lists. This is essentially an
        imitation of the ajax action but the javascript is performed on
        page load.
        """
        try:
            if (instance and instance.family):
                family = instance.family
                siblings_list = family.get_siblings()
                #remove self from list. Must use key to compare
                my_key = instance.key()
                for i in range(0, len(siblings_list)):
                    if (my_key == siblings_list[i].key()):
                        del siblings_list[i]
                        break                    
                result_list, key_list,combined_list = \
                           SchoolDB.assistant_classes.QueryMaker.get_keys_names_fields_from_object_list(
                               siblings_list, False, 
                               ["class_year", "section"])
                if (len(result_list) > 0):
                    data["siblings_initial_val"] = \
                        simplejson.dumps(result_list)
                parents_list = family.get_parents()
                result_list, key_list, combined_list = \
                           SchoolDB.assistant_classes.QueryMaker.get_keys_names_fields_from_object_list(
                               parents_list, False, ["contact_order",
                                                     "cell_phone","relationship"])
                if (len(result_list) > 0):
                    data["parents_initial_val"] = \
                        simplejson.dumps(result_list)
        except:
            instance.family = None

    @staticmethod
    def initialize(data):
        PersonForm.initialize(data)
        initialize_fields([
            ("birth_community", "birth_community_name"),
            ("birth_municipality", "birth_municipality_name"),              
            ("birth_province", "birth_province_name"),              
            ("section", "section_name"),
            ("student_status","student_status_name"),
            ("student_major","student_major_name"),
            ("special_designation","special_designation_name")], data)
        #initialize_student_transfer(data)

    @staticmethod
    def generate_class_javascript_code(javascript_generator):
        stat = javascript_generator.add_autocomplete_field(
            class_name = "student_status")
        stat.add_extra_params({"use_class_query":"!true!"})
        clsyr = javascript_generator.add_autocomplete_field(
            class_name = "class_year", field_name = "id_class_year")
        clsyr.set_local_choices_list(SchoolDB.choices.ClassYearNames)
        sect = javascript_generator.add_autocomplete_field(
            class_name = "section")
        sect.add_dependency(clsyr, False)
        major = javascript_generator.add_autocomplete_field(
            class_name = "student_major")
        major.add_extra_params({"use_class_query":"!true!"})
        sd = javascript_generator.add_autocomplete_field(
            class_name = "special_designation")
        sd.add_extra_params({"use_class_query":"!true!"})
        brthprov = javascript_generator.add_autocomplete_field(
            class_name = "province", 
            field_name = "id_birth_province_name",
            key_field_name = "id_birth_province")
        brthmuni = javascript_generator.add_autocomplete_field(
            class_name = "municipality", 
            field_name = "id_birth_municipality_name",
            key_field_name = "id_birth_municipality")
        brthmuni.add_dependency(brthprov, True)
        brthcom = javascript_generator.add_autocomplete_field(
            class_name = "community", 
            field_name = "id_birth_community_name",
            key_field_name = "id_birth_community")
        brthcom.add_dependency(brthmuni, True)
        return (stat, clsyr, sect, major, sd, brthcom, brthmuni, brthprov)

    def generate_javascript_code(self, javascript_generator):
        self.parent_form.generate_javascript_code(self, 
                                                  javascript_generator)
        StudentForm.generate_class_javascript_code(javascript_generator)

    @staticmethod
    def generate_select_javascript_code(javascript_generator, 
                                        select_field):
        
        query = SchoolDB.models.StudentStatus.all()
        query.filter("default_choice =", True)
        default_status = query.get()
        if (default_status):
            student_status_value = str(default_status.key())
            student_status_name_value = unicode(default_status)
        else:
            student_status_value = ""
            student_status_name_value = ""
        javascript_generator.add_javascript_params ({
            "fieldName":"Family Name", "auxFields":[
                {"name":"student_status_name","label":"Enrollment Status",
                 "fieldType":"view", "value":student_status_name_value},
                {"name":"student_status","label":"Hidden",
                 "fieldType":"hidden", "value": student_status_value},
                {"name":"class_year","label":"Class Year",
                 "fieldType":"view"},
                {"name":"section_name","label":"Section","fieldType":"view"},
                {"name":"section","label":"Hidden","fieldType":"hidden"}]})
        (stat, clsyr, sect, stumjr, spdes, brthc, brthmuni, brthprov) = \
         StudentForm.generate_class_javascript_code(javascript_generator)
        select_field.add_dependency(stat, True)
        select_field.add_dependency(clsyr, False)
        select_field.add_dependency(sect, True)
        select_field.add_extra_params({
            "extra_fields":
            "first_name|middle_name|gender|section|class_year",
            "format": "last_name_only",
            "leading_value_field":"last_name"})
        
    @staticmethod
    def initialize_form_params(select_form):
        status_field = select_form.select_class.base_fields["student_status"]
        status_name_field = select_form.select_class.base_fields["student_status_name"]
        query = SchoolDB.models.StudentStatus.all()
        query.filter("name =", "Enrolled")
        default_status = query.get()
        if (default_status):
            status_field.initial = str(default_status.key())
            status_name_field.initial = unicode(default_status)
#----------------------------------------------------------------------

class StudentGroupingForm(BaseStudentDBForm):
    """
    This form is never used by itself. It is a parent form of the base 
    class for Sections and Classes
    """
    name = forms.CharField(required=True, max_length=50,
                           widget=forms.TextInput(attrs=
                            {'class':'required  entry-field'}))
    teacher_name = forms.CharField(required=False, label="Teacher",
                                   widget=forms.TextInput(attrs={'class':
                                        'autofill history-entry entry-field'}))
    teacher = forms.CharField(required=False,
                              widget=forms.HiddenInput(), initial = "")
    teacher_change_date = forms.DateField(required=False, 
                widget=forms.DateInput(format="%m/%d/%Y", attrs={'class':
                    'popup-calendar date-mask history-datefield entry-field'}))
    teacher_history = forms.CharField(required=False,
                                widget=forms.HiddenInput, initial="NOTSET")
    element_names = ["name", "teacher", "teacher_change_date", 
                     "teacher_history"]
    parent_form = BaseStudentDBForm

    def generate_choices(self):
        self.fields["teacher_name"].choices = \
            SchoolDB.models.create_choice_array_from_class(
                SchoolDB.models.Teacher, 
                SchoolDB.models.getActiveDatabaseUser().get_active_organization_key(),
                "last_name")

    def modify_params(self, param_dict):
        add_history_field_params(param_dict, ("teacher", "Teacher", ""))

    def generate_javascript_code(self, javascript_generator):
        tchr = javascript_generator.add_autocomplete_field(
            class_name = "teacher")

    @staticmethod
    def initialize(data):
        initialize_fields([("teacher", "teacher_name")], data)

    def save(self, instance, model_class = None):
        """
        Perform normal actions and then, if a teacher has been assigned
        to the grouping add this student grouping to the teacher's
        associated database user's interesting list. This will
        automatically add classes and sections to the teacher's chosen
        list. This function can be called repeatedly because the
        support function will only add the student grouping once to the
        teacher's list.
        """
        instance = BaseStudentDBForm.save(self, instance)
        teacher = convert_to_instance_value(instance, "teacher",
                                        self.cleaned_data["teacher"])
        if (teacher and model_class):
            teacher.add_to_interesting_instances(model_class, instance.key())
        return instance

#----------------------------------------------------------------------      
class ClassroomForm(BaseStudentDBForm):
    name = forms.CharField(required=True, max_length=60, label="Name*:",
                           widget=forms.TextInput(attrs=
                            {'class':'required entry-field', 'minlength':'3'}))
    active = forms.BooleanField(label="Active", required=False)
    location = forms.CharField(required=False, max_length=1000,
                        label="Location:",
                        widget=forms.Textarea(attrs={'cols':50, 'rows':3,
                                                    'class':'entry-field'}))
    other_information = forms.CharField(required=False, max_length=1000,
                        label="Other Information:",
                        widget=forms.Textarea(attrs={'cols':50, 'rows':3,
                                                    'class':'entry-field'}))
    parent_key = forms.CharField(required=False,  
                                 widget=forms.HiddenInput, initial="NOTSET")
    element_names = ["name", "active","location","other_information"]
    parent_form = BaseStudentDBForm

    def create_new_instance(self):
        return  SchoolDB.models.Classroom.create(name = 
                self.cleaned_data["name"])
#----------------------------------------------------------------------      

class SectionForm(StudentGroupingForm):
    class_year = forms.CharField(required=True,
                                 widget=forms.TextInput(attrs={
                                     'class':'autofill required entry-field'}))
    section_type_name = forms.CharField(required = False, 
                label="Section Type:", widget=forms.TextInput(attrs=
                {'class':'autofill entry-field'}))
    section_type = forms.CharField(required = False, 
                                   widget=forms.HiddenInput, initial="")
    classroom_name = forms.CharField(required=False, label="Classroom",
                    widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    classroom = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")
    element_names = ["section_type", "class_year", "classroom"]
    parent_form = StudentGroupingForm

    def create_new_instance(self):
        return SchoolDB.models.Section(
            parent = SchoolDB.models.getActiveDatabaseUser().get_active_organization(),
            name = self.cleaned_data["name"])

    @staticmethod
    def generate_class_javascript_code(javascript_generator):       
        clsyr = javascript_generator.add_autocomplete_field(
            class_name = "class_year", field_name = "id_class_year")
        clsyr.set_local_choices_list(SchoolDB.choices.ClassYearNames)
        clsrm = javascript_generator.add_autocomplete_field("classroom")
        sect_type = javascript_generator.add_autocomplete_field(
            class_name = "section_type")
        sect_type.add_extra_params({"use_class_query":"!true!"})
        return (clsyr, clsrm, sect_type)

    def generate_javascript_code(self, javascript_generator):
        self.parent_form.generate_javascript_code(self,
                                                  javascript_generator)
        SectionForm.generate_class_javascript_code(javascript_generator)

    @staticmethod    
    def generate_select_javascript_code(javascript_generator, 
                                        select_field):      
        javascript_generator.add_javascript_params (
            {"auxFields":[{"name":"class_year","label":"Class Year",
                           "fieldType":"view"}]})
        clsyr, clsrm, sect_type = \
             SectionForm.generate_class_javascript_code(
            javascript_generator)
        select_field.add_dependency(clsyr, is_key = False)
        select_field.add_dependency(clsrm, False)
        select_field.add_extra_params({"filter_school":"false",
                                    "extra_fields":"class_year|teacher"})

    @staticmethod
    def initialize(data):
        SectionForm.parent_form.initialize(data)
        initialize_fields([("section_type", "section_type_name"),
                           ("classroom", "classroom_name")], data)

    def modify_params(self, param_dict):
        """
        Override the parent form StudentGrouping action for the
        teacher field to generate a different name for the teacher
        field.
        """
        add_history_field_params(param_dict, ("teacher", "Advisor", ""))
    
    def save(self, instance):
        """
        Perform normal actions and then, if a teacher has been assigned
        as section advisor add the sectin to the teachers "my sections"
        list. There is no problem performing this repeatedly -- nothing
        will be added to the teachers record if it is already there.
        """
        StudentGroupingForm.save(self, instance, 
                    model_class = Section)
        
#---------------------------------------------------------------------- 

class OrganizationForm(BaseStudentDBForm):
    name = forms.CharField(required=True, max_length=60, label="Name*",
                widget=forms.TextInput(attrs={'class':'required entry-field', 
                                                         'minlength':'3'}))
    general_info = forms.CharField(required=False,
                    max_length=1000, widget=forms.Textarea(
                        attrs={'cols':50, 'rows':3, 'class':'entry-field'}))
    address = forms.CharField(required=False, max_length=1000,
                widget=forms.Textarea(attrs={'cols':50, 'rows':3,
                                                'class':'entry-field'}))
    postal_address = forms.CharField(required=False, max_length=1000,
                        widget=forms.Textarea(attrs={'cols':50, 'rows':3,
                                                    'class':'entry-field'}))  
    contacts_initial_val = forms.CharField(required=False,
                                           widget=forms.HiddenInput)
    element_names = ["name", "general_info", "address", "postal_address"]
    parent_form = BaseStudentDBForm

    @staticmethod
    def add_extras(instance, data):
        """
        Load the list of contacts.
        """
        if (instance):
            try:
                contacts_list, contacts_string, key_list = \
                             SchoolDB.models.Organization.get_contacts_list(
                                 instance, ["person","telephone"])
                if (len(contacts_list) > 0):
                    data["contacts_initial_val"] = simplejson.dumps(contacts_list)
            except:
                pass

    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        pass

#----------------------------------------------------------------------      

class SchoolForm(OrganizationForm):

    division_name = forms.CharField(required = True, label="Division*",
                                    widget=forms.TextInput(attrs=
                                                           {'class':'ui-widget autofill required entry-field'}))
    division = forms.CharField(required = False, 
                               widget=forms.HiddenInput, initial="")
    municipality_name = forms.CharField(required = False, 
                                        label="Municipality*",
                                        widget=forms.TextInput(attrs=
                                                               {'class':'ui-widget autofill required entry-field'}))
    municipality = forms.CharField(required = False, 
                                   widget=forms.HiddenInput, initial="")
    principal_name = forms.CharField(required = False, 
                                     label="Principal", widget=forms.TextInput(attrs=
                                                                               {'class':'ui-widget autofill entry-field'}))
    principal = forms.CharField(required = False, 
                                widget=forms.HiddenInput, initial="")
    school_creation_date = forms.DateField(required=False,
                    widget=forms.DateInput(format="%m/%d/%Y",
                                attrs={"class":"date-mask entry-field"}))
    municipality_choice_name = forms.CharField(required = False, 
                    label="Municipality", widget=forms.TextInput(attrs=
                                        {'class':'autofill entry-field'}))
    municipality_choice = forms.CharField(required = False, 
                                          widget=forms.HiddenInput, initial="")
    students_municipalities = forms.CharField(required = False, 
                                              widget=forms.HiddenInput)  
    element_names = ["division", "municipality", "principal", 
                     "school_creation_date"]
    parent_form = OrganizationForm

    def create_new_instance(self):
        return SchoolDB.models.School(name = self.cleaned_data["name"])

    def generate_javascript_code(self, javascript_generator):
        div = javascript_generator.add_autocomplete_field(
            class_name = "division")
        muni = javascript_generator.add_autocomplete_field(
            class_name = "municipality")
        muni.add_dependency(div, True)
        prin = javascript_generator.add_autocomplete_field(
            class_name = "administrator", field_name="id_principal_name",
            key_field_name = "id_principal")
        #muni_ch = javascript_generator.add_autocomplete_field(
            #class_name = "municipality", 
            #field_name="id_municipality_choice_name",
            #key_field_name="id_municipality_choice")
        #muni_ch.add_dependency(div, True)

    @staticmethod
    def generate_select_javascript_code(javascript_generator, 
                                        select_field):
        javascript_generator.add_javascript_params (
            {"auxFields":[
                {"name":"division_name","label":"Division",
                 "fieldType":"view"},
                {"name":"division","label":"Hidden", "fieldType":"hidden"}]})
        select_field.add_extra_params({ "extra_fields":"division"})
        division = javascript_generator.add_autocomplete_field(
            class_name = "division")
        select_field.add_dependency(division, True)

    @staticmethod
    def initialize(data):
        initialize_fields([("division", "division_name"),
                           ("municipality", "municipality_name"),   
                           ("principal", "principal_name")], data)

    @staticmethod
    def add_extras(instance, data):
        """
        For School forms, convert the list of the students 
        municipalities.
        """
        OrganizationForm.add_extras(instance,data)
        if (instance):
            try:
                muni_list = instance.get_students_municipalities()
                json_string = simplejson.dumps(muni_list)
                data["students_municipalities"] = json_string
            except:
                pass

    def set_values_from_form(self, instance):
        """
        Load the list of students municipalities back into the database
        for the school.
        """
        OrganizationForm.set_values_from_form(self,instance)
        try:
            json_muni_data = self.cleaned_data[
                "students_municipalities"]
            if json_muni_data:
                data_list = simplejson.loads(json_muni_data)
                instance.save_municipalities_list(data_list)
        except ValueError, err:
            #db.errors['__all__'] = unicode(err)
            pass


#----------------------------------------------------------------------      

class MunicipalityForm(OrganizationForm):
    province_name = forms.CharField(required = True, label="Province*",
                widget=forms.TextInput(attrs=
                    {'class':'autofill ui-widget required entry-field'}))
    province = forms.CharField(required = False, widget=forms.HiddenInput, 
                               initial="")
    division_name = forms.CharField(required = False, label="Division",
                widget=forms.TextInput(attrs=
                                {'class':'autofill entry-field'}))
    division = forms.CharField(required = False, widget=forms.HiddenInput, 
                               initial="")
    type = forms.ChoiceField(required=False, label="Type",
                    choices=SchoolDB.choices.convert_to_form_choice_list(
                                 SchoolDB.choices.MunicipalityType))
    element_names = ["province", "division", "type"]
    parent_form = OrganizationForm

    def create_new_instance(self):
        return SchoolDB.models.Municipality(name = self.cleaned_data["name"])

    def generate_javascript_code(self, javascript_generator):
        prov = javascript_generator.add_autocomplete_field(
            class_name = "province")
        div = javascript_generator.add_autocomplete_field(
            class_name = "division")
        div.add_dependency(prov, True)

    @staticmethod
    def generate_select_javascript_code(javascript_generator, 
                                        select_field):
        javascript_generator.add_javascript_params (
            {"titleNamePlural":"Municipalities","auxFields":[
                {"name":"province_name","label":"Province",
                 "fieldType":"view"},
                {"name":"province","label":"Hidden", "fieldType":"hidden"}]})
        prov = javascript_generator.add_autocomplete_field(
            class_name = "province")
        select_field.add_dependency(prov, True)


    @staticmethod
    def initialize(data):
        initialize_fields([("province", "province_name"),
                           ("division","division_name")], data)

#----------------------------------------------------------------------      

class CommunityForm(OrganizationForm):
    province_name = forms.CharField(required = False, label="Province*",
                                    widget=forms.TextInput(attrs=
                                    {'class':'autofill required entry-field'}))
    province = forms.CharField(required = False, widget=forms.HiddenInput, 
                               initial="")
    municipality_name = forms.CharField(required = True, 
                label="Municipality*", widget=forms.TextInput(attrs=
                {'class':'autofill required entry-field'}))
    municipality = forms.CharField(required = False, 
                                   widget=forms.HiddenInput, initial="")
    element_names = ["municipality"]
    parent_form = OrganizationForm

    def create_new_instance(self):
        return SchoolDB.models.Community.create(self.cleaned_data["name"],
                               self.cleaned_data["municipality"])

    @staticmethod
    def generate_class_javascript_code(javascript_generator):
        prov = javascript_generator.add_autocomplete_field(
            class_name = "province")
        mun = javascript_generator.add_autocomplete_field(
            class_name = "municipality")
        mun.add_dependency(prov,True)
        return(prov, mun)

    def generate_javascript_code(self, javascript_generator):
        CommunityForm.generate_class_javascript_code(javascript_generator)

    @staticmethod
    def generate_select_javascript_code(javascript_generator, 
                                        select_field):
        select_field.add_extra_params({
            "extra_fields":"municipality"})
        javascript_generator.add_javascript_params ({"auxFields":[
            {"name":"province_name","label":"Province",
             "fieldType":"view"},
            {"name":"province","label":"Hidden", "fieldType":"hidden"},
            {"name":"municipality_name","label":"Municipality",
             "fieldType":"view"},
            {"name":"municipality","label":"Hidden",
             "fieldType":"hidden"}],
            "titleName":"Barangany", "titleNamePlural":"Barangay",
            "fieldName":"Barangay"})
        prov, mun = CommunityForm.generate_class_javascript_code(
            javascript_generator)
        select_field.add_dependency(prov, True)
        select_field.add_dependency(mun, True)

    @staticmethod
    def initialize(data):
        """
        Perform extra work to initialize these form fields.
        The community does not itself have a province parameter,
        it is implied by the municipality. Get the province
        from the municipality and then load it as if it existed in
        the community.
        """
        data["province"] = ""
        muni = data.get("municipality",None)
        if (muni):
            try:
                munikey = SchoolDB.models.get_key_from_string(muni)
                province = SchoolDB.models.Municipality.get(munikey).province
                data["province"] = str(province.key())
            except:
                pass
        initialize_fields([("municipality", "municipality_name"),
                           ("province","province_name")], data)

#----------------------------------------------------------------------   
class RegionForm(OrganizationForm):
    parent_form = OrganizationForm
    area_name = forms.CharField(required = False, label="Area Name")
    
    element_names = ["area_name"]
    def create_new_instance(self):
        return SchoolDB.models.Region(name = self.cleaned_data["name"])

#----------------------------------------------------------------------      

class ProvinceForm(OrganizationForm):
    region_name = forms.CharField(required = False, label="Region",
                                  widget=forms.TextInput(attrs=
                                        {'class':'autofill entry-field'}))
    region = forms.CharField(required = False, widget=forms.HiddenInput, 
                             initial="")
    element_names = ["region"]
    parent_form = OrganizationForm

    def create_new_instance(self):
        return SchoolDB.models.Province(name = self.cleaned_data["name"])

    def generate_javascript_code(self, javascript_generator):
        reg = javascript_generator.add_autocomplete_field(
            class_name = "region")

#----------------------------------------------------------------------   

class ContactForm(BaseStudentDBForm):
    name = forms.CharField(required=True, max_length=60, label="Office*",
                           widget=forms.TextInput(attrs=
                                                  {'class':'required entry-field','minlength':'3'}))
    person = forms.CharField(required=False, max_length=60, 
                        label="Contact Person", widget=forms.TextInput(attrs=
                                                        {'class':'entry-field'}))
    telephone = forms.CharField(required=False, max_length=60,
                            widget=forms.TextInput(attrs={'class':'entry-field'}))
    fax = forms.CharField(required=False, max_length=60,
                          widget=forms.TextInput(attrs={'class':'entry-field'}))
    email = forms.EmailField(required=False, max_length=60,
                            widget=forms.TextInput(attrs={'class':'entry-field'}))
    general_info = forms.CharField(required=False, max_length=1000,
                        widget=forms.Textarea(attrs={'cols':50, 'rows':3,
                                                    'class':'entry-field'}))
    parent_key = forms.CharField(required=False,  
                                 widget=forms.HiddenInput, initial="NOTSET")
    element_names = ["name", "telephone","fax","email",
                     "person", "general_info"]
    parent_form = BaseStudentDBForm

    def create_new_instance(self):
        organization_key =  SchoolDB.models.get_key_from_string( 
            self.cleaned_data["parent_key"])
        return  SchoolDB.models.Contact.create(name = self.cleaned_data["name"],
                               organization = organization_key)


#----------------------------------------------------------------------      

class MultiLevelDefinedForm(BaseStudentDBForm):
    name = forms.CharField(required=True, max_length=60, label="Name*",
                           widget=forms.TextInput(attrs={'class':'required entry-field', 
                                                         'minlength':'2'}))
    organization = forms.ChoiceField(required=False)
    #organization = forms.CharField(required=False, label="Organization",
            #widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    other_information = forms.CharField(required=False, 
                                        max_length = 250, widget=forms.Textarea(
                                            attrs={'cols':50, 'rows':2, 'class':'entry-field'}))    
    element_names = ["name", "organization", "other_information"]
    parent_form = BaseStudentDBForm

    def generate_choices(self):
        self.fields["organization"].choices = \
            SchoolDB.models.MultiLevelDefined.create_org_choice_list(
                SchoolDB.models.getActiveDatabaseUser().get_active_organization())

#----------------------------------------------------------------------   

class DateBlockForm(MultiLevelDefinedForm):
    start_date = forms.DateField(required=True, label="Start Date*",
                                 widget=forms.DateInput(format="%m/%d/%Y",
                                attrs={'class':'date-mask required entry-field'}))
    end_date = forms.DateField(required=True, label="End Date*",
                               widget=forms.DateInput(format="%m/%d/%Y",
                                attrs={'class':'date-mask required entry-field'}))
    parent_form = MultiLevelDefinedForm

    element_names = ["start_date", "end_date"]

    def generate_javascript_code(self, javascript_generator):
        javascript_generator.add_javascript_code(
            """
            $('#id_start_date').datepicker({changeMonth: true,
                changeYear: true});
            $('#id_end_date').datepicker({changeMonth: true, 
            changeYear: true});
            """)

    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        select_field.add_extra_params({
            "extra_fields":"organization|start_date|end_date",
            "use_class_query":"True"})


#----------------------------------------------------------------------
class SchoolYearForm(DateBlockForm):
    parent_form = DateBlockForm

    def create_new_instance(self):
        return SchoolDB.models.SchoolYear.create(self.cleaned_data["name"], 
                                 db.Key(self.cleaned_data["organization"]))
    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        DateBlockForm.generate_select_javascript_code(
            javascript_generator, select_field)
        javascript_generator.add_javascript_params ({
            "titleName":"School Year", 
            "titleNamePlural":"School Years"})


#----------------------------------------------------------------------
class SchoolDayForm(MultiLevelDefinedForm):
    date = forms.DateField(required=True,
        widget=forms.DateInput(format="%m/%d/%Y",
        attrs={'class':'popup-calendar date-mask required entry-field'}))
    day_type = forms.CharField(required=False,
                                      widget=forms.TextInput(attrs=
                                        {'class':'autofill entry-field'}))
    #active_classyears = forms.MultipleChoiceField(
                    #widget=forms.CheckboxSelectMultiple(choices = 
                                                        #["a","b","c"]))
    first_year = forms.BooleanField(required=False, initial="True")
    second_year = forms.BooleanField(required=False, initial="True")
    third_year = forms.BooleanField(required=False, initial="True")
    fourth_year = forms.BooleanField(required=False, initial="True")
    parent_form = MultiLevelDefinedForm
    element_names = ["date", "school_year", "day_type", "first_year", "second_year", "third_year", "fourth_year"]

    def create_new_instance(self):        
        return SchoolDB.models.SchoolDay.create(self.cleaned_data["date"],
                                self.cleaned_data["organization"])

    def generate_javascript_code(self, javascript_generator):
        org = javascript_generator.add_autocomplete_field(
            class_name = "school_year", field_name = 
            'id_school_year_name', key_field_name = 'id_school_year')
        daytype = javascript_generator.add_autocomplete_field(
            class_name = "day_type", field_name = 
            'id_day_type')
        daytype.set_local_choices_list(SchoolDB.choices.SchoolDayType)

    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        select_field.add_extra_params({
            "extra_fields":"date|organization|day_type",
            "use_class_query":"True"})
        javascript_generator.add_javascript_params ({
            "titleName":"School Day", 
            "titleNamePlural":"School Days"})

#----------------------------------------------------------------------
class GradingPeriodForm(DateBlockForm):
    parent_form = DateBlockForm

    def create_new_instance(self):
        return SchoolDB.models.GradingPeriod.create(self.cleaned_data["name"], 
                                    db.Key(self.cleaned_data["organization"]))
    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        DateBlockForm.generate_select_javascript_code(
            javascript_generator, select_field)
        javascript_generator.add_javascript_params ({
            "titleName":"Grading Period", 
            "titleNamePlural":"Grading Periods"})
        
#----------------------------------------------------------------------

class SchoolCalendarForm(MultiLevelDefinedForm):
    date = forms.DateField(required=True,
        widget=forms.DateInput(format="%m/%d/%Y",
        attrs={'class':'popup-calendar date-mask required entry-field'}))
    school_year_name = forms.CharField(required=True, label="School Year",
                                       widget=forms.TextInput(attrs=
                                        {'class':'autofill entry-field'}))
    school_year = forms.CharField(widget=forms.HiddenInput,initial="")
    school_day_type = forms.CharField(required=False,
                                      widget=forms.TextInput(attrs=
                                        {'class':'autofill entry-field'}))
    parent_form = MultiLevelDefinedForm

    element_names = ["date", "school_year", "school_day_type"]

    def create_new_instance(self):
        return SchoolDB.models.SchoolDay.create(self.cleaned_data["name"], 
                                db.Key(self.cleaned_data["organization"]))

    def generate_javascript_code(self, javascript_generator):
        org = javascript_generator.add_autocomplete_field(
            class_name = "school_year", field_name = 
            'id_school_year_name', key_field_name = 'id_school_year')
        daytype = javascript_generator.add_autocomplete_field(
            class_name = "school_day_type", field_name = 
            'id_school_day_type')
        daytype.set_local_choices_list(SchoolDB.choices.SchoolDayType)

    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        javascript_generator.add_javascript_params ({
            "titleName":"School Calendar", 
            "titleNamePlural":"School Calendars"})

#----------------------------------------------------------------------      
class ClassPeriodForm(MultiLevelDefinedForm):
    start_time = forms.TimeField(required=True, label="Start Time*",
                widget=forms.TextInput(attrs={'class':' required time-mask entry-field'}))
    end_time = forms.TimeField(required=True, label="End Time*",
                widget=forms.TextInput(attrs={'class':'required time-mask entry-field'}))
    parent_form = MultiLevelDefinedForm

    element_names = ["start_time", "end_time"]

    def create_new_instance(self):
        return SchoolDB.models.ClassPeriod.create(name = self.cleaned_data["name"], 
                    organization = db.Key(self.cleaned_data["organization"]))

    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        select_field.add_extra_params({
            "extra_fields":"organization|start_time|end_time",
            "use_class_query":"True"})
        javascript_generator.add_javascript_params (
            {"titleName":"Class Period", "titleNamePlural":"Class Periods",
             "fieldName":"Class Period Name"})

#----------------------------------------------------------------------      
class SubjectForm(MultiLevelDefinedForm):
    used_in_achievement_tests = forms.BooleanField(
        label="Used In Achievement Tests", required=False)
    taught_by_section = forms.BooleanField(
        label="Taught By Sections", required=False)
    parent_form = MultiLevelDefinedForm
    element_names=["used_in_achievement_tests", "taught_by_section"]
    
    def create_new_instance(self):
        return SchoolDB.models.Subject.create(self.cleaned_data["name"], 
                              db.Key(self.cleaned_data["organization"]))

    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        select_field.add_extra_params({
            "extra_fields":"organization", "use_class_query":"True"})
        javascript_generator.add_javascript_params (
            {"titleName":"Curriculum Subject", 
             "titleNamePlural":"Curriculum Subjects",
             "fieldName":"Subject Name"})

#----------------------------------------------------------------------  
class SectionTypeForm(MultiLevelDefinedForm):
    parent_form = MultiLevelDefinedForm

    def create_new_instance(self):
        return SchoolDB.models.SectionType.create(self.cleaned_data["name"], 
                              db.Key(self.cleaned_data["organization"]))

    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        select_field.add_extra_params({
            "extra_fields":"organization", "use_class_query":"True"})
        javascript_generator.add_javascript_params (
            {"titleName":"Section Type", 
             "titleNamePlural":"Section Types",
             "fieldName":"Section Type Name"})

#----------------------------------------------------------------------  
class StudentMajorForm(MultiLevelDefinedForm):

    name_abbreviation = forms.CharField(required=False, label="Name Abbreviation")
    parent_form = MultiLevelDefinedForm
    element_names = ["name_abbreviation"]
    
    def create_new_instance(self):
        return SchoolDB.models.StudentMajor.create(self.cleaned_data["name"], 
                              db.Key(self.cleaned_data["organization"]))

    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        select_field.add_extra_params({
            "extra_fields":"organization", "use_class_query":"True"})
        javascript_generator.add_javascript_params (
            {"titleName":"Student Major", 
             "titleNamePlural":"Student Majors",
             "fieldName":"Student Major Name"})

#----------------------------------------------------------------------  
class SpecialDesignationForm(MultiLevelDefinedForm):
    parent_form = MultiLevelDefinedForm

    def create_new_instance(self):
        return SchoolDB.models.SpecialDesignation.create(self.cleaned_data["name"], 
                              db.Key(self.cleaned_data["organization"]))

    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        select_field.add_extra_params({
            "extra_fields":"organization", "use_class_query":"True"})
        javascript_generator.add_javascript_params (
            {"titleName":"Special Designation", 
             "titleNamePlural":"Special Designations",
             "fieldName":"Special Designation"})

#----------------------------------------------------------------------
class SchoolDayTypeForm(BaseStudentDBForm):
    name = forms.CharField(required=True, label="School Day Type Name")
    active_morning = forms.BooleanField(required=False, 
            label="School In Session in Morning")
    active_afternoon = forms.BooleanField(required=False, 
            label="School In Session in Afternoon")
    default_choice = forms.BooleanField(required=False, 
                label="Default Choice")
    other_information = forms.CharField(required=False,
                    label="Other Information",
                    max_length =250,widget=forms.Textarea(
                    attrs={'cols':50, 'rows':2, 'class':'entry-field'}))
    parent_form = BaseStudentDBForm
    element_names = ["name", "active_morning", "active_afternoon",
                     "default_choice", "other_information"]

    def create_new_instance(self):
        return SchoolDB.models.SchoolDayType(name=self.cleaned_data["name"])

#----------------------------------------------------------------------
class StudentStatusForm(BaseStudentDBForm):
    name = forms.CharField(required=True, label="Student Status Type Name")
    active_student = forms.BooleanField(required=False, label="Active Student")
    default_choice = forms.BooleanField(required=False, 
                                        label="Default Choice")
    other_information = forms.CharField(required=False,
                    label="Other Information",
                    max_length =250,widget=forms.Textarea(
                    attrs={'cols':50, 'rows':2, 'class':'entry-field'}))
    parent_form = BaseStudentDBForm
    element_names = ["name", "active_student", "default_choice",
                     "other_information"]

    def create_new_instance(self):
        return SchoolDB.models.StudentStatus(name=self.cleaned_data["name"])

#---------------------------------------------------------------------- 

class DivisionForm(OrganizationForm):
    region_name = forms.CharField(required=True, label="DepEd Region*:",
                                  widget=forms.TextInput(attrs=
                                                         {'class':'autofill required entry-field'}))
    region = forms.CharField(required=False,widget=forms.HiddenInput, 
                             initial="")
    province_name = forms.CharField(required=False, label="Province:",
            widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    province = forms.CharField(required = False, widget=forms.HiddenInput, 
                               initial="")
    element_names = ["region","province"]
    parent_form = OrganizationForm

    def create_new_instance(self):
        return SchoolDB.models.Division(name = self.cleaned_data["name"])  

    @staticmethod
    def initialize(data):
        initialize_fields([("region", "region_name"),
                           ("province","province_name")], data)


    def generate_javascript_code(self, javascript_generator):
        prov = javascript_generator.add_autocomplete_field(
            class_name = "province")
        regn = javascript_generator.add_autocomplete_field(
            class_name = "region")

    @staticmethod
    def generate_select_javascript_code(javascript_generator, 
                                        select_field):
        javascript_generator.add_javascript_params (
            {"auxFields":[
                {"name":"region_name","label":"Region",
                 "fieldType":"view"},
                {"name":"region","label":"Hidden", "fieldType":"hidden"}]})
        region = javascript_generator.add_autocomplete_field(
            class_name = "region")
        select_field.add_dependency(region, True)
        select_field.add_extra_params({
            "extra_fields":"region"})

#---------------------------------------------------------------------- 

class ClassSessionForm(StudentGroupingForm):
    subject_name = forms.CharField(required=True, label="Subject*",
                            widget=forms.TextInput(attrs={'class':'autofill entry-field required'}))
    subject = forms.CharField(required=True,
                              widget=forms.HiddenInput, initial = "")
    student_major_name = forms.CharField(required=False, label="Student Major",
                            widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    student_major = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")
    level = forms.CharField(required=False,
            widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    class_period_name = forms.CharField(required=False, 
                                label="Class Period", widget=forms.TextInput(attrs=
                                            {'class':'autofill entry-field'}))
    class_period = forms.CharField(required=False,
                                   widget=forms.HiddenInput, initial = "") 
    class_year = forms.CharField(required=False,
                    widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    students_assigned_by_section = forms.BooleanField(required=False,
                    label="Students Assigned by Section",  initial=True)
    section_name = forms.CharField(required=False, label="Section",
                    widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    section = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")
    classroom_name = forms.CharField(required=False, label="Classroom",
                    widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    classroom = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")
    school_year_name = forms.CharField(required=False, label="School Year*:",
                    widget=forms.TextInput(attrs={'class':'autofill entry-field required'}))
    school_year = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")
    start_date = forms.DateField(required=False,
                    widget=forms.DateInput(format="%m/%d/%Y",
                        attrs={"class":"date-mask entry-field required"}))
    end_date = forms.DateField(required=False,
                    widget=forms.DateInput(format="%m/%d/%Y",
                        attrs={"class":"date-mask entry-field required"}))
    element_names = ["subject", "student_major", "level", "class_year", 
                     "class_period", "class_year", 
                     "students_assigned_by_section",
                     "section", "classroom", "school_year", 
                     "start_date", "end_date"]
    parent_form = StudentGroupingForm

    def create_new_instance(self):
        return SchoolDB.models.ClassSession.create(self.cleaned_data["name"],
                    SchoolDB.models.getActiveDatabaseUser().get_active_organization()) 

    @staticmethod
    def initialize_dates(data):
        """
        If this class_session does not have the school year set
        initialize the date fields to the current school year. These
        are probably the correct values and the fields are required.
        """
        year_string = data.get("school_year", None)
        if (not year_string):
            #year not yet assigned. Initialize.
            year = SchoolDB.models.get_school_year_for_date(date.today())
            year_string = str(year.key())
            data["school_year"] = year_string
            data["school_year_name"] = unicode(year)
        year = SchoolDB.models.get_instance_from_key_string(year_string)
        if (not data.get("start_date", None) and year):
            data["start_date"] = year.start_date
        if (not data.get("end_date", None)  and year):
            data["end_date"] = year.end_date   
    
    @staticmethod
    def process_request(data):
        """
        This action is performed here so that it will be called even
        on a new instance.
        """
        ClassSessionForm.initialize_dates(data)
        
    @staticmethod
    def initialize(data):
        ClassSessionForm.parent_form.initialize(data)
        ClassSessionForm.initialize_dates(data)
        initialize_fields([("subject", "subject_name"),
                           ("student_major","student_major_name"),
                           ("section", "section_name"), 
                           ("class_period", "class_period_name"),
                           ("classroom", "classroom_name"),
                           ("school_year","school_year_name")], data)

    @staticmethod
    def initialize_form_params(select_form):
        select_form.set_titlename_plural("Classes")

    @staticmethod
    def generate_class_javascript_code(javascript_generator):
        subject = javascript_generator.add_autocomplete_field("subject")
        subject.add_extra_params({"use_class_query":"!true!"})
        studentmjr = javascript_generator.add_autocomplete_field(
            "student_major")
        studentmjr.add_extra_params({"use_class_query":"!true!"})
        level = javascript_generator.add_autocomplete_field(
            class_name = "level", field_name = "id_level")
        level.set_local_choices_list(SchoolDB.choices.ClassLevel)
        clsyr = javascript_generator.add_autocomplete_field(
            class_name = "class_year", field_name = "id_class_year")
        clsyr.set_local_choices_list(SchoolDB.choices.ClassYearNames)
        sect = javascript_generator.add_autocomplete_field(
            class_name = "section", field_name = "id_section_name",
            key_field_name = "id_section")
        sect.add_dependency(clsyr, False)
        prd = javascript_generator.add_autocomplete_field(
            class_name = "class_period")
        prd.add_extra_params({"use_class_query":"!true!"})
        clsrm = javascript_generator.add_autocomplete_field("classroom")
        tchr = javascript_generator.add_autocomplete_field(
            class_name = "teacher")
        schlyr = javascript_generator.add_autocomplete_field(
            class_name = "school_year")
        schlyr.add_extra_params({"ignore_organization":"!true!"})
        return subject,studentmjr,clsyr,sect,prd,clsrm,tchr,schlyr

    def generate_javascript_code(self, javascript_generator):
        subject, studentmjr, clsyr, sect, prd, clsrm, tchr, schlyr = \
               ClassSessionForm.generate_class_javascript_code(
                   javascript_generator)
        javascript_generator.add_javascript_code(
            """
            $('#id_start_date').datepicker({changeMonth: true,
                changeYear: true});
            $('#id_end_date').datepicker({changeMonth: true, 
            changeYear: true});
            """ )


    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        javascript_generator.add_javascript_params (
            {"titleName":"Class",
             "titleNamePlural":"Classes", "fieldName":"Class Name",
             "auxFields":[
                 {"name":"subject_name","label":"Subject",
                  "fieldType":"view"},
                 {"name":"subject","label":"Hidden","fieldType":"hidden"},
                 {"name":"student_major_name","label":"Student Major",
                  "fieldType":"view"},
                 {"name":"student_major","label":"Hidden",
                  "fieldType":"hidden"},
                 {"name":"class_year","label":"Class Year",
                  "fieldType":"view"},
                 {"name":"section_name","label":"Section",
                  "fieldType":"view"},
                 {"name":"section","label":"Hidden","fieldType":"hidden"},
                 {"name":"class_period_name","label":"Period",
                  "fieldType":"view"},
                 {"name":"class_period","label":"Hidden",
                  "fieldType":"hidden"},
                 {"name":"classroom_name","label":"Classroom",
                  "fieldType":"view"},
                 {"name":"classroom","label":"Hidden","fieldType":"hidden"},
                  {"name":"teacher_name","label":"Teacher",
                  "fieldType":"view"},
                 {"name":"teacher","label":"Hidden","fieldType":"hidden"},
                 {"name":"school_year_name","label":"School Year",
                  "fieldType":"view"},
                 {"name":"school_year","label":"Hidden",
                  "fieldType":"hidden"}]
             })
        select_field.add_extra_params({
            "extra_fields":"section|student_major|class_year|class_period|classroom|teacher"})
        (subject, studentmjr, clsyr, sect, prd, clsrm, tchr, schlyr) = \
         ClassSessionForm.generate_class_javascript_code(
             javascript_generator)
        select_field.add_dependency(subject, True)
        select_field.add_dependency(studentmjr, True)
        select_field.add_dependency(clsyr,False)
        select_field.add_dependency(sect, True)
        select_field.add_dependency(prd, True)
        select_field.add_dependency(clsrm,False)
        select_field.add_dependency(tchr, True)
        select_field.add_dependency(schlyr, True)

    def save(self, instance):
        """
        Perform normal actions and then, if a teacher has been assigned
        as teacher for the class add the class to the teachers "my classes"
        list. There is no problem performing this repeatedly -- nothing
        will be added to the teachers record if it is already there.
        """
        StudentGroupingForm.save(self, instance, model_class = ClassSession)

#----------------------------------------------------------------------
class CreateClassSessionsForm(BaseStudentDBForm):
    """
    This form is used to configure and initiate the bulk creation of
    classes. It is meant to be run only once for each set of class
    sessions created. All class sessions can be created from a single
    use of this form is will probably only be used once each year by a
    school. Not only are the class session entities created but also
    all students class records. This means that a single run with a
    2000 student high school could create as many as 10000 database
    entities. Thus the use of this from must be tightly controlled with
    further major checks prior to execution.
    """
    start_date = forms.DateField(required=False,
        widget=forms.DateInput(format="%m/%d/%Y",                    
            attrs={"class":"date-mask entry-field popup-calendar required"}))
    end_date = forms.DateField(required=False,
        widget=forms.DateInput(format="%m/%d/%Y",                    
            attrs={"class":"date-mask entry-field popup-calendar required"}))
    classes_in_section_classrooms = forms.BooleanField(required=False)
    json_request_info = forms.CharField(required = False, 
                widget=forms.HiddenInput)
    
    def save(self, instance):
        """
        This is a replacement for the normal save action. Nothing will
        saved. The data will be used to initiate the creation of the
        class sessions.
        """
        start_date= self.cleaned_data["start_date"]
        end_date = self.cleaned_data["end_date"]
        classes_in_section_classrooms = self.cleaned_data[
            "classes_in_section_classrooms"]
        json_request_info = self.cleaned_data["json_request_info"]
        if (json_request_info):
            creator = SchoolDB.system_management.BulkClassSessionsCreator(start_date, 
                                end_date, 1, json_request_info)
            request_table, conflict_table, other_info = \
                         creator.process_request()
            #now report the initial result
            #specialShowAction(instance=None, requested_action="save", 
                    #classname="", formname=CreateClassSessionsFormStep2,
                    #title_suffix="Confirm Multiple Class Sessions Creation",
                    #template="create_class_sessions_step2",
                    #extra_params={"request_table":request_table, 
                                    #"conflict_table":conflict_table,
                                    #"other_info":other_info,
                                    #"start_date":str(start_date.toordinal()),
                                    #"end_date":str(end_date.toordinal()),
                                    #"use_classrooms":str(
                                        #classes_in_section_classrooms)})

    @staticmethod
    def process_request(data):
        """
        Initialize the date fields to the current school year. These
        are probably the correct values and the fields are required.
        """
        data["start_date"] = SchoolYear.school_year_start_for_date()
        data["end_date"] = SchoolYear.school_year_end_for_date()   
    

    def modify_params(self,params):
        params["title_prefix"] = ""
        params["title_bridge"] = ""
        params["title_suffix"] = "Create Many Classes for School Year " + \
              unicode(SchoolYear.school_year_for_date(date.today()))

    @staticmethod
    def generate_javascript_code(javascript_generator):
        class_years = get_class_years_only()        
        (subject_names, subject_name_to_key_dict, subject_key_to_name_dict) = \
         get_possible_subjects("taught_by_section =")
        subject_keys = [str(subject_name_to_key_dict[name])
                            for name in subject_names]
        javascript_generator.add_javascript_params ({
        "json_subject_names":simplejson.dumps(subject_names),
        "json_subject_keys":simplejson.dumps(subject_keys),
        "json_classyear_names":simplejson.dumps(class_years),
        "school_year_key":\
        str(SchoolYear.school_year_for_date(date.today()).key())})

#----------------------------------------------------------------------
class CreateClassSessionsFormStep2(BaseStudentDBForm):
    """
    This form displays two tables "Class Session Creation Conflicts" and
    "Class Sessions to be Created". These show the problems in in the
    initial request and the actions to be performed. It is not initiated in
    the normal manner by a web request but rather by a function call from
    the first step form CreateClassSessionsForm.
    """
    json_final_request = forms.CharField(required = False, 
                widget=forms.HiddenInput)
    
    def modify_params(self, params):
        params["title_prefix"] = ""
        params["title_bridge"] = ""
        params["title_suffix"] = "Proposed Class Sessions to Create"


#----------------------------------------------------------------------

class AssignStudentsForm(BaseStudentDBForm):
    """
    This form displays two tables, "Assigned Students" and "Eligible
    Students", with buttons to add or remove students from a class
    roster. This is meant for Student Majors classes that are not
    taught per section.
    """
    class_year = forms.CharField(required=False,
            widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    assignment_date = forms.DateField(required=False,
        widget=forms.DateInput(format="%m/%d/%Y",                    
            attrs={"class":"date-mask entry-field popup-calendar required"}))
    assigned_students = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")
    class_session = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")    
    parent_form = BaseStudentDBForm

    def modify_params(self,params):
        params["title_prefix"] = ""
        params["title_bridge"] = ""
        params["title_details"] = " to<br/>" + \
              self.class_session.detailed_name()
        #params["value_right_btn"] = "Assign"
                
    def generate_javascript_code(self, javascript_generator):
        self.class_session = getprocessed().requested_instance
        #current_instance set in page itself
        if not self.class_session:
            self.class_session = getprocessed().current_instance
        cy_handler = """
        select: function(event, data) {
            classYearChanged(data);} """
        clsyr = javascript_generator.add_autocomplete_field(
            class_name = "class_year", field_name = "id_class_year",
        custom_handler = cy_handler)
        clsyr.set_local_choices_list(SchoolDB.choices.ClassYearNames)
        if self.class_session :
            javascript_generator.add_javascript_params ({
                "class_session_key":str(self.class_session.key()),
                "student_major_key":
                str(SchoolDB.models.get_key_from_instance(
                    self.class_session.student_major)),
                "class_year":self.class_session.class_year
                })

    @staticmethod                                                 
    def initialize(data):
        """
        Set the default values for the class year and assignment start
        date.
        """
        class_session = getprocessed().requested_instance
        #current_instance set in page itself
        if not class_session:
            class_session = getprocessed().current_instance
        data["class_year"] = class_session.class_year
        data["assignment_date"] = class_session.school_year.start_date
    
    def save(self, instance):
        """
        Do not perform any of the standard form save actions.
        Perform a save by processing the assigned students field to a
        list of student keys and then adding the list of students to the
        class session. The student class function prevents duplicates so
        all students can be safely added. 
        """
        assigned_students_list = []
        assigned_students_text = self.cleaned_data["assigned_students"]
        #Get the instance again to assure that it is the correct class
        class_session_instance = SchoolDB.models.get_instance_from_key_string(
            self.cleaned_data["object_instance"], 
            SchoolDB.models.ClassSession)
        assigned_students_list = []
        if (assigned_students_text):
            assigned_students_text_list = assigned_students_text.split(",")
            for text_key in assigned_students_text_list:
                student = SchoolDB.models.get_instance_from_key_string(text_key,
                                                        SchoolDB.models.Student)
                if student:
                    assigned_students_list.append(student)
        if (class_session_instance and (len(assigned_students_list) > 0)):
            class_session_instance.add_students_to_class(
                assigned_students_list, self.cleaned_data["assignment_date"])
        
          
#----------------------------------------------------------------------

class AssignSectionStudentsForm(BaseStudentDBForm):
    """
    This form displays a single list of students in the section and a
    button to assign the all of them to the class. The Student model
    prevents multiple assignment to the same class so this assignment
    action may be done multiple times without problem.
    """
    section_students = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")
    class_session = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")
    parent_form = BaseStudentDBForm

    def modify_params(self,params):
        """
        Set the title to include both the class and the section.
        If either does not exist then present a warning instead
        """
        params["title_prefix"] = ""
        params["title_bridge"] = ""
        class_session = getprocessed().requested_instance
        details = ""
        if class_session:
            details = " from<br/>%s to<br/>Section %s" \
                  %(unicode(class_session.section),
                            unicode(class_session))
            section_name = unicode(class_session.section)
        else:
            details = "<br/><p class='title_warning'>" + \
                    "Error: Cannot assign students:<br/>"
            if (not class_session):
                details = details + "No Class Selected"
            else:
                details = details + class_session.detailed_name() + \
                    " has no Section."
            details = "</p>"
        params["title_details"] = details
             
    def generate_javascript_code(self, javascript_generator):
        class_session = getprocessed().requested_instance
        if class_session:
            class_session_key = getprocessed().selection_key
            section_key = str(class_session.section.key())
        else:
            class_session_key = ""
            section_key = ""           
        javascript_generator.add_javascript_params ({
                "class_session_key":class_session_key,
                "section_key":section_key
                })

    def save(self, instance):
        """
        Do not perform any of the standard form save actions.
        Perform a save by processing the students table to a
        list of student keys and then adding the list of students to the
        class session. The student class function prevents duplicates so
        all students can be safely added. 
        """
        section_students_list = []
        section_students_text = self.cleaned_data["section_students"]
        #Get the instance again to assure that it is the correct class
        class_session_instance = SchoolDB.models.get_instance_from_key_string(
            self.cleaned_data["class_session"], SchoolDB.models.ClassSession)
        section_students_list = []
        if (section_students_text):
            section_students_text_list = \
                        simplejson.loads(section_students_text)
            for text_key in section_students_text_list:
                student = SchoolDB.models.get_instance_from_key_string(text_key,
                                                        SchoolDB.models.Student)
                if student:
                    section_students_list.append(student)
        if (class_session_instance and (len(section_students_list) > 0)):
            class_session_instance.add_students_to_class(
                section_students_list, class_session_instance.start_date)

#----------------------------------------------------------------------

class GradeWorkForm(BaseStudentDBForm):
    """
    This is the base form class for the grading instances and the student
    grade forms.
    """
    class_session = forms.CharField(required=True,
                        widget=forms.HiddenInput, initial = "")
    class_session_name = forms.CharField(required=False,
                                widget=forms.HiddenInput, initial = "")
    element_names = ["class_session"]
    parent_form = BaseStudentDBForm

    def modify_params(self, param_dict, prefix_for_title):
        try:
            class_session = getprocessed().prior_selection
            if (class_session):
                class_session_key = convert_string_to_key(class_session)
                if (class_session_key):
                    class_session_name = unicode(class_session_key)
                    param_dict["title_suffix"] = \
                              prefix_for_title + class_session_name
        except AttributeError:
            pass

    @staticmethod
    def initialize(data):
        initialize_fields([("class_session", "class_session_name")], data)


    @staticmethod
    def initialize_form_params(select_form):
        pass


    @staticmethod
    def generate_select_javascript_code(javascript_generator, 
                                        select_field, title):
        """
        This classes function is an example of filtering using
        a value contained in the request. In this example it uses
        the key of another object already selected which is
        to be filtered in the search for the table.
        """
        if (getprocessed().selection_key_valid):
            class_session = getprocessed().selection_key
            prior_selection = class_session
            javascript_generator.add_javascript_params (
                {"title":title,
                 "titleNamePlural":"Grading Instances",
                 "priorSelection":class_session})
            select_field.add_extra_params({
                "extra_fields":"grading_type", 
                "filterkey-class_session":class_session})

#----------------------------------------------------------------------

class GradingInstanceForm(GradeWorkForm):
    """
    This form is for tests or other activities 
    """
    name = forms.CharField(required=True, label="Name:*",
            widget=forms.TextInput(attrs={'class':'required entry-field', 
                                                         'minlength':'5'}))
    grading_type = forms.ChoiceField(required=True, label="Type:*",
                choices=SchoolDB.choices.convert_to_form_choice_list(
                            SchoolDB.choices.GradingInstanceType))
    percent_grade = forms.FloatField(required=False, 
            label="% Class Grade:",
            min_value=1, max_value=100, widget=forms.TextInput(
                    attrs={'class':'entry-field numeric-field percentage-mask'}))
    multiple = forms.BooleanField(required=False, label="Multiple Grades:")
    extra_credit = forms.BooleanField(required=False, label="Extra Credit:")
    other_information=forms.CharField(required=False, max_length=1000,
                        label="Other Information:",
                        widget=forms.Textarea(attrs={
                            'cols':50, 'rows':2, 'class':'entry-field'}))
    planned_date=forms.DateField(required=True, label="Planned Date:",
                        widget=forms.DateInput(format="%m/%d/%Y",
                        attrs={'class':'date-mask required entry-field'}))
    element_names = ["name", "class_session", "grading_type",
                     "percent_grade", "multiple", "extra_credit",
                     "other_information"]
    parent_form = GradeWorkForm

    def create_new_instance(self):
        return SchoolDB.models.GradingInstance.create(
            name=self.cleaned_data["name"], 
            class_session=convert_string_to_key(
                self.cleaned_data["class_session"]),
            planned_date=self.cleaned_data["planned_date"])

    #@staticmethod
    #def process_request(data):
        #"""
        #The "class_session" is determined from the select action
        #for the class_session just before this form is created
        #to create a new grading instance. Thus it must be preloaded
        #into the form field when the form is first created.
        #"""
        #prior_selection = parsed["prior_selection"]
        #if (get_instance_from_key_string(prior_selection) and
            #(parsed["requested_action"] == "Create")):
            #data["class_session"] = prior_selection


    def modify_params(self, param_dict):
        GradeWorkForm.modify_params(self, param_dict, 
                                    "Grading Instance for ")
    @staticmethod
    def initialize(data):
        GradeWorkForm.initialize(data)

    @staticmethod
    def initialize_form_params(select_form):
        select_form.set_title("Work With Grading Instances")
        GradeWorkForm.initialize_form_params(select_form)

    def generate_javascript_code(self, javascript_generator):
        """
        The "class_session" is determined from the select action for
        the class_session just before this form is created to create a
        new grading instance. Because it is a required field preloading
        it triggers error checking. Thus it must be loaded at the
        browser when the form page is displayed.
        """
        prior_selection = getprocessed().prior_selection
        if (prior_selection and 
            getprocessed().requested_action == "Create"):
            # create the code for loading
            script = \
                   '$(function() { $("#id_class_session").val("%s"); });' \
                   %prior_selection
            javascript_generator.add_javascript_code(script)

    @staticmethod
    def generate_select_javascript_code(javascript_generator, 
                                        select_field):
        """
        This classes fuction is an example of filtering using
        a value contained in the request. In this example it uses
        the key of another object already selected which is
        to be filtered in the search for the table.
        """
        if (getprocessed().selection_key_valid):
            title = "Work With Grading Instances for " + \
                  unicode(getprocessed().requested_instance)
            GradeWorkForm.generate_select_javascript_code(
                javascript_generator, select_field, title)

#----------------------------------------------------------------------

class AchievementTestDescriptionForm(BaseStudentDBForm):
    """
    The primary information about the achievment test result is
    maintained by school. This class contains the information which
    describes the achievement test so that upper level orgs can create
    a definition of a test to be used by the schools.
    """
    
#----------------------------------------------------------------------


class AchievementTestForm(BaseStudentDBForm):
    """
    This form is for tests or other activities 
    """
    name = forms.CharField(required=True, label="Name*:",
            widget=forms.TextInput(attrs={'class':'required entry-field', 
                                           "size":35, 'minlength':'5'}))
    date = forms.DateField(required=True, label="Test Date:*",
        widget=forms.DateInput(format="%m/%d/%Y", attrs={"size":12,
            "class":"date-mask popup-calendar entry-field"}))
    grading_type = forms.CharField(label="Test Type:*",
            widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    percent_grade = forms.FloatField(required=False, label="% Class Grade:",
            min_value=1, max_value=100, widget=forms.TextInput(
                    attrs={'class':'entry-field small-numeric-field percentage-mask'}))
    other_information=forms.CharField(required=False, max_length=1000,
                label="Other Information:", widget=forms.Textarea(attrs={
                        'cols':50, 'rows':2, 'class':'entry-field'}))
    json_subject_names = forms.CharField(widget=forms.HiddenInput)
    json_classyear_names = forms.CharField(widget=forms.HiddenInput)
    json_testing_info = forms.CharField(required=False, max_length=1000, 
                                        widget=forms.HiddenInput)
    element_names = ["name", "date", "grading_type", "percent_grade",
                     "other_information"]
    parent_form = BaseStudentDBForm


    def create_new_instance(self):
        """
        Create with almost all information because the information is used
        within associated instances of different classes
        """
        return SchoolDB.models.AchievementTest.create(
            self.cleaned_data["name"],
            SchoolDB.models.getActiveDatabaseUser().get_active_organization())
        
    def modify_params(self, param_dict):
        param_dict["title_bridge"] = " an "

    def set_values_from_form(self, instance):
        """
        Add/modify information about the test's subjects to the current
        instance.
        """
        BaseStudentDBForm.set_values_from_form(self,instance)
        at_info = []
        try:
            subject_names = simplejson.loads(self.cleaned_data[
                 "json_subject_names"])
            class_year_names = simplejson.loads(self.cleaned_data[
                "json_classyear_names"])
            testing_info = simplejson.loads(self.cleaned_data[
                "json_testing_info"])
            class_year_dict = {}
            for subject_instance in testing_info:
                class_year = class_year_names[subject_instance[0]]
                subject_name = subject_names[subject_instance[1]]
                number_questions = int(subject_instance[2])
                at_info.append((class_year, subject_name, number_questions))
                class_year_dict[class_year] = True
            instance.class_years = class_year_dict.keys()
            instance.update(at_info)
            instance.put()
        except ValueError:
            pass
        
    @staticmethod
    def generate_javascript_code(javascript_generator):
        grading_type= javascript_generator.add_autocomplete_field(
        class_name = "grading_type", field_name = "id_grading_type")
        grading_type.set_local_choices_list(
            SchoolDB.choices.AchievementTestType)
        instance_string = javascript_generator.get_instance_string()
        json_subject_names, json_classyear_names, json_testing_info = \
                    AchievementTestForm.generate_testing_info(instance_string)
        javascript_generator.add_javascript_params ({
        "json_subject_names":json_subject_names,
        "json_classyear_names":json_classyear_names,
        "json_testing_info":json_testing_info})
        return grading_type

        
    @staticmethod    
    def generate_select_javascript_code(javascript_generator, 
                                        select_field):      
        javascript_generator.add_javascript_params (
            {"auxFields":[{"name":"grading_type","label":"Achievement Test Type",
                           "fieldType":"view"}]})
        grading_type = AchievementTestForm.generate_javascript_code(
            javascript_generator)
        select_field.add_dependency(grading_type,False)
        select_field.add_extra_params({"extra_fields":"grading_type|date"})

    @staticmethod    
    def generate_testing_info(instance_string):
        """
        Create the data structures that contain the information necessary
        for display. The subject name and classyear name lists are always
        set. If editing a current achievement test then the current 
        information is encoded also.
        """
        subject_names, class_years, view_info = \
                SchoolDB.models.AchievementTest.get_info_for_view(instance_string)
        testing_info = []
        for subject_instance in view_info:
            try:
                class_year_index = class_years.index(subject_instance[0])
                subject_index = subject_names.index(subject_instance[1])
                number_questions = subject_instance[2]
                testing_info.append((class_year_index, subject_index,
                                     number_questions))
            except ValueError:
                pass
        if (len(testing_info)):
            json_testing_info = simplejson.dumps(testing_info)
        else:
            json_testing_info = None
        return simplejson.dumps(subject_names), simplejson.dumps(class_years), \
               json_testing_info
                                   
#---------------------------------------------------------------------- 
class GradesForm(GradeWorkForm):
    """
    This form is used to assign grades for a single grading instance to
    all students in the class
    """
    parent_form = GradeWorkForm

    @staticmethod
    def initialize(data):
        GradeWorkForm.initialize(data)

    @staticmethod
    def initialize_form_params(select_form):
        select_form.set_title("Grading Instance to Enter Grades for ")
        GradeWorkForm.initialize_form_params(select_form)

    def modify_params(self, params):
        GradeWorkForm.modify_params(self, params, " For ")
        params["title_prefix"] = "Set Grades"
        params["title_bridge"] = " "

    def generate_javascript_code(self, javascript_generator):
        """
        The grading instance key is the only value that is needed.
        Load that as a simple variable value for javascript use. The
        variable name "gradingInstance" is already a global variable
        declared in "grades.js". Load the gi information, and class
        session name for general use by the page.
        """
        grade_instance = getprocessed().requested_instance
        grade_instance_keystring = (str(grade_instance.key()))
        prior_selection_keystring = getprocessed().prior_selection
        if (grade_instance_keystring and prior_selection_keystring and
            getprocessed().selection_key_valid):
            keystr_array = simplejson.dumps([grade_instance_keystring])
            script = \
                "gradingInstances = '" + keystr_array + \
                "';\nvar classSession = '" + prior_selection_keystring + "';"
            javascript_generator.add_no_wrap_javascript_code(script)

    @staticmethod
    def generate_select_javascript_code(javascript_generator, 
                                        select_field):
        """
        This classes fuction is an example of filtering using
        a value contained in the request. In this example it uses
        the key of another object already selected which is
        to be filtered in the search for the table.
        """
        if (getprocessed().selection_key_valid):
            title = "Enter Grades For " + \
                  unicode(getprocessed().requested_instance)
            GradeWorkForm.generate_select_javascript_code(
                javascript_generator, select_field, title)

#---------------------------------------------------------------------- 
class AchievementTestGradesForm(BaseStudentDBForm):
    """
    This form is used to set or view grades for all subjects on an 
    achievement test by section.
    """
    class_year = forms.CharField(required=True, label="Class Year",
                                 widget=forms.TextInput(attrs={
                                     'class':'autofill required entry-field'}))
    section_name = forms.CharField(required=False, label="Section",
                widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    section = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")
    achievement_test_name = forms.CharField(required=False, 
                label="Achievement Test",
                widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    achievement_test = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")   
    parent_form = BaseStudentDBForm

    def modify_params(self, param_dict):
        param_dict["id_right_btn"] = "save_grades_btn"
 
    def generate_javascript_code(self, javascript_generator):
        clsyr = javascript_generator.add_autocomplete_field(
            class_name = "class_year", field_name = "id_class_year")
        clsyr.set_local_choices_list(SchoolDB.choices.ClassYearNames)
        sect = javascript_generator.add_autocomplete_field(
            class_name = "section", field_name = "id_section_name",
            key_field_name = "id_section")
        sect.add_dependency(clsyr, False)
        achtest = javascript_generator.add_autocomplete_field(
            class_name = "achievement_test", 
            field_name = "id_achievement_test_name",
            key_field_name = "id_achievement_test",
            ajax_root_path = "/ajax/get_achievement_tests_for_section")
        achtest.add_dependency(sect, True)
        
        
    #@staticmethod
    #def initialize(data):
        #"""
        #Initialize the class year and section to the users section.
        #Note: This should be done only when coming from the teacher's       
        #My Work page.
        #"""
        #if (getprocessed()):
            #if (getprocessed().return_page == "my_work"):
                #section_keystr = getprocessed().cookies["aS"]
                #if section_keystr:
                    #section = SchoolDB.models.get_instance_from_key_string(section_keystr, 
                                                    #SchoolDB.models.Section)
                    #if section:
                        #data["section"] = section_keystr
                        #data["section_name"] = unicode(section)
                        #data["class_year"] = section.class_year

    @staticmethod
    def process_request(data):
        try:
            if (getprocessed().path_page_stack[-1] == "/my_work"):
                active_section_key = \
                    DatabaseUser.get_single_value(None, "active_section")
                active_section = Section.get(active_section_key)
                data["section"] = str(active_section_key)
                data["section_name"] = unicode(active_section)
                data["class_year"] = active_section.class_year
        except:
            pass
                            
#---------------------------------------------------------------------- 
class GradingPeriodResultsForm(BaseStudentDBForm):
    """
    This form is used to set the class session grades for the end of
    the grading period.
    """
    object_instance = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "") 
    parent_form = BaseStudentDBForm
    
    def build_periods_checkboxes(self, user_is_teacher):
        """
        Generate the html code to display the block of grading periods
        that can be used. Each grading period has the name, a checkbox
        for view, and a checkbox for edit. THe vlues for the checkboxes
        are the keystrings for the grading periods.
        """
        html_string = ""
        valid_grading_periods = \
                SchoolDB.models.GradingPeriod.get_completed_grading_periods()
        if (len(valid_grading_periods) == 0):
            html_string = """
            <p class="warning-field">
            There are no grading periods for this year that are completed so no
            grades can be entered or viewed. <br>
            Click "Cancel" to return to the previous page.
            """
        else:
            html_string = """
    <table class="unbordered">
    <tr><td>Grading Period</td><td class="centered-object">Dates</td>
    <td >View</td>
            """
            if user_is_teacher:
                html_string += "<td>Edit</td>"
            html_string += "</tr>"
            period_keystrs = [str(p.key()) for p in valid_grading_periods]
            period_names = [unicode(p) for p in valid_grading_periods]
            period_dates = [p.get_date_string() for p in valid_grading_periods]
            for i in xrange(len(valid_grading_periods)):
                id_string = "period%d" %i
                html_string += """
        <tr><td>%s</td><td>%s</td>
        <td><input name="period-checkbox" id="%s-view" 
        class="period-view centered-object" type="checkbox" value=%s></td>
        """ %(period_names[i], period_dates[i], id_string, 
                  period_keystrs[i])
        if user_is_teacher :
            html_string += """
        <td><input name="period-checkbox" id="%s-edit" 
        class="period-edit centered_object" type="checkbox" value=%s></td>
            """  %(id_string, period_keystrs[i])
        html_string += "</tr></table>"
        return html_string
                        
    def modify_params(self, param_dict):
        param_dict["id_right_btn"] = "save_grades_btn"
        param_dict["user_is_teacher"] = self.user_is_teacher
        param_dict["class_session_name"] = self.name
        prefix = ""
        if self.user_is_teacher:
            prefix = "Edit or "
        param_dict["form_title"] = \
                  "%sView Grading Periods for %s" %(prefix, self.name)
        param_dict["period_checkboxes"] = self.build_periods_checkboxes(
            self.user_is_teacher)
     
    def generate_javascript_code(self, javascript_generator):
        keystring = self.data["object_instance"]
        class_session = \
            SchoolDB.utility_functions.get_instance_from_key_string(
                keystring, ClassSession)
        if (class_session.teacher):
            self.user_is_teacher = (class_session.teacher.key() == 
                               getActiveDatabaseUser().get_active_person().key())
        else:
            self.user_is_teacher = False
        self.name = unicode(class_session)
        javascript_generator.add_javascript_params (
            {"class_session_name":self.name, 
             "user_is_teacher":self.user_is_teacher})

    #@staticmethod
    #def initialize(data):
        #"""
        #Initialize the class year and section to the users section.
        #Note: This should be done only when coming from the teacher's       
        #My Work page.
        #"""
        #if (getprocessed()):
            #if (getprocessed().return_page == "Fmy_work"):
                #class_session_keystr = \
                    #getprocessed().cookies["aC"]
                #if class_session_keystr:
                    #class_session = SchoolDB.models.get_instance_from_key_string(
                        #class_session_keystr, SchoolDB.models.ClassSession)
                    #if class_session:
                        #data["class_session"] = class_session_keystr
        #data["requested_action"] = "Ignore"
            
#---------------------------------------------------------------------- 
class AttendanceForm(BaseStudentDBForm):
    """
    This form displays the page to log attendance. All of the information
    and the forms table is generated via external python code so this is
    merely a display wrapper. No new objects are created when using this
    form.
    """
    section_name=forms.CharField(required=False, widget=forms.HiddenInput)
    section=forms.CharField(required=False,widget=forms.HiddenInput)
    state=forms.CharField(required=False, widget=forms.HiddenInput)
    requested_action=forms.CharField(required=False,
                                     widget=forms.HiddenInput)
    redirect_page=forms.CharField(required=False,widget=forms.HiddenInput) 


    #@staticmethod
    #def get_period_information(request):
        #start_date = request.GET.get("start_date",None)
        #end_date = request.GET.get("end_date")
        #weeks = request.GET.get("weeks",2)
        #return (start_date, end_date, weeks)

    @staticmethod
    def process_response():
        """
        The save action has already been fully processed via an ajax
        request. The only action necessary now is a redirect to the
        appropriate page. This will use the form value "request_source"
        to determine if the request came from "My Work" to return to it
        or, if not, to return to the home page.
        """

        redirect_page = "index"
        form = AttendanceForm(getprocessed().values)
        try:
            errors = form.errors
            if not errors:
                redirect_page = form.cleaned_data["redirect_page"]
        except ValueError, err:
            errors['__all__'] = unicode(err)
        return http.HttpResponseRedirect(redirect_page)

    #The following error methods need to be changed to something friendlier
    @staticmethod
    def error_no_section():
        return http.HttpResponseBadRequest("No section requested.")

    @staticmethod
    def error_no_students(section_name):
        return http.HttpResponseBadRequest(
            "No students in section %s " %section_name)

    @staticmethod
    def initialize(data):
        initialize_fields([("section", "section_name")], data)


#---------------------------------------------------------------------   

class UserTypeForm(BaseStudentDBForm):
    name = forms.CharField(required=True, max_length=60, label="Name*",
                           widget=forms.TextInput(attrs={'class':'required', 
                                                         'minlength':'5'}))
    home_page = forms.CharField(required=False, max_length=60, 
                                label="Home Page")
    school_only = forms.BooleanField(required=False)
    view_reports = forms.BooleanField(required=False)
    enter_attendance = forms.BooleanField(required=False)
    enter_grades = forms.BooleanField(required=False)
    edit_students = forms.BooleanField(required=False)
    edit_grades = forms.BooleanField(required=False)
    edit_school_entries = forms.BooleanField(required=False)
    create_users = forms.BooleanField(required=False)
    set_users_organization = forms.BooleanField(required=False)
    edit_general_entries = forms.BooleanField(required=False)
    create_user_type = forms.BooleanField(required=False)
    master_user = forms.BooleanField(required=False)
    element_names = ["name", "home_page", "school_only", "view_reports", 
                     "enter_attendance", "enter_grades",
                     "edit_students", "edit_grades", "edit_general_entities",
                     "edit_school_entries", "create_users",
                     "edit_general_entries", "set_users_organization",
                     "create_user_type", "master_user"]
    parent_form = BaseStudentDBForm

    def create_new_instance(self):
        return SchoolDB.models.UserType(name = self.cleaned_data["name"])

    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        javascript_generator.add_javascript_params ({"titleName":"User Type",
                    "titleNamePlural":"User Types", "fieldName":"User Type"})
        select_field.add_extra_params({"filter_school":"false",
                                       "leading_value_field":"name"})

#----------------------------------------------------------------------     

class MasterDatabaseUserForm(BaseStudentDBForm):
    """
    This is a wide open form for creating database users. It allows database
    users to be built for any organization and even without a person record.
    Not easy to use but flexible. This can only be used by the master admin
    user.
    """
    first_name = forms.CharField(required=True, max_length=60,
                                 label="First Name*",
            widget=forms.TextInput(attrs={'class':'required entry-field', 
                                            'minlength':'2'}))
    middle_name = forms.CharField(required=False, max_length=60,
                                 label="Middle Name",
            widget=forms.TextInput(attrs={'class':'entry-field', 
                                            'minlength':'1'}))
    last_name = forms.CharField(required=True, max_length=60, 
                                label="Family Name*",
            widget=forms.TextInput(attrs={'class':'required entry-field', 
                                            'minlength':'2'}))
    email = forms.EmailField(required=True, max_length=60, 
                    label="Email Address*", widget=forms.TextInput(attrs=
                         {'class':'required email entry-field',
                          "minlength":"7"}))
    contact_email = forms.EmailField(required=False, max_length=60, 
            label="Preferred Email Address", widget=forms.TextInput(attrs=
                         {'class':'email entry-field'}))

    user_type_name = forms.CharField(required=True, 
                        label="Database User Type*", 
                        widget=forms.TextInput(attrs=
                                {'class':'autofill entry-field required'}))
    user_type = forms.CharField(required=False, widget=forms.HiddenInput)
    guidance_counselor = forms.BooleanField(required=False, initial=False)
    organization_name = forms.CharField(required=True, 
                        label="Organization:*", widget=forms.TextInput(attrs=
                                {'class':'autofill entry-field required'}))
    organization = forms.CharField(required=False, widget=forms.HiddenInput)
    person_type = forms.ChoiceField(required=False, 
                                choices=(("teacher","Teacher"), 
                                ("administrator", "Administrator")),
                                label="Database Identity Type")
    person_name = forms.CharField(required=False, 
            label="Database Identity:", widget=forms.TextInput(attrs=
                                {'class':'autofill entry-field'}))
    person = forms.CharField(required=False, widget=forms.HiddenInput)
    other_information = forms.CharField(required=False,
        max_length=1000, widget=forms.Textarea( 
                    attrs={'cols':50, 'rows':2, 'class':'entry-field'}))
    element_names = ["first_name", "middle_name", "last_name", 
                     "email", "contact_email", "organization", 
                     "user_type", "guidance_counselor",
                     "person", "other_information"]
    parent_form = BaseStudentDBForm

    def create_new_instance(self):
        org_key = SchoolDB.models.get_key_from_string(self.cleaned_data["organization"])
        user_type_key = SchoolDB.models.get_key_from_string(self.cleaned_data["user_type"])
        return SchoolDB.models.DatabaseUser(
            first_name = self.cleaned_data["first_name"],
            last_name = self.cleaned_data["last_name"],
            organization = org_key,
            user_type = user_type_key,
            email = self.cleaned_data["email"])

    @staticmethod
    def generate_class_javascript_code(javascript_generator):
        usr_type = javascript_generator.add_autocomplete_field(
            class_name = "user_type")
        org = javascript_generator.add_autocomplete_field(
            class_name = "organization")
        per = javascript_generator.add_autocomplete_field(
            class_name = "teacher", field_name = "id_person_name",
            key_field_name = "id_person")
        per.add_extra_params({"ignore_organization":"!true!"})
        per.add_dependency(org, True)
        return org,per,usr_type
    
    def generate_javascript_code(self, javascript_generator):
        MasterDatabaseUserForm.generate_class_javascript_code(javascript_generator)
        
    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        javascript_generator.add_javascript_params ({
            "titleName":"Database User",
            "titleNamePlural":"Database Users", 
            "fieldName":"Database User Family Name",
            "auxFields":[{"name":"Organization_name",
                         "label":"DepEd Organization:",
                         "field_type":"view"}]})
        #>>>>>>needs rethinking!!<<<<<<<<
        org, per, user_type = \
           MasterDatabaseUserForm.generate_class_javascript_code(
            javascript_generator)
        select_field.add_dependency(org, True)
        select_field.add_extra_params({
            "extra_fields":"first_name|middle_name|user_type|organization|person|email",
            "format": "last_name_only",
            "leading_value_field":"last_name"})

    @staticmethod
    def initialize(data):
        initialize_fields([("user_type","user_type_name"), 
                            ("organization", "organization_name"),
                           ("person", "person_name")], data)

#----------------------------------------------------------------------  

class StandardDatabaseUserForm(BaseStudentDBForm):
    """
    The simple database user form for db admins in an organization. This has
    controls built in to always use the current users organization and to use
    values from a person that has already been created.
    """
    email = forms.EmailField(required=True, max_length=60, 
                    label="Gmail Address*", widget=forms.TextInput(attrs=
                         {'class':'required email entry-field',
                          "minlength":"7"}))
    person_name = forms.CharField(required=False, 
            label="Person*:", widget=forms.TextInput(attrs=
                                {'class':'required autofill entry-field'}))
    person = forms.CharField(required=False, widget=forms.HiddenInput)
    guidance_counselor = forms.BooleanField(required=False, initial=False)
    other_information = forms.CharField(required=False,
        max_length=1000, widget=forms.Textarea( 
                    attrs={'cols':50, 'rows':2, 'class':'entry-field'}))
    element_names = ["email", "guidance_counselor",
                     "person", "other_information"]
    parent_form = BaseStudentDBForm

    def generate_javascript_code(self, javascript_generator):
        pers = javascript_generator.add_autocomplete_field(
            class_name = "paygrade", field_name = "id_paygrade")
        pers.set_local_choices_list(
            SchoolDB.models.DatabaseUser.get_candidate_persons())
        pers.add_extra_params({"use_key":"!true!"})
    
    @staticmethod
    def initialize(data):
        initialize_fields([("person", "person_name")], data)
        
#----------------------------------------------------------------------  
class SelectForm(BaseStudentDBForm):

    def __init__(self, select_class, select_class_name, 
                 title_prefix, submit_action, view_only,
                 title):
        BaseStudentDBForm.__init__(self)
        self.selection_key = forms.CharField(required=False, 
                                             widget=forms.HiddenInput)
        self.parent_form = BaseStudentDBForm
        self.select_class = select_class
        self.select_class_name = select_class_name
        self.title = title
        self.titlename =  select_class_name.title().replace("_"," ")
        if (title_prefix):
            self.title = title_prefix + self.titlename
        self.titlename_plural = None
        if (view_only):
            self.requested_action = "View"
        self.return_url = "/" + select_class_name
        self.submit_action = submit_action
        self.page_path_action = "Push"
        self.breadcrumbs = generate_breadcrumb_line()
        self.select_class.initialize_form_params(self)

    def set_submit_action(self, submit_action):
        """
        Set the submit_action (the url for the submit. Add the
        "/" in front so that the specified form action need
        not worry about the initial "select/" in the url
        path.
        """
        self.submit_action = submit_action

    def set_title(self, title):
        self.title = title

    def set_titlename_plural(self, titlename_plural):
        self.titlename_plural = titlename_plural

    def set_select_class(self, select_class, select_class_name):
        self.select_class = select_class
        self.select_class_name = select_class_name
        self.titlename = select_class_name.title()

    def generate_javascript_code(self, javascript_generator):
        javascript_generator.add_javascript_code(
"""
   buildInputFields(localParams.auxFields,
     localParams.fieldName, "generated_input_fields_div");
""")        
        #if (not self.titlename_plural):
            #self.titlename_plural = self.titlename + "s"
        #if (not self.title):
            #self.title = "Work With " + self.titlename_plural
        javascript_generator.add_javascript_params(
            {"targetClass":self.select_class_name,
             "returnUrl":self.return_url,
             "titleName":self.titlename,
             "titleNamePlural":self.titlename + "s",
             "auxFields":[], "fieldName": self.titlename +"'s Name",
             "leadingValueField":"name",
             "priorSelection":""})
        select_field = javascript_generator.add_autocomplete_field(
            class_name = self.select_class_name, 
            field_name = "id_selection",
            response_command = "createWidgetTable(ajaxResponse);")
        select_field.ajax_root_path = "/ajax/select_table"
        select_field.add_extra_params({"filter_school":"true",
                                       "leading_value_field":"name",
                                       "maximum_count":150})
        self.select_class.generate_select_javascript_code(
            javascript_generator, select_field)
        #now generate the title if necessary because we have the correct
        #titleNamePlural
        if (not self.title):
            self.title = "Work With " + \
                javascript_generator.get_javascript_param("titleNamePlural")
        if (not javascript_generator.get_javascript_param("title")):
            javascript_generator.add_javascript_params({"title":self.title})
        #return the select_field fo further work by child classes
        return select_field   
#----------------------------------------------------------------------  
class DatabrowserForm(SelectForm):
     
    def __init__(self, select_class, select_class_name, 
                 title_prefix, submit_action):
        SelectForm.__init__(self, select_class=select_class, 
                          select_class_name=select_class_name,
                          title_prefix = title_prefix,
                          submit_action=submit_action, 
                          view_only=True,
                          title="")
        self.parent_form = SelectForm
        
    def generate_javascript_code(self, javascript_generator):
        select_field = SelectForm.generate_javascript_code(self,
                                                javascript_generator)
        #change the "extra_fields" parameter to use the selected fields
        #in the displayed results
        select_field.add_extra_params({
            "extra_fields":"!updateDisplayFields()!",
            "maximum_count":900})
        field_choices_table, selected_fields_table = \
                    createBrowserFieldsTables(self.select_class_name)
        javascript_generator.add_javascript_params({
            "field_choices_table":field_choices_table,
            "selected_fields_table":selected_fields_table})
        

#----------------------------------------------------------------------  
class MyWorkForm(BaseStudentDBForm):
    """
    This is a specialized near top level menu customized for a teacher user
    type. It predefines a set of choices for section and clsass_session
    that associated with the teacher. There will probably be either zero or
    one section so the choice list for the section will be filled in prior
    to presentation. The list of classes is more expensive to recover so it
    is generated by an ajax request only when needed.
    """
    users_section_name = forms.CharField(required = False, label="Section",
                    widget=forms.TextInput(attrs= {'class':'autofill entry-field'}))
    users_section = forms.CharField(required=False, widget=forms.HiddenInput)
    users_class_session_name = forms.CharField(required = False, label = "Class",
                    widget=forms.TextInput(attrs= {'class':'autofill entry-field'}))
    users_class_session = forms.CharField(required=False, 
                                    widget=forms.HiddenInput)
    def __init__(self, data):
        """
        Extract the information about the user for use with the pages
        javascript. The teacher will have some classes that she teaches
        and may be a section advisor. Attach a list of keys of both
        sections and class sessions to be used by javascript.
        """
        BaseStudentDBForm.__init__(self)
        activeDbUser = SchoolDB.models.getActiveDatabaseUser()
        self.dbuser = activeDbUser.get_active_user()
        self.person = activeDbUser.get_active_person()
        self.organization_key = activeDbUser.get_active_organization_key()
        self.organization_name = \
            activeDbUser.get_active_organization_name()
        self.keys_list = ["active_section", "active_class_session"]
        self.values_dict = self.dbuser.get_private_info_multiple_values(
            self.keys_list)
        self.users_section = self.values_dict["active_section"]
        self.users_class_session = self.values_dict["active_class_session"]
        self.users_section_name = ""
        self.users_class_session_name = ""
        self.user_is_section_advisor = False
        self.user_is_class_session_teacher = False
        session = None
        if (self.users_section):
            section = SchoolDB.models.get_instance_from_key_string(
                self.users_section, SchoolDB.models.StudentGrouping)
            if section :
                self.users_section_name = unicode(section)
                if section.teacher:
                    self.user_is_section_advisor = \
                        (section.teacher.key()== self.person.key())
            if (self.users_class_session):
                session = SchoolDB.models.get_instance_from_key_string(
                    self.users_class_session, 
                    SchoolDB.models.StudentGrouping)
            if session:
                self.users_class_session_name = session.detailed_name()
                if session.teacher:
                    self.user_is_class_session_teacher = \
                        (session.teacher.key() == self.person.key())
           
    def build_choice_list(self, choices_class):
        """
        Create a choice list for the form that will be shown in a
        autofill field. The key has a special use here. THe keystring
        is prefixed by a '=' or '-' to indicate if the user is the
        teacher for the section or class. This must be stripped in the
        javascript on the webpage before sending as a key to the
        database.
        """
        choices = []
        instances_list = \
                self.dbuser.get_interesting_instances_class_list(choices_class)
        for instance in instances_list:            
            if (choices_class == SchoolDB.models.ClassSession):
                name = instance.detailed_name()
            else:
                name = unicode(instance)
            keystr = str(instance.key())
            if (instance.teacher and (instance.teacher.key() == self.person.key())):
                keystr = '+' + keystr
            else:
                keystr = '-' + keystr
            choice = ({'label':name, \
                       'value':name, \
                       'key':keystr})
            choices.append(choice)
        return choices
            
    #def modify_params(self, params):
        #params['title_bridge'] = ""
        #params['title_prefix'] = ""
        #params['title_suffix'] = "My Work Page"
        
    def generate_javascript_code(self, javascript_generator):
        sect_handler = """
        select: function(event, data) {
            setActiveSection(data);} """
        sect = javascript_generator.add_autocomplete_field(
            class_name = "section", field_name = "id_users_section_name",
            key_field_name = "id_users_section",
            custom_handler = sect_handler)
        sect.set_local_choices_list(self.build_choice_list(SchoolDB.models.Section))
        cls_handler = """
        select: function(event, data) {
            setActiveClassSession(data);} """
        cls = javascript_generator.add_autocomplete_field(
            class_name = "class_session",
            field_name = "id_users_class_session_name",
            key_field_name = "id_users_class_session",
            custom_handler = cls_handler)
        cls.set_local_choices_list(
            self.build_choice_list(SchoolDB.models.ClassSession))
        #Allow intial functionwithou a person associated with the database
        #user
        if (self.person):
            person_key = str(self.person.key())
            person_name = unicode(self.person)
        else:
            person_key = "Unknown"
            person_name = "Unknown"           
        javascript_generator.add_javascript_params({
            "dbUserKey":str(self.dbuser.key()), 
            "personKey":person_key,
            "personName":person_name,
            "organizationKey":str(self.organization_key),
            "organizationName":self.organization_name,
            "users_section":self.users_section,
            "users_class_session":self.users_class_session,
            "users_section_name":self.users_section_name,
            "users_class_session_name":self.users_class_session_name,
            "user_is_section_advisor":self.user_is_section_advisor,
            "user_is_class_session_teacher":self.user_is_class_session_teacher,
            "school":str(SchoolDB.models.getActiveDatabaseUser().get_active_organization().key())
            })
        return javascript_generator
    
    #def save(self):
        #"""
        #Set the selected section and class session in the user data
        #"""
        #saved_values = {"active_section": 
                            #self.cleaned_data["users_section"],
            #"active_section_name":self.cleaned_data["users_section_name"],
            #"active_class_session":self.cleaned_data["users_class_session"],
            #"active_class_session_name":
            #self.cleaned_data["users_class_session_name"]}
        #self.dbuser.set_private_info_multiple_values(
            #saved_values)

    @staticmethod
    def process_request(data):
        activeDbUser = SchoolDB.models.getActiveDatabaseUser()
        dbuser = activeDbUser.get_active_user()
        keys_list = ["active_section","active_class_session"]
        values_dict = dbuser.get_private_info_multiple_values(keys_list)
        data["users_section"] = values_dict["active_section"]
        data["users_class_session"] = values_dict["active_class_session"]

#----------------------------------------------------------------------  
class ChooseForm(BaseStudentDBForm):
    """
    This form presents a selection table of students in the section.
    The fields include the students name and a boolean for all required
    record fields completed.
    """
    def __init__(self, choose_type, choose_object_class, choose_action):
        BaseStudentDBForm.__init__(self)
        self.choose_type = choose_type
        self.choose_object_class = choose_object_class
        self.choose_action = choose_action
        
    def modify_params(self, params):
        params['title_bridge'] = ""
        params['view_only'] = (self.choose_action == "View")
        params['select_fieldset_header'] = "Select " + params["title_suffix"]
        
    def generate_javascript_code(self, javascript_generator):
        #fix this!
        ajax_function_name = "create_" + self.choose_type + "_table"
        key = getprocessed().selection_key
        javascript_generator.add_javascript_params({
            "ajax_function_name":ajax_function_name,
            "key":key, "object_class":self.choose_object_class,
            "template_requested_action":self.choose_action,
            "prior_selection":"NOTSET"
        })
    
#----------------------------------------------------------------------  
class AttendanceReportForm(BaseStudentDBForm):
    """
    This form presents a generalized form page with choices to generate
    student attendance forms.
    """
    section_name = forms.CharField(required = False, label="Section",
                    widget=forms.TextInput(attrs= 
                        {'class':'autofill required'}))
    section = forms.CharField(required=False, widget=forms.HiddenInput)
    start_date = forms.DateField(required=False, 
            widget=forms.DateInput(format="%m/%d/%Y", attrs={"size":10,
            "class":"date-mask popup-calendar required entry-field"}))
    end_date = forms.DateField(required=False, 
            widget=forms.DateInput(format="%m/%d/%Y", attrs={"size":10,
            "class":"date-mask popup-calendar required entry-field"}))
    report_type = forms.ChoiceField(required=False,
            choices=(("Daily","Daily"), 
                     ("Student Summary","Student Summary")), initial="Daily")
    
    def modify_params(self, params):
        params["title_prefix"] = "Create"
        params["title_bridge"] = " an "

    def generate_javascript_code(self, javascript_generator):
        sect = javascript_generator.add_autocomplete_field(
            class_name = "section")
        return javascript_generator

#----------------------------------------------------------------------  
class StudentAgeReportForm(BaseStudentDBForm):
    """
    This form presents a page to generate a school register form.
    """
    class_year = forms.CharField(required=False,
                    widget=forms.TextInput(attrs={
                        'class':'autofill entry-field', "size":11}))
    section_name = forms.CharField(required = False, label="Section",
                    widget=forms.TextInput(attrs= 
                        {'class':'autofill entry-field', "size":11}))
    section = forms.CharField(required=False, widget=forms.HiddenInput)
    reference_date = forms.DateField(required=False, 
        widget=forms.DateInput(format="%m/%d/%Y", attrs={"size":8,
        "class":"date-mask popup-calendar entry-field"}))
    min_age = forms.IntegerField(required=False, initial=10,
                                 widget=forms.TextInput(attrs={
                                     'class':'entry-field', "size":5}))
    max_age = forms.IntegerField(required=False, initial=22,
                                 widget=forms.TextInput(attrs={
                                     'class':'entry-field', "size":5}))
    trim_years = forms.ChoiceField(required=False,
                    choices=[("on","Yes"),("off","No")])
    restrict_years = forms.ChoiceField(required=False,
                    choices=[("on","Yes"),("off","No")])
    age_calc_type = forms.ChoiceField(required=False,
                    choices=SchoolDB.choices.AgeCalcType)
    
    def modify_params(self, params):
        params["title_prefix"] = "Create"
        
    def generate_javascript_code(self, javascript_generator):
        clsyr = javascript_generator.add_autocomplete_field(
                class_name = "class_year", field_name = "id_class_year")
        clsyr.set_local_choices_list(SchoolDB.choices.ClassYearNames)
        sect = javascript_generator.add_autocomplete_field(
                class_name = "section")
        sect.add_dependency(clsyr, False)
        return javascript_generator

#----------------------------------------------------------------------  
class SectionListReportForm(BaseStudentDBForm):
    """
    This form presents a page to generate a school register form.
    """
    section_name = forms.CharField(required = False, label="Section",
                    widget=forms.TextInput(attrs= 
                        {'class':'autofill required', "size":11}))
    section = forms.CharField(required=False, widget=forms.HiddenInput)

    def modify_params(self, params):
        params["title_prefix"] = "Create"
        
    def generate_javascript_code(self, javascript_generator):
        sect = javascript_generator.add_autocomplete_field(
            class_name = "section")
        return javascript_generator

#----------------------------------------------------------------------

class SectionGradingPeriodGradesForm(BaseStudentDBForm):
    """
    This form presents a table of grades for all students in a section for
    a single grading period.
    """
    section_name = forms.CharField(required = False, label="Section:",
                    widget=forms.TextInput(attrs= 
                        {'class':'autofill required', "size":11}))
    section = forms.CharField(required=False, widget=forms.HiddenInput)
    grading_period_name = forms.CharField(required = False, label="Grading Period:",
                    widget=forms.TextInput(attrs= 
                        {'class':'autofill required', "size":11}))
    grading_period = forms.CharField(required=False, widget=forms.HiddenInput)

    def modify_params(self, params):
        params["title_prefix"] = "Create"
        
    def generate_javascript_code(self, javascript_generator):
        sect = javascript_generator.add_autocomplete_field(
            class_name = "section")
        gdprd = javascript_generator.add_autocomplete_field(
            class_name = "grading_period")
        gdprd.add_extra_params({"use_class_query":"!true!"})
        return javascript_generator
    
    @staticmethod
    def process_request(data):
        try:
            if (getprocessed().path_page_stack[-1] == "/my_work"):
                active_section_key = \
                    DatabaseUser.get_single_value(None, "active_section")
                active_section = Section.get(active_section_key)
                data["section"] = str(active_section_key)
                data["section_name"] = unicode(active_section)
        except:
            pass

#----------------------------------------------------------------------
class StudentRecordsCheckForm(BaseStudentDBForm):
    """
    This form presents a page to generate a several student record
    error forms.
    """
    section_name = forms.CharField(required = False, label="Section",
                    widget=forms.TextInput(attrs= 
                        {'class':'autofill required', "size":11}))
    section = forms.CharField(required=False, widget=forms.HiddenInput)
    report_type = forms.ChoiceField(required=False,
            choices=(("Missing Fields","Missing Fields"), 
                     ("No Section","No Section"),
                     ("No Current Enrollment", "No Current Enrollment")), 
            initial="Missing Fields")
    
    def modify_params(self, params):
        params["title_prefix"] = "Create"
        
    def generate_javascript_code(self, javascript_generator):
        sect = javascript_generator.add_autocomplete_field(
            class_name = "section")
        return javascript_generator

#----------------------------------------------------------------------  
class Form1ReportForm(BaseStudentDBForm):
    """
    This form presents a page to generate a school register form.
    """
    section_name = forms.CharField(required = False, label="Section",
                    widget=forms.TextInput(attrs= 
                        {'class':'autofill required', "size":11}))
    section = forms.CharField(required=False, widget=forms.HiddenInput)
    gender = forms.ChoiceField(required=False, label="Gender",
            choices=(("Male","Male"), ("Female","Female")), initial="Male")

    def modify_params(self, params):
        params["title_prefix"] = "Create"
        
    def generate_javascript_code(self, javascript_generator):
        sect = javascript_generator.add_autocomplete_field(
            class_name = "section")
        return javascript_generator

#----------------------------------------------------------------------  
class Form2ReportForm(BaseStudentDBForm):
    """
    This form presents a page to generate a Form 2 Monthly Attendance
    Report
    """
    section_name = forms.CharField(required=False,
            widget=forms.TextInput(attrs={'class':'autofill entry-field required'}))
    section = forms.CharField(required=False, widget=forms.HiddenInput)
    month = forms.DateField(required=False, 
            widget=forms.DateInput(format="%m/%Y", attrs={"size":7,
            "class":"month-mask required entry-field"}))

    def modify_params(self, params):
        params["title_prefix"] = "Create"
        school = SchoolDB.models.getActiveDatabaseUser().get_active_organization()
        division = school.division
        region = division.region
        params["schoolname"] = unicode(school)
        params["division"] = unicode(division)
        params["region"] = unicode(region)
        
    def generate_javascript_code(self, javascript_generator):
        sect = javascript_generator.add_autocomplete_field(
            class_name = "section")
        
#----------------------------------------------------------------------  
class Form14ReportForm(BaseStudentDBForm):
    """
    This form is the standard report form for the school for
    achievement tests.
    """
    section_name = forms.CharField(required=False, label="Section",
            widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    section = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")
    achievement_test_name = forms.CharField(required=False, 
            label="Achievement Test",
            widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    achievement_test = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")   
    gender = forms.ChoiceField(required=False, label="Gender",
            choices=(("Male","Male"), ("Female","Female")), initial="Male")
    parent_form = BaseStudentDBForm
    
    def modify_params(self, params):
        params["title_prefix"] = "Create"
        school = SchoolDB.models.getActiveDatabaseUser().get_active_organization()
        division = school.division
        region = division.region
        params["schoolname"] = unicode(school)
        params["division"] = unicode(division)
        params["region"] = unicode(region)
        #fix this to work from achievemnt test selected
        params["school_year"] = unicode(SchoolYear.school_year_for_date())
        
    def generate_javascript_code(self, javascript_generator):
        sect = javascript_generator.add_autocomplete_field(
            class_name = "section", field_name = "id_section_name",
            key_field_name = "id_section")
        achtest = javascript_generator.add_autocomplete_field(
            class_name = "achievement_test", 
            field_name = "id_achievement_test_name",
            key_field_name = "id_achievement_test")


#----------------------------------------------------------------------  
class BaseSummaryForm(BaseStudentDBForm):
    """
    This form creates a summary report of student information for higher
    level organizations.
    """
    all_organizations = forms.BooleanField(required=False)
    #position = forms.CharField(required=False)
    by_gender = forms.BooleanField(required=False, 
                                       label="Show By Gender")
    by_class_year = forms.BooleanField(required=False, 
                                       label="Summarize by Class Year")
    single_line_per_school = forms.BooleanField(required=False, 
label="Single Line Per School")
    
    def modify_params(self, params):
        params["title_prefix"] = "Create"        
        org_type = SchoolDB.models.getActiveDatabaseUser().get_active_organization_type()
        params["upper_level_hide"] = ' class="hidden" '
        params["school_hide"] = ' class="hidden" '
        if (org_type == "DepEd Region"):
            params["next_level_name"] = "DepEd Division"
            params["upper_level_hide"] = ''
        elif (org_type == "Division"):
            params["next_level_name"] = "School"
            params["upper_level_hide"] = ''
        else:
            params["school_hide"] = ''
            params["is_school"] = True
    
    def generate_javascript_code(self, javascript_generator):
        org = \
            SchoolDB.models.getActiveDatabaseUser().get_active_organization()
        org_choices = org.get_subordinate_organizations_choice_list()
        selected_fields_table = SchoolDB.gviz_api.DataTable(
            ("field","string","Selected Fields"))
        selected_fields_table.LoadData([])
        selected_fields_descriptor = "(%s)" %selected_fields_table.ToJSon()
        field_choices_table = SchoolDB.gviz_api.DataTable(
            ("field","string","Field Choices"))
        selected_orgs_table = SchoolDB.gviz_api.DataTable(
            ("field","string","Selected Organizations"))
        selected_orgs_table.LoadData([])
        selected_orgs_descriptor = "(%s)" %selected_orgs_table.ToJSon()
        org_choices_table = SchoolDB.gviz_api.DataTable(
            ("field","string","Organization Choices"))
        org_choices_table.LoadData(org_choices)
        org_choices_descriptor = "(%s)" %org_choices_table.ToJSon()
        javascript_generator.add_javascript_params({
            "selected_fields_table":selected_fields_descriptor,
            "org_choices_table":org_choices_descriptor,
            "selected_orgs_table":selected_orgs_descriptor})
        return field_choices_table

#----------------------------------------------------------------------  
class AchievementTestSummaryForm(BaseSummaryForm):
    achievement_test_name = forms.CharField(required=False, 
            label="Achievement Test",
            widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    achievement_test = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")   
    subject_name = forms.CharField(required=False, 
            label="Subject",
            widget=forms.TextInput(attrs={'class':'autofill entry-field'}))
    subject = forms.CharField(required=False,
                              widget=forms.HiddenInput, initial = "")   
    parent_form = BaseSummaryForm
    
    def modify_params(self, params):
        self.parent_form.modify_params(self, params)
        params["title_bridge"] = " An "
        params["title_suffix"] = "Achievement Test Summary Report"
        params["report_title"] = "Achievement Test Summary"
        params["show_choose_fields_block"] = True
        params["achievement_test"] = True

    def generate_javascript_code(self, javascript_generator):
        achtest = javascript_generator.add_autocomplete_field(
            class_name = "achievement_test")
        field_choices_table = self.parent_form.generate_javascript_code(
            self, javascript_generator)
        field_choices_table.LoadData(
            SchoolDB.reports.AchievementTestReport.get_report_field_choices())
        field_choices_descriptor = "(%s)" %field_choices_table.ToJSon()
        sub = javascript_generator.add_autocomplete_field(
            class_name = "subject",
            ajax_root_path = "/ajax/get_subjects_for_achievement_test")
        sub.add_dependency(achtest)
        javascript_generator.add_javascript_params({
            "field_choices_table":field_choices_descriptor,
            "report_type":"achievementTest"})

#----------------------------------------------------------------------  
class StudentSummaryForm(BaseSummaryForm):
    parent_form = BaseSummaryForm
    
    def modify_params(self, params):
        self.parent_form.modify_params(self, params)
        params["title_suffix"] = "Student Statistics Summary Report"
        params["report_title"] = "Student Statistics Summary"
        params["show_choose_fields_block"] = True

    def generate_javascript_code(self, javascript_generator):
        field_choices_table = self.parent_form.generate_javascript_code(
            self, javascript_generator)
        field_choices_table.LoadData(
            SchoolDB.reports.StudentSummaryReport.get_report_field_choices())
        field_choices_descriptor = "(%s)" %field_choices_table.ToJSon()
        javascript_generator.add_javascript_params({
            "field_choices_table":field_choices_descriptor,
            "report_type":"studentSummary"})

#----------------------------------------------------------------------  
class VersionedTextManagerForm(BaseStudentDBForm):
    name = forms.CharField(required=True, max_length=60, label="Name*",
                           widget=forms.TextInput(attrs={'class':'required', 
                                                         'minlength':'5'}))
    title = forms.CharField(required = False, label = "Title")
    help_formatted = forms.BooleanField(required = False, initial = True,
                                        label = "Formatted for Help")
    page_template = forms.CharField(required = False, 
                                    label = "Page Template Name")
    dialog_template = forms.CharField(required = False, 
                                      label = "Dialog Template Name",
                                      initial = "simple_dialog.html")
    general_info = forms.CharField(required=False, label = 
                        "Other Information",
                        max_length=1000, widget=forms.Textarea(
                        attrs={'cols':50, 'rows':3, 'class':'entry-field'}))
    revision_number = forms.CharField(required=True, max_length=60, 
                    label="Revision Number*",
                    widget=forms.TextInput(attrs={'class':'required'}))
    open_text_window = forms.BooleanField(required = False, 
                                          widget=forms.HiddenInput)
    new_text_page = forms.CharField(required=False, 
                                   widget=forms.HiddenInput)
    element_names = ['name', 'title', 'help_formatted','dialog_template', 
                     'page_template','general_info', 'revision_number']
    
    parent_form = BaseStudentDBForm
    
    def save(self, instance):
        """
        Perform a standard save action. If new_text_page is true then
        create a new history entry, a new page, and open the page. Just
        open the current page if false.
        """
        saved_instance = BaseStudentDBForm.save(self, instance)
        if self.cleaned_data["new_text_page"]:
            saved_instance.create_new_revision(self.revision_number)
        return saved_instance
   
    def post_creation(self):
        """
        Create an initial text page when the manager is first created
        """
        pass
        #self.create_new_instance(self.revision_number)
        
    def create_new_instance(self):
        """
        Use the model create function to assure everything initialized
        correctly.
        """
        return SchoolDB.models.VersionedTextManager.create(
            name = self.cleaned_data["name"])

    @staticmethod
    def generate_select_javascript_code(javascript_generator,
                                        select_field):
        select_field.add_extra_params({
            "extra_fields":"title|revision_number|dialog_template|page_template", "filter_school":"false" })
     
    def generate_custom_return(self, instance):
        text_page = instance.get_current_version()
        if text_page:
            return specialShowAction(text_page, "Edit", "versioned_text",
                VersionedTextForm, "Text Page", "versioned_text",
                "versioned_text")
                    
#----------------------------------------------------------------------
class VersionedTextForm(BaseStudentDBForm):
    manager = forms.CharField(required=False, 
                                   widget=forms.HiddenInput)
    revision_number = forms.CharField(required=False, label="Revision:")
    last_edit_date = forms.DateField(required=False,
        widget=forms.DateInput(format="%m/%d/%Y", attrs={"size":12,
           "class":"date-mask popup-calendar entry-field"}))
    author_name = forms.CharField(required=False,
                            label="Author:",
                            widget=forms.TextInput(attrs={
                                'class':'autofill entry-field'})) 
    author = forms.CharField(required=False, 
                                   widget=forms.HiddenInput)
    comment = forms.CharField(required=False, label="Comments",
                    max_length=200, widget=forms.Textarea(
                    attrs={'cols':50, 'rows':1, 'class':'entry-field'}))
    content = forms.CharField(required=True, 
                    label='Page Text', widget=forms.Textarea(
                    attrs={'cols':90, 'rows':40, 
                           'class':'entry-field text-page-edit'}))
    parent_form = BaseStudentDBForm
    element_names = ["revision_number", "last_edit_date", "author",
                     "comment", "content"]
    
    def generate_javascript_code(self, javascript_generator):
        author = javascript_generator.add_autocomplete_field(
            field_name = "id_author_name",
            key_field_name = "id_author",
            class_name = "database_user")
        return javascript_generator

    @staticmethod
    def initialize(data):
        initialize_fields([("author", "author_name")], data)
#-------------------------Special Purpose Forms------------------------
# These forms are used for testing and maintenance and are not meant 
# for normal work.

class GenerateGradesForm(BaseStudentDBForm):
    """
    This form is used to define which acheivement tests, grading instances, 
    and class years will have grades automatically filled in. It is meant
    only for testing and should never be used on a real site. The url 
    should be typed in and only available to the the database developer.
    Warning:Dangerous!
    """
    class_year = forms.CharField(required=True,
                             widget=forms.TextInput(attrs={
                                 'class':'autofill required entry-field'}))

    achievement_test_name = forms.CharField(required = False, 
                label="Achievement Test:", widget=forms.TextInput(attrs=
                {'class':'autofill entry-field'}))
    achievement_test = forms.CharField(required = False, 
                                   widget=forms.HiddenInput, initial="")
    grading_period_name = forms.CharField(required = False, 
                label="Grading Period:", widget=forms.TextInput(attrs=
                {'class':'autofill entry-field'}))
    grading_period = forms.CharField(required = False, 
                                   widget=forms.HiddenInput, initial="")
    fixed_seed = forms.BooleanField(required=False)
    
    def generate_javascript_code(self, javascript_generator):
        clsyr = javascript_generator.add_autocomplete_field(
            class_name = "class_year", field_name = "id_class_year")
        clsyr.set_local_choices_list(SchoolDB.choices.ClassYearNames)
        achtest = javascript_generator.add_autocomplete_field(
            class_name = "achievement_test")
        gdprd = javascript_generator.add_autocomplete_field(
            class_name = "grading_period")
        gdprd.add_extra_params({"use_class_query":"!true!"})
    
    def save(self, instance):
        """
        This is a replacement for the normal save action. Nothing will
        saved. The data will be used to initiate the  grades generation.
        """
        class_year = self.cleaned_data["class_year"]
        achievement_test = self.cleaned_data["achievement_test"]
        grading_period = self.cleaned_data["grading_period"]
        if (achievement_test):
            SchoolDB.local_utilities_functions.create_fake_at_grades(class_year, achievement_test)
        elif grading_period:
            SchoolDB.local_utilities_functions.create_fake_gp_grades(class_year, grading_period)
        
        
#--------------------------Utility Functions---------------------------
def convert_to_field_value(instance, field_name):
    """
    If the field contains a reference to another object, convert to a string.
    If not, just return the value.
    """
    form_value = None
    if hasattr(instance, field_name):
#  if name_is_in_model(instance,field_name):
        form_value = instance.__getattribute__(field_name)
        if is_reference(instance, field_name) and form_value:
            form_value = str(form_value.key())
    return form_value

def convert_to_instance_value(instance, field_name, form_value):
    """
    If the field contains a reference to another object, convert the form
    string value to an instance key. If the field is other than a reference
    return it unchanged.
    """
    instance_value = form_value
    if is_reference(instance, field_name):
        instance_value = convert_string_to_key(form_value)
    return instance_value

def is_reference(instance,field_name):
    """
    Determine if the attribute in the model of the instance is a reference
    by the name of the attribute. Return false if no such attribute exists.
    """
    is_a_reference = False
    if name_is_in_model(instance,field_name):
        properties_dict = instance.properties()
        attribute = properties_dict[field_name]
        is_a_reference = isinstance(attribute, db.ReferenceProperty)
    return is_a_reference

def convert_string_to_key(keystring):
    """
    Try to convert a string expected to be the stringified key
    to a model instance. Return None if unsuccessful.
    """
    model_instance = None
    if ((len(keystring) != 0) and (keystring != "NOTSET")) :
        try:
            dbkey=db.Key(keystring)
            model_instance = db.get(dbkey)
        except db.BadKeyError:
            model_instance = None
    return model_instance

def name_is_in_model(instance, name):
    """
    Confirm that there is a model attribute of the instance by
    that name.
    """
    properties_dict = instance.properties()
    return properties_dict.has_key(name)

#----------------------------------------------------------------------
def get_return_page_from_cookie():
    """
    Use the information from the "return_to_page" value in the current
    cookie to choose the next page to be displayed. The value will have
    '/' char replaced by '%02f' so they must be reconverted
    """
    return_page = getprocessed().return_page
    if (not return_page):
        return_page = "/index"
    return return_page

#----------------------------------------------------------------------
def map_page_to_usertype(page, perform_mapping = True):
    """
    Some pages are different for each type of user. All top level pages
    and some others are different. This function performs the mapping
    from the generic name to the specific name. This also helps
    security by mapping away from restricted pages. Pages which are
    common to all users are passed through unchanged. The mapping
    dictionaries are included within this function. 
    """
    #Again perform legal mapping to assure that a bad page cannot be
    #accessed. This blocks attempts to use edited cookie.
    if (not users.is_current_user_admin()):
        if (not getActiveDatabaseUser().get_active_user_type().legal_url(
            page)):
            #this will end all further processing of the request
            raise ProhibitedURLError, page  

    teacher = {"":"schoolhome",
               "index":"schoolhome",
               "maint":"school_maint" 
               }
    school_db_administrator = {"":"schoolhome",
               "index":"schoolhome",
               "maint":"schooladmin_maint",
               "database_user":"standard_database_user"}
    upper_level_user = {"":"upperlevel_home", 
                   "index":"upperlevel_home", 
                   "maint":"upperlevel_maint"}
    upper_level_db_administrator = {"":"upperlevel_adminhome",
                                    "index":"upperlevel_adminhome",
                                    "maint":"upperleveladmin_maint",
                                    "database_user":"standard_database_user"}
    master = {"":"masterhome",
              "index":"masterhome",
              "maint":"othertypes",
              "database_user":"master_database_user"
              } 
    dict_map = {"Master":master,"Teacher":teacher, 
              "SchoolDbAdministrator":school_db_administrator, 
              "UpperLevelUser":upper_level_user,
              "UpperLevelDbAdministrator":upper_level_db_administrator}
    page_map = dict_map[unicode(getActiveDatabaseUser().get_active_user_type())]
    # strip leading slash if present
    page = page.lstrip('/')
    if perform_mapping:
        return_page = page_map.get(page, page)
    else:
        return_page = page
    return return_page
#----------------------------------------------------------------------
def map_form_to_usertype(formname, perform_mapping = True):
    """
    Some pages are different for each type of user. All top level pages
    and some others are different. This function performs the mapping
    from the generic name to the specific name. This also helps
    security by mapping away from restricted pages. Pages which are
    common to all users are passed through unchanged. The mapping
    dictionaries are included within this function. 
    """
    teacher = {}
    school_db_administrator = {
        "StandardDatabaseUserForm":"StandardDatabaseUserForm"}
    upper_level_user = {}
    upper_level_db_administrator = {
        "StandardDatabaseUserForm":"StandardDatabaseUserForm"}
    master = {"StandardDatabaseUserForm":"MasterDatabaseUserForm"}
    dict_map = {"Master":master,"Teacher":teacher, 
              "SchoolDbAdministrator":school_db_administrator, 
              "UpperLevelUser":upper_level_user,
              "UpperLevelDbAdministrator":upper_level_db_administrator}
    form_map = dict_map[unicode(getActiveDatabaseUser().get_active_user_type())]
    if perform_mapping:
        return_form = form_map.get(formname, formname)
    else:
        formname = formname
    return formname
#----------------------------------------------------------------------

def perform_utilities():
    """
    Perform misc utilities for database maintainance 
    """
    # load municipalities from html file
    results = "No action"
    #results = load_provinces.scan_file('data/communitys.html')
    #remove_from_database("Organization")
    #remove_from_database("Province")

def convert_form_date(string_val, alternate_date=None):
    """
    A date will be returned as a string in the format as entered in a
    form -- "mm/dd/yyyy" that it is entered. Parse it and then convert
    to a python date. The alternate_date will be returned if the parsed
    date is unusable.
    """
    the_date = alternate_date
    if string_val and (len(string_val) > 7):
        try:
            #just use the exception to handle any problems
            date_string = str(string_val)
            month, day, year = date_string.split("/")
            the_date = date(int(year),int(month),int(day))
        except StandardError:
            the_date = alternate_date
    return the_date


def add_history_field_params(param_dict, entity_name_tuple):
    """
    The HTML code for a history entry (a single row) is fairly lengthy.
    This hides much of the text in a few named fields. Each history entity
    in the form has its own custom definitions to make the use in
    the template much cleaner.
    """
    css_warning_class = "warning-field hidden"
    entity_name, display_name, extra_text = entity_name_tuple
    change_warning = """
  <tr class="%s" id="id_%s_warning">
  <td>--></td>
  <td colspan="4">
  %s has changed. Please enter the date of the change.
  </td></tr> 
  """ %(css_warning_class, entity_name, display_name)
    dict_name = entity_name + "_change_warning"
    param_dict[dict_name] = change_warning
    field_label = """
  <tr>
  <td><label for="id_%s" id="label_%s">%s:%s</label></td>
  <td> """ %(entity_name, entity_name, display_name, extra_text)
    dict_name = entity_name + "_field_label"
    param_dict[dict_name] = field_label
    date_label = """
  </td>
  <td id="id_%s_change_date_label" >
  <label for="id_%s_change_date" id="label_%s_change_date">Date of Change:</label></td>
  <td id="id_%s_change_date_field" >
  <div class="fieldWrapper">
  """ %(entity_name, entity_name, entity_name, entity_name)
    dict_name = entity_name + "_date_label"
    param_dict[dict_name] = date_label
    button = """
  </div></td>
  <td><input id="%s_edit_btn" value="View All" class="btn tb inside"
         onclick="edit_history('%s', '%s');" type="button" title="View all history entries for %s"></input> </td>
         </tr>
  """ %(entity_name, entity_name, display_name, display_name)
    dict_name = entity_name + "_button"
    param_dict[dict_name] = button

#----------------------------------------------------------------------
def create_section_students_table(parameter_dict, primary_object,
                                        secondary_class, secondary_object):
    """
    Create the list of students in a section that will be used in a
    selection table. The table is a simple one with the standard three
    columns for the student name. There may be a fourth column if the
    special field parameter is set. If the special field is
    "records_check" then the column shows if the student record has all
    fields completed. If the special field is "assignment_status" then
    the column shows if the student has been assigned to the class
    session defined in parameter "class_session". 
    The primary_object is the section.
    """
    special_field = parameter_dict.get("special_field","")
    class_session = parameter_dict.get("class_session","")
    query = SchoolDB.models.Student.all()
    SchoolDB.models.active_student_filter(query)
    query.filter("section = ", primary_object)
    query.order("last_name")
    query.order("first_name")
    selection_table = []
    selection_keys = []
    table_description = [('last_name', 'string', 'Family Name'),
                         ('first_name', 'string', 'First Name'),
                         ('middle_name', 'string', 'Middle Name')]
    if (special_field == "records_check"):
        table_description.append(
            ('record_complete', 'string', 'Record Complete'))
    elif (special_field == "assignment_status"):
        table_description.append(
            ('record_complete', 'string', 'Assignment Status'))       
    for student in query:
        table_entry = [student.last_name, student.first_name, 
                student.middle_name]
        if (special_field == "records_check"):
            missing_fields, missing_fields_count = \
                          student.get_missing_fields()
            if (missing_fields_count == 0):
                table_entry.append("OK")
            else:
                table_entry.append("Incomplete")
        elif (special_field == "assignment_status"):
            class_session_key = db.Key(class_session)
            classes = student.get_active_class_sessions()
            if (classes.count(class_session_key) > 0):
                table_entry.append("Assigned")
            else:
                table_entry.append("Not yet assigned")            
        selection_table.append(table_entry)
        selection_keys.append(str(student.key()))
    return(table_description, selection_table, selection_keys, None, "")

#----------------------------------------------------------------------

def create_class_session_students_table(parameter_dict, primary_object,
                                        secondary_class, secondary_object):
    """
    Create the list of students in a class session that will be used in a
    selection table. The table is a simple one with the standard three
    columns for the student name.
    The primary_object is the class session.
    """
    students, student_records, student_record_dict =\
            primary_object.get_students_and_records(status_filter="Active",
                                                    sorted=True)
    selection_table = []
    selection_keys = []
    for student in students:
        name = student.full_name_lastname_first()
        gender = student.gender
        class_year = student.class_year
        section = unicode(student.section)        
        table_entry = [name, gender, class_year, section]
        selection_table.append(table_entry)
        selection_keys.append(str(student.key()))
    table_description = [('name', 'string', 'Name'),
                ('gender', 'string', 'Gender'),
                ('class_year','string','Class Year'),
                ('section', 'string', 'Section')]
    return(table_description, selection_table, selection_keys, None, "")

#----------------------------------------------------------------------

def create_section_classes_table(parameter_dict, primary_object,
                                        secondary_class, secondary_object):
    """
    Create the list of students in a class session that will be used in a
    selection table. The table is a simple one with the standard three
    columns for the student name.
    The primary_object is the class session.
    """
    query = SchoolDB.models.ClassSession.all()
    query.filter("organization = " , 
                SchoolDB.models.getActiveDatabaseUser().get_active_organization())
    query.filter("section = ", primary_object)
    query.filter("school_year =", SchoolDB.models.SchoolYear.school_year_for_date())
    class_sessions = query.fetch(100)
    ordered_class_sessions = SchoolDB.models.ClassSession.sort_by_time(class_sessions)
    selection_table = []
    selection_keys = []
    for session  in ordered_class_sessions:
        table_entry = (unicode(session.class_period), session.name,
                       unicode(session.teacher), unicode(session.subject))
        selection_table.append(table_entry)
        selection_keys.append(str(session.key()))
    table_description = [('period', 'string', 'Period'),
                ('name', 'string', 'Class Name'),
                ('teacher', 'string', 'Teacher'),
                ('subject', 'string', 'Subject')]
    return(table_description, selection_table, selection_keys, None, "")

#----------------------------------------------------------------------

def create_students_eligible_for_class_table(parameter_dict, primary_object,
                                        secondary_class, secondary_object):
    """
    Create the list of students with the designated major who are of
    the defined class year and are notalready assigned to a class of
    this type for this school year.
    """
    class_year = parameter_dict["class_year"]
    student_major = primary_object
    students_query = SchoolDB.models.Student.all()
    students_query.filter("organization = " , 
            SchoolDB.models.getActiveDatabaseUser().get_active_organization())
    students_query.filter("class_year = ", class_year)
    students_query.filter("student_major = ", student_major)
    SchoolDB.models.active_student_filter(students_query)
    all_legal_students = students_query.fetch(1000)
    if (parameter_dict.get("list_all_students", False)):
        eligible_students = all_legal_students
    else:
        #The normal case where students that are already assigned to a class
        #do not show up
        classes_query = db.Query(SchoolDB.models.ClassSession,
                                 keys_only = True)
        classes_query.filter("organization = " , 
                SchoolDB.models.getActiveDatabaseUser().get_active_organization())
        classes_query.filter("student_major", student_major)
        #classes are not filtered by class year because the student might take
        #a class of a different year level
        majors_classes = classes_query.fetch(1000)
        eligible_students = []
        for student in all_legal_students:
            #get a list of the students class records that are currently
            active_class_sessions = \
                    student.get_active_class_sessions()
            found_class_session = None
            for session in active_class_sessions:                
                found_class_session = majors_classes.count(session)
                if found_class_session:
                    break
            if (not found_class_session):
                eligible_students.append(student)
    selection_table = []
    selection_keys = []
    for student in eligible_students:
        name = student.full_name_lastname_first()
        gender = student.gender
        class_year = student.class_year
        section = unicode(student.section)        
        table_entry = [name, gender, class_year, section]
        selection_table.append(table_entry)
        selection_keys.append(str(student.key()))
    table_description = [('name', 'string', 'Name'),
                ('gender', 'string', 'Gender'),
                ('class_year','string','Class Year'),
                ('section', 'string', 'Section')]
    #for student in eligible_students:
        #table_entry = (student.last_name, student.first_name, 
                #student.middle_name, unicode(student.section))
        #selection_table.append(table_entry)
        #selection_keys.append(str(student.key()))
    #table_description = [('last_name', 'string', 'Family Name'),
                #('first_name', 'string', 'First Name'),
                #('middle_name', 'string', 'Middle Name'),
                #('section', 'string', 'Section')]
    return(table_description, selection_table, selection_keys, None, "")

#----------------------------------------------------------------------

def initialize_fields(fields_list, data):
    #The fields list has tuples that are pairs of the values for 
    #the the key field and the name field for that key.
    for data_value in fields_list:
        key_string = data[data_value[0]]
        if key_string:
            linked_object = convert_string_to_key(key_string)
            if (linked_object):
                data[data_value[1]] = unicode(linked_object)

#----------------------------------------------------------------------

def get_form_from_class_name(class_name_string):
    """
    Map a string that is the model class name to the associated
    form class. Return None if not found.
    """
    if (class_name_string):
        class_formname_map = {
            "my_choices":(MyChoicesForm),
            "achievement_test":(AchievementTestForm),
            "administrator":(AdministratorForm),
            "attendance":(AttendanceForm), 
            "calendar":(SchoolCalendarForm),
            "community":(CommunityForm),
            "classroom":(ClassroomForm),
            "class_session":(ClassSessionForm),
            "class_period":(ClassPeriodForm),
            "contact":(ContactForm),
            "database_user":(StandardDatabaseUserForm),
            "division":(DivisionForm),
            "grading_instance":(GradingInstanceForm),
            "grading_period":(GradingPeriodForm),
            "grading_period_results":(GradingPeriodResultsForm),
            "municipality":(MunicipalityForm),
            "my_work":(MyWorkForm),
            "organization":(OrganizationForm),
            "parent_or_guardian":(ParentOrGuardianForm),
            "province":(ProvinceForm),
            "region":(RegionForm), 
            "school":(SchoolForm),
            "school_day":(SchoolDayForm),
            "school_day_type":(SchoolDayTypeForm),
            "school_year":(SchoolYearForm),
            "grading_period":(GradingPeriodForm),
            "section":(SectionForm),
            "section_type":(SectionTypeForm),
            "special_designation":(SpecialDesignationForm),
            "student":(StudentForm),
            "student_major":(StudentMajorForm),
            "student_status":(StudentStatusForm),
            "subject":(SubjectForm),
            "teacher":(TeacherForm),
            "user_type":(UserTypeForm),
            "versioned_text_manager":(VersionedTextManagerForm),
            "versioned_text":(VersionedTextForm)
        }
        form_class = class_formname_map.get(class_name_string, None)
    return form_class

#----------------------------------------------------------------------

def filter_keystring(keystring):
    """
    Perform initial protective filtering on string. This doesn't
    mean that the key is valid, just that it is not too long and 
    contains only letters and numbers. It may return a truncated
    key or, if invalid characters are discovered no key at all.
    """
    if keystring:
        keystring = keystring[0:150]
        keystring = keystring.strip()
    return keystring

#----------------------------------------------------------------------
class ProcessedRequest:
    """
    A simple enhancement of the Dango HttpRequest class. This adds some
    trivial parsing of the data for key values used repeatedly in view
    functions. These are form fields defined in either the form objects
    or the page template that are available at any form submission.
    They are not provided or used in ajax requests. Static page
    requests rely on the default values programmed into this class. The
    key values are:
    --- selection_key: the string value of the key returned in a 
        selection request
    --- selection_instance: the database instance associated with
        the key
    --- selection_key_valid: boolean is true if selection key was given
        and yielded a valid selection instance
    --- prior_selection: the previous selection key used in some two stage
        requests
    --- state - the current state of the instance that is being acted upon
         [New, Exists]
    --- requested_action:  
        -"Create" - create a fresh form for the class to be returned
        -"Edit" - return a form with the data from an existing instance
        -"Further Selection" - make a second selection with the returned
            selection key returned in a value in the javascript params
        -"Save" - save the data from the edited form and return to 
            "return_page" defined in the initial "showXX python function
        -"Ignore" - do nothing, return to predefined return url. Any
            unknown actions are mapped to Ignore
    ---values_dict: a copy of the request MultiValueDict that is mutable
    """
    def __init__(self, request = None):
        self.selection_key = None
        self.requested_instance = None
        self.selection_key_valid = False
        self.current_object_key = None
        self.current_instance = None
        self.current_instance_valid = False
        self.state = "New"
        self.requested_action = "Edit"
        self.prior_selection = None
        self.cookies = None
        self.return_page = ""
        self.values = {}
        if request:
            if request.method == "POST":
                data = request.POST
            else:
                data = request.GET
            for k in data.keys():
                self.values[k] = data[k]
            self.selection_key = filter_keystring(
                self.values.get("selection_key", None))
            if (self.selection_key):
                self.requested_instance = \
                    SchoolDB.models.get_instance_from_key_string(self.selection_key)
                self.selection_key_valid = (self.requested_instance != None)
            self.current_instance_key = filter_keystring(
                self.values.get("object_instance", None))
            if (self.current_instance_key):
                self.current_instance = \
                    SchoolDB.models.get_instance_from_key_string(self.current_instance_key)
                self.current_instance_valid = (self.current_instance != None)
            self.cookies = request.COOKIES
            if (self.cookies):
                # limit size of return page text to prevent
                # attack
                rptext = \
                    self.cookies.get("nP","/index")[:150]
                self.return_page = \
                    SchoolDB.utility_functions.cleanup_django_escaped_characters(
                        rptext)
                self.bc_page_stack = self.get_path_stack("bcSt")
                self.path_page_stack = self.get_path_stack("pgSt")
                logging.info("-----------next:'%s'" %self.return_page)
                logging.info("-----------bc stack: '%s'" %self.bc_page_stack)
                logging.info("-----------path stack: '%s'" %self.path_page_stack)
            #filter for unkown or illegal values
            self.state = self.values.get("state","New")
            if (["New","Exists"].count(self.state) == 0):
                self.state = "New"
            self.requested_action = \
                self.values.get("requested_action", "Edit")
            if (["Create", "Edit", "View", "Save", "Select", 
                 "Further Selection"].count(self.requested_action) == 0):
                self.requested_action = "Ignore"
            self.prior_selection = filter_keystring(
                self.values.get("prior_selection", None))
    def get_path_stack(self, cookie_name):
        text = self.cookies.get(cookie_name,"[]")[:200]
        cleaned = \
            SchoolDB.utility_functions.cleanup_django_escaped_characters(text)
        try:
            page_stack = simplejson.loads(cleaned)
        except:
            page_stack = []
        return page_stack

#----------------------------------------------------------------------

def getprocessed():
    """
    Always use this function to get the processed request info
    """
    global __processed_request__
    return __processed_request__

def getrequest():
    """
    Always use this function to get the direct request
    """
    global __http_request__
    return __http_request__

def initrequest(http_request):
    global __http_request__
    global __processed_request__
    __http_request__ = http_request
    __processed_request__ = ProcessedRequest(http_request)

#----------------------------------------------------------------------
class BreadcrumbGenerator:
    """
    Create a description of the webpage structure of a site to 
    generate the html text for the breadcrumb line. The structure
    is defined page by page with the add_page command with three
    arguments: the page title, the url of the page, and the title
    of the parent. The structure can also be defined in one or 
    more lists of tuples of the three values using add_pages.
    Once the structure is defined it can either be recovered in 
    a list of the path from the root page to the requested page.
    More usefully, a completely formatted webpage entry for a page
    can be generated with command generate_breadcrumb.
    """
    #title_tree = {}
    #url_dict = {}

    #def add_page(self, title, url, parent_title):
        #self.url_dict[title] = url
        #self.title_tree[title] = parent_title

    #def add_pages(self, pages_list):
        #for page in pages_list:
            #self.add_page(page[0],page[1],page[2])

    #def get_breadcrumb_list(self, title):
        #breadcrumb_list = []
        #while self.title_tree.has_key(title):
            #breadcrumb_list.insert(0,((self.url_dict[title], title)))
            #title = self.title_tree[title]       
        #return breadcrumb_list

    #def has_page(self, title):
        #return self.url_dict.has_key(title)
    name_map = {
        "index":"Main Menu",
        "upperlevel_adminhome":"Main Menu",
        "upperlevel_home":"Main Menu",
        "schoolhome":"Main Menu",
        "my_work":"My Work",
        "student":"Student",
        "section":"Section",
        "choose_report":"Choose a Report Type",
        "attendance":"Enter Attendance",
        "section_students":"Section Students",
        "class_session_students":"Class Students",
        "section_classes":"Section Class Schedule",
        "student_emergency":"Student Emergency",
        "othertypes":"Special Information",
        "teacher":"Teacher",
        "administrator":"Administrator",
        "class_session":"Class",
        "subject":"Subject",
        "section_type":"Section Type",
        "student_major":"Student Major",
        "special_designation":"Special Designation",
        "school":"School",
        "region":"Region",
        "division":"Division",
        "province":"Province",
        "municipality":"Municipality",
        "community":"Barangay",
        "otherwork":"Other Work",
        "database_user":"Database User",
        "master_database_user":"Database User",
        "standard_database_user":"Database User",
        "user_type":"User Type",
        "school_year":"School Year",
        "calendar":"School Calendar",
        "schoolday":"School Day",
        "school_day_type":"School Day Type",
        "class_period":"Class Period",
        "achievement_test":"Achievement Test",
        "achievement_test_grades":"Achievement Test Grades",
        "versioned_text_manager":"Text Manager",
        "attendance_report":"Attendance Report",
        "assign_students":"Assign Students",
        "student_age":"Student Age Distribution",
        "section_list":"Section List",
        "school_register":"School Register",
        "section_grading_period_grades":"Grading Period Grades",
        "choose_custom_report":"Choose a Custom Report",
        "custom_report":"Custom Report", 
        "student_record_check":"Student Record Check",
        "grades":"Grades", 
        "grading_instance":"Grading Instance",
        "enter_grades":"Enter Grades",
        "grading_period_results":"Grading Period Grades",
        "gradebook_entry_calendar":"Gradebook Entry Calendar",
        "utilrequest":"Run Utility",
        "utilresponse":"Utility Response"
    }
    
    def get_breadcrumb_list(self, cookies):
        """
        Create a list of breadcrumb names from the breadcrumb path
        cookie created by the web page. The path names are mapped via
        the name_map_dict to the breadcrumb name for each path name.
        """
        page_stack = ["index"]
        if (cookies):
            bctext = cookies.get("bcSt","[]")[:200]
            bccleaned = \
                SchoolDB.utility_functions.cleanup_django_escaped_characters(
                            bctext)
            try:
                page_stack = simplejson.loads(bccleaned)
            except:
                pass
        path_list = [ path.lstrip("/") for path in page_stack]
        name_list = []
        for path in path_list:
            name = ""
            name_end = ""
            full_path = path
            if (path.startswith("select/")):
                path = path.replace("select/", "")
                name = "Select "
            if (path.startswith("initialselect/")):
                path = path.replace("initialselect/", "")
                name = "Select "
                path = path.split("/")[0]
            if (path.startswith("choose/")):
                path = path.replace("choose/", "")
                name = "Choose "
            if (path.startswith("reports/")):
                path = path.replace("reports/", "")
            map_name = self.name_map.get(path, "Current Page")
            name = name + map_name + name_end
            name_list.append((full_path,name))
        return name_list
    
    def generate_breadcrumb(self, cookies, separator=" &raquo; "):
        """
        Generate the full html text for the bread crumb line for
        the page titled "title". All except the final entry are 
        links and have the css_class of "breadcrumb". The final entry,
        the current page, is simply the title and has the css class
        "breadcrumb_final" so that it can have unique formatting.
        The second argument, separator, can be used to define a different
        separator value. The default value is the most commonly used.
        """
        breadcrumb_text = ''
        breadcrumb_list = self.get_breadcrumb_list(cookies)
        breadcrumb_text = '<div class="breadcrumb print-hidden">'
        for i in range(len(breadcrumb_list)):
            if (i == len(breadcrumb_list)-1):
                # the current page -- do not add separator and url
                page_text = '%s</div>' %breadcrumb_list[i][1]
            else:
                page_text = '<a class="initial_breadcrumb print-hidden" href="/%s">%s</a>%s' \
                          %(breadcrumb_list[i][0], breadcrumb_list[i][1], separator)
            breadcrumb_text += page_text
        return breadcrumb_text

def generate_breadcrumb_line(cookies = None):
    """
    Create a full html breadcrumb line for the current_page from
    the site_description and page_title.
    """
    generator = BreadcrumbGenerator()
    return generator.generate_breadcrumb(cookies)

def return_error_page(error_string_suffix):
    error_string = "Sorry, you may not " + error_string_suffix
    return http.HttpResponseForbidden(error_string)

class ResultLogger:
    lines = []
    def add_line(self, result):
        self.lines.append(unicode(result))

    def clear_lines(self):
        self.lines = []

    def add_lines(self,additional_lines):
        self.lines.extend(additional_lines)

    def text(self):
        separator = unicode('<br/>')
        result = ""
        for line in self.lines:
            result = result + line + separator
        return result

class RequestError(exceptions.Exception):
    def __init__(self, args=None):
        self.response = http.HttpResponseBadRequest(args)
    
class ProhibitedError(exceptions.Exception):
    pass

class ProhibitedNoLoginError(ProhibitedError):
    def __init__(self, args=None):
        error_text = http.HttpResponseForbidden("<h1>You must be logged in to use the database.</h1>")
        self.response = http.HttpResponseForbidden(error_text)

class ProhibitedUserError(ProhibitedError):
    def __init__(self, args=None):
        template_name = "invaliduser.html"
        params = {}
        logging.warning("Unknown user: %s", args.email())
        params["account_name"] = args.email()
        params["database_name"] = "Philippines School Database"
        params["retry_url"] = users.create_logout_url("/")
        self.response = shortcuts.render_to_response(template_name, params)
        
class ProhibitedURLError(ProhibitedError):
    """
    The url was valid but access is prohibited to the user. Log attempt
    and raise django 404 error to return standard 404 error message. This
    hides the prohibited url from the user
    """
    def __init__(self, url):
        log_string = \
            "User: %s  Organization: %s Prohibited URL: '%s'." \
            %(SchoolDB.models.getActiveDatabaseUser().get_active_user_name(),
              SchoolDB.models.getActiveDatabaseUser().get_active_organization_name(), url)
        logging.warning(log_string)
        raise http.Http404
    
class ClassActionProhibitedError(ProhibitedError):
    """
    The requested action was not allowed on any instance of the class
    for the current user. Log prohibited request and send back an 
    error message with class name
    """
    def __init__(self, target_action, target_class, error_report_function):
        active_user = SchoolDB.models.getActiveDatabaseUser()
        log_string = \
            "User: %s  Organization: %s Prohibited action '%s' on class '%s'" \
            %(active_user.get_active_user_name(),
            active_user.get_active_organization_name(),
            target_action, target_class)
        #log(log_string)
        response_string_suffix = "%s on a %s." %(target_action, 
                                                 target_class)
        self.response = error_report_function(response_string_suffix)
        
class InstanceActionProhibitedError(ProhibitedError):
    """
    The requested action was prohibited on that specific instance. This
    may be caused by an instance not in the users organization or by
    some further restriction of access. The action was generally permitted on 
    objects of that class.
    """
    def __init__(self, args):
        target_action, error_report_function, target_class, \
                 target_object, reason = args
        active_user = SchoolDB.models.getActiveDatabaseUser()
        log_string = \
            "User: %s  Organization: %s Prohibited action: '%s' Instance: '%s' of class '%s'" \
            %(active_user.get_active_user_name(),
            active_user.get_active_organization_name(),
            target_action, unicode(target_object), 
            SchoolDB.models.get_model_class_from_name(target_class).classname)
        if reason:
            log_string += " Reason: '%s'" %reason
        #log(log_string)
        response_string_suffix = "%s '%s'" %(target_action, 
                                    unicode(target_object))
        if reason:
            response_string_suffix += " because %s." %reason
        self.response = error_report_function(response_string_suffix)
        
    
