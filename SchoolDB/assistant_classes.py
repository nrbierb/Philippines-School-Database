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
This file contains miscellaneous non database classes that is used to support code in one or more other files.
"""
import cPickle, zlib, datetime, base64, logging
import SchoolDB.models 
import SchoolDB.views
from django.utils import simplejson
from google.appengine.ext import db
from google.appengine.api import taskqueue

class InformationContainer():
    """
    An abstract base class. Classes derived from this will be used to store
    and manipulate data that cannot be not easily or efficiently stored or
    used by the apps database datatypes and does not need to be searched
    directly. Objects of the derived classes are normally stored in the
    database as blobs after pickling and may optionally use compression to
    reduce storage size.
    """
    def __init__(self, version_id):
        #Change version id when a software change in the class 
        #definition requires that the data be converted in a 
        #different manner upon unpickling. 
        self.version_id = version_id
        self.conversion_functions = []

    @staticmethod
    def get_data(stored_data, compressed = True, 
                 current_version = 1,update_to_current_version = True):
        data_object = None
        if (stored_data):
            try:
                if (compressed):
                    stored_data = zlib.decompress(stored_data)
                data_object = cPickle.loads(stored_data)
                if ((data_object.version_id != current_version) and 
                    update_to_current_version):
                    data_object.update_to_version(current_version)
            except StandardError, err:
                data_object = None
                raise StandardError, err
        return data_object

    def update_to_current_version(self):
        """
        A default class function that does nothing. This need
        not be redefined in a child class until there is a update
        to a version that requires some change in the data stored.
        """
        return self

    def put_data(self, compress = True):
        """
        Convert back into the stored form by pickling with optional
        compression. By default compression is used.
        """
        try:
            stored_data = cPickle.dumps(self)
            if (compress):
                stored_data = zlib.compress(stored_data)
        except StandardError, err:
            stored_data = None
        return stored_data

    
#------------------------------------------------------------------
class KeyedStore():
    """
    This is a simple general class that can be used to create binary
    strings that have an identifying key field and a data field. The
    key field's identifying text may be of any length or text that does
    not include the string '-|-' which is used as a seperator. The data
    field's text has no restrictions. This could be used, for example,
    to combine a datastore keystring with an information container.
    """

    def __init__(self, stored_string="", key="", data=""):
        """
        Split into component parts if there is a stored_string that was
        previously created by "convert" from a previous instance of
        this class. If not, use the values (if any) for key and data.
        An init with no args leaves an empty object ready for setting.
        """
        self.key = key
        self.data = data
        if stored_string:
            fields = stored_string.split("-|-", 1)
            if (len(fields) > 1):
                self.key, self.data = fields
                
    def get_key(self):
        return self.key
    
    def get_data(self):
        return self.data
    
    def set_key(self, key):
        self.key = str(key)
        
    def set_data(self, data):
        self.data = str(data)
        
    def convert(self):
        """
        Return a string with the key and data separated by the marker characters
        """
        return self.key + "-|-" + self.data

#----------------------------------------------------------------------
class TaskGenerator():
    """
    The class to create and queue tasks. This will create one
    or more tasks.
    -task_name, function, and function_args must be specified.
    -org: The keystring for the org that will be active for the task. If not
     defined then the caller's organization will be used.
    -instance_keylist: The list of keys for instances that should be 
      processed by the function
    -query_iterator: alternate to the keylist, it uses the keys_only query.
     Note: only one of the next two should be defined
    -instances per task: if there is an instance_keylist this is the number of
     instances to be process by a single task. It the total length of the 
     instance keylist is greater than this then multiple tasks will be queued.
     """
     
    def __init__(self, task_name, function, function_args="", 
                    organization = None, instance_keylist = None,
                    query_iterator = None, instances_per_task = 10,
                    rerun_if_failed = True):
        self.task_dict = {"task_name":task_name, "function":function, 
                         "args":function_args, "organization":organization,
                         "rerun_if_failed":rerun_if_failed}
        self.task_name = task_name
        self.instance_keylist = instance_keylist
        self.instances_per_task = instances_per_task
        self.query_iterator = query_iterator
        
    def send_task(self):
        """
        Prepare task for sending by pickling and compressing all parameters.
        Then add task to queue.
        """
        packed = zlib.compress(cPickle.dumps(self.task_dict))
        encoded = base64.b64encode(packed)
        params_data = {"task_data":encoded}
        taskqueue.add(url="/task", params=params_data) 
        
    def queue_tasks(self):
        """
        Perform the task generation. Write information about success in
        info log or failure into error log.
        """
        try:
            task_count = 0
            if self.instance_keylist:
                block_end = self.instances_per_task - 1
                while self.instance_keylist:
                    task_keylist = self.instance_keylist[0:block_end]
                    self.task_dict["target_instances"] = task_keylist
                    self.send_task()
                    del self.instance_keylist[0:block_end]
                    task_count += 1
            elif self.query_iterator:
                keys_blocks = SchoolDB.models.get_blocks_from_iterative_query(
                    self.query_iterator, self.instances_per_task)
                for block in keys_blocks:
                    keystring_block = [str(key) for key in block]
                    self.task_dict["target_instances"] = keystring_block
                    self.send_task() 
                    task_count += 1
            else:
                self.send_task()
                task_count = 1
            result_string = "%s: %d tasks successfully enqueued." \
                   %(self.task_name, task_count)
            logging.info(result_string)
            return True, result_string
        except StandardError, e:
            result_string = "%s: Failed after enqueueing %d tasks. Error: %s" \
                    %(self.task_name, task_count, e)
            logging.error(result_string)
            return False, result_string

#------------------------------------------------------------------
class StatisicalResults():
    """
    A simple class that contains the standard statistical measures and
    the means to create them.
    """
    def __init__(self, histogram_limits=[]):
        self.valid = False
        self.count = 0
        self.minimum = 0.0
        self.maximum = 0.0
        self.average = 0.0
        self.median = 0.0
        self.histogram_limits = histogram_limits
        #extra entry for "greater than" last limit value
        self.histogram = [0 for i in range(len(histogram_limits) + 1)]

    def set_information(self, values):
        """
        Process a list of numbers to calculate the statistical results.
        """
        self.valid = True
        self.count = len(values)
        if self.count:
            max_index = self.count - 1
            self.average = sum(values) / self.count
            values.sort()
            self.minimum = values[0]
            self.maximum = values[max_index]	    
            if ((self.count) % 2 == 1):
                self.median = values[(self.count + 1)/2 - 1]
            else:
                self.median = (values[self.count/2] + \
                               values[ self.count/2 +1]) / 2.0
            hist_limits = (65,74,79,89,1000)
            hist_index = 0
            for i in xrange(self.count):
                for hist_index in xrange(len(hist_limits)):
                    if values[i] <= histogram_limits[hist_index]:
                        self.histogram[hist_index] += 1
                        break

    def aggregate_information_from_multiple_results(self, results_list):
        """
        Combine the results from several StatisticalResults instances into this
        statistical result. This aggregate instance must be created prior to
        using this. It will normally be a newly created one when this function
        is called although it could be used to further aggregate groups if no
        instances are in the further lists. If an results_list instance is not
        marked valid it is ignored. Return the count of input instances, and
        the number that were valid. The average is weighted by the count, the
        median is the median of the input instances, the maximum and minimum is
        across instances, and the histogram is the sum of all.
        """
        weighted_average_sum = 0.0
        median_list = []
        valid_count = 0
        if (len(results_list)):
            for result in results_list:
                if (result.valid):
                    valid_count += 1
                    self.count += result.count
                    weighted_average_sum += result.count * result.average
                    r_median_list = [result.median for i in xrange(result.count)]
                    median_list.extend(r_median_list)
                    if ((result.minimum < self.minimum) or 
                        (self.minimum == 0)):
                        self.minimum = result.minimum
                    if (result.maximum > self.maximum):
                        self.maximum = result.maximum
                    for i, num in enumerate(result.histogram):
                        self.histogram[i] += num
            median_list.sort()
            if ((self.count) % 2 == 1):
                self.median = median_list[(self.count + 1)/2 - 1]
            else:
                self.median = (median_list[self.count/2] + \
                               median_list[ self.count/2 +1]) / 2.0
            self.average = weighted_average_sum / self.count
        return (len(results_list), valid_count)

#------------------------------------------------------------------
class StudentsGradingValue():
    """
    This is a small class that contains the information about a single
    grade. It is used in a list in the students grading instance so
    it has no direct reference to the ClassSession's GradingInstance.
    It contains five parameters, three of which are for tracking grade
    changes after initial entry.
    Grade Value: (float) the unscaled value entered into the grading
      form
    Grade Date: the date of the grading event
    Change Date: if the date is changed after entry this is the date
      of the most recent change. Initial value: None. A non-null value
      serves as a flag that the value was changed.
    Initial value: If the grade is changed, this is the value that was
      first assigned. Value intial grade value. Unchangeable after 
      first assignment.
    Last editor: The key of the user that last changed the value. 
      Initial value : the key of the initial grade entry person.
    """

    def __init__(self, gradevalue, grade_event_id, date, editor):
        self.value = gradevalue
        self.grade_event_id = grade_event_id
        self.initialdate = date
        self.changedate = None
        self.initialvalue = gradevalue
        self.lasteditor = editor

    def change(self, newvalue, editor, 
               changedate = datetime.datetime.now()):
        self.value = newvalue
        self.lasteditor = editor
        self.changedate = changedate

    def was_changed(self):
        return (self.changedate != None)

    def change_delta(self):
        return (self.value - self.initialvalue)

    def get_grade(self):
        """
        Return a tuple of the gradeval and the date for use in
        higher level reporting
        """
        return (self.value, self.initialdate)

#------------------------------------------------------------------
class StudentsGradingInstance():
    """
    This is not a db model class. It is a small class that represents the
    students result on a grading instance, i.e. the grade on a test or
    multiple tests if the grading instance is defined as a multiple. It
    is truly only a container and summary element.
    Parameters:
    Results: List of student grading values
    """
    def __init__(self):
        self.values_list = []

    def get_changed_values(self):
        changed_values = []
        for value in self.values_list:
            if (value.was_changed()):
                changed_values.append(value)
        return changed_values

    def add_grade(self, grade_value, grade_event_id, date, editor):
        grade_value = StudentsGradingValue(
            grade_event_id=grade_event_id, 
            gradevalue=grade_value, date=date, editor=editor)
        self.values_list.append(grade_value)

    def get_gradingvalue_object(self, grade_event_id):
        gradingvalue_object = None
        for value in self.values_list:
            if (value.grade_event_id == grade_event_id):
                gradingvalue_object = value
                break
        return gradingvalue_object

    def edit_grade(self, new_grade, editor, gradingvalue_object):
        """
        Change a grade that already has been set if the value is different.
        The edit marks the grade as changed and adds further information
        about when it was changed and who changed it.
        """
        if (gradingvalue_object and (gradingvalue_object.value != new_grade)):
            gradingvalue_object.change(new_grade, editor)
        return (gradingvalue_object)

    def set_grade(self, grade_value, grading_event_id, date, editor,
                  edit_ok = True):
        """
        Either add or change a grade as appropriate. If a gradevalue object
        already exists for a grading event then it is edited. If not, a new
        gradevalue object is added. This is normally the only function
        for grade entry that is used externally
        """
        gradingvalue_object = self.get_gradingvalue_object(grading_event_id)
        if gradingvalue_object:
            if (edit_ok):
                gradingvalue_object = self.edit_grade(grade_value, 
                                                      editor, gradingvalue_object)
            return edit_ok
        else:
            gradingvalue_object = self.add_grade(grade_value, 
                                                 grading_event_id, date, editor)
            return True

    def get_grade_value(self,grading_event_id):
        """
        Get a single grade value by the event_id
        """
        gradingvalue_object = self.get_gradingvalue_object(grading_event_id)
        value = None
        if gradingvalue_object:
            value = gradingvalue_object.value
        return value

    def get_grades(self, start_date = None, cutoff_date = None,
                   current_value_only = True):
        """
        Return a list of tuples of the gradeval and the id for use in
        higher level reporting
        """
        grades_list = []
        for value in self.values_list:
            if (((start_date == None) or 
                 (value.initialdate > start_date)) and
                ((cutoff_date == None) or 
                 (value.initialdate <= cutoff_date))):
                if current_value_only:
                    grades_list.append(value.value)
                else:
                    #this is for use during checks for editing
                    grade_tuple = (value.value, value.initialvalue)
                    grades_list.append(grade_tuple)
        return grades_list

    def get_summary_grade(self, start_date = None, cutoff_date = None):
        """
        Return a single tuple of (grade, initialgrade) for this 
        grading instance. If this instance has multiple grades then
        they will be averaged. Any grades beyond the cutoff date will
        be ignored.
        """
        grades_list = self.get_grades(start_date, cutoff_date)
        count = len(grades_list)
        if (count ==1):
            #the most common case of only one grade for the instance
            return grades_list[0]
        if (count > 1):
            #a multiple grades instance. The grades must be combined 
            #proportionately based upon weight.
            grade_sum = 0.0
            initialgrade_sum = 0.0
            for grade in grades_list:
                grade_sum += grade[0]
                initialgrade_sum += grade[1]
            grade = grade_sum / count
            initialgrade = initialgrade_sum / count
            return (grade, initialgrade)
        else:
            # no grades at all -- nothing in range
            return None
#------------------------------------------------------------------
class StudentsClassInstanceGrades(InformationContainer):
    """
    Store all of the students grades within a single object that 
    can be converted to a "blob" for storage within the database.
    All grades are stored as instances of StudentsGradingInstance
    in a dictionary keyed by the associated GradeInstance key.
    """

    def __init__(self, version_id = 1):
        InformationContainer.__init__(self, version_id)
        self.grades = {}

    def set_grade(self, grading_instance_key, grading_event_id, 
                  date, grade_value, editor, edit_ok = True):
        """
        Add a grade for the instance if not already entered or if multiple.
        If not, edit the current if edit is ok.
        """
        grading_instance_keystr = str(grading_instance_key)
        editor_keystr = str(editor.key())
        if (not self.grades.has_key(grading_instance_keystr)):
            self.grades[grading_instance_keystr] = StudentsGradingInstance()
        successful = self.grades[grading_instance_keystr].set_grade(
            grade_value=grade_value, grading_event_id=grading_event_id,
            date=date, editor=editor_keystr, edit_ok = edit_ok)
        return successful

    def contains_grades(self):
        """
        Return True if there are some grades in the object
        """
        return (len(self.grades) > 0)

    def get_grade(self, grading_instance_key, grading_event_id=1):
        """
        Get a single grade value from the instance selected by the grade event
        key. If no grade information for the instance or no grade with the id
        reutrn None. The default grading_event_id will return the first grade
        value -- normally the only grade value.
        """
        grading_instance_keystr = str(grading_instance_key)
        grading_instance = self.grades.get(grading_instance_keystr)
        if grading_instance:
            return grading_instance.get_grade_value(grading_event_id)
        else:
            return None

    #def edit_grade(self, grading_instance_key, date, 
                    #new_value, editor):
        #grading_instance = self.grades.get(grading_instance_key)
        #edit_performed = False
        #if grading_instance:
            #edit_performed = grading_instance.edit_grade(grade_value=new_value, 
                            #grading_event=grading_event, editor=editor, date=date)
        #return edit_performed

    def get_change_count(self):
        count = 0
        for instance in self.grades.values():
            count += len(instance.get_changed_instances())
        return count

    def get_changed_instances(self):
        changed_instances_list = []
        for instance_entry in self.grades.items():
            changed_instances = \
                              instance_entry[1].get_changed_instances()
            if (len(changed_instances) > 0):
                changed_instances_list.append((instance_entry[0],
                                               changed_instances))
        return changed_instances_list

    def get_grades(self, grading_instance_keys, start_date = None, 
                   cutoff_date = None, summary_values = False,
                   last_value = False):
        """
        Return a dictionary of grade information keyed by the
        grading_instance. Each instance key in the instance list will
        be in the dictionary. If summary_values is True then the value
        will be the single grade which is possibly a combination of
        several tests. If False then the value will be a ditionary of
        tuples of the grade value and the initial grade value keyed by
        the grading events for the instance -- normally only one. If
        there is no grade record for that instance the value will be
        None. This assumes that the grading instances have one or more
        grading events in the date range.
        """
        values_dict = {}
        values_list = []
        for key in grading_instance_keys:
            grading_instance = SchoolDB.models.GradingInstance.get(key)
            grading_events = grading_instance.getGradingEvents(
                start_date, cutoff_date)
            grade_val = None
            if self.grades.has_key(key):
                if summary_values:
                    grade_val = \
                              self.grades[key].get_summary_grade(grading_events)
                else:
                    grade_val = \
                              self.grades[key].get_grades(grading_events)
                    if (last_value and (len(grade_val) > 0)):
                        grade_val = grade_val[len(grade_val) - 1]
            values_dict[key] = grade_val
            values_list.append(grade_val)
        return values_dict, values_list

#----------------------------------------------------------------------  

class GradingEvent():
    """
    A single grade event. Each grading instance has at least one of these.
    If the grading instance is multiple then there will be more than 1.
    Each student in the class has a reference to this along with their
    personal value for the grade for all grades given in a class. The
    weighting value is purely arbitrary and is used only when combining
    several grades in a single grading instance -- for example daily tests
    with different weights. If required is true then the student is given a
    0 if she was not graded and the total grade for the instance is reduced
    accordingly.
    """
    def __init__(self, date, id, weight=1.0, required=True):
        self.date = date
        self.id = id
        self.weight = weight
        self.required = required
        self.grades_entered = False

    def get_weighted_grade(self, base_grade):
        return (self.weight * base_grade)

    #definitions for list ordering
    def __lt__(self, other_grading_event):
        return (self.date < other_grading_event.date)

    def __gt__(self, other_grading_event):
        return (self.date > other_grading_event.date)

    def _lt__(self,date):
        return (self.date < date)

    #Simple interface functions for use outside of GradingEvents    
    def valid_grades(self):
        return self.grades_entered

    def get_date(self):
        return self.date

    def is_required(self):
        return self.required

    def is_valid(self):
        return self.grades_entered

class GradingEvents(InformationContainer):
    """
    Another simple container for a list of grading events. It is maintained
    sorted by date. The date is used for external reference to a grading
    event which implies that there can be no more than one grading event
    per day for the GradingInstance that contains this object. This is in
    use a very reasonable assumption. 
    """
    def __init__(self, version_id = 1):
        InformationContainer.__init__(self, version_id)
        self.grading_events = []

    def empty(self):
        return (len(self.grading_events) == 0)

    def get_grading_event(self, date = None):
        grading_event = None
        if (not self.empty()):
            if (date == None):
                event = self.grading_events[0]
            else:
                for event in self.grading_events:
                    if (event.date == date):
                        grading_event = event
        return grading_event		

    def get_grading_event_by_id(self, index):
        if (index < len(self.grading_events)):
            event = self.grading_events[index]
            return event.date
        return None

    def get_grading_event_date_by_index(self, index):
        if (index < len(self.grading_events)):
            event = self.grading_events[index]
            return event.date
        return None

    def add_grading_event(self, date, weight=1.0, required=True,):
        new_id = len(self.grading_events)
        new_event = GradingEvent(date, id, weight, required)
        self.grading_events.append(new_event)
        self.grading_events.sort()
        return new_event

    def get_grading_events_in_period(self, start_date, end_date):
        events = []
        if (not self.empty()):
            event = self.grading_events[0]
            for event in self.grading_events:
                if ((event.date <= end_date) and (event.date >= start_date)):
                    events.append(event)
        return events

    def set_grades_entered(self, date = None):
        if (not self.empty()):
            if (not date):
                event = self.grading_events[0]
            else:
                event = self.get_grading_event(date)
            if (event):
                event.grades_entered = True
                return True
        return False

    def get_date(self):
        """
        The normal case is only one single grade in a grading instance. Thus
        the first grading event date is the date for the grading instance.
        """
        date = None
        if (not self.empty()):
            date = self.grading_events[0].date
        return date

    def change_date(self, new_date, old_date=None):
        """
        Search for event with the old_date and change it.
        If no old_date change the date on the first event.
        A new event will never be added.
        """
        grading_event = self.get_grading_event(old_date)
        if (not grading_event):
            if (not len(self.grading_events)):
                self.add_grading_event(new_date)
            grading_event = self.grading_events[0]
        grading_event.date = new_date

    def get_grading_events_count(self):
        return len(self.grading_events)

    def is_valid(self):
        """
        At least one event has been created and has grades entered
        """
        if (self.get_grading_events_count):
            for event in self.grading_events:
                if event.is_valid():
                    return True
        return False

    def event_is_valid(self, date):
        """
        Valid if an event exists for that date and has grades_entered
        """
        valid = False
        event = self.get_grading_event(date)
        if event:
            valid = event.is_valid()
        return valid

#----------------------------------------------------------------------
class AjaxGetGradeHandler:
    """
    Process Ajax requests for grades and rosters for a specified
    class session. The actions are selected by the arguments in the
    Ajax request. All return a tuple with a boolean for successful
    completion and a formatted json return string. All of the 
    supporting database actions are performed by the ClassSession 
    model class.    
    The action type ids and actions are:
    class_roster: return a list of keys and names for all students
    *grading_instances: return a list of keys and multiple parameters
      for all grading instances.
    *grades_table: return a table of student key, student grading record
      key, and grades for one or more grading instances specified in a
      list of instance keys. An empty string will be returned for all 
      grades not yet entered for a student
    *valid_grades: return a table similar to the grades_table for all 
      instances that are valid (have grades entered for some students)
      and, optionally, in a a certain time period. 

    Note: security is highly important here. No information should be
    returned to the browser if it is not meant for display or access. 
    Grading records are the most attractive target for abuse in the 
    system.      
    """

    def __init__(self, student_group, json_data):
        self.student_group = student_group
        try:
            data = simplejson.loads(json_data)
            self.requested_action = data["requested_action"]
            self.achievement_test = data["achievement_test"]
            grading_instances_key_strings = simplejson.loads(data["gi_keys"])
        except StandardError, e:
            raise StandardError, ("Failed in init for get_grades: " + str(e))
        (self.grading_instances_key_strings, self.grading_instances_keys, 
         self.grading_instance_keys_dict, all_valid) = \
         process_grade_instance_keys(grading_instances_key_strings)
        self.grading_instance_detail_dict = \
            AjaxGetGradeHandler.build_grading_instances_detail_dict(
                self.grading_instances_key_strings, 
                self.grading_instance_keys_dict)
        self.table_name = "gradesTable"
        #initialize other class variables that are filled by the differing
        #init actions for class session tests and achievement tests students
        #is a list of student instances, all others contain keys and are 
        #indexed by keys
        self.students = []
        self.student_record_keys = []
        self.student_record_keys_dict ={}
        if (self.achievement_test):
            self.init_for_achievement_tests()
        else:
            self.init_for_normal_classes()
        self.result_string = "Unknown Failure"
        self.successful = True

    def init_for_normal_classes(self):
        """
        Initialize the object with information from a single class session.
        The student class record for all grading instances is the same 
        because all instances are from the same class.
        """
        self.student_keys, student_record_keys, student_record_keys_dict = \
            self.student_group.get_students_and_records(
                sorted = True, record_by_key=True)
        for student in self.students:
            record_key = student_record_keys_dict[student]
            student_record_by_grading_instance = {}
            for gd_inst_key in self.grading_instances_keys:
                student_record_by_grading_instance[gd_inst_key] = record_key
            self.student_record_keys.append(student_record_by_grading_instance)
            self.student_record_keys_dict[student.key()] = \
                student_record_by_grading_instance

    def init_for_achievement_tests(self):
        """
        Intialize the object with information from an achievement test.
        This will normally be a list of grading instances, one for each
        subject on the test. Each grading instance will have a
        different student class record mapping to the class the student
        is taking for that subject.
        """
        #build subject list
        subjects_dict = {}
        for gd_inst_key in self.grading_instances_keys:
            gd_inst = SchoolDB.models.GradingInstance.get(gd_inst_key)
            subjects_dict[gd_inst_key] = gd_inst.subject.key()
        self.students = self.student_group.get_students()
        for student in self.students:
            student_record_by_subject = \
                student.get_class_records_by_subject(subjects_dict.values())
            student_record_by_gd_inst_key = {}
            for gd_inst_key in self.grading_instances_keys:
                subject_key = subjects_dict[gd_inst_key] 
                student_record_by_gd_inst_key[gd_inst_key] = \
                        student_record_by_subject.get(subject_key, None)
            self.student_record_keys.append(student_record_by_gd_inst_key)
            self.student_record_keys_dict[student.key()] = \
                student_record_by_gd_inst_key

    def create_class_roster_and_json(self, keys_only=False):
        """
        Create a single array of (student class record key, 
        student name) for all students in the class. If keys_only        
        """
#        try:
        roster_list = []
        for student in self.students:
            student_keystr = \
                           str(student.key())
            if not keys_only:
                name = student.full_name_lastname_first()
                element = (student_keystr, name)
                roster_list.append(element)
            else:
                roster_list.append(student_keystr)
        json_string = simplejson.dumps(roster_list)
        self.successful = True
        #except StandardError, e: 
            #error_string = "Roster create failed: " + str(e)
            #raise StandardError(error_string)            
        return roster_list, json_string

    def create_grading_instances_data(self):
        """
        Create an array and a dictionary, the array with just the key and 
        the name to build a simple list table and a dictionary indexed by
        the key with the other relevant data. The information in the 
        dictionary can be used in an information expansion or detailed 
        table.
        """
        json_data = [self.grading_instances_key_strings,
                     self.grading_instance_detail_dict]
        json_string = simplejson.dumps(json_data)
        return (self.grading_instances_key_strings, 
                self.grading_instance_detail_dict, json_string)

    def create_table_header(self):
        """
        Create a list of header parameters to be used by the google
        table widget. In addition, create a list of grading instances
        that can be used to get furnter information from the grading
        instances associated with the column.
        """
        header = [("name","string","Student Name")]
        grading_instances_list = [None]
        for gi_keystr in self.grading_instances_key_strings:
            gi_key = SchoolDB.models.get_key_from_string(gi_keystr)
            grading_instance = SchoolDB.models.GradingInstance.get(
                self.grading_instance_keys_dict[gi_key])
            subject = grading_instance.subject
            title = unicode(subject)
            if self.achievement_test:
                #add number of questions as aid to entry
                title = "%s %d" %(title, grading_instance.number_questions)
            column_hdr = (gi_keystr, "string", title)
            header.append(column_hdr)
            grading_instances_list.append(grading_instance)
        return header, grading_instances_list

       
    def create_table_data(self):
        """
        Create a two level array in the form to be used by the google
        table widget. The first column is the student name, the
        subsequent columns are the students grading instances values.
        In addition, create a matching 2-D array of
        student_class_record keys associated with the grade value. This
        allows each grade to be added to an arbitrary table. Finally,
        build an array of student names and numerical values for grades
        to be used in tables that add further surrounding elements (ex.,
        Form 14)
        """
        #build tables for data
        row = ["" for i in range(len(self.grading_instances_keys) + 1)]
        table_data = [list(row) for i in range(len(self.students))]
        row = [0 for i in range(len(self.grading_instances_keys) + 1)]
        raw_data = [list(row) for i in range(len(self.students))]
        row = ["" for i in range(len(self.grading_instances_keys))]
        student_record_data = [list(row) for i in range(len(self.students))]
        for y, student in enumerate(self.students):
            table_data[y][0] = student.full_name_lastname_first()
            raw_data[y][0] = table_data[y][0]
            for x, gd_inst_key in enumerate(self.grading_instances_keys):
                student_record_key = \
                                   self.student_record_keys_dict[student.key()][gd_inst_key]
                grade = None
                if student_record_key:
                    student_record_data[y][x] = str(student_record_key)
                    student_record = \
                                   SchoolDB.models.StudentsClass.get(student_record_key)
                    grade = student_record.get_grade(gd_inst_key)
                if grade:
                    grade_str = "value=%5.1f" %grade
                else:
                    grade_str = ""
                    grade = 0
                table_data[y][x+1] = '<input type="text" class="entry-field numeric-field" ' +\
                          'id="%s-%s-%s" %s></input>' %(self.table_name, x, y, grade_str)
                raw_data[y][x+1] = grade
        return table_data, student_record_data, raw_data

    def create_table(self):
        """
        Create the ajax return value for a full table representation
        with the Google table. 
        """
        table_header, grading_instances_list = self.create_table_header()
        table_data, student_record_data, raw_data = \
                  self.create_table_data()
        data_table = SchoolDB.gviz_api.DataTable(table_header)
        data_table.LoadData(table_data)
        json_table = data_table.ToJSon()
        json_student_record_data = simplejson.dumps(student_record_data)
        return json_table, json_student_record_data
    
    def create_raw_information(self):
        """
        Create the table header and array of student names and
        numerical values that can be used in building an extended
        table with other surrounding elements.
        """
        table_header, grading_instances_list = self.create_table_header()
        table_data, student_record_data, raw_data = \
                  self.create_table_data()
        return table_header, grading_instances_list, raw_data
    
    def create_full_package(self):
        """
        Create a complete json set of values for the normal grade page.
        It includes the table and the student_key_list just like any
        other client table usage but is then extended by the list of
        grading instances in the same order as the columns and the
        dictionary of details about each grading instance.
        """
        json_return_dict = {}
        json_table, json_student_record_data = self.create_table()
        json_return_dict["tableDescriptor"] = json_table
        json_return_dict["studentRecordsArray"] = json_student_record_data
        unused, json_student_keylist = self.create_class_roster_and_json(True)
        json_return_dict["keysArray"] = json_student_keylist
        json_return_dict["gradingInstKeyArray"] = \
                        simplejson.dumps(self.grading_instances_key_strings)
        json_return_dict["gradingInstDetails"] = \
                        simplejson.dumps(self.grading_instance_detail_dict)
        full_json_return = simplejson.dumps(json_return_dict)
        return full_json_return

    def service_request(self):
        """
        Map the request type to a class function for service and
        return the result.
        """
        if (self.requested_action):
            if (self.requested_action == "class_roster"):
                s, rs = self.successful, self.create_class_roster_and_json()
            elif (self.requested_action == "grading_instances"):
                s, rs = self.successful, \
                 self.create_grading_instances_data()[1]
            elif (self.requested_action == "full_package"):
                s, rs = self.successful, self.create_full_package()
            else:
                s = False
                rs = 'Unknown action "%s" requested.' %self.requested_action
        else:
            s = False
            rs = 'Unknown action "%s" requested.' %self.requested_action
        return s, rs


    @staticmethod
    def build_grading_instances_detail_dict(key_strings,
                                            instance_dictionary):
        """
        Create a dictionary of information about the grading
        instances. It has a dict of value_names and values.
        The value names are short to minimize total size. Then each of
        these dicts are added as an entry in the upper level dict 
        indexed by the grading instance key
        """
        detail_dict = {}
        for key_string in key_strings:
            index_key = SchoolDB.models.get_key_from_string(key_string)
            gi_key = instance_dictionary.get(index_key, None)
            if (gi_key):
                gi = SchoolDB.models.GradingInstance.get(gi_key)
                values_dict = { "name":unicode(gi),
                                "grdType":gi.grading_type,
                                "percentGrd":gi.percent_grade,
                                "extraCredit":gi.extra_credit,
                                "multiple":gi.multiple,
                                "otherInfo":gi.other_information,
                                #"valid":gi.valid,
                                #"dates":gi.dates
                                }
                detail_dict[key_string] = values_dict
        return detail_dict

#----------------------------------------------------------------------

class AjaxSetGradeHandler:
    """
    Set grades for students and update information about grading instance.
    This is a very commonly used class that reads/modifies many records so 
    it is as efficient as possible.
    """

    def __init__(self, student_grouping, gi_owner, gi_key_strings, 
                 student_record_key_strings, 
                 grades_table,
                 student_class_records_table,
                 gi_changes):
        """
        The initialization parameters are:
        1. "gi_keys" - a list of grading instance keys
        2. "student_keys" - a list of student instance keys
        3. "grade_table" - a 2D table of grade values
        4. "student_class_records_table" - a 2D table of student class records
        which matches the grade values
        5. "gi_changes" - a two level dictionary of values to be changed for
            each grading_instance. Top level keyed by grading instance, 
            second level by value name. May be None
        All are json strings so must be converted for use.
        """

        self.student_grouping = student_grouping
        self.grading_instance_owner = gi_owner
        self.grading_instances_key_strings, self.grading_instances_keys, \
            self.grading_instance_keys_dict, all_valid = \
            process_grade_instance_keys(gi_key_strings)
        if (not all_valid):
            raise SchoolDB.ajax.AjaxError(
                "Invalid grading instances in save table. No records saved.")
        self.grading_instances_dict = {}
        self.grading_instances = []
        for gi_key in self.grading_instances_keys:
            grading_instance = SchoolDB.models.GradingInstance.get(gi_key)
            self.grading_instances_dict[gi_key] = grading_instance
            self.grading_instances.append(grading_instance)
        self.student_record_keystrings = student_record_key_strings
        self.grades_table = grades_table
        self.gi_changes = gi_changes
        self.student_class_records_table=student_class_records_table
        self.student_class_record_dict = {}
        self.changed_student_grade_records = []
        self.grade_recording_date = datetime.date.today()
        self.editor = SchoolDB.models.getActiveDatabaseUser().get_active_user()
        self.rows_count = len(self.grades_table)

    def service_request(self):
        """
        Perform all necessary actions for the grade table save request.
        Each table row represents a single student so load each one at
        a time but do not perform the put. After all changes have been
        made then use a "put" to enter all changed records at once.
          Then process all changes for the grading instances. This is
        normally only the gi date which may be set the first time that
        grades are entered for the set.
        """
        self._check_table_consistency()
        self._load_student_class_records()
        if (self.gi_changes):
            for grading_instance_key in self.gi_changes.keys():
                self.save_grading_instance_change(grading_instance_key)
        self.save_grades()
        self._update_summary_data_if_necessary()
        return_string = \
                      simplejson.dumps("Successfully saved %d students grades" \
                                       %self.rows_count)
        return True, return_string

    def _check_grading_instance_consistency(self):
        """
        Check the dictionary of the grading instances to confirm that
        all exist and are owned by the class_session or achievement test.
        """
        for keystr in self.grading_instances_dict.keys():
            gd_inst = self.grading_instances_dict[keystr]
            if (gd_inst.owner != self.grading_instance_owner):
                raise SchoolDB.ajax.AjaxError(
                    "At least one gradebook entry is not correct. No records saved.")

    def _check_table_consistency(self):
        """
        The tables are 2D - a list of lists with separate row and column
        keys. The column keys have already been checked in init. Now
        confirm that the row keys are valid and that the table
        dimensions are correct. While it might be possible to try
        saving other rows if a record key is bad, a bad record key
        might indicate some tampering with the data so all data is
        ignored.
        """
        row_count = len(self.student_record_keystrings)
        rows_good = ((len(self.grades_table) == row_count) and
                     (len(self.student_class_records_table) == row_count))
        column_count = len(self.grading_instances_keys)
        for i in xrange(row_count):
            columns_good = ((len(self.grades_table[i]) == column_count) and
                            (len(self.student_class_records_table[i]) == column_count))
            if not columns_good:
                break
        if (not (rows_good and columns_good)):
            raise SchoolDB.ajax.AjaxError(
                "Records table size is wrong. No records saved.")

    def save_grades(self):
        """
        Save the table data from one row into the student record
        associated with the row. 
        """
        for row_index in xrange(self.rows_count):
            grades_row = map(convert_to_float, self.grades_table[row_index])
            records_row = self.student_class_records_table[row_index]
            for index in xrange(0,len(grades_row)):
                if (grades_row[index]):
                    grading_instance = self.grading_instances_dict[
                        self.grading_instances_keys[index]]
                    student_class_record = self.student_class_record_dict[
                        records_row[index]]
                    if (grading_instance and student_class_record):
                        student_grade_info = student_class_record.set_grade(
                            grading_instance_key = grading_instance.key(),
                            grade_value = grades_row[index],
                            editor = self.editor,
                            date = self.grade_recording_date)
                        if (student_grade_info):
                            student_class_record.put_grade_info(
                                student_grade_info)
        db.put(self.student_class_record_dict.values())

    def _load_student_class_records(self):
        """
        Scan the student class section array and load all records.
        """
        for i in range(len(self.student_class_records_table)):
            for j in range(len(self.student_class_records_table[i])):
                scr_keystring = self.student_class_records_table[i][j]
                if (not self.student_class_record_dict.has_key(
                    scr_keystring)):
                    instance = SchoolDB.models.get_instance_from_key_string(
                        scr_keystring, SchoolDB.models.StudentsClass)
                    if (not instance):
                        raise SchoolDB.ajax.AjaxError(
                            "At least one student class record does not exist. No records saved.")
                    if (str(instance.parent_key()) != 
                        self.student_record_keystrings[i]):
                        raise SchoolDB.ajax.AjaxError(
                            "At least one student class record does not belong to the student. No records saved.")
                    self.student_class_record_dict[scr_keystring] = instance

    def save_grading_instance_change(self, grade_instance_key):
        """
        There may be a dictionary of changed values for the grade instance.
        The most comman change will be the date of the test (or whatever)
        which is entered at the same time the grades are entered.
        """
        change = self.gi_changes[grade_instance_key]
        if change:
            grade_instance = self.grading_instances_dict[grade_instance_key]
            date_string = change.get("new_date", None)
            new_date = SchoolDB.views.convert_form_date(date_string)
            date_string = change.get("old_date", None)
            old_date = SchoolDB.views.convert_form_date(date_string)
            if (new_date and (new_date != old_date)):
                entry_index = grade_instance.set_date(old_date, new_date)
                grade_instance.set_instance_valid_state[entry_index, True]

    #--These functions for achievement test summary data
    def _create_grade_lists_by_gender(self):
        """
        Achievement test grade summaries are reported by gender. Three lists 
        of grades are need for each subject: combined, male, and female.
        Create two lists of table row indexes by gender and use that
        to create the gender grades lists.
        """
        students = [SchoolDB.models.get_instance_from_key_string(keystr) \
                    for keystr in self.student_record_keystrings]
        males = []
        females = []
        for i, student in enumerate(students):
            if (student.gender == "Female"):
                females.append(i)
            else:
                males.append(i)
        subjects = [gi.subject for gi in self.grading_instances]
        subject_keystrs = [str(subject.key()) for subject in subjects]
        grades_by_subject = {}
        for col_index, keystr in enumerate(subject_keystrs):
            male_grades = []
            for x in males:
                num = convert_to_float(self.grades_table[x][col_index])
                if (num):
                    male_grades.append(num)
            female_grades = []
            for x in females:
                num = convert_to_float(self.grades_table[x][col_index])
                if (num):
                    female_grades.append(num)
            combined_grades = []
            for x in xrange(len(students)):
                num = convert_to_float(self.grades_table[x][col_index])
                if (num):
                    combined_grades.append(num)
            grades_by_subject[keystr] = (combined_grades, male_grades,
                                         female_grades)
        return grades_by_subject

    def _update_summary_data_if_necessary(self):
        """
        Use the grading instance_owner to determine if the grades are for an
        achievement test, and if so, which one. Then load the grade lists by
        gender into the test summary data.
        """
        test = self.grading_instance_owner
        if (test.kind() == "AchievementTest"):
            grade_lists = self._create_grade_lists_by_gender()
            test.update_summary_information(str(self.student_grouping.key()),
                                            grade_lists)
#----------------------------------------------------------------------

def process_grade_instance_keys(gi_string_keys, owner=None):
    """
    Convert each key_string to a grading_instance, confirm that it is
    of the correct class and then confirm that each grading_instance
    belongs to the class. Return a tuple of a list of valid key_strings
    and a dictionary of valid instances indexed by the key_string.
    """
    valid_string_keys = []
    valid_instances_keys = []
    valid_instance_keys_dict = {}
    for key_string in gi_string_keys:
        try:
            instance_key = SchoolDB.models.get_key_from_string(key_string)
            #the key strings
            valid_string_keys.append(key_string)
            #the actual keys
            valid_instances_keys.append(instance_key)
            # a dict of the instances themselves indexed by the key
            valid_instance_keys_dict[instance_key] = instance_key
        except:
            #if exception just skip key_string
            pass
    all_valid = (len(gi_string_keys) == len(valid_string_keys))
    return (valid_string_keys, valid_instances_keys, valid_instance_keys_dict,
            all_valid)
#----------------------------------------------------------------------
def convert_to_float(val):
    """
    Trivial function to convert to a float value or return None.
    None is a legal value.
    """
    try:
        num = float(val)
        return num
    except:
        return None

#----------------------------------------------------------------------
class GradingPeriodGradesHandler:
    """
    This class performs all supporting functions for ajax calls to work 
    with the grades values for the grading period.
    """
    def __init__(self, class_session, edit_grading_periods,
                 view_grading_periods, students=[], results_table = None):
        self.class_session = class_session
        self.results_table = results_table
        self.table_name = "gradingPeriodGrades"
        self.student_keystrs = students
        # Get the grading periods that have been completed so that grades can
        # be recorded. 
        gradeable_grading_periods = \
                                  SchoolDB.models.GradingPeriod.get_completed_grading_periods()
        gd_keystrs = [str(p.key()) for p in gradeable_grading_periods]
        self.reporting_periods = []
        self.reporting_action = {}
        self.edit_grading_periods_from_get = []	
        for keystr in gd_keystrs:
            gd_key = SchoolDB.models.get_key_from_string(keystr)
            if (edit_grading_periods.count(keystr)):
                self.reporting_periods.append(gd_key)
                self.reporting_action[gd_key] = True
                self.edit_grading_periods_from_get.append(keystr)
            elif (view_grading_periods.count(keystr)):
                self.reporting_periods.append(gd_key)
                self.reporting_action[gd_key] = False		
        self.class_roster = []
        if (len(students)):
            #a list of students has been sent
            for student_key in students:
                student = SchoolDB.models.get_instance_from_key_string(
                    student_key)
                name = student.full_name_lastname_first()
            self.class_roster.append([student, name])
        else:
            self.class_roster = self.class_session.create_class_roster()
        self.usable = (len(self.reporting_periods) > 0)
        #get all grading period results for the class session
        if self.usable:
            self.grade_period_results = \
                SchoolDB.models.GradingPeriodResult.get_results_for_class_session(
                    self.class_session)	

    def _create_get_table_data(self):
        """
        Return a table of the grades for the students in the class session for
        the grading periods selected and gradeable. The most currnt gradeable
        period is returned as editable if the user is the teacher of the
        class. All others are simply viewable. Any gradings periods that are
        not yet in the list of gradeable periods are not included in the
        table.
        """
        # build a 2-D array of the results with grading perios as column
        # and student as row. First ak an empty one so that empties can be left
        row = []
        table = []
        student_keylist = []
        #for x in xrange(len(self.reporting_periods) + 1):
            #row.append(None)
        #for y in xrange(len(self.class_roster)):
            #table.append(list(row))
        #for i, (student, name) in enumerate(self.class_roster):
            #table[i][0] = name
            #student_keylist.append(student)
            #for j, period in enumerate(self.reporting_periods):
                #for result in self.grade_period_results:
                    #if ((result.grading_period == period) and
                        #(result.parent() == 
                            #SchoolDB.models.get_instance_from_key_string(student))):
                        #table[i][j + 1] = result
        #build table for data
        row = [None for i in range(len(self.reporting_periods)+1)]
        table = [list(row) for i in range(len(self.class_roster))]
        for j, period_key in enumerate(self.reporting_periods):
            grading_period_results = \
                                   SchoolDB.models.GradingPeriodResult.get_results_for_class_session(db.get(period_key))
            for i, (student, name) in enumerate(self.class_roster):
                table[i][0] = name
                student_keylist.append(student)
                for result in grading_period_results:
                    if ((result.grading_period.key() == period_key) and
                        (result.parent_key() == 
                         SchoolDB.models.get_key_from_string(student))):
                        table[i][j + 1] = result.assigned_grade
        #change format information for edited columns
        report_col_index=-1
        for x in xrange(1,(len(self.reporting_periods)+1)):
            if self.reporting_action[self.reporting_periods[x-1]]:
                report_col_index += 1
                for y in xrange(len(table)):
                    grade = table[y][x]
                    if (grade):
                        grade_str = "value=%5.1f" %grade
                    else:
                        grade_str = ""
                    table[y][x] = \
                         '<input type="text" class="entry-field numeric-field" ' +\
                         'id="%s-%s-%s" %s></input>' \
                         %(self.table_name, report_col_index, y, grade_str)
        self.table = table
        self.student_keylist = student_keylist
        return table, student_keylist

    def _create_get_table_header(self):
        """
        Create a list of header parameters to be used by the google table 
        widget.
        """
        header = [("name","string","Student Name")]
        for period in self.reporting_periods:
            header.append((str(period), "string", unicode(db.get(period))))
        return header

    def _create_get_return_data(self):
        """
        Create the ajax return value for a full table representation
        with the Google table. 
        """
        table_header = self._create_get_table_header()
        table_data, student_keylist = self._create_get_table_data()
        data_table = SchoolDB.gviz_api.DataTable(table_header)
        data_table.LoadData(table_data)
        json_table = data_table.ToJSon()
        json_student_keylist = simplejson.dumps(student_keylist)
        json_edited_grading_periods = simplejson.dumps(
            self.edit_grading_periods_from_get)
        return_dict = {"tableDescriptor":json_table,
                       "keysArray":json_student_keylist,
                       "editedGradingPeriods":json_edited_grading_periods,
                       "tableName":self.table_name}
        json_results = simplejson.dumps(return_dict)
        return json_results

    def _set_grading_period_grade(self, grading_period, student_key, 
                                  grading_period_results, grade_value_string):
        """
        Search through list of grading period results for the student and
        grading period. If found, set new value. If not found, create it.
        If missing any required values do nothing.
        """
        current_result = None
        grade_set = False
        if (grade_value_string and grading_period and student_key):
            grade = float(grade_value_string)
            for i, result in enumerate(grading_period_results):
                if ((result.parent_key() == student_key) and 
                    (result.grading_period.key() == grading_period.key())):
                    current_result = result
                    grading_period_results.pop(i)
                    break
            if current_result:
                grade_set = current_result.set_grade(grade)
            else:
                current_result = SchoolDB.models.GradingPeriodResult.create(
                    class_session = self.class_session, 
                    grading_period = grading_period,
                    student = student_key,
                    assigned_grade = grade)
                grade_set = True
        return grade_set

    def get_grades(self):
        if self.usable:
            return self._create_get_return_data()
        else:
            return ""

    def set_grades(self):
        """
        Set the values from the table into the students' grading period results.
        Create result if necessary.
        """
        sets_count = 0
        for x, gd_inst_keystr in enumerate(self.results_table["columns"]):
            gd_period = \
                      SchoolDB.models.get_instance_from_key_string(gd_inst_keystr)
            grading_period_results = SchoolDB.models.GradingPeriodResult.get_results_for_class_session(gd_period)
            for y, student_keystr in enumerate(self.results_table["keys"]):
                student_key = \
                            SchoolDB.models.get_key_from_string(student_keystr)
                if (self._set_grading_period_grade(gd_period, student_key, 
                                                   grading_period_results, 
                                                   self.results_table["data"][y][x])):
                    sets_count += 1
        return simplejson.dumps("%d grades set." %sets_count)


#----------------------------------------------------------------------
class QueryDescriptor:
    """
    This is a trivial class that is just a dictionary with default
    values. This defines the parameters to be used by a QueryMaker
    object in its query. If the object of the query has a class
    function "createSpecialSelectFilterActionList" then this object will be
    passed on to it by the QueryMaker.
    """
    def __init__(self):
        self.dict = {"leading_value":None,
                     "filters":(),
                     "ancestor_filter_value":None,
                     "sort_order":(),
                     "use_class_query":False,
                     "filter_by_organization":True,
                     "maximum_count":600,
                     "count_only":False,
                     "keys_only":False,
                     "return_iterator":False}

    def set(self, name, value):
        self.dict[name] = value

    def get(self, name):
        """
        Nomally this should always return a value, either that set or
        the default. If some undefined parameter is requested it will
        return None.
        """
        return self.dict.get(name, None)

#----------------------------------------------------------------------
class QueryMaker:
    """
    Perform a query for a list of objects. The arguments are:
    model_class: the class name for the objects.
    query_filters: a list of tuples of two string values
      1. parameter name and comparator
      2. comparison value (may be None or an empty string
            -- if so filter not applied)
         Note, if "None" is the value to be used for comparison then
         this value will be the string "None" 
    Leading value filters: a list of tuples of string, string, boolean
      1. Parameter name
      2. The first characters in the selected value
      3. Leading character is capitalized (boolean). This allows a lower
         case letter to be entered as the first letter when the stored value
         will be capitalized
    sort_params: a list of string values for parameters used for sorting. Note: 
      the name should begin with a "-" if reverse order desired
    ancestor: ancestor instance. Not used if value is None
    maximum_count: largest number of objects returned
    count_only: return only a count. NOTE: the function will return an integer
      if this value is true otherwise a list of 0 or more objects will be
      returned
    All arguments except model_class have usable defaults so a keyword function
    call can be made easily.
    This function will apply the filters only if a comparison values is given
    for each all of the filter definitions. Thus a complete type of query can be
    defined in a function wihout worry that some of the values used for 
    selection may not be present.
    """

    def __init__(self, model_class, descriptor):
        """
        Initialize to default values. All object variables except
        model_class must be set explicitly if different from default.
        """
        self.model_class = model_class
        self.descriptor = descriptor

    def _perform_query(self):
        """
        Process the query description to build the database query and
        perform it. Return the list of objects from the query.
        """
        if self.descriptor.get("keys_only"):
            query = self.model_class.all(keys_only=True)
        else:
            query = self.model_class.all()
        if (self.descriptor.get("filter_by_organization") and
            self.model_class.properties().has_key("organization")):
            organization = \
                SchoolDB.models.getActiveDatabaseUser().get_active_organization_key()
            query.filter("organization =", organization)
        for filter_def in self.descriptor.get("filters"):
            if (filter_def[1]):
                query.filter(filter_def[0], filter_def[1])
        if (self.descriptor.get("leading_value")):
            leading_field, leading_string = self.descriptor.get("leading_value")
            if (leading_string):               
                lower_match = self._build_lower_match_string(
                    leading_string, leading_string)
                upper_limit = self._build_upper_limit_string(
                    lower_match)
                query.filter(leading_field + ' >=', lower_match)
                query.filter(leading_field + ' <', upper_limit)
        if (self.descriptor.get("ancestor_filter_value")):
            ancestor_key_string = self.descriptor.get("ancestor_filter_value")
            ancestor = SchoolDB.models.get_instance_from_key_string(
                ancestor_key_string)
            if (ancestor):
                query.ancestor(ancestor)    
        if (self.descriptor.get("count_only")):
            entries_count = query.count(self.descriptor.get("maximum_count"))
            #Note return here with an integer
            return entries_count
        #sort only if it is not just a count
        for sort_param in self.descriptor.get("sort_order"):
            query.order(sort_param)
        if (self.descriptor.get("return_iterator")):
            #return the query itself for use as iterator
            return query
        else:
            #return the results as a list of objects
            object_list = \
                        query.fetch(int(self.descriptor.get("maximum_count")))
            return object_list

    def _build_lower_match_string(self, initial, should_capitalize):
        lower_match = initial.strip()
        if should_capitalize:
            lower_match = lower_match.title()
        return lower_match

    def _build_upper_limit_string(self, lower_match):
        chars_list = list(lower_match)
        upper_limit = ""
        if (chars_list):
            last_char = chars_list.pop()
            next_char = unichr(ord(last_char)+1)
            chars_list.append(next_char)
            for char in chars_list:
                upper_limit = upper_limit + char
        return upper_limit

    #def get_count(self):
        #"""
        #Get a count of the selection only
        #"""
        #return self._perform_query(count_only = True)

    #def get_iterator(self):
        #"""
        #Return the query object itself for use in an iterator
        #"""
        #return self._perform_query(count_only = False, 
                                    #return_query_object = True)

    def get_objects(self):
        """
        Get a list of the objects in the selection
        """
        if (self.descriptor.get("use_class_query") and 
            self.model_class.custom_query_function):
            return self.model_class.custom_query(self.descriptor)
        else:
            return self._perform_query()

    def get_keys_and_names(self, special_format = False, 
                           extra_fields = [], no_key_in_list=False):
        """
        Get a list of tuples (key, name) where name is the unichr
        function return value
        """
        object_list = self._perform_query()
        return QueryMaker.get_keys_names_fields_from_object_list( 
            object_list, special_format, extra_fields, no_key_in_list)

    @staticmethod
    def get_keys_names_fields_from_object_list(object_list,
                                               special_format = None, extra_fields = [], 
                                               no_key_in_list=False):
        """
        Generate a list and string of the keys and the values
        of a list of objects. The special_format argument takes
        a function to format the primary field if other than
        standard. extra_fields is a list of other field names 
        whose values will also be included in the result.
        The normal return form includes the object key in the 
        list element as the object values. If no_key_in_list the 
        key is not included. Keys are always returned in second
        key_list list.
        """
        result_list = []
        key_list = []
        combined_list = []
        for object in object_list:
            the_key = str(object.key())
            key_list.append(the_key)
            the_name = ""
            if (special_format):
                try:
                    the_name = object.format(special_format)
                except:
                    the_name = unicode(object)
            else:
                the_name = unicode(object)
            if no_key_in_list:
                object_values_list = [the_name]
            else:
                object_values_list = [the_key, the_name]                
            value_string = the_name
            for field in extra_fields:
                try:
                    field_value = unicode(getattr(object,field))
                except:
                    field_value = " "
                object_values_list.append(field_value)
                value_string = value_string + " " + field_value
            result_list.append(object_values_list)

            the_string = "%s|%s\n" %(value_string , the_key)
            combined_entry = {"value": the_name, "label": value_string,
                              "key" : the_key}
            combined_list.append(combined_entry)
        if (len(result_list) == 0):
            result_list = ""
        return result_list, key_list, combined_list


#----------------------------------------------------------------------
class AutoCompleteField():
    """
    This class contains all parameters necessary to generate
    the javascript for a single autocomplete field.
    """
    def __init__(self, class_name, field_name, key_field_name,
                 ajax_root_path, response_command, custom_handler):
        self.class_name = class_name
        self.field_name = field_name
        self.key_field_name = key_field_name
        self.depends_upon = []
        self.require_filled = []
        self.autocomplete_params = {'minLength':0,'delay':500}
        self.extra_params = {}
        self.dependent_fields = []
        self.local_choices_list = None
        self.use_local_choices = False
        self.ajax_root_path = ajax_root_path
        self.local_data_name = self.class_name + "_value"
        self.local_data_text = ""
        self.autocomplete_command = ""
        self.response_command = response_command
        self.custom_handler = custom_handler
        self.javascript_text = ""

    def add_dependency(self, dependency_field, is_key = True):
        self.depends_upon.append({"field":dependency_field, 
                                  "is_key":is_key})

    def add_autocomplete_params(self, param_dict):
        self.autocomplete_params.update(param_dict)

    def add_extra_params(self, param_dict):
        self.extra_params.update(param_dict)

    def set_local_choices_list(self, local_choices_list):
        self.local_choices_list = local_choices_list
        self.use_local_choices = True

    def add_child_fields(self, fields_list):
        """
        Scan all AutoCompleteField objects in the list (exept self)
        and add the object's field name to the dependent fields list
        """
        for autocomplete_field in fields_list:
            if (autocomplete_field != self):
                for field in autocomplete_field.depends_upon:
                    if (field["field"] == self):
                        self.dependent_fields.append(autocomplete_field)

    def get_query_value_field(self):
        """
        Get the name of the field that should be used to get the
        value for a query by a dependent field.
        """
        if self.local_choices_list:
            return self.field_name
        else:
            return self.key_field_name

    def _generate_data_list(self):
        if self.use_local_choices:
            code = "\n    var " + self.local_data_name + " = " + \
                 simplejson.dumps(self.local_choices_list) + ";"
            self.local_data_text += code

    def _generate_autocomplete_command(self):
        """
        Build the necessary javascript functions for this autocomplete
        field.
        """
        params_string = ""
        #create the extra params dictionary
        if (self.autocomplete_params):
            params_string = "    " + \
                          simplejson.dumps(self.autocomplete_params).strip("{}")
        if params_string:
            params_string = params_string.rstrip(',')
            params_string = params_string.replace('"','')
        self.autocomplete_command = """
  $("#%s").autocomplete({%s%s,%s
    });
  $("#%s").bind("dblclick", function(){
      $("#%s").val("");
      $("#%s").keydown();
      });""" \
            %( self.field_name,
               self._generate_source_definition(), params_string,
               self._generate_further_actions(),
               self.field_name, self.field_name, self.field_name)

    def _generate_source_definition(self):
        """
        Build the necessary javascript functions for this autocomplete
        field.
        """
        if self.use_local_choices :
            #the choices are local so just use the list
            source = "    source:  " + self.local_data_name + ","
        else:
            jq_name = '$("#%s")' %self.field_name
            extra_params = ""
            for dependent_field in self.depends_upon:
                field_string = """,
		'filter"""		
                if (dependent_field["is_key"]):
                    field_string = field_string + "key"
                field_string = field_string + "-" + \
                             dependent_field["field"].class_name + \
                             """': function() {
		    return (($('#%s').val())? $('#%s').val():'');
		}""" %(dependent_field["field"].field_name,
                       dependent_field["field"].get_query_value_field())
                extra_params = extra_params + field_string
            for dict_entry in self.extra_params.items():
                param_string = """,
		'%s': '%s'""" %(dict_entry[0], dict_entry[1])
                extra_params = extra_params + param_string
            source = """
    source: function(request, response) {
        showQueryActive(%s);
	$.ajax({
	    url: "%s",
	    data: {
	        'class': "%s",
	        'q':    request.term%s
	        },
	    success: function(ajaxResponse, textStatus, XMLHttpRequest) {
	        showQueryCompleted(%s);
	        if ((ajaxResponse === null) || (ajaxResponse.length === 0)) {
	            showQueryNoData(%s);
	            return [];
	            }
	        %s
	    },
	    error: function(xhr, textStatus, errorThrown){
	        alert(textStatus);
	        showQueryError(%s);
	        reportServerError(xhr, textStatus, errorThrown);
		}
	    });
        },
""" %(jq_name, self.ajax_root_path, self.class_name, 
      extra_params, jq_name, jq_name, self.response_command,
      jq_name)	
        return source

    def _generate_further_actions(self):
        """
        Create the the javascript code for to handle the events select.,
        focus, and change for the autocomplete object. If the parameter
        custom_select_handler is True then the standard code for the selct
        event is not created and must be written in other javascript for the
        page.
        """
        if self.custom_handler:
            return self.custom_handler
        else:
            further_actions = """	
    select: function(event, ui) {
	$("#%s").val(ui.item.value);""" %self.field_name
            if not self.use_local_choices:
                further_actions += """
				$("#%s").val(ui.item.key);
                """ %self.key_field_name				
            further_actions += """	
	return false;
	},""" 
            further_actions = further_actions + """
    focus: function(event, ui) {
	$("#%s").val(ui.item.value);
	return false;
	}""" %(self.field_name) 
            dependent_action_string = ""
            if (len(self.dependent_fields)):
                dependent_action_string = """,
    change: function(event, ui) {"""
            for dependent in self.dependent_fields:
                dep_str = """
	$("#%s").val("");
	$("#%s").val("");""" \
                        %(dependent.field_name, dependent.key_field_name)
                dependent_action_string = dependent_action_string + dep_str
                dependent_action_string = dependent_action_string 
            if (dependent_action_string):
                further_actions = further_actions +\
                                dependent_action_string + '}'
            required_field_string = ""
            if (len(self.require_filled)):
                required_filled_string = """,
    search: function(event, ui) {
	    var searchOk = true;"""
                for required in self.require_filled:
                    required_str = """
	    if ($("#%s").val().len == 0) {
		warnRequired($("#%s"));
		searchOk = false;""" \
                                 %(required.key_field_name, required.field_name)
                    required_filled_string = required_filled_string + \
                                           required_str
                required_field_string = required_field_string + """
	    return searchOk; 
	}"""
            if (required_field_string):
                further_actions = further_actions + ',' + required_field_string
            return further_actions

    def generate_javascript(self):
        self._generate_data_list()
        self._generate_autocomplete_command()
        self.javascript_text = self.local_data_text + \
            self.autocomplete_command 
        self.javascript_text = \
            self.javascript_text.replace("'!",'').replace("!'",'')
        return self.javascript_text

#----------------------------------------------------------------------       
class JavascriptGenerator():
    """"
    This class creates the javascript that is added to a webpage
    for the specific use of only that page. It may be called 
    several times which will concatenate each computed script.
    """
    script_header = """
<!-- Automatically generated code. Do not edit -->
"""
    wrapper_header = """
$(function(){
    """
    script_tail = """
  });
<!-- End automatically generated code. -->
    """

    def __init__(self, instance_string=""):
        self.params_dict = {}
        self.script_text = ""
        self.final_text = ""
        self.no_wrap_text = ""
        self.class_name = ""
        self.autocomplete_fields = []
        self.instance_string = instance_string

    def get_instance_string(self):
        return self.instance_string

    def add_javascript_params(self, custom_params_dict):
        self.params_dict.update(custom_params_dict)

    def get_javascript_param(self, param_name):
        return self.params_dict.get(param_name, "")

    def generate_params_text(self):
        if (len(self.params_dict) > 0):
            return "var localParams = %s;" \
                   %simplejson.dumps(self.params_dict)
        else:
            return ""

    def add_autocomplete_field(self, class_name, field_name = "", 
                               key_field_name="", 
                               ajax_root_path="/ajax/select",
                               response_command="response(ajaxResponse);",
                               custom_handler=""):
        if (not field_name):
            field_name = "id_" + class_name + "_name"
        if (not key_field_name):
            key_field_name = "id_" + class_name
        autocomplete_field = AutoCompleteField(class_name=class_name,
                                               field_name=field_name,key_field_name= key_field_name, 
                                               ajax_root_path=ajax_root_path,
                                               response_command=response_command,
                                               custom_handler=custom_handler)
        self.autocomplete_fields.append(autocomplete_field)
        return autocomplete_field

    def add_javascript_code(self, javascript_code):
        """
        A simple way to directly add some javascript code to be 
        added to the html page. Use this only if code is dynamic
        and cannot be added to a javascript file. This will be 
        run during the initialization phase.
        """
        self.script_text += "\n" + javascript_code + "\n"


    def add_no_wrap_javascript_code(self, javascript_code):
        """
        A simple way to directly add some javascript code to be 
        added to the html page. Use this only if code is dynamic
        and cannot be added to a javascript file. The code here will
        be inserted outside of the $(function) block. It is meant
        for variable initialization.
        """
        self.no_wrap_text += "\n" + javascript_code + "\n"

    def add_read_only(self):
        """
        Add javascript code to form page to change it to a view only
        page.
        """
        self.add_javascript_code("makePageReadOnly();")

    def get_final_code(self):
        """
        This should be called only after all fields and extra
        javascript have been set. It will return a string of
        javascript functions in a "ready" function wrapper.
        """
        for autocomplete_field in self.autocomplete_fields:
            autocomplete_field.add_child_fields(
                self.autocomplete_fields)
        for autocomplete_field in self.autocomplete_fields:
            self.script_text += autocomplete_field.generate_javascript()
        self.final_text = self.no_wrap_text + self.script_header
        self.final_text += self.generate_params_text()
        if (len(self.script_text) > 0):
            self.final_text += self.wrapper_header + \
                self.script_text + self.script_tail
        return self.final_text