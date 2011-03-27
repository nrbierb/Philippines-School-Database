#!/usr/bin/python2.5

import SchoolDB.models
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from datetime import date
import sys

"""
Low level maintenance actions such as deleting some database elements.
Use with care.
"""

def delete_student(logger, first_name = "None", last_name= "None", 
                   bdmonth = 0, bdday = 0, bdyear = 0):
    """
    Use the student class function "remove" to completely delete a student
    and all associated records. The tuple of first name, last name and
    birthdate should be sufficient for identification. Warn and do not
    delete if more than one found. Rname duplicate slightly to choose which
    to delete
    """
    if (first_name == "None"):
        logger.add_line("usage: delete_student first_name last_name birthday_month birthday_day birthday_year")
        return
    query = SchoolDB.models.Student.all()
    query.filter("first_name =", first_name)
    query.filter("last_name =", last_name)
    birthdate = date(bdyear, bdmonth, bdday)
    query.filter("birthdate = ", birthdate)
    target_list = query.fetch(10)
    if (len(target_list) == 1):
        target_list[0].remove()
        logger.add_line( "%s %s removed" %(first_name, last_name) )   
    elif (len(target_list) > 1):
        logger.add_line( "Too many matches: %d found." %len(target_list))
        return
    else:
        logger.add_line( "%s %s not found. BD month: %d  day: %d  year: %d" \
              %(first_name, last_name, bdmonth, bdday, bdyear))
        return
    