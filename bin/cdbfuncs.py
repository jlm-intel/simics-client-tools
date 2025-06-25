#!/usr/intel/bin/python
#def reg_arr_value_bits(byte_arr, offset, msb, lsb):
try:
    import os # path functions
    import sys # argument processing

    # looks like cdb2 stuff moved from ../ic to ../_tools

    # include CDB paths when possible so we can reuse some of their classes
    if os.path.exists("../_tools/cdb2"):
        sys.path.append("../_tools/cdb2")

        if os.path.exists("../_tools/cdb2/parsers"):
            sys.path.append("../_tools/cdb2/parsers")
        else:
            print "WARNING: ../_tools/cdb2/parsers not found. Run from a project directory."
    else:
        print "WARNING: ../_tools/cdb2 not found. Run from a project directory."
    #print sys.path

    import glob # filename expansion
    import datetime # date and time functions
    from shutil import copyfile # copy files when needed

    #from lxml import etree # xml parsing
    import xml.etree.ElementTree as etree

    import cdb_classes # SrcBank, Register, Field, etc.
    from crif import parse
except:
    print("ERROR: Problem importing dependencies. Are you running from the root of a project directory? (tgl, adl, etc.)")
    quit()

def get_date_string():
    timeobj = datetime.datetime.now()
    #timeobj.microsecond = 0 # this is a read-only property, need to find out how to round to nearest second
    readable = timeobj.isoformat()
    return readable

def process_dir(dirname):
    #print os.path.join(dirname, "*.py")
    filelist = glob.glob(os.path.join(dirname, "*.py"))
    if len(filelist) == 0:
        print "ERROR: No files found matching", os.path.join(dirname, "*.py")
        return False

    for curpath in filelist:
        curfilebase = os.path.basename(curpath)
        # indicate whether this file s
        can_disable(curfilebase)

# function assumes you're just passing a filename, not a whole path
def can_disable(filename):
    result = False
    # different logic if name contains "Lane"
    lane_pos = filename.find("Lane")
    if lane_pos != -1:
        # get digit after string appears (Lane position + 4 for "lane")
        digit_index = lane_pos + 4
        if len(filename) >= digit_index:
            digit = filename[digit_index]
            if digit.isdigit():
                if int(digit) > 0:
                    #print filename, "contains Lane", digit
                    append_logfile(filename + " contains non-zero Lane")
                    result = True

    else:
        # stuff
        namelen = len(filename)
        scorecount = 0
        trimcount = 0
        for i, c in enumerate(filename):
            if c == "_":
                scorecount += 1
            if scorecount == 7:
                trimcount = i
                break
        if scorecount >= 7:
            # remove everything up through the 7th underscore
            filename = filename[trimcount:namelen]
            # convert to lowercase for substring search
            filename = filename.lower()
            # remove anything after "pci_" because that will be non-relevant hex digits
            pci_pos = filename.find("pci_")
            if pci_pos != -1:
                filename = filename[:pci_pos]
            # now check the remaining text for non-zero digits
            for n in filename:
                if n.isdigit():
                    if int(n) > 0:
                        #print filename, "contains a non-zero digit"
                        append_logfile(filename + " contains non-zero digit")
                        result = True
                        break
        else:
            print filename, "doesn't have enough underscores."

        #if result == False:
        #    print filename, " is not a candidate"

    return result

def get_logfile_name():
    directory = os.getcwd()
    user = os.environ['USER']
    fullpath = os.path.join(directory, user)
    fullpath += ".txt"
    return fullpath

def create_logfile(filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
    file = open(filepath, "w+")
    file.close()

def append_logfile(output):
    if os.path.exists(get_logfile_name()) == False:
        create_logfile(get_logfile_name())
    file = open(get_logfile_name(), "a+")
    file.write(output + "\n")
    file.close()

# extracts the searchable string information that identifies the current DevBank or RegLayout file.
def trim_bankfile_name(bankfile):
    # convert to lower case
    curfile = bankfile.lower()

    # search for devbank_ (8 len) or reglayout_ (10 len)
    prelen = 8
    strpos = curfile.find("devbank_")
    if (strpos == -1):
        strpos = curfile.find("reglayout_")
        if (strpos == -1):
            # if not found, abort
            print "ERROR: No devbank or reglayout found."
            return ""
        else:
            prelen = 10

    # remove prefix otherwise
    curfile = curfile[strpos + prelen:]

    # search for sb
    # SB format is sb_cf_00_CR.dml (underscores and 2-digit values)
    # other format is 0.8.0.CFG.dml (dots and single-digit values)
    # replace all periods with underscores
    curfile = curfile.replace(".", "_")

    # remove everything after 3rd underscore
    filelen = len(curfile)
    scorecount = 0
    trimcount = 0
    for i, c in enumerate(curfile):
        if c == "_":
            scorecount += 1
        if scorecount == 3:
            trimcount = i
            break

    if (scorecount < 3):
        print "ERROR: Not a regular devbank or reglayout filename. (Not enough underscores.)"
        return ""

    # only keep everything up to the third slash
    curfile = curfile[:(trimcount)]

    # we also have to de-zero-pad the numerical fields (for example "0c" must become "c" and "00" must become "0")
    finalstring = ""
    elements = curfile.split("_")
    for curelement in elements:
        if (len(curelement) > 1) and (curelement[0] == "0"):
            curelement = curelement[1:]
        finalstring += curelement
        finalstring += "_"

    # we now have the prefix of a search term
    return finalstring

# locates files that are likely transform scripts based on the passed DevBank or RegLayout file
# returns a list of actual matching transform paths.
def bankfile_to_transform_query(bankfile, releasename):
    foundfiles = []
    if len(releasename) == 0:
        print "ERROR: Please specify a release name (ex: adls-a0-19ww21a)"
        return foundfiles

    # get searchable string from filename
    curfile = trim_bankfile_name(bankfile)
    if len (curfile) == 0:
        print "ERROR: Could not derive search prefix from filename: " + bankfile
        return foundfiles

    # begin building a search path: current working directory + linux64/autogen/transform/releasename
    transformpath = get_transform_dir(releasename)
    #  check that directory exists
    if (not os.path.isdir(transformpath)):
        print "ERROR: " + transformpath + " not found. Please run from root of platform?"
        return foundfiles

    # also build filespec to search for: curfile + "*"
    searchspec = os.path.join(transformpath, curfile)
    searchspec += "*"

    # do a glob with that directory and filespec
    foundfiles = glob.glob(searchspec)
    if len(foundfiles) == 0:
        print "ERROR: No files matching filespec: " + searchspec

    # return found files (if returned list is zero length, no matches found)
    return foundfiles

def is_devbank(bankfile):
    return bankfile.startswith("DevBank_")

def is_reglayout(bankfile):
    return bankfile.startswith("RegLayout_")

# returns True if passed filename is either DevBank or RegLayout
def is_valid_bankfile(bankfile):
    return is_devbank(bankfile) or is_reglayout(bankfile)

# get directory with DevBank and RegLayout files
def get_regs_dir(releasename):
    return os.path.join("linux64/autogen/regs", releasename)

# get directory with transform scripts
def get_transform_dir(releasename):
    return os.path.join("linux64/autogen/transform", releasename)

# get names of releases found in transform directory
def get_release_names():
    releasenames = []
    if not os.path.exists("linux64/autogen/transform"):
        print "ERROR: Transform directory not found. Make sure you're running from project root (adl, tgl, etc)."
        return releasenames

    searchspec = os.path.join("linux64/autogen/transform", "*")
    tempreleases = glob.glob(searchspec)
    for currel in tempreleases:
        curname = os.path.basename(currel)
        releasenames.append(curname)

    return releasenames



# get directory with extracted crif xml
def get_extracted_dir(releasename):
    base_path = os.path.join("linux64/obj/modules", releasename)
    return os.path.join(base_path, "compiled/extracted/")

# change a DevBank to a RegLayout filename.
# zero-length return string means input file was not a DevBank or RegLayout
def get_companion_filename(bankfile):
    resultfile = ""
    if is_devbank(bankfile):
        resultfile = bankfile.replace("DevBank_", "RegLayout_", 1)

    if is_reglayout(bankfile):
        resultfile = bankfile.replace("RegLayout_", "DevBank_", 1)

    if len(resultfile) == 0:
        print "ERROR: " + bankfile + " is not a DevBank or RegLayout filename."

    return resultfile

# return a list of tuples containing transform prefix and CRIF filename
def get_devbank_map(bankfile, releasename):
    resultlist = []
    curfile = bankfile

    # make sure we're working with a devbank filename (convert RegLayout to DevBank if necessary)
    if not is_devbank(bankfile):
        #print "INFO: Not a DevBank filename. Checking if this is a RegLayout file..."
        curfile = get_companion_filename(bankfile)

    # validate returned filename
    if len(curfile) == 0:
        print "ERROR: Not a valid bank file: " + bankfile
        return resultlist

    # confirm bankfile exists
    regsdir = get_regs_dir(releasename)
    curpath = os.path.join(regsdir, curfile)
    if not os.path.exists(curpath):
        print "ERROR: Bank file not found: " + curpath
        return resultlist

    # open file and begin reading line by line
    # look for lines containing "// * "
    openfile = open(curpath, "r")
    for curline in openfile:
        if curline.find("// * ") != -1:
            # for each line, initialize curtransform and curname strings
            transformname = ""
            crifname = ""
            #print curline
            # split found line by " "
            elements = curline.split(" ")
            for curelement in elements:
                # discard anything shorter than 3 spaces
                if len(curelement) >= 3:
                    # if doesn't begin with ( it is a transform name
                    if curelement[0] != "(":
                        # - save as first element in tuple
                        transformname = curelement
                    else:
                        # if begins with ( it is a CRIF "name" tag
                        # - remove ( and ), plus the trailing :
                        crifname = curelement.translate(None, '():')
                        # - trim whitespace and save as second element in tuple
                        crifname = crifname.strip()

             # if curtransform and curname are both greater than 0 len, add to the resultlist as a 2-element tuple
            if (len(transformname) > 0) and (len(crifname) > 0):
                newtuple = (transformname, crifname)
                resultlist.append(newtuple)
            else:
                print "WARNING: Line lacked either transform or crifname: " + curelement
    # always close file
    openfile.close()

    return resultlist

def get_transform_paths(bankfile, releasename, confirmedonly = False):
    resultlist = []

    # get devbank map
    tuple_list = get_devbank_map(bankfile, releasename)
    if (len(tuple_list) == 0):
        print "ERROR: No tuples returned from query: " + bankfile + ", " + releasename
        return resultlist

    # if tuples found, build paths (transformdir + transformname + ".py")
    for curtuple in tuple_list:
        curpath = get_transform_dir(releasename)
        curpath = os.path.join(curpath, curtuple[0])
        curpath += ".py"
        addtolist = True
        #print curpath
        if (confirmedonly):
            if not os.path.exists(curpath):
                print "WARNING: File not found: " + curpath
                addtolist = False
        if addtolist:
            resultlist.append(curpath)

    # return list
    return resultlist

def is_string_in_file(filepath, searchtext):
    result = False

    try:
        # open read-only file and search for text until found or EOF
        openfile = open(filepath, "r")
        for curline in openfile:
            if curline.find(searchtext) != -1:
                result = True
                break
        openfile.close()
    except:
        print "ERROR: Exception thrown ", sys.exc_info()[0], sys.exc_info()[1]

    return result


def get_crif_paths(bankfile, releasename):
    # get devbank map
    resultlist = []
    tuple_list = get_devbank_map(bankfile, releasename)
    if (len(tuple_list) == 0):
        print "ERROR: No tuples returned from query: " + bankfile + ", " + releasename
        return resultlist

    for curtuple in tuple_list:
        resultlist += search_crifs_for_text(curtuple[1], releasename)

    return resultlist

def search_crifs_for_text(searchtext, releasename):
    resultlist = []

    # get and confirm crif XML directory
    crifdir = get_extracted_dir(releasename)
    if (not os.path.exists(crifdir)):
        print "ERROR: Directory not found: " + crifdir
        return resultlist

    # get list of all crif files in dir
    searchspec = os.path.join(crifdir, "*.xml")
    criflist = glob.glob(searchspec)
    if len(criflist) == 0:
        print "ERROR: No CRIF XML files found in " + crifdir
        return resultlist

    # if tuples found, build paths (transformdir + transformname + ".py")
    for curfile in criflist:
            if is_string_in_file(curfile, searchtext):
                resultlist.append(curfile)

    # return list
    return resultlist

def dump_crif_details(criffile):
    # open xml file
    xml_tree = etree.parse(criffile)
    crifel = xml_tree.getroot()
    for curreg in crifel.findall("registerFile"):
        print_element(curreg, "name")
        print_element(curreg, "longName")
        print_element(curreg, "type")
        print_element(curreg, "portid")
        print_element(curreg, "Fabric")
        print_element(curreg, "Opcode")
        print_element(curreg, "prefix")
        print_element(curreg, "SB_Fid")
        #print_element(curreg, "description")
#                        crifname = curelement.translate(None, '():')
        curel = curreg.find("description")
        temptext = curel.text
        temptext = temptext.replace("\n", ', ')
        print "\t" + curel.tag + " = " + temptext

        #nameel = curreg.find("name")
        #print nameel.tag + " + " + nameel.text
        #nameel = curreg.findall("name")
        #for thisel in nameel:
            #print thisel.tag + thisel.text
        #for thisname in curreg.iter("name"):
            #print thisname.tag + " = " + thisname.text
        #for child in curreg:
            #print child.tag, child.attrib

def print_element(rootel, tagname):
    curel = rootel.find(tagname)
    if (curel != None):
        print "\t" + curel.tag + " = " + curel.text
    else:
        print "\t" + tagname + " not found."

# compares two crif directories and builds/returns lists of which releases have unique banks
# and which banks are shared. returns None in case of general failure, otherwise returns a tuple
# containing left_only, right_only, both_lists. The both_lists is itself a list of tuples (0 = left, 1 = right)
def compare_crif_dirs(leftdir, rightdir, namesubstr = None):
    left_only = []
    right_only = []
    both_lists = [] # list of tuples for both left and right

    print "Loading left CRIF from " + leftdir + "..."
    left_full = load_crif_dir(leftdir, namesubstr)
    if not left_full:
        print "ERROR: Unable to load CRIF data from " + leftdir
        return None

    print "Loading right CRIF from " + rightdir + "..."
    right_full = load_crif_dir(rightdir, namesubstr)
    if not right_full:
        print "ERROR: Unable to load CRIF data from " + rightdir
        return None

    print "Searching right list for banks in left..."
    for curreg_left in left_full:
        foundmatch = False
        for curreg_right in right_full:
            if (curreg_left.original_registerfile_name == curreg_right.original_registerfile_name):
                # found a matching bank; end search here
                foundmatch = True
                both_lists.append((curreg_left, curreg_right))
                break
        if not foundmatch:
            # didn't find exact bank match
            left_only.append(curreg_left)

    print "Searching left list for banks in right..."
    for curreg_right in right_full:
        foundmatch = False
        for curreg_left in left_full:
            if (curreg_left.original_registerfile_name == curreg_right.original_registerfile_name):
                # found a matching bank; end search here
                foundmatch = True
                # NOT adding to both list, since it has already been captured
                break
        if not foundmatch:
            # didn't find exact bank match
            right_only.append(curreg_right)

    return (left_only, right_only, both_lists)


# loads all XML files in specified directory and returns a list of all the resulting SrcBanks.
# returns None on error
def load_crif_dir(workdir, namesubstr = None):
    bank_list = []

    if not os.path.exists(workdir):
        print "ERROR: Directory doesn't exist: " + workdir
        return bank_list

    filelist = glob.glob(os.path.join(workdir, "*.xml"))
    if len(filelist) == 0:
        print "ERROR: No files found matching", os.path.join(workdir, "*.xml")
        return False

    for curpath in filelist:
        #print curpath
        crsrcbank = parse(curpath, workdir, (False,))
        if (not crsrcbank):
            print "WARNING: Parse failed for " + curpath
            continue

        # print xml filename
        #if crsrcbank.src_file:
        #    print "src_file: " + crsrcbank.src_file
        # print crif bank name
        #if crsrcbank.original_registerfile_name:
        #    print "original_registerfile_name: " + crsrcbank.original_registerfile_name
        additem = True
        if namesubstr:
            if (not crsrcbank.original_registerfile_name) or (crsrcbank.original_registerfile_name.find(namesubstr) == -1):
                # skip this item, because it doesn't match our search
                additem = False
        if additem:
            bank_list.append(crsrcbank)

    # sort returned list
    bank_list.sort(key=lambda x: x.original_registerfile_name, reverse=False)

    return bank_list


# main function for testing
def main(*kwargs):

    # default values
    cmd = "help"
    releasename = "tgl-h-p0-19ww18"
    bankfile = ""
    targetdir = None
    workdir = None # general purpose directory variable
    crifname = None
    verbose = False
    otherdir = None

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
            print "Key: " + key + " Value: " + val
            # populate supported variables
            if key[0] == "b":
                bankfile = val
            elif key[0] == "r":
                releasename = val
            elif key[0] == "c":
                crifname = val
            elif key[0] == "t":
                targetdir = val
            elif key[0] == "d":
                workdir = val
            elif key[0] == "o":
                otherdir = val
            else:
                print "Unexpected parameter key: " + key
        elif (key != None):
            # no value, must be command or "verbose"
            if key[0] == "v":
                print "Enabling verbose mode."
                verbose = True
            else:
                cmd = key
                print "Command = " + cmd

    # execute commands
    if (cmd[0] == "h"):
        # help
        print "\nusage: cdbfuncs.py [COMMAND] [KEY=VALUE]..."
        print   "Perform various lookup commands in platform CDB-related files (CRIF XML, transforms, register DML)."
        print   "Must be run from the root of a VP platform (adl, tgl, etc.)."
        print "\nCommands:"
        print   " help - Show this info."
        print   " dump [b=bankfile] [r=releasename] [t=targetdir] - Dump info based on DevBank or RegLayout bankfile in named release."
        print   "      If targetdir parameter is passed, copies any confirmed files to that target directory."
        print   " folders [r=releasename] - List important CDB folders for the named release."
        print   " name [c=crifname] [r=releasename] - Locate CRIF XML files containing crifname substring in named release."
        print   " releases - List release names found in current transform directory."
        print   " loadcrif [d=directory] [c=crifname] [verbose] - Load the contents of an entire CRIF XML directory into a list of banks."
        print   "          crifname parameter is optional. If specified, only CRIF banks that contain the passed substring in their"
        print   "          name are returned. If verbose is specified, register and field names will also be included."
        print   " comparecrif [d=directory] [o=otherdirectory] [c=crifname] - compare the contents of two CRIF XML directories."
        print   "             crifname parameter is optional and can narrow the results to matching CRIF name substring."

    elif (cmd[0] == "f"):
        print "\n*** FOLDERS (" + releasename + ") ***"
        print get_regs_dir(releasename)
        print get_transform_dir(releasename)
        print get_extracted_dir(releasename)
    elif (cmd[0] == "d"):
        print "\n*** DUMP (" + releasename + ") ***"
        # do a length check since the bash function wrapper sends a zero-length param
        if len(bankfile) == 0:
            print "\nERROR: You must at least specify a bankfile to proceed further."
            return -1

        if len(releasename) == 0:
            print "\nERROR: You must at least specify a release name."
            return -1

        print "\n*** DEVBANK INFO ***"
        tuple_list = get_devbank_map(bankfile, releasename)
        if (len(tuple_list) == 0):
            print "ERROR: No tuples returned from query: " + bankfile + ", " + releasename
        else:
            for curtuple in tuple_list:
                print curtuple[0], " / ", curtuple[1]

        print "\n*** TRANSFORM FILES (confirmed) ***"
        transformpaths = get_transform_paths(bankfile, releasename, True)
        if len(transformpaths) == 0:
            print "ERROR: No transforms returned."
        else:
            for curtrans in transformpaths:
                print curtrans
                if (targetdir != None):
                    if (not os.path.isdir(targetdir)):
                        print "ERROR: Directory not found: " + targetdir
                        return -1
                    targetfilename = os.path.basename(curtrans)
                    targetfilepath = os.path.join(targetdir, targetfilename)
                    # only copy file if target not found (might have already edited a version)
                    if os.path.exists(targetfilepath):
                        print "WARNING: File already exists: " + targetfilepath
                    else:
                        try:
                            copyfile(curtrans, targetfilepath)
                            print "INFO: Copied to " + targetfilepath
                        except:
                            print "ERROR: ", sys.exc_info()[0], sys.exc_info()[1]

        print "\n*** CRIF FILES (might take some time...) ***"
        crifpaths = get_crif_paths(bankfile, releasename)
        if len(crifpaths) == 0:
            print "ERROR: No CRIF files returned."
        else:
            for curcrif in crifpaths:
                print curcrif
                dump_crif_details(curcrif)
    elif (cmd[0] == "n"):
        # name (search)
        print "\n*** CRIF FILES (might take some time...) ***"
        crifpaths = search_crifs_for_text(crifname, releasename)
        if len(crifpaths) == 0:
            print "ERROR: No CRIF files returned."
        else:
            for curcrif in crifpaths:
                print curcrif
                dump_crif_details(curcrif)
    elif (cmd[0] == "r"):
        # releases
        releasenames = get_release_names()
        if len(releasenames) == 0:
            print "ERROR: No releases found in transform folder."
            return -1

        print "\n*** RELEASE NAMES ***"
        for currel in releasenames:
            print currel
    elif (cmd[0] == "l"):
        # loadcrif
        if workdir == None:
            print "ERROR: Please specify a directory to scan for CRIF XML files."
            return -1

        print "\n*** Loading CRIF contents from " + workdir + " (this may take a while...)"
        bank_list = load_crif_dir(workdir, crifname)
        if not bank_list:
            print "ERROR: load_crif_dir returned an empty list."
            return -1

        # dump results
        for curbank in bank_list:
            print curbank.original_registerfile_name
            # print name used for DML file
            print     "\t    dml_name: " + curbank.dml_name()
            # get_bank_name is in Bank class, not SrcBank
            #print "bank_name: " + curbank.get_bank_name()
            # print name used for transform and pickle files
            print     "\tsrc_basename: " + curbank.src_basename

            if verbose:
                print "\t   Registers (" + str(len(curbank.regs)) + "):"
                #curbank.sort_regs()
                curbank.regs.sort(key=lambda reg: reg.name)
                for curreg in curbank.regs:
                    print "\t\t" + curreg.name
                    print "\t\t\tFields (" + str(len(curreg.fields)) + "):"
                    for curfield in curreg.fields:
                        print "\t\t\t\t" + curfield.name
                print "\n"

            # make space
            print "\n"
    elif (cmd[0] == "c"):
        # comparecrif
        print
        result_tuple = compare_crif_dirs(workdir, otherdir, crifname)
        if not result_tuple:
            print "\nERROR: compare_crif_dirs failed."
            return -1
        if not result_tuple[0]:
            print "\nWARNING: No left-only list."
        else:
            print "\n*** Banks only found in " + workdir + " (" + str(len(result_tuple[0])) + "):"
            for curbank in result_tuple[0]:
                print "\t{0} (left), {1}, {2}".format(curbank.original_registerfile_name, curbank.dml_name(), curbank.src_basename)

        if not result_tuple[1]:
            print "WARNING: No right-only list."
        else:
            print "\n*** Banks only found in " + otherdir + " ("+ str(len(result_tuple[1])) + "):"
            for curbank in result_tuple[1]:
                print "\t{0} (right), {1}, {2}".format(curbank.original_registerfile_name, curbank.dml_name(), curbank.src_basename)

        if not result_tuple[2]:
            print "WARNING: No found-in-both list."
        else:
            print "\n*** Banks found in both directories (" + str(len(result_tuple[2])) + "):"
            for curtuple in result_tuple[2]:
                dml_name_out = curtuple[0].dml_name()
                if (dml_name_out != curtuple[1].dml_name()):
                    dml_name_out += "->"
                    dml_name_out += curtuple[1].dml_name()
                src_basename_out = curtuple[0].src_basename
                if (src_basename_out != curtuple[1].src_basename):
                    src_basename_out += "->"
                    src_basename_out += curtuple[1].src_basename
                print "\t{0}, {1}, {2}".format(curtuple[0].original_registerfile_name, dml_name_out, src_basename_out)
    else:
        print "ERROR: Unexpected command: " + cmd + ". Please run with help as an argument to see supported commands."

    print " "

if __name__== "__main__":
    main(*sys.argv[1:])