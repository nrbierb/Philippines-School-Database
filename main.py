# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Bootstrap for running a Django app under Google App Engine.

The site-specific code is all in other files: settings.py, urls.py,
models.py, views.py.  And in fact, only 'settings' is referenced here
directly -- everything else is controlled from there.

"""

# Standard Python imports.
import os
import sys
import logging
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from google.appengine.dist import use_library
use_library('django', '1.2')

from appengine_django import InstallAppengineHelperForDjango
from appengine_django import have_django_zip
from appengine_django import django_zip_path
InstallAppengineHelperForDjango()

# Google App Engine imports.
from google.appengine.ext.webapp import util

# Import the part of Django that we use here.
import django.core.handlers.wsgi
#import the datastore caching code from 
#http://www.snippetin.com/snippet/view/memcaching-all-entities-for-google-app-engine-datastore
#import SchoolDB.datastore_cache
#SchoolDB.datastore_cache.DatastoreCachingShim.Install()
import SchoolDB.views
    
def main():
    # Ensure the Django zipfile is in the path if required.
    if have_django_zip and django_zip_path not in sys.path:
        sys.path.insert(1, django_zip_path)
  
    # Create a Django application for WSGI.
    application = django.core.handlers.wsgi.WSGIHandler()
  
    # Run the WSGI CGI handler with that application.
    util.run_wsgi_app(application)

#def main():
    ## This is the main function for profiling
    ## We've renamed our original main() above to real_main()
    #import cProfile, pstats, StringIO
    #prof = cProfile.Profile()
    #prof = prof.runctx("real_main()", globals(), locals())
    #stream = StringIO.StringIO()
    #stats = pstats.Stats(prof, stream=stream)
    #stats.sort_stats("time")  # Or cumulative
    #stats.print_stats(80)  # 80 = how many to print
    ## The rest is optional.
    ## stats.print_callees()
    ## stats.print_callers()
    #logging.info("Profile data:\n%s", stream.getvalue())    

if __name__ == '__main__':
    main()
