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
This file contains miscellaneous functions that are used in several files.
"""
from datetime import date, timedelta, time
import logging, re, operator
from google.appengine.ext import db
from google.appengine.api import memcache
from django.utils import simplejson
import SchoolDB.gviz_api

def make_table(table_description, table_data):
    """
    Create the ajax return value for a full table representation
    with the Google table.
    """
    data_table = SchoolDB.gviz_api.DataTable(table_description)
    data_table.LoadData(table_data)
    json_table = data_table.ToJSon()
    return json_table

def produce_table(table_description, table_data, key_list):
    """
    Combine an already jsonfied google data table and a key list into a
    single json string to be processed by javascript on the web page.
    """
    json_table = make_table(table_description, table_data)
    json_key_list = simplejson.dumps(key_list)
    json_combined = simplejson.dumps({"keysArray":json_key_list, 
                                      "tableDescriptor":json_table})
    return json_combined

def filter_by_date(query, before_or_after = "after", parameter = 
                   "student_status_change_date", delta_days = 0, 
                                        specified_date = None):
    """
    Add a filter to a query to add a date check. This does not
    perform a query, it just adds a computed filter statement to a
    query description. If delta days is 0 then the date is set to four
    weeks before the current school year so that the function can be
    easily used to filter for current students.
    """
    if (specified_date):
        compare_date = specified_date
    elif (delta_days == 0):
        current_year = SchoolDB.models.SchoolYear.school_year_for_date()
        if current_year:
            compare_date = current_year.start_date - timedelta(28)
        else:
            #no school year, just use today
            compare_date = date.today()
    else:
        compare_date = date.today() - timedelta(delta_days)
    if (before_or_after == "after"):
        match = parameter + " > "
    else:
        match = parameter + " < "
    query.filter(match, compare_date)
    return query

def clean_up_letter_casing(target_string):
    """
    Set capitalization appropriate for names. If both capital and
    lower case letters are present leave unchanged. Otherwise capitalize the 
    first letter of each word.
    """
    uppers = re.search(r'[A-Z]',target_string)
    lowers = re.search(r'[a-z]',target_string)
    if (not uppers or not lowers):
        new_string = target_string.title()
    else:
        new_string = target_string
    return new_string

def create_choice_array_from_query(query):
    """
    Use to create a list of tuples of key and instance name. This uses
    the memcache key only and name memcache. Query should be key only.
    """
    results = query.fetch(1000)
    choice_list = [(None, "--------")]
    for res in results:
        name = get_name(res)
        choice = (str(res), name)
        choice_list.append(choice)
    return choice_list

def create_choice_array_from_class(model_class, organization_key=None,
                        sort_field = 'name', extra_filter_tuples = None):
    """
    This creates the choice array from the model class with optional
    filtering by organization and perhaps some further query filter
    comparisons. It uses the the name memcache
    """
    query = model_class.all(keys_only=True)
    query.order(sort_field)
    if organization_key:
        query.filter('organization =', organization_key)
    if extra_filter_tuples:
        for filter_tuple in extra_filter_tuples:
            query.filter(filter_tuple[0], filter_tuple[1])
    return (create_choice_array_from_query(query))

def get_num_days_in_period(start_date, end_date):
    """
    Return a long that is the number of days in a period defined
    by the start_date and end_date. This count includes both days.
    """
    td_diff = end_date - start_date
    return (td_diff.days +1)

def compare_person_by_gender_name(p1, p2):
    """
    A compare function to be used in a sort of persons. The primary 
    is gender (male first), then last name, and finally first name.
    """
    #multiplier for gender is negative to invert order 
    #(male before female)
    try:
        compare = cmp(p1.gender,p2.gender) * (-20) + \
                cmp(p1.last_name,p2.last_name) * 10 + \
                cmp(p1.first_name,p2.first_name) * 5
        return (cmp(compare,0))
    except:
        return 1

def compare_class_session_by_time_and_name(c1, c2):
    """
    Compare a class by start_time and name. Used in a standard sort of 
    classes. This requires special handling if the start time is not set.
    """
    c1name = unicode(c1)
    c2name = unicode(c2)
    c1time = time(7,0)
    c2time = time(7,0)
    if c1.class_period :
        c1time = c1.class_period.start_time
    if c2.class_period :
        c2time = c2.class_period.start_time
    compare = cmp(c1time, c2time) *2 + cmp(c1name, c2name)
    return compare              
                  
def sort_table_contents_and_key(table_contents, key_list, compare_fields_list):
    """
    This is a generalized utility function for sorting a 2D table list
    and an associated key list. The key_list may be None or an empty
    list which will then be ignored. The compare fields list is a tuple
    of tuples (table field index, sort reverse) and is sorted with the
    last in the list as the most important. The return values are the
    sorted table and a list of keys sorted to retain their relationship
    with table rows.
    """
    key_list_len = 0
    if (key_list):
        key_list_len = len(key_list)
    table_contents_len = len(table_contents)
    keys_appended = (key_list_len == table_contents_len)
    if keys_appended:
        for i in xrange(0,table_contents_len):
            table_contents[i].append(key_list[i])
    sorted_table = table_contents
    for compare_info in compare_fields_list:
        sorted_table = sorted(sorted_table, 
                              key = operator.itemgetter(compare_info[0]), 
                              reverse = compare_info[1])
    #now split back into table and key_list
    sorted_key_list = []
    if (keys_appended):
        for table_row in sorted_table:
            sorted_key_list.append(table_row.pop())
    return(sorted_table, sorted_key_list)
     
def get_key_from_string(key_string):
    key = None
    if key_string :
        key = db.Key(key_string)
    return key

def get_key_from_instance(instance):
    """
    Trivial wrapper that prevents a exception if instance is None
    for those times that None is an acceptable value
    """
    if instance:
        return instance.key()
    else:
        return None

def get_key_list(key_string_list, object_class):
    """
    Get a list of keys for objects of a defined class from 
    a list of tuples which each have a key string as the first 
    list element
    """
    key_list = []
    if (key_string_list):
        for element in key_string_list:
            try:
                element_key_string = element[0]
                element_key = db.Key(element_key_string)
                if (element_key.kind() == object_class):
                    key_list.append(element_key)
            except db.BadKeyError:
                continue               
    return key_list

def get_key_name_list(instance_list, special_format_function=None, 
                      extras = None):
    """
    Generate a list of key_string, unicode(referenced_record) tuples 
    from a list of entities. This can then
    be used to generate the json text to use with the request answer.
    """
    pairs = []
    try:
        for instance in instance_list:
            key_string  = str(instance.key())
            if special_format_function :
                name = special_format_function(instance)
            else:
                name = unicode(instance)
            if (extras):
                pairs.append([key_string, name, extras])
            else:
                pairs.append([key_string, name])
    except:
        pairs=[]
    return pairs

def get_instance_from_key_string(key_string, instance_type = db.Model):
    """
    Try to find an instance from a string that should be a key. If
    found, check the instance class to confirm that it is actually an
    instance that is useable. Remember that the class is the base type
    if the class is a child class.
    """
    the_instance = None
    try:
        the_key = get_key_from_string(key_string)
        if (the_key):
            the_instance = instance_type.get(the_key)
    except db.BadKeyError, e:
        error_string = "failed to get correct instance from key " + str(e)
        the_instance = None
    return the_instance

def get_entities_by_name(class_name, search_name, key_only = False, 
                 single_only=True, organization=None, max_fetched=50):
    """
    Get entities of class class_name with the name search_name.
    If key_only return just the key(s). 
    If single_only return at most one result directly from a get,
    otherwise return a list as a result of a fetch.
    If organization specified filter by that organization
    """
    search_name = search_name.strip()
    query = class_name.all(keys_only=True)
    query.filter("name =", search_name)
    if organization:
        query.filter("organization =", organization)
    if single_only:
        keys = query.get()
    else:
        keys = query.fetch(max_fetched)
    if key_only:
        return keys
    else:
        return(db.get(keys))

def get_class_session_from_section_and_subject(section_name, 
                subject_name, organization_name = ""):
    """
    Return the class session for a section chosen by name with the
    subject chosen by name. If given, the named school will be used,
    if not, the users organization will be used.
    """
    if (not organization_name):
        school = \
            SchoolDB.models.getActiveDatabaseUser().get_active_organization()
    else:
        school = SchoolDB.utility_functions.get_entities_by_name(
            SchoolDB.models.School, organization_name)
    if not school:
        logging.info("No school named '%s' found." %organization_name)
        return None
    section_key = SchoolDB.utility_functions.get_entities_by_name(
        class_name=SchoolDB.models.Section, key_only= True,
        search_name = section_name, organization = school)
    if not section_key:
        logging.info("No section named '%s'" %section_name)
        return None
    subject_key = SchoolDB.utility_functions.get_entities_by_name(
        class_name=SchoolDB.models.Subject, search_name = subject_name,
        key_only = True)
    if not subject_key:
        logging.info("No subject named '%s'" %subject_name)
        return None
    query = SchoolDB.models.ClassSession.all(keys_only=True)
    query.filter("section = ", section_key)
    query.filter("subject = ", subject_key)
    key = query.get()
    if not key:
        logging.info("No class session found for section %s subject %s" \
                    %(section_name, subject_name))
    return db.get(key)

def get_schools_in_named_organization(organization_name = "", 
                                      use_default_org = True):
    """
    Get a list of all schools in the organization with the name
    organization name. If no organization name is given or it can't be
    found use the user's organization if use_default_org is true.
    """
    organization = None
    schools_list = []
    if (organization_name):
        organization = get_entities_by_name(SchoolDB.models.Organization,
                                            organization_name)
    if (not organization and use_default_org):
        organization = \
            SchoolDB.models.getActiveDatabaseUser().get_active_organization()
    if organization:
        schools_list = organization.get_schools()
    return schools_list
        
def get_blocks_from_iterative_query(query, blocksize):
    """
    Return a list of blocks (a list of max-size blocksize) of
    the result of an iterative query. This will return all results
    of the query.
    """
    blocks_list = []
    block = []
    #>>problem with cache software. Consider cursor instead for blocks
    for i in query:
        block.append(i)
        if (len(block) >= blocksize):
            blocks_list.append(block)
            block = []
    #Add remainder as final block. This also assures that the returned
    #structure is consistent even if there are no query results.
    blocks_list.append(block)
    return blocks_list
    
def filter_keystring(keystring):
    """
    Perform initial protective filtering on string. This doesn't
    mean that the key is valid, just that it is not too long and 
    contains only letters and numbers. It may return a truncated
    key or, if invalid characters are discovered no key at all.
    """
    if keystring:
        keystring = keystring[0:150]
        #leave commented until can find characters in keystring
        if re.search(r'(\W)', keystring):
            keystring = None
    return keystring

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

def get_fields_value(instance,field_name):
    """
    Return the value of the named field in the instance. If the field
    is a reference then return the unicode(instance). If not, just return
    unicode(field).
    """ 
    try:
        properties_dict = instance.properties()
        attribute = properties_dict[field_name]
        if isinstance(attribute, db.ReferenceProperty):
            key = attribute.get_value_for_datastore(instance)
            field_value = get_name(key)
        else:
            field_value = unicode(getattr(instance,field_name))
        return field_value
    except:
        return " "
    
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

def get_name(instance_key):
    """
    Get the text value from the named memcache "Names" associated with
    an etity key. This will normally be the name for the instance that is
    created with the entities "unicode" function
    """
    if instance_key:
        name = memcache.get(str(instance_key), namespace="Names")
        if name:
            #logging.info("Found '%s'" %name)
            return name
        else:
            instance = db.get(instance_key)
            if instance:
                name = unicode(instance)
                memcache.add(key=str(instance_key), value=name,
                             namespace="Names")
                logging.info("Added '%s'" %name)
                return name
    return ""
        
def name_is_in_model(instance, name):
    """
    Confirm that there is a model attribute of the instance by
    that name.
    """
    properties_dict = instance.properties()
    return properties_dict.has_key(name)


def get_keys_for_class(classname):
    """
    Return a list of keys for all entities of class classname.
    """
    model_class = SchoolDB.models.get_model_class_from_name(classname)
    query = model_class.all(keys_only=True)
    key_list = query.fetch(50000)
    return key_list 

def simple_remove(entity, perform_remove):
    """
    Delete the entity if perform_remove is True. Report deletion
    or, if perform remove is False delete emulation, via logging.
    """
    try:
        if perform_remove:
            entity.delete()
            #This is very expensive but is the only way to be absolutely
            #sure that there is no incorrect information in the cache
            #memcache.flush_all()
            text = "Removed %s %s" %(entity.classname, unicode(entity))
        else:
            text = "Simulated removal of %s %s" %(entity.classname, 
                                                  unicode(entity))
        logging.info(text)
    except StandardError, e:
        logging.error("Failed %s Error: %s" %(text, e))
        perform_remove = False
    return perform_remove
    
def cleanup_django_escaped_characters(s):
    """
    Django replaces some key characters in strings for safety. They must be reconverted befor the string can be used.
    """
    s = s.replace("%5B", "[")
    s = s.replace("%5D", "]")
    s = s.replace("%22", '"')
    s = s.replace("%2F", "/")
    s = s.replace("%2C", ",")
    return s