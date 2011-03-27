#!/usr/bin/python
from datetime import date

class Student(object):
    def __init__(self, name):
        self.name = name
    def get_name(self):
        return self.name
#----------------------------------------------------------------------
class StudentsClass(object):
    
    def __init__(self, class_session, name):
        self.student = Student(name)
        self.class_session = class_session
        self.grades = []
        self.final_grade = 0.0
        
    def get_student(self):
        #return self.parent()
        return self.student
    
    
    def set_grade(self, grading_element_id, instance_id,
                  grade):
        grade = _GradingInstanceGrade(grading_element_id,
                       instance_id, grade)  
        self.grades.append(grade)
    
    def get_grading_elements(self):
        grading_plan = self.class_session.get_grading_plan()
        grading_elements = grading_plan.get_ordered_element_list()
        return grading_elements
    
    def get_grades_for_grading_element(self, grading_element):
        """
        Get a list of grade_values for all of the student's grading
        instances for a grading element
        """
        grading_element_id = grading_element.get_id()
        grades_of_desc = []
        for grade_instance in self.grades:
            (is_one, grade) = \
             grade_instance.get_grade_if_in_grading_element(
                grading_element_id)
            if (is_one):
                grades_of_desc.append(grade)
        return grades_of_desc
    
    def compute_final_grade(self):
        """
        """        
        final_grade = 0.0
        for element in  self.get_grading_elements():
            grades = self.get_grades_for_grading_element(element)
            num_grades = len(grades)
            element_grade = 0.0
            if (num_grades > 0):
                grade_sum = 0.0
                for grade in grades:
                    grade_sum += grade
                element_grade = grade_sum / num_grades
                final_grade += element_grade * \
                            element.get_percentage_of_final()
        #rescale because the percentage of final is expressed in 
        #percent, not fraction of whole
        final_grade = final_grade / 100.0
        self.final_grade = final_grade
        return final_grade
        
    def set_final_grade(self, grade):
        """
        Set the final grade manually.
        """
        self.final_grade = grade

#----------------------------------------------------------------------
class _GradingInstanceGrade():
    
    def __init__(self, grading_element_id, grading_instance_id,
                 grade):
        self.grading_element_id = grading_element_id
        self.grading_instance_id = grading_instance_id
        self.grade = grade
        
    def get_grade_if_in_grading_element(self, 
                                            grading_element_id):
        """
        Return the tuple (boolean is_one, float grade)
        """
        is_one = (self.grading_element_id == grading_element_id)
        return (is_one, self.grade)
    
#----------------------------------------------------------------------
class ClassSession(object):
    """
    This represents what vould be called a "scheduled class", a class
    taught by a teacher to a defined group of students at the same time.
    """
    
    def __init__(self):
        self.grading_plan = ClassGradingPlan()
        self.students_classes = []
            
    def get_grading_plan(self):
        return self.grading_plan
    
    def add_student(self, student):
        student_class = StudentsClass(self, student)
        self.students_classes.append(student_class)
        return student_class
        
    def get_students_classes(self):
        return self.students_classes    
        #q = StudentsClass.all()
        #q.filter("class_session =", self)
        #students_classes = q.fetch()
        #return students_classes
    
    def get_students_in_class(self):
        students = []
        for student_class in self.students_classes:
            students.append(student_class.student)
        return students
        #students_classes = self.get_students_classes()
        #students = []
        #for student_class in students_classes:
            #students.append(students_classes.parent())
    

#----------------------------------------------------------------------
class ClassGradingPlan(object):
    
    def __init__(self):
        self.element_order_index = []
        self.grading_elements = {}

    def add_element(self, grading_element_args, before_element= -1):
        """
        This is the primary way to add a grading element.
        The "grading_elament_arguments" is a dictionary that contains the
        arguments necessary for a class_grading_element. The element id
        is computed in this function. The before element argument allows 
        the element to be placed in the order sequence with -1 meaning
        add to end.
        """
        element_id = len(self.element_order_index)
        element = ClassGradingElement(grading_element_args["name"],
                element_id, grading_element_args["type"],
                grading_element_args["percent_final"], 
                grading_element_args["extra_credit"],
                grading_element_args["other_info"])
        self.grading_elements[element_id] = element
        self.reorder_element(element_id, before_element)
        return element
    
    def reorder_element(self, element_id, before_element_id):
        before_index = -1
        try: 
            if (before_element_id != -1):
                before_index = self.element_order_index.find(element_id)
            self.element_order_index.remove(element_id)            
        except ValueError:
            pass
        if (before_index == -1):
            self.element_order_index.append(element_id)
        else:
            self.element_order_index.insert(before_index, element_id)
        return self.get_ordered_element_list()
    
    def get_ordered_element_list(self):
        """
        Return a list of the elements in the order of the element index
        """
        elements = []
        for eo_index in self.element_order_index:
            elements.append(self.grading_elements[eo_index])
        return (elements)
    
    def get_element(self, element_id):
        return self.grading_elements[element_id]
    
            
#----------------------------------------------------------------------      
class ClassGradingElement(object):
    def __init__(self, name, id, type, percent_final, extra_credit = False,
                  other_info=""):
        self.name = name
        self.id = id
        self.type = type
        self.percent_final = percent_final
        self.extra_credit = extra_credit
        self.other_info = other_info
        self.instances = []
    
    def get_id(self):
        return self.id
    
    def get_percentage_of_final(self):
        return self.percent_final
    
    def add_instance(self, date):
        instance_id = len(self.instances)
        instance = _ClassGradingInstance(instance_id, date)
        self.instances.append(instance)
        return instance_id
    
    def get_instance_date(self, instance_id):
        return self.instances[instance_id]
    
    def change_date(self, instance_id, new_date):
        self.instances[instance_id].set_date(new_date)
        
    def average_grade(self):
        sum = 0
        for students_grade in grades:
            sum += students_grade.grade
        average = sum / len(grades)
        return average
    
#----------------------------------------------------------------------
class _ClassGradingInstance(object):
    def __init__(self, id, date):
        self.id = id
        self.date = date
    
    def set_date(self):
        self.date = date
        
    def get_date(self, id):
        return date
        
#----------------------------------------------------------------------
def add_instance(grading_plan, element_id, date, grade):
    grd_el = grading_plan.get_element(element_id)
    instance_id = grd_el.add_instance(date)
    students_classes = class_session.get_students_classes()
    for s in students_classes:
        grade += 2
        s.set_grade(element_id, instance_id, grade)
    
def add_element(grading_plan, name, type, percent, extra = False, other = ""):
    ge = {}
    ge["name"] = name
    ge["type"] = type
    ge["percent_final"] = percent
    ge["extra_credit"] = extra
    ge["other_info"] = other
    grading_element = grading_plan.add_element(ge)
    return grading_element.get_id()
    
if __name__ == '__main__':
    #unittest.main()
    class_session = ClassSession()
    for name in ("Joe", "Fred", "Sally", "Jane"):
        class_session.add_student(name)
    grading_plan = class_session.get_grading_plan()
    id = []
    td = []
    id.append(add_element(grading_plan,"Daily Test", "daily", 25))
    id.append(add_element(grading_plan,"Mid Term", "midterm", 25))
    id.append(add_element(grading_plan,"Final", "final", 50))
    td.append(date(2009,8,20))
    td.append(date(2009,8,25))
    td.append(date(2009,8,30))
    for i in (0,1,2):
        add_instance(grading_plan, id[i], td[i], (75 + i*5)) 
    for i in class_session.get_students_classes():
        final = i.compute_final_grade()
        print "%s: %f" %(i.get_student().get_name(), final)
    for i in class_session.get_students_in_class():
        print i.get_name()
    print "done"
    
    
    
    