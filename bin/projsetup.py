#!/usr/intel/bin/python3.7.4
import os # path functions
import sys # argument processing
import glob # filename expansion

# Note: Recursive glob only supported in python 3.5+

# Can pass an alternate Simics install path to search for simics-6.x.y installations:
#
# Example:
# ./projsetup.py  /nfs/site/disks/ssg_stc_simics_base-packages-release/simics-6/

def main(*kwargs):

    # default values
    dir_search_string = "simics-6.*"
    ver_substr = "simics-"
    install_path = "/tmp/localdisk/simics/jlmayfie/simics-6"
    ver_a = 0
    ver_b = 0
    ver_c = 0
    latest_path = ""
    passes = 0
    total_entries = 0
    command_line = ""

    # version variables (ver_a-ver_c) represent sections in the simics version stamp.
    # example: simics-6.0.51:
    # ver_a = 6, ver_b = 0, ver_c = 51

    # process arguments
    for arg in kwargs:
        print("DEBUG: arg:",arg)
        install_path = arg
    
    #searchspec = os.path.join(dirname, '**')
    #searchspec = os.path.join(searchspec, 'SUITEINFO')
    searchspec = os.path.join(install_path, dir_search_string)
    filelist = glob.glob(searchspec, recursive=True)
    if len(filelist) == 0:
        print ("ERROR: No files found matching", searchspec)
    #return sorted(filelist)
    #filelist = sorted(filelist)
    for curfile in filelist:
        total_entries += 1
        #print(curfile)
        # isolate version string into a separate string
        substr_loc = curfile.rindex(ver_substr)
        if (substr_loc == -1):
            print("WARNING: Can't find ver_substr",ver_substr)
            continue
        locfile = curfile[(substr_loc + len(ver_substr)):]
        #print(locfile)
        ver_comps = locfile.split(".")
        if (len(ver_comps) < 3):
            print("WARNING: Can't find three version components in",locfile)
            continue
        locver_a = int(ver_comps[0])
        locver_b = int(ver_comps[1])
        locver_c = int(ver_comps[2])
        if ((locver_a >= ver_a) and (locver_b >= ver_b) and (locver_c >= ver_c)):
            ver_a = locver_a
            ver_b = locver_b
            ver_c = locver_c
            latest_path = curfile
            passes = total_entries
    print("INFO: Found",latest_path,"in",passes,"passes out of",total_entries,"total entries.")
    command_line = os.path.join(latest_path, "bin/project-setup")
    print("INFO: Attempting to run", command_line)
    cmd_result = os.system(command_line)
    if (cmd_result == 0):
        print("INFO: Command returned successfully.")
    else:
        print("ERROR: Command failed.")
        
    
if __name__== "__main__":
    main(*sys.argv[1:])
    
