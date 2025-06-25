#!/usr/intel/bin/python3.12.3

# This script searches for all "test.log" files under the specified directory, and then creates a unique
# directory under the target location and copies all contents from the parent test directory into the
# unique target location. The purpose here is to be able to quickly gather logs from a local repo into
# a common location for easy diffing.
#
# You can optionally run greperrors inside individual target directories to generate files that extract
# errors/failures/exceptions into separate files, or run 'logerrors' to generate those files in all
# directories under /nfs/site/proj/simics/users/jlmayfie/logs (or your current target directory).

import argparse # argument parsing
import glob # recursive file search
import os # path functions
import datetime # fromtimestamp
import subprocess # Popen

from shutil import copyfile

STYLE_OS = 0
STYLE_LINUX = 1
STYLE_WINDOWS = 2

class TestResult:
    RESULT_ERROR = -1
    RESULT_SUCCESS = 0
    RESULT_FAILURE = 1
    RESULT_TIMEOUT = 2

    def __init__(self, testname, filename):
        self.testname = testname
        self.filename = filename
        self.totalseconds = 0.0
        self.failures = []
        self.timeouts = []
        self.successes = []
        self.run_targets = []
        self.fmod_configs = []
        self.param_dicts = []

def parse_args():
    # collectdefaults.py fusesdir targetdir
    parser = argparse.ArgumentParser(description="Recursively finds default_fuse_values.txt files and copies uniquely-named versions to a given target directory.")
    parser.add_argument('-f', '--fusedir', type=str, default=".", help='Directory to recursively search for default_fuse_values files.')
    parser.add_argument('-t', '--targetdir', type=str, required=True, help='Directory to copy renamed fuse files to.')
    args = parser.parse_args()
    return args

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

def tail(filename, lines=10):
    # adapted from: https://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-similar-to-tail

    if lines == 0:
        print("ERROR: Must specify at least 1 line to return.")
        return []

    f = open(filename, "rb")

    BUFSIZ = 1024
    f.seek(0, 2)
    remaining_bytes = f.tell()
    size = lines + 1
    block = -1
    data = []

    while size > 0 and remaining_bytes > 0:
        if remaining_bytes - BUFSIZ > 0:
            # Seek back one whole BUFSIZ
            f.seek(block * BUFSIZ, 2)
            # read BUFFER
            bunch = f.read(BUFSIZ)
        else:
            # file too small, start from beginning
            f.seek(0, 0)
            # only read what was not read
            bunch = f.read(remaining_bytes)

        bunch = bunch.decode('utf-8')
        data.insert(0, bunch)
        size -= bunch.count('\n')
        remaining_bytes -= BUFSIZ
        block -= 1

    f.close()
    return ''.join(data).splitlines()[-lines:]

def find_test_logs(dir, filename = "test.log"):
    foundfiles = []
    # confirm directory exists
    if (not os.path.exists(dir)) or (not os.path.isdir(dir)):
        print(f"ERROR: {dir} does not exist or is not a directory!")
        return foundfiles

    # do recursive search for files matching filename
    searchspec = os.path.join(dir, '**')
    searchspec = os.path.join(searchspec, filename)
    foundfiles = glob.glob(searchspec, recursive=True)

    # return list of filenames
    return foundfiles

# returns test results plus name of directory to create
def extract_result(filename, tail_lines, branchname):
    result = TestResult.RESULT_ERROR
    testname = ""
    dirname = ""
    result_text = "ERROR"

    STATE_SEARCHING = 0
    STATE_TESTS = 1

    # remove everything up to "test\"
    # test_str = os.path.sep + "test" + os.path.sep
    test_str = "test" + os.path.sep

    # remove "\test.log" and beyond
    # log_str = os.path.sep + "0" + os.path.sep + "test.log"
    log_str = os.path.sep + "test.log"

    testpos = filename.find(test_str)
    if (testpos == -1):
        print(f"ERROR: Could not find {test_str} in {filename}.")
        return result, dirname

    logpos = filename.find(log_str)
    if (logpos == -1):
        print(f"ERROR: Could not find {log_str} in {filename}.")
        return result, dirname

    # skip the "test/"
    testname = filename[testpos + 5:logpos]
    testname = testname.replace(os.path.sep, "-")
    # print(f"TEST: {testname}")

    cur_state = STATE_SEARCHING

    for cur_line in tail_lines:
        if (cur_state == STATE_SEARCHING):
            if (cur_line.find("### SUMMARY") == -1):
                # skip anything before the summary section
                continue
            else:
                # process all subsequent lines
                cur_state = STATE_TESTS
        else:
            # determine what kind of result this is
            stripped = cur_line.strip()
            if stripped.startswith("TIMEOUT: "):
                if (TestResult.RESULT_TIMEOUT > result):
                    result = TestResult.RESULT_TIMEOUT
                    result_text = "TIMEOUT"
            elif stripped.startswith("FAILURE: "):
                if (TestResult.RESULT_FAILURE > result):
                    result = TestResult.RESULT_FAILURE
                    result_text = "FAILURE"
            elif TestResult.RESULT_SUCCESS > result:
                result = TestResult.RESULT_SUCCESS
                result_text = "SUCCESS"

    # get test.log date/time
    mtime = os.path.getmtime(filename)
    dtime = datetime.datetime.fromtimestamp(mtime)
    # don't need seconds in string ("%S" is for 2-digit seconds)
    # don't need year in string ("#Y" is for 4-digit year)
    timestring = dtime.strftime("%m-%d-%H-%M")

    dirname = f"{testname}-{branchname}-{result_text}-{timestring}"
    return result, dirname

# TODO - major overhaul; this should copy log results to appropriately-named directories rather than parse
#        log output and return results
def collect_logs(filelist, target, branchname):
    logs_processed = 0

    # collect test results (at end of file)
    for curfile in filelist:
        # print(f"FILE: {curfile}")
        curlines = tail(curfile)
        TestResult.RESULT_ERROR
        testname = ""
        curresult, testname = extract_result(curfile, curlines, branchname)
        if (curresult is not TestResult.RESULT_ERROR):
            logs_processed += 1
            # print(f"{testname} - {curresult}")
            # create target directory
            target_path = os.path.join(target, testname)
            if (os.path.exists(target_path)):
                print(f"WARNING: {target_path} already exists. Re-using...")
            else:
                os.makedirs(target_path)

            # get source path from test.log filename
            sourcedir = os.path.dirname(curfile)
            # print(f"sourcedir: {sourcedir}")

            # copy source contents to target
            print(f"Copying files from {sourcedir}...")
            filenames = [f for f in os.listdir(sourcedir) if os.path.isfile(os.path.join(sourcedir, f))]
            for cursource in filenames:
                sourcefile = os.path.join(sourcedir, cursource)
                if os.path.isfile(sourcefile):
                    targetfile = os.path.join(target_path, cursource)
                    copyfile(sourcefile, targetfile)

    return logs_processed


if __name__ == "__main__":
    args = parse_args()

    print("Directory to search for default_fuse_values.txt: " + args.fusedir)
    print(f"Target location for renamed files logs: {args.targetdir}")

    # find all default_fuse_values files
    found_files = find_test_logs(args.fusedir, "default_fuse_values.txt")
    if (len(found_files) == 0):
        print(f"ERROR: No test logs found in {args.fusedir}.")
        quit()
    else:
        print(f"INFO: Found {len(found_files)} default_fuse_values files.")

    # confirm that target directory exists
    if (os.path.exists(args.targetdir)):
        if (not os.path.isdir(args.targetdir)):
            print(f'ERROR: {args.targetdir} exists but is not a directory.')
            quit()
    try:
        os.makedirs(args.targetdir, exist_ok=True)
    except OSError as e:
        print(f'ERROR: verify_directory unable to make directory {args.targetdir} ({e.strerror})')

    for cur_file in found_files:
        # get actual filename
        filepart1 = os.path.basename(cur_file)
        # get name of parent directory
        filepart2 = os.path.basename(os.path.dirname(cur_file))

        target_path = os.path.join(args.targetdir, filepart2 + "_" + filepart1)
        print(f"target_path: {target_path}")

        try:
            copyfile(cur_file, target_path)
        except OSError as e:
            print(f'ERROR: Unable to copy {cur_file} to {target_path} ({e.strerror})')
