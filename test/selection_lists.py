"""
Test the list generating functions
"""

import sys
import unittest
import itertools
from datetime import date, timedelta
sys.path.insert(1,'/home/master/SchoolsDatabase/phSchoolDB/')
from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()
from appengine_django.models import BaseModel
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from SchoolDB import choices, models, student_attendance, \
     assistant_classes
if __name__ == '__main__':
    province_list = models.Province.get_choice_list()
    province_key = province_list[0][0]
    div_list = models.Division.get_choice_list()
    div_key = div_list[1][0]
    municpality_list = models.Municipality.get_choice_list(
        leading_value = "co")
    municipality_key = municpality_list[0][0]
    barangay_list = models.Barangay.get_choice_list()
    barangay_list = models.Barangay.get_choice_list(
        municipality = municipality_key)
    barangay_list = models.Barangay.get_choice_list(
        municipality = municipality_key, 
                                    leading_value = "p")
    school_list = models.School.get_choice_list(division = div_key, 
                                leading_value = "C")
    school_key = school_list[0][0]
    section_list = models.Section.get_choice_list(school=school_key)
    section_list = models.Section.get_choice_list(school=school_key,
                                            leading_value = "zi")
    section_key = section_list[0][0]
    subject_list = models.Subject.get_choice_list()
    subject_list = models.Subject.get_choice_list(
        leading_value = "mat")
    class_list = models.ClassSession.get_choice_list(
        school=school_key)
    student_list = models.Student.get_choice_list(school=school_key)
    print len(student_list)
    student_list = models.Student.get_choice_list(school=school_key,
                                        section = section_key)
    print len(student_list)
    student_list = models.Student.get_choice_list(school=school_key,
                                        section = section_key,
                                        leading_value = "ca")
    print len(student_list)
    

