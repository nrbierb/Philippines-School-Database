"""
A trivial update program to add the Student Major history to all students
"""
from google.appengine.ext import db
import SchoolDB.models
from datetime import date

def add_student_major_history(logger = None):
    """
    Create student major history objects and add to the student object.
    """
    q = SchoolDB.models.Student.all()
    q.filter("student_major_history = ", None)
    count = 0
    for student in q:        
        if (student.student_major_history == None):
            count += 1
            name = student.last_name
            history =  SchoolDB.models.History.create(student,
                                            "student_major", True)
            student.student_major_history = history
            try:
                student.put()
            except UnicodeEncodeError:
                # the sdk seems to have a problem with unicode characters
                # just delete the newly created history
                history.remove()
                name = unicode(student)
                logger.add_line("At count %d, skipped %s." %(count, name))
                pass            
    result = "Added %d Student Major Histories" \
          %(count)
    logger.add_line(result)


def clear_student_major_histories(c):
    """
    If there are problems with the add of the student major histories
    just delete all and remove the refernce from the student. Then everything
    can be redone cleanly.
    """
    hq=SchoolDB.models.History.all()
    hq.filter("attribute_name =", "student_major")
    history_list = hq.fetch(1000)
    history_count = len(history_list)
    db.delete(history_list)
    sq = SchoolDB.models.Student.all()
    sq.filter("student_major_history != ", None)
    student_list = sq.fetch(1000)
    student_count= len(student_list)
    change_list = []
    for student in student_list:
        student.student_major_history = None
        change_list.append(student)
        if (len(change_list) > 99):
            db.put(change_list)
            change_list = []
    db.put(change_list)
    result = "%d histories and %d students" \
           %(history_count,student_count)    
    logger.add_line(result)
    
def assign_student_majors_for_test_database(logger=None):
    """
    Assign student_majors to all student records to  use for testing.
    Do not use on real database!
    """
    q = SchoolDB.models.StudentMajor.all()
    majors = q.fetch(1000)
    num_majors = len(majors)
    sq = SchoolDB.models.Student.all()
    sq.filter("student_major_history != ", None)
    sq.filter("student_major = ", None)
    student_list = sq.fetch(1000)
    student_count = 0
    change_list = []
    for student in student_list:
        student_count += 1
        major = majors[student_count % num_majors]
        student.student_major = major
        student.student_major_change_date = date.today()
        student.student_major_history.add_or_change_entry_if_changed(
            student.student_major_change_date, "", major)
        change_list.append(student)
        if (len(change_list) > 99):
            db.put(change_list)
            change_list = []
    db.put(change_list)
    result = "Assigned %d Student Majors" \
          %(student_count)
    logger.add_line(result)
