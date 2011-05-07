"""
This is a conversion utility to convert from the old stlye history that used a list of individual database objects for the entries to the new version that uses a single blob that contains all of the history entry obects.
"""
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from google.appengine.api import users
from datetime import date, timedelta, datetime, time
import pickle, sys, logging
import SchoolDB.views
import SchoolDB

#----------------------------------------------------------------------  

def history_is_old_form(history_obj):
    """
    Test for histories that have not yet been converted.
    """
    return history_obj.history_entries_store == None

def convert_history(history_obj, pending_histories, pending_entries):
    """
    Convert old version history to new one in place. This moves all
    history entry objects into a blob in the history object. It needs
    to be run only once. Rather than delete the entry and put the
    modified history they are appended to a list for more efficient
    higher level batch processing.
    """
    try:
        reference_errors_count = 0
        entry_objs = history_obj.history_list
        count = len(entry_objs)
        new_entries_list = []
        for old_entry_obj_key in entry_objs:
            old_entry_obj = db.get(old_entry_obj_key)
            if (old_entry_obj):
                try:
                    new_entry = SchoolDB.models.HistEntry(
                        start_date=old_entry_obj.start_date, 
                        end_date=old_entry_obj.end_date,
                        info_string=old_entry_obj.info_string,
                        info_reference=old_entry_obj.info_reference)
                    new_entries_list.append(new_entry)
                except:
                    reference_errors_count += 1
                    pass
                pending_entries.append(old_entry_obj)
                #if (old_entry_obj.info_reference):
                    #history_obj.add_reference(old_entry_obj.info_reference)
        if (count > 0):
            #The history must have not been converted before
            history_obj.history_entries_store = pickle.dumps(new_entries_list)
        history_obj.history_list = []
        pending_histories.append(history_obj)    
        return count, reference_errors_count
    except StandardError, e:
        logging.error("Failed in convert_history: %s" %e)
        return 0,0

def commit_changes(pending_histories, pending_entries):
    try:
        db.put(pending_histories)
        db.delete(pending_entries)
    except StandardError, e:
        logging.error("failed in commit_changes: %s" %e)
    
def convert_histories_task(prior_count, perform_conversion):
    tested_count = 0
    changed_count = 0
    entries_count = 0
    commit_failures = 0
    reference_error_count = 0
    try:
        q = SchoolDB.models.History.all()
        q.filter("history_list !=", None)
       # histories=q.fetch(5000)
        #logging.info("%d old histories found" %len(histories))
        pending_histories = []
        pending_entries = []
        block_size = 500
        histories = q.fetch(block_size)
        for history_obj in histories:
            tested_count += 1
            if (history_obj.history_list):
                if (perform_conversion == "yes"):
                    num_entries, ref_errors = \
                        convert_history(history_obj, pending_histories,
                                        pending_entries)
                    reference_error_count += ref_errors
                else: 
                    num_entries = len(history_obj.history_list)                    
                changed_count += 1
                entries_count += num_entries
                #perform db actions once every 25 histories
                try:
                    if (len(pending_histories) > 25):
                        logging.info(" Starting history converison for %d histories and removed %d entries. Current ref error count %d" 
                                     (len(pending_histories), len(pending_entries), reference_error_count))
                        if (perform_conversion == "yes"):
                            commit_changes(pending_histories, pending_entries)
                        logging.info("Completed conversion")
                        pending_histories = []
                        pending_entries = []
                except StandardError,e:
                    commit_failures +=1
        #cleanup final
        if (perform_conversion == "yes"):
            commit_changes(pending_histories, pending_entries)
            logging.info("Converted %d histories" %len(pending_histories))
        result = "Converted %d history objects out of %d and removed %d history entries with %d failures. Total %d histories" \
              %(changed_count, tested_count, entries_count, commit_failures, 
                prior_count + block_size)
        logging.info(result)
        if (tested_count == block_size):
            # more histories left to check, chain another task
            prior_count += block_size
            if (prior_count <23000):
                args = 'prior_count=%d, perform_conversion="%s"' \
                     %(prior_count, perform_conversion)
                task_generator = SchoolDB.assistant_classes.TaskGenerator(
                    task_name = "Convert Histories", function=
                    "SchoolDB.utilities.convert_histories.convert_histories_task",
                    function_args=args, rerun_if_failed=False)
            else:
                logging.info("Maxed out history conversion. Some histories still not right.")
            task_generator.queue_tasks()
        return True
    except StandardError, e:
        logging.error("Convert histories failed after %d conversions:%s"
                      %(prior_count + changed_count, e))

def convert_histories(logger, perform_conversion="no"):
    args = 'prior_count=%d, perform_conversion="%s"' \
         %(0, perform_conversion)
    #q = SchoolDB.models.History.all()
    #q.filter("history_list !=", None)
    #a=q.fetch(5000)
    #logging.info("%d histories old" %len(a))
    task_generator = SchoolDB.assistant_classes.TaskGenerator(
        task_name = "Convert Histories", function=
        "SchoolDB.utilities.convert_histories.convert_histories_task",
        function_args=args, rerun_if_failed=False)
    task_generator.queue_tasks()
    logger.add_line("Queued conversions with changes. Perform conversions:" + perform_conversion)
    #logger.add_line("%d histories old" %len(a))
    

def convert_histories_single(logger, perform_conversion):
    tested_count = 0
    changed_count = 0
    entries_count = 0
    commit_failures = 0
    reference_error_count = 0
    try:
        q = SchoolDB.models.History.all()
        q.filter("history_list !=", None)
        histories=q.fetch(1000)
        logging.info("%d old histories found" %len(histories))
        pending_histories = []
        pending_entries = []
        for history_obj in histories:
            tested_count += 1
            if (history_obj.history_list):
                if (perform_conversion == "yes"):
                    num_entries, ref_errors = \
                        convert_history(history_obj, pending_histories,
                                        pending_entries)
                    reference_error_count += ref_errors
                else: 
                    num_entries = len(history_obj.history_list)                    
                changed_count += 1
                entries_count += num_entries
                #perform db actions once every 25 histories
                try:
                    if (len(pending_histories) > 25):
                        logging.info(" Starting history converison for %d histories and removed %d entries." 
                                     (len(pending_histories), len(pending_entries)))
                        if (perform_conversion == "yes"):
                            commit_changes(pending_histories, pending_entries)
                        logging.info("Completed conversion")
                        pending_histories = []
                        pending_entries = []
                except StandardError,e:
                    commit_failures +=1
        #cleanup final
        if (perform_conversion == "yes"):
            commit_changes(pending_histories, pending_entries)
            logging.info("Converted %d histories" %len(pending_histories))
        result = "Converted %d history objects out of %d and removed %d history entries with %d failures. Reference error count %d" \
              %(changed_count, tested_count, entries_count, commit_failures,
                reference_error_count)
        logging.info(result)
        logger.add_line(result)
    except StandardError, e:
        logging.error("Convert histories failed after %d conversions:%s"
                      %(changed_count, e))

def remove_unused_histories(logger):
    """
    remove histories with no info
    """
    count = 0
    del_count = 0
    pending = []
    pending_count = 0
    query = SchoolDB.models.Student.all()
    for student in query:
        pending.append(student)
        pending_count +=1
        try:
            hist = student.awards_history
            if hist:
                hist.delete()
                del_count += 1
            student.awards_history = None
        except:
            pass
        try:
            hist = student.awards_history
            if hist:
                hist.delete()
                del_count += 1
            student.awards_history = None
        except:
            pass
        try:
            hist = student.other_activities_history
            if hist:
                hist.delete()
                del_count += 1
            student.other_activities_history = None
        except:
            pass
        try:
            hist = student.post_graduation_history
            if hist:
                hist.delete()
                del_count += 1
            student.post_graduation_history = None
        except:
            pass
        count = count+1
        if (pending_count > 50):
            db.put(pending)
            pending = []
            pending_count = 0
            logging.info("Cleaned %d students %d histories" %(count, del_count))
    db.put(pending)
    logger.add_line("Checked %d students. Removed %d histories" 
                    %(count, del_count))
         
def remove_invalid_histories(logger = None, check_only = True):
    """
    Look for histories with parent entities that have been removed. If
    check_only is false then remove the history. To make the check
    efficient a list of keys of all existing entities of classes that
    could have histories is created first and tehn tested against. This
    means that the get on the parent object will not be necessary.
    """
    keys_dict= {}
    person_keylist = SchoolDB.utility_functions.get_keys_for_class("person")
    for key in person_keylist:
        keys_dict[key]=0
    logging.info("Found %d person keys" %len(person_keylist))
    sg_keylist = SchoolDB.utility_functions.get_keys_for_class(
        "student_grouping")
    logging.info("Found %d school groups keys" %len(sg_keylist))
    for key in  sg_keylist:
        keys_dict[key] = 0
    sg_keylist = SchoolDB.utility_functions.get_keys_for_class(
        "organization")
    logging.info("Found %d organization keys" %len(sg_keylist))
    for key in  sg_keylist:
        keys_dict[key] = 0
    history_keylist = SchoolDB.utility_functions.get_keys_for_class("history")
    logging.info("Found %d history keys" %len(history_keylist))
    history_entry_keylist = SchoolDB.utility_functions.get_keys_for_class("history_entry")
    logging.info("Found %d history entry keys" %len(history_entry_keylist))
    orphan_histories = []
    for history_key in history_keylist:
        if (history_key.parent() and (not keys_dict.has_key(history_key.parent()))):
            orphan_histories.append(history_key)
            logging.info("Orphan history name "+
                         (db.get(history_key).attribute_name))
    logger.add_line("Found %d orphan histories." %len(orphan_histories))
    logging.info("Found %d orphan histories." %len(orphan_histories))
    if not check_only:
        logging.info("Removing orphan histories.")
#        db.delete(orphan_histories)
        result = "History removal complete."
        logger.add_line(result)
        logging.info(result)
    
def check_history_list_length(logger, fetch_count = 2000):
    query = SchoolDB.models.History.all()
    query.filter("history_list !=", None)
    histories = query.fetch(fetch_count)
    with_list_count = 0
    with_single_list = 0
    with_multiple_list = 0
    with_long_list = 0
    total_list_entries = 0
    empty_list_count = 0
    long_list_count = 0
    single_names = []
    multiple_names = []
    try:
        for history in histories:
            if (history.history_list):
                with_list_count += 1
                l = len(history.history_list)
                total_list_entries += l
                if (l == 0):
                    empty_list_count += 1
                elif (l == 1):
                    with_single_list += 1
                    if (with_single_list < 30):
                        single_names.append(history.attribute_name)
                else:
                    with_multiple_list += 1
                    if (with_multiple_list < 30):
                        multiple_names.append(history.attribute_name)
                        if (l > 2):
                            with_long_list += 1
    except StandardError, e:
        logging.error("failed during check: %s" %e)
    result = "List:%d   Empty:%d  Single:%d  Multiple:%d  Long:%d  Total:%d      SingleNames:%s         MultipleNames: %s" \
           %(with_list_count, empty_list_count,
             with_single_list, with_multiple_list, with_long_list,
             total_list_entries, single_names, multiple_names)
    logging.info(result)
    logger.add_line(result)
