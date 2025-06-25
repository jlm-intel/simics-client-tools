#!/usr/intel/bin/python3.7.4

#import subprocess # for subprocess
import os # for environ and scandir
import sys # for exit
import argparse # for argument parsing
import glob # filename expansion

def parse_args():
    parser = argparse.ArgumentParser(description="Recursively searches for \
                                     files of a given filename and renames \
                                     them to a target filename, overwriting \
                                     existing files with the target name.")
    parser.add_argument('dir', type=str,
                        help='Directory to search for source files.')
    parser.add_argument('--source', type=str,
                        default = "new_reference.json", required=False,
                        help='Source filename to search for in directory.')
    parser.add_argument('--target',
                        type=str,
                        default="golden_reference.json", required=False,
                        help='Target filename to copy found source files to.')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()

    source_file = args.source
    target_file = args.target
    search_dir = args.dir
    successes = 0
    errors = 0

    print("Source filename to search for: " + source_file)
    print("Target filename to rename found sources to: " + target_file)
    print("Directory to search for source files: " + search_dir)

    # locate source files
    searchspec = os.path.join(search_dir, '**')
    searchspec = os.path.join(searchspec, source_file)
    filelist = glob.glob(searchspec, recursive=True)

    # if none found, end
    if len(filelist) == 0:
        print ("ERROR: No files found matching " + source_file + " under " +
               search_dir)
        quit()

    for curfile in filelist:
        # debug - print found files
        # print(curfile)

        # if found, build new path to target file
        new_target = os.path.join(
            os.path.dirname(curfile),
            target_file)

        # debug - print target path
        #print(new_target)

        # delete or back up existing target if found
        # (TODO?)

        # rename/move source to target
        try:
            os.replace(curfile, new_target)
            successes += 1
            print("Successfully updated " + new_target)
        except IsADirectoryError:
            print("Source is a file but destination is a directory: " +
                  new_target)
            errors += 1
        except NotADirectoryError:
            print("Source is a directory but destination is a file: " +
                  new_target)
            errors += 1
        except PermissionError:
            print("Operation not permitted: " +
                  new_target)
            errors += 1
        except OSError as error:
            print("OS error occurred: " + new_target)
            errors += 1

    # count successful replacements and errors
    print("Number of source files successfully moved: " + str(successes))
    print("Number of errors encountered: " + str(errors))
