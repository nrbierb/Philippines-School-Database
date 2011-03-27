"""
Test the grades action
"""


import cPickle, zlib, datetime
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
class StudentsGradingValue():
    """
    This is a small class that contains the information about a single
    grade. It is used in a list in the students grading instance so
    it has no direct reference to the ClassSession's GradingInstance.
    It contains five parameters, three of which are for tracking grade
    changes after initial entry.
    Grading Event: a reference to the unique GradinEvent for every grade
      entered
    Grade Value: float the unscaled value entered into the grading
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
    
    def __init__(self, gradingevent, gradevalue, date, editor):
        self.gradingevent = gradingevent
        self.value = gradevalue
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
    
    def add_grade(self, grade_value, date, editor):
        grade_value = StudentsGradingValue(grade_value, grading_event,
                                           date, editor)
        self.values_list.append(grade_value)
    
    def get_gradingvalue_object(self, date):
        grade_value = None
        for value in self.values_list:
            if (value.date == date):
                grade_value = value
                break
        return grade_value
    
    def edit_grade(self, new_value, editor, grading_event):
        """
        Change a grade that already has been set. 
        """
        grade_value = self.get_gradingvalue_object(grading_event)
        if (grade_value):
            grade_value.value = new_value
            grade_value.change_date = datetime.datetime.now()
            grade_value.lasteditor = editor
        return (grade_value != None)
        
    def get_grades(self, start_date = None, cutoff_date = None):
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
            #a multiple grades instance
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
    can be converted to a "blob" for starage within the database.
    All grades are stored as instances of StudentsGradingInstance
    in a dictionary keyed by the associated GradeInstance key.
    """
    
    def __init__(self, version_id = 1):
        InformationContainer.__init__(self, version_id)
        self.grades = {}
        
    def add_grade(self, grading_instance_key, date, grading_event, grade_value, 
                  editor):
        if (self.grades.has_key(grading_instance_key)):
            grading_instance = self.grades.get(grading_instance_key, 
                                           StudentsGradingInstance())
        else:
            grading_instance = StudentsGradingInstance()
            self.grades[grading_instance_key] = grading_instance
        grading_instance.add_grade(grading_event, grade_value, date, editor)
        return grading_instance
    
    def get_grade(self, grading_instance_key):
        grading_instance = self.grades.get(grading_instance_key)
        if grading_instance:
            return grading_instance.grading()
        else:
            return None
        
    def edit_grade(self, grading_instance_key, grading_event, 
                   new_value, editor):
        grading_instance = self.grades.get(grading_instance_key)
        edit_performed = False
        if grading_instance:
            edit_performed = grading_instance.edit_grade(new_value, 
                                        editor, date)
        return edit_performed
    
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
       
    def get_grades(self, instances_list, start_date = None, 
                   cutoff_date = None, summary_values = False):
        """
        Return a dictionary of grade information keyed by the 
        grading_instance. Each instance key in the instance list
        will be in the dictionary. If summary_values is True then the
        value will be the single grade which is possibly a combination
        of several tests. If False then the value will be a list of
        tuples of the grade value and id. If there is no grade
        record for that instance the value will be None.
        """
        values_dict = {}
        for key in instances_list:
            if self.grades.has_key(key):
                if summary_values:
                    values_dict[key] = \
                    self.grades[key].get_summary_grade(start_date, cutoff_date)
                else:
                    values_dict[key] = self.grades[key].get_grades(
                        start_date,cutoff_date)
            else:
                values_dict[key] = None
        return values_dict

        
#-----------------------------------------------------------------------
#The following code is used only for test
class GradeInst():
    def __init__(self, name, percent, dates, extra_credit = False):
        self.name = name
        self.percent = percent
        self.extra_credit = extra_credit
        self.dates = []
        for i in dates:
            self.dates.append(datetime.datetime(2009, i[0], i[1]))
            
    def date(self, index):
        if (index < len(self.dates)):
            return self.dates[index]
        
class StuGr():
    
    def __init__(self):
        self.gradeInst = None
        self.value = 0.0
    
def load_grade_inst(test_data):
    grade_inst_dict = {}
    for inst in test_data:
        grinst = GradeInst(inst[0], inst[1], inst[2], inst[3])
        grade_inst_dict[inst[0]] = grinst
    return grade_inst_dict
    
def load_stu_grades(inst_dict, test_data, student, editor=10):
    for i in test_data:
        key = i[0]
        value = i[1]
        index = i[2]
        grinst = inst_dict.get(key, None)
        if (grinst):
            #confirm valid grade
            date = grinst.date(index)
            student.add_grade(key, date, value, editor)
            
grinst_data = (
    ("Midterm",20.0, ((10,29),),False),
    ("Regional",10.0, ((9,20),),False),
    ("Daily", 30.0, ((6,20),(7,5),(7,15),(11,10)),False),
    ("Final", 40.0, ((12, 15),),False))
    
stu_data = (
    ("Daily", 50, 0),
    ("Daily", 75, 1),
    ("Midterm", 60, 0),
    ("Daily", 100, 2),
    ("Regional", 80, 0),
    ("Daily", 90, 3),
    ("Final", 85, 0))

quarter_start = (datetime.datetime(2009,6,8),
                 datetime.datetime(2009, 10,20), None)
quarter_end =  (datetime.datetime(2009,10,20),
                datetime.datetime(2010, 2,1), None)

if __name__ == '__main__':
    st = StudentsClassInstanceGrades()
    grade_instances = load_grade_inst(grinst_data)
    load_stu_grades(grade_instances, stu_data, st)
    inst_list = grade_instances.keys()
    for i in (0,1,2):
        grades = st.get_grades(inst_list, quarter_start[i], 
                               quarter_end[i], False)
        grades_summary = st.get_grades(inst_list, quarter_start[i], 
                                       quarter_end[i], True)
        print grades
        print grades_summary
        print "----------------------------------------------"
    blob = st.put_data()
    st1 = StudentsClassInstanceGrades.get_data(blob)
    print st1
        
        
    

