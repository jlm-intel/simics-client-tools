#!/usr/intel/bin/python3.7.4
# Note: Recursive glob only supported in python 3.5+
try:
    import os # path functions
    import sys # argument processing
    import glob # filename expansion
    import datetime # date and time functions
    from shutil import copyfile # copy files when needed
    import re # regular expressions
    import subprocess # running external processes

except:
    print("ERROR: Problem importing dependencies. Are you running from the root of a project directory? (tgl, adl, etc.)")
    quit()

def get_suiteinfos(dirname):
    #print os.path.join(dirname, "*.py")
    searchspec = os.path.join(dirname, '**')
    searchspec = os.path.join(searchspec, 'SUITEINFO')
    filelist = glob.glob(searchspec, recursive=True)
    if len(filelist) == 0:
        print ("ERROR: No files found matching", os.path.join(dirname, "SUITEINFO"))
    return sorted(filelist)

def get_tags(suiteinfo_path):
    tags = set()
    try:
        lines = open(suiteinfo_path).readlines()
    except:
        lines = []
        print("ERROR: Unable to load file: " + suiteinfo_path)

    for line in lines:
        # the "r preceding the tags string below makes python process the line as a "raw string"
        # .* - match any character except a newline
        # following line returns a match object with all the contents after "tags:"
        r = re.match(r"tags:(.*)", line)
        if r:
            # prune and split tags into separate items
            tags = r.groups()[0].strip().split()
            break

    return sorted(tags)

def get_file_contents(suiteinfo_path):
    lines = []
    try:
        lines = open(suiteinfo_path).readlines()
    except:
        lines = []
        print("ERROR: Unable to load file: " + suiteinfo_path)
    return lines


def contains_tag(tags, wanted_tag):
    for curtag in tags:
        if (curtag == wanted_tag):
            return True
    return False

# searches passed list of SUITEINFOs for files either containing or NOT containing wanted tag
def get_files_by_tag(filelist, wanted_tag, return_containing = True):
    return_list = list()
    for curfile in filelist:
        curtags = get_tags(curfile)
        # only add to return list if:
        # - tag found AND containing desired
        # - tag missing AND missing desired
        if (contains_tag(curtags, wanted_tag) == return_containing):
            #print("Adding", curfile, "to list.")
            # note: For some reason, return_list += curfile was adding as individual characters instead of filename strings?
            return_list.append(curfile)

    #print("len(return_list): ", len(return_list))
    return return_list

def build_tagline(tags):
    tagline = "tags:"
    for curtag in tags:
        tagline += " "
        tagline += curtag

    # IMPORTANT: WriteLines() doesn't add newline characters to output; you must add your own!
    tagline += "\n"
    return tagline

def is_tagline(line):
    if line.startswith("tags:"):
        return True
    return False

# main function for testing
def main(*kwargs):

    # default values
    cmd = "help"
    workdir = "." # general purpose directory variable
    tag = None # tag to add, remove, or find
    testname = None
    undo_type = ""

    # process arguments
    for arg in kwargs:
        key = None
        val = None
        if len(arg) > 0:
            key = arg.split("=")[0]
            if arg.find("=") != -1:
                val = arg.split("=")[1]
        if (key != None) and (val != None):
            # key and value pair
            print ("Key: " + key + " Value: " + val)
            # populate supported variables
            if key[0] == "a": # add tag
                tag = val
                cmd = "add"
            elif key[0] == "r": # remove tag
                tag = val
                cmd = "remove"
            elif key[0] == "f": # find tag
                tag = val
                cmd = "find"
            elif key[0] == "t": # test testname
                cmd = "test"
                testname = val
            elif key[0] == "m": # missing tag
                cmd = "missing"
                tag = val
            elif key[0] == "u": # undo changes
                cmd = "undo"
                undo_type = val
            else:
                print ("Unexpected parameter key: " + key)
        elif (key != None):
            # no value, must be working directory
                workdir = key

    # execute commands
    if (cmd[0] == "h"):
        # help
        #        1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890
        print( "\nusage: tags.py [path] [COMMAND=TAG]")
        print(   "Batch operations on SUITEINFO tags. Recursively runs from current directory if no dir specified.")
        print( "\nCommands:")
        print(   " help - Show this info.")
        print(   " add=tag - Add specified tag if not found.")
        print(   " remove=tag - Remove specified tag if found.")
        print(   " find=tag - Find SUITEINFO files containing given tag.")
        print(   " missing=tag - Find SUITEINFO files missing/without given tag.")
        print(   " undo=git - Undo changes to all found SUITEINFO files (git method).")
        print(   " test=testname - Perform a debug test. (See below for options.)")
        print(   "     - suiteinfos - Dump a list of all found SUITEINFO files.")
        print(   "     - dumptags - Dump tags found in each file.")
        print(   "     - findoff - Finds all files with the off tag.")
        print(   "     - findmissingadl - Finds all files MISSING the ADL tag.")
    elif (cmd[0] == "f"):
        print( "\n*** find (" + tag + ") ***")
        # get suiteinfos
        filelist = get_suiteinfos(workdir)
        if len(filelist) == 0:
            print( "ERROR: No SUITEINFO files found.")
        else:
            # get list of files containing tag
            resultlist = get_files_by_tag(filelist, tag, True)
            # return list + stats
            for curfile in resultlist:
                print(curfile)
            print("Found", len(resultlist), "occurrences of", tag, "tag in", len(filelist), "SUITEINFO files.")

    elif (cmd[0] == "m"):
        print( "\n*** missing (" + tag + ") ***")
        # get suiteinfos
        filelist = get_suiteinfos(workdir)
        if len(filelist) == 0:
            print( "ERROR: No SUITEINFO files found.")
        else:
            # get list of files containing tag
            resultlist = get_files_by_tag(filelist, tag, False)
            # return list + stats
            for curfile in resultlist:
                print(curfile)
            print("Found", len(resultlist), "occurrences of missing ", tag, "tag in", len(filelist), "SUITEINFO files.")

    elif (cmd[0] == "a"):
        print( "\n*** add (" + tag + ") ***")
        errors = 0
        updatedfiles = 0
        filelist = get_suiteinfos(workdir)
        if len(filelist) == 0:
            print( "ERROR: No SUITEINFO files found.")
        else:
            # find suiteinfos missing tag
            resultlist = get_files_by_tag(filelist, tag, False)
            # for each remaining file:
            for curfile in resultlist:
                # get current tags list
                tags = get_tags(curfile)
                # add missing tag
                tags.append(tag)
                # build new tagline
                tagline = build_tagline(sorted(tags))
                # back up original to "~" version
                backup_file = curfile + "~"
                try:
                    copyfile(curfile, backup_file)
                    # QUESTION: Replace tag line in readlines result? Then can just dump out with writelines.
                    # load file contents
                    contents = get_file_contents(curfile)
                    if len(contents) == 0:
                        print("WARNING: No lines loaded from file", curfile, ". Skipping.")
                        # break out of try block
                        break

                    # replace tags line
                    for x in range(len(contents)):
                        if is_tagline(contents[x]):
                            contents[x] = tagline
                            # question: safe to break here, or should we keep looking for extra tags lines?
                            break

                    # create target file and dump new contents
                    f = open(curfile, "w")
                    f.writelines(contents)
                    # close/save file
                    f.close()
                    # update success count
                    updatedfiles += 1
                    print("INFO: Updated file", curfile)

                except:
                    print("ERROR: Unable to update file:", curfile)
                    errors += 1
            print("INFO: Added ", tag, "to", updatedfiles, "files out of", len(filelist), "total, with", errors, "errors.")

    elif (cmd[0] == "r"):
        print( "\n*** remove (" + tag + ") ***")
        errors = 0
        updatedfiles = 0
        filelist = get_suiteinfos(workdir)
        if len(filelist) == 0:
            print( "ERROR: No SUITEINFO files found.")
        else:
            # find suiteinfos missing tag
            resultlist = get_files_by_tag(filelist, tag, True)
            # for each remaining file:
            for curfile in resultlist:
                # get current tags list
                tags = get_tags(curfile)
                # add missing tag
                tags.remove(tag)
                # build new tagline
                tagline = build_tagline(sorted(tags))
                # back up original to "~" version
                backup_file = curfile + "~"
                try:
                    copyfile(curfile, backup_file)
                    # QUESTION: Replace tag line in readlines result? Then can just dump out with writelines.
                    # load file contents
                    contents = get_file_contents(curfile)
                    if len(contents) == 0:
                        print("WARNING: No lines loaded from file", curfile, ". Skipping.")
                        # break out of try block
                        break

                    # replace tags line
                    for x in range(len(contents)):
                        if is_tagline(contents[x]):
                            contents[x] = tagline
                            # question: safe to break here, or should we keep looking for extra tags lines?
                            break

                    # create target file and dump new contents
                    f = open(curfile, "w")
                    f.writelines(contents)
                    # close/save file
                    f.close()
                    # update success count
                    updatedfiles += 1
                    print("INFO: Updated file", curfile)

                except:
                    print("ERROR: Unable to update file:", curfile)
                    errors += 1
            print("INFO: Removed", tag, "from", updatedfiles, "files out of", len(filelist), "total, with", errors, "errors.")

    elif (cmd[0] == "u"):
        print( "\n*** undo (" + undo_type + ") ***")

        # currently only one undo type
        if (undo_type != "git" ):
            print("ERROR: Unsupported undo type:", undo_type)
            return -1

        errors = 0
        updatedfiles = 0
        filelist = get_suiteinfos(workdir)
        if len(filelist) == 0:
            print( "ERROR: No SUITEINFO files found.")
        else:
            for curfile in filelist:
                try:
                    print("Attempting to undo", curfile, "...")
                    output = subprocess.run(["git", "checkout", curfile])
                    output.check_returncode()
                except CalledProcessError:
                    print("ERROR: Git error while attempting to revert", curfile)
                    errors += 1
                    continue
                except:
                    print("ERROR: Unexpected error while attempting to revert", curfile)
                    errors += 1
                    continue

                # if here, curfile was a success
                updatedfiles += 1

            print("INFO: Undid changes to", updatedfiles, "files out of", len(filelist), "total, with", errors, "reported errors.")

    elif (cmd[0] == "t"):
        print( "\n*** test (" + testname + ") ***")
        if (testname == "suiteinfos"):
            filelist = get_suiteinfos(workdir)
            if len(filelist) == 0:
                print( "ERROR: No SUITEINFO files found.")
            else:
                for curfile in filelist:
                    print(curfile)
        elif (testname == "dumptags"):
            filelist = get_suiteinfos(workdir)
            if len(filelist) == 0:
                print( "ERROR: No SUITEINFO files found.")
            else:
                for curfile in filelist:
                    print(curfile)
                    tags = get_tags(curfile)
                    if len(tags) == 0:
                        print("ERROR: No tags found in " + curfile)
                    else:
                        print(tags)

        elif (testname == "findoff"):
            filelist = get_suiteinfos(workdir)
            if len(filelist) == 0:
                print( "ERROR: No SUITEINFO files found.")
            else:
                resultlist = get_files_by_tag(filelist, "off", True)
                for curfile in resultlist:
                    print(curfile)
                print("Found ", len(resultlist), " occurrences of off tag in ", len(filelist), " SUITEINFO files.")

        elif (testname == "findmissingadl"):
            filelist = get_suiteinfos(workdir)
            if len(filelist) == 0:
                print( "ERROR: No SUITEINFO files found.")
            else:
                resultlist = get_files_by_tag(filelist, "ADL", False)
                for curfile in resultlist:
                    print(curfile)
                print("Found ", len(resultlist), " occurrences of missing ADL tag in ", len(filelist), " SUITEINFO files.")

        else:
            print( "ERROR: Unexpected test name.")
    else:
        print( "ERROR: Unexpected command: " + cmd + ". Please run with help as an argument to see supported commands.")

    print( " ")

if __name__== "__main__":
    main(*sys.argv[1:])