# -*- coding: utf-8 -*-
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.conf.urls.defaults import *

urlpatterns = patterns('SchoolDB.views',
        (r'^index', 'showIndex'),
        (r'^masterhome', 'showIndex'),
        (r'^schoolhome', 'showIndex'),
        (r'^schooladminhome', 'showIndex'),
        (r'^upperlevel_home', 'showIndex'),
        (r'^upperlevel_adminhome', 
           'showIndex'),
        (r'^maint', 'showMaint'),
        (r'^othertypes', 'showMaint'),
        (r'^school_maint', 'showMaint'),
        (r'^schooladmin_maint', 'showMaint'),
        (r'^upperlevel_maint', 'showMaint'),
        (r'^upperleveladmin_maint', 'showMaint'),
        (r'^administrator', 'showAdministrator'),
        (r'^admin', 'showAdmin'),
        (r'^dynamic', 'showDynamic'),
        (r'^my_work', 'showMyWork'),
        (r'^choose_report', 'showChooseReport'),
        (r'^choose_custom_report', 
           'showChooseCustomReport'),
        (r'^custom_report', 'showDataBrowser'),
        (r'^choose_error_report', 'showChooseErrorReport'),
        (r'^choose_grading_type', 'showChooseGradingType'),
        (r'^choose','showChoose'),
        (r'^student_emergency', 'showStudentEmergency'),
        (r'^student_status', 'showStudentStatus'),
        (r'^student_major', 'showStudentMajor'),
        (r'^person', 'showPerson'),
        (r'^teacher', 'showTeacher'),
        (r'^student', 'showStudent'),
        (r'^select', 'showSelectDialog'),
        (r'^initialselect', 'showSelectDialog'),
        (r'^school_year', 'showSchoolYear'),
        (r'^calendar', 'showCalendar'),
        (r'^school_day_type', 'showSchoolDayType'),
        (r'^school_day', 'showSchoolDay'),
        (r'^grading_instance', 'showGradingInstance'),
        (r'^grading_period_results','showGradingPeriodResults'),
        (r'^achievement_test_grades', 'showAchievementTestGrades'),
        (r'^section_achievement_test_grades', 
         'showSectionAchievementTestGrades'),
        (r'^achievement_test', 'showAchievementTest'),
        (r'^grading_period', 'showGradingPeriod'),
        (r'^grading_event','showGradingEvent'),
        (r'^class_period', 'showClassPeriod'),
        (r'^school', 'showSchool'),
        (r'^organization', 'showOrganization'),
        (r'^region', 'showRegion'),
        (r'^contact','showContact'),
        (r'^classroom', 'showClassroom'),
        (r'^class_session', 'showClassSession'),
        (r'^subject', 'showSubject'),
        (r'^section_type', 'showSectionType'),
        (r'^section', 'showSection'),
        (r'^special_designation', 'showSpecialDesignation'),
        (r'^parent', 'showParentOrGuardian'),
        (r'^municipality', 'showMunicipality'),
        (r'^attendance', 'showAttendance'),
        (r'^province', 'showProvince'),
        (r'^community', 'showCommunity'),
        (r'^division', 'showDivision'),
        (r'^region','show Region'),
        (r'^assign_students','showAssignStudents'),
        (r'^otherwork', 'showOtherWork'),
        (r'^gradebook_entries_calendar', 
         'showGradebookEntriesCalendar'),
        (r'^grades', 'showGrades'),
        (r'^entergrades', 'showEnterGrades'),
        (r'^reports', 'showReports'),
        (r'^summary_student', 'showStudentSummary'),
        (r'^summary_at', 'showAchievementTestSummary'),
        (r'^my_choices', 'showMyChoices'),
        (r'^database_user', 'showDatabaseUser'),
        (r'^standard_database_user', 'showDatabaseUser'),
        (r'^master_database_user', 'showMasterDatabaseUser'),
        (r'^user_type', 'showUserType'),
        (r'^history', 'showHistory'),
        (r'^versioned_text_manager', 
         'showVersionedTextManager'),
        (r'^versioned_text', 'showVersionedText'),
        (r'^manual', 'showManual'),
        (r'^create_class_sessions', 
         'showCreateClassSessions'),                       
        (r'^ajax',  'processAjaxRequest'),
        (r'^generate_grades', 'showGenerateGrades'),
        (r'^runtest', 'showTest'),
        (r'^utilrequest', 'runUtil'),
        (r'^task', 'runTask'),
        (r'^$', 'showIndex'),
)
