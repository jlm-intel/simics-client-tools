#!/usr/intel/bin/python3.7.4
# Note: Recursive glob only supported in python 3.5+
import os # file functions
import sys # argument support
import time # sleep

def safe_remove(file_to_remove, max_tries = 3, wait_seconds = 1):
    file_waiting = True
    tries = max_tries
    # only attempt to remove if file found
    if (os.path.exists(file_to_remove)):
        while ((tries > 0) and file_waiting):
            try:
                os.remove(file_to_remove)
                
                # if we're here, the operation succeeded
                file_waiting = False
                print("INFO: Removed file {}.".format(file_to_remove))
            except Exception as e:
                print(e)
                tries -= 1
                print("INFO: Failed to remove {}. {} tries remaining.".format(file_to_remove, tries))
                if (tries > 0):
                    time.sleep(wait_seconds)
                else:
                    print("WARNING: Retries exhausted. Unable to remove {}.".format(file_to_remove))
        
    else:
        print("INFO: File {} not found. (Already removed?)".format(file_to_remove))
        
def main(*args):
    print("size of args:",len(args))
    # note: can't specify args[1] for some reason? syntax error. how to get just 1 item out of the list?
    for x in args:
        safe_remove(x)


if __name__== "__main__":
    main(*sys.argv[1:])
