#!/usr/intel/bin/python3.12.3

# This script takes a given input file and produces a copy with all known timestamp strings removed.
# This results in a log file that is easier to diff against other log files, since it reduces noise from
# trivial differences that are only related to timestamps.

import argparse # argument parsing
import re

def parse_args():
    parser = argparse.ArgumentParser(description="Removes timestamps from text files.")
    parser.add_argument('infile', type=str, help='File to remove timestamps from.')
    parser.add_argument('outfile', type=str, help='Output file with timestamps removed.')
    # parser.add_argument('-w', '--windows', action='store_true', help='Force test command to Windows format.')
    # parser.add_argument('-l', '--linux', action='store_true', help='Force test command to Linux format.')
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

def remove_timestamps(input_file, output_file):
    # Timestamp formats:
    # [11:40:57.3797]
    # 00:00:37.897000
    # Timestamp=0.348200
    enc_type = get_encoding_type(input_file)

    try:
        with open(input_file, mode='r', encoding=enc_type) as infile, open(output_file, 'w') as outfile:
            for line in infile:
                cleaned_line = re.sub(r'\[\d{2}:\d{2}:\d{2}.\d{4}\]', '', line)  #Removes [11:40:57.3797]
                cleaned_line = re.sub(r'\d{2}:\d{2}:\d{2}.\d{6}', '', cleaned_line) #Removes 00:00:37.897000
                cleaned_line = re.sub(r'Timestamp=\b\d+\.\d+\b', '', cleaned_line) #Removes Timestamp=0.348200
                cleaned_line = re.sub(r' \b0[xX][0-9a-fA-F]+ \b\d+\]', '', cleaned_line) #Removes ' 0x69de594c 62340141750]'
                cleaned_line = re.sub(r'\[Time-stamp \b0[xX][0-9a-fA-F]+\]', '', cleaned_line) #Removes [Time-stamp 0x0000f1aa]
                cleaned_line = re.sub(r'\[TS \b0[xX][0-9a-fA-F]+\]', '', cleaned_line) #Removes [TS 0x0000f1aa]
                cleaned_line = re.sub(r'xtal \b\d+\]', 'xtal]', cleaned_line) #Removes .xtal 2341298008]
                outfile.write(cleaned_line)
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
    except Exception as e:
         print(f"An error occurred: {e}")

if __name__ == "__main__":
    args = parse_args()
    remove_timestamps(args.infile, args.outfile)
    print(f"Timestamps removed. Output saved to '{args.outfile}'")

