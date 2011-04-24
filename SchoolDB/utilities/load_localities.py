import cPickle, bz2

def create_province(province_name):
    db_province = Province(name=province_name)
    return db_province.put()

def create_municipality(municipality, province_object):
    db_municpality = Municipality(name = municipality.municipality_name,
                                   id = municipality.municipality_id,
                                   province = province_object)
    db_municpality.put()
    barangays = []
    for barangay_name in municipality.barangays:
        barangays.append(Barangay.create(barangay_name, db_municpality))
    db.put(barangays)
           
def load_database(data, provinces):
    try:
        provinces = data.iterkeys()
        for province_name in provinces:
            process_province = True
            if (len(provinces) !=0):
                process_province = provinces.count(province_name)
            if (process_province):
                province_object = load_localities.create_province(
                    province_name)
                for municipality in data[province_name]:
                    usable = ["Danao City", "Compostela", "Liloan", 
                                  "Mandaue City"]
                    if (usable.count(municipality.municipality_name) > 0):
                        append_result_line( municipality.municipality_name)
                        load_localities.create_municipality(municipality,
                                                            province_object)
    except StandardError, e:
        append_result_line("Failed to create all provinces: " + e)
        return False
    return True

def delete_class(class_type):
    found = True
    i=0
    while found:
        q = class_type.all()
        objects = q.fetch(1000)
        print len(objects)
        found = (len(objects) > 0)
        db.delete(objects)
        i+=1
        append_result_line("deleted %d %s" %(i, class_type))

def delete_all_localities():
    try:
        load_localities.delete_class(Province)
        load_localities.delete_class(Municipality)
        load_localities.delete_class(Barangay)
    except StandardError, e:
        append_result_line("Failed to delete all localities: " + e)
        return False
    return True
    
def load_localities(pickle_file, provinces= []):
    data = local_utilities.read_pickle(pickle_file)
    if (data):
        #if (load_localities.delete_all_localities()):
            #pass
        load_localities.load_database(data, provinces)
    
            
            
            
        
        