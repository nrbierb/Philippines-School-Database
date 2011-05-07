#!/usr/bin/env python
#coding:utf-8
# Author:   --<>
# Purpose: 
# Created: 08/10/2009

from datetime import date, timedelta
import time
import exceptions
from google.appengine.ext import db
from django.utils import simplejson
import SchoolDB

class AttendenceTableStudentInformation:
    """
    Read a students attendance record and return information about
    a period for a defined set of days in a manner easily used to
    generate the webpage table.
    """
    def __init__(self, student, start_date, day_periods):
        """
        Initialize with basic information from the database.
        student: student instance reference
        start_date, end_date: datetime dates 
        """
        self.student = student
        self.start_date = start_date
        self.day_periods = day_periods
        self.student_name = student.full_name_lastname_first(
            show_middle_name=False)
        self.student_gender= student.gender
        self.student_attendance_record = self.student.attendance
        
    def get_raw_information(self):
        """
        Get the information from the database and return the name and a list
        of tuples of the morning and afternoon attendance.
        """
        try:
            info = self.student_attendance_record.get_period_info(
                self.start_date, self.day_periods)
            return (self.student_name, self.student_gender, info)
        except AttributeError:
            raise AttributeError, \
                  "Failed to get student attendance record for: %s" \
                  %unicode(self.student)
        
    
    def get_attendance_for_day(self, target_date):
        """
        Return the attendence status for the morning and afternoon
        of the day at the offset from the start day.
        """
        name, gender, info = self.get_raw_information()
        return info.get_days_attendance(target_date)
    
    def get_summary_for_period(self, start_date, end_date):
        name, gender, info = self.get_raw_information()
        return info.get_summary(start_date, end_date)
                 
#---------------------------------------------------------------------
    
class AttendanceTableCreator:
    """
    This is the primary class for the creation of an html table to be used in
    a web page to show and edit student attendance. It uses several helper
    classes to get the data from the database for the student. 
    """
    
    def __init__(self, students, end_date, section, start_date=None,
                 num_weeks=2):
        """
        Intialize with the section reference, a start date for the table,
        and an end date. Normally the end date will be the current day.
        Class users should use date.fromtimestamp(time.localtime()) to
        assure that the day is correct for the local area.
        """
        self.students = students
        self.section = section
        self.end_date = end_date
        self.start_date = start_date
        self.num_weeks = num_weeks
        self.display_end_date = \
            AttendanceTableCreator.compute_display_end_date(self.end_date)
        if not self.start_date:
            self.start_date = \
                AttendanceTableCreator.compute_default_start_date(
                self.display_end_date, self.num_weeks)
        self.days_count = self.compute_real_days()
        self.total_days_count = SchoolDB.models.get_num_days_in_period(
            self.start_date, self.display_end_date)
        self.dayperiod_type = []
        self.date_list = []
        self.day_description = []
        self.html_table = '<table id="headerTable" class="simple">'
        self.html_pretty = True
        self._load_days_lists()
    
    def create_table_description(self):
        """
        Create a description for the attendance table. This is just
        a list of header types and names.
        """
        table_description = ["Name"]
        label = 0
        for i in range(self.total_days_count):
            #The name is never shown. Assure that it is small to not
            #column resizing
            table_description.append(
                (str(i), "number"))
            table_description.append((
                str(i + self.total_days_count), "number"))
        return table_description
    
    def create_table_data(self):
        """
        Create a list of the data rows. Each row has the student name
        and the attendance data for the date range.
        """
        table_rows = []
        if (len(self.students)):
            table_rows = [self._create_student_row(student) for student
                          in self.students]
        return table_rows
    
    @staticmethod
    def compute_display_end_date(end_date):
        """
        Compute the day that is at the end of the current week. If
        the end date is in the week then display end date is
        Friday of the week, if on the weekend, then the display date
        is on the Sunday of the week.
        """
        weekday = end_date.isoweekday()
        remaining_days = 6 - weekday
        if (weekday == 7):
            remaining_days = 6
        return (end_date + timedelta(remaining_days))  

    @staticmethod
    def compute_default_start_date(display_end_date, num_weeks):
        """
        Return a date that is the default value for start based upon the
        end date. This will be num_weeks prior starting on a Sunday
        """
        # compute the end of the week that we will be displaying and then
        # move the number of weeks prior
        days_earlier = 7 * num_weeks - 1
        start_date = display_end_date - timedelta(days_earlier)
        return start_date
 
    def compute_real_days(self):
        """
        The end_date may be in the future. Calculate the number of days 
        from the start date to the present.
        """
        if (self.end_date > date.today()):
            return SchoolDB.models.get_num_days_in_period(
                self.start_date, date.today())
        else:
            return SchoolDB.models.get_num_days_in_period(
                self.start_date, self.end_date)
            
    def _create_student_row(self, student):
        student_info = AttendenceTableStudentInformation(student,
            self.start_date, self.total_days_count)
        student_name, student_gender, attend_data = \
                    student_info.get_raw_information()
        #Modify for day type.
        for i in range(self.days_count):
            if ((attend_data[2 * i] &
                SchoolDB.models.StudentAttendanceRecord.valid)
                and (self.dayperiod_type[2* i]&
                SchoolDB.models.StudentAttendanceRecord.valid)):
                attend_data[2 * i] |= self.dayperiod_type[2* i]
                attend_data[2 * i + 1] |= self.dayperiod_type[2* i + 1]
        row = [student_name]
        row.extend(attend_data)
        return row       
        
    def _compute_week_index(self, column_index):
        """
        Compute the number of weeks prior to the end_days week.
        This can be used in webpage javascript to determine which
        weeks are shown. The index will be 0 for the last week
        and increasing as the date is earlier. The lower the index
        the closer to the end_date (the most current date)
        """
        latest_week = self.end_date.isocalendar()[1]
        column_date = self.start_date + timedelta(column_index)
        week = column_date.isocalendar()[1]
        week_index = latest_week - week
        return week_index
            
    def _load_days_lists(self):
        """
        Get the type of day for all days and load into the array. Check
        the school year first. If the day is not in the school year
        mark invalid and do not test further
        """
        school_year = \
                SchoolDB.models.get_school_year_for_date(
                    self.start_date)
        for i in range(0, self.total_days_count):
            day = self.start_date + timedelta(i)
            if (not school_year or (not school_year.in_block(day))):
                morning_type = afternoon_type = 0
                day_description = "Not in school year."
            elif (i > self.days_count):
                morning_type = afternoon_type = \
                    SchoolDB.models.StudentAttendanceRecord.valid
                day_description = "In the future."
            else:
                morning_type = afternoon_type = \
                        SchoolDB.models.StudentAttendanceRecord.valid
                morning_school_day, afternoon_school_day, day_description = \
                                  SchoolDB.models.is_school_day(day,
                                                        self.section)
                if morning_school_day:
                    morning_type |= \
                        SchoolDB.models.StudentAttendanceRecord.school_day
                if afternoon_school_day:
                    afternoon_type |= \
                        SchoolDB.models.StudentAttendanceRecord.school_day
            self.dayperiod_type.append(morning_type)
            self.dayperiod_type.append(afternoon_type)
            self.day_description.append(day_description)
            self.date_list.append(day.toordinal())
        
    #----------------------------------------------------------------------
    def add_element(self, element, new_line=True, indent_count=0, 
                    row_end=False):
        """
        Add a single html element to the table. This supports pretty
        printing. If new_line the element will add a new_line after itself.
        The element will be indented by indent spaces
        """
        if (self.html_pretty or row_end):
            if new_line:
                end = "\n"
            indent = indent_count*' '
        else:
            end = ""
            indent = ""
        self.html_table = self.html_table + indent + element + end
        
    #----------------------------------------------------------------------
    def generate_header_row(self):
        """
        Create a row to be used as a header for each gender
        Use the status information from the morning period for
        each day
        """
        weekday_abbrev = ("M","T","W","T","F","S","S")
        weeknames = self._create_week_dates_text()
        self.add_element('<thead class="fixedHeader" style="width: 986px;">',True,0)
        self.add_element('<tr id="datesRow">', True, 2)
        self.add_element('<th class="attTblHeaderName attTblHeaderDateFill" id="id_tablehdr_fill" ></th>', True, 4)
        th = '<th class="attTblHeaderDate" id="id_tablehdr_firstweek" colspan="7">%s</th>' %weeknames[0]
        self.add_element(th, True, 4)
        th = '<th class="attTblHeaderDate" id="id_tablehdr_firstweek" colspan="7">%s</th>' %weeknames[1]
        self.add_element(th, True, 4)
        self.add_element('</tr>' , True, 2)
        self.add_element('<tr id="daysRow">', True, 2)
        th_name = \
            '<th class="attTblHeaderBase attTblHeaderName  ui-widget-header" name="headerTdName" id="id_table_header">Name</td>'
        self.add_element(th_name, True, 4)
        for column_index in xrange(0, self.total_days_count):
            day = self.start_date + timedelta(column_index)
            day_text = weekday_abbrev[day.weekday()]
            week = self._compute_week_index(column_index)
            date_ordinal = day.toordinal()
            if (not SchoolDB.models.StudentAttendanceRecord.is_valid(
                    self.dayperiod_type[column_index* 2])):
                title_text = day.strftime("%a, %b %d %Y") + \
                           "  Future day so it cannot be set."
                th_type = "headerTdNed ui-state-disabled"
            elif (not SchoolDB.models.StudentAttendanceRecord.is_schoolday(
                    self.dayperiod_type[column_index * 2])):
                title_text = day.strftime("%a, %b %d %Y") + \
                           "  " + self.day_description[column_index] + \
                           " so it cannot be set."
                th_type = "headerTdNsd ui-state-disabled"
            else:
                title_text = day.strftime("%a, %b %d %Y") + \
                           "  " + self.day_description[column_index]
                th_type = "headerTdSd"
            #fix for last to clean up border
            if (column_index  == self.total_days_count - 1):
                modifier = "attTblHeaderRight"
            else:
                modifier = ""
            th_text = \
              '<th id="attDay-%s" class="attTblHeaderBase attSelectable ui-widget-header %s %s" title="%s" >%s</th>' \
              %(column_index, th_type, modifier, title_text, day_text)
            self.add_element(th_text, True, 4)
        #th_text = '<th class="attTblHeaderBase attTblHeaderFiller" name="headerTdFiller" id="headerTdFiller" colspan="2"></th>'
        #self.add_element(th_text, True, 4)
        self.add_element('</tr>', True, 2, True)
        self.add_element('</thead>', True, 0)
        self.add_element('</table>')
        return self.html_table

    #----------------------------------------------------------------------
    def _warn_no_students(self):
        """
        Create a single table row with a message that no students were
        found.
        """
        message = "<tr><h2>No student records were found</h2></tr>"
        self.add_element(message,True,0,True)
            
    #----------------------------------------------------------------------
    def _create_week_dates_text(self):
        """
        Create date range descriptions of the form "Aug 30 - Sep 3"
        as a list for each week displayed. The earlist is first.
        """
        week_start = []
        week_end = []
        week_text = []
        week_start.append(self.start_date)
        week_end.append(self.start_date + timedelta(days=6))
        week_start.append(week_end[0] + timedelta(days=1))
        week_end.append(self.display_end_date)
        for i in (0,1):
            week_start_month = week_start[i].strftime("%b")
            week_start_day = week_start[i].strftime("%d").lstrip("0")
            week_end_month = week_end[i].strftime("%b")
            week_end_day = week_end[i].strftime("%d").lstrip("0")
            week_text.append("%s %s - %s %s" %(week_start_month, 
                week_start_day, week_end_month, week_end_day))
        return week_text
            

def load_daytypes_lists(start_date, total_day_count, section = None, 
                        usable_day_count = 0):
    """
    Get the type of day for all days and load into the array. Check the
    school year first. If the day is not in the school year mark
    invalid and do not test further. If a section is given, then get
    specific results for the sections class year . Finally, some days
    might be in the future and thus unusable. Mark them valid (they are
    in the school year because they passed the initial test)
    """
    if (not usable_day_count):
        usable_day_count = total_day_count
    day_type_list = []
    date_list = []
    school_year = \
            SchoolDB.models.get_school_year_for_date(start_date)
    for i in xrange(0, total_day_count):
        day = start_date + timedelta(i)
        if (not school_year or (not school_year.in_block(day))):
            morning_type = afternoon_type = 0
        elif (i > usable_day_count):
            morning_type = afternoon_type = \
                SchoolDB.models.StudentAttendanceRecord.valid
        else:
            morning_type = afternoon_type = \
                    SchoolDB.models.StudentAttendanceRecord.valid
            morning_school_day, afternoon_school_day, day_description = \
                              SchoolDB.models.is_school_day(day,
                                                    section)
            if morning_school_day:
                morning_type |= \
                    SchoolDB.models.StudentAttendanceRecord.school_day
            if afternoon_school_day:
                afternoon_type |= \
                    SchoolDB.models.StudentAttendanceRecord.school_day
        day_type_list.append((morning_type, afternoon_type))
        date_list.append(day)
    return (day_type_list, date_list)
                
########################################################################
class AttendanceResultsProcessor():
    """
    Load the returned results into the attendance record for each
    student. This uses three lists returned from the gui. The list of
    student keys maps to the rows in the attendance data list. Each row
    represents one student and contains the data already packed and
    ready for storage. The final list is the list of days with ordinals
    for each day. This is used with the attendance data list for each
    student to map the date to the data.
    """

    #----------------------------------------------------------------------
    def __init__(self, keys, attendance_data, days):
        """Constructor"""
        self.keys = keys
        self.attendance_data = attendance_data
        self.days = days
        
    def process_data(self):
        """
        This is the only function that will be called outside the class to
        perform all actions.
        """
        num_records = len(self.attendance_data)
        for i in range(len(self.keys)):
            student_key = self.keys[i]
            if (i < num_records):
                self._load_student_record(student_key,
                    self.attendance_data[i])
                
    def _load_student_record(self, student_key, students_attendance_data):
        """
        Put attendance information back into the database. It
        is already packed.
        """
        student = SchoolDB.models.Student.get(db.Key(student_key))
        if (student):
            student.attendance.save_multiple_dates(self.days,
                students_attendance_data)

#----------------------------------------------------------------------

class RosterChangeEvent():
    """
    Each event has the date (in ordinal form), the key of the
    student, and two different sets of flags: "cause" and
    "direction". There are three causes: 1."status",
    (i.e, Enrolled,DroppedOut) 2."transfer" 3."reassigned" and two
    directions: 1:add to section and 0:remove from
    section.
    """
    
    def __init__(self, student_key, event_date, cause_name, direction):
        """
        Map direction and cause into internal values and create
        the final object with all data set.
        """
        cause_names = {"student_status":0, "transfer":1, "reassign":2}
        self.student_key = student_key
        self.date_ordinal = event_date.toordinal()
        self.cause = cause_names[cause_name]
        self.direction = 1
        if (direction == "Out"):
            self.direction = 0
    
    def get_student(self):
        """
        Return the student entity.
        """
        return db.get(self.student_key)
    
    def get_event_text(self):
        """
        Return a short text describing the change: Student Name and
        reason as a report_abbrev value
        """
        report_abbrev = [("Drop Out", "Enrl"), ("Trn Out", "Trn In"),
                     ("Mv Out", "Mv In")]
        name = unicode(db.get(self.student_key))
        reason = report_abbrev[self.cause][self.direction]
        return name + " " + reason
    
    def add_to_section(self):
        return self.direction
    
    
#----------------------------------------------------------------------

class SectionRosterProcessor:
    """
    This class provides a temporary object to do all of the 
    processing needed by the section roster changes class.
    it uses the current section list to work backward in time to
    recreate the section list at the earlier dates. It returns three
    sets of data: a section list with all students who were in the
    section at some time between start and end data, an array of
    the set of the active students for each day between start and
    end date, and a list of strings, one per day, with text
    infomation about the change.
    """
    def __init__(self, current_student_list, start_date, end_date,
                 change_events_list):
        self.all_students_dict = dict([student.key(), student] \
                            for student in current_student_list)
        self.end_date_ordinal = end_date.toordinal()
        self.start_date_ordinal = start_date.toordinal()
        self.change_events = change_events_list
        self.number_of_days = self.end_date_ordinal - \
            self.start_date_ordinal + 1
        self.event_index = len(self.change_events) - 1
        self.active_dicts = [self.all_students_dict.copy()
                             for i in xrange(self.number_of_days)]
        self.event_texts = ["" for i in xrange(self.number_of_days)]
        
    def correct_list_to_end_date(self):
        """
        If some changes in the roster have happened after the
        end_date roll these back until the day after the end date
        to get a set with the correct students for the end_date.
        """
        if len(self.change_events):
            event_index = len(self.change_events) - 1
            while (self.change_events[event_index].date_ordinal >
                   self.end_date_ordinal):
                event = self.change_events[event_index]
                student_key = event.student_key
                if event.add_to_section():
                    # add is in forward direction - for reverse we
                    # remove it
                    del(self.all_students_dict[student_key])             
                else:
                    self.all_students_dict[student_key] = \
                        db.get(student_key)
                event_index -= 1
                
    def add_event_text(self, day_index, event):
        """
        Add the text description of the event to todays entry
        """
        current_text = self.event_texts[day_index]
        if len(current_text):
            current_text += ", "
        current_text += event.get_event_text()
        self.event_texts[day_index] = current_text
        
    def process_event(self, event, day_index, scratchpad_dict):
        """
        Make changes to the student list and active student set for
        the day as needed and add the event text description to the
        event_texts.
        """
        student_key = event.student_key
        if event.add_to_section():
            #The student was not in the section yesterday but
            #already have her in the list of students 
            del(scratchpad_dict[student_key])
        else:
            #The student is no longer in the section as of today.
            #Thus there has been no record of the student in our
            #dict of students as we move backwards in time
            student = db.get(student_key)
            self.all_students_dict[student_key] = student
            scratchpad_dict[student_key] = student
        self.add_event_text(day_index, event)
                        
    def process_all_events(self):
        """    
        Move backward a day at a time from the end date back to the
        start date. Process each event that occured at that day.
        """
        day_ordinal = self.end_date_ordinal
        scratchpad_dict = self.all_students_dict.copy()
        if len(self.change_events):
            for day_index in xrange(self.number_of_days-1, 0, -1):
                self.active_dicts[day_index] = scratchpad_dict.copy()
                if (self.change_events[self.event_index].date_ordinal == 
                    day_ordinal):
                    while ((self.event_index > -1) and 
                        self.change_events[
                            self.event_index].date_ordinal ==
                           day_ordinal):
                        event = self.change_events[self.event_index]
                        self.process_event(event, day_index,
                                           scratchpad_dict)
                        self.event_index -= 1
                day_ordinal -= 1
                    
    def create_daily_information_for_period(self):
        self.correct_list_to_end_date()
        self.process_all_events()
        return (self.all_students_dict, self.active_dicts, 
                self.event_texts)

#----------------------------------------------------------------------
class SectionRosterChanges(SchoolDB.assistant_classes.InformationContainer):
    """
    This class maintains a list of changes in the status of students in
    the section. Each change of student in the section is kept as a
    dated record. The section roster can be determined at any point in
    time by working from a known roster and processing each of the
    events. The processing is done from the current roster backwards
    because this will normally be used from reports for the fairly
    recent past.
    """
    
    def __init__(self, version_id = 1):
        SchoolDB.assistant_classes.InformationContainer.__init__(
            self, version_id)
        self.change_events = []
        
    def clean(self):
        """
        Remove all events from the list. This is normally done at the
        start of the year because the prior years data is unwanted.
        """
        self.change_events = []
        
    def add_change_event(self, event_date, student_key, cause_name, 
                         direction):
        """
        Create a new change event and add to list of events
        """
        event = RosterChangeEvent(event_date, student_key, cause_name, 
                         direction)
        self.change_events.append(event)
        self.change_events.sort(key=lambda event: event.date_ordinal)

    def create_period_information(self, current_student_list, start_date, 
                                  end_date):
        """
        Create a section roster processor object and use it to generate
        the complete information for the period
        """
        processor = SectionRosterProcessor(current_student_list,
                        start_date, end_date, self.change_events)
        return processor.create_daily_information_for_period()
            
#----------------------------------------------------------------------
class AttendanceReports:
    """
    Generate tables and reports of student attendance.
    """
    def __init__(self, section, start_date, end_date, parameter_dict):
        """Constructor"""
        self.section = section
        self.start_date = start_date
        self.end_date = end_date
        self.parameter_dict = parameter_dict
        self.total_days = (end_date - start_date).days
        self.table_descriptor = []
        self.table_data = []
        self.keys_list = []
        self.error = None
        self.students = section.get_inclusive_student_list_for_period(
            start_date=start_date, end_date=end_date, 
             sort_by_gender = False)
        
    @staticmethod
    def create_report_table(parameter_dict , primary_object,
            secondary_class, secondary_object):
        """
        The standard way to get a report. This will return the report
        in a manner appropriate for use in a google table for
        presentation.
        """
        if (not primary_object):
            return (None,None,None,"No class section chosen for report")
        date_str = parameter_dict.get("start_date","")
        start_date = SchoolDB.views.convert_form_date(
            date_str, (date.today() - timedelta(weeks=4)))
        date_str = parameter_dict.get("end_date","")
        end_date = SchoolDB.views.convert_form_date(date_str, date.today())
        report_type = parameter_dict.get("report_type", "Daily")
        report_generator = AttendanceReports(primary_object, start_date,
                                             end_date, parameter_dict)
        if (report_type == "Daily"):
            report_generator.generate_section_report()
        elif (report_type == "Student Summary"):
            report_generator.generate_student_report()
        return report_generator.return_table_results()
    
    def return_table_results(self):
        return(self.table_descriptor, self.table_data, self.keys_list, 
               None, self.error)
    
    def generate_section_report(self):
        """
        Generate report for a section with day by day enrollment 
        and attendance broken out by gender and morning and afternoon.
        """
        summary_line = ["No Students in Section",0,0,0,0,0,0,0.0]
        day_type_list, dates_list = \
            load_daytypes_lists(self.start_date, self.total_days,
                                self.section, self.total_days)
        self.num_schooldays = len(dates_list)
        if len(self.students):
            summary_line[0] = "Averages"
            for i in xrange(0,self.total_days):
                if (((day_type_list[i][0] & \
                    SchoolDB.models.StudentAttendanceRecord.school_day)) or
                    ((day_type_list[i][1] & \
                      SchoolDB.models.StudentAttendanceRecord.school_day))):
                    #skip non school days
                    self.keys_list.append("")
                    self.table_data.append(
                        self._generate_section_report_day(
                            dates_list[i], summary_line)[0])
            if (len(self.table_data)):
                for i in range(1,8):
                    summary_line[i] = \
                        round((float(summary_line[i])/ len(self.table_data)),1)
        self.table_data.append(summary_line)
        self.table_descriptor = \
            [('date','string','Date'),
             ('m_en', 'number', 'Male En'),
             ('f_en', 'number', 'Female En'),
             ('m_morn', 'number', 'Male Morn'),
             ('f_morn', 'number', 'Female Morn'),
             ('m_aft', 'number', 'Male Aft'),
             ('f_aft', 'number', 'Female Aft'),
             ('percent', 'number', '% Present')]
    
    def _generate_section_report_day(self, day, summary_line):
        day_name = day.strftime("%a, %b %d")
        registered_totals = [0,0]
        morning_totals = [0,0]
        afternoon_totals = [0,0] 
        for student in self.students:
            morn, aft, valid, schoolday = \
                student.attendance.get_days_attendance(day)
            if valid:
                if (student.gender == "Male"):
                    index = 0
                else:
                    index = 1
                registered_totals[index] += 1
                morning_totals[index] += morn
                afternoon_totals[index] += aft
        tot_reg = registered_totals[0] + registered_totals[1]
        if not tot_reg:
            tot_reg = 1
        tot_present_morn = morning_totals[0] + morning_totals[1] 
        tot_present_aft = afternoon_totals[0] + afternoon_totals[1]
        percent_morn = 100.0 * float(tot_present_morn) / tot_reg
        percent_aft = 100.0 * float(tot_present_aft) / tot_reg
        tot_percent = percent_morn + percent_aft
        if (tot_present_aft and tot_present_morn):
            tot_percent /= 2.0
        tot_percent = round(tot_percent,1)
        day_line = [day_name,
                    registered_totals[0],registered_totals[1],
                    morning_totals[0], morning_totals[1],
                    afternoon_totals[0],afternoon_totals[1],
                    tot_percent]
        for i in range(1, len(day_line)):
            summary_line[i] += day_line[i] 
        return day_line, summary_line
                    
            
        
    def generate_student_report(self):
        """
        Generate a student report with each line a student name and
        attendance information for one or more periods. The definition
        of the periods depends upon the period_type: "day count",
        "weekly", "monthly", "quarterly".
        """
        
        period_type = self.parameter_dict.get("period_type", "monthly")
        insert_gender_markers = self.parameter_dict.get(
            "insert_gender_markers", False)
        period = [(self.start_date,self.end_date)]
        for student in self.students:
            self.table_data.append(self._generate_single_student_report_line(
                student,period, False))
            self.keys_list.append("")
        self.table_descriptor = \
            [('name','string','Name'),
             ('days_present','number', 'Days Present'),
             ('percent_present', 'number', '% Present')]
        
    def _generate_single_student_report_line(self, student_record, periods,
                    use_period_separator = True, separator = None,):
        """
        Generate the full line for a student attendance report given a
        list of sampling periods. Each period has four columns: days
        present, %total, days absent, %total. If use_period_separator
        then insert the separator value in the array after each period.
        Periods are defined by tuples (start_date, end_date)
        """
        line = [student_record.full_name_lastname_first()]
        for period in periods:
            # if requested insert a separator between each period but
            # not between the name and the first period
            if (use_period_separator and (len(line) > 1)):
                line.append(separator)
            school_days, days_present = \
                       student_record.attendance.get_summary(
                           period[0], period[1])
            if not school_days:
                school_days = 1
            percent_present = round((100.0 *days_present / school_days), 1)
            days_absent = school_days - days_present
            percent_absent = 100.0 - percent_present
            line.extend((days_present, percent_present))
                        #days_absent, percent_absent))
        return line

class Form2Report:
    """
    Generate the Form 2 attendance report
    """
    def __init__(self, section, month, parameter_dict):
        """Constructor"""
        self.section = section
        try:
            mn, yr = month.split("/")
            self.start_date = date(int(yr), int(mn), 1)
            self.end_date = date(int(yr), int(mn)+1, 1) - timedelta(1)
        except:
            #if no success with getting month use the most recuent full month
            tm = date.today().timetuple()
            self.start_date = date(tm.tm_year,tm.tm_mon-1, 1)
            self.end_date = date(tm.tm_year, tm.tm_mon, 1) - timedelta(1)
        self.parameter_dict = parameter_dict
        self.total_days = (self.end_date - self.start_date).days + 1
        self.school = \
            SchoolDB.models.getActiveDatabaseUser().get_active_organization()
        self.data = {}
        self.extra_data = ""
        self.table_descriptor = []
        self.table_data = []
        self.keys_list = []
        self.error = None
        self.students = section.get_students()
        
    @staticmethod
    def create_report_table(parameter_dict , primary_object,
            secondary_class, secondary_object):
        """
        The standard way to get a report. This will return the report
        in a manner appropriate for use in a google table for
        presentation.
        """
        if (not primary_object):
            return (None,None,None,"No class section chosen for report")
        month = parameter_dict.get("month","")
        report_generator = Form2Report(primary_object, month,
                                             parameter_dict)
        report_generator.generate_main_table()
        report_generator.generate_extra_data()
        return report_generator.return_table_results()
    
    def return_table_results(self):
        return(self.table_descriptor, self.table_data, self.keys_list, 
               self.extra_data, self.error)
    
    def generate_extra_data(self):
        """
        This table is such a confused mess of multiple lines and
        irregular datatypes that it is best handled by simply
        generating the whole block of html code here
        """
        self.data["male_initial"], self.data["female_initial"] = \
            self.get_initial_student_count()
        
        date_line = '<p class="report-title"> %s</p>' \
                  %(self.start_date.strftime("%B %Y"))
        row1 = """
        <table>
        <tr class="tblRow"><td>%s</td><td>Enrollment For Year</td>
        <td>Male:</td><td>%d</td><td>Female:</td><td>%d</td>
        <td>Total:</td><td>%d</td></tr>
        """ %(unicode(self.school), self.data["male_initial"], 
              self.data["female_initial"], 
              self.data["male_initial"] + self.data["female_initial"])
        row2 = """
        <tr class="tblOddRow"><td>%s</td><td>Enrollment For Month</td>
        <td>Male:</td><td>%d</td><td>Female:</td><td>%d</td>
        <td>Total:</td><td>%d</td></tr>
        """ %(unicode(self.section), self.data["male_current"], 
              self.data["female_current"],
              self.data["male_current"] + self.data["female_current"])
        row3 = """
        <tr class="tblRow"><td>%s</td><td>Average Attendance</td>
        <td>Male:</td><td>%.1f</td><td>Female:</td><td>%.1f</td>
        <td>Total:</td><td>%.1f</td></tr>
        """ %("Secondary", self.data["aa_male"], self.data["aa_female"] ,
                                self.data["aa_combined"])
        row4 ="""
        <tr class="tblOddRow"><td>%s</td><td>Percentage of Attendance</td>
        <td>Male:</td><td>%.1f %% </td><td>Female:</td><td>%.1f %% </td>
        <td>Total:</td><td>%.1f %% </td></tr>
        """ %(unicode(self.school.municipality), self.data["pa_male"], 
              self.data["pa_female"], self.data["pa_combined"])
        row5 = """
        <tr class="tblRow"><td>School Days: %d</td><td>Percentage of Enrollment</td>
        <td>Male:</td><td>%.1f %% </td><td>Female:</td><td>%.1f %% </td>
        <td>Total:</td><td>%.1f %% </td></tr>
        </table>
        """ %(self.data["num_school_days"], 
              self.data["male_current"] * 100.0 / self.data["male_initial"],
              self.data["female_current"] * 100.0 / 
              self.data["female_initial"],
              (self.data["male_current"] + self.data["female_current"]) * 
              100.0 /
              (self.data["male_initial"] + self.data["female_initial"]))
        full_table = date_line + row1 + row2 + row3 + row4 + row5
        self.extra_data = simplejson.dumps(full_table)
    
    def generate_main_table(self):
        """
        Generate report for a section with day by day enrollment 
        and attendance broken out by gender and morning and afternoon.
        """
        summary_line = ["No Students in Section",0,0,0,0,0,0,"               "]
        day_type_list, dates_list = \
            load_daytypes_lists(self.start_date, self.total_days,
                                self.section, self.total_days)
        num_school_days = 0
        for day in day_type_list:
            if (((day[0] & \
                SchoolDB.models.StudentAttendanceRecord.school_day)) or
                ((day[1] & \
                  SchoolDB.models.StudentAttendanceRecord.school_day))):
                    num_school_days +=1 
        section_roster_changes = self.section.get_section_roster_changes()
        self.all_students_dict, self.active_students_daily_dicts, \
            self.event_texts = \
                        section_roster_changes.create_period_information(
                            self.students, self.start_date, self.end_date)
        if len(self.students):
            summary_line[0] = "Averages"
            for i in xrange(self.total_days):
                self.table_data.append(
                    self._generate_main_table_day(
                        i, summary_line)[0])
            if (len(self.table_data)):
                for i in range(3,7):
                    if (num_school_days):
                        summary_line[i] = \
                                round((float(summary_line[i])/ 
                                       num_school_days),1)
                    else:
                        #If no schooldays in this period then no real
                        #numbers. Just prevent a divide by 0 error.
                        summary_line[i] = 0.0
                for i in range(1,3):
                    summary_line[i] = \
                            round((float(summary_line[i])/ 
                                   self.total_days),1)  
                summary_line[7] = "               "
        self.table_data.append(summary_line)
        final_row = self.table_data[self.total_days - 1]
        if (num_school_days and len(self.table_data)):
            self.data["aa_male"] = (summary_line[3] +\
                                     summary_line[5]) / 2.0
            self.data["aa_female"] = (summary_line[4] + \
                                      summary_line[6] )/2.0 
            self.data["aa_combined"] = (self.data["aa_male"] + \
                self.data["aa_female"]) /2.0
            self.data["pa_male"] = \
                self.data["aa_male"] * 100.0 / summary_line[1]
            self.data["pa_female"] = \
                self.data["aa_female"] * 100.0 / summary_line[2]
            self.data["pa_combined"] = (self.data["pa_male"] + \
                self.data["pa_female"])/ 2.0
        else:
            #If no schooldays in this period then no real
            #numbers. Just prevent a divide by 0 error.
            self.data["pa_male"] = 0.0
            self.data["pa_female"] = 0.0
            self.data["pa_combined"] = 0.0
            self.data["aa_male"] = 0.0
            self.data["aa_female"] = 0.0
            self.data["aa_combined"] = 0.0
        self.data["num_school_days"] = num_school_days
        self.data["male_current"] = final_row[1]
        self.data["female_current"] = final_row[2]
        self.table_descriptor = \
            [('date','string','Date'),
             ('m_en', 'number', 'Male Enrolled'),
             ('f_en', 'number', 'Female Enrolled'),
             ('m_morn', 'number', 'Male Morning'),
             ('f_morn', 'number', 'Female Morning'),
             ('m_aft', 'number', 'Male Afternoon'),
             ('f_aft', 'number', 'Female Afternoon'),
             ('remarks', 'string', 'Remarks')]
    
    def _generate_main_table_day(self, day_index, summary_line):
        day_name = ("%d" %(day_index + 1))
        day = self.start_date + timedelta(day_index)
        registered_totals = [0,0]
        morning_totals = [0,0]
        afternoon_totals = [0,0] 
        for student_key in self.all_students_dict.keys():
            student = self.active_students_daily_dicts[day_index].get(student_key, None)
            if (student):
                morn, aft, valid, schoolday = \
                    student.attendance.get_days_attendance(day)
                if valid:
                    if (student.gender == "Male"):
                        index = 0
                    else:
                        index = 1
                    registered_totals[index] += 1
                    morning_totals[index] += morn
                    afternoon_totals[index] += aft
        day_line = [day_name,
                    registered_totals[0],registered_totals[1],
                    morning_totals[0], morning_totals[1],
                    afternoon_totals[0],afternoon_totals[1],
                    self.event_texts[day_index]]
        for i in range(1, len(day_line)-1):
            summary_line[i] += day_line[i] 
        return day_line, summary_line
                        
    def get_initial_student_count(self):
        """
        Get the number of students in hte section at the beginning of the
        school year.
        """
        #do not return 0 because it will generate a divide by zero in
        #the calling function
        male_count = self.section.number_male_students
        if not male_count:
            male_count = 1
        female_count = self.section.number_female_students
        if not female_count:
            female_count = 1
        return male_count, female_count
        