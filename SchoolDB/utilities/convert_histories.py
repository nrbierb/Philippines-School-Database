"""
This is a conversion utility to convert from the old stlye history that used a list of individual database objects for the entries to the new version that uses a single blob that contains all of the history entry obects.
"""
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from google.appengine.api import users
from datetime import date, timedelta, datetime, time
import pickle, sys
import SchoolDB.models
#----------------------------------------------------------------------  

def convert_history(history_obj, pending_histories, pending_entries):
    """
    Convert old version history to new one in place. This moves all
    history entry objects into a blob in the history object. It needs
    to be run only once. Rather than delete the entry and put the
    modified history they are appended to a list for more efficient
    higher level batch processing.
    """
    entry_objs = history_obj.history_list
    count = len(entry_objs)
    new_entries_list = []
    for old_entry_obj_key in entry_objs:
        old_entry_obj = db.get(old_entry_obj_key)
        if (old_entry_obj):
            new_entry = SchoolDB.models.HistEntry(
                start_date=old_entry_obj.start_date, 
                end_date=old_entry_obj.end_date,
                info_string=old_entry_obj.info_string,
                info_reference=old_entry_obj.info_reference)
            new_entries_list.append(new_entry)
            pending_entries.append(old_entry_obj)
            #if (old_entry_obj.info_reference):
                #history_obj.add_reference(old_entry_obj.info_reference)
    if (count > 0):
        #The history must have not been converted before
        history_obj.history_entries_store = pickle.dumps(new_entries_list)
    elif (history_obj.history_entries_store == None):
        history_obj.history_entries_store = pickle.dumps([])    
    history_obj.history_list = []
    pending_histories.append(history_obj)    
    return count

def commit_changes(pending_histories, pending_entries):
    db.put(pending_histories)
    db.delete(pending_entries)
    
def convert_histories(logger = None):
    q = SchoolDB.models.History.all()
    count = 0
    entries_count = 0
    pending_histories = []
    pending_entries = []
    histories = q.fetch(5000)
    for history_obj in histories:
        num_entries = \
            convert_history(history_obj, pending_histories, pending_entries)
        count += 1
        entries_count += num_entries
        #perform db actions once every 100 histories
        if (len(pending_histories) > 50):
            commit_changes(pending_histories, pending_entries)
            pending_histories = []
            pending_entries = []
            sys.stderr.write("> %d  %d\n" %(count, entries_count))
            sys.stderr.flush()
    #cleanup final
    commit_changes(pending_histories, pending_entries)
    result = "Converted %d history objects and removed %d history entries" \
          %(count, entries_count)
    logger.add_line(result)
    
if __name__ == '__main__':
    convert_histories()