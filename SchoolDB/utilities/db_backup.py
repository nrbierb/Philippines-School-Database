#!/usr/bin/python2.5
"""
Download or upload all of the database
using the bulkloader with no special configuration files
"""
import sys, os, optparse, datetime

class TransferClass:
    def __init__(self, direction, local_dir, app_id, url_address=""):
        self.direction = direction
        self.local_dir = local_dir
        self.url_address = url_address
        self.app_id = app_id
        if not url_address:
            self.url_address = \
                "http://" + app_id + ".appspot.com/_ah/remote_api"
        self.app_id = app_id
    
    def build_command(self):
        date_string = datetime.date.today().strftime("%m%d%y")
        filename = "%s%s.%s.sqlite3" %(self.local_dir, self.app_id, 
                                        date_string)
        return("cd /home/master/SchoolsDatabase/google_sdk.1.5.2/google_appengine; " +
            "echo 'molemo4d' | " + "python2.5 bulkloader.py --" + 
            self.direction + " --app_id=" + self.app_id + 
            " --url=" + self.url_address + 
            " --filename=" + filename + 
            " --batch_size=20 --rps_limit=500 " + 
            "--email='nrbierb@gmail.com' --passin ")
    
    def perform_transfer(self):
        print ">>>>>>>>>>>>> starting " + self.direction + " <<<<<<<<<<<<<<"
        command = self.build_command()
        os.system(command)
        print "<<<<<<<<<<<<<< finished " + self.direction + " >>>>>>>>>>>>>"
        print 
    
if __name__ == "__main__":
    p = optparse.OptionParser()
    p.add_option("--dir", type="string", dest="local_dir")
    p.add_option("--down", action="store_const", const="dump", 
                 dest="direction")
    p.add_option("--up", action="store_const", const="restore", 
                 dest="direction")
    p.add_option("--url", type="string", dest="url_address")
    p.add_option("--app_id", type="string", dest="app_id")
    p.set_defaults(local_dir="/home/master/SchoolsDatabase/datastore/dump/",
                   direction="dump",
                   url_address="",
                   app_id="pi-schooldb")
    opt, args = p.parse_args()
    #>>restore to local database
    loader = TransferClass(direction= opt.direction, 
                           local_dir = opt.local_dir,
                           url_address = opt.url_address,
                           app_id = opt.app_id)
    loader.perform_transfer()
    print "---------------- Completed dump/restore ------------------"
        