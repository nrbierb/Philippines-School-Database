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
Update the student summaries for all schools. This should be done nightly. 
Normally there will be little work because there will be little change.
"""

import os,sys,logging
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')
from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()
from google.appengine.api import users
from google.appengine.ext import db
import SchoolDB.views
import SchoolDB.models

def update_all_schools_summaries(force_update = False):
    """
    The standard scheduled action to update the school summaries which
    is performed nightly. Only the summaries which have been marked for
    updating will do anything unless force update is set True.
    """
    query = SchoolDB.models.School.all()
    for school in query:
        logging.info("Starting student summary update for %s" %unicode(school))
        school.update_student_summary(force_update)
        logging.info("Completed student summary update for %s" %unicode(school))
        
if __name__ == '__main__':
    logging.info("School Student Summaries: Starting forced update of all schools.")
    update_all_schools_summaries(True)
    logging.info("School Student Summaries:Completed all forced task initiations")