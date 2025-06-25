#!/usr/intel/bin/python3.7.4

import os # for environ and scandir
import glob # for filename expansion
from pathlib import Path # for file owner info
import shutil # for rmtree
import time # for sleep
import datetime

MINUTES_REPEAT = 30

def delete_temp_files():
    files_deleted = 0
    dirs_deleted = 0
    errors = 0

    # get username
    #os.getlogin() <- throws FileNotFoundError exception on EC Linux
    cur_user = os.environ.get("USER")
    #print(f"Current user: {cur_user}")

    # find code.* files in /tmp and delete files owned by username
    file_list = glob.glob(os.path.join("/tmp", "code.*"))
    for cur_file in file_list:
        cur_path = Path(cur_file)
        try:
            if (cur_path.owner() == cur_user):
                print(f"{cur_file} ({cur_path.owner()})")
                try:
                    os.remove(cur_file)
                    files_deleted += 1
                except:
                    print(f"ERROR: Unable to delete file {cur_file}")
                    errors += 1
        except:
            print(f"ERROR: Couldn't get owner for {cur_file}")
            continue

    # find pyright* directories in /tmp and delete dirs owned by username
    dir_list = glob.glob(os.path.join("/tmp", "pyright*"))
    for cur_dir in dir_list:
        if (not os.path.isdir(cur_dir)):
            continue

        cur_path = Path(cur_dir)
        try:
            if (cur_path.owner() != cur_user):
                continue
        except:
            print(f"ERROR: Couldn't get owner for {cur_file}")
            continue

        print(f"Directory: {cur_dir}")
        try:
            shutil.rmtree(cur_dir)
            dirs_deleted += 1
        except:
            print(f"ERROR: Couldn't remove directory {cur_dir}")
            errors += 1

    if (files_deleted > 0) or (dirs_deleted > 0) or (errors > 0):
        datestring = datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")
        print(f"Deleted {files_deleted} files and {dirs_deleted} dirs with {errors} errors at {datestring}.")

print(f"Cleaning up VS Code TMP files every {MINUTES_REPEAT} minutes. Press CTRL+C to stop.")
while(True):
    delete_temp_files()
    time.sleep(MINUTES_REPEAT * 60)
