#!/usr/intel/bin/python3.7.4

import argparse
import os.path
from subprocess import run

def parse_args():
    parser = argparse.ArgumentParser(description="Packages and uploads fusegen XML files.")
    parser.add_argument('search_string', type=str,
                        help='String you would like to search for in the given text file.')
    parser.add_argument('log_file', type=str,
                        help='Path to log file (or any text file) you would like to search for a given substring.')
    parser.add_argument('--ignore_case', action='store_true',
                        required=False,
                        help='Indicates whether searches should be case-insensitive. (Default = False; case-sensitive.)')
    args = parser.parse_args()
    return args

def load_text_file(filepath):
    items = []
    try:
        inf = open(filepath, "r")
    except:
        print(f"ERROR: Unable to open input file {filepath}")
        return items

    items = inf.readlines()
    inf.close()
    return items


if __name__ == "__main__":
    args = parse_args()

    if (not os.path.exists(args.log_file)):
        print(f"ERROR: File {args.log_file} not found!")
        exit(1)

    lines = load_text_file(args.log_file)
    if (len(lines) == 0):
        print(f"ERROR: No lines read from {args.log_file}")
        exit(1)

    found_items = {}
    for cur_line in lines:
        fresult = -1
        if (args.ignore_case):
            fresult = cur_line.lower().find(args.search_string.lower())
        else:
            fresult = cur_line.find(args.search_string)
        if (fresult != -1):
            cur_count = 0
            new_line = cur_line.strip("\n")
            try:
                # get existing value, if any
                cur_count = found_items[new_line]
            except KeyError:
                # it's okay; just haven't added this line yet
                cur_count = 0
            found_items[new_line] = (cur_count + 1)

    if (len(found_items) == 0):
        print(f"Did not find any instances of {args.search_string} in {args.log_file}")
        exit(1)

    for cur_item in found_items:
        print(f"LINE: {cur_item}, INSTANCES: {found_items[cur_item]}")
    print(f"Unique lines containing {args.search_string}: {len(found_items)}")
