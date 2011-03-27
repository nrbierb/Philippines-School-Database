"""
Test the chioce list javascript generator
"""

import sys
#import unittest
#import itertools
sys.path.insert(1,'/home/master/SchoolsDatabase/phSchoolDB/')
from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango()
from SchoolDB import choices, assistant_classes
#class AutoCompleteField():
    #"""
    #This class contains all parameters necessary to generate
    #the javascript for a single autocomplete field.
    #"""
    #def __init__(self, class_name, field_name, key_field_name,
                 #must_match, ajax_root_path):
        #self.class_name = class_name
        #self.field_name = field_name
        #self.key_field_name = key_field_name
        #self.depends_upon = []
        #self.autocomplete_params = []
        #self.extra_params = []
        #self.dependent_fields = []
        #self.local_choices_list = None
        #self.ajax_root_path = ajax_root_path
        #self.local_data_name = self.class_name + "_value"
        #self.local_data_text = ""
        #self.autocomplete_command = ""
        #self.result_command = ""
        #self.javascript_text = ""
        #if (must_match):
            #self.autocomplete_params.append(("mustMatch","true"))
    
    #def add_dependency(self, dependency_field_name):
        #self.depends_upon.append(dependency_field_name)
        
    #def add_dependencies(self, name_list):
        #self.depends_upon.extend(name_list)
        
    #def add_autocomplete_params(self, param_tuples):
        #for param in param_tuples:
            #self.autocomplete_params.append(param)
            
    #def add_extra_params(self, param_tuples):
        #for param in param_tuples:
            #self.extra_params.append(param)
        
    #def set_local_choices_list(self, local_choices_list):
        #self.local_choices_list = local_choices_list
        
    #def add_child_fields(self, fields_list):
        #"""
        #Scan all AutoCompleteField objects in the list (exept self)
        #and add the object's field name to the dependent fields list
        #"""
        #for autocomplete_field in fields_list:
            #if (autocomplete_field != self):
                #for field in autocomplete_field.depends_upon:
                    #if (field == self):
                        #self.dependent_fields.append(autocomplete_field)

    #def get_query_value_field(self):
        #"""
        #Get the name of the field that should be used to get the
        #value for a query by a dependent field.
        #"""
        #if self.local_choices_list:
            #return self.field_name
        #else:
            #return self.key_field_name
        
    #def _generate_data_list(self):
        #if self.local_choices_list:
            #code = self.local_data_name + " = " + str(
                #self.local_choices_list) + ";"
            #self.local_data_text += code

    #def _generate_autocomplete_command(self):
        #"""
        #Build the necessary javascript functions for this autocomplete
        #field.
        #"""
        #params_string = ""
        ##create the extra params dictionary
        #for dependent_field in self.depends_upon:
            #self.extra_params.append((dependent_field.class_name,
                #'function()  {return $("#%s").val();}' \
                #%dependent_field.get_query_value_field()))
        #if (self.extra_params):
            #params_string = ", {\n    extraParams:{"
            #for param in self.extra_params:
                #params_string = "%s\n    '%s': %s," \
                              #%(params_string, param[0], param[1])
            #params_string = params_string.rstrip(',') + "},"            
        #if (self.autocomplete_params):
            #if (not params_string):
                #params_string = ", {"
            #for param in self.autocomplete_params:
                #params_string = "%s\n    '%s': %s," \
                              #%(params_string, param[0], param[1]) 
        #if params_string:
            #params_string = params_string.rstrip(',') + "}"
        #if self.local_choices_list :
            ##the choices are local so just use the list
            #source = self.local_data_name
        #else:
            #source = '"%s/%s"' %(self.ajax_root_path, self.class_name)
        #self.autocomplete_command = """
            
  #$("#%s").autocomplete(%s%s);""" %(self.class_name, source, params_string)

    #def _generate_result_command(self):
        #dependents_string = ""
        #for dependent in self.dependent_fields:
            #dep_str = """
        #$("input#%s").flushCache();
        #$("#%s").val("");
        #$("#%s").val("");""" %(dependent.field_name, dependent.field_name, 
                  #dependent.key_field_name)
            #dependents_string = dependents_string + dep_str
        #data_str = """
        #if (data)
            #$("#%s").val(data[1]);
        #else 
            #$("#%s").val("");""" %(self.key_field_name, self.key_field_name)
        #if self.local_choices_list:
            ##there is no database key value because if there is a static list
            ##it is not a database object
            #data_str = ""
        #self.result_command = """
        
  #$("#%s").result(function(event, data, formatted) {%s%s});""" \
            #%(self.field_name, data_str, dependents_string)
        
    #def generate_javascript(self):
        #self._generate_data_list()
        #self._generate_autocomplete_command()
        #self._generate_result_command()
        #self.javascript_text = self.local_data_text + \
            #self.autocomplete_command + \
            #self.result_command
        #return self.javascript_text

##----------------------------------------------------------------------       
#class JavascriptGenerator():
    #""""
    #This class creates the javascript that is added to a webpage
    #for the specific use of only that page. It may be called 
    #several times which will concatenate each computed script.
    #"""
    #script_text = ""
    #autocomplete_fields = []
    #script_header = """
#<!-- Automatically generated code. Do not edit -->
#<script type="text/javascript">
  #$(document).ready(function(){
    #"""
    #script_tail = """
  #});
#</script>
#<!-- End automatically generated code. -->
    #"""
    
    #def add_autocomplete_field(self, class_name, field_name = "", 
                           #key_field_name="", must_match=True, 
                           #ajax_root_path="../ajaxselect"):
        #if (not field_name):
            #field_name = class_name
        #if (not key_field_name):
            #key_field_name = field_name + "Key"
        #autocomplete_field = AutoCompleteField(class_name=class_name,
             #field_name=field_name,key_field_name= key_field_name, 
             #must_match=must_match, ajax_root_path=ajax_root_path)
        #self.autocomplete_fields.append(autocomplete_field)
        #return autocomplete_field
    
    #def add_javascript_code(self, javascript_code):
        #"""
        #A simple way to directly add some javascript code to be 
        #added to the html page. Use this only if code is dynamic
        #and cannot be added to a javascript file. This will be 
        #run during the initialization phase.
        #"""
        #self.script_text += "\n" + javascript_code + "\n"
                                      
                            
    #def get_final_code(self):
        #"""
        #This should be called only after all fields and extra
        #javascript have been set. It will return a string of
        #javascript functions in a "ready" function wrapper.
        #"""
        #for autocomplete_field in self.autocomplete_fields:
            #autocomplete_field.add_child_fields(
                #self.autocomplete_fields)
        #for autocomplete_field in self.autocomplete_fields:
            #self.script_text += autocomplete_field.generate_javascript()
        #if (len(self.script_text) > 0):
            #self.script_text = self.script_header + self.script_text + \
                #self.script_tail
        #return self.script_text

if __name__ == '__main__':
    generator = assistant_classes.JavascriptGenerator()
    cy = generator.add_autocomplete_field(class_name="class_year")
    cy.set_local_choices_list(choices.ClassYearNames)
    cy.add_autocomplete_params([("minChars", 0), 
                                      ("autoFill", "true")])
    sc = generator.add_autocomplete_field(class_name="section")
    sc.add_dependency(cy)
    stu = generator.add_autocomplete_field(class_name="student",
                                           must_match=False)
    stu.add_dependencies([cy, sc])
    pv = generator.add_autocomplete_field(class_name="province")
    mun = generator.add_autocomplete_field(class_name="municipality")
    mun.add_dependency(pv)
    mun.add_autocomplete_params([("minChars", 0)])
    bg =generator.add_autocomplete_field(class_name="barangay")
    bg.add_dependencies([pv, mun])
    bg.add_autocomplete_params([("minChars", 0)])
    print generator.get_final_code()
    
    