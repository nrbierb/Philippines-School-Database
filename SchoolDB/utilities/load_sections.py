"""
Load a csv file with section records in csv form into the database.
"""
import csv

def read_file(file_name):
    """
    Open the csv file, then use a csv DictReader to convert to
    a list of dictionaries, one per line
    """
    f = open(file_name)
    lines = []
    reader = csv.DictReader(f)
    for line in reader:
        lines.append(line)
    f.close()
    return lines

def delete_sections_at_school(school):
    num_found = 1
    while (num_found > 0):
        q = Section.all()
        q.filter("school =", school)
        sections = q.fetch(1000)
        num_found = len(sections)
        append_result_line("%d to delete" %num_found)
        db.delete(sections)

def load_sections(school_name, file_name):
    records = load_sections.read_file(file_name)
    school = local_utilities.get_object(School, school_name)
    if (not school):
        return append_result_line("ERROR: UNKNOWN SCHOOL: " + school_name)
    load_sections.delete_sections_at_school(school)
    for record in records: 
        section = Section(name = record["name"],
                          class_year = record["class_year"],
                          parent = school)
        section.put()
        section.post_creation()
    return append_result_line("Completed. Added %d records." 
                               %(len(records)))
