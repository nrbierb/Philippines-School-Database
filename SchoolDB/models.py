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
Primary file for the model portion of the database. Most of the
definition and core action of the models using the Goolgle appengine
database are here.
"""
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from google.appengine.api import users
from google.appengine.api import datastore_errors
from datetime import date, timedelta, datetime, time
import re 
import array, pickle, bz2, logging
import types, operator
import exceptions
import django.template
import SchoolDB.choices 
import SchoolDB.assistant_classes
import SchoolDB.reports
import SchoolDB.summaries
# The global object that represents the database user active for this 
# session

__activeDatabaseUser = None
__activeOrganization = None

class DateNotInStudentAttendanceRecord(exceptions.Exception):
    def __init__(self, args=None):
        self.args = args

"""
This file contains all of the database classes for the School Database.
"""

class HistoryEntry(db.Model):
    """
    The original class that used a separate database entry for each.
    This legacy code must remain until all old form databases
    have been converted
    """
    start_date = db.DateProperty() 
    end_date = db.DateProperty(date.max)
    info_string = db.StringProperty()
    info_reference = db.ReferenceProperty()

    def remove_reference(self):
        if (self.info_reference):
            db.delete(self.info_reference)

class HistEntry():
    """
    The basic entity of a history. The entry will represent an event,
    status, etc. that has a specific time to start and end. More than
    one entry in a list of entries can be active at the same time if 
    there is more than one which has an end date in the future.
    Each entry may contain either a string or a key to some other 
    entity as a description of the entry.
    """

    _empty_flag_string = "--------"

    def __init__(self, start_date, end_date = date.max, 
                 info_string = "", info_reference = ""):
        self.start_date = start_date
        self.end_date = end_date
        self.info_string = info_string
        self.set_info_reference(info_reference)

    def get_info_reference(self):
        """
        Convert from string to actual reference
        """
        if (self.info_reference_keystring):
            return (db.get(db.Key(self.info_reference_keystring)))
        else:
            return None

    def get_info_key(self):
        """
        Convert from string to the key
        """
        if (self.info_reference_keystring):
            return (db.Key(self.info_reference_keystring))
        else:
            return None
       
    def set_info_reference(self, info_reference=None):
        """
        Convert to string for store
        """
        if info_reference:
            try:
                self.info_reference_keystring = str(info_reference)
            except:
                self.info_reference_keystring= ""
        else:
            self.info_reference_keystring= ""

    def set_info(self, info_string="", info_reference=None):
        self.info_string = info_string
        self.set_info_reference(info_reference)

    def __unicode__(self):
        """
        For the common case the text information that should be
        returned will be contained in the "info_string". If there 
        is an info_key that will contain the correct unicode value
        so fetch it and use its unicode method. Then add information
        about the date
        """
        text = self._empty_flag_string
        if (self.info_string and (len(self.info_string) > 0)):
            text = self.info_string
        elif (self.info_reference_keystring):
            try:
                text = unicode(self.get_info_reference())
            except db.BadKeyError, err:
                db.errors['__all__'] = unicode(err)
        return text

    def get_end_date(self):
        """
        Return end date if valid one is set, else None
        """
        if (self.end_date != date.max):
            return self.end_date
        else:
            return None

    def set_end_date(self, end_date):
        self.end_date = end_date

    def set_start_date(self, start_date):
        self.start_date = start_date

    def get_string_tuple(self):
        start_date_string = format_date(self.start_date)
        if (self.end_date == date.max):
            end_date_string = ""
        else:
            end_date_string = format_date(self.end_date)
        return(unicode(self), start_date_string, end_date_string)

    def get_string_dict(self):
        value, start_date, end_date = self.get_string_tuple()
        return {"value":value, "start_date": start_date, "end_date":end_date}

    def get_full_string(self, show_end_date=False, field_size=20):
        str_tuple = self.get_string_tuple()
        value_string = "%-*s %s" %(field_size, str_tuple[0], str_tuple[1])
        if show_end_date :
            value_string = "%s  %s" %(value_string, str_tuple[2])
        return (value_string)

    def get_character_key_value(self):
        return str(self.key())

    def get_selection_list_entry(self, show_end_date=False, field_size=20):
        return (self.get_character_key_value(), 
                self.get_full_string(show_end_date, field_size))

    def remove_reference(self):
        if (self.info_reference_keystring):
            db.delete(self.get_info_reference())

    def same_info_reference(self, info_reference_key):
        """
        Compare key values
        """
        is_same = (not (info_reference_key or self.info_reference_keystring))
        if (info_reference_key and self.info_reference_keystring):
            try:
                is_same = (str(info_reference_key) == 
                           self.info_reference_keystring)
            except:
                is_same = False
        return is_same

    def compare(self, start_date, info_string, info_reference_key):
        """
        Compare the entry with the argument values. Return a tuple of 
        [value_changed (either info_string or info reference), date_changed]
        """
        if (info_string or self.info_string):
            string_value_changed = (info_string != self.info_string)
        else:
            string_value_changed = False        
        value_changed = (string_value_changed or 
                         not (self.same_info_reference(info_reference_key)))
        date_changed = (start_date != self.start_date)
        return (date_changed, value_changed)

    def same_values(self, info_string, info_reference):
        """
        Compare the entry with the argument values. Return true if
        entry has different info_string or if no info string a
        different reference.
        """
        return ((info_string == self.info_string) and
                         self.same_info_reference(info_reference))

    def is_active_at_date(self, test_date):
        """
        Return true if start date is earlier and end date is later than
        the test_date
        """
        return ((self.start_date <= test_date) and 
                (self.end_date >= test_date))
    
#----------------------------------------------------------------------  

class History(polymodel.PolyModel):
    """
    A major class used throughout the database to retain a historical
    record of values of a single parameter in a single entity. This
    record is stored in a blob to elminate the need for subordinate
    entities.
    """
    attribute_name = db.StringProperty(required=True)
    is_reference = db.BooleanProperty(default=False)
    is_private_reference_object = db.BooleanProperty(default=False)
    multi_active = db.BooleanProperty(default=False)
    history_entries_store = db.BlobProperty(default=None)
    full_references_list=db.ListProperty(db.Key)
    entries_list = []
    #unused legacy field from prior implementation
    history_list = db.ListProperty(db.Key)
    _empty_flag_string = "--------"

    @staticmethod
    def create(ownerref, attributename, isreference=False, 
               multiactive=False, isprivate_reference_object=False):
        """
        This is like the __init__ class method but is used becuse the appDB
        reserves all ""--" definitions for itself. 
        """
        history_obj = History(parent=ownerref, 
                              attribute_name = attributename, 
                              is_reference = isreference, 
                              is_private_reference_object=
                              isprivate_reference_object,
                              multi_active = multiactive)
        # assure that history_entries_store will always unpickle to a list
        history_obj.entries_list = []
        history_obj.put_history()
        return history_obj

    def load_list_if_needed(self):
        """
        Unpickle the entries_store to the entries_list if
        this has not already been done.
        """
        if (not self.history_entries_store):
            #this object is just being created so don't attempt to read
            #an empty string
            self.entries_list = []
        elif (not self.entries_list):
            self.entries_list = pickle.loads(self.history_entries_store)

    def put_history(self):
        """
        An extension of the standard db.put to repickle the entries_list
        and then perform the put
        """
        self.history_entries_store = pickle.dumps(self.entries_list)
        self.put()
    
    def add_reference(self, info_reference):
        """
        If this history uses references then add this to the list of
        references if it is not already there. The full_references_list
        keeps a list of all references that have been included in the
        history, not just the current ones. This allows a low cost scan
        for an entity that at one time was associated with the
        histories owner. Example: search for classes that teacher
        taught by scanning all histories from classes for thaose which
        have the teacher entitiy as a reference.
        """
        if (self.is_reference and info_reference):
            ref_key = info_reference
            if ref_key:
                if (self.full_references_list.count(ref_key) == 0):
                    self.full_references_list.append(ref_key)
                
    def add_entry(self, start_date, info_str, info_instance = None):
        """
        Add a new entry to the history list. The entry will normally be
        the most recent (start > all other entries) so it will be
        appended to the list. Then, if not multiactive, set the end time
        of the latest previous entry to the start time if the end time
        is not already set. The start date could be earlier than
        earlier data as an effort to add prior information to a record.
        If so, then insert in the appropriate place in the history. If
        the history is multiactive no end date need be set.
        """
        new_entry = HistEntry(start_date=start_date, end_date=date.max,
                            info_string=info_str, info_reference=info_instance)
        self.add_reference(info_instance)
        self.load_list_if_needed()
        if (len(self.entries_list) == 0):
            self.entries_list.append(new_entry)
        else:
            entry_entered = False
            for i in range(len(self.entries_list)):
                if ((not self.entries_list[i].start_date) or 
                    (start_date < self.entries_list[i].start_date)):
                    if not self.multi_active:
                        #If the earlier entry was not at the end of 
                        #the list (the most current), then this new
                        #entry already has an end date. This is the
                        #backfill case and is rare.
                        new_entry.set_end_date( 
                            self.entries_list[i].start_date)
                        if (i >0):
                            self.entries_list[i-1].set_end_date(
                                start_date)
                    self.entries_list.insert(i,new_entry)
                    entry_entered = True
                    break
            if (not entry_entered):
                #The common case -- this entry is the latest
                if (not self.multi_active):
                    #The previous latest should have its end date set if not
                    # it is not set already.
                    prior_entry = self.entries_list[len(self.entries_list)-1]
                    if (prior_entry.end_date > start_date):
                        prior_entry.set_end_date(start_date)
                self.entries_list.append(new_entry)
        self.put_history()

    def add_or_change_entry_if_changed(self, start_date=None, info_str="", 
                                       info_reference = None, end_date=None):
        """
        This is the standard call from an input form. The date and
        value is compared with the current entry. If different, then a
        new entry is added. If only the date has changed then the start
        date is changed in the current entry -- assume that the date
        has just been corrected. If multiactive add a new entry if
        there is no other of the same value or the entry with the same
        value has already ended and just change the end date or
        starting date as appropriate otherwise.
        All of these tests assure that a change action is idempotent.
        """
        current_entry = self.get_current_entry()
        if (not current_entry):
            self.add_entry(start_date, info_str, info_reference)
        else:
            if (not self.multi_active):
                date_changed, info_changed = current_entry.compare(start_date,
                                                    info_str, info_reference)
                if (date_changed):
                    if (info_changed):
                        #If the date and the info is changed then it is a
                        #new value
                        self.add_entry(start_date, info_str, info_reference)
                    else:
                        #if only the start date is changed then assume this
                        #is just a correction of the start date
                        self.change_start_date(current_entry, start_date)
                        self.put_history()
                elif (info_changed):
                    current_entry.set_info(info_str, info_reference)
                    #If only a single entry is allowed then assume the change
                    #in value is a correction so just change the value and do
                    #not create another entry
                    self.put_history()
            else:
                #This is multiple value.
                #Search for an entry with the same value and state. If
                #the entry does not have an end date and the action is
                #to add the event, then just change the start date. If
                #the entry already has an end date or does not exist
                #and the action is to set a start date then create a
                #new entry.
                entry = self.find_entry_with_value(info_str, info_reference)
                if (entry):
                    if start_date:
                        if (not entry.get_end_date()):
                            entry.set_start_date(start_date)
                        else:
                            #The previous has already ended. Add a new entry
                            self.add_entry(start_date, info_str, info_reference)
                    elif end_date:
                        entry.set_end_date(end_date)
                else:
                    #No prior entry of this value. Add a new entry.
                    self.add_entry(start_date, info_str, info_reference)
 
    def change_start_date(self, entry, new_date):
        """
        Changing the start date can be complex if this is not the first
        element of the history. The end date of the previous entry will
        be need to be moved back if the new date is earlier but may or
        may not need to be moved forward if the date is later. It is
        even more complicated if the new start date is earlier than the
        start date of the previous entry. For now, just change the date
        and extend the code later to handle the complexities.
        """
        index = self.entries_list.index(entry)
        if ((index != 0) and (not self.multi_active) and 
            (self.get_entry(index-1).end_date == entry.start_date)):
            #the previous entry was terminated by the change to the 
            #new one so adjust its end date
            self.get_entry(index-1).set_end_date(new_date)
        entry.set_start_date(new_date)

    def clean_up_entries(self):
        """
        Scan list and remove invalid entries which have either no value
        or no start date. This should occur very very rarely.
        """
        removed_entries = False
        self.load_list_if_needed()
        for i in range(len(self.entries_list)-1,-1,-1):
            #scan from back so can remove easily
            entry = self.entries_list[i]
            #remove invalid entries
            if (not entry.start_date):
                #invalid start date
                del self.entries_list[i]
                removed_entries = True
            elif (not self.get_entry_value(entry, key_only=True)):
                del self.entries_list[i]
                removed_entries = True
        if (removed_entries):
            #if changed, save changes.
            self.put_history()
    
    def get_active_entries(self):
        """
        Return a list of the history elements that have no valid end date -- i.e., they are still active. 
        """
        active_list = []
        today = date.today()
        self.load_list_if_needed()
        self.clean_up_entries()
        for entry in self.entries_list:
            if (entry.end_date and entry.end_date > today) :
                active_list.append(entry)
        return active_list

    def get_current_entry(self, return_multi=True):
        """
        Return the single entry which is active and has the latest start
        date. This is used in the common case where only the most recent 
        entry is currently active. In some cases, the history will be 
        "closed out" so that no entries are currently active. "None" will be
        returned in this case. If the history is multi_active and 
        return_multi is true then return a list of active entries
        """
        current_entry = None
        active_entries = self.get_active_entries()
        if (return_multi and self.multi_active):
            current_entry = active_entries
        else:
            for entry in active_entries:
                if (current_entry == None):
                    current_entry = entry
                elif (entry.start_date > current_entry.start_date):
                    current_entry = entry
        return current_entry

    def get_entry_value(self, entry, key_only=False):
        if (self.is_reference):
            if (key_only):
                value = entry.get_info_key()
            else:
                value = entry.get_info_reference()
        else:
            value = entry.info_string
        return value
        
    def get_current_entry_value_and_date(self, key_only=False, 
                                         return_multi=True):
        current_entry = self.get_current_entry(return_multi)
        if (current_entry):
            if (type(current_entry) == types.ListType):
                value = [self.get_entry_value(entry, key_only) for
                         entry in current_entry]
                entry_date = [entry.start_date for
                              entry in current_entry]
            else:
                value = self.get_entry_value(current_entry, key_only)
                entry_date = current_entry.start_date
        else:
            #no record -- nothing yet added return null for record
            #current date for date
            value = None
            entry_date = date.today()
        return(value, entry_date)

    def get_entry(self, index):
        """
        Return None if index is off the end of the list
        """
        if (len(self.entries_list) <= index):
            return None
        else:
            return self.entries_list[index]

    def find_entry_with_value(self, info_str, info_reference):
        """
        Search for the most recent entry with the same value.
        """
        #Reverse list to search from most recent backwards in time.
        entry = None
        self.entries_list.reverse()
        for e in self.entries_list:
            if e.same_values(info_str, info_reference):
                entry = e
                break
        self.entries_list.reverse()
        return entry
    
    def entry_count(self):
        return len(self.entries_list)
    
    def is_empty(self):
        return (self.entry_count() == 0)

    def adjust_date(self, changed_entry, new_start_date, new_end_date = None):
        pass

    def get_intervening_changes(self, start_date, end_date):
        """
        Return a list of entries dated between the start date and the end date.
        """
        start_list = []
        end_list = []
        self.load_list_if_needed()
        for entry in self.entries_list:
            if ((entry.start_date >= start_date) and 
                (entry.start_date <= end_date)):
                start_list.append(entry)
            elif ((entry.end_date >= start_date) and 
                  (entry.end_date <= end_date)):
                end_list.append(entry)
        return (start_list, end_list)

    def get_value_at_date(self, test_date):
        """
        Return the value that was active at the check date. The caller
        will generally know if the history is single or multivalue and
        if it is a reference. To assure no confusion the tuple (result,
        is_reference, is_list) is returned. Either none or an empty list
        will be returned if there is no entry that spans that date.
        """
        if (self.multi_active):
            values = []
        value = None
        start_dates = []
        self.load_list_if_needed()
        for entry in self.entries_list:
            if entry.is_active_at_date(test_date):
                value = self.get_entry_value()
                start_date = entry.start_date
                if not self.multi_active:
                    return_value = value
                    break
                else:
                    values.append(value)
                    start_dates.append(start_date)
        if self.multi_active:
            #return two lists instead of single values
            return_value = values
            start_date = start_dates
        return (return_value, start_date, self.is_reference, self.multi_active)
    
    def get_value_at_end_of_school_year(self, ref_date=None, 
                            period_start_date=None, period_end_date=None):
        """
        Return the tuple value_at_end_of year and boolean changed
        during year. If current class year return current value. The
        return values will be single values if history is not
        multi_active or parallel lists if multi_active. Either the
        reference date (a date in the school year of interest) or the
        test_period start_date and end_date must be given. Using the
        reference date will require two queries. If this will be used
        more than once in an action then the period start data and tend
        date should be calculated externally and passed as arguments.
        """
        if (not (period_start_date and period_end_date)):
            period_start_date, period_end_date = \
                    SchoolYear.school_year_start_and_end_dates(ref_date, True)
        if (period_end_date >= date.today()):
            value, start_date = self.get_current_entry_value_and_date(
            key_only=False, return_multi=True)
        else:
            (value, start_date, is_reference, is_multi_active) = \
             self.get_value_at_date(period_end_date)
        if (type(value) == types.ListType):
            changed_during_year = \
                [(st_date >= period_start_date) for st_date in start_date]
        else:
            changed_during_year = (start_date >= period_start_date)
        return value, changed_during_year
                                           
    #********************* History Utility Actions ******************
    #The following numerous methods provide externally simple means for
    #for viewing the history in a variety of text, list, and selection 
    #list forms for use in web pages and reports

    def __unicode__(self):
        """
        Return the text value in the obtained from the "current"
        history entry. If there are no current entries then return flag string.
        """
        info_string = self._empty_flag_string
        current_entry = self.get_current_entry()
        if current_entry:
            info_string = unicode(current_entry)
        return info_string

    def get_dated_single_string(self, field_size=20):
        """
        Like the "__unicode__" version but with the start date.
        """
        dated_single_string = self._empty_flag_string
        current_entry = self.get_current_entry()
        if current_entry:
            dated_single_string = \
                        current_entry.get_full_string(False, field_size)
        return dated_single_string

    def get_active_string(self):
        """
        Create a single line comma separated string of all of the active
        entries.
        """ 
        active_string = self._empty_flag_string
        actives = self.get_active_entries()
        if (len(actives) > 0):
            active_string = unicode(actives[0])
            for entry in actives[1:]:
                active_string = active_string + ", " + unicode(entry)
        return active_string

    def get_entries_list(self, actives_only=False):
        self.load_list_if_needed()
        if actives_only:
            entries_list = self.get_active_entries()
        else:
            entries_list = self.entries_list
        return entries_list

    def get_entries_tuples_list(self, actives_only=False):
        """
        Create a list of the entries with each a three part tuple of 
        the strings.
        """
        entries_tuples_list = []
        for entry in self.get_entries_list(actives_only):
            entries_tuples_list.append(entry.get_string_tuple())
        return entries_tuples_list

    def get_entries_dict_list(self, actives_only=False):
        entries_dict_list = []
        for entry in self.get_entries_list(actives_only):
            entries_dict_list.append(entry.get_string_dict())
        return entries_dict_list

    def get_entries_choice_list(self, actives_only=False, show_end_date=False,
                                field_size=20):
        """
        Create a list of key, entry string value tuples ready for use in
        a form ChoiceField.
        """
        entries_choice_list = []
        for entry in self.get_entries_list(actives_only):
            entries_choice_list.append(entry.get_selection_list_entry(
                show_end_date, field_size))
        return entries_choice_list

    def remove(self):
        """
        Clean up all history elements in this history.
        Then delete self. This will provide a clean deletion of the 
        history.
        """  
        if (self.is_private_reference_object):
            for entry in self.entries_list:
                entry.remove_reference()
        self.delete()

#----------------------------------------------------------------------
class Organization(polymodel.PolyModel):
    """
    A abstract base class that contains all common information for
    all organizations. Never directly created.
    """
    last_edit_time = db.DateTimeProperty(auto_now=True)
    last_editor = db.ReferenceProperty()
    name = db.StringProperty(required=True)
    general_info = db.StringProperty(required=False, multiline=True)
    address = db.StringProperty(required=False, multiline=True)
    location = db.GeoPtProperty(required=False)
    postal_address = db.StringProperty(required=False)
    inactive = db.BooleanProperty()
    inactive_date = db.DateProperty()
    custom_query_function = False
    classname = "Organization"

    def post_creation(self):
        """
        A default action that does nothing
        """
        pass

    def form_data_post_processing(self):
        """
        Perform actions that modify data in the model other than the
        form fields. All of the data from the form has already been
        loaded into the model ' instance so this processing does not
        need the form at all. For this class this is just a default
        funcion that does nothing.
        """
        pass

    def __unicode__(self):
        return self.name

    @staticmethod    
    def get_contacts_list(organization, fields):
        """
        Create a list of all contacts in the organization.
        The list includes the db key for the contact, the 
        position, and persons name, and the phone number
        """
        query_descriptor = SchoolDB.assistant_classes.QueryDescriptor()
        query_descriptor.set("filter_by_organization",False)
        query_descriptor.set("ancestor_filter_value",str(organization.key()))
        query_descriptor.set("sort_order",["name"])
        query =  SchoolDB.assistant_classes.QueryMaker(Contact, query_descriptor)
        return query.get_keys_and_names(extra_fields = fields)

    def in_organization(self, organization_key, requested_action):
        return (self.key() == organization_key)

    def get_subordinate_organizations(self, active_only = True, 
                                      next_level_only=False):
        """
        Return a list of organzations that are a part of this
        organization, ex. a school for a division. This is just a base
        class fill function -- return an empty list.
        """
        subordinate_dict = {}
        subordinate_dict["-"] = []
        return subordinate_dict
    
    def build_subordinate_dict(self, subordinate_class, filter_name,
                               next_level_only):
        """
        Build a dictionary of subordinate organizations. If there is
        only one level then the dict will have a single entry with the
        key "-" an the list of subordinates. If there is a second level
        then the dict will have keys for each of the direct
        subordinates and with lists of the secondary subordinates
        """
        query = subordinate_class.all()
        filter_string = filter_name + " ="
        query.filter(filter_string, self)
        #comment out for now -- seems to have some problem...
        #if active_only:
            #query.filter("inactive =", False)
        subordinates = query.fetch(500)
        subordinate_dict={}
        if not next_level_only or self.lowest_level_org():
            for subordinate in subordinates:
                second_level_dict = \
                     subordinate.get_subordinate_organizations(
                        active_only=False, 
                        next_level_only=next_level_only)
                second_level_org_list = second_level_dict["-"]
                subordinate_dict[subordinate] = second_level_org_list
        else:
            subordinate_dict["-"] = subordinates               
        return subordinate_dict

    def get_subordinate_organizations_list(self, active_only = True, 
                                      next_level_only=False,
                                      bottom_level_only=False):
        """
        Use get_subordinate_organizations to create the possibly multi level
        dict and then flatten it to a simple list of organizations. If
        bottom_level_only true then do not include the mid level
        organizations in the list
        """
        sub_dict = self.get_subordinate_organizations(active_only,
                                                      next_level_only)
        if sub_dict.has_key('-'):
            #There is only a single level, just return the contained list
            return sub_dict['-']
        else:
            #Multiple levels, flatten. This is non recursive because only 2 
            #levels exist
            if bottom_level_only:
                subordinate_list = []
            else:
                subordinate_list = sub_dict.keys()
            for low_level_list in sub_dict.values():
                subordinate_list.extend(low_level_list)

    def get_subordinate_organizations_choice_list(self, 
                    active_only = True, next_level_only=False,
                    extended_name = True):
        """
        Return a list of tuples (org keystring, org name). This is used
        in almost all upper level reports to allow a choice of
        subordinate organizations for a restricted report. If
        extended_name is true and there are two levels in the list then
        prepend the next level org name to each line of the lower
        entry.
        """
        subordinate_dict = self.get_subordinate_organizations( 
            active_only = active_only, next_level_only=next_level_only)
        choices = []
        for upper_org in subordinate_dict.keys():
            if (upper_org != "-"):
                upper_org_name = unicode(upper_org)
            else:
                upper_org_name = ""
            for org in subordinate_dict[upper_org]:
                org_name = unicode(org)
                if (upper_org_name and extended_name):
                    org_name = upper_org_name + "-" + org_name
                choices.append((str(org.key()), org_name))
        return choices
    
    def get_schools(self):
        """
        Return a list of all schools under this organization.
        """
        return []
    
    def visible_organization(self):
        """
        Compare users organization with this to confirm that this is
        either the same or a subordinate organization.
        """
        user_org = \
            SchoolDB.models.getActiveDatabaseUser().get_active_organization_key()
        if (user_org == self.key()):
            return True
        else:
            sub_orgs = self.get_subordinate_organizations_list()
            return (sub_orgs.count(user_org) > 0)

    def lowest_level_org(self):
        """
        True if there are no further subordinate organizations.
        These orgs are School and Community
        """
        return False
    
    @staticmethod
    def get_field_names():
        field_names = [("general_info", "General Information"),
                       ("address", "Address")]
        return field_names

    def remove(self):
        self.delete()

#----------------------------------------------------------------------
class Contact(db.Model):
    """
    Contact is a general class that represents a person or office 
    that may be contacted for some purpose. A list of contacts is
    a part of each organizational unit class. Only the name is required but at 
    least one of the other fields should have some information to make it 
    the contact info useful.
    The parameters are:
    name - either the name of the office or person. Normally this should be
                 the name of the office and then the persons name is noted in 
                 the general info
    telephone - phone number
    fax - phone number
    email - email address
    general_info - free form text for further information
    A contact is permanently associated with an organization by the 
    "parent, child" database relationship.
    """
    name = db.StringProperty(required=True)
    person = db.StringProperty()
    telephone = db.StringProperty()
    fax = db.StringProperty()
    email = db.StringProperty()
    general_info = db.StringProperty(multiline=True)
    custom_query_function = False
    classname = "Contact"

    @staticmethod
    def create(name, organization):
        return Contact(name = name, parent = organization)

    def post_creation(self):
        """
        A default action that does nothing
        """
        pass

    def form_data_post_processing(self):
        """
        Perform actions that modify data in the model other than the form fields.
        All of the data from the form has already been loaded into the model '
        instance so this processing does not need the form at all.
        For this class this is jut a default function that does nothing.
        """
        pass

    def __unicode__(self):
        return self.name

    def in_organization(self, organization_key, requested_action):
        return (self.parent == organization_key)

    def remove(self):
        self.delete()

#----------------------------------------------------------------------
class National(Organization):
    """
    National Deped. Only one of these created initially.
    """

    classname = "National DepEd"

    def __unicode__(self):
        return self.name

    @staticmethod
    def get_national_org():
        qry = National.all()
        national = qry.get()
        if (not national):
            # the object hasn't been created yet (this happens only once!)
            national = National(name = "National")
            national.put()
        return national

    def get_subordinate_organizations(self, active_only=True, 
                                      next_level_only=True):
        """
        All DepEd organizations are subordinate. This has 3 levels of
        organization underneath which is not supported by code so this
        should be called with next_level_only set to true. Actually, a
        better solution would simple be to query upon the classtype.
        """
        subordinates = []
        query = Region.all()
        if active_only:
            query.filter("inactive =", False)
        regions = query.fetch(100)
        subordinates = regions
        if not next_level_only:
            for region in regions:
                subordinates.append(
                    region.get_subordinate_organizations(active_only))
        return subordinates

#----------------------------------------------------------------------
class Region(Organization):
    """
    The DepEd Region. This has no explicit reference to a containing
    organization because National is implicit. The additiaional field
    area_name is used in fields that include a further description
    beyond the region name itself.
    """

    area_name = db.StringProperty()
    classname = "DepEd Region"

    def __unicode__(self):
        return self.name

    def full_name(self):
        if self.area_name:
            return self.name + ", " + self.area_name
        else:
            return self.name
        
    def get_subordinate_organizations(self, active_only = True, 
                                      next_level_only=False):
        """
        Return a list of divisions and schools that are in this region.
        """
        subordinate_class = Division
        filter_name = "region"
        return self.build_subordinate_dict(subordinate_class, filter_name,
                                           next_level_only)

    def get_schools(self):
        """
        Get all schools in the region. This is a second level organization
        so the schools in every division will need to be aggregated.
        """
        subordinate_dict = self.get_subordinate_organizations()
        schools = []
        for division in subordinate_dict.values():
            schools.extend(division.values())
        return schools

#----------------------------------------------------------------------
class Province(Organization):
    """
    A top level governmental organization. This contains a reference to
    the DepEd region that its schools are in. This is an associative
    rather than a heirarchical relationship.
    """ 

    classname = "Province"
    region = db.ReferenceProperty(Region)

    def __unicode__(self):
        return self.name

    def get_subordinate_organizations(self, active_only = True, 
                                      next_level_only=False):
        """
        Return a list of municipalities and barangays that are in this province.
        """
        subordinate_class = Municipality
        filter_name = "province"
        return self.build_subordinate_dict(subordinate_class, filter_name,
                                           next_level_only)
    

#----------------------------------------------------------------------
class Division(Organization):
    """
    The DepEd division. It contains a refernce to the region that it is
    in and the province. The region is a heirarchical relationship, the
    province merely an associative.
    """
    classname = "DepEd Division"
    region = db.ReferenceProperty(Region)
    province = db.ReferenceProperty(Province)

    @staticmethod
    def get_field_names():
        field_names = Organization.get_field_names()
        field_names.extend([("region", "Region"), 
                            ("province", "Province")])
        return field_names

    def get_subordinate_organizations(self, active_only = True, 
                                      next_level_only=True):
        """
        Return a list of schools that are in this division.
        """
        subordinate_class = School
        filter_name = "division"
        return self.build_subordinate_dict(subordinate_class, filter_name,
                                           True)  
    def get_schools(self):
        """
        Get all schools in the division. This is a first level org so
        all schools are at the first level of the subordinate dict.
        """
        subordinate_dict = self.get_subordinate_organizations()
        return subordinate_dict.values()
    
    def get_municipalities(self):
        """
        Return a list of municipalities in this division
        """
        query = Municipality.all()
        query.filter("division =", self)
        return query.fetch(500)
    
#----------------------------------------------------------------------
class Municipality(Organization):
    province = db.ReferenceProperty(Province)
    division = db.ReferenceProperty(Division)
    type = db.StringProperty(choices = SchoolDB.choices.MunicipalityType)
    id = db.StringProperty()
    custom_query_function = True
    classname = "Municipality"

    @staticmethod
    def remove(municipality):
        fully_delete_entity(municipality, [Community])

    @staticmethod
    def custom_query(query_descriptor):
        """
        Return a list of municipality names from the active organization
        which should be a school
        """
        school = getActiveDatabaseUser().get_active_organization()
        try:
            object_list = school.students_municipalities
        except:
            object_list = []
        return object_list    

    @staticmethod
    def get_field_names():
        field_names = Organization.get_field_names()
        field_names.extend([("province", "Province"), 
                            ("division", "Divivision")])
        return field_names

    def get_subordinate_organizations(self, active_only = True, 
                                      next_level_only=False):
        """
        Return a list of barangays in this municipality.
        """
        subordinate_class = Community
        filter_name = "municipality"
        return self.build_subordinate_dict(subordinate_class, filter_name,
                                           next_level_only)
    
    def get_schools_in_municipality(self, active_only=True):
        """
        Return a list of schools located in this municipality
        """
        query = School.all()
        query.filter("municipality =", self)
        if active_only:
            query.filter("inactive =", False)
        return(query.fetch(100))
    
#----------------------------------------------------------------------
class Community(Organization):
    """
    A generic name for the lowest level of local government. In the
    Philippines this is the barangay.
    """
    municipality = db.ReferenceProperty(Municipality)
    custom_query_function = False
    #note: this is Philippines specific for display.
    classname = "Barangay"

    def lowest_level_org(self):
        """
        Communities are the lowest level civic org.
        """
        return True

    @staticmethod
    def create(name, municipality):
        return (Community(municipality=municipality, name=name,
                          parent=municipality))

    
#----------------------------------------------------------------------

class StudentStatus(db.Model):
    """
    A simple class that dfines a name and some other properties for the
    status of a student. Note that this is not a multilevel and can be
    edited only by the master user. This must be strict for consistency
    at all levels of DepEd organization.
    """
    name = db.StringProperty(required=True)
    active_student = db.BooleanProperty(default=False)
    default_choice = db.BooleanProperty(default=False)
    other_information = db.StringProperty(multiline=True)
    custom_query_function = False
    classname = "Student Status"

    @staticmethod
    def create(name):
        return StudentStatus(name=name)

    def __unicode__(self):
        return self.name

    def post_creation(self):
        pass

    def form_data_post_processing(self):
        pass

    def in_organization(self, organization_key, requested_action):
        """
        Status can be seen by anyone but only edited by the master user
        """
        return (requested_action == "View")

    def remove(self):
        self.delete()

#----------------------------------------------------------------------

class SchoolDayType(db.Model):
    """
    The type of a school day such as normal day, half day, holiday,
    etc. This associates a name with poteneital attendance parameters.
    It is editable only by the master user.
    """
    name = db.StringProperty(required=True)
    active_morning = db.BooleanProperty(default=False)
    active_afternoon = db.BooleanProperty(default=False)
    default_choice = db.BooleanProperty(default=False)
    other_information = db.StringProperty(multiline=True)
    custom_query_function = False
    classname = "School Day Type"

    @staticmethod
    def create(name):
        return SchoolDayType(name=name)

    def __unicode__(self):
        return self.name

    def post_creation(self):
        pass

    def form_data_post_processing(self):
        pass

    def in_organization(self, organization_key, requested_action):
        """
        Status can be seen by anyone but only edited by the master user
        """
        return (requested_action == "View")

    def remove(self):
        self.delete()

#----------------------------------------------------------------------

class MultiLevelDefined(polymodel.PolyModel):
    """
    The base class for many different classes. This class allows an
    entity with the same name to be redefined at multiple
    organizational heirarchy levels. The definition that is the most
    specific for an organization is used for that organiztion. FOr
    example, an entity with the same name is defined for National,
    region, and school. For the specific school the school definition
    will be used. For other schools in the region the region definition
    will be used. For schools in other regions the national definition
    will be used.
    """
    last_edit_time = db.DateTimeProperty(auto_now=True)
    last_editor = db.ReferenceProperty()
    name = db.StringProperty(required=True)
    organization = db.ReferenceProperty(Organization, 
                                        collection_name="multilevel_orgs")
    other_information = db.StringProperty(multiline=True)
    custom_query_function = True
    classname = "MultiLevel"

    @staticmethod
    def create(name, organization):
        return MultiLevelDefined(name=name, 
                                 parent=organization)
    def __unicode__(self):
        return self.name

    def post_creation(self):
        pass

    def form_data_post_processing(self):
        pass

    @staticmethod
    def build_hierarchy_keylist(organization):
        """
        Construct a list of keys from the National level on down as far
        as the the organization.
        """
        keylist = [National.get_national_org().key()]
        if (organization.classname == "DepEd Region"):
            keylist.append(organization.key())
        elif (organization.classname == "DepEd Divison"):
            keylist.extend([organization.region.key(), organization.key()])
        elif (organization.classname == "School"):
            keylist.extend([organization.division.region.key(), 
                            organization.division.key(),
                            organization.key()])
        return keylist

    @staticmethod
    def create_org_choice_list(organization):
        """
        Create a list of tuples (org_key, org_name) in inverse
        heirarchical order for use in gui choices
        """
        keylist = MultiLevelDefined.build_hierarchy_keylist(organization)
        keylist.reverse()
        choices = []
        for key in keylist:
            choices.append([key, unicode(Organization.get(key))])
        return choices

    def in_organization(self, organization_key, requested_action):
        """
        The definition for "in_organization" is different for View
        than for the other actions. An instance can only be edited
        by a user in that particular organization. An instance can
        be viewed if it is in any containing organization.
        """
        if (requested_action != "View"):
            return (self.organization.key() == organization_key)
        else:
            keylist = MultiLevelDefined.build_hierarchy_keylist(
                db.get(organization_key))
            for org_key in (keylist):
                if (org_key == self.organization.key()):
                    return True
            return False

    @staticmethod
    def merge_lists(mergelist, addlist, sort_field = "name"):
        if (len(mergelist) == 0):
            #the initial condition
            newlist = addlist
        elif (len(addlist) == 0):
            #a common case where the addlist is empty
            newlist = mergelist 
        else:
            newlist = []
            while ((len(mergelist) > 0) and (len(addlist) > 0)):
                if (mergelist[0].name < addlist[0].name):
                    #The most common case where there is a member
                    #of the merge list ready to add
                    merge_obj = mergelist.pop(0)
                    newlist.append(merge_obj)
                    continue
                if (mergelist[0].name == addlist[0].name):
                    #There is an object in both lists that have the
                    #same name. Add the higher priorty addlist one to
                    # the results list
                    merge_obj = mergelist.pop(0)
                    add_obj = addlist.pop(0)
                    newlist.append(add_obj)
                    continue
                if (mergelist[0].name > addlist[0].name):
                    #The object in the add list needs to be added 
                    add_obj = addlist.pop(0)
                    newlist.append(add_obj)
            #now add anything left in either of the lists to the end
            if (len(mergelist) > 0):
                newlist.extend(mergelist)
            elif (len(addlist) > 0):
                newlist.extend(addlist)              
        return newlist

    @staticmethod
    def custom_query(query_descriptor, target_class, sort_function = None):
        """
        Create the choice list in a special manner. The list will
        contain combination of three lists selected first by school,
        then by division, and finally by region.
        """
        organization = getActiveDatabaseUser().get_active_organization()
        merge_list = []
        query_descriptor.set("use_class_query", False)
        query_descriptor.set("filter_by_organization", False)
        keylist = MultiLevelDefined.build_hierarchy_keylist(organization)
        for authority in (keylist):
            query_descriptor.set("filters", [("organization", authority)])
            query = SchoolDB.assistant_classes.QueryMaker(target_class, 
                                                          query_descriptor)
            object_list =  query.get_objects()                        
            merge_list = MultiLevelDefined.merge_lists(merge_list,
                                                       object_list)
        if (sort_function):
            merge_list = sort_function(merge_list)
        return merge_list

    @staticmethod    
    def sort_by_org_level(instances):
        """
        Sort by the order of the organizations that have a definition
        for this object. The most restricted comes first.
        """
        # almost always only 0 or 1 -- quick out for that case without
        # any other work
        if (len(instances) < 2):
            return instances
        else:
            #convoluted search method to limit the number of queries
            #first, build an array with each potential find in its
            #own location, then remove the empties.
            sorted_list = [None,None,None,None]
            for level in ((0,3),(3,0),(2,1),(1,2)):
                inst, instances = \
                    MultiLevelDefined._get_by_org_level(instances,level[0])
                if inst:
                    sorted_list[level[1]] = inst
                    if (len(instances) == 0):
                        break
            #clean up list
            clean_list = []
            for i in sorted_list:
                if i:
                    clean_list.append(i)
            return clean_list

    @staticmethod
    def _get_by_org_level(instances, level):
        """
        Get an instance from the list at the level of the index:
        0: National
        1: Regional
        2: Division
        3: Local
        Remove from list and return the instance and the shortened list
        """
        if (len(instances) > 0):
            lcl_org = getActiveDatabaseUser().get_active_organization()
            if (level == 0):
                org_key = National.get_national_org().key()
            elif (level == 1):
                org_key = lcl_org.division.region.key()
            elif (level == 2):
                org_key = lcl_org.division.key()
            else:
                org_key = lcl_org.key()
            at_level = None
            for i in instances:
                if (i.organization.key() == org_key):
                    instances.remove(i)
                    return i, instances
        return None, instances

    @staticmethod
    def get_field_names():
        field_names = [("organization", "Organization"),
                       ("other_information", "Other Information")]
        return field_names

    def remove(self):
        self.delete()
#----------------------------------------------------------------------
class DateBlock(MultiLevelDefined):
    start_date = db.DateProperty()
    end_date = db.DateProperty()
    classname = "Date Period"

    @staticmethod
    def create(name, organization):
        return DateBlock(name=name, parent=organization)

    def in_block(self, date):
        return ((date >= self.start_date) and 
                (date <= self.end_date))

    @staticmethod
    def sort_function(sort_list):
        sort_list.sort(key = lambda x:(x.start_date))
        return sort_list

    @staticmethod
    def custom_query(query_descriptor):
        return MultiLevelDefined.custom_query(query_descriptor, DateBlock,
                                              DateBlock.sort_function)
    @staticmethod
    def get_field_names():
        field_names = MultiLevelDefined.get_field_names()
        field_names.extend([("start_date", "Start Date"),
                            ("end_date", "End Date")])
        return field_names

    @staticmethod
    def filter_results_for_inrange(query_results, target_date):
        """
        A query can only filter on a single inequality. This function
        is performs the scond half of the filtering. The initial query
        should be with the end_date >= target_date. This will eliminate
        all those already expired so that the search will probably be
        much shorter.
        """
        inrange = []
        sorted_inrange = []
        if (len(query_results)):
            for result in query_results:
                if (result.start_date <= date):
                    inrange.append(result)
            if (len(inrange)):
                sorted_inrange = MultiLevelDefined.sort_by_org_level(inrange)
        return sorted_inrange

    def get_date_string(self):
        """
        Return a string in the form 11/22/2010-12/23/2010 for the
        start and end dates
        """
        start = self.start_date.strftime("%m/%d/%Y")
        end = self.end_date.strftime("%m/%d/%Y")
        return (start + " - " + end)

#---------------------------------------------------------------------
class SchoolYear(DateBlock):

    classname = "School Year"

    @staticmethod
    def create(name, organization):
        return SchoolYear(name=name, parent=organization)

    @staticmethod
    def custom_query(query_descriptor):
        return MultiLevelDefined.custom_query(query_descriptor, SchoolYear,
                                              DateBlock.sort_function)
    @staticmethod
    def school_year_for_date(date = date.today()):
        """
        Return the school year object for the specified date at the
        most local
        """
        query = SchoolYear.all()
        query.filter("end_date >=",date)
        years = query.fetch(100)
        #can only do inequality query filter on one property so must
        #do other filter here. Not too bad, most of the time there will 
        #probably be only one or two SchoolYears
        year = None
        year_list = SchoolYear.filter_results_for_inrange(years, date)
        if (len(year_list)):
            year = year_list[0]
        return year        
    
    @staticmethod
    def prior_school_year_for_date(date = date.today()):
        ref_date = date - timedelta(365)
        prior_year = SchoolYear.school_year_for_date(ref_date)
        return prior_year
        
    @staticmethod
    def school_year_boundary_for_date(get_school_start, date = date.today()):
        """
        Return start date of the school year if get_school_start True else
        get_school_end
        """
        year = SchoolYear.school_year_for_date(date)
        if year:
            if get_school_start:
                return year.start_date
            else:
                return year.end_date
        else:
            return None 

    @staticmethod
    def school_year_start_for_date(date = date.today()):
        """
        Return the start date of the school year. 
        """
        return SchoolYear.school_year_boundary_for_date(True, date)

    @staticmethod
    def school_year_end_for_date(date = date.today()):
        """
        Return the end date of the school year. 
        """
        return SchoolYear.school_year_boundary_for_date(False, date)
    
    @staticmethod
    def school_year_start_and_end_dates(date = date.today(),
                                        include_prior_break=False):
        """
        Return the tuple start_date, end_date for the school year.
        If include_prior_break is true set the start_date to the end
        of the prior school year + 1 day to encompass a complete
        calendar.
        """
        school_year = SchoolYear.school_year_for_date()
        start_date = school_year.start_date
        if (include_prior_break):
            ref_date = date - timedelta(365)
            prior_year = SchoolYear.prior_school_year_for_date(ref_date)
            if prior_year:
                start_date = prior_year.end_date + timedelta(1)
        end_date = school_year.end_date
        return start_date, end_date

    @staticmethod
    def get_field_names():
        field_names = DateBlock.get_field_names()
        return field_names

#---------------------------------------------------------------------
class GradingPeriod(DateBlock):
    school_year = db.ReferenceProperty(SchoolYear)
    classname = "Grading Period"

    @staticmethod   
    def create(name, organization):
        return GradingPeriod(name=name, parent=organization)

    @staticmethod
    def custom_query(query_descriptor):
        return MultiLevelDefined.custom_query(query_descriptor,
                                              GradingPeriod, DateBlock.sort_function)

    @staticmethod
    def get_field_names():
        field_names = DateBlock.get_field_names()
        field_names.append(("school_year", "School Year"))
        return field_names

    @staticmethod
    def get_completed_grading_periods():
        """
        Get the grading periods in the current school year that have
        ended no later than the current date. These are the only ones
        that can have valid grades. This is a long complicated process 
        with challenges in query and filtering. The end result will be
        a list from 0 - 3 element long sorted by start date.
        """
        school_year = SchoolYear.school_year_for_date()
        query = GradingPeriod.all()
        #query.filter("start_date >=", school_year.start_date)
        query.filter("end_date <=", date.today())
        query.order("-end_date")
        #with inverse sort order only the most recent will be included
        #this assusmes that no more than four years of grading periods
        #have been defined for the future
        periods = query.fetch(12)
        #now work backwards to get sorted int the correct way
        in_range_periods = []
        for i in range(len(periods) ,0,-1):
            period = periods[i - 1]
            if (period.start_date >= school_year.start_date):
                in_range_periods.append(period)
        #If only one or none then skip all of the following -- unneeded
        if (len(in_range_periods) < 2):
            return(in_range_periods)
        #Now only periods completed and in current school year
        #There may be some multidefined, so sort organization and
        #then remove probable matches
        periods_sorted = MultiLevelDefined.sort_by_org_level(in_range_periods)
        filtered_periods = []
        #the periods toward the front are better. Look for another further down
        #the list and remove it
        max_offset = timedelta(15)
        while (len(periods_sorted) > 1):
            compare_value = periods_sorted.pop(0)
            filtered_periods.append(compare_value)
            for i, period in enumerate(periods_sorted):
                to_delete = []
                if ((period.start_date <= (compare_value.start_date +
                                           max_offset))
                    and (period.start_date >= (compare_value.start_date -
                                               max_offset))):
                    to_delete.append(i)
            if (len(to_delete) > 0):
                to_delete.reverse()
                for i in to_delete:
                    periods_sorted.pop(i)
        if (len(periods_sorted)==1):
            filtered_periods.append(periods_sorted[0])
        #now there should be only one for each time period. Do a final time
        #sort
        final_periods_list = GradingPeriod.sort_function(filtered_periods)
        return final_periods_list

#----------------------------------------------------------------------
class SchoolDay(MultiLevelDefined):
    """
    The information about the type for a single day. This is created
    for every calendar day with most days either normal schoolday,
    weekend, or summer vacation. The day_type is one of limited list.
    The booleans for each year indicate if this definition is to be
    used for that year. if not, then the higher level one is used.
    Normally all are true.
    """
    date = db.DateProperty(required = True)
    day_type = db.StringProperty(choices = SchoolDB.choices.SchoolDayType)
    first_year = db.BooleanProperty(default = True)
    second_year = db.BooleanProperty(default = True)
    third_year = db.BooleanProperty(default = True)
    fourth_year = db.BooleanProperty(default = True)
    classname = "School Day"

    @staticmethod
    def create(date, organization_keystring):
        """
        The school day is rather unique. The name is really only a marker
        derived from the date and the organization but it is required to create the instance. Thus it must be generated from the other information prior to instance creation.
        """
        organization = get_instance_from_key_string(organization_keystring,
                                                    Organization)
        if organization:
            org_name = unicode(organization)
        else: org_name = "NotGiven"
        name = "%s-%s" %(date.strftime("%m/%d/%Y"), unicode(organization))
        return SchoolDay(name=name, date=date, organization=organization)

    @staticmethod
    def sort_function(sort_list):
        sort_list.sort(key = lambda x:(x.date))
        return sort_list

    @staticmethod
    def custom_query(query_descriptor):
        return MultiLevelDefined.custom_query(query_descriptor,
                                              SchoolDay, SchoolDay.sort_function)

    @staticmethod
    def get_school_day(date, section):
        """
        A special purpose query that returns both the most local day
        and the one above if the record is local to the school.
        """
        query = SchoolDay.all()
        query.filter("date =", date)
        days = query.fetch(10)
        if (len(days) == 0):
            day = None
        elif (len(days) == 1):
            day = days[0]
        else:
            sorted_days = MultiLevelDefined.sort_by_org_level(days)
            #The most locally defined is first. If the value for the 
            #appropriate class year is true then this local day type
            #applies. If false then the more general day type is
            #used. Ex. makeup day for only some year levels
            use_local_type = True
            classyear = section.class_year
            local_daytype = sorted_days[0]
            #if the day is redifined at the national level there will
            #be only a single entry in the sorted day list. There will
            #be at least two otherwise. Choose the next most local if
            #there are multiple ones
            if (len(sorted_days) > 1):
                index = 1
            else:
                index = 0
            general_daytype = sorted_days[index]
            #classyear list is in order. Use only index to allow a
            #change in the year names
            if (classyear == SchoolDB.choices.ClassYearNames[0]):
                use_local_type = local_daytype.first_year
            elif (classyear == SchoolDB.choices.ClassYearNames[1]):
                use_local_type = local_daytype.second_year
            elif (classyear == SchoolDB.choices.ClassYearNames[2]):
                use_local_type = local_daytype.third_year
            elif (classyear == SchoolDB.choices.ClassYearNames[3]):
                use_local_type = local_daytype.fourth_year
            if (use_local_type):
                day = local_daytype
            else:
                day = general_daytype
        return day   

#----------------------------------------------------------------------
class ClassPeriod(MultiLevelDefined):
    start_time = db.TimeProperty()
    end_time = db.TimeProperty()
    classname = "Class Period"

    @staticmethod
    def create(name, organization):
        """
        Add default start and end times to ensure that these fields are
        filled with some value that is safe for computation but
        obviously wrong
        """
        default_time = datetime.time(0,0)
        return ClassPeriod(name=name, parent=organization,
                           start_time=default_time, end_time=default_time)

    def in_class_period(self, time_val):
        return ((time_val >= self.start_time) and 
                (time_val < self.end_time))

    @staticmethod
    def sort_function(sort_list):
        for p in sort_list:
            if not p.start_time:
                p.start_time = time(0,0)
        sort_list.sort(key=lambda x:x.start_time)
        return sort_list

    @staticmethod
    def custom_query(query_descriptor):
        return MultiLevelDefined.custom_query(query_descriptor,
                                              ClassPeriod, ClassPeriod.sort_function)

    @staticmethod
    def get_field_names():
        field_names = MultiLevelDefined.get_field_names()
        field_names.extend([("start_time", "Start Time"),
                            ("end_time", "End Time")])
        return field_names

#----------------------------------------------------------------------
class Subject (MultiLevelDefined):
    """
    A simple multilevel class. The field used_in achievement_tests
    is set True only if it is a National defined subject.
    """
    classname = "Class Subject"
    used_in_achievement_tests = db.BooleanProperty()
    taught_by_section = db.BooleanProperty()
    
    @staticmethod
    def create(name, organization):
        return Subject(name=name, parent=organization,
                       used_in_achievement_tests =
                       (organization == National.get_national_org()))

    @staticmethod
    def custom_query(query_descriptor):
        return MultiLevelDefined.custom_query(query_descriptor, Subject)

#----------------------------------------------------------------------
class SectionType (MultiLevelDefined):

    classname = "Section Type"

    @staticmethod
    def create(name, organization):
        return SectionType(name=name, parent=organization)


    @staticmethod
    def custom_query(query_descriptor):
        return MultiLevelDefined.custom_query(query_descriptor, SectionType)

#----------------------------------------------------------------------
class StudentMajor (MultiLevelDefined):

    classname = "Student Major"

    @staticmethod
    def create(name, organization):
        return StudentMajor(name=name, parent=organization)


    @staticmethod
    def custom_query(query_descriptor):
        return MultiLevelDefined.custom_query(query_descriptor, StudentMajor)

#----------------------------------------------------------------------
class SpecialDesignation (MultiLevelDefined):

    classname = "Special Designation"

    @staticmethod
    def create(name, organization):
        return SpecialDesignation(name=name, parent=organization)


    @staticmethod
    def custom_query(query_descriptor):
        return MultiLevelDefined.custom_query(query_descriptor, 
                                              SpecialDesignation)

#----------------------------------------------------------------------
class Person(polymodel.PolyModel):
    """
    Person is the base class for all types of personal information. Simple,
    peripheral persons such as parents can be directly represented by this 
    class but others such as teachers and students will contain much more 
    complex information and thus be child classes with more data fields.
    """
    last_edit_time = db.DateTimeProperty(auto_now=True)
    last_editor = db.ReferenceProperty()
    first_name = db.StringProperty(required=True)
    middle_name = db.StringProperty()
    last_name = db.StringProperty(required=True)
    gender = db.StringProperty(choices = SchoolDB.choices.Gender, default =
                               "Female")
    title = db.StringProperty()
    address = db.StringProperty(multiline=True)
    province = db.ReferenceProperty(Province, collection_name = "person_province")
    municipality = db.ReferenceProperty(Municipality, collection_name=
                                        "person_municipality")
    community = db.ReferenceProperty(Community, collection_name =
                                     "person_community")
    cell_phone = db.StringProperty(required=False)
    landline_phone = db.StringProperty(required=False)
    email = db.StringProperty(required=False)
    other_contact_info = db.StringProperty(multiline=True)
    position = db.StringProperty(required=False)
    organization = db.ReferenceProperty(Organization, 
                                        collection_name="person_organization")
    organization_change_date = db.DateProperty()
    organization_history = db.ReferenceProperty(History,
                            collection_name="person_organization_history")
    other_information = db.StringProperty(multiline=True)
    custom_query_function = False
    classname = "Person"

    def full_name(self, include_title = True):
        """
        Generate a string of all elements of the name combined in the 
        normal manner first name, middle_name, last_name. If include_title
        is true then add the title at the front if a title is set.
        """
        padded_title = ""
        if self.title and include_title:
            padded_title = self.title + " "
        padded_middle = ""
        if self.middle_name:
            padded_middle = self.middle_name + " "
        full_name = "%s%s %s%s" %(padded_title, self.first_name, 
                                  padded_middle, self.last_name)
        return full_name

    def full_name_lastname_first(self, show_middle_name = True):
        """
        Generate a string of all elements of the name combined in the 
        reverse manner last_name, first name, middle_name
        """
        padded_middle = ""
        if (self.middle_name and show_middle_name):
            padded_middle = " " + self.middle_name
        full_name = "%s, %s%s" %(self.last_name, self.first_name,
                                 padded_middle)
        return full_name

    @staticmethod    
    def format_full_name_lastname_first(person):
        try:
            full_name = person.full_name_lastname_first()
        except:
            full_name = ""
        return full_name

    def format(self, format_name):
        """
        An inelegant solution but simple
        """
        if (format_name == "full_name_lastname_first"):
            return self.full_name_lastname_first()
        elif (format_name == "last_name_only"):
            return unicode(self.last_name)
        else:
            return unicode(self)

    def __unicode__(self):
        name = self.full_name(True)
        return name

    def post_creation(self):
        """
        This assures that the first name, middle name, and last name
        fields will be capitalized.
        """
        self.first_name = clean_up_letter_casing(self.first_name)
        self.middle_name = clean_up_letter_casing(self.middle_name)
        self.last_name = clean_up_letter_casing(self.last_name)

    def form_data_post_processing(self):
        """
        Perform actions that modify data in the model other than the 
        form fields. All of the data from the form has already been
        loaded into the model instance so this processing does not 
        need the form at all.
        This is a default action that does nothing.
        """
        pass

    def get_associated_database_user(self):
        """
        Find the database user associated with this person.
        """
        query = DatabaseUser.all()
        query.filter("person =", self)
        return (query.get())

    def in_organization(self, organization_key, requested_action):
        return (self.organization.key() == organization_key)

    @staticmethod
    def person_custom_query(organization, leading_value, value_dict,
                            query):
        """
        Perform a standard query for a person that will search and sort
        on the last name. This is the normal way that a person list will
        be chosen.
        """
        if value_dict.has_key("filterkey-organization"):
            query.add_filter("organization =", 
                             value_dict["filterkey-organization"])
        query.leading_value_filters = [("last_name", leading_value, True)]
        query.sort_params = ["last_name", "first_name"]
        return query.get_keys_and_names(Person.full_name_lastname_first)

    def remove(self):
        if (self.organization_history):
            self.organization_history.remove()
        self.delete()

    @staticmethod
    def get_field_names():
        field_names = \
                    [("first_name", "First Name"),
                     ("middle_name", "Middle Name"),
                     ("gender", "Gender"),
                     ("province", "Province"),
                     ("municipality", "Municipality"),
                     ("community", "Barangay"),
                     ("address", "Address"),
                     ("cell_phone", "Cell Phone"),
                     ("landline_phone", "Landline Phone"),
                     ("email", "Email")]
        return field_names
#----------------------------------------------------------------------
class Administrator(Person):
    """
    A class with no additional fields. This is used just for filtering
    of type of people by function and assures that person is only an
    abstract base class.
    """
    classname = "Administrator"

    def post_creation(self):
        """
        A default action that does nothing
        """
        Person.post_creation(self)
        self.put()

    @staticmethod
    def get_field_names():
        field_names = Person.get_field_names()
        field_names.extend([                     
            ("title", "Title"),
            ("position", "Position"),
            ("organization", "Organization")])
        return field_names
        
#------------------------------------------------------------------
class StudentSchoolSummaryHistory(History):
    """
    This class contains all student summary information for the school
    to be used by higher level user reports. It is a direct child of a
    history with each history entry containing a private reference to a 
    StudentInfoSummary. This class contains no additional database
    parameters beyond those in a history. All of the work for the
    information is performed by the class in the blob.
    """
    
    @staticmethod
    def create(school):
        """
        Create a school summary instance. See the parent class
        "history" for the creation actions. Then create the student
        info summary blob object and insert into the history.
        """         
        summary_history = StudentSchoolSummaryHistory(parent = school, 
                                 attribute_name = "student_summary",
                                 is_reference = True, multi_active = False,
                                 is_private_reference_object=True)
        summary_history.entries_list = []
        summary_history.put_history()
        summary_history.add_new_summary(school)
        return summary_history
    
    def add_new_summary(self, school):
        """
        Create a new StudentSchoolSummary in add it to the history.
        This is first done upon history creation and can then be done
        at intervals to maintain an historical view of the school's
        student information.
        """
        student_school_summary = StudentSchoolSummary.create(self, school)
        self.add_entry(date.today(), "", student_school_summary.key())
        
    def get_current_summary(self):
        student_school_summary, version_date = \
                         self.get_current_entry_value_and_date()
        return student_school_summary
    
    def mark_section_needs_update(self, section_key):
        student_school_summary = self.get_current_summary()
        student_school_summary.mark_section_needs_update(section_key)

    def update_current_summary(self, force_update=False):
        try:
            student_school_summary = self.get_current_summary()
            if force_update:
                student_school_summary.force_update()
                result = "\
                Student Summary Information forced update for all sections."
            else:
                count = student_school_summary.update_if_necessary()
                result = "Student School Summary will update %d sections." \
                       %count
            logging.info(unicode(self.parent()) + ": " + result)
            return True
        except StandardError, e:
            result = "Student School Summary failed: %s" %e
            
#------------------------------------------------------------------
class StudentSchoolSummary(db.Model):
    """
    This class contains summary information about the students
    organized by section. It is stored as a compressed Information
    Container in the student summary database object -- actually just
    the blob contained in a history entry. It provides a high level
    interface to the StudentSectionInfoSummary instances. There is only
    one of these per school that is current. The schools key is stored
    in this object for use when searching for new sections. 
    """
    school = db.ReferenceProperty()
    section_dict = db.BlobProperty()
    
    @staticmethod
    def create(parent, school):
        """
        Create the student info summary object with the student summary
        as parent. Add all sections at the school and update the
        information for all. At the end the instance will be ready for
        use filled with the most current information.
        """
        summary = StudentSchoolSummary(parent = parent)
        summary.initialize(school)
        return summary
    
    def initialize(self, school):
        """
        Set school, add a section_summary for each section, and then
        update all section_summaries.
        """
        self.school = school
        sect_dict = SchoolDB.summaries.StudentSchoolSectionDict()
        self.section_dict = sect_dict.put_data()
        self.put()
        self.add_sections_if_necessary()
        self.put()
    
    def add_sections_if_necessary(self):
        """
        Sections will be created in the school after the initial
        creation of this instance. Check for current sections and add
        any new sections for the school
        """
        query = SchoolDB.models.Section.all(keys_only = True)
        query.ancestor(self.school)
        section_keys = query.fetch(500)
        for section_key in section_keys:
            section_summary = self.get_section_summary(section_key)
            if (not section_summary):
                section_summary = self.create_section_summary(section_key)
          
    def mark_section_needs_update(self, section_key, put_self=True):
        """
        When a student record for the section is created or changed
        this summary object and the section summary is marked for
        update. If the section's summary has not yet been created then
        create it first. This assures that every section that has
        students has a section summary object.
        """
        self.section_dict = \
            SchoolDB.summaries.StudentSchoolSectionDict.mark_status(
             self.section_dict, section_key, False)
        section_summary_key = \
            SchoolDB.summaries.StudentSchoolSectionDict.get_section_summary(
                self.section_dict, section_key)
        if section_summary_key:
            db.get(section_summary_key).needs_update()
        if (put_self):
            self.put()
    
    def mark_section_current(self, section_key):
        """
        After the student section summary has completed its update task
        it will call this function to update the section_dict.
        """
        self.section_dict = \
            SchoolDB.summaries.StudentSchoolSectionDict.mark_status(
             self.section_dict, section_key, True)
        self.put()

    def force_update(self):
        """
        Mark all sections to require update, then call update_if_necessary
        to perform it.
        """
        for section_key in SchoolDB.summaries.StudentSchoolSectionDict.get_section_keys(
            self.section_dict):
            self.mark_section_needs_update(section_key, put_self = False)
        self.put()
        self.update_if_necessary()
    
    def create_section_summary(self, section_key):
        """
        Create a new section summary for the section. Add the 
        """
        section_summary = \
            StudentSectionSummary.create(self, section_key)
        self.section_dict = \
            SchoolDB.summaries.StudentSchoolSectionDict.add_section(
            self.section_dict, section_key, section_summary.key())
        return section_summary

    def get_section_summary(self, section_key, 
                            create_if_necessary = True):
        """       
        """
        section_summary = None
        section_summary_key = \
            SchoolDB.summaries.StudentSchoolSectionDict.get_section_summary(
                self.section_dict, section_key)
        if section_summary_key:
            section_summary = db.get(section_summary_key)
        elif (create_if_necessary):
            section_summary = self.create_section_summary(section_key)
        return section_summary

    def update_if_necessary(self):
        """
        Check the status of the summary. if all are current do nothing.
        If at least one is not current then check the status dict for
        each section. If it is not marked current then update the
        section summary in a unique task. Return a count of the
        sections that will be updated.
        """
        count = 0
        is_current = \
                SchoolDB.summaries.StudentSchoolSectionDict.get_is_current(
                    self.section_dict)
        if (not is_current):
            need_update_list = \
               SchoolDB.summaries.StudentSchoolSectionDict.get_all_summaries_not_current(
                   self.section_dict)
            for section_summary_key in need_update_list:
                    self.create_update_section_summary_task(
                        section_summary_key)
                    count += 1
        return count
    
    def create_update_section_summary_task(self, section_summary_key):
        """
        Create a task that will request this info_summary to update the
        specific section. This funciont is called for every section
        that requires updating so each section is updated in its own
        task.
        """
        #try:
        section_name = db.get(section_summary_key).get_section_name()
        task_name = section_name + "_update_student_summary" 
        task_generator = SchoolDB.assistant_classes.TaskGenerator(
            task_name=task_name,
            function=
            "SchoolDB.models.StudentSectionSummary.perform_update_task",
            function_args=('"' +str(section_summary_key)+ '"'), 
            organization=str(self.school))
        task_generator.queue_tasks()
        #except 
        
    def get_section_summaries_list(self):
        """
        Create a list of all of the student section summaries for the
        school. This is slightly expensive so the list should be
        kept by the caller to be used in report generation.
        """
        summary_keys = SchoolDB.summaries.StudentSchoolSectionDict.get_all_summaries(
            self.section_dict)
        summaries_list = [db.get(key) for key in summary_keys]
        return summaries_list
    
    def get_sections_by_class_year(self, class_year, summaries_list, 
                                   sort=True):
        """
        Get a list of all section summaries of the class_year sorted
        by section_name.
        """
        class_year_summaries_list = []
        for section_summary in summaries_list:
            if (section_summary.get_class_year() == class_year):
                class_year_summaries_list.append(section_summary)
        if (sort):
            def nm_sort (a,b):
                if a.get_section_name() < b.get_section_name():
                    return -1
                elif a.get_section_name() > b.get_section_name():
                    return 1
                return 0
            class_year_summaries_list.sort(nm_sort)
        return class_year_summaries_list
        
    def get_class_year_summary(self, class_year, summaries_list):
        """
        Combine the data for all sections in a class year into a single
        section summary object that can be used in the same way as an
        actual section summary.
        """
        section_summary_list = \
                    self.get_sections_by_class_year(class_year, 
                                                summaries_list, False)
        cy_summary = SchoolDB.summaries.StudentSectionSummaryData()
        cy_summary.section_name = class_year
        cy_summary.class_year = class_year
        median_age = [[],[],[]]
        for section_summary in section_summary_list:
            section_data = section_summary.get_data()
            for i in range(3):
                cy_summary.num_students[i] += section_data.num_students[i]
                cy_summary.balik_aral[i] += section_data.balik_aral[i]
                cy_summary.transferred_in[i] += \
                          section_data.transferred_in[i]
                cy_summary.transferred_out[i] += \
                          section_data.transferred_out[i]
                cy_summary.dropped_out[i] += section_data.dropped_out[i]
                cy_summary.average_age[i] += \
                    section_data.average_age[i] * \
                    section_data.num_students[i]
                if (section_data.max_age[i] > cy_summary.max_age[i]):
                    cy_summary.max_age[i] = section_data.max_age[i]
                if (section_data.min_age[i] < cy_summary.min_age[i]):
                    cy_summary.min_age[i] = section_data.min_age[i]
                median_age[i].extend([section_data.median_age[i] for j in
                                   range(section_data.num_students[i])])
        for i in range(3):
            if (cy_summary.num_students[i]):
                cy_summary.average_age[i] /= cy_summary.num_students[i]
            cy_summary.average_age[i] = round(cy_summary.average_age[i],1)
            if (len(median_age[i])):
                median_age[i].sort()
                cy_summary.median_age[i] = \
                           median_age[i][len(median_age) / 2]
            else:
                median_age[i] = 0        
        return cy_summary
        
#----------------------------------------------------------------------
class StudentSectionSummary(db.Model):
    """
    """
    is_current = db.BooleanProperty(default = False)
    section = db.ReferenceProperty()
    student_school_summary = db.ReferenceProperty(StudentSchoolSummary)
    data_store = db.BlobProperty()
    
    @staticmethod
    def create(student_school_summary, section):
        section_summary = StudentSectionSummary(
            parent=student_school_summary,
            student_school_summary=student_school_summary,
            section = section)
        section_summary.data_store = section_summary.create_data_store()
        section_summary.put()
        return section_summary
    
    def create_data_store(self):
        summary_info = SchoolDB.summaries.StudentSectionSummaryData()
        return summary_info.put_data()
    
    def get_section_name(self):
        return unicode(self.section)
    
    def get_class_year(self):
        return self.section.class_year
    
    def get_data(self):
        """
        Get the fully expanded StudentSectionSummaryData ready for use
        """
        return SchoolDB.summaries.StudentSectionSummaryData.get_data(
            self.data_store)
    
    def get_summary_information(self):
        summary_data = self.get_data()
        return (summary_data, self.section, self.is_current)
    
    def mark_current(self):
        """
        Set the is_current flag to true and also set the section's status
        in the school summary object.
        """
        self.is_current = True
        self.student_school_summary.mark_section_current(
            self.section.key())

    def needs_update(self):
        """
        Set is_current to False. The StudentSchoolSummary object has
        already been set.
        """
        self.is_current = False
        self.put()
        
    def update(self):
        try:
            summary_data = self.get_data()
            summary_data.update_student_information(self.section)
            self.data_store = summary_data.put_data()
            self.mark_current()
            self.put()
            info = "%s summary data updated successfully" \
                 %self.get_section_name()
            logging.info(info)
            return True
        except StandardError, e:
            error = "%s summary data update failed: %s" \
                  %(self.get_section_name, e)
            logging.error(error)
            return False

    @staticmethod
    def perform_update_task(section_summary_keystr):
        """
        Update the section summary data and mark both self and school
        summary status as section current.
        """
        section_summary = get_instance_from_key_string(
            section_summary_keystr)
        if (section_summary):
            return section_summary.update()
        else:
            return False
#----------------------------------------------------------------------
class School(Organization):
    """
    School is the class that contains all of the specific information about the
    individual school. 
    The parameters are:
    name - the school name used in official correspondence or records
    address - a general description of location
    location - the GPS coordinates 
    municipalty - key of the municipality object
    division - the name of the DepEd division or city that the school is in
    school_creation_date - date of founding
    student_summary - a single summary object of information 
    """
    municipality = db.ReferenceProperty(Municipality)
    division = db.ReferenceProperty(Division)
    principal = db.ReferenceProperty(Person)
    school_creation_date = db.DateProperty()
    students_municipalities = db.ListProperty(db.Key)
    student_summary = db.ReferenceProperty(StudentSchoolSummaryHistory)
    classname = "School"

    def save_municipalities_list(self, result_list):
        """
        Set the list of municipalities to the keys in the list that 
        has been given. The argument list is a list of tuples. The first
        value in each tuple is the key so use that and ignore the rest.
        """
        data_list = get_key_list(result_list, "Organization")
        self.students_municipalities = data_list

    def get_students_municipalities(self):
        """
        return a list of keys and names of the students municipalites
        """
        st_muni_ent = map(lambda(s):db.get(s), 
                          self.students_municipalities)
        municipality_pairs = get_key_name_list(st_muni_ent)
        return municipality_pairs

    def post_creation(self):
        """
        Create the student summary associated with the school
        """
        self.student_summary = StudentSchoolSummaryHistory.create(self)
        self.put()
    
    def get_schools(self):
        """
        Only this school is in this organization -- obviously
        """
        return [self]
    
    def lowest_level_org(self):
        """
        Schools are the lowest level DepEd org.
        """
        return True

    def update_student_summary(self, force_update=False):
        """
        Update the student summary for the school. Force update will
        cause a rebuild of all section summaries - very expensive. If
        not force update then only those sections marked as out of date
        will be rebuilt. Most of the time this will be very few or
        none.
        """
        try:
            #Try an action that uses the reference. If it fails, then 
            #reference is invalid. The docs imply just using a get but
            #that doesn't work at least in the local environment
            self.student_summary.attribute_name
        except datastore_errors.Error:
            self.student_summary = None       
        if self.student_summary:
            return self.student_summary.update_current_summary(
                    force_update)
        else:
            student_summary = StudentSchoolSummaryHistory.create(self)
            self.student_summary = student_summary
            self.put()
            return student_summary.update_current_summary(True)
        
    @staticmethod
    def get_field_names():
        field_names = [("name", "Name"), 
                       ("municipality", "Municipality"),
                       ("division", "Division")]
        return field_names

def update_all_schools_summaries(logger, force_update = False):
    """
    The standard schduled action to update the school summaries which
    is performed nightly. Only the summaries which have been marked for
    updating will do anything unless force update is set True.
    """
    query = School.all()
    for school in query:
        school.update_student_summary(force_update)
        
#----------------------------------------------------------------------

class Teacher(Person):
    """
    Teacher is a child class of person that adds a history of employment that
    contains the teachers paygrade, schools,etc.
    """
    subjects = db.ListProperty(db.Key)
    birthdate = db.DateProperty()
    primary_subject = db.ReferenceProperty(Subject,
                                collection_name="primary_subject_group")
    secondary_subject = db.ReferenceProperty(Subject,
                                collection_name="secondary_subject_group")
    paygrade = db.StringProperty(choices = SchoolDB.choices.TeacherPaygrade)
    employment_history = db.ReferenceProperty(History)
    custom_query_function = False
    classname = "Teacher"

    def post_creation(self):
        Person.post_creation(self)
        self.organization = getActiveDatabaseUser().get_active_organization()
        self.employment = db.StringProperty()
        self.employment_start_date = db.DateProperty()
        self.employment_history = History.create(self,
                                                 "employment_history")
        self.put()

    @staticmethod
    def get_field_names():
        field_names = Person.get_field_names()
        field_names.extend([
            ("paygrade", "Paygrade"),
            ("title", "Title"),
            ("position", "Position"),
            ("organization", "Organization")])
        return field_names

    def remove(self):
        self.employment_history.remove()
        self.delete()

#----------------------------------------------------------------------
class Classroom(db.Model):
    """
    A trivial class with information about a classroom. This is used to
    standardize the classroom names for a school, to associate a
    section with a classroom, and to provide location and other
    information about the room. If the classroom is not ready to be
    used or is no longer used then "active" is should be unchecked so
    that it will not be among the classrooms offered as a choice.
    """
    name = db.StringProperty(required=True)
    organization = db.ReferenceProperty(Organization,required=True)
    active = db.BooleanProperty(required=False,default=True)
    location = db.StringProperty(required=False, multiline=True)
    other_information = db.StringProperty(required=False, multiline=True)
    custom_query_function = False
    classname = "Classroom"


    @staticmethod
    def create(name):
        organization = \
                     getActiveDatabaseUser().get_active_organization()
        return Classroom(name=name, parent=organization,
                         organization=organization)

    def post_creation(self):
        """
        Note that organization is defined as a reference of type School
        rather than just organization. A classroom in any
        organization other than a school is meaningless. Thus the
        active user must be a member of the school or a highly
        privileged database administrator that can set the active
        organization before creating this object.
        """
        if (not self.organization):
            self.organization = \
                getActiveDatabaseUser().get_active_organization()
        self.put()

    def form_data_post_processing(self):
        """
        Perform actions that modify data in the model other than the
        form fields. All of the data from the form has already been
        loaded into the model ' instance so this processing does not
        need the form at all. For this class this is just a default
        funcion that does nothing.
        """
        pass

    def __unicode__(self):
        return self.name

    def in_organization(self, organization_key, requested_action):
        return (self.organization.key() == organization_key)

    def remove(self):
        self.delete()
    
#----------------------------------------------------------------------

class StudentGrouping(polymodel.PolyModel):
    last_edit_time = db.DateTimeProperty(auto_now=True)
    last_editor = db.ReferenceProperty()
    organization = db.ReferenceProperty(School, collection_name=
                                        "student_grouping_schools")
    name = db.StringProperty(required=True)
    classroom = db.ReferenceProperty(Classroom)
    teacher = db.ReferenceProperty(Teacher, collection_name=
                                   "student_grouping_teachers")
    teacher_change_date = db.DateProperty()
    teacher_history = db.ReferenceProperty(History, collection_name=
                                           "student_grouping_teacher_histories")
    custom_query_function = False
    classname = "Student Group"

    def post_creation(self):
        """
        Note that organization is defined as a reference of type School
        rather than just organization. A student grouping in any
        organization other than a school is meaningless. Thus the
        active user must be a member of the school or a highly
        privileged database administrator that can set the active
        organization before creating this object.
        """
        if (not self.organization):
            self.organization = \
                getActiveDatabaseUser().get_active_organization()
        self.put()
        return self

    def form_data_post_processing(self):
        """
        Perform actions that modify data in the model other than the
        form fields. All of the data from the form has already been
        loaded into the model ' instance so this processing does not
        need the form at all. For this class this is jus a default
        funcion that does nothing.
        """
        self.update_my_histories()

    def in_organization(self, organization_key, requested_action):
        return (self.organization.key() == organization_key)

    def get_history_tuple_by_name(self, name):
        history_name_dict = {}
        history_name_dict["teacher"] = (self.teacher, 
                                        self.teacher_change_date,
                                        self.teacher_history)
        return history_name_dict[name]

    def update_my_histories(self):
        """
        The histories primary fields are changed by form editing.
        Compare the values of those fields with the current entry in
        the history. If not equal then a new event has occured so add
        another history element.
        """
        history_names = ["teacher"]
        for name in history_names:
            history_create_params = self.get_history_create_info(name)
            _update_history(self, name, history_create_params)

    def get_history_create_info(self, attribute_name):
        """
        Return a tuple of the parameters required for the history
        object creation. These are used as direct arguments in the
        history create function and are in the order (self,
        attributename, is_reference, multiactive, is_private_reference)
        """
        hist_mapping = {"teacher":(self, "teacher", True, 
                                          False, False)}
        return hist_mapping.get(attribute_name, None)

    def __unicode__(self):
        return self.name

    @staticmethod
    def get_field_names():
        field_names = [("teacher", "Teacher"),
                       ("teacher_change_date", "Teacher Change Date")]
        return field_names

    def remove(self):
        self.teacher_history.remove()
        self.delete()

#----------------------------------------------------------------------
class Section(StudentGrouping):
    class_year = db.StringProperty()
    section_type = db.ReferenceProperty(SectionType)
    creation_date = db.DateProperty()
    termination_date = db.DateProperty()
    classname = "Section"

    @staticmethod
    def create(name,school):
        return Section(name=name, parent=school)

    def has_students(self):
        """
        Try to fetch the key of a single student from the section. If
        no key is returned then the section has no students.
        """
        query = Student.all(keys_only=True)
        query.filter("section =", self)
        student_key = query.get()
        return (student_key != None)

    def get_students(self):
        """
        Create a list of references to student instances that are
        in a single section at a school. Sort by gender and last
        name. This only yields the students currently in section,
        """
        query = Student.all()
        active_student_filter(query)
        query.filter("section =", self)
        query.order("last_name")
        query.order("first_name")
        results = query.fetch(500)
        return results

    def user_is_section_head(self):
        if (self.teacher):
            return (self.teacher.key() == 
                    getActiveDatabaseUser().get_active_person().key())
        else:
            return False

    def get_student_list(self):
        """
        Return a list of student keys, keystrings, and student names in
        the form used in nearly all section-based forms and reports.
        """
        names = []
        keys = []
        keystrings = []
        query = Student.all()
        active_student_filter(query)
        query.filter('section = ', self)
        query.order('gender')
        query.order('last_name')
        query.order('first_name')
        for student  in query:
            names.append(student.full_name_lastname_first())
            key = student.key()
            keys.append(key)
            keystrings.append(str(key))
        return keys, keystrings, names
    
    def student_info_changed(self, student):
        """
        Information in a studant instance that is in this section has
        changed.. Mark the section's summary for update required.
        """
        school = self.organization
        school_summary = school.student_summary
        school_summary.mark_section_needs_update(self.key())

    @staticmethod
    def get_field_names():
        field_names = [("class_year", "Class Year"),
                       ("section_type", "Section Type"), 
                       ("classroom", "Classroom"), ("teacher", "Teacher"),
                       ("teacher_change_date", "Teacher Change Date"),
                       ("section_creation_date", "Section Creation Date"),
                       ("section_termination_date", "Section Termination Date")]
        return field_names

#----------------------------------------------------------------------
class ClassSession(StudentGrouping):
    """
    A single class for a specified group of students at a particular period. 
    This is a child class of Student Gouping so the key elements of teacher,
    location, school, etc are contained in the parent class.
    The parameters are:
    subject 
    level 
    period 
    section 
    class_year 
    start_date 
    end_date 
    grade_element_ordered_list     

    """
    subject = db.ReferenceProperty(Subject)
    student_major = db.ReferenceProperty(StudentMajor)
    level = db.StringProperty(choices = SchoolDB.choices.ClassLevel)
    class_period = db.ReferenceProperty(ClassPeriod)
    students_assigned_by_section = db.BooleanProperty(default=True)
    section = db.ReferenceProperty(Section)
    class_year = db.StringProperty(choices = SchoolDB.choices.ClassYearNames)
    start_date = db.DateProperty()
    end_date = db.DateProperty()
    school_year = db.ReferenceProperty(SchoolYear)
    credit_units = db.FloatProperty()
    grade_instance_ordered_list = db.ListProperty(db.Key)
    classname = "Class Session"    

    def detailed_name(self):
        return ("%s - %s - %s" %(unicode(self.name), 
                                 unicode(self.class_period), unicode(self.teacher)))
    
    @staticmethod
    def create(name,school):
        return ClassSession(name=name, parent=school)

    @staticmethod
    def create_if_necessary(name, subject_keystring, section_keystring, 
                start_date, end_date, school_year_keystring,
                classroom_is_section_classroom=True):
        """
        There should normally be only one class session for a
        particular subject for a section each class year. This create
        queries the database to see if there is already such a class
        session in the database. If so, then nothing is created and the
        preexisting class session is returned. If not (the normal
        case), then the class session is created as are all student
        class records. This function allows the call to be idempotent
        -- repeated calls produce the same result as a single call.
        This function performs numerous tests for validity and
        permission. It is normally called by task and must be protected
        from error.
        This should only be used to create class sessions that are taught
        by section!
        """
        logging_prefix = 'Create class_session "' + name +'"'
        subject = get_instance_from_key_string(subject_keystring)
        section = get_instance_from_key_string(section_keystring)
        school_year = get_instance_from_key_string(school_year_keystring)
        if subject and section and school_year:
            query = ClassSession.all()
            query.filter("subject =",subject)
            query.filter("section =" ,section)
            query.filter("school_year = ", school_year)
            class_session_entity = query.get()
        else:
            logging.error(logging_prefix + " failed: One or more bad keys.")
            return None
        if not class_session_entity:
            #none exists, create one
            #determine organization from section
            school = section.organization
            #confirm legal to create class for this section
            if (not school.key() == 
                getActiveDatabaseUser().get_active_organization_key()):
                logging.error(
                    logging_prefix + " failed: user is not in organization.")
                return None
            try:
                start_date = date.fromordinal(int(start_date))
                end_date = date.fromordinal(int(end_date))
                class_year = section.class_year
                class_session = ClassSession(parent=school, name=name,
                            subject=subject, section=section, 
                            class_year=class_year, start_date=start_date, 
                            end_date = end_date, school_year=school_year,
                            organization=school)
                if classroom_is_section_classroom:
                    class_session.classroom = section.classroom
                #now use post_creation to put in database and assign students
                #to the class
                class_session_entity = StudentGrouping.post_creation(
                    class_session)
                result = class_session.assign_to_all_section_students()
                msg = logging_prefix + \
                    " initial creation completed successfully."
                logging.info(msg)
            except StandardError, e:
                class_session_entity = None
                msg = "%s failed during creation: %s" %(logging_prefix, e)
                logging.error(msg)
        return class_session_entity
                        
    def post_creation(self):
        StudentGrouping.post_creation(self)
        #For now, if a section is assigned then assign all students
        #in the section to the class. This logic may need to be
        #rethought...
        if (self.section):
            self.assign_to_all_section_students()
        return self

    @staticmethod
    def sort_by_time(class_sessions):
        """
        Return the list of class_session instances sorted by the start
        time of the class determined by the class period. This takes
        the actual class session instances, not the keys as an
        argument. This should be used for a limited number of classes
        because it is fairly expensive in queries.
        """
        cls_and_periods = []
        #sort first by name so that same period classes are ordered
        #by name (secondary sort)
        class_sessions.sort(key=lambda cls: cls.name)
        #now sort by period time (primary sort)
        class_sessions.sort(key=lambda cls: cls.class_period.start_time)
        return class_sessions

    @staticmethod
    def create_ordered_list(class_session_keys, keys_are_strings=True):
        """
        A common form of use for a list of classes is a list of sorted
        tuples of key, name, period name. Create this from a list of
        class_session keys. If keys_are_strings is True convert and
        filter the key list first.
        """
        if keys_are_strings:
            keys = get_key_list(class_session_keys,"StudentGrouping")
        else:
            keys = class_session_keys
        try:
            class_sessions = ClassSession.get(keys)
            class_sessions = ClassSession.sort_by_time(class_sessions)
        except db.BadKeyError:
            error = "Wrong key type in class_sessions list"
        result_list = []
        for sess in class_sessions:
            result_list.append((sess.key(), unicode(sess), 
                                unicode(sess.period)))
        return result_list

    def get_student_class_records(self, status_filter = "", keys_only=False):
        q = StudentsClass.all(keys_only=keys_only)
        q.filter("class_session =", self)
        if (status_filter):
            q.filter("current_status =", status_filter)
        return (q.fetch(900))

    @staticmethod    
    def sort_students_in_place(students):
        students.sort(compare_person_by_gender_name)
        return students

    def get_students_from_records(self, student_records):
        students = []
        for student_class in student_records:
            students.append(student_class.get_student())
        return students

    def get_students_and_records(self, status_filter="", sorted = False,
                                 record_by_key=False):
        """
        The most efficient way to get all students and student records.
        This returns a list of student class records, a list of
        students, and a dictionary of student records keyed by student.
        The dictionary provides a low cost way to get student records
        from students. If sorted is true then the lists of students and
        student_keys are both sorted in the standard class session sort
        order. This function is performed in a minimal number of
        queries.
        """
        student_records = self.get_student_class_records(status_filter=
                                                         status_filter)
        students = self.get_students_from_records(student_records)
        student_record_dict = {}
        for i in xrange(0,len(students)):
            if record_by_key:
                student_record_dict[students[i]] = \
                                   student_records[i].key()
            else:
                student_record_dict[students[i]] = \
                                   student_records[i]
        if sorted:
            #cannot sort with just keys
            ClassSession.sort_students_in_place(students)
            student_records = []
            for student in students:
                student_records.append(student_record_dict[student])
        return students, student_records, student_record_dict

    def create_class_roster(self, return_class_record_dictionary=False):
        """
        Create an array of (student_key, student name) tuples for all
        students in the class. This is the heavyweight version that
        performs all queries and sorting. Use the global "get_key_list"
        function with the list of students if you already have the
        student list. If return_class_record_dict is true then return
        the dictionary as a second member of a tuple with the roster
        list.
        """
        students, student_records, student_record_dict\
                = self.get_students_and_records(status_filter="Active")
        students.sort(compare_person_by_gender_name)
        return_list = get_key_name_list(students, 
                        Person.format_full_name_lastname_first)
        if (return_class_record_dictionary):
            return return_list, student_record_dict
        else:
            return return_list

    @staticmethod
    def static_add_student_to_class(student_keystring,
                                    class_session_keystring, start_date):
        """
        A static function definition for use by tasks.
        """
        students_class = None
        class_session_name = ""
        student_name = ""
        try:
            class_session = get_instance_from_key_string(
                class_session_keystring, ClassSession)
            if class_session:
                class_session_name = unicode(class_session)
                student = get_instance_from_key_string(
                    student_keystring, Student)
                if student:
                    student_name = unicode(student)
                    students_class = class_session.add_student_to_class(
                        student, date.fromordinal(int(start_date)))
        except StandardError, e:
            logging.error('Add student "%s" to class "%s" failed: %s' \
                          %(student_name, class_session_name, e))
        return students_class
    
    def add_student_to_class(self, student, start_date=None):
        """
        Add a student to the class by creating a StudentsClass instance 
        for the class session. If the student is already assigned to the class 
        then no new record will be added.
        """
        if (not start_date):
            start_date = self.start_date
        students_class = student.assign_class_session(self, self.subject,
                                                      start_date)
        return students_class

    def singlerun_add_students_to_class(self, student_list, start_date=None):
        """
        Add a list of students to the class. The list may be just a
        section list for section based classes or a list of students
        generated from a selection GUI.
        """
        if (not start_date):
            start_date = None
        else:
            start_date = date.fromordinal(start_date)
        students_class_records = []
        for student in student_list:
            students_class = self.add_student_to_class(student, start_date)
            if (students_class):
                students_class_records.append(students_class)
        return students_class_records
                           
    def add_students_to_class(self, student_list, start_date=None):
        """
        Add a list of students to the class. The list may be just a
        section list for section based classes or a list of students
        generated from a selection GUI. This function uses tasks to
        add students.
        """
        if (not start_date):
            start_date = self.start_date
        task_name = "AddStudentsToClass: " + self.name
        function = "SchoolDB.models.ClassSession.static_add_student_to_class"
        function_args = "class_session_keystring= '%s'" %str(self.key())
        if start_date:
            function_args = "%s, start_date='%d'" %(function_args, 
                                                 start_date.toordinal())
        instance_keylist = [ str(student.key()) for student in student_list]
        task = SchoolDB.assistant_classes.TaskGenerator(task_name=task_name,
                    function=function, function_args=function_args,
                    instance_keylist=instance_keylist, 
                    instances_per_task=15)
        return task.queue_tasks()
        
    def assign_to_all_section_students(self):
        """
        The class session will be given to all students in the section.
        Most classes are taught in this manner (i.e., the session is
        for all only the students in a single section) so this allows
        for easy entry of most of students schedules.
        """
        students_list = self.section.get_students()
        return self.add_students_to_class(students_list)

    def get_grading_instances(self, keys_only=False):
        """
        Query the database for all grading instances belonging to 
        this class session.
        """
        query = GradingInstance.all()
        query.ancestor(self)
        instances = query.fetch(1000)        
        return instances

    def user_is_class_session_teacher(self):
        if (self.teacher):
            return (self.teacher.key() == 
                    getActiveDatabaseUser().get_active_person().key())
        else:
            return False

    #def add_instance(self, grading_instance_args, before_instance= -1):
        #"""
        #This is the primary way to add a grading instance.
        #The "grading_elament_arguments" is a dictionary that contains the
        #arguments necessary for a class_grading_instance. The instance id
        #is computed in this function. The before instance argument allows 
        #the instance to be placed in the order sequence with -1 meaning
        #add to end.
        #"""
        #instance = ClassGradingElement(self, grading_instance_args["name"],
                #grading_instance_args["type"],
                #grading_instance_args["percent_final"], 
                #grading_instance_args["extra_credit"],
                #grading_instance_args["other_info"])
        #self.grading_instances[instance_id] = instance
        #self.reorder_instance(instance_id, before_instance)
        #return instance

    #def reorder_instance(self, instance_id, before_instance_id):
        #before_index = -1
        #try: 
            #if (before_instance_id != -1):
                #before_index = self.instance_order_index.find(instance_id)
            #self.instance_order_index.remove(instance_id)            
        #except ValueError:
            #pass
        #if (before_index == -1):
            #self.instance_order_index.append(instance_id)
        #else:
            #self.instance_order_index.insert(before_index, instance_id)
        #return self.get_ordered_instance_list()

    #def get_ordered_instance_list(self):
        #"""
        #Return a list of the instances in the order of the instance index
        #"""
        #instances = []
        #for eo_index in self.instance_order_index:
            #instances.append(self.grading_instances[eo_index])
        #return (instances)

    #def get_instance(self, instance_id):
        #return self.grading_instances[instance_id]

    #@staticmethod
    #def create_subject_choice_array(subject_name):
        #query_string = \
        #"SELECT __key__ FROM ClassSession WHERE subject= :subject AND organization = :school"
        #query = db.GqlQuery(query_string, subject=subject_name, 
                            #organization= getActiveDatabaseUser().get_active_organization())
        #return (create_choice_array_from_query(query))


#----------------------------------------------------------------------  

class GradingInstance(db.Model):
    """
    A representation of one or more graded elements of the same type and
    name. It has an assigned percentage of the total student grade. If
    flagged as multiple it may have more than one sub-instance. An example
    of a single instance would be a final test or paper, a multiple
    instance several grades for daily tests.
    """
    name = db.StringProperty(required = True)
    owner = db.ReferenceProperty()
    subject = db.ReferenceProperty(Subject, collection_name="subjects")
    grading_type = db.StringProperty()
    percent_grade = db.FloatProperty()
    extra_credit = db.BooleanProperty()
    multiple = db.BooleanProperty()
    other_information = db.StringProperty(multiline=True)
    events = db.BlobProperty()
    number_questions = db.IntegerProperty()
    class_year = db.StringProperty() #this is only used for achievement tests
    classname = "Gradebook Entry"

    @staticmethod
    def create(name, owner, planned_date=None):
        """
        Create a new grading instance associated with the specified
        class session. If a date id given create a grading event
        associated with the instance at that date.
        """
        new_instance=GradingInstance(name=name, 
                                     owner=owner,
                                     parent=owner)
        gd_events = SchoolDB.assistant_classes.GradingEvents()
        if (planned_date):
            gd_events.add_grading_event(planned_date)
        new_instance.events = gd_events.put_data()
        new_instance.put()
        return new_instance

    def __unicode__(self):
        return unicode(self.name)

    def post_creation(self):
        """
        A default action that does nothing
        """
        pass

    def form_data_post_processing(self):
        """
        Perform actions that modify data in the model other than the
        form fields. All of the data from the form has already been
        loaded into the model's instance so this processing does not
        need the form at all. For this class this is just a default
        function that does nothing.
        """
        pass

    def get_percentage_of_final(self):
        return self.percent_grade

    def get_grading_events(self):    
        return SchoolDB.assistant_classes.GradingEvents.get_data(self.events)

    def store_grading_events(self, grading_events):
        self.events=grading_events.put_data()

    def get_event_date(self, event_list_index):
        grading_events = self.get_grading_events()
        return grading_events.get_grading_event_date_by_index(event_list_index)

    def set_date(self, new_date, old_date = None, put=True):
        """
        The common method to either add or change a current date. if the
        grading type is multiple then the list of dates in the
        grading_entries is scanned for the old_date. If found, it is set to
        the new date. If not, as will normally be the case because the
        prior date is None then just add it to the list. If the grading
        instance is single then then dates[0] is set unconditionally.
        """
        grading_events = self.get_grading_events()
        grading_events.change_date(new_date, old_date)
        self.store_grading_events(grading_events)
        if (put):
            self.put()
        return self

    def get_event_on_date_valid_state(self, date):
        grading_events = self.get_grading_events()
        return grading_events.event_is_valid(date)

    def get_valid_state(self):
        """
        Valid if at least one grading event has been created and has
        grades entered.
        """
        grading_events = self.get_grading_events()
        return grading_events.is_valid()
    
    def in_organization(self, organization_key, requested_action):
        return (self.parent == organization_key)

    def get_classification(self):
        """
        Return a sting with a basic classification of type single entry,
        multiple entry, or upper level based upon the graing_instance type
        """
        classification = "Single"
        if (self.multiple):
            classification = "Recurring"
        if ((self.grading_type == "National Test") or
            (self.grading_type == "Regional Test") or
            (self.grading_type == "Division Test")):
            classification = "UpperLevel"
        return classification

    @staticmethod
    def get_field_names():
        field_names = [("name", "Name")]
        return field_names

    #def average_grade(self):
        #sum = 0
        #for students_grade in grades:
            #sum += students_grade.grade
        #average = sum / len(grades)
        #return average            
#----------------------------------------------------------------------  

class AchievementTest(db.Model):
    """
    A representation of an achievement test from a higher level
    organization such as a national, regional, or division test. These may
    have separate parts for each subject that are graded individually and
    are normally either for all class years or only single years. This
    class contains information for only one class year. It is the central
    class to integrate data about the test but the actual results and data
    are maintained in the classes of the normal grades. There are
    GradingInstance/GradingEvent pairs for each subject on the test.
    """
    classname = "Achievement Test"
    last_edit_time = db.DateTimeProperty(auto_now=True)
    last_editor = db.ReferenceProperty()
    organization = db.ReferenceProperty(Organization)
    name = db.StringProperty(required=True)
    date = db.DateProperty()
    percent_grade = db.FloatProperty()
    class_years = db.ListProperty(str)
    #the choices are a subset of the GradingInstanceType
    grading_type = db.StringProperty(choices = 
                                     SchoolDB.choices.AchievementTestType)
    #The subject list should include only those at the national level
    subjects = db.ListProperty(db.Key)
    summary_blob = db.BlobProperty()
    other_information = db.StringProperty(multiline=True)

    @staticmethod
    def create(name, organization):
        """
        Set organization and parent to users org upon creation
        """
        new_instance = AchievementTest(name=name, parent=organization, 
                                       organization=organization)
        new_instance.put()
        return new_instance

    @staticmethod
    def findAchievementTest(organization, 
                            date=None, grading_type=None, 
                            class_year="", name="", date_range=10, 
                            min_date=None, max_date = None):
        """
        This is a loose search for the test by an external actor such
        as a query from an upper level organization. Because this is
        entered locally the name cannot be guaranteed to be consistent
        nor can the date be guranteeed to be exactly correct but the
        organization should be correct. This search assumes that
        achivement tests of a specific type by a single organization do
        not occur very often. It searches by organization, test type,
        and date +-date_range days. It is filtered by class year so that
        each class year is returned individually
        """
        if (date):
            delta = timedelta(date_range + 1)
            min_date = date - delta
            max_date = date + delta
        query = AchievementTest.all()
        query.filter("organization = ", organization)
        if min_date:
            query.filter("date >", min_date)
        if max_date:
            query.filter("date <", max_date)
        if grading_type:
            query.filter("grading_type = ", grading_type)
        if class_year:
            query.filter("class_year = ", class_year)
        tests = query.fetch(50)
        if (len(tests) == 0):
            return None
        if (name and (len(tests) > 1)):
            for test in tests:
                if (test.name.find(name)):
                    return test
        if (len(tests) == 0):
            return None
        else:
            return test[0]

    @staticmethod
    def findAchievementTestsForSection(section):
        """
        Return a list of Achievement tests that are available for the section
        for the school year to date and a bit in the future sorted in reverse
        chronological order.
        """
        class_year = section.class_year
        school_year = SchoolYear.school_year_for_date(date.today())
        min_date = school_year.start_date
        max_date = date.today() + timedelta(10)
        query = AchievementTest.all()
        query.filter("organization = ", 
                     getActiveDatabaseUser().get_active_organization())
        query.filter("date >", min_date)
        query.filter("date <", max_date)
        query.filter("class_year =", class_year)
        query.order("-date")
        return query.fetch(50)

    
    def update(self, updated_information):
        """
        Update or create the summary and grading instances for the
        achivement test.
        """
        self.update_grading_instances(updated_information)
        self.update_summary_subjects(updated_information)
        
    def update_summary_subjects(self, updated_information):
        """
        Add or remove summary contents for the achievement test. If no
        summary instance has yet been created for a new achivement
        test, fully create it. This performs a put of this AchievmentTest
        instance when complete.
        """
        if self.summary_blob:
            summary = self.get_summary()
        else:
            summary = SchoolDB.summaries.AchievementTestSummary()
        subject_names, name_to_key_dict, key_to_name_dict = \
                get_possible_subjects("used_in_achievement_tests =")
        for info_tuple in updated_information:
            classyear_name, subject_name, number_questions = info_tuple
            subject_keystr = str(name_to_key_dict.get(subject_name, None))
            summary.add_year_and_subject(classyear_name, subject_keystr)
        self.save_summary(summary)
    
    def in_organization(self, organization,other):
        #>>>>>FIX THIS HACK SOON!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!<<<<
        return True
    
    def update_grading_instances(self, updated_information):
        """
        Check for grading instances already created for the year and
        subject. If they exist, update with changed information. If 
        not, create and fill. If there are instances that are no longer
        needed and there are no other references to them remove
        them, else mark them as invalid.
        """
        grading_instances = self.get_grading_instances()
        subject_names, name_to_key_dict, key_to_name_dict = \
                get_possible_subjects("used_in_achievement_tests =")
        updated_grading_instances = []
        for info_tuple in updated_information:
            class_year, subject_name, number_questions = info_tuple
            subject_key = name_to_key_dict.get(subject_name, None)
            if subject_key:
                grading_instance = None
                found = False
                for grading_instance in grading_instances:
                    if ((grading_instance.class_year == class_year)
                        and (grading_instance.subject.key() == subject_key)):
                        grading_instances.remove(grading_instance)
                        found = True
                        break
                if not found:
                    #create new
                    gi_name = "%s.%s" %(self.name, subject_name)
                    gd_events=SchoolDB.assistant_classes.GradingEvents()
                    if (self.date):
                        gd_events.add_grading_event(self.date)
                    gd_events_blob=gd_events.put_data()
                    grading_instance = GradingInstance(name=gi_name, 
                                    subject=subject_key,
                                    grading_type=self.grading_type,
                                    percent_grade=float(self.percent_grade),
                                    extra_credit=False,
                                    multiple=False,
                                    events=gd_events_blob,
                                    number_questions = number_questions,
                                    class_year=class_year, 
                                    parent=self)
                else:
                    grading_instance.number_questions = number_questions
                    grading_instance.set_date(self.date, None, False)
                updated_grading_instances.append(grading_instance)
        db.put(updated_grading_instances)
        #now clean up any grading instances no longer needed
        #confirm that they have not already been used before removing
        for gd_inst in grading_instances:
            used = gd_inst.get_valid_state()
            if (not used):
                gd_inst.delete()

    @staticmethod
    def get_info_for_view(instance_string = ""):
        """
        Create a list of subjects and class years to be used in the form.
        If there is a keystring for an AchievementTest, 
        Use the set of grading instances for the test to generate a list of
        tuples in the same form as is used to update the grading instances.
        This contains all information necessary for edit and display
        """
        subject_names, name_to_key_dict, key_to_name_dict = \
                     get_possible_subjects("used_in_achievement_tests =")
        class_years = get_class_years_only()
        view_info = [ ]
        at_instance = get_instance_from_key_string(instance_string)
        if (at_instance):
            grading_instances = at_instance.get_grading_instances()
            for grading_instance in grading_instances:
                try:
                    class_year = grading_instance.class_year
                    subject = key_to_name_dict[grading_instance.subject.key()]
                    number_questions = grading_instance.number_questions
                    view_info.append([class_year, subject, number_questions])
                except:
                    pass
        return subject_names, class_years, view_info

    def get_grading_instances(self):
        instance_query = GradingInstance.all()
        instance_query.ancestor(self)
        return(instance_query.fetch(100))

    def changeDate(self, old_date, new_date):
        """
        Change the date for self and all of the underlying grading events
        """
        self.date = new_date
        grading_instances = self.get_grading_instances()
        for instance in grading_instances:
            instance.set_date(old_date, new_date, False)
        grading_instances.put()

    def change_percent_grade(self, percent_grade):
        """
        Change the percentage that the test represents in the overall student
        grade. This should be done only if the subject has not had a unique
        percentage set.
        """
        for instance in self.get_grading_instances():
            if (instance.percent_grade == self.percent_grade):
                instance.percent_grade = percent_grade
        self.percent_grade = percent_grade

    def mark_test_completed(self):
        """
        When the test has been completed the grading instances should
        show valid so that the results can be used in computing the
        grades.
        """
        for instance in self.get_grading_instances():
            instance.valid[0] = True

    def get_summary(self):
        summary = SchoolDB.summaries.AchievementTestSummary.get_data(
            self.summary_blob)
        return summary

    def save_summary(self, summary):
        """
        Convert the summary information back into the blob, save it in 
        self, and put self back into the database
        """
        summary_blob = \
            SchoolDB.summaries.AchievementTestSummary.put_data(summary)
        self.summary_blob = summary_blob
        self.put()

    def update_summary_information(self, section_keystr, grade_lists):
        """
        Record the grades for a section in the summary information.
        This is normally done when the grades are entered from the
        web form.
        """
        summary = self.get_summary()
        if summary:
            for subject_keystr in grade_lists.keys():
                combined_grades, male_grades, female_grades = \
                               grade_lists[subject_keystr]
                summary.set_ati_statistics_for_class_and_subject(section_keystr,
                    subject_keystr, combined_grades, male_grades, female_grades)
            self.save_summary(summary)

    def get_summary_information_for_section(self, section_keystr):
        """
        Return a dictionary of AchievementTestSummaries for the section
        keyed by subject_keystr
        """
        summary = self.get_summary()
        class_year = list(summary.class_year_by_section(section_keystr))
        subject_keystrs = list(summary.subjects_by_year(class_year))
        section_dict = {}
        for subject_keystr in subject_keystrs:
            section_dict[subject_keystr] = \
                        summary.get_ati_statistics_for_section_and_subject(
                            section_keystr, subject_keystr)
        return section_dict

    def get_summary_information_for_class_year(self, class_year):
        """
        Return a dictionary of AchievementTestSummaries aggregated across all
        section in the class year keyed by the subject keystr
        """
        summary = self.get_summary()
        subject_keystrs = list(summary.subjects_by_year[class_year])
        class_year_dict = {}
        for subject_keystr in subject_keystrs:
            class_year_dict[subject_keystr] = \
                summary.aggregate_ati_statistics_set_for_class_year_and_subject(
                               class_year, subject_keystr)
        return class_year_dict

    def __unicode__(self):
        return self.name

    def form_data_post_processing(self):
        pass

    def post_creation(self):
        pass

#----------------------------------------------------------------------
class Family(db.Model):
    """
    This is a very simple database class that serves merely as a
    connector between parents and students in the same family. All have
    a reference to this object which allows simple database queries to
    establish the relationship among all of them.
    """
    name = db.StringProperty(default="")
    custom_query_function = False
    classname = "Family"


    def post_creation(self):
        self.put()

    def filter_class(self, instances, filter_name):
        """  
        Because of the problems with the polymodel neither the class
        nor the collection list name work. This requires the rather
        obtuse approach of testing for a property that is unique to the
        particular class.
        """       
        filtered_list = []
        for instance in instances:
            properties = instance.properties()
            if (properties.has_key(filter_name)):
                filtered_list.append(instance)
        return filtered_list

    def get_parents(self):
        """
        Get references for all parentsOrGuardians instances that
        reference the family.
        """
        instances = self.parentorguardian_set.fetch(100)
        return self.filter_class(instances, "relationship")

    def get_siblings(self):
        instances = self.students_set.fetch(100)
        return self.filter_class(instances, "class_year")

    def remove(self, last_student = None):
        """
        The family object can only be removed after student objects 
        that refer to it are gone themselves. Do nothing otherwise.
        ParentsOrGuardians are connected only throught the family
        object so delete them just before self.
        The last student will still have a reference at this point,
        so confirm that that the final reference is the caller.
        """
        siblings = self.get_siblings()
        if (((len(siblings) == 1) and \
             (siblings[0].key() == last_student.key())) or \
            (len(siblings)== 0)):
            parents = self.get_parents()
            for parent in parents:
                parent.remove()
            self.delete()

    def in_organization(self, organization_key, requested_action):
        """
        The family's organization is simply that of the first students
        organization. This will then track the student if she moves. At
        first creation the student record will not yet exist. For this
        case just return true so that action can continue. That will be
        valid in this special case.
        """
        siblings = self.get_siblings()
        if (len(siblings) > 0):            
            in_org = \
                   (siblings[0].organization.key() == organization_key)
        else:
            #new family -- no student yet
            in_org = True
        return in_org

    @staticmethod
    def get_field_names():
        field_names = [("name", "Name")]
        return field_names


#----------------------------------------------------------------------
class ParentOrGuardian(Person):

    family = db.ReferenceProperty(Family)
    relationship = db.StringProperty(choices = 
                                     SchoolDB.choices.Relationship)
    contact_order = db.StringProperty(choices = 
                                      SchoolDB.choices.ContactOrder)
    occupation = db.StringProperty()
    classname = "Parent or Guardian"

    def post_creation(self):
        Person.post_creation(self)
        self.put()


#----------------------------------------------------------------------
class StudentAttendanceRecord(db.Model):
    """
    This is a simple database class for a students complete attendance 
    record.
    It is refered to by only a single student. It contains a list of dates
    and attendance status for each day. Each day has two entries, one
    for the moning and one for the afternoon session because all 
    reporting is based upon half days. Each half's information is 
    encoded into a single byte.
    The encoding is:
    Define encoding values for states.
    Each value is a unique bit in a byte. This means that setting
    can be done by addition rather than bitwise or. 
    Example: Student present for entire day:
    valid + known + school_day + afternoon_present + morning_present 
    Out of range for student registered period or school not in 
    session -- all values are set to this initially. These dates
    are not used in any calculations.
    --- invalid = 0
    Within the range of of times that the attendance information is
    usable. This means that the student is registered and school is
    in session. (bit 8 set)
    --- valid = 128
    Attendance information has been set or is non school day. This
    is set only after the student has been processed through the
    the attendance page.
    --- known = 64
    The day is a "school day" when students are expected to be 
    present.
    --- school_day = 32
    The session is either morning or afternoon half days.
    Student was present for that session
    --- present = 1
    The start date is the reference date for the array of days. It is
    used to compute the date that each byte represents. It is represented
    as the ordinal of the date because all calculations use this value.
    If the student record is created after the start of the school year
    the prior days present and absent fields allow coding of this 
    information. This can also be used if the student record has not
    been created for prior years.
    """

    start_date_ordinal = db.IntegerProperty()
    attendance = db.BlobProperty()
    prior_days_present = db.IntegerProperty()
    prior_days_absent = db.IntegerProperty()
    student_is_active = db.BooleanProperty()
    attendance_array = None
    custom_query_function = False
    classname = "Attendance Record"
    extension_days = 150
    max_extension_days = 600
    # Define encoding values for states.
    # Each value is a unique bit in a byte. This means that setting
    # can be done by addition rather than bitwise or. Each half_day
    # is a single byte.
    # Example: Student present for morning:
    # valid + known + school_day + present 
    # Out of range for student not registered or school not in 
    # session. These days are not used in any calculations.
    invalid = 0
    #Within the range of of times that the attendance information is
    #usable. This means that the student is registered and school is
    #in session. (bit 8 set)
    valid = 128
    # Attendance information has been set or is non school day. This
    # is set only after the student has been processed through the
    # the attendance page.
    known = 64
    # The day is a "school day" when students are expected to be 
    # present.
    school_day = 32
    # Student was present that session
    present = 1

    @staticmethod
    def create(parent_entity, start_date = date.today(), 
               prior_days_present = 0, prior_days_absent = 0, 
               initial_array_size = 400):
        """
        This is like the __init__ class method but is used because the
        appDB reserves all ""--" definitions for itself. 
        """
        initial_array = array.array("B",[0])
        start_date_ordinal = start_date.toordinal()
        today = date.today().toordinal()
        #increase in intial size by the number of days prior of the
        #start date from today
        if (start_date_ordinal < today):
            initial_array_size += 2* (today - start_date_ordinal)
        initial_array *= initial_array_size
        initial_array_blob = bz2.compress(initial_array.tostring())
        attendence_entity = StudentAttendanceRecord(parent=parent_entity, 
                            start_date_ordinal=start_date_ordinal, 
                            prior_days_present=prior_days_present,
                            prior_days_absent=prior_days_absent,
                            attendance=initial_array_blob)
        attendence_entity.active_attendance = initial_array
        #intialize the array based upon students initial status.
        #This will also perform the put to save the record in the database
        attendence_entity.student_status_changed(start_date,
                            parent_entity.student_status.active_student)
        return attendence_entity

    @staticmethod 
    def is_valid(day_type):
        return day_type & StudentAttendanceRecord.valid

    @staticmethod 
    def is_known(day_type):
        return day_type & StudentAttendanceRecord.known

    @staticmethod 
    def is_schoolday(day_type):
        return day_type & StudentAttendanceRecord.school_day

    @staticmethod 
    def is_present(day_type):
        return day_type & StudentAttendanceRecord.present

    def _get_student(self):
        return self.parent()

    def _is_active(self):
        student = self._get_student()
        return student.student_status.active_student

    def _get_index_for_date(self, the_date):
        """
        Return the array index for the morning of the date. The
        afternoon will be the next array element.
        """
        date_ordinal = the_date.toordinal()
        index = 2 * (date_ordinal - self.start_date_ordinal)
        return (int(index))

    def _get_array(self):
        """
        Attendance is stored in the database as a "blob", a string of 
        data. Convert back to an array.
        """
        if (not self.attendance_array):
            expanded = bz2.decompress(self.attendance)
            attendance_str = str(expanded)
            attendance_array = array.array("B")
            attendance_array.fromstring(attendance_str)
            self.attendance_array = attendance_array
        return self.attendance_array

    def _put_array(self):
        """
        Attendance is stored in the database as a "blob", a string of
        data. Convert the attencace_array back into this form,
        compress then store.
        """
        self.attendance = \
            bz2.compress(self.attendance_array.tostring())
        self.put()
        return self.attendance_array

    def extend_array(self, current_array, target_date):
        """
        Create an array of attendance information to append to the
        current array. First, check that the length is not too great to
        protect against wrong date entry. Then, check the last entry to
        determine what the student status ws at the time the current
        array ended. Then check the students status for the dates
        between the prior end date and the current date to set the
        intermediate days appropriately. Finally, set the future days
        to the current status. Return the array.

        All of this complexity is needed because there may have been an
        intervening period such as the school break during which the 
        student's status may have changed one or more times.
        """
        last_index = len(current_array)
        target_index = self._get_index_for_date(target_date)
        delta_index = target_index - last_index
        last_date = date.fromordinal(self.start_date_ordinal + \
                                     int(last_index / 2))
        if (delta_index > self.max_extension_days * 2):
            raise IndexError, \
                  """
                  Too many days since the last date. Check the current date. 
                  Last Date: %s  Current Date: %s  Number of days:%s"
                  """\
                  %(last_date.strftime(),
                    target_date.strftime(),
                    delta_index / 2)
        extend_array_size = delta_index + (self.extension_days * 2)
        #start by building the extension with the initial value based
        #upon the student status which was current at the start date
        initial_value = 0
        if self._is_active():
            initial_value = StudentAttendanceRecord.valid
        extend_array = array.array("B",[initial_value])
        extend_array *= extend_array_size
        current_array.extend(extend_array)
        start_status_changes, end_status_changes = \
            self._get_student().student_status_history.get_intervening_changes(
                                last_date, target_date)
        #if there have been changes then handle in the normal way. For
        #student status the start and end are at the same time so it is
        #only necessary to look at the start
        for change in start_status_changes:
            status = change.info_reference.get()
            active_student = status.active_student
            if (self.student_is_active != active_student):
                self.student_status_changed(
                    status.startDate, active_student)

    def get_start_date(self):
        """
        Return the start date as a datetime.date object
        """
        return date.fromordinal(self.start_date_ordinal)

    def get_period_info(self, start_date, number_of_days):
        """
        The standard method of getting attendance information for
        a period. The information is returned as a list of integers
        with the same encoded values. The information is inclusive
        of the start date. If there are days that are not in the
        array those day are reported as invalid.
        If the number of days is 0 or negative the request is
        meaningless so return None.
        """
        if (number_of_days <= 0):
            return None
        else:
            self._get_array()
            start_index = self._get_index_for_date(start_date)
            end_index = start_index + 2 * number_of_days
            start_pad = []
            #First check to see if we have run completely off
            #the end of the table. If so, then we extend the table to
            #fit.
            if (end_index >= len(self.attendance_array)):   
                #extending the array automatically saves it
                self.extend_array(self.attendance_array, 
                                  start_date + timedelta(number_of_days))
            if (end_index < 0):
                empty = [0]
                empty *= (2 * number_of_days)
                return empty
            #at least part of the period is invalid data
            if (start_index < 0):
                start_pad = [0]
                start_pad *= -start_index
                start_index = 0
            period_values = self.attendance_array[start_index: end_index]
            return start_pad + list(period_values)

    def get_period_info_by_date(self, start_date, end_date):
        """
        Get a list of attendance information for the days start_date
        through end_date (inclusive). The information is returned as
        a list of integers. This function is just a convience function
        for the primary function get_period_info if it is easier to
        use dates rather than a date ordinal and day count. If the
        start and end dates are the same then the information for
        that single date is reutrned.
        """
        day_delta = end_date - start_date
        number_of_days = day_delta.days + 1
        if (number_of_days < 1):
            #invalid request
            return None
        else:
            return self.get_period_info(start_date, 
                                        number_of_days)

    @staticmethod
    def pack_date_info(valid, known, school_day, present):
        """
        Pack a set of boolean parameters describing the day period
        into a single number that can be truncated as a byte
        """
        info = 0
        if present:
            info |= StudentAttendanceRecord.present
            known = True
        if school_day:
            info |= StudentAttendanceRecord.school_day
        if known:
            info |= StudentAttendanceRecord.known
            valid = True
        if valid:
            info |= StudentAttendanceRecord.valid
        return info


    def save_date_info(self, date_ordinal, packed_info_morning,
                       packed_info_afternoon):
        """
        Store at the packed value for a single day at the correct index
        for the date. The date ordinal (not the index) assists in
        efficiency and transparency.

        Data is stored only if the array is already correctly sized. The
        extension of the array is performed during the read to give
        appropriate initial values for the editing function.

        This function does not perform the put to save the data in the 
        database.
        """
        array_index = int(2 * (date_ordinal - self.start_date_ordinal))
        array_size = len(self.attendance_array)
        if (array_index >= 0) and (array_index < array_size):
            self.attendance_array[array_index] = packed_info_morning
            self.attendance_array[array_index +1] = packed_info_afternoon
        return self.attendance_array

    def save_multiple_dates(self, days_list, data_list):
        """
        Save multiple days of attendance data. The days_list is
        simply a list of day ordinals for each day's records in the
        data_list. The data_list contains an already packed record
        for each day period ready for database insertion.
        """
        self._get_array()
        i = 0
        for day in days_list:
            try:
                self.attendance_array = self.save_date_info(
                    date_ordinal = day,
                    packed_info_morning = data_list[i], 
                    packed_info_afternoon = data_list[i+1])
                i += 2
            except IndexError:
                break
        self._put_array()

    #assist functions for commonly used data needs
    def get_summary(self, start_date, end_date):
        """
        Generate summary information about attendance in a form
        commonly used in student records.
        """
        period_data = self.get_period_info_by_date(start_date, end_date)
        periods_present = 0
        school_days = 0
        for day_period in period_data:
            if (day_period & self.valid):
                if (day_period & self.school_day):
                    school_days += 0.5
                    if (day_period & self.known):
                        if (day_period & self.present):
                            periods_present += 1
                    else:
                        #>>>The following is based upon the assumption
                        #that valid school days that are not known were
                        #simply not entered and that the student was
                        #probably there. Not really accurate, but
                        #probably the best guess
                        periods_present += 1
        #each morning and afternoon each count as .5 days
        days_present = round((periods_present / 2.0),1)
        return (school_days, days_present)

    def get_days_attendance(self, day_date):
        """
        Return information about one days attendance that can be easily
        used in school reports.
        """
        info = self.get_period_info(day_date, 1)
        morning = 0
        afternoon = 0
        if (info[0] & self.present):
            morning = 1
        if (info[1] & self.present):
            afternoon = 1
        valid = self.is_valid(info[0])
        schoolday = self.is_schoolday(info[0])
        return (morning, afternoon, valid, schoolday)

    def student_status_changed(self, day_date, is_active):
        """
        When the status changes set all days of the array from the
        day_date, the date of status change, onwards to the appropriate
        value and set the new status in the student registered
        property. If the student is registered then just set the flag
        bit in every byte. If the student is now not registered then
        clear each byte completely because there can be no usable
        information in it.
        If the start date is not already set then this is a first time 
        initialization upon registration. Set the start day first
        so that the index function will work. Note: the start day may 
        be in the future if a student record is created with a future
        registration date.
        """        
        self.student_is_active = is_active
        start_index = self._get_index_for_date(day_date)
        self._get_array()
        for i in xrange(start_index, len(self.attendance_array)):
            if is_active :
                self.attendance_array[i] = StudentAttendanceRecord.valid
            else:
                self.attendance_array[i] = 0
        self._put_array()

#----------------------------------------------------------------------
class StudentTransfer(db.Model):
    """
    A class that contains the information for a student transferring into
    or out of the school. An instance of this class is meant to be
    connected to a "transfer" history for the student. This base class
    contains the reference to the other school or, if not in the database,
    the name, the direction of transfer, and a general info field.
    """
    name = db.StringProperty(required=True)
    db_school = db.ReferenceProperty(School)
    direction = db.StringProperty(required=True, default="In")
    general_info = db.StringProperty(multiline=True)
    classname = "Student Transfer"

    @staticmethod
    def create(name, student, db_school = None):
        if (db_school):
            name = db_school.name()
        return StudentTransfer(name=name, parent=student)

    def __unicode__(self):
        return self.name + " " + self.direction

    def needs_new_record(self, new_record):
        """
        Compare the current instance with the new one. If the direction
        of transfer is different then it is a new instance.
        """
        return (self.direction != new_record.direction)

    def update_current_record(self, new_record):
        """
        Copy the data from the other instance into this one.
        This will be done when the transfer is edited but is not
        a new one.
        """
        needs_save = False
        for i in (
            [self.name,new_record.name],
            [self.db_school, new_record.db_school],
            [self.direction, new_record.direction],
            [self.general_info, new_record.general_info]):
            if (i[0] != i[1]):
                i[0] = i[1]
                needs_save = True
        if needs_save:
            self.put()
        return self

    def in_organization(self, organization_key, requested_action):
        return (self.parent == organization_key)

    @staticmethod
    def update_school_transfer_history(student):
        """
        Special action for school transfer to check values in the
        school transfer fields and perhaps create a StudentTransfer
        record.
        """
        school_name = student.transfer_school_name
        if school_name:
            new_record = StudentTransfer.create(school_name, student)
            new_record.direction = student.transfer_direction
            new_record.general_info = \
                      student.transfer_other_info
            current_record, date = \
                          student.transfer_history.get_current_entry_value_and_date(return_multi=False)
            if (current_record):
                needs_new_record = \
                                 current_record.needs_new_record(new_record)
            else:
                needs_new_record = True
            if (needs_new_record):
                new_record.put()
                student.transfer_history.add_entry(student.transfer_date,
                                                   "", new_record.key())
            else:
                current_record.update_current_record(new_record)

    @staticmethod
    def get_field_names():
        field_names = [("name", "Name")]
        return field_names

    def remove(self):
        self.delete()

#------------------------------------------------------------------
class StudentsClass(db.Model):
    """
    This contains the basic information and connectors to other 
    database objects for a single student's class session. Obects of 
    this class are always direct children of the student so just
    self.parent() will return the associated student
    The parameters are:
    class_session - reference to the class_session
    current_status - reference to the most recent history instance of
            status change
    status_history - a standard history record
    grade_info store - a compressed blob that holds the information 
      about all grades. See the assistant_classes file for the 
      StudentsGradingValue and the StudentsClassInstanceGrades.
    computed_grade - the grade computed from all grading elements prior
           the cutoff date
    assigned_grade - This is normally the same as the computed grade
            but may be set manually. 
    cutoff_date - the last date to be used with grading instances and entered
            grades. This will be a the end of the grading period for intermediate
            periods and after the end of the course for the final grade
    """
    class_session = db.ReferenceProperty(ClassSession, required=True)
    subject = db.ReferenceProperty(Subject, required=True)
    current_status = db.StringProperty(choices = 
                                       SchoolDB.choices.StudentClassStatus)
    start_date = db.DateProperty()
    end_date = db.DateProperty()
    grade_info_store = db.BlobProperty()
    grading_periods = db.ListProperty(db.Key)
    computed_final_grade = db.FloatProperty(default = 0.0)
    assigned_final_grade = db.FloatProperty(default = 0.0)
    classname = "Students Class Record"

    @staticmethod
    def create(student, class_session_ref, subject, start_date):
        students_class_obj = StudentsClass(parent=student,
                                           class_session=class_session_ref,
                                           subject=subject)
        students_class_obj.grade_info_store = \
                          SchoolDB.assistant_classes.StudentsClassInstanceGrades(1).put_data()
        students_class_obj.put()
        if (not start_date):
            start_date = class_session_ref.start_date
        students_class_obj.set_status("Active", start_date)
        students_class_obj.put()
        return students_class_obj
    
    def get_student(self):
        return self.parent()        

    def in_organization(self, organization_key, requested_action):
        return self.get_student().in_organization(organization_key, 
                                                  requested_action)

    def get_class_session(self):
        return self.class_session

    def update_student_cache(self):
        """
        The student record contains a cache of active classes for use
        with general queries. Tell the student to update this cache.
        """

        student = self.parent()
        student.update_active_classes_cache()

    def set_status(self, status, change_date):
        self.current_status = status
        if ((status == "Active") and (not self.start_date)):
            self.start_date = change_date
        elif ((status == "Dropped" or status == "Passed"
              or status == "Transfered" or status == "Failed")
              and (not self.end_date)):
            self.end_date = change_date
        self.put()
        self.update_student_cache()

    def get_grade_info(self):
        """
        Convert the StudentsClassInstanceGrades stored blob into a useable
        object. 
        """
        if (self.grade_info_store):
            grade_info = \
                       SchoolDB.assistant_classes.InformationContainer.get_data(
                           stored_data = self.grade_info_store, 
                           compressed = True, current_version = 1)
        else:
            grade_info = None
        return grade_info

    def put_grade_info(self, grade_info):
        """
        Regenerate the stored blob value from the grade_info object
        """
        self.grade_info_store = grade_info.put_data(compress = True)

    def get_grade(self, grading_instance_key, grading_event_id=1):
        """
        Get a single grade value. Returns None if the grading_instance
        or the event could not be found
        """
        grade_info = self.get_grade_info()
        grade_value = grade_info.get_grade(grading_instance_key, \
                                           grading_event_id)
        return grade_value

    def get_student_and_grades(self, grading_instance_keys):
        """
        Get the information necessary to easily build a grade table 
        for display and edit. Return the student object to allow 
        the calling function to extact any information needed about
        the student. Get the numeric value of the grade for each
        grading instance in the grading instance list. If there is not
        yet a recorded grade return None for that instance. See
        StudentsClassInstanceGrades get_grades for further information
        about the grades return format.
        """
        try:
            student = self.get_student()
            grade_info = self.get_grade_info()
            #These options are set to get the last grade that was entered
            #for this grading instance. To be further thought about...
            grades_dict, grades_list = grade_info.get_grades(
                grading_instance_keys = grading_instance_keys, start_date = None, 
                cutoff_date = None, summary_values = False,
                last_value = True)
        except StandardError:
            student, grades_list = None, None
        return (student, grades_list)

    def set_grade(self, grading_instance_key,
                  grade_value, editor, grading_event_id = 1, 
                  date = date.today(), grade_info = None):
        """
        Add or edit a grade record. Normally the grade info blob will already
        have been extracted (more efficient for multiple grades) so it
        will be used directly. The normal use will be to call this the
        first time to extract the grade info, insert the result, and
        then use the returned grade_info object in the next call. Note:
        this does not the grade info back into the blob nor does it
        perform a database put. These actions must be done explictly by
        the caller.
        """
        if (not grade_info):
            grade_info = self.get_grade_info()
        if (grade_info):
            result = grade_info.set_grade(grading_instance_key, 
                                          grading_event_id, date, grade_value, editor)
        return grade_info

    #def edit_grade(self, new_value, editor, gradeinstance_id = 1):
        #"""
        #Change a grade that already has been set. 
        #"""
        #grade_info = self.get_grade_info()
        #if (grade_info):
            #result = grade_info.edit_grade(grading_instance_key,
                                            #gradeinstance_id,
                                            #new_value, editor)
            #if (result):
                #self.put_grade_info(grade_info)
                #self.put()


    def compute_grade(self, grading_period, save_grade = True):
        """
        Combine all individual grading elements 
        >>>>>>>>>>>>>>>>>> THIS Needs Work!<<<<<<<<<<<<<<<<<<<<<
        """        
        grade_info = self.get_grade_info()
        period_grade = 0.0
        initial_period_grade = 0.0
        start_date = date.min
        cutoff_date = date.max
        if (grade_info):
            element_total_percentage = 0.0
            grades = grade_info.get_grades(None, start_date, cutoff_date)
            for element in self.grade_info(start_date,
                                           cutoff_date):
                element_percentage = element.get_percentage_of_final()
                if (not element.extra_credit):
                    #extra credit is above the normal percentage so do not use
                    #it for scaling
                    element_total_percentage += element_percentage
                (element_grade, initial_grade) = \
                 self.grade_info.get_grade(element)
                period_grade += element_grade * element_percentage
                initial_period_grade += initial_grade * element_percentage
            #rescale because the achievable fraction may be less than 1 if 
            #cutoff date is prior to the end of the class year
            period_grade = period_grade / element_total_percentage
            initial_period_grade = initial_period_grade / \
                                 element_total_percentage
            self.computed_grade = period_grade
            self.initial_computed_grade = initial_period_grade
            if (save_grade):
                self.put()
        return period_grade

    def set_assigned_grade(self, grading_period, assigned_grade,
                           compute_grade = False, use_computed_grade=False):
        """
        Set the reported grade. If use_computed_grade is True then set the 
        assigned grade to the computed grade. If False then the assigned 
        id set directly.
        """
        if (compute_grade):
            computed_grade = self.compute_grade(grading_period, save_grade=False)
            if use_computed_grade:
                assigned_grade = computed_grade
        else:
            computed_grade = 0
        gp_result = self.get_grading_period_result(grading_period)
        if (not gp_result):
            gp_result = GradingPeriodResult(self, grading_period,
                                            computed_grade, assigned_grade)
        else:
            gp_result.set_grades(computed_grade, assigned_grade)
        gp_result.put()

    def get_grading_period_result(self, grading_period):
        """
        Return the grading period result oject that is associated with this
        class record for the specific grading period.
        """
        query = GradingPeriodResult.all()
        query.filter("grading_period = ", grading_period)
        query.filter("student_class_record", self)
        return query.get()

    def get_grading_period_grade(self, grading_period):
        """
        The assigned grade is the "official" grade for the grading period.
        Return that from the appropriate GradingPeriodResult
        instance. Return  None if there is no result for that period.
        """
        result = self.get_grading_period_result(grading_period)
        if result:
            return result.assigned_grade
        else:
            return None

    def get_grading_periods_grades(self):
        """
        Return a dictionary keyed by the grading period of the assigned_grade
        for this class record. This is a way to get the grades for multiple
        grading periods with only a single query.
        """
        grades = {}
        query = GradingPeriodResult.all()
        query.filter("student_class_record", self)
        for gp_result in query:
            grades[gp_result.grading_period] = gp_result.assigned_grade
        return grades

    def remove_record_if_not_yet_used(self):
        """
        Delete this class session if there is no data in it and there
        are no grading period results associated with it. Once grades
        have been entered this will not be performed. Return True if
        the record was deleted, False if it could not be. This is meant
        to allow a record to be cleaned up if the student was assigned
        by accident.
        """
        #check for grading period results
        query = GradingPeriodResult.all()
        query.ancestor(self)
        if (query.count(1) == 0):
            grade_info = self.get_grade_info()
            if (not grade_info.contains_grades()):
                self.set_status("Invalid", date.today())
                self.remove()
                return True
        return False

    def remove(self):
        self.delete()

#----------------------------------------------------------------------
class Student(Person):
    """
    Student is the key class of the entire application -- the primary reason
    for the application. It has numerous parameters to contain or reference
    much of the information about the student. Most of the are histories.
    Several of these histories, such as status or class year have a single
    current value that is also represented individually for indexing and
    selection. These are kept up-to-date programatically.

    The additional parameters are:
    Student ID - string
    Mother - key to person
    Father - key to person
    Guardian - key to person
    Siblings -lisr of keys to other students
    Birth Date - datetime
    Status - current enumerated choice of status
    Status History - history of status
    Class Year - current enumerated choice of class year
    Class Year History- history of enumerated choices of year
    Section - current key for section
    Section History- history of keys to sections
    Classes - list of keys to current classes
    Classes - history of classes (multiple active)
    Other Activities - list of current activities
    Other Activities - history of extracurricular activities (multiple active)
    Awards - history of awards (multiple active)
    Ranking - history of class ranking
    Post Graduation Info - history of information about student after graduation
    """
    student_id = db.StringProperty()
    family = db.ReferenceProperty(Family, collection_name="students_set")
    birthdate = db.DateProperty()
    birth_community = db.ReferenceProperty(Community, 
                                           collection_name="birth_community")
    birth_community_other = db.StringProperty()
    birth_municipality = db.ReferenceProperty(Municipality,
                                              collection_name="birth_municipality")
    birth_municipality_other = db.StringProperty()
    birth_province = db.ReferenceProperty(Province)
    birth_other_country = db.StringProperty()
    elementary_school = db.StringProperty()
    elementary_graduation_date = db.DateProperty()
    elementary_gpa = db.FloatProperty(default=85.0)
    years_in_elementary = db.FloatProperty()
    attendance = db.ReferenceProperty(StudentAttendanceRecord)
    student_status = db.ReferenceProperty(StudentStatus)
    student_status_change_date = db.DateProperty()
    student_status_history = db.ReferenceProperty(History,
                                        collection_name="status_history")
    class_year = db.StringProperty()
    class_year_change_date = db.DateProperty()
    class_year_history = db.ReferenceProperty(History,
                                        collection_name="class_year_history")
    section = db.ReferenceProperty(Section, collection_name="section")
    section_change_date = db.DateProperty()
    section_history = db.ReferenceProperty(History,
                                           collection_name="section_history")
    student_major = db.ReferenceProperty(StudentMajor)
    student_major_change_date = db.DateProperty()
    student_major_history = db.ReferenceProperty(History,
                                            collection_name="major_history")
    ranking = db.StringProperty()
    ranking_change_date = db.DateProperty()
    ranking_history = db.ReferenceProperty(History,
                                           collection_name="ranking_history")
    special_designation = db.ReferenceProperty(SpecialDesignation)
    special_designation_change_date = db.DateProperty()
    special_designation_history = db.ReferenceProperty(History,
                                collection_name="special_designation_history")
    other_activities = db.StringProperty()
    other_activities_history = db.ReferenceProperty(History,
                                collection_name="other_activities_history")
    awards = db.StringProperty()
    awards_history = db.ReferenceProperty(History,
                                          collection_name="awards_history")
    post_graduation = db.StringProperty()
    post_graduation_history = db.ReferenceProperty(History,
                                                   collection_name="post_graduation_history")
    transfer_history = db.ReferenceProperty(History,
                                            collection_name="transfer_history")
    transfer_school_name = db.StringProperty()
    transfer_direction = db.StringProperty()
    transfer_other_info = db.StringProperty()
    transfer_date = db.DateProperty()
    active_class_session_cache = db.ListProperty(db.Key)
    active_class_record_cache = db.ListProperty(db.Key)
    custom_query_function = True
    classname = "Student"

    def post_creation(self, school = None):
        """
        Intialize the student object by creating all history objects
        """
        Person.post_creation(self)
        if (school):
            self.organization = school
        else:
            self.organization = \
                getActiveDatabaseUser().get_active_organization()
        registered_status_type = get_entities_by_name(StudentStatus,
                        "Registered", key_only = True, single_only=True)
        if (self.student_status_change_date):
            startdate = self.student_status_change_date
        else: 
            startdate = date.today()
        self.attendance = StudentAttendanceRecord.create(
            parent_entity = self, start_date = startdate)
        #self.student_status_history = History.create(self,
                                                     #"student_status", True)
        #self.class_year_history = History.create(self, "class_year")
        #self.section_history = History.create(self, "section", True)
        #self.student_major_history = History.create(self,
                                                    #"student_major", True)
        #self.other_activities_history = History.create(self,
                                        #"other_activities", False, True)
        #self.awards_history = History.create(self, "awards", False, True)
        #self.ranking_history = History.create(self, "ranking")
        #self.special_designation_history = History.create(self, 
                                            #"special_designation", True, True)
        #self.transfer_history = History.create(self, 
                                               #"transfer", True, True)
        #self.post_graduation_history = History.create(self, "post_graduation",
                                                      #False, True)
        self.update_my_histories()
        self.put()

    def remove(self):
        if self.family:
            self.family.remove(self)
        fully_delete_entity(self, [History, StudentsClass,
                                   StudentAttendanceRecord,
                                   StudentTransfer])

    def form_data_post_processing(self):
        """
        Perform actions that modify data in the model other than the
        form fields. All of the data from the form has already been
        loaded into the model instance so this processing does not need
        the form at all.
        """
        StudentTransfer.update_school_transfer_history(self)
        self.update_my_histories()
        self.put()

    def age(self, reference_date, age_type_calc = "schoolyear"):
        """
        The age as used by Philippines DepEd is complex formula, not
        merely the difference in years between birthdate and the
        present date. The reference date is that date at which we wish
        the age calculated. Often this will be the current date.
        There are three choices here -- in the school year, at end of the
        school year, and actual. The default is "in school year"
        """
        if (self.birthdate):
            bd = self.birthdate.timetuple()
            rd = reference_date.timetuple()
            #first calculate the effective "current year"
            # if not during the schoolyear then it is just the actual
            #if it is during the school year jun-dec, actual
            #if it is during the schoolyear jan-mar then year-1 to keep same
            #"year' for age computation throughout the school year
            ref_year = rd.tm_year
            if (rd.tm_mon <4):
                ref_year -= 1
            base_age = ref_year - bd.tm_year
            #now adjust from the quarter of the year of the birthdate
            if (bd.tm_mon < 4):
                age = base_age + 0.5
            elif (bd.tm_mon > 9):
                age = base_age - 0.5
            else:
                age = base_age
            if age_type_calc == "endyear":
                age += 0.75
            if age_type_calc == "actual":
                #for out of school -- just real age rounded to 0.5 years
                real_age = reference_date - self.birthdate
                years = real_age.days / 365.0
                #perform rounding
                age = round(years * 2) / 2.0
            return age
        else:
            return 0
    def update_my_histories(self):
        """
        The histories primary fields are changed by form editing. Compare the
        values of those fields with the current entry in the history. If not
        equal then a new event has occured so add another history element.
        """
        history_names = ["student_status", "class_year", "section", 
                         "student_major", "ranking","special_designation"]
        for name in history_names:
            history_create_params = self.get_history_create_info(name)
            _update_history(self, name, history_create_params)

    def assign_class_session(self, class_session, subject, start_date = None):
        """
        Create a StudentsClass object for the student with a specified
        classsession instance. If the startdate is the default "None"
        value use the start date of the class session as the start date.
        If a record for the same class session has already been created
        do not create a new one, just return the one already created.
        """
        q = StudentsClass.all()
        q.filter("class_session =", class_session)
        q.ancestor(self)
        students_class = q.get()
        if (not students_class):
            students_class = StudentsClass.create(self, class_session,
                                                  subject, start_date)
        return students_class

    def update_active_classes_cache(self):
        """
        Build the class sessions and class records caches by scanning all 
        of the students class records for those with the status "Active"
        """
        active_class_records = self.get_class_records_with_status("Active")
        self.active_class_record_cache = \
            map(lambda(record):record.key(), active_class_records)
        #for class_record in active_class_records:
            #active_class_sessions.append(class_record.get_class().key())
        self.active_class_session_cache = \
            map(lambda(record):record.get_class_session().key(), 
                active_class_records)
        self.put()

    def get_active_class_sessions(self):
        """
        Use the active class cache to quickly return the current active
        class sessions.
        """
        if (self.active_class_session_cache == None):
            self.update_active_classes_cache()
        return self.active_class_session_cache

    def get_active_class_records(self):
        """
        Use the active class records cache to quickly return the current
        active student class records
        """
        if (self.get_active_class_records == None):
            self.update_active_classes_cache()
        return self.active_class_record_cache

    def get_class_records_with_status(self, status):
        """
        Get a list of all of the students classes with the status of
        "status", one of the choices in the StudentClassStatus list.
        This can only get classes of one status at a time. Classes
        are ordered by the start date.
        """
        class_records_with_status = []
        all_classes = self.get_all_classes()
        for student_class in all_classes:            
            if (unicode(student_class.current_status) == status):
                class_records_with_status.append(student_class)
        return class_records_with_status

    def get_all_classes(self):
        """
        Get all classes that the student has ever participated in
        no matter what the status.
        """
        q = StudentsClass.all()
        q.ancestor(self)
        return q.fetch(500)

    def get_class_records_by_subject(self, subjectkey_list):
        """
        Return a dictionary of class records in the cache keyed
        by subject key. This supports achievement test recording.
        """
        record_by_subject = {}
        class_sessions = self.get_active_class_sessions()
        class_records = self.get_active_class_records()
        for class_record_key in class_records:
            class_record = db.get(class_record_key)
            class_session = class_record.get_class_session()
            class_session_subject_key = class_session.subject.key()
            for subjectkey in subjectkey_list:
                if (class_session_subject_key == subjectkey):
                    record_by_subject[subjectkey] = class_record.key()
        return record_by_subject

    def get_parents(self):
        if (self.family != None):
            return self.family.get_parents()
        else:
            return []

    def get_missing_fields(self):
        """
        Check the student record for values in the check fields. The
        type of field will determine the means of checking. String
        fields are checked for empty strings, history fields for a
        value in the current field, date field for non-null, and
        parent_or_guardian field through the function get_parents which
        looks for parent records associated with the students family.
        The checked fields are defined in this report code.
        """
        missing_count = 0
        missing_fields = {}
        fields = {"mun":(self.municipality),
                  "bg":(self.community),
                  "bd":(self.birthdate),
                  "ed":(self.student_status_change_date),
                  "cy":(self.class_year_change_date),
                  "sd":(self.section_change_date),
                  "es":(self.elementary_school),
                  "eg":(self.elementary_graduation_date),
                  "ega":(self.elementary_gpa),
                  "ye":(self.years_in_elementary)}  
        fields["bp"] = (self.birth_province or 
                        self.birth_other_country)
        fields["bm"] = (self.birth_municipality or
                        self.birth_municipality_other)
        fields["bb"] = (self.birth_community or 
                        self.birth_community_other)
        family, parents = (self.family, 
                           (len(self.get_parents()) > 0))
        fields["pg"] = parents
        for field in fields.iteritems():
            #change to boolean with true meaning that the field does
            #has data
            if (not field[1]):
                missing_fields[field[0]] = False
                missing_count += 1
            else:
                missing_fields[field[0]] = True
        return missing_fields, missing_count

    @staticmethod
    def get_history_choice_list(attribute_name):
        """
        Histories may have a free form text input or a limited range of
        choices depending upon the entry. This will return the list to
        be used if it is supposed to be a choice and None otherwise.
        """
        history_choice_list = None
        if (attribute_name == "student_status"):
            history_choice_list = create_choice_array_from_class(
                StudentStatus, getActiveDatabaseUser().get_active_organization())
        elif (attribute_name == "class_year"):
            history_choice_list = SchoolDB.choices.ClassYearNames
        elif (attribute_name == "section"):
            history_choice_list = create_choice_array_from_class(
                Section, getActiveDatabaseUser().get_active_organization())
        elif (attribute_name == "student_major"):
            history_choice_list = create_choice_array_from_class(
                StudentMajor, getActiveDatabaseUser().get_active_organization())
        elif (attribute_name == "special_designation"):
            history_choice_list = create_choice_array_from_class(
                SpecialDesignation, 
                getActiveDatabaseUser().get_active_organization())
        return history_choice_list

    @staticmethod
    def get_history_form_info(attribute_name):
        """
        Return a tuple with a boolean for the type of information that the
        field contains and the title that should be used with an form of this
        attribute.
        Return True if the value is limited and entered from a list of
        choices, False for other types that just have a freeform text field.
        """
        type_mapping = {"student_status":("Choice", "Student Status"), 
                        "class_year":("Choice", "Class Year"),
                        "section":("Choice", "Section"),
                        "student_major":("Choice", "Student Major"),
                        "special_designation":("Choice","Special Designation"),
                        "other_activities":("Text", "Other Activities"),
                        "ranking":("Text", "Ranking"),
                        "transfer":("Object", "School Transfer")}
        return type_mapping.get(attribute_name, None)

    def get_history_create_info(self, attribute_name):
        """
        Return a tuple of the parameters required for the history
        object creation. These are used as direct arguments in the
        history create function and are in the order (self,
        attributename, is_reference, multiactive, is_private_reference)
        """
        hist_mapping = {"student_status":(self, "student_status", True, 
                                          False, False), 
                "class_year":(self, "class_year", False, False, False),
                "section":(self, "section", True, False, False, ),
                "student_major":(self, "student_major", True, False, False, ),
                "special_designation":(self, "special_designation", 
                                       True, True, False),
                "other_activities":(self,
                                "other_activities", False, True, False),
                "ranking":(self, "ranking", False, False, False, ),
                "transfer":(self, "transfer", True, True, False)}
        return hist_mapping.get(attribute_name, None)

    @staticmethod
    def custom_query(organization, leading_value, value_dict):
        """
        Get a list of students from a school selected by school_key with
        optional class_year, section, and leading_values. A list of 
        tuples (name, section, class_year, gender)
        """
        descriptor = SchoolDB.assistant_classes.QueryDescriptor()
        filters = []
        if value_dict.has_key("filter-class_year"):
            filters.append("class_year", value_dict["filter-class_year"])
        if value_dict.has_key("filter-student_status"):
            filters.append("student_status",
                           value_dict["filter-student_status"])
        if value_dict.has_key("filterkey-section"):
            filters.append("section", value_dict["filterkey-section"])
        descriptor.set("filters", filters)
        sort_params = ["last_name", "first_name"]
        if value_dict.has_key("sort_by_gender"):
            sort_params.append("-gender")
        descriptor.set("sort_order", sort_params)
        descriptor.set("leading_value", "last_name")
        q = SchoolDB.assistant_classes.QueryMaker(Student, descriptor)
        student_list = q.get_objects()
        students = []
        return_string = ""
        for student in student_list:
            key = student.key()
            name = student.full_name_lastname_first()
            section = unicode(student.section)
            class_year = student.class_year
            gender = student.gender[1]
            string = name + "|" + str(key) +"\n"
            return_string = return_string + string
            students.append((key, name, section, class_year, gender))
        return students, return_string

    def __unicode__(self):
        """
        Students do not use titles so assure a title will not
        be included in the name.
        """
        name = self.full_name(False)
        return name

    @staticmethod
    def get_field_names():
        field_names = Person.get_field_names()
        field_names.extend([("birthdate", "Birthdate"),
                            ("student_status", "Student Status"),
                            ("student_status_change_date", "Student Status Change Date"),
                            ("class_year", "Class Year"),
                            ("class_year_change_date", "Class Year Change Date"),
                            ("section", "Section"),
                            ("section_change_date", "Section Change Date"),
                            ("student_major", "Student Major"),
                            ("student_major_change_date", "Student Major Change Date"),
                            ("special_designation", "Special Designation"),
                            ("special_designation_change_date", 
                             "Special Designation Change Date"),
                            ("birth_prrovince", "Birth Province"),
                            ("birth_municipality", "Birth Municipality"),
                            ("birth_community", "Birth Barangay"),
                            ("elementary_school", "Elementary School"),
                            ("elementary_gpa", "Elementary GPA"),
                            ("years_in_elementary", "Years in Elementary")])
        return field_names

#----------------------------------------------------------------------

class UserType(db.Model):
    """
    A class that defines the permissions for tasks for a particular
    type of user. Example: "student" that can only perform
    simple actions to aid in data entry
    Virtually all of the data is maintained in python dictionaries that are
    pickled into a single element, the data vault.
    """
    name = db.StringProperty()
    permissions_vault = db.BlobProperty()
    master_user = db.BooleanProperty(default=False)
    max_time_between_accesses = db.IntegerProperty(default=120)
    home_page= db.StringProperty()
    maint_page= db.StringProperty()
    custom_query_function = False
    active_permissions_vault = None
    classname = "User Type"

    def __unicode__(self):
        return self.name

    def prepare_to_save(self):
        """
        Prepare the user type instance for saving but do not perform
        the put.
        """
        self.permissions_vault = \
            self.active_permissions_vault.prepare_to_save()

    def post_creation(self):
        """
        setup permissions vault and put result
        """
        self.prepare_to_save()
        self.put()

    def form_data_post_processing(self):
        """
        A default action that does nothing
        """

    def prepare_for_use(self):
        """
        Set the active_permissions_vault the ready to use version from
        the data that is stored in the permissions_vault field
        """
        self.active_permissions_vault = \
            UserPermissionsVault.prepare_for_use(self.permissions_vault)

    #The next two functions are the real purpose of the user type
    #object. They provide support for security functions based upon the
    #user
    def legal_url(self, url_name):
        """
        Check against record of allowed urls. If the current user is
        admin shortcircuit the whoe thing to prevent problems with database
        damage.
        """
        if users.is_current_user_admin():
            return True
        if (self.active_permissions_vault == None):
            UserType.prepare_for_use(self)
        return self.active_permissions_vault.legal_url(url_name)

    def action_ok(self, action_name, target_name, target_instance = None):
        """
        Check action, target_name (either a class or a special action such as
        set attendance or create a report) and the instance that the action
        will be perfomred upon.
        """
        if users.is_current_user_admin():
            return True
        if (self.active_permissions_vault == None):
            UserType.prepare_for_use(self)
        return self.active_permissions_vault.action_ok(action_name,
                                                       target_name, target_instance)

    @staticmethod    
    def custom_query(organization, leading_value, value_dict):
        return custom_query(organization, leading_value, value_dict,
                            UserType)

    @staticmethod
    def get_field_names():
        field_names = [("name", "Name")]
        return field_names

    def remove(self):
        self.delete()

#The next two classes are not data models in themselves but rather provide
#support for the user model class

class TargetTypePermission():
    """
    A "packed" integer that contains all of the perimissions data for a
    single class for a single user. The data is in two sections. The
    first section controls local (in the user's organiztion) actions.
    The second section controls actions outside of the users
    organization. Each section has three different permission
    parameters: delete, edit, and view. Each parameter has a bit when
    set indicates permission for that action. In addition, there is a
    second bit that when set indicates that there are special
    conditions that apply so a further special function must be called.
    The data is encoded in an integer,with the values indexed by offsets.
    """
    def __init__(self, initial_value = 0, is_class = True):
        self.is_class = is_class
        self.packed_value = 0
        if initial_value:
            self.load_permissions(initial_value)

    def get_name_bit_mask(self, name):
        """
        The integer value for the single bit that is set with that name
        """
        name_value_bit = {"View":1, "View_special":2,
                          "Edit":16, "Edit_special":32,
                          "Delete":64, "Delete_special":128,
                          "View_nonorg":256, "View_nonorg_special":512,
                          "Edit_nonorg":4096, "Edit_nonorg_special":8292,
                          "Delete_nonorg":65536, "Delete_nonorg_special":131072}
        return name_value_bit.get(name, 0)

    def get_bit(self, name):
        #test only as boolean -- actual value int value will be
        #different for each
        return self.packed_value & self.get_name_bit_mask(name)

    def set_bit(self, name, value):
        if (value):
            self.packed_value |= self.get_name_bit_mask(name)
        else:
            self.packed_value &= ~self.get_name_bit_mask(name)

    def load_permissions(self,permissions):
        """
        Load values from input sequences. Two sequences, first for nonorg,
        second for standard inside org This is used only during creation
        or edit
        """
        self.set_bit("View", permissions[1][2][1])
        self.set_bit("View_special", permissions[1][2][0])
        self.set_bit("Edit", permissions[1][1][1])
        self.set_bit("Edit_special", permissions[1][1][0])
        self.set_bit("Delete", permissions[1][0][1])
        self.set_bit("Delete_special", permissions[1][0][0])
        self.set_bit("View_nonorg", permissions[0][2][1])
        self.set_bit("View_nonorg_special", permissions[0][2][0])
        self.set_bit("Edit_nonorg", permissions[0][1][1])
        self.set_bit("Edit_nonorg_special", permissions[0][1][0])
        self.set_bit("Delete_nonorg", permissions[0][0][1])
        self.set_bit("Delete_nonorg_special", permissions[0][0][0])

    def is_legal(self, action, target_in_organization):
        if (not target_in_organization):
            action += "_nonorg"
        return (self.get_bit(action) != 0)

    def needs_special_action(self, action, target_in_organization):
        action += "_special"
        return self.is_legal(action, target_in_organization)

class UserPermissionsVault():
    """
    A single instance of this class defines all permissions for a single
    type of user. It contains three dictionaries, each for a specific
    portion of the validation. Processing, loading, and unloading the
    object once inside the user type database entity is the
    responsibility of the data entity class. Action_names are:
    "view", "edit", "delete"
    >>>This requires further work to handle special actions<<<
    """
    def __init__(self, url_default_permission, url_permissions, 
                 target_default_permission, target_permissions):
        self.url_default_permission = url_default_permission
        self.url_permissions = url_permissions
        self.target_default_permission = target_default_permission
        self.target_permissions = target_permissions

    def legal_url(self, url_name):
        """
        This is the first test called during user validation. If not legal
        then no other tests or actions except some sort of rejection
        needs to be done.
        """
        url_split = url_name.split('/')
        if (len(url_split) > 1):
            base_url = url_split[1]
        else:
            base_url = url_split[0]
        return self.url_permissions.get(base_url, self.url_default_permission)

    def action_ok(self, action_name, target_name, target_instance = None):
        """
        This could be called twice, first from early check when only the
        object type is known to provide a first level filter and then again
        within the form after the object instance is known.
        """
        target_permissions = self.target_permissions.get(target_name, 
                                                         self.target_default_permission)
        if (target_permissions.is_class and target_instance):
            target_in_organization = target_instance.in_organization(
                getActiveDatabaseUser().get_active_organization_key(), 
                action_name)
        else:
            #should be elif target_name.in_organization or something similar
            # >>> to be done <<<
            target_in_organization = True
        #map other actions that will change an object to "Edit" for purposes
        #of table lookup
        if ((action_name == "Save") or (action_name == "Create")):
            action_name = "Edit"
        return target_permissions.is_legal(action_name,
                                           target_in_organization)
    def prepare_to_save(self):
        data = pickle.dumps(self)
        return bz2.compress(data)

    @staticmethod
    def prepare_for_use(saved_instance):
        data = bz2.decompress(saved_instance)
        return pickle.loads(data)


#----------------------------------------------------------------------

class DatabaseUser(db.Model):
    """
    A class that defines unique record for a database user. Anyone 
    that wishes to work with the Student Database in any way must
    have a record of this type which includes the google apps user.
    In addition, there should be an instance of class Person or higher
    in the database associated with the user.
    This is the critical class for security because the google user account
    and the type of user (thus, the permissions of the user) are associated.
    These records should be editible only by one or two people in any 
    organization and then only for users in their organization.
    """
    person = db.Reference(Person)
    first_name = db.StringProperty()
    middle_name = db.StringProperty()
    last_name = db.StringProperty()
    name = db.StringProperty()
    email = db.StringProperty(required=True)
    contact_email = db.StringProperty()
    user = db.UserProperty()
    phdb_password = db.StringProperty()
    organization = db.ReferenceProperty(Organization, required=True)
    user_type = db.ReferenceProperty(UserType)
    guidance_counselor = db.BooleanProperty(default=False)
    last_access_time = db.DateTimeProperty(auto_now=True)
    usage_time = db.IntegerProperty(default=0)
    preferences = db.BlobProperty()
    interesting_instances = db.ListProperty(db.Key)
    other_information = db.StringProperty(multiline=True)
    custom_query_function = False
    classname = "Database User"

    def format(self, format_name):
        """
        An inelegant solution but simple
        """
        if (format_name == "last_name_only"):
            return unicode(self.last_name)
        else:
            return unicode(self)

    def __unicode__(self):
        return self.last_name + ", " + self.first_name

    def post_creation(self):
        """
        """
        self.user = users.User(self.email)
        self.name = unicode(self)
        self.preferences=pickle.dumps({})
        self.usage = 0
        self.put()

    def form_data_post_processing(self):
        """
        If the users organization has not already been set then
        set it to the current school -- i.e. the school of the
        person creating the user. This assures that a school admin
        can only create users for her school.
        """
        if (self.organization == None):
            self.organization = \
                getActiveDatabaseUser().get_active_organization()
            self.put()

    def in_organization(self, organization_key, requested_action):
        return (self.organization.key() == organization_key)

    def check_time_since_last_access(self):
        """
        Get the time difference between now and the last access.
        Compare this with the max difference allowable for the
        user type and return the time difference and the result 
        of the comparison.
        """
        timedelta_since_last = datetime.now() - self.last_access_time
        minutes_since_last = int(timedelta_since_last.seconds / 60)
        too_long = (minutes_since_last > 
                    self.user_type.max_time_between_accesses)
        if (timedelta_since_last.seconds < 300):
            self.usage_time += timedelta_since_last.seconds
        return (too_long, minutes_since_last)

    def update_last_access_time(self):
        """
        Set the access time to now.
        """
        self.put()
        return self.last_access_time

    def update_object_list(self, args_dict, focus_class, change_instance_key):
        """
        Get a list of interesting instances of a specified class.
        This is an interface function for ajax, etc.
        """
        action = args_dict.get("action","get")
        if (action != "get" and change_instance_key):
            changed = False
            count = self.interesting_instances.count(change_instance_key)
            if ((action == "remove") and count):
                self.interesting_instances.remove(change_instance_key)
                changed = True
            elif ((action == "add") and not count):
                self.interesting_instances.append(change_instance_key)
                changed = True
            if changed:
                self.put()               
        return self.get_interesting_instances_class_list(focus_class)

    def get_interesting_instances_class_list(self, model_class):
        """
        Get an unsorted list of instances from the interesting
        instances list of a specified class.
        """
        filtered_list = []
        #We will need all instances to determine type so fetch all at once
        instances = db.get(self.interesting_instances)
        for i in instances:
            #If no exception then key is of right type.
            if (i and (i.class_name() == model_class.class_name())):
                filtered_list.append(i)
        return filtered_list

    def update_interesting_instances(self, instances_list, model_class):
        """
        Change the list to reflect the current list for the specified
        model class. Instance performs put only if there was a change.
        """
        current_instances = self.get_interesting_instances_class_list(
            model_class)
        #perform checking so that we do not perform the expensive update
        #of the database record if unnecessary.
        list_changed = (len(current_instances) != len(instances_list))
        if (not list_changed):
            #lists are same length, now check contents 
            for i in current_instances:
                try:
                    instances_list.find(i)
                    #there is not a match so the lists are different
                except ValueError:
                    list_changed = True
                    break
        if (list_changed):
            #There may be instances of different classes so we must work
            # only with this class. First remove all that were there
            # and then add all from new list.
            try:
                for i in current_instances:
                    self.interesting_instances.remove(i)
                for i in instances_list:
                    #confirm that the new instance is valid
                    try:
                        if (i.kind == model_class):
                            self.interesting_instances.append(i)
                    except db.Error:
                        pass
            except ValueError:
                #for some reason it wasn't found -- never should happen
                pass
            self.put()
        return list_changed

    def get_preference(self, preferenceName):
        """
        Get the value of the preference associated with the name. This is a
        safe action because it does not change anything.
        """
        #temporary fix for current users. Take out after all have been 
        #updated.
        if (self.preferences == None):
            self.post_creation()
        preference_dict = pickle.loads(self.preferences)
        return preference_dict.get(preferenceName, "")


    def _set_preference(self, name, value):
        """
        Set a single preference value. To prevent an attack by
        setting too many or too long preferences a maximum of
        50 preferences will be allowed. Each preference can 
        only be a maximum of 500 bytes.
        """
        preference_dict = pickle.loads(self.preferences)
        if (name != ""):
            if (len(preference_dict) < 51):
                preference_dict[name] = value[:500]
                self.preferences = pickle.dumps(preference_dict)
                self.put()

    def _remove_preference(self, name):
        """
        Set a single preference value. To prevent an attack by
        setting too many or too long preferences. A maximum of
        50 preferences will be allowed. Each preference can 
        only be a maximum of 500 bytes.
        """
        preference_dict = pickle.loads(self.preferences)
        if (name != ""):
            preference_dict.pop(name)
            self.preferences = pickle.dumps(preference_dict)
            self.put()

    #The following wrappers are for security. They use the current
    #user so only that record can be read
    @staticmethod
    def set_single_value(unused, value_name, value):
        #set user preference value for the active user
        activeDbUser = getActiveDatabaseUser()
        dbuser = activeDbUser.get_active_user()
        dbuser._set_preference(value_name,value)

    @staticmethod
    def get_single_value(unused, value_name):
        #get user preference value for the active user
        activeDbUser = getActiveDatabaseUser()
        dbuser = activeDbUser.get_active_user()
        return dbuser.get_preference(value_name)

    @staticmethod
    def remove_single_value(unused, value_name):
        #get user preference value for the active user
        activeDbUser = getActiveDatabaseUser()
        dbuser = activeDbUser.get_active_user()
        return dbuser._remove_preference(value_name)

    @staticmethod    
    def custom_query(organization, leading_value, value_dict):
        return custom_query(organization, leading_value, value_dict,
                            DatabaseUser)

    @staticmethod
    def get_field_names():
        field_names = [("name", "Name")]
        return field_names

    def remove(self):
        self.delete()

#----------------------------------------------------------------------

class GradingPeriodResult(db.Model):
    """
    A simple class to keep summary information about a students grades
    in a class for a specific period. This is a child of a student with
    references to the student class record and the class session. This
    is meant to be kept in long term records so that the students class
    record may be deleted.
    """
    computed_grade = db.FloatProperty()
    assigned_grade = db.FloatProperty()
    grading_period = db.ReferenceProperty(GradingPeriod, required=True)
    class_session = db.ReferenceProperty(ClassSession, required=True)
    #the following values are for the assigned grade edit tracking
    initial_assigned_date = db.DateProperty()
    initial_assigned_grade = db.FloatProperty()
    initial_editor = db.ReferenceProperty(DatabaseUser, 
                                          collection_name="initial_editor")
    change_date = db.DateProperty()
    last_editor = db.ReferenceProperty(DatabaseUser,
                                       collection_name="last_editor")


    @staticmethod
    def create(class_session, grading_period, student, assigned_grade = None,
               computed_grade = None):
        gp_result = GradingPeriodResult(parent = student, 
                                        computed_grade = computed_grade, 
                                        assigned_grade = assigned_grade,
                                        grading_period = grading_period, 
                                        class_session = class_session,
                                        initial_editor = getActiveDatabaseUser().get_active_user(),
                                        last_editor = getActiveDatabaseUser().get_active_user(),
                                        initial_assigned_date = date.today(),
                                        initial_assigned_grade = assigned_grade)
        gp_result.put()


    def set_grade(self, assigned_grade = None, computed_grade = None, 
                  action_date = date.today(), 
                  editor = None):
        """
        Set or change the grade. Normally this will be called to set the
        assigned grade to a new value so the change history tracking
        will be updated.
        """
        if not editor:
            editor = getActiveDatabaseUser().get_active_user()
        if computed_grade:
            self.computed_grade = computed_grade
        if assigned_grade:
            if (self.assigned_grade and 
                (assigned_grade != self.assigned_grade)):
                #this is a change so log the history info
                self.change_date = action_date
                self.last_editor = editor
            elif (not self.assigned_grade):
                self.initial_assigned_grade = assigned_grade
                self.initial_assigned_date = action_date
                self.initial_editor = editor
            if (self.assigned_grade != assigned_grade):
                #there was a change
                self.assigned_grade = assigned_grade
                self.put()

    def assigned_grade_is_set(self):
        return (self.assigned_grade != None)

    def assigned_grade_has_been_changed(self):
        return (self.change_date != None)

    def compute_grade(self, copy_to_assigned=False):
        """
        Perform actions necessary to coumpute the grade and set the
        computed value. Copy this to the assigned grade if
        copy_to_assigned is true. Do not record as an editing
        """
        #TBD do compute action
        if (copy_to_assigned):
            self.assigned_grade = self.computed_grade

    @staticmethod
    def get_results_for_class_session(class_session):
        if class_session:
            return class_session.gradingperiodresult_set.fetch(500)
        else:
            return []

#----------------------------------------------------------------------

class VersionedTextManager(History):
    """
    A utility class for text information such as help pages that may be
    updated to a different version. It is an extension of a history
    class object to maintain prior history with a few other fields. It
    maintains full copies rather than deltas because most items are
    expected to be rather short, infrequently changed, and with a large
    amount changed when a change is made. The actual pages are of class
    VersionedText. The title and template fields help support Django
    form actions.

    Note: There is one manager per "page" that is versioned. For
    example, if there is a unique page of help text per form page then
    there will be the same number of VersionedTextManager instances.
    For a manual this may, for example, be broken up by chapter. The
    revision number here is updated from the version text form. If it
    is higher than the current pages revision number a new revision
    page will be created.
    """
    name = db.StringProperty(required = True)
    title = db.StringProperty(multiline=True)
    help_formatted = db.BooleanProperty(default = True)
    dialog_template = db.StringProperty()
    page_template = db.StringProperty()
    revision_number = db.StringProperty(required=True, default = "0.1")
    general_info = db.StringProperty(multiline=True)
    classname = "Text Page Manager"

    @staticmethod
    def create(name, title = "", template = "", general_info = ""):
        """
        Define a create method to assure that all of the parent class
        History variables are set correctly. Use this always to create
        this object. The further parameters for create may allow all
        values to be set prior to the initial 'put'
        """
        manager = VersionedTextManager(parent = None, 
                            attribute_name = "versioned_text",
                            is_reference = True, multi_active = False, 
                            private_reference_object=True, name = name)
        manager.entries_list = []
        manager.name = name
        manager.put_history()
        manager.put_history()
        return manager


    def post_creation(self):
        """
        Create the initial page with revision 0.1
        """
        new_page = VersionedText(revision_number = self.revision_number,
                        content = "Empty page",
                        author = getActiveDatabaseUser().get_active_user(),
                        comment = "Initial revision")
        new_page.put()
        self.add_entry(date.today(), "Initial revision", new_page)

    def form_data_post_processing(self):
        """
        Create a new text revision if new number.
        Open editor window with page to edit.
        """
        pass
        #current_page = self.get_current_version()
        #if (self.revision_number > current_page.revision_number):
            #edit_page = \
                        #self.create_new_revision(revision_number, 
                            #getActiveDatabaseUser().get_active_user())

    def get_current_version(self):
        current_version, current_date = \
                       self.get_current_entry_value_and_date()
        return current_version

    def get_version(self, target_revision = "current", 
                    return_default_if_not_found = True):
        """
        Search the unique versions of the page for one with the 
        target revision number. If the target revision cannot be
        found and 
        """
        if (target_revision == "current"):
            selected_version =  self.get_current_version()
        else:
            selected_version = None
            for entry in self.get_entries_list():
                version = entry.get_info_reference()
                if (version and 
                    (version.revision_number == target_revision)):
                    selected_version = version
            #page not found
            if ((not selected_version) and return_default_if_not_found):
                selected_version = self.get_current_version()
        return selected_version

    def create_new_revision(self, revision_number, author):
        """
        Standard editing action is to create new version and then edit
        into it. This allows an easy edit, save, test cycle while
        working on a revision of the page.
        """
        new_page = VersionedText(revision_number = revision_number,
                                 author = author)
        new_page.content = self.get_current_version().content
        new_page.put()
        self.add_entry(start_date = date.today(), info_str="",
                       info_instance = new_page)
        return new_page

    def __unicode__(self):
        return self.name

    @staticmethod
    def get_field_names():
        field_names = [("name", "Name"), ("title", "Title"),
                       ("dialog_template", "Dialog Template"),
                       ("page_template", "Page Template"),
                       ("revision_number", "Revision Number")]
        return field_names

    def get_raw_text(self):
        text_page = self.get_current_version()
        return unicode(text_page)

    def get_processed_text(self, template_type = "Dialog", 
                           revision_number = "current", test_text = None):
        """
        This is the key function for this class. The text is normally
        from the current versioned text page of this manager. If the
        text_revision_number is specified then that text page will be
        used instead. If test_text is specified then that will be used
        instead of the current text so that an edit of the text can be
        tested before saving. If a template is defined for the
        appropriate template type then the text is processed by django
        with the appropriate template. The resulting text is returned as
        a single string.
        """
        raw_text = ""
        balloon_help_dict = {}
        if (test_text):
            raw_text = test_text
            text_version = "Test"
            text_date = date.today()
        else:
            text_version = self.get_version(revision_number)
            if (self.help_formatted):
                # parse page to parts for dialog and for ballon help
                (help_dialog_text, balloon_help_dict) = \
                 text_version.parse_help_formatted_page()
            else:
                help_dialog_text = unicode(text_version)
            revision_number = text_version.revision_number
            text_date = text_version.last_edit_date
        if (template_type == "Page"):
            template_name = self.page_template
        else:
            template_name = self.dialog_template
        if template_name:
            template = django.template.loader.get_template(template_name)
            if template :
                #set all of the text as "content". This makes the 
                #template just a wrapper round a single block
                params= {"content":help_dialog_text, "title":self.title,
                         "version":revision_number, "text_date":text_date}
                processed_text = template.render(
                    django.template.Context(params))
                return processed_text, balloon_help_dict
        else:
            return help_dialog_text, balloon_help_dict      

    def remove(self, remove_references=True):
        History.remove(True)

#----------------------------------------------------------------------

class VersionedText(db.Model):
    """
    A utility class that contains block of text with a version field,
    authors_name, and comments field similar to any version control
    system. It is meant for help pages, etc and is designed to be
    managed by a VersionedTextManager. A new VersionedText instance should be
    created for each instance.
    """
    author = db.ReferenceProperty(DatabaseUser, required=True)
    revision_number = db.StringProperty(required=True)
    last_edit_date = db.DateProperty(date.today())
    comment = db.StringProperty(multiline = True)
    content = db.TextProperty(required=True)

    def form_data_post_processing(self):
        pass

    def post_creation(self):
        pass

    def __unicode__(self):
        return unicode(self.content)

    def get_author_info(self):
        person_name = unicode(self.author.person)
        user_email = self.author.email()
        return(person_name, user_email)

    def remove(self):
        self.delete()

    def parse_help_formatted_page(self):
        """
        This is a secific function for use with a page constructed for 
        help for a web page. The page has two sections, a freeform text
        section and a dictionary keyed by DOM object ids of help balloon
        text. This function parses the page and returns both parts.
        """
        parse_re = re.compile(r'(.*)(?=<\!--<<).*(?={)(.*)(?=-->)',re.DOTALL)
        parts = parse_re.match(self.content)
        if (parts):
            help_dialog_text = parts.group(1)
            balloon_dict_text = parts.group(2)
            cleaned_text = balloon_dict_text.replace("\r\n"," ")
            balloon_dict = eval(cleaned_text)
        else:
            #re failed so something wrong with text
            help_dialog_text = ""
            balloon_dict = {}
        return (help_dialog_text, balloon_dict)

#----------------------------------------------------------------------

class ActiveDatabaseUser:
    """
    The class for a single object that contains information about the user
    performing the current operation. It is derived from the google login 
    user. It is used in several places to determine permissions or the organization
    to be used in an operation. The organization is especialy critical in
    filtering access and display of the various instances of data. Normally it
    is fixed by the identity of the user but it may be set to a different
    organization by a database user of a class that has permission to do so.
    """

    classname = "Text Page"

    def __init__(self, current_user):
        """
        Set the key parameters from the DatabaseUser instance current user.
        Cache some values for ready access or change if permitted
        """
        self._active_user = current_user
        self._active_organization = current_user.organization

    def get_active_organization(self):
        """
        Return a reference to the active organization. This may have been
        changed by a privileged user
        """
        return self._active_organization

    def get_active_organization_key(self):
        """
        Return the key of the active organization. A trivial extension
        just as a convienence function.
        """
        return self._active_organization.key()

    def get_active_organization_name(self):
        """
        Use the organizations unicode function to return a name for display
        """
        return unicode(self._active_organization)

    def get_active_organization_type(self):
        """
        Return the classname of the organization. This is the type of
        the organization
        """
        return self._active_organization.classname

    def get_active_user(self):
        """
        Return a reference to the active user. This cannot be changed.
        """
        return self._active_user

    def get_active_user_name(self):
        """
        Return a reference to the active user. This cannot be changed.
        """
        return unicode(self._active_user)

    def get_active_person(self):
        """
        Each database user should have an associated instance of Person in the
        database.  Return a reference to that user.
        """
        person = self._active_user.person
        return person

    def get_active_user_type(self):
        return self._active_user.user_type

    def get_active_user_type_name(self):
        return unicode(self._active_user.user_type)

    def set_active_organization(self, new_organization):
        """
        Check the permissions of the active user to determine if this is
        allowed. If so, confirm that the new organization is valid, then
        change. Return true upon success else false.
        """
        user_type = self._active_user.user_type
        successful = False
        if (user_type.change_active_organization):
            try:
                if (new_organization.kind() == "Organization"):
                    self._active_organization = new_organization
                    successful = True
            except:
                pass
        return successful

######### Utility Functions not associated with a single class for #######
######### internal use #######
def _update_history(instance, value_name, create_params):
    """
    The history primary fields are changed by form editing. Compare the
    values of those fields with the current entry in the history. If not equal
    then a new event has occured so update the history. If no history has yet
    been created, create one and store the value in it. Unfortunately I have not yet found a way in python to set a value selected by name, so the hack of the history field is used to allow writes of a new history into the history element.
    """
    date_name = value_name + "_change_date"
    history_name = value_name + "_history"
    value = \
        instance.properties()[value_name].get_value_for_datastore(instance)
    change_datetime = \
        instance.properties()[date_name].get_value_for_datastore(instance)
    if (value and change_datetime):
        #if no value and time nothing can be set in a history
        change_date = change_datetime.date()
        history = \
            instance.properties()[history_name].get_value_for_datastore(
                instance)
        #confirm that there is a history and create one if not
        key = instance.properties()[history_name].get_value_for_datastore(
                                                            instance)
        if (key):
            history = db.get(key)
        else:
            history = History.create(ownerref = create_params[0],
                              attributename = create_params[1],
                              isreference = create_params[2], 
                              multiactive = create_params[3],
                              isprivate_reference_object = create_params[4])
            instance.__setattr__(history_name,history)
            instance.put()
        needs_update = history.is_empty()
        if not needs_update:
            history_value, history_date = \
                         history.get_current_entry_value_and_date(
                             key_only=True)
            needs_update = ((value != history_value) or 
                             (change_date != history_date))
        if needs_update:
            _perform_history_update(instance, history, 
                                    change_date, value)        
        
                                  #the_date, the_value)        

def _perform_history_update(instance, history, the_date, the_value):
    if (history.is_reference):
        history.add_or_change_entry_if_changed(the_date, "", the_value)
    else:
        history.add_or_change_entry_if_changed(the_date,the_value)
    # The value and date in the instance may not be the current
    # value if the edited entry is an older one. Use the sync to 
    # insure that they are correct
    _sync_history_fields(instance, history)

def _sync_history_fields(instance, history):
    """
    Update the current_value and last time of change with the history 
    object.
    """
    instance.value, instance.date_of_change = \
            history.get_current_entry_value_and_date()

######### Utility Functions not associated with a single class for #######
######### external use. #######
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
        current_year = SchoolYear.school_year_for_date()
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
    return target_string

def is_school_day(date, section = None):
    """
    Get the school day appropriate for section. Return two
    """
    school_day = (True, True)
    day = SchoolDay.get_school_day(date, section)
    if (day):
        if ((day.day_type == "School Day") or
            (day.day_type == "Makeup Full Day")):
            school_day = (True,True)
        elif (day.day_type == "Makeup Half Day Morning"):
            school_day = (True, False)
        elif (day.day_type == "Makeup Half Day Afternoon"):
            school_day = (False, True)
        else:
            school_day = (False, False)
        day_type = day.day_type
    else:
        #no day, just fake it. This probably should be expanded with
        #school year
        if (date.weekday() > 4):
            school_day = (False, False)
            day_type = "Unknown"
    return school_day[0], school_day[1], day_type


def create_choice_array_from_query(query):
    results = query.fetch(1000)
    choice_list = [(None, "--------")]
    for res in results:
        name = unicode(res)
        res_key = res.key()
        choice = (str(res_key), name)
        choice_list.append(choice)
    return choice_list

def create_choice_array_from_class(model_class, organization_key=None,
                                   sort_field = 'name', extra_filter_tuples = None):
    query = model_class.all()
    query.order(sort_field)
    if organization_key:
        query.filter('organization', organization_key)
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
    compare = cmp(p1.gender,p2.gender) * (-20) + \
            cmp(p1.last_name,p2.last_name) * 10 + \
            cmp(p1.first_name,p2.first_name) * 5
    return (cmp(compare,0))

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


def get_student_status_key_for_name(name):
    """
    Get the single key for the student_status "Enrolled" for use
    in filters for students with an active status.
    """
    query = SchoolDB.models.StudentStatus.all(keys_only=True)
    query.filter("name =", name)
    return (query.get())

def get_active_student_status_key():
    """
    Get the single key for the student_status "Enrolled" for use
    in filters for students with an active status.
    """
    query = SchoolDB.models.StudentStatus.all(keys_only=True)
    query.filter("active_student =", True)
    return (query.get())

def active_student_filter(query):
    """
    Set query filters to limit results to current active students.
    These filters are for the student status "enrolled" and the date of
    enrollment within one month prior to the current school year. Note:
    this uses an inequality filter on date, so there can be no other
    order parameter directly set. Sorting on name, etc. must be done on
    the list of records after the database request.
    """
    active_status_key = get_active_student_status_key()
    query.filter("student_status = ", active_status_key)
    #filter_by_date(query, "after", "student_status_change_date", 0)
    return query


def format_date(the_date):
    """
    Convert a valid date to a unicode string mm/dd/yyyy
    """
    try:
        date_string = unicode(the_date.strftime("%m/%d/%Y"))
    except :
        date_string = unicode("")
    return date_string

def all_children(entity, childrens_classes):
    """ 
    Childrens classes is a list of data classes that can be children of the
    entity. They are used to in the queries for children.
    """
    children = []
    for cls in childrens_classes:
        q = cls.all()
        q.ancestor(entity)
        children.extend(q.fetch(1000))
    return children

def fully_delete_entity(entity, childrens_classes):
    """
    Delete not only the specific entity but also all of its children.
    This can clean up after a complex object. Childrens classes is a list of
    data classes that can be children of the entity. They are used to
    in the queries for children.
    """
    targets = [entity]
    targets.extend(all_children(entity, childrens_classes))
    db.delete(targets)


def get_school_year_for_date(day_date = date.today()):
    """
    Determine the class year based upon the date and the school 
    calendar. This uses "approximation". If the current date is two or
    three weeks prior or after then that year is chosen. Summer 
    sessions require further definition so a flag is also returned to 
    indicate that the year might need manual definition.
    """
    return SchoolYear.school_year_for_date(day_date)

def get_class_years_only():
    """
    Return the ClassYearNames from choices without the name "None"
    """
    year_names = list(SchoolDB.choices.ClassYearNames)
    try:
        year_names.remove("None")
    except ValueError:
        pass
    return year_names

def get_possible_subjects(filter_string):
    """
    Get a dict of subject names by keys and an ordered list of keys for
    subjects defined at the national level. The filter_string is used to add another filter. If the result is meant for achievement tests then the string is "used_in_achievement_tests =", if for class_session creation then the string is "taught_by_section =".
    """
    query = Subject.all()
    query.filter("organization =", National.get_national_org()) 
    query.filter(filter_string, True)
    query.order("name")
    subjects = query.fetch(20)
    subject_name_to_key_dict = {}
    subject_key_to_name_dict = {}
    subject_names = []
    for subject in subjects:
        subject_name = unicode(subject)
        subject_names.append(subject_name)
        subject_name_to_key_dict[subject_name] = subject.key()
        subject_key_to_name_dict[subject.key()] = subject_name
    return (subject_names, subject_name_to_key_dict, 
            subject_key_to_name_dict)

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

def custom_query(organization, leading_value, value_dict, target_class):
    """
    Return a keys and names list for the specified class. The only
    filter value is the "name" field. The list is ordered by name
    """
    query = SchoolDB.assistant_classes.QueryMaker(target_class, value_dict)
    return query.get_keys_and_names()    

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

def get_model_class_from_name(name_string):
    """
    Return the model class for a string with the same characters but
    all lower case. This is used to convert a string into the actual
    class.
    """
    if (name_string):
        class_name_map = {"administrator":Administrator, 
                          "achievement_test":AchievementTest, 
                          "community":Community,
                          "class_session":ClassSession, 
                          "class_period":ClassPeriod,
                          "classroom":Classroom,
                          "contact":Contact, "database_user":DatabaseUser,
                          "division":Division,"family":Family,
                          "grading_instance":GradingInstance, 
                          "grading_period":GradingPeriod,
                          "municipality":Municipality, 
                          "organization":Organization,
                          "person":Person,
                          "parent_or_guardian":ParentOrGuardian,
                          "province":Province,
                          "region": Region, "school": School,
                          "school_day":SchoolDay, 
                          "school_day_type":SchoolDayType,
                          "school_year": SchoolYear,
                          "section": Section, 
                          "section_type": SectionType, 
                          "special_designation":SpecialDesignation,
                          "student": Student, 
                          "student_grouping":StudentGrouping,
                          "student_major":StudentMajor,
                          "grading_period_result":GradingPeriodResult,
                          "student_status":StudentStatus, 
                          "student_summary":StudentSchoolSummaryHistory,
                          "subject": Subject,
                          "teacher": Teacher,
                          "versioned_text_manager":VersionedTextManager,
                          "versioned_text":VersionedText,
                          "user_type": UserType}
        model_class = class_name_map.get(name_string, None)
    return model_class

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
    query = class_name.all(keys_only=key_only)
    query.filter("name =", search_name)
    if organization:
        query.filter("organization =", organization)
    if single_only:
        return query.get()
    else:
        return query.fetch(max_fetched)

def get_blocks_from_iterative_query(query, blocksize):
    """
    Return a list of blocks (a list of max-size blocksize) of
    the result of an iterative query. This will return all results
    of the query.
    """
    blocks_list = []
    block = []
    for i in query:
        block.append(i)
        if (len(block) >= blocksize):
            blocks_list.append(block)
            block = []
    #Add remainder as final block. This also assures that the returned
    #structure is consistent even if there are no query results.
    blocks_list.append(block)
    return blocks_list
    
def setActiveDatabaseUser(databaseUser):
    global __activeDatabaseUser, __activeOrganization
    __activeDatabaseUser = ActiveDatabaseUser(databaseUser)
    __activeOrganization = __activeDatabaseUser.get_active_organization()

def setActiveOrganization(organization):
    global __activeOrganization
    __activeOrganization = organization
    
def getActiveDatabaseUser():
    global __activeDatabaseUser
    return __activeDatabaseUser
