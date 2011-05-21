import SchoolDB.models
import SchoolDB.views
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from datetime import date, timedelta
def create_schooldays(logger, start_date, end_date, school_break = ""):
    """ 
    Create a block of SchoolDay instances with either the type
    schoolday for weekdays or weekend for weekend days. Takes two
    agruments, both inclusive: start_date, end_date. Both are in the
    format "mm/dd/yyyy". The defining organization is "national".
    Perform a query on the range first and do not create an instance
    for any day that already has "national" defined for it.
    """
    #get national org instance
    if ((not start_date) or (not end_date)):
        logger.add_line("Missing date(s) as parameters. Error: Quitting")
    start = SchoolDB.views.convert_form_date(start_date)
    end = SchoolDB.views.convert_form_date(end_date)
    national = SchoolDB.models.National.get_national_org()
    query = SchoolDB.models.SchoolDay.all()
    query.filter("date >=", start)
    query.filter("date <=", end)
    query.filter("organization =", national.key())
    existing = query.fetch(500)
    the_date = start
    one_day = timedelta(1)
    logger.add_line("Number preexisting: %d" %(len(existing)))
    schoolday_instances = []
    created_count = 0
    while (the_date <= end):
        if (len(existing) == 0) or (the_date != existing[0].date):
            if (the_date.weekday() < 5):
                if (school_break):
                    dtype = "Not In Session"
                else:
                    dtype = "School Day"
            else:
                dtype = "Weekend"
            new_record = SchoolDB.models.SchoolDay(
                name=the_date.strftime("%m/%d/%Y") + "-National DepEd", date=the_date,
                    organization=national, day_type=dtype)
            schoolday_instances.append(new_record)
            created_count += 1
        else:
            existing.pop(0)
        the_date += one_day
    db.put(schoolday_instances)
    logger.add_line("Number created: %d" %created_count)
    
