import re, codecs, cPickle, bz2
from SchoolDB.models import *
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from google.appengine.api import users

class Muni:
    def __init__(self, municipality_id, municipality_name, \
                 province_name):
        self.municipality_id = municipality_id
        self.municipality_name = unicode(municipality_name)
        self.province_name = province_name
        self.barangays = []
        
    def add_barangay(self, barangay):
        self.barangays.append(unicode(barangay))

class LocalityLoader:
    def __init__(self, logger, input_file, provinces=[], munis=[],
                 list_municipalities=False, delete_localities=False):
        self.logger = logger
        self.input_file = input_file
        self.provinces_to_process = provinces
        self.municipalities_to_process = munis
        self.list_municipalities = list_municipalities
        self.delete_localities = delete_localities
        self.data = None
        
    def create_province(self, province_name):
        db_province = Province(name=province_name)
        self.logger.add_line("--" + province_name)
        return db_province.put()
    
    def create_municipality(self, municipality, province_object):
        db_municpality = Municipality(name = municipality.municipality_name,
                                       id = municipality.municipality_id,
                                       province = province_object)
        db_municpality.put()
        barangays = []
        for barangay_name in municipality.barangays:
            barangays.append(Barangay.create(barangay_name, db_municpality))
        db.put(barangays)
        if (self.list_municipalities):
            self.logger.add_line("%s: %d" %(municipality.municipality_name,
                                        len(barangays)))
        return db_municpality
    
    def should_process(self, name, ok_list):
        return ((len(ok_list) == 0) or \
               (ok_list.count(name) != 0))
        
    def load_database(self):
        try:
            provinces = self.data.iterkeys()
            for province_name in provinces:
                if self.should_process(province_name, 
                                       self.provinces_to_process):
                    province_object = self.create_province(
                        province_name)
                    for municipality in self.data[province_name]:
                        if (self.should_process(municipality.municipality_name,
                              self.municipalities_to_process)):                            self.create_municipality(
                                municipality, province_object)
        except StandardError, e:
            self.logger.add_line("Failed to create all provinces: " %e)
            return False
        return True
    
    def delete_class(self,class_type):
        found = True
        i=0
        while found:
            q = class_type.all()
            objects = q.fetch(500)
            found = (len(objects) > 0)
            db.delete(objects)
            i+=1
            if (found):
                self.logger.add_line("deleted %d %s group# %d" 
                                 %(len(objects), class_type, i))   
    def delete_all_localities(self):
        try:
            self.delete_class(Province)
            self.delete_class(Municipality)
            self.delete_class(Barangay)
        except StandardError, e:
            self.logger.add_line("Failed to delete all localities: " + e)
            return False
        return True
        
    def scanFile(self):
        try:
            parse_header = re.compile( \
                         r'^\<h2 id\=\"([^\"]+)\W+([^\<]+)\<br\>([^\<]+)')
            parse_list = re.compile(r'^\<li\>([^\<]+)')
            provinces = {}
            barangay_info = []
            barangay_list = False
            parsing_list = False
            f = codecs.open(self.input_file,'r','utf-8')
            for line in f:
                parsed_line = parse_header.search(line)
                if parsed_line:
                    muni = Muni(parsed_line.group(1),\
                        parsed_line.group(2),parsed_line.group(3))
                    barangay_list = True
                    province_name = unicode(parsed_line.group(3))
                    if (not provinces.has_key(province_name)):
                        provinces[province_name] = []
                    provinces[province_name].append(muni)
                    continue
                parsed_line = parse_list.search(line)
                if (barangay_list and parsed_line):
                    muni.add_barangay(parsed_line.group(1))
                    parsing_list = True
                    continue
                if ((not parsed_line) and parsing_list):
                    parsing_list = False
                    barangay_list = False
            self.data = provinces
            self.logger.add_line("Input processing complete. %d Provinces."
                                 %len(self.data))
        except StandardError,e:
            self.logger.add_line("Failed data file read: "%e)
            self.data = None
        return provinces
    
    def read_pickle(self):
        try:
            f = bz2.BZ2File(self.file, "r")
            data_string = f.read(10000000)
            self.data = cPickle.loads(data_string)
            self.logger.add_line("data bytes: %d  data_records: %d" 
                           %(len(data_string), len(data)))
        except StandardError,e:
            self.logger.add_line("Failed pickle read: "%e)
            self.data = None

    def load(self):
        data = self.scanFile()
        if (data):
            if (self.delete_localities):
                self.delete_all_localities()
            self.load_database()
    
def load_localities(logger, input_file, provinces= [], munis = [],
                    list_municipalities=False, delete_localities=False):
    loader = LocalityLoader(logger, input_file, provinces, munis,
                            list_municipalities, delete_localities)
    loader.load()        
            
            
        
        