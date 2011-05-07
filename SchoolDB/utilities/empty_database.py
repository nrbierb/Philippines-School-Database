from google.appengine.ext import db
import SchoolDB
import SchoolDB.models
import SchoolDB.local_utilities_functions
import logging

def empty_database(logger, initial_text = "Starting to Empty"):
    logger.add_line(initial_text)
    for del_class in [
        #SchoolDB.models.HistoryEntry, 
        SchoolDB.models.History
        #SchoolDB.models.Contact, 
        #SchoolDB.models.National, 
        #SchoolDB.models.Region,
        #SchoolDB.models.Division, 
        #SchoolDB.models.Province, 
        #SchoolDB.models.Municipality, 
        #SchoolDB.models.Community, 
        #SchoolDB.models.StudentStatus,
        #SchoolDB.models.Subject, 
        #SchoolDB.models.SchoolDay, 
        #SchoolDB.models.SchoolYear,
        #SchoolDB.models.ClassPeriod, 
        #SchoolDB.models.ClassSession,
        #SchoolDB.models.Classroom,
        #SchoolDB.models.SpecialDesignation, 
        #SchoolDB.models.Section,
        #SchoolDB.models.SectionType,
        #SchoolDB.models.GradingInstance,
        #SchoolDB.models.GradingPeriod,
        #SchoolDB.models.Family,
        #SchoolDB.models.ParentOrGuardian,
        #SchoolDB.models.StudentAttendanceRecord,
        #SchoolDB.models.Student,
        #SchoolDB.models.StudentTransfer,
        #SchoolDB.models.StudentsClass,
        #SchoolDB.models.VersionedText,
        #SchoolDB.models.VersionedTextManager
        #DO NOT UNCOMMENT THESE!
        #SchoolDB.models.Teacher, 
        #SchoolDB.models.UserType,
        #SchoolDB.models.Administrator, 
        #SchoolDB.models.School, 
        #SchoolDB.models.DatabaseUser
        ]:
        logger.add_line("Starting delete for " + del_class.classname)
        task_name = "Empty Database " + del_class.classname
        query = del_class.all(keys_only=True)
        args = "classname=%s" %str(del_class)
        task_generator = SchoolDB.assistant_classes.TaskGenerator(
                    task_name = task_name, function = "db.delete", \
                    function_args = "", query_iterator=query, 
                    rerun_if_failed = False)
        task_generator.queue_tasks()
        #keys_blocks = SchoolDB.models.get_blocks_from_iterative_query(
                #query, 100)
        #task_count = 0
        #for block in keys_blocks:
            ##do not create task if block is empty
            #if block:
                ##put lists of keys in argument so all can be handled at the
                ##end by a single function call
                #keystrings = [str(key) for key in block]
                #SchoolDB.local_utilities_functions.queue_tasks(
                    #task_name = task_name, function =\
                    #"SchoolDB.utilities.empty_database.delete_database_objects", 
                    #function_args = args)
                #task_count += 1
        logger.add_line("All tasks successfully enqueued.")
    logger.add_line("All emptied")
    return (True)

def delete_database_objects(args_dict):
    """
    A trivial action to delete all database entities with the
    listed keys and report the result. The list of keys is sent in a 
    compressed pickle to limit data transfer
    """
    try:
        classname = args_dict.get("classname", "Unknown")
        delete_keystrings = args_dict.get("delete_keys", [])
        if delete_keystrings:
            count = len(delete_keystrings)
            delete_keys = [db.Key(key_string) for key_string in delete_keystrings]
            #delete a block of 20 each call
            block_end = 19
            while delete_keys:
                key_block = delete_keys[0:block_end]
                db.delete(key_block)
                del delete_keys[0:block_end]
            logging.info("Completed delete of %d %s" %(count, classname))
        return True
    except StandardError, e:
        info = "delete_database_objects for class %s failed: %s" \
             %(classname, e)
        logging.error(info)
        return False
    