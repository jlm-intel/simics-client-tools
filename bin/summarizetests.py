#!/usr/intel/bin/python3.12.3

# This script searches a given test archive directory for all instances of "test.log" and extracts test information
# from each one, to present a summary of the test content. The resulting summary includes some useful details:
# - Number of test successes, failures, and timeouts (Each test directory technically represents a test "suite"
# that can run several individual tests.)
# - Complete sorted list of tests found in the archive directory.
# - The shortest N tests that timed out and failed. (To help you quickly choose tests to run locally for debugging.)
# - Individual test parameters.
# - Commands you can copy/paste to run the tests locally (optionally formatted for Windows or Linux)
# - All FMOD configurations used (and how often)
# - All Test scripts used (and how often)
# - All simics parameters used for each test (and how often)
#
# - Use the --num-tests option to set the maximum number of tests to get detailed info for.
# - Use --platform to specify the name of the platform (this is required to get accurate test command lines for vp tool.)

import argparse # argument parsing
import glob # recursive file search
import os # path functions
import ast # ast.literal_eval

STYLE_OS = 0
STYLE_LINUX = 1
STYLE_WINDOWS = 2

class TestResult:
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
    parser = argparse.ArgumentParser(description="Summarizes results of downloaded pretest logs.")
    parser.add_argument('dir', type=str, help='Directory containing extracted pretest logs.')
    parser.add_argument('-n', '--num-tests', type=int, default=3, help='Number of individual test details to return in summary results. Default is 3.')
    parser.add_argument('-p', '--platform', type=str, default="novalake-s-6.0", help='Platform string to use in test commands. Default is novalake-s-6.0')
    parser.add_argument('-w', '--windows', action='store_true', help='Force test command to Windows format.')
    parser.add_argument('-l', '--linux', action='store_true', help='Force test command to Linux format.')
    parser.add_argument
    args = parser.parse_args()
    return args

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

def extract_results(filename, tail_lines):
    result = None

    STATE_SEARCHING = 0
    STATE_TESTS = 1

    # remove everything up to "test\"
    test_str = os.path.sep + "test" + os.path.sep

    # remove "\test.log" and beyond
    log_str = os.path.sep + "0" + os.path.sep + "test.log"

    testpos = filename.find(test_str)
    if (testpos == -1):
        print(f"ERROR: Could not find {test_str} in {filename}.")
        return result
    
    logpos = filename.find(log_str)
    if (logpos == -1):
        print(f"ERROR: Could not find {log_str} in {filename}.")
        return result

    # skip the initial separator in the test name
    testname = filename[testpos + 1:logpos]
    # print(f"TEST: {testname}")

    result = TestResult(testname, filename)

    cur_state = STATE_SEARCHING
    # keep track of total script times for this test
    cur_total_time = 0.0

    for cur_line in tail_lines:
        if (cur_state == STATE_SEARCHING):
            if (cur_line.find("### SUMMARY") == -1):
                # skip anything before the summary section
                continue
            else:
                # process all subsequent lines
                cur_state = STATE_TESTS
        else:
            # determine what kind of result this is and remember the type
            cur_result = TestResult.RESULT_SUCCESS
            stripped = cur_line.strip()
            if stripped.startswith("TIMEOUT: "):
                cur_result = TestResult.RESULT_TIMEOUT
                stripped = stripped[len("TIMEOUT: "):]
            elif stripped.startswith("FAILURE: "):
                cur_result = TestResult.RESULT_FAILURE
                stripped = stripped[len("FAILURE: "):]
            else:
                stripped = stripped[len("SUCCESS: "):]

            # extract the script name
            elapsed_pos = stripped.find(" (elapsed: ")
            if (elapsed_pos == -1):
                print(f"ERROR: Couldn't find elapsed string in {stripped}")
                continue
            script = stripped[:elapsed_pos]
            # print(f"\t{script}")

            # extract the elapsed time
            cur_time = stripped[elapsed_pos + len(" (elapsed: "):]
            dot_pos = cur_time.find("s,")
            if (dot_pos == -1):
                print(f"ERROR: Couldn't find elapsed seconds amount in {stripped}")
                continue
            cur_time = cur_time[:dot_pos]
            cur_real_time = float(cur_time)
            cur_total_time += cur_real_time

            # create a new dict with the results and add to the appropriate list
            # result structure:
            # str SCRIPT
            # int TYPE
            # float SECONDS
            new_result = {
                "SCRIPT" : script,
                "TYPE" : cur_result,
                "SECONDS" : cur_real_time
            }

            if (cur_result == TestResult.RESULT_TIMEOUT):
                result.timeouts.append(new_result)
            elif (cur_result == TestResult.RESULT_FAILURE):
                result.failures.append(new_result)
            else:
                result.successes.append(new_result)
    
    result.totalseconds = cur_total_time
    return result

def collect_logs(filelist):
    results = []

    # collect test results (at end of file)
    for curfile in filelist:
        # print(f"FILE: {curfile}")
        curlines = tail(curfile)
        curresult = extract_results(curfile, curlines)
        if (curresult is not None):
            # collect test parameters (at beginning and sometimes middle of file) "[sim info] run_target("
            # store the run_target line in self.run_targets
            # parse the fmod configuration out of the run_target line
            # store the run_target line in a simple list (fmod_configs). will do a separate method that counts each fmod configuration's usage. dupes allowed in this list.
            curresult.run_targets, curresult.fmod_configs, curresult.param_dicts = get_params_and_fmods(curfile)
            results.append(curresult)

    total_success = 0
    total_fail = 0
    total_timeout = 0

    for cur_result in results:
        total_success += len(cur_result.successes)
        total_fail += len(cur_result.failures)
        total_timeout += len(cur_result.timeouts)
    
    print(f"Total successes: {total_success}")
    print(f"Total failures: {total_fail}")
    print(f"Total timeouts: {total_timeout}")
    print("")

    return results

def get_top_results(results, type, max_num, platform, style, highest = False):
    testnames = []
    status_text = "Shortest"
    if (highest):
        status_text = "Longest"

    type_text = "successes"
    if (type == TestResult.RESULT_FAILURE):
        type_text = "failures"
    elif (type == TestResult.RESULT_TIMEOUT):
        type_text = "timeouts"

    # get subset of tests depending on whether there are any of the requested type
    subresults = []
    for cur_result in results:
        if (type == TestResult.RESULT_FAILURE):
            if (len(cur_result.failures) > 0):
                subresults.append(cur_result)
        elif (type == TestResult.RESULT_TIMEOUT):
            if (len(cur_result.timeouts) > 0):
                subresults.append(cur_result)
        elif (len(cur_result.successes) > 0):
            subresults.append(cur_result)

    # sort the list in ascending or descending order (highest = descending)
    print (f"{status_text} {max_num} {type_text}:")
    subresults = sorted(subresults, key = lambda x: x.totalseconds, reverse=highest)

    # print details on the top max_num results
    cur_idx = 0
    for cur_result in subresults:
        print(f"Test: {cur_result.testname} - {cur_result.totalseconds} seconds")
        print(f"- File: {cur_result.filename}")
        if (len(cur_result.run_targets) == 0):
            print(f"- Targets: (NONE FOUND - file probably truncated)")
        else:
            print(f"- Targets:")
            for cur_targ in cur_result.run_targets:
                print(f"--- {cur_targ}")
        if (len(cur_result.fmod_configs) == 0):
            print(f"- FMODs: (NONE FOUND - file probably truncated)")
        else:
            print(f"- FMODs:")
            for cur_fmod in cur_result.fmod_configs:
                print(f"--- {cur_fmod}")

        # format command
        formatted_test = cur_result.testname
        if (style == STYLE_LINUX):
            formatted_test = formatted_test.replace(os.path.sep, "/")
        elif (style == STYLE_WINDOWS):
            formatted_test = formatted_test.replace(os.path.sep, "\\")
        testnames.append(formatted_test)

        print(f"- Cmd: vp platform test {platform} --keep-logs --by-name {formatted_test}")

        cur_idx += 1
        if (cur_idx >= max_num):
            break

        print("")
    
    # build a command to run all X tests
    big_command = f"vp platform test {platform} --keep-logs --by-name "
    for cur_name in testnames:
        big_command += cur_name
        big_command += " "
    print("")
    print(f"Command to run all {len(testnames)} tests:")
    print(big_command)

    print("")


def get_matching_lines(filename, starting_string):
    lines = []
    with open(filename, 'r') as file:
        curline = file.readline()
        while curline:
            # bytes_str = starting_string.encode('utf-8')
            if (curline.find(starting_string) != -1):
                lines.append(curline.strip())
            curline = file.readline()
        file.close()
    
    return lines

def get_params_and_fmods(filename):
    fmods = []
    lines = get_matching_lines(filename, "[sim info] run_target(")
    param_dicts = []

    if len(lines) == 0:
        # print(f"WARNING: No target line found in {filename}. Returning.")
        return lines, fmods
    
    for cur_line in lines:
        # get just fmods
        search_term = "'fmod': '"
        fpos = cur_line.find(search_term)
        if (fpos == -1):
            fmods.append("(BMOD)")
        else:
            cur_fmod = cur_line[fpos + len(search_term):]
            delim = cur_fmod.find("'")
            if (delim == -1):
                print("WARNING: No closing ' found!")
            else:
                cur_fmod = cur_fmod[:delim]
            fmods.append(cur_fmod)
        # get all parameters
        search_term = "preset_params "
        fpos = cur_line.find(search_term)
        if (fpos == -1):
            print(f"WARNING: No params found in line {cur_line}")
        else:
            param_line = cur_line[fpos + len(search_term):]
            # yaml is not a default python package
            #param_dict = yaml.load(param_line)
            param_line.replace("'", "\"")
            # print(f"param_line: {param_line}")
            # print(f"cur_line: {cur_line}")
            param_dict = ast.literal_eval(param_line)
            param_dicts.append(param_dict)
            
    return lines, fmods, param_dicts


if __name__ == "__main__":
    args = parse_args()

    print("Directory to search for logs: " + args.dir)
    print(f"Platform string to use in test commands: {args.platform}")

    # determine preferred style for test command
    style = STYLE_OS
    if (args.linux):
        style = STYLE_LINUX
    if (args.windows):
        style = STYLE_WINDOWS

    if (style == STYLE_OS):
        print(f"Test command style: OS default")
    elif (style == STYLE_LINUX):
        print(f"Test command style: Linux")
    else:
        print(f"Test command style: Windows")

    found_logs = find_test_logs(args.dir, "test.log")
    if (len(found_logs) == 0):
        print(f"ERROR: No test logs found in {args.dir}.")
        quit()

    # get details for all tests
    results = collect_logs(found_logs)

    testnames = []
    for cur_result in results:
        testnames.append(cur_result.testname)
    # sort the list of test names and print it
    testnames = sorted(testnames)
    print("Complete list of tests with failures or timeouts:")
    for cur_name in testnames:
        print(f"- {cur_name}")
    print("")

    # return the shortest timeout results
    get_top_results(results, TestResult.RESULT_TIMEOUT, args.num_tests, args.platform, style)

    # return the shortest failure results
    get_top_results(results, TestResult.RESULT_FAILURE, args.num_tests, args.platform, style)

    # find all fmod combinations used and count them
    cfg_dict = {}
    time_dict = {}
    fail_dict = {}
    params_dict = {}
    for cur_res in results:
        # find all recorded fmod configs
        for cur_cfg in cur_res.fmod_configs:
            if cur_cfg in cfg_dict:
                cfg_dict[cur_cfg] = cfg_dict[cur_cfg] + 1
            else:
                cfg_dict[cur_cfg] = 1

        # find all failed scripts
        for cur_fail in cur_res.failures:
            if cur_fail["SCRIPT"] in fail_dict:
                fail_dict[cur_fail["SCRIPT"]] = fail_dict[cur_fail["SCRIPT"]] + 1
            else:
                fail_dict[cur_fail["SCRIPT"]] = 1

        # find all timed out scripts
        for cur_time in cur_res.timeouts:
            if cur_time["SCRIPT"] in time_dict:
                time_dict[cur_time["SCRIPT"]] = time_dict[cur_time["SCRIPT"]] + 1
            else:
                time_dict[cur_time["SCRIPT"]] = 1
        
        for cur_param in cur_res.param_dicts:
            #for pindex, (key, value) in enumerate(cur_param.items()):
            for key, value in cur_param.items():
                new_key = f"{key}:{value}"
                if new_key in params_dict:
                    params_dict[new_key] = params_dict[new_key] + 1
                else:
                    params_dict[new_key] = 1

    if (len(cfg_dict) == 0):
        print("No fmod configurations found.")
    else:
        print("FMOD configurations:")
        for key, value in cfg_dict.items():
            print(f"- {key} : {value} times")

    print("")
    if (len(time_dict) == 0):
        print("No timeout scripts found.")
    else:
        print("Scripts that timed out:")
        for key, value in time_dict.items():
            print(f"- {key} : {value} times")

    print("")
    if (len(fail_dict) == 0):
        print("No failed scripts found.")
    else:
        print("Scripts that failed:")
        for key, value in fail_dict.items():
            print(f"- {key} : {value} times")

    print("")
    if (len(params_dict) == 0):
        print("No test parameters found.")
    else:
        print("Test parameters used:")
        for key, value in sorted(params_dict.items()):
            print(f"- {key} : {value} times")
