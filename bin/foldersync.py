import argparse # for argument parsing
import os # for path commands
import shutil # for disk space commands
import glob # for recursive file finding

from file_utilities import copy_newer_file, save_json_file, load_json_file, verify_directory, FileUtilitiesConstants, make_long_path # for my file methods
from pathlib import Path # unlink

def parse_args():
    # set up default settings filename
    program_dir = os.path.dirname(__file__)
    settings_default = os.path.join(program_dir, "foldersync.json")

    parser = argparse.ArgumentParser(description="Syncs local directories to a remote storage location, optionally pruning out obsolote backup files.")
    parser.add_argument('--settings_file', type=str, required=False, default=settings_default, help='Directory where you want to place cleaned-up files.')
    parser.add_argument('--setup', action='store_true', help='Creates a template settings file which you must populate with your desired settings.')
    parser.add_argument('--dryrun', action='store_true', help='Does not actually copy or delete any files; just prints what would happen.')
    parser.add_argument('--prune', action='store_true', help='Delete orphaned files in backup location.')
    parser.add_argument('--debug_limit', type=int, required=False, default=0, help='Max number of files to process in each directory (for debugging purposes).')
    parser.add_argument('--verbose', action='store_true', help='Print more file details while running. (Can increase runtime for large jobs.)')
    args = parser.parse_args()
    return args

def sync_directories(settings_path, dry_run, debug_limit, prune, verbose):
    success = False
    errors = 0
    copied = 0
    pruned = 0
    pruned_dirs = 0
    skipped = 0
    volume_stats = {}

    settings = load_json_file(settings_path)
    if (None == settings):
        print(f"ERROR: Unable to load settings file {settings_path}")
        return success

    # get "before" file usage
    for cur_volume in settings["remote_volumes"]:
        stat = shutil.disk_usage(cur_volume)
        print(f"Space free on {cur_volume}: {stat.free}")
        volume_stats[cur_volume] = {
            "free_before": stat.free,
            "free_after": 0
        }

    for cur_profile_name in settings['profiles']:
        #print(cur_profile_name)
        cur_profile = settings['profiles'][cur_profile_name]
        local_dir = cur_profile['local_dir']
        remote_dir = cur_profile['remote_dir']

        # enable long path handling
        local_dir = make_long_path(local_dir)
        remote_dir = make_long_path(remote_dir)
        #print(f'local_dir: {local_dir}')
        #print(f'remote_dir: {remote_dir}')

        print(f"Searching for new files in {local_dir}...")
        # make sure local_dir is a directory
        if (not os.path.isdir(local_dir)):
            print(f'ERROR: {local_dir} is not a directory. Skipping.')
            continue
        if (not verify_directory(remote_dir)):
            # method prints a warning if not able to create
            continue
        # build recursive search path for all files
        searchspec = os.path.join(local_dir, "**", "*")
        filelist = glob.iglob(searchspec, recursive = True)
        local_len = len(local_dir)
        # NOTE: This is to remove the pre-pended "\" that's left when you strip the local_dir from the total path.
        #       os.path.join removes the first directory from the second argument if the string begins with a "\" because
        #       it thinks you're specifying an absolute path, so it discards the directory portion.
        local_len += 1

        print (f"Processing files in {local_dir}. This might take a while...")
        DEBUG_LIMITER = 0
        # TODO: Reject ignored filetypes (using fnmatch filename matching)
        for cur_file in filelist:
            if (os.path.isdir(cur_file)):
                continue
            # build prospective target path
            # since we are doing recursive searches, we need to build the full target path, not just append the filename to remote_dir
            #print(f'{remote_dir} + {cur_file[local_len:]}')
            target_path = os.path.join(remote_dir, cur_file[local_len:])
            # print(f'{cur_file} -> {target_path}')
            copy_result = copy_newer_file(cur_file, target_path, move_file=False, sync_mode=False, dry_run=dry_run, verbose=verbose)
            if (copy_result == FileUtilitiesConstants.RESULT_ERROR):
                errors += 1
            elif (copy_result == FileUtilitiesConstants.RESULT_SKIPPED):
                skipped += 1
            else:
                copied += 1
            # halt operation if we reach the debug max
            if (debug_limit > 0):
                DEBUG_LIMITER += 1
                if (DEBUG_LIMITER >= debug_limit):
                    break

        if (prune):
            # build recursive search path for all files
            print (f"Searching for potentially orphaned files in {remote_dir}. This might take a while...")
            searchspec = os.path.join(remote_dir, "**", "*")
            filelist = glob.iglob(searchspec, recursive = True)
            remote_len = len(remote_dir)
            remote_len += 1
            dirlist = []
            print (f"Processing orphaned files in {remote_dir}. This might take a while...")
            DEBUG_LIMITER = 0
            for cur_file in filelist:
                if (os.path.isdir(cur_file)):
                    # add to the dirlist, if needed
                    if cur_file not in dirlist:
                        dirlist.append(cur_file)
                    continue
                target_path = os.path.join(local_dir, cur_file[remote_len:])
                if (not os.path.exists(target_path)):
                    # file not found in local directory, cur_file is orphaned
                    if (verbose):
                        print(f'Orphaned file: {bytes(cur_file, 'utf-8').decode('ascii', 'ignore')}')
                    if (dry_run):
                        pruned += 1
                    else:
                        try:
                            Path.unlink(cur_file, missing_ok=False)
                            pruned += 1
                        except FileNotFoundError as e:
                            print(f'ERROR: Unable to remove orphaned file {bytes(cur_file, 'utf-8').decode('ascii', 'ignore')}. ({e.strerror})')
                            errors += 1
                        except Exception as e:
                            print(f"ERROR: Problem removing orphaned file {bytes(cur_file, 'utf-8').decode('ascii', 'ignore')}: " + e)
                            errors += 1
                    if (debug_limit > 0):
                        DEBUG_LIMITER += 1
                        if (DEBUG_LIMITER >= debug_limit):
                            break
            # now delete empty directories. first, sort in reverse order so nested dirs come first
            dirlist = sorted(dirlist, reverse=True)
            for cur_dir in dirlist:
                if not os.listdir(cur_dir):
                    # directory not empty
                    try:
                        os.rmdir(cur_dir)
                        pruned_dirs += 1
                    except OSError as error:
                        print(f"ERROR: Unable to remove {cur_dir}: {error}")
                        errors += 1

    # get "after" file usage
    for cur_volume in settings["remote_volumes"]:
        stat = shutil.disk_usage(cur_volume)
        volume_stats[cur_volume]["free_after"] = stat.free
        print(f"Space free on {cur_volume}: {volume_stats[cur_volume]["free_before"]} (before), {volume_stats[cur_volume]["free_after"]} (after). ")
        space_saved = volume_stats[cur_volume]["free_before"] - volume_stats[cur_volume]["free_after"]
        print(f"Space saved on {cur_volume}: {space_saved} bytes")

    print(f'Copied {copied}, skipped {skipped}, and pruned {pruned} files and {pruned_dirs} empty directories, with {errors} errors.')

    return success

def create_settings(settings_path):
    # file format
    # "remote_volumes" - list of backup drives, so we can collect before/after usage information
    # "profiles" - named pairs of local and remote directories to sync (videos, documents, music, etc), same format as multisync's profiles
    success = False
    # note - if all directories are backing up to the same remote drive, you only need a single "remote_volume" entry
    # TODO: Add section of filetypes to ignore.

    blob = {
        'remote_volumes': [
                '(backup_path_1)',
                '(backup_path_2)'
        ],
        'profiles': {
            "Documents": {
                'local_dir': 'local_full_path',
                'remote_dir': 'remote_full_path'
            },
            "Downloads": {
                'local_dir': 'local_full_path',
                'remote_dir': 'remote_full_path'
            },
            "Music": {
                'local_dir': 'local_full_path',
                'remote_dir': 'remote_full_path'
            },
            "Pictures": {
                'local_dir': 'local_full_path',
                'remote_dir': 'remote_full_path'
            },
            "Videos": {
                'local_dir': 'local_full_path',
                'remote_dir': 'remote_full_path'
            }
        }
    }

    success = save_json_file(settings_path, blob)
    if (success): 
        print("INFO: Settings file is: " + settings_path + ", edit this file to complete setup.")
    else:
        print(f"ERROR: Unable to configure settings file {settings_path}")

if __name__ == "__main__":
    args = parse_args()

    # default path set in parse_args
    settings_path = args.settings_file

    # if setup requested, create settings
    if (args.setup):
        create_settings(settings_path)
        exit()

    # perform sync operation
    if (args.debug_limit > 0):
        print(f'INFO: Limiting files processed per directory to {args.debug_limit} for debug purposes.')
    sync_directories(settings_path, args.dryrun, args.debug_limit, args.prune, args.verbose)
