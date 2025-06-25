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
    parser = argparse.ArgumentParser(description="Collects test logs and uploads them to a central location.")
    parser.add_argument('dir', type=str, help='Directory containing test logs (searched recursively).')
    parser.add_argument('-t', '--target', type=str, default="/nfs/site/proj/simics/users/jlmayfie/logs", help='Directory to copy test results to.')
    parser.add_argument('-r', '--reset', action='store_true', help='Reset test directories (deletes all "test.log" files under dir).')
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

    print("Directory to search for logs: " + args.dir)
    print(f"Target location for uploaded logs: {args.target}")

    # find all log files
    found_logs = find_test_logs(args.dir, "test.log")
    if (len(found_logs) == 0):
        print(f"ERROR: No test logs found in {args.dir}.")
        quit()

    # get the git branch name of the target directory
    success = False
    curbranch = ""
    success, curbranch = get_git_branch(args.dir)
    if (False == success):
        print(f"WARNING: Couldn't get git branch for {args.target}. Using 'nobranch' instead.")
        curbranch = "nobranch"

    # if user has chosen to reset, just delete all found test.log files
    if args.reset:
        print("Resetting log directories (deleting test.log files)...")
        for cur_file in found_logs:
            print(f"- Removing {cur_file}...")
            os.remove(cur_file)
    else:
        # get details for all tests
        results = collect_logs(found_logs, args.target, curbranch)
