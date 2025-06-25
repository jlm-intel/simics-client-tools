import shutil # for copy2
import os # for path commands
import json # for json parsing/creation

from pathlib import Path
from json.decoder import JSONDecodeError

class FileUtilitiesConstants:
    RESULT_ERROR = 0,
    RESULT_COPIED = 1,
    RESULT_SKIPPED = 2

def copy_file(source_path, target_path, move_file=False):
    # get and confirm existence of directory path (minus filename) - os.makedirs(path, exist_ok=True)
    # print(f"source_path: {source_path}, target_path: {target_path}")
    target_dir = os.path.dirname(target_path)
    try:
        os.makedirs(target_dir, exist_ok=True)
    except OSError as e:
        print(f'ERROR: copy_file unable to make directory {target_dir} ({e.strerror})')
        return FileUtilitiesConstants.RESULT_ERROR

    # copy file from source to target
    # print warning if failed
    try:
        shutil.copy2(source_path, target_path, follow_symlinks=False)
    except OSError as e:
        print(f'ERROR: Unable to copy file {source_path} ({e.strerror})')
        return FileUtilitiesConstants.RESULT_ERROR

    if (move_file):
        try:
            Path.unlink(source_path, missing_ok=False)
        except FileNotFoundError as e:
            print(f'WARNING: Unable to remove source file {source_path}. ({e.strerror})')
            return FileUtilitiesConstants.RESULT_ERROR
        except PermissionError as e:
            print(f"WARNING: Permission error attempting to remove file {source_path}. It might be write-protected or in use by another program.")
            return FileUtilitiesConstants.RESULT_ERROR
        except Exception as e:
            print(f"WARNING: Problem removing source file {source_path}: " + e)
            return FileUtilitiesConstants.RESULT_ERROR

    # if we're here the file copied
    return FileUtilitiesConstants.RESULT_COPIED

def copy_newer_file(file_one_path, file_two_path, move_file=False, sync_mode=False, dry_run = False, verbose = True):
    # initialize file times
    file_one_time = 0
    file_two_time = 0
    file_one_exists = True
    file_two_exists = True
    source_path = file_one_path
    target_path = file_two_path
    proceed = False
    result = FileUtilitiesConstants.RESULT_ERROR

    try:
        file_one_time = os.path.getmtime(file_one_path)
    except OSError:
        file_one_exists = False

    try:
        file_two_time = os.path.getmtime(file_two_path)
    except OSError:
        file_two_exists = False

    if not sync_mode:
        # non-sync mode first (copy in one direction only)
        if not file_one_exists:
            # no source file, abort
            print(f'ERROR: {file_one_path} does not exist.')
            return result
        else:
            if not file_two_exists:
                # no file2, just copy
                proceed = True
            else:
                if (file_two_time < file_one_time) and ((file_one_time - file_two_time) > 1.0):
                    # file1 is newer, copy
                    proceed = True
                else:
                    # no else condition; file is silently skipped if no need to copy
                    result = FileUtilitiesConstants.RESULT_SKIPPED
    else:
        # sync mode (bi-directional copy possible)
        if not file_one_exists:
            if not file_two_exists:
                # no files, abort
                print(f'ERROR: Neither {file_one_path} nor {file_one_path} exist.')
                return result
            else:
                # copy file2 to file1
                source_path = file_two_path
                target_path = file_one_path
                proceed = True
        else:
            if not file_two_exists:
                # copy file1 to file2
                proceed = True
            else:
                if (file_two_time < file_one_time) and ((file_one_time - file_two_time) > 1.0):
                    # file1 is newer, copy file1 to file2
                    proceed = True
                else:
                    if ((file_one_time < file_two_time) and ((file_two_time - file_one_time) > 1.0)):
                        # file2 is newer, copy file2 to file1
                        source_path = file_two_path
                        target_path = file_one_path
                        proceed = True
                    else:
                        # no reason to copy; files are the same
                        result = FileUtilitiesConstants.RESULT_SKIPPED

    if (proceed):
        if (verbose):
            print(f'INFO: Copying {bytes(source_path, 'utf-8').decode('ascii', 'ignore')}...')
        if (dry_run):
            result = FileUtilitiesConstants.RESULT_COPIED
        else:
            result = copy_file(source_path, target_path, move_file)
            # don't need to unlink here; above command already unlinks file if move is True
    else:
        # this might be redundant, considering we set skip cases above...
        result = FileUtilitiesConstants.RESULT_SKIPPED

    return result

def save_json_file(file_path, data_blob):
    f = None
    success = False

    try:
        f = open(file_path, 'w')
        json.dump(data_blob, f, indent = 4)

        # if we're here it was successful
        success = True
    except OSError as e:
        print("ERROR: (OS) " + e.strerror)
    except JSONDecodeError as e:
        print("ERROR: (JSON) " + e.msg)
    except Exception as e:
        print("ERROR: " + e)

    if ((None != f) and (not f.closed)):
        f.close()
    return success

def load_json_file(file_path):
    f = None
    blob = None

    try:
        f = open(file_path)
        blob = json.load(f)
    except OSError as e:
        print("ERROR: (OS) " + e.strerror)
    except JSONDecodeError as e:
        print("ERROR: (JSON) " + e.msg)
    except Exception as e:
        print("ERROR: " + e)

    if ((None != f) and (not f.closed)):
        f.close()
    return blob

def verify_directory(directory_path, make_if_missing = True, verbose = False):
    success = False

    if (os.path.exists(directory_path)):
        # print(f"Path exists")
        if (os.path.isdir(directory_path)):
            if (verbose):
                print(f"INFO {directory_path} is a dir")
            success = True
        else:
            if (verbose):
                print(f'INFO: {directory_path} exists but is not a directory.')
    elif (make_if_missing):
        try:
            os.makedirs(directory_path, exist_ok=True)
            # print("Made dir")
            success = True
        except OSError as e:
            print(f'ERROR: verify_directory unable to make directory {directory_path} ({e.strerror})')

    # print(f"Returning {success}")
    return success

def is_long_path(cur_path):
    if (cur_path.startswith("\\\\?\\UNC\\")):
        # already a long UNC path (\\?\UNC\)
        return True
    elif (cur_path.startswith("\\\\?\\")):
        # already a long normal path (\\?\)
        return True

    # if we're here it's a normal UNC or regular path
    return False

def make_long_path(cur_path):
    if (is_long_path(cur_path)):
        # just return passed string as-is
        return cur_path
    
    if (cur_path.startswith("\\\\")):
        # it's a regular UNC path (\\)
        cur_path = "\\\\?\\UNC\\" + cur_path[2:]
    else:
        cur_path = "\\\\?\\" + cur_path

    return cur_path

def load_text_file(file_path):
    text_lines = []

    try:
        with open(file_path, 'r') as file:
            for line in file:
                text_lines.append(line.strip())
    except FileNotFoundError as e:
        print("ERROR: " + e.strerror + f" ({file_path})")
    except Exception as e:
        print("ERROR: " + e)

    return text_lines
