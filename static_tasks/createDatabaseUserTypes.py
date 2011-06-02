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
Create user permission data for user type entities which will be
loaded directly into the entity. This defines the user types directly
and progamatically --easer to do than build a form to set it. All user
types are defined here.
"""

import sys, os, logging
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')
from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()
from google.appengine.api import users
from google.appengine.ext import db
import SchoolDB.views
import SchoolDB.models

"""
Create user permission data for user type entities which will be
loaded directly into the entity. This defines the user types directly
and progamatically --easer to do than build a form to set it. All user
types are defined here.
"""

class UserPermissionsCreator():
    """
    Create a UserPermissions object from definitions. THis is used only once
    for each user type to initially store the information.
    """
    def __init__(self, url_default=True, class_default=0, ajax_default=True):
        self.url_permissions = {}
        self.url_permissions_default = url_default
        self.target_permissions = {}
        self.target_permissions_default = class_default
                
    def load_url_permission(self, url, permission):
        self.url_permissions[url] = permission
        
    def load_target_type_permissions(self, target_name, permissions, is_class):
        packed_permissions = SchoolDB.models.TargetTypePermission(permissions,
                                                                  is_class)
        self.target_permissions[target_name] = packed_permissions
            
    def load_urls(self, url_permissions):
        for url in url_permissions.iteritems():
            self.load_url_permission(url[0], url[1])
            
    def load_class_permissions(self,class_permissions):
        for target in class_permissions.iteritems():
            self.load_target_type_permissions(target[0],target[1], True)
            
    def load_function_permissions(self,function_permissions):
        for target in function_permissions.iteritems():
            self.load_target_type_permissions(target[0],target[1], False)
            
    def create_user_permissions_vault(self, permissions):
        self.url_permissions_default = permissions["default_url"]
        self.target_permissions_default = \
            permissions["default_target_permission"]
        self.load_urls(permissions["url_permissions"])
        self.load_class_permissions(permissions["class_permissions"])
        self.load_function_permissions(permissions["function_permissions"])
        permission_vault = SchoolDB.models.UserPermissionsVault(
            self.url_permissions_default, self.url_permissions,
            self.target_permissions_default, self.target_permissions)
        return permission_vault
        
       
#global shortcut definitions
no = (0,0)
yes = (0,1)
spec = (1,1)
delete = (yes, yes, yes)
edit = (no, yes, yes)
view = (no, no, yes)
nothing = (no,no,no)
delete_special = (spec,spec,spec)
edit_special = (no,spec,spec)
view_special = (no,no,spec)
standard_prohibited = (nothing, nothing)
standard_view = (nothing, view)
standard_edit = (nothing, edit)
standard_broad_view = (view, view)
standard_broad_edit = (edit, edit)
local_edit_broad_view = (view, edit)
standard_view_special = (nothing, view_special)
standard_edit_special = (nothing, edit_special)

# define a fuction like this for the user class and comment out the others

def build_teacher_permissions():
    #all other urls are true
    default_url = True
    urls = {'masterhome':False,
            'upperlevel_home':False,
            'adminhome':False,
            'schooladminhome':False,
            'upperlevel_adminhome':False,
            'schooladmin_maint':False,
            'othertypes':False,
            'otherwork':False,
            'database_user':False,
            'standard_database_user':False,
            'master_database_user':False,
            'user_type':False,
            'runtest':False,
            'utilrequest':False}
    
    default_target_permission = \
                        SchoolDB.models.TargetTypePermission(standard_view)
    default_target_permission.load_permissions(standard_view)
    class_permissions = {"administrator":standard_broad_view,
                         "assign_students":standard_edit,
                          "community":standard_broad_view,
                          "class_session":standard_edit,
                          "class_period":standard_view,
                          "classroom":standard_view,
                          "contact":standard_broad_view,
                          "standard_database_user":standard_prohibited,
                          "master_database_user":standard_prohibited,
                          "database_user":standard_prohibited,
                          "division":standard_broad_view,
                          "family":standard_edit,
                          "grading_instance":standard_edit,
                          "grading_period":standard_view,
                          "grading_period_results":standard_edit,
                          "municipality":standard_broad_view,
                          "organization":standard_broad_view,
                          "person":standard_view,
                          "parent_or_guardian":standard_edit,
                          "province":standard_broad_view,
                          "region":standard_broad_view, 
                          "school":standard_broad_view,
                          "school_day":standard_view,
                          "school_year":standard_view,
                          "section":standard_view, 
                          "section_type":standard_view, 
                          "special_designation":standard_view,
                          "student":standard_edit,
                          "student_status":standard_broad_view,
                          "subject":standard_broad_view,
                          "teacher":standard_edit,
                          "achievement_test_grades":standard_edit,
                          "achievement_test":standard_view,
                          "versioned_text_manager":standard_prohibited,
                          "user_type":standard_prohibited}
    
    function_permissions = {"attendance":standard_edit,
                              "enter_grades":standard_edit,
                              "my_work":standard_edit,
                              "school_report":standard_edit,
                              "report_student_age":standard_edit,
                              "report_attendance":standard_edit,
                              "report_section_list":standard_edit,
                              "report_school_register":standard_edit,
                              "report_student_record_check":standard_edit,
                              "create_user":standard_prohibited}    
    permissions = {"default_url":default_url,
        "url_permissions":urls, 
        "default_target_permission":default_target_permission,
        "class_permissions":class_permissions,
        "function_permissions":function_permissions}
    return (permissions)

def build_school_db_administrator_permissions():
    """
    An extension of the teachers permisssions to allow the further
    actions needed to support the school.
    """
    perms = build_teacher_permissions()
    url_changes = {"school_admin_home":True,
                   "othertypes":True,
                   #"otherwork":True,
                   "database_user":True,
                   "standard_database_user":True}
    class_permission_changes = {"adminstrator":local_edit_broad_view,
                "community":standard_broad_edit,
                "class_period":standard_edit,
                "classroom":standard_edit,
                "contact":standard_broad_edit,
                #"database_user":(edit_special,nothing,standard_edit),
                #The special edit function for only up to teacher must
                #be written and tested. For now, just give standard edit
                #permissions
                "standard_database_user":standard_edit,
                "database_user":standard_edit,
                "grading_period":standard_edit,
                "municipality":standard_broad_edit,
                "school":standard_edit,
                "school_day":standard_edit,
                "section":standard_edit,
                "subject":standard_edit}
    function_permission_changes = {"create_user":standard_edit}
    perms["url_permissions"].update(url_changes)
    perms["class_permissions"].update(class_permission_changes)
    perms["function_permissions"].update(function_permission_changes)
    return perms

#def build_student_permissions():
    #default_url = False;
    #urls = {"student_home":True,
                 #"select":True,
                 #"attendance":True,
                 #"enter_grades":True}
    #default_target_permission = standard_prohibited
    #class_permissions = {"grading_instance":standard_view,
                                 #"section":standard_view_special,
                                 #"class_session":standard_view_special,
                                 #"grading_instance":standard_view_special}
    #function_permissions = {"enter_grades":standard_edit_special,
                                          #"attendance":standard_edit_special}
    #permissions = {"default_url":default_url,
        #"url_permissions":urls, 
        #"default_target_permission":default_target_permission,
        #"class_permissions":class_permissions,
        #"function_permissions":function_permissions}
    #return permissions

def build_upper_level_permissions():
    default_url = True
    default_target_permission = \
            SchoolDB.models.TargetTypePermission(standard_broad_view)
    default_target_permission.load_permissions(standard_broad_view)
    urls = {'masterhome':False,
            "schoolhome":False,
            'schooladminhome':False,
            'upperlevel_adminhome':False,
            'schooladmin_maint':False,
            'upperlevel_adminhome':False,
            'othertypes':False,
            'otherwork':False,
            'database_user':False,
            'standard_database_user':False,
            'master_database_user':False,
            'user_type':False,
            'runtest':False,
            'utilrequest':False}
    class_permissions = {"administrator":standard_broad_view,
                          "community":standard_broad_view,
                          "class_session":standard_prohibited,
                          "class_period":standard_view,
                          "contact":standard_broad_view, 
                          "database_user":standard_prohibited,
                          "standard_databaser_user":standard_prohibited,
                          "master_database_user":standard_prohibited,
                          "division":standard_broad_view,
                          "family":standard_prohibited,
                          "grading_instance":standard_prohibited,
                          "grading_period":standard_view,
                          "municipality":standard_broad_view,
                          "organization":standard_broad_view,
                          "person":standard_view,
                          "parent_or_guardian":standard_prohibited,
                          "province":standard_broad_view,
                          "region":standard_broad_view, 
                          "school":standard_broad_view,
                          "school_day":standard_view,
                          "school_year":standard_broad_view,
                          "section":standard_prohibited, 
                          "section_type":standard_broad_view, 
                          "special_designation":standard_broad_view,
                          "student":standard_prohibited,
                          "student_status":standard_broad_view,
                          "subject":standard_broad_view,
                          "teacher":standard_broad_view,
                          "versioned_text_manager":standard_prohibited,
                          "user_type":standard_prohibited,
                          "student_summary":standard_edit}
    #fix this about student summary. Why class? Review permissions code.
    function_permissions = {"student_summary":standard_edit,
                            "report_achievement_test_summary":standard_edit}
    permissions = {"default_url":default_url,
        "url_permissions":urls, 
        "default_target_permission":default_target_permission,
        "class_permissions":class_permissions,
        "function_permissions":function_permissions}
    return (permissions)
    

"""
review permissions when time:
default url type
achievement test type
summary reports type
"""
def build_upper_level_admin_permissions():
    perms = build_upper_level_permissions()
    url_changes = {"upperlevel_adminhome":True,
                   "othertypes":True,
                   #"otherwork":True,
                   "database_user":True}
    class_permission_changes = {"adminstrator":local_edit_broad_view,
                                "achievement_test":standard_broad_edit,
                "community":standard_broad_edit,
                "class_period":standard_edit,
                "contact":standard_broad_edit,
                "database_user":(edit_special,nothing,standard_edit),
                "division":standard_edit,
                "region":standard_edit,
                "grading_period":standard_edit,
                "school_day":standard_edit,
                "school_year":standard_edit,
                "section_type":standard_edit,
                "special_designation":standard_edit,
                "student_status":standard_edit,
                "subject":standard_edit,
                "municipality":standard_broad_edit}
    default_target_permission = (view,edit)
    function_permission_changes = {"create_user":standard_edit}
    perms["url_permissions"].update(url_changes)
    perms["class_permissions"].update(class_permission_changes)
    perms["function_permissions"].update(function_permission_changes)
    return perms

def build_master_permissions():
    #Never really used because user validation is blocked for master
    #but in place for consistency
    #It gives permission for all actions
    default_url = True
    urls ={}
    default_target_permission = (delete,delete)
    class_permissions = {}
    function_permissions = {}
    permissions = {"default_url":default_url,
        "url_permissions":urls, 
        "default_target_permission":default_target_permission,
        "class_permissions":class_permissions,
        "function_permissions":function_permissions}
    return permissions

def create_user_type(name, home_page, permissions_function, maint_page, 
                     master_user=False):
    user_type = SchoolDB.models.UserType()
    user_type.master_user = master_user
    user_type.name = name
    user_type.home_page = home_page
    user_type.maint_page = maint_page
    permissions_creator = UserPermissionsCreator() 
    permission_params = permissions_function()
    user_type.active_permissions_vault = \
             permissions_creator.create_user_permissions_vault(permission_params)
    user_type.prepare_to_save()
    return user_type 

def create_upper_level_user_type():
    return create_user_type(name = "UpperLevelUser", 
        home_page = "upperlevel_home",
        maint_page = "upperlevel_maint",
        permissions_function = build_upper_level_permissions)

def create_upper_level_db_admin_type():
    return create_user_type(name = "UpperLevelDbAdministrator", 
        home_page = "upperlevel_adminhome",
        maint_page = "upperleveladmin_maint",
        permissions_function = build_upper_level_admin_permissions)
    
def create_teacher_user_type():
    user_type = SchoolDB.models.UserType()
    user_type.master_user = False
    user_type.name = "Teacher"
    user_type.home_page = "schoolhome"
    user_type.maint_page = "school_maint"
    permissions_creator = UserPermissionsCreator()    
    permission_params = build_teacher_permissions()
    user_type.active_permissions_vault = \
             permissions_creator.create_user_permissions_vault(permission_params)
    user_type.prepare_to_save()
    return user_type

def create_school_db_admin_user_type():
    user_type = SchoolDB.models.UserType()
    user_type.master_user = False
    user_type.name = "SchoolDbAdministrator"
    user_type.home_page = "schooladminhome"
    user_type.maint_page = "schooladmin_maint"
    permissions_creator = UserPermissionsCreator()    
    permission_params = build_school_db_administrator_permissions()
    user_type.active_permissions_vault = \
             permissions_creator.create_user_permissions_vault(permission_params)
    user_type.prepare_to_save()
    return user_type

def create_student_user_type():
    user_type = SchoolDB.models.UserType()
    user_type.master_user = False
    user_type.name = "Student"
    user_type.home_page = "studenthome"
    user_type.maint_page = "studenthome"
    permissions_creator = UserPermissionsCreator()    
    permission_params = build_student_permissions()
    user_type.active_permissions_vault = \
             permissions_creator.create_user_permissions_vault(permission_params)
    user_type.prepare_to_save()
    return user_type

def create_master_user_type():
    user_type = SchoolDB.models.UserType()
    user_type.master_user = True
    user_type.name = "Master"
    user_type.home_page = "adminhome"
    user_type.maint_page = "admin_maint"
    permissions_creator = UserPermissionsCreator()    
    permission_params = build_master_permissions()
    user_type.active_permissions_vault = \
             permissions_creator.create_user_permissions_vault(permission_params)
    user_type.prepare_to_save()
    return user_type

def build_user_types():
    """
    This function creates the user types for further manipulation but
    does not perform a "put" to save them.
    """
    types = {}
    types["Teacher"] = create_teacher_user_type()
    types["SchoolDbAdministrator"] = create_school_db_admin_user_type()
    #types["Student"] = create_student_user_type()
    types["UpperLevelUser"] = create_upper_level_user_type()
    types["UpperLevelDbAdministrator"] = create_upper_level_db_admin_type()
    types["Master"] = create_master_user_type()
    return types

def update_database_user_types(logger = None):
    """
    Perform the Update actions. For the database user types that are
    new add to database. For those that merely need the permissions to
    be updated get the current instance and replace the
    permissions_vault.
    """
    user_types = build_user_types()
    update_list = ("Teacher", "UpperLevelUser","UpperLevelDbAdministrator","SchoolDbAdministrator", "Master", None)
    for i in update_list:
        if i:
            user_type_instance = user_types[i]
            query = SchoolDB.models.UserType.all()
            query.filter("name =", i)
            dbUser = query.get()
            if dbUser:
                dbUser.permissions_vault = user_type_instance.permissions_vault
                dbUser.put()
            else:
                user_type_instance = user_types[i]
                user_type_instance.put()
    logging.info("Created %d user types", len(update_list))
                
if __name__ == '__main__':
    update_database_user_types()