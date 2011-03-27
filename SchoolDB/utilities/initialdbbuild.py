import SchoolDB.models
initialbuild_logger = None
def initialbuild(loggr):
    global initialbuild_logger
    initialbuild_logger = loggr
    national = SchoolDB.models.National(name = "National DepEd")
    national.put()
    for name in ("Math", "Science", "Filipino", "English", "TLE", "AP"):
        subject = SchoolDB.models.Subject(name=name, organization = national, parent = national)
        subject.put()
    for name in ("Registered", "Dropped Out", "Graduated"):
        status = SchoolDB.models.StudentStatus(name = name, organization = national,
                                   parent = national)
        status.put()
    for name in ("Pilot", "Regular", "Remedial"):
        type = SchoolDB.models.SectionType(name = name, organization = national,
                                   parent = national)
    #school_year = SchoolYear(name = "2009-2010", 
                             #start_date = datetime.date(2009,6,10),
                             #end_date = datetime.date(2010,3,29), 
                             #organization = national, parent = national)
    #school_year.put()
    for p in (("First",07,00,07,55),("Second",7,55,8,50),
                ("Third",8,50,9,45),("Fourth",9,45,10,40),
                ("Fifth",10,40,11,35),("Lunch",11,35,12,35),
                ("Sixth",12,35,13,30),("Seventh",13,30,14,25),
                ("Eighth",14,25,15,20)):
        period = SchoolDB.models.ClassPeriod(name = p[0] + " Period",
                             organization = national, parent= national)
        try:
            period.start_time = datetime.time(p[1],p[2])
            period.end_time = datetime.time(p[3],p[4])
        except:
            pass
            #organization = national, parent= national)
        period.put()
    for name in ("School Administrator","Teacher","Database Administrator", 
                 "School DbAdministrator","School Staff", "Division Staff",
                 "Regional Staff", "Master"):
        usertype = SchoolDB.models.UserType(name = name)
        usertype.put()
    region = SchoolDB.models.Region(name="Region 9")
    region.put()
    for name in ("Cebu City", "Danue City", "Cebu Province"):
        division = SchoolDB.models.Division(name = name, region = region)
        division.put()
    for name in ("Compostela NHS", "Compostela SciTec", "Practice School 2",
                 "Practice School 1"):
        school = SchoolDB.models.School(name=name, division = division)
        school.put()
    master_person = SchoolDB.models.Administrator(first_name = "Neal", last_name = "Bierbaum", 
                                  organization = school, gender = "Male")
    master_person.put()
    masterDBUser = SchoolDB.models.DatabaseUser(name = "Neal Bierbaum", 
                                person = master_person,
                                organization = school, 
                                email="nrbierb@gmail.com",
                                user_type = usertype)
    masterDBUser.post_creation()
    teacher = SchoolDB.models.Teacher(first_name = "A", middle_name = "Db", last_name = "Tester",
                      organization = school)
    teacher.put()
    teacher_user = SchoolDB.models.DatabaseUser(name = "A Db Tester", person=teacher, 
                                organization = school,
                                email = "ph.db.tester@gmail.com", 
                                usertype = usertype)
    teacher_user.post_creation()
    teacher = SchoolDB.models.Teacher(first_name = "A", middle_name = "Practice", 
                     last_name = "TeacherCmpstla", organization = school)
    teacher.put()
    teacher_user = SchoolDB.models.DatabaseUser(name = "A Practice TeacherCmp", 
                                person=teacher, organization = school,
                                email = "ph.db.cnhs.teacher@gmail.com", 
                                usertype = usertype)
    teacher_user.post_creation()
    teacher = SchoolDB.models.Teacher(first_name = "A", middle_name = "Practice", 
                      last_name = "TeacherSci", organization = school)
    teacher.put()
    teacher_user = SchoolDB.models.DatabaseUser(name = "A Practice TeacherSci", 
                                person=teacher, organization = school,
                                email = "ph.db.scitech.teacher@gmail.com", 
                                usertype = usertype)
    teacher_user.post_creation()
    initialbuild_logger.add_line ("Intial creation complete.")
    