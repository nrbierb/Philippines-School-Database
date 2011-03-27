#!/usr/bin/python2.5
"""
Download or upload all of the database
Classes affected are:
HistoryEntity
History
Organization
Contact
StudentStatus
MultiLevelDefined
Person
StudentGrouping
GradingInstance
Family
StudentAttendanceRecord
GradingPeriodResults
StudentsClass
UserType
DatabaseUser
VersionedText
"""
import sys, os, optparse

#data_classes = ["HistoryEntry","History","Organization","Contact",
           #"StudentStatus","MultiLevelDefined","Person","StudentGrouping",
           #"GradingInstance","Family","StudentAttendanceRecord",
           #"GradingPeriodResults","StudentsClass","UserType",
           #"DatabaseUser","VersionedTextManager","VersionedText"]
data_classes = ["Person"]
class TransferClass:
    def __init__(self, direction, local_dir, url_address, app_id):
        self.direction = direction
        self.local_dir = local_dir
        if (self.direction == "--dump"):
            os.mkdir(local_dir)
        self.url_address = url_address
        self.app_id = app_id
    
    def build_command(self, data_class):
        return("cd /home/master/SchoolsDatabase/google_sdk.1.3.3/google_appengine; " +
            "echo 'molemo4d' | "+
            "python2.5 bulkloader.py " + self.direction + 
            " --app_id=" + self.app_id + 
            " --url=" + self.url_address + "/remote_api --kind=" + 
            data_class + " --filename=" + self.local_dir + "/" 
            + data_class + ".dat --batch_size=40 --rps_limit=500 " + 
            "--email='nrbierb@gmail.com' --passin ")
    
    def process_class(self, data_class):
        print ">>>>>>>>>>>>> starting " + data_class + " <<<<<<<<<<<<<<"
        command = self.build_command(data_class)
        os.system(command)
        print "<<<<<<<<<<<<<< finished " + data_class + " >>>>>>>>>>>>>"
        print 
    
if __name__ == "__main__":
    p = optparse.OptionParser()
    p.add_option("--dir", type="string", dest="local_dir")
    p.add_option("--down", action="store_const", const="--dump", 
                 dest="direction")
    p.add_option("--up", action="store_const", const="--restore", 
                 dest="direction")
    p.add_option("--url", type="string", dest="url_address")
    p.add_option("--app_id", type="string", default="ph-scldb")
    opt, args = p.parse_args()
    #loader = TransferClass(direction=opt.direction, 
                           #local_dir = opt.local_dir,
                           #url_address = opt.url_address,
                           #app_id = opt.app_id)
    #loader = TransferClass(direction= "--dump", 
                           #local_dir = "/home/master/SchoolsDatabase/datastore/dump/pi-schooldb-dev.full",
                           #url_address = "http://localhost:8000",
                           #app_id = "pi-schooldb-dev")
    loader = TransferClass(direction= "--restore", 
                           local_dir = "/home/master/SchoolsDatabase/datastore/dump/pi-schooldb-dev.full",
                           url_address = "http://ph-scldb.appspot.com",
                           app_id = "ph-scldb")
    for data_class in data_classes:
        loader.process_class(data_class)
    print "---------------- Completed dump/restore ------------------"
        