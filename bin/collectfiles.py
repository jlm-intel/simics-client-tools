import argparse # for argument parsing
import os # for path commands
import glob # for recursive file finding

from file_utilities import verify_directory, load_text_file, copy_file, FileUtilitiesConstants # for my file methods
from pathlib import Path # unlink

def parse_args():
    # argument names cannot contain dashes ('-') if you want the variable name to have the same name as the argument, since var names can't have dashes.
    # Paths passed as arguments cannot end in "\", at least on Windows. They seem to automatically be interpreted as escape characters when ending a string.
    parser = argparse.ArgumentParser(description="Searches a given source directory for a given list of full or partial filenames, and copies any matches to a given target directory.")
    parser.add_argument('--file_list', type=str, required=True, help='File containing full or partial filenames to search for in source directory.')
    parser.add_argument('--source', type=str, required=True, help='Directory to search for files. (Can be nested.)')
    parser.add_argument('--target', type=str, required=True, help='Directory to copy found files to. (Single flat directory.)')
    parser.add_argument('--plugins32', action='store_true', help='Indicates that file_list is a cubase-project-plugins report, and you want to extract 32-bit plugin names from it.')
    parser.add_argument('--plugins64', action='store_true', help='Indicates that file_list is a cubase-project-plugins report, and you want to extract 64-bit plugin names from it.')
    parser.add_argument('--keep_tree', action='store_true', help='Reproduces the directory structure fron source instead of copying everything to a flat directory.')
    args = parser.parse_args()
    return args


def process_line(line):
    procline = ""

    colpos = line.find(':')
    if (colpos == -1):
        # not a plugin line, skip
        return ""
    else:
        # account for trailing ": "
        colpos += 2
    parpos = line.rfind('(')
    if (parpos == -1):
        # not a plugin line, skip
        return ""
    else:
        # account for preceding " "
        parpos -= 1
    procline = line[colpos:parpos]
    # print(f"Found: ->{procline}<-")

    return procline

def extract_plugin_names(lines, get32bit, get64bit):
    names = []

    STRING_32_SUMMARY = "Summary: Plugins Used In 32-bit Projects"
    STRING_64_SUMMARY = "Summary: Plugins Used In 64-bit Projects"
    STRING_ALL_SUMMARY = "Summary: Plugins Used In all Projects"

    search_string = ""
    end_string = STRING_ALL_SUMMARY
    if (get64bit):
        search_string = STRING_64_SUMMARY
    if (get32bit):
        search_string = STRING_32_SUMMARY
    if (False == get32bit) and (False == get64bit):
        print("ERROR: You must specify 32-bit, 64-bit, or both when processing plugin reports.")
        return names
    
    STEP_INIT = 0
    STEP_PROCESS_32_BIT = 2
    STEP_PROCESS_64_BIT = 4
    STEP_END = 5

    cur_step = STEP_INIT
    for cur_line in lines:
        cur_line = cur_line.strip()
        if cur_step == STEP_INIT:
            if (cur_line.startswith(search_string)):
                if get32bit and (search_string == STRING_32_SUMMARY):
                    cur_step = STEP_PROCESS_32_BIT
                    end_string = STRING_64_SUMMARY
                elif get64bit and (search_string == STRING_64_SUMMARY):
                    cur_step = STEP_PROCESS_64_BIT
                    end_string = STRING_ALL_SUMMARY
                elif (search_string == STRING_ALL_SUMMARY):
                    break
        elif cur_step == STEP_PROCESS_32_BIT:
            if (cur_line.startswith(end_string)):
                if (get64bit):
                    cur_step = STEP_PROCESS_64_BIT
                    end_string = STRING_ALL_SUMMARY
                    continue
                else:
                    cur_step = STEP_END
                    end_string = STRING_ALL_SUMMARY
                    continue
            procline = process_line(cur_line)
            if len(procline) > 0:
                if (procline not in names):
                    names.append(procline)
        elif cur_step == STEP_PROCESS_64_BIT:
            if (cur_line.startswith(end_string)):
                cur_step = STEP_END
                end_string = STRING_ALL_SUMMARY
                break
            procline = process_line(cur_line)
            if len(procline) > 0:
                if (procline not in names):
                    names.append(procline)
        else:
            # print("INFO: Reached the end case.")
            break

    return names

if __name__ == "__main__":
    args = parse_args()
    errors = 0
    copied = 0
    nomatches = 0

    # load file list
    file_lines = load_text_file(args.file_list)
    if (args.plugins32 or args.plugins64):
        file_lines = extract_plugin_names(file_lines, args.plugins32, args.plugins64)

    # make sure source dir exists
    if not (verify_directory(args.source, False)):
        print(f"ERROR: {args.source} does not exist!")
        quit()

    # make sure target dir exists
    if not (verify_directory(args.target, True)):
        print(f"ERROR: {args.target} does not exist, and can't create it!")
        quit()

    # find all files in source dir
    searchspec = os.path.join(args.source, '**')
    searchspec = os.path.join(searchspec, '*')
    filelist = glob.glob(searchspec, recursive=True)

    # locate matching files and copy them to target
    for cur_line in file_lines:
        any_found = False
        # print(f"- {cur_line} - ")
        for cur_file in filelist:
            if os.path.basename(cur_file).startswith(cur_line):
                if verify_directory(cur_file, False):
                    # found a directory with a matching name. ignore!
                    continue
                print(f"Found: {cur_file}")
                if (args.keep_tree):
                    trimmed_dir = os.path.dirname(cur_file)
                    # print(f"trimmed_dir 1: {trimmed_dir}")
                    trimmed_dir = trimmed_dir[len(args.source):]
                    # print(f"trimmed_dir 2: {trimmed_dir}")
                    if (len(trimmed_dir) > 0) and (trimmed_dir[0] == os.path.sep):
                        trimmed_dir = trimmed_dir[1:]
                    target_dir = os.path.join(args.target, trimmed_dir)
                    # print(f"   target_dir: {target_dir} (args.target: {args.target})")
                    target_file = os.path.join(target_dir, os.path.basename(cur_file))
                    # print(f"  target_file: {target_file}")
                else:
                    target_file = os.path.join(args.target, os.path.basename(cur_file))
                if (FileUtilitiesConstants.RESULT_ERROR == copy_file(cur_file, target_file)):
                    errors += 1
                else:
                    copied += 1
                    any_found = True
        if (not any_found):
            print(f"WARNING: No matches found for {cur_line}")
            nomatches += 1

    print(f"Files searched for: {len(file_lines)}")
    print(f"Files found and copied: {copied}")
    print(f"Missing files (no matches found): {nomatches}")
    print(f"Errors: {errors}")
