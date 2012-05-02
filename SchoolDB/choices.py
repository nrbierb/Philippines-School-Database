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
Global arrays of standard values for several multivalued parameters.
All are tuples to be used in the choice field definitions.
These may need some kind of update in the future...
The arrays are:
Student Class Year Name
Student Status
Teacher Paygrade
School Day Type
Municipality Class
"""
Gender = [
    "Female",
    "Male"]

Relationship = [
    "Mother",
    "Father",
    "Guardian"]

ContactOrder = [
    "First",
    "Next",
    "No Contact"
]

ClassYearNames = [
    "First Year",
    "Second Year",
    "Third Year",
    "Fourth Year",
    'None']

ClassLevel = [
    "Normal",
    "Advanced",
    "Remedial",
    "Other" ]

GradingInstanceType = [
    "Class Test",
    "Division Test",
    "Regional Test",
    "National Test",
    "Paper / Presentation",
    "Classroom Activity",
    "Outside Activity",
    "Classroom Participation",
    "Special Credit" ]

AchievementTestType = [
    "National Test",
    "Regional Test",
    "Division Test",
    "School Based"]
    
StudentClassStatus = [
    "Active",
    "Passed",
    "Failed",
    "Incomplete",
    "Dropped"]

AgeCalcType = [
    ("schoolyear", "At June"),
    ("endyear", "At March"),
    ("actual", "Actual")
    ]

TeacherPaygrade = [
    "Local Item",
    "Level One",
    "Level Two",
    "Level Three",
    "Master",
    "Master Teacher 1",
    "Master Teacher 2"]

SchoolDayType = [
    "School Day",
    "Weekend",
    "National Holiday",
    "Local Holiday",
    "Makeup Full Day",
    "Makeup Half Day Morning",
    "Makeup Half Day Afternoon",
    "Not In Session",
    "Break",
    "Start Year",
    "End Year",
    "Start Summer Session",
    "End Summer Session",
    "QuarterEnd",
    "Other Not Attend" ]

MunicipalityType = [
    "Fifth Class",
    "Fourth Class",
    "Third Class",
    "Second Class",
    "First Class",
    "City" ]

utility_function_choices = [
    "SchoolDB.local_utilities_functions.update_student_summary_utility",
    "SchoolDB.local_utilities_functions.update_section_initial_student_counts",
    "SchoolDB.local_utilities_functions.build_all_student_class_records",
    "SchoolDB.local_utilities_functions.count_student_class_records_task",
    "SchoolDB.local_utilities_functions.fix_student_class_record_count",
    "SchoolDB.local_utilities_functions.end_of_year_update_school",
    "SchoolDB.local_utilities_functions.start_of_year_update_school",
    "SchoolDB.local_utilities_functions.check_encoding_count",
    "SchoolDB.local_utilities_functions.find_duplicate_students",
    "SchoolDB.local_utilities_functions.create_new_attendance_records_utility",
    "SchoolDB.local_utilities_functions.create_fake_at_grades",
    "SchoolDB.local_utilities_functions.create_fake_gp_grades",
    "SchoolDB.local_utilities_functions.dump_student_info_to_email",
    "SchoolDB.local_utilities_functions.create_schooldays",
    "assign_student_majors_for_test_database",
    "create_students_for_school"]

def convert_to_form_choice_list(base_list):
	expanded_list = []
	for entry in base_list:
		expanded_entry = (entry,entry)
		expanded_list.append(expanded_entry)
	return expanded_list

#global constants
#organization codes
OrgTypeSchool = 1
OrgTypeDivision = 2
OrgTypeRegion = 3
OrgTypeBarangay = 4
OrgTypeMunicipality = 5
