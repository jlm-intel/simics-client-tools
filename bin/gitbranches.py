#!/usr/intel/bin/python3.7.4

import subprocess # for subprocess
import os # for environ and scandir
import sys # for exit

def get_git_branch(curpath):
    success = False
    process = subprocess.Popen(["git", "-C", curpath, "branch",
                                "--show-current"], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    branch_name, branch_error = process.communicate()
    curbranch = branch_name.decode("utf-8")
    curbranch = curbranch.replace("\n", "")
    if (curbranch == ""):
        # print ("%s - Not a git repo." % curpath)
        success = False
    else:
        # print("%s - %s" % (curpath, curbranch))
        success = True

    return (success, curbranch)

# get environment value SIMICSUSERDIR
basedir = "/tmp/localdisk/simics/jlmayfie"
try:
    basedir = os.environ['SIMICSUSERDIR']
except KeyError:
    print("ERROR: SIMICSUSERDIR variable not found, defaulting to:",
          basedir)

try:
    dirs = os.scandir(basedir)
except FileNotFoundError:
    print("ERROR: %s is not a valid directory." % (basedir))
    sys.exit(1)

print("Git branches found in %s:" % basedir)

for curdir in dirs:
    if (not curdir.is_dir()):
        # skip files
        continue

    # curdir.name - directory name
    # curdir.path - full directory path
    #print(curdir.path)
    (success, curbranch) = get_git_branch(curdir.path)
    if (success):
        print("%s - %s" % (curdir.name, curbranch))
    #else:
    #    print("%s - Not a git repo." % curdir.name)

dirs.close()
