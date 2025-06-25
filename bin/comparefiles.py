#!/usr/intel/bin/python3.12.3

# This script compares two given text files and prints three separate lists as a result:
# - Lines unique to the first file.
# - Lines unique to the second file.
# - Lines common to both files.
#
# You can optionally sort the resulting lists in alphabetical order.
#
# If using this with Simics test logs, you might want to run nostamps.py on the log files
# first, to remove timestamps that can make meaningful comparison difficult.

import argparse # argument parsing

def parse_args():
    parser = argparse.ArgumentParser(description="Compares two text files and prints the results.")
    parser.add_argument('file1', type=str, help='First text file.')
    parser.add_argument('file2', type=str, help='Second text file.')
    parser.add_argument('-s', '--sort', action='store_true', help='Sort comparison results before printing.')
    args = parser.parse_args()
    return args

def open_attempt(filename, enc_type):
    try:
        f = open(filename, mode='r', encoding=enc_type)
        line = f.readline()
    except:
        # file didn't open, fail out
        return False

    # if we're here it succeeded
    f.close()
    return True

def get_encoding_type(filename):
    if open_attempt(filename, 'utf_16'):
        return 'utf_16'
    if open_attempt(filename, 'utf-8'):
        return 'utf_8'
    if open_attempt(filename, 'ascii'):
        return 'ascii'

    # if we're here, we don't know the type
    return 'undefined'

def get_file_lines(filename):
    lines = []

    enc_type = get_encoding_type(filename)
    if (enc_type == 'undefined'):
        print(f"ERROR: Unable to determine encoding of {filename}!")
        return lines

    with open(filename, 'r', encoding=enc_type) as file:
        line = file.readline()
        while line:
            lines.append(line.strip())
            line = file.readline()
        file.close()
    
    return lines

def compare_lines(lines1, lines2, sort):
    file1_lines = []
    file2_lines = []
    common_lines = []

    for cur_line in lines1:
        if cur_line in lines2:
            if (cur_line not in common_lines):
                common_lines.append(cur_line)
        else:
            if (cur_line not in file1_lines):
                file1_lines.append(cur_line)
    
    for cur_line in lines2:
        if not cur_line in lines1:
            if (cur_line not in file2_lines):
                file2_lines.append(cur_line)

    if sort:
        file1_lines = sorted(file1_lines)
        file2_lines = sorted(file2_lines)
        common_lines = sorted(common_lines)
    
    return file1_lines, file2_lines, common_lines

def print_header(string_to_print):
    border_line = '-' * len(string_to_print)
    print("")
    print(border_line)
    print(string_to_print)
    print(border_line)

if __name__ == "__main__":
    file1_lines = []
    file2_lines = []
    common_lines = []
    args = parse_args()

    print(f" First file: {args.file1}")
    print(f"Second file: {args.file2}")

    file1_lines = get_file_lines(args.file1)
    if (len(file1_lines) == 0):
        print(f"ERROR: No content in {args.file1}.")
        quit()

    file2_lines = get_file_lines(args.file2)
    if (len(file2_lines) == 0):
        print(f"ERROR: No content in {args.file2}.")
        quit()

    file1_lines, file2_lines, common_lines = compare_lines(file1_lines, file2_lines, args.sort)

    print_header(f"LINES ONLY IN {args.file1}")
    for cur_line in file1_lines:
        print(cur_line)

    print_header(f"LINES ONLY IN {args.file2}")
    for cur_line in file2_lines:
        print(cur_line)
    
    print_header("LINES IN BOTH FILES")
    for cur_line in common_lines:
        print(cur_line)
