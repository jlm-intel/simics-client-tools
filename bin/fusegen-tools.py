#!/usr/intel/bin/python3.7.4

# This is a multi-purpose script for extracting different kinds of information out of
# fusegen XML files. At initial check-in it supports three use cases:
# - Generate a worksheet that contains lockout value IDs for all fuses. ("default mode")
# - Generate a text file that contains computed lockout values for arbitraty groups of fuses. ("compute mode")
# - Generate a list of fuses/softstraps that use groups other than 0-3 for fuse & 4 for straps ("high_groups mode")
# - Generate an editable fuse patch file based on a list of fuse names ("make_patch mode")

import xml.etree.cElementTree as etree

import argparse
import os
import math

BYTE_BITS = 8
INVALID_GROUP = -1
DIRECT_FUSE = "DirectFuse"
SOFT_STRAP = "SoftStrap"
DWORD_BYTES = 4

def parse_args():
    parser = argparse.ArgumentParser(description="Lockbit dumper and computer")
    parser.add_argument('--source', metavar='source', type=str,
                        default = "fusegen.xml", required=False,
                        help='Source fusegen XML file to parse for fuse data.')
    parser.add_argument('--target', metavar='target',
                        type=str,
                        default="lockbits.csv", required=False,
                        help='Output filename. In default mode, this is a '
                            'CSV file containing info on all fuses. In compute '
                            'mode it is a text file that contains the combined '
                            'bit flags for the fuses listed in the fuse name '
                            'input file.')
    parser.add_argument('--name_file', metavar='name_file', type=str,
                        default='', required=False,
                        help='Optional file, passed as input, that contains '
                            'a list of fuse names (one per line). Script '
                            'looks up the fuses by name and computes a single '
                            'combined bit flag value representing the LVID '
                            'bits of all found fuses.')
    parser.add_argument('--names_only', action='store_true', help='Causes '
                            'script to generate a "names file" containing '
                            'all the names of the fuses in this file instead'
                            'of a CSV file. Used for cases where you need to'
                            'batch-compute a bunch of lockout ID bits.')
    parser.add_argument('--high_groups', action='store_true', help='Run in '
                            'high-groups mode which looks for fuses and straps '
                            'with new-style groups (fuses > 3, straps != 4). '
                            'This is to identify IPs that need to specify the '
                            'correct pulling style for newer fuses/straps')
    parser.add_argument('--make_patch', action='store_true', help='Run in '
                            'generate patch mode, which reads an input file '
                            'of fuse names (--name_file) and generates a '
                            'patch file (--target) with the values from '
                            'fusegen.')
    parser.add_argument('--update_patch', action='store_true', help='Create '
                            'a new fuse patch based on a pre-existing patch '
                            'file and a default_fuse_values file. Values from '
                            'old patch are preserved but new patch will use '
                            'memory locations and sizes from the '
                            'default_fuse_values file. Requires --old_patch, '
                            '--target, and --default_values arguments. '
                            'Optionally takes --imported_values argument.')
    parser.add_argument('--reconcile_patch', action='store_true',
                        required=False, help='Run in reconcile mode, which '
                        'creates a new patch by looking up fuses by address '
                        'and startbit in an older patch file and determining '
                        'which fuses they represent in a provided '
                        'default_fuse_values.txt file. Requires the '
                        '--old_patch and --default_values arguments.')
    parser.add_argument('--prune_patch', action='store_true', help='Generate '
                        'a new copy of a given patch file that only contains '
                        'fuses whose values are different from the fusegen '
                        'defaults. Requires --old_patch, --default_values, '
                        'and --target.')
    parser.add_argument('--compare_patch', action='store_true',
                        help='Compares an old patch to a new one and prints '
                        'a report of differences. Requires --old_patch and '
                        '--new_patch arguments.')
    parser.add_argument('--compare_xml', action='store_true',
                        help='Compares an old fusegen XML to a new one and prints '
                        'a report of differences. Requires --old_patch and '
                        '--new_patch. (Pass XML filenames.) Optionally takes'
                        '--prefix to search only for fuses whose names start '
                        'with the given prefix.')
    parser.add_argument('--old_patch', metavar='old_patch', type=str,
                        default='', required=False,
                        help='(Required for --update_patch mode) Path to an '
                            'existing fuse patch.')
    parser.add_argument('--new_patch', metavar='new_patch', type=str,
                        default='', required=False,
                        help='(Required for --compare_patch mode) Path to an '
                            'existing fuse patch.')
    parser.add_argument('--default_values', metavar='default_values', type=str,
                        default='', required=False,
                        help='(Required for --update_patch mode) Path to an '
                            'existing default_fuse_values file.')
    parser.add_argument('--imported_values', metavar='imported_values', type=str,
                        default='', required=False,
                        help='Optional argument for --update_patch. Specifies '
                        'an additional file to load as source data when '
                        'updating a patch. Any fuses not already specified '
                        'in the pre-existing fuse patch file will be added to '
                        'the patch from this file. Duplicate entries will be '
                        'ignored.')
    parser.add_argument('--locked_fuses', metavar='locked_fuses', type=str,
                        default='', required=False,
                        help='Optional argument for --update_patch. Specifies '
                        'a file that contains a list of fuses whose values '
                        'should not be replaced when --imported_values option '
                        'is used. This lets us adopt new values in future '
                        'fuse releases without breaking fuses we know we '
                        'need to override.')
    parser.add_argument('--config_out', metavar='config_out', type=str,
                        default='', required=False,
                        help='Specify a config.out filename (associated with '
                             'pcode and dcode releases). When called with '
                             '--update_patch, will update and add PCODE or '
                             'DCODE fuses with values from this file. '
                             'NOTE: Filename should contain either "pcode"'
                             'or "dcode" to determine which fuse prefix to use.')
    parser.add_argument('--fuse_default_ovrd', metavar='fuse_default_ovrd', type=str,
                        default='', required=False, help='Similar to config_out '
                        'option, but uses the fusegen default override format. '
                        'Mutually exclusive with the config_out option.')
    parser.add_argument('--dump_blob', metavar='dump_blob', type=str,
                        default='', required=False,
                        help='Specify a file representing a pcode or dcode blob '
                        'in hex string format and an associated default_values '
                        'file and writes a report indicating the address and '
                        'value of every byte, plus fuses found at that memory '
                        'address. Uses --default_values, --target, '
                        'and --start_address arguments.')
    parser.add_argument('--import_text_blob', metavar='import_text_blob', type=str,
                        default='', required=False,
                        help='Import a TXT blob file and extract the fuse '
                        'values from it, saving the results as a giant patch '
                        'file. Only different values are saved. Uses --target, '
                        '--default_values, --group_number, --source, and --prefix. Optionally takes --type_softstrap if you are decoding a softstrap payload (default is fuses).'
                        '*Text blob comes from "data response ready" line in '
                        'fuse controller logs.*')
    parser.add_argument('--import_int_blob', metavar='import_int_blob', type=str,
                        default='', required=False,
                        help='Import a TXT blob file and extract the fuse '
                        'values from it, saving the results as a giant patch '
                        'file. Only different values are saved. Uses --target, '
                        '--default_values, --group_number, and --prefix. '
                        '*These blobs are the TXT files used for pcode and dcode '
                        'fuse overrides specified in platform.target.yml.*')
    parser.add_argument('--prefix', metavar='prefix', type=str, default='',
                        help='Prefix of fuses you are searching for when '
                        'importing blobs. punit_punit_fw_fuses or '
                        'dmu_fuse_fw_fuses')
    parser.add_argument('--start_address', metavar='start_address', type=str,
                        default='', required=False,
                        help='A memory address where the blob dump starts.')
    parser.add_argument('--pcode-stats', action='store_true', help='Scans a '
                            'HUB fusegen XML file for PUNIT FW fuses and '
                            'returns relevant details')
    parser.add_argument('--dcode-stats', action='store_true', help='Scans a '
                            'HUB fusegen XML file for DMU FW fuses and '
                            'returns relevant details')
    parser.add_argument('--dump_dlut', action='store_true', help='Dumps the '
                            'Distribution Lookup Table (DLUT) from XML into '
                            'CSV format. Uses the --source and --target '
                            'arguments.')
    parser.add_argument('--dump_ip_info', action='store_true', help='Dumps the '
                            'SOC IP Instance from XML into '
                            'CSV format. Uses the --source and --target '
                            'arguments.')
    parser.add_argument('--print_fuse_stats', action='store_true', help='Prints '
                            'stats for all fuses and softstraps on a per-IP basis. '
                            'Uses the --source argument.')
    parser.add_argument('--type_softstrap', action='store_true', help='Indicates '
                            'that you are interested in SoftStrap groups instead '
                            'of DirectFuse groups. Used by --import_int_blob and '
                            '--import_text_blob. DirectFuse is assumed if you do '
                            'not pass this argument')
    parser.add_argument('--group', metavar='group', type=int,
                        default=INVALID_GROUP, help='Specifies which DirectFuse or '
                        'SoftStrap group number you wish to import when using '
                        '--import_text_blob or --import_int_blob. You must specify '
                        'a valid group when using these options.')
    parser.add_argument('--merge_values', action='store_true', help='Imports '
                        'values from a fuse override file (in name=value '
                        'format) and updates the values from a '
                        '--default_values file, saving the results to '
                        '--target file.  Use --changes_only to save a target'
                        'that only includes items with updated values.')
    parser.add_argument('--changes_only', action='store_true', help='Optional '
                        'argument for --merge_values that will only save '
                        'items where the value has changed.')
    parser.add_argument('--merge_patches', action='store_true', help='Combines '
                        'two patches into a single patch. Both patches MUST '
                        'be based on the same fusegen. In case where values '
                        'for the same fuse are different, --new_patch values '
                        'will be used (unless --locked_fuses is specified). '
                        'Required: --old_patch, --new_patch, and --target. '
                        'Optional: --locked_fuses')
    args = parser.parse_args()
    return args


# imported from cdb_classes.py
class MyException(Exception):
    pass


# imported from cdb_api.py
def process_value(text, bit_length=None, info=""):
    # if bit_length argument is set, print a warning if the value doesn't fit

    if text == "0/0/0":
        return 0

    base = 0

    if text is None or text == "None":
        return 0

    text_to_parse = text

    text = text.replace("_", "")

    if text[0] == '{' and text[-1] == '}':
        text = text[1:-1]

    if "'" in text:
        text = text.split("'")[1] #in input like 5'b10111 take just b10111

    if text.startswith('0x'):#0x7c or x7c
        text = text[2:]
        base = 16

    elif text.startswith('x'): #x7c
        text = text.strip('x')
        base = 16

    elif text.endswith('h') or text.startswith('h'): #h1fd or 1fh
        text = text.strip('h')
        base = 16

    elif text.endswith('b') or text.startswith('b'): #b101 or 11b
        text = text.strip('b')
        base = 2

    elif text.endswith('d') or text.startswith('d'): #d19 or 99d
        text = text.strip('d')
        base = 10

    elif text.isdigit():
        base = 10

    if (text == "S") or (text == "s"):
        return 0

    if text == "F" and base != 16:
        return 0

    if text == "-":
        return 0

    if text == "'1":
        return 1

    try:
        text = int(text, base)
    except ValueError as ex:
        raise MyException("Error: Cannot parse value %s: %s\n" % (text_to_parse, repr(ex)))

    # check length
    if bit_length and bit_length < len(bin(text)) - 2:
        print("Warning: defined field value too long: bit length %d cannot fit value %#x (%s)" % (bit_length, text, info), file=sys.stderr)

    return text


# Wrapper that iterates through XNL file and gets LVID constant info
def parse_for_constants(tree):
    root = tree.getroot()
    assert root.tag == "FuseGen"
    constants = None
    for el in root:
        if el.tag == "Constants":
            assert constants == None
            constants = parse_constants(el)
    return (constants)


# Locates the fusegen constants related to lockout value id bits and collects
# some relevant information in dict form. There is one dict object for each
# category of fuses (INTELHVM, INTELIFP, OEMIFP). Takes the fusegen XML
# tree object as input.
def parse_constants(tree):
    constants = []

    # fuse category identifiers can be different for constant vs register name
    cat_prefixes = [
        {"CONST" : "INTELHVM", "REG" : "IntelHVM"},
        {"CONST" : "INTELIFP", "REG" : "IntelIFP"},
        {"CONST" : "OEMIFP", "REG" : "OEMIFP"},
    ]

    # locate the row # constants for the 3 fuse categories
    for cur_prefix in cat_prefixes:
        # build constant name, like INTELHVM_LOVLD_ROWBEGIN
        begin_name = "%s_LOVLD_ROWBEGIN" % (cur_prefix["CONST"])
        end_name = "%s_LOVLD_ROWEND" % (cur_prefix["CONST"])

        # first pass to capture the LVID beginning rows
        for entry in tree:
            if (entry.tag != "Constant"):
                # only care about Constant elements
                continue

            ent_name = entry.attrib["Name"]
            if (ent_name != begin_name):
                # ignore other constants
                continue

            ent_value = process_value(entry.attrib["Value"])

            # construct lockout bit register name.
            # line length restrictions require breaking this string
            # format into separate commands. Note, using "name" element
            # instead of "Instance" element to identify register.
            tmp_name = "SOCFuseGen_reserved_LockoutID_%s_row_%s_bit_0"
            reg_name = tmp_name % (cur_prefix["REG"], str(ent_value))

            # add this constant to the list; ADDR and WIDTH fields will be
            # populated later
            const_entry = {
                "CONST" : cur_prefix["CONST"],
                "REG" : cur_prefix["REG"],
                "NAME" : ent_name,
                "ROWBEGIN" : ent_value,
                "ROWEND" : ent_value, # can't be lower than ROWBEGIN
                "REG_NAME" : reg_name,
                "ADDR" : 0,
                "WIDTH" : 0
            }
            constants.append(const_entry)

        # second pass to capture LVID end rows
        for entry in tree:
            if (entry.tag != "Constant"):
                # only care about Constant elements
                continue

            ent_name = entry.attrib["Name"]
            if (ent_name != end_name):
                # ignore other constants
                continue

            ent_value = process_value(entry.attrib["Value"])

            # locate entry with NAME matching begin_name
            for cur_const in constants:
                if (cur_const["NAME"] != begin_name):
                    # skip non-matching entry
                    continue

                # populate the entry with the correct closing value
                cur_const["ROWEND"] = ent_value

    # Uncomment below to see populated details about the lockout ID fuses.
    # print(constants)
    return constants


# Wrapper that iterates through XML file and gets LVID bit values
def parse_for_lockbits(tree):
    root = tree.getroot()
    assert root.tag == "FuseGen"
    lockbits = None
    for el in root:
        if el.tag == "DirectFuses":
            assert lockbits == None
            lockbits = parse_lockbits(el)
    return (lockbits)


def fixupFuseName(name):
    chars = " /-():[]#."
    for c in chars:
        name = name.replace(c, "_")
    if name[0].isdigit():
        name = "_" + name
    return name


def parse_lockbits(tree):
    lockbits = []

    for fuse in tree:
        # applies only to fuses, not straps
        if (fuse.tag != "Fuse"): continue

        name = fuse.find("name").text.strip()

        # only use "0" CatLockoutID if it's not a SOCFuseGen-generated
        # entry
        lock_id = process_value(fuse.find("CatLockoutID").text)
        if (lock_id == 0):
            if (name.find("SOCFuseGen_reserved") != -1):
                # use -1 to indicate not a real CatLockoutID.
                lock_id = -1

        fuse_entry = {
            "NAME" : fixupFuseName(name),
            "ADDR" : process_value(fuse.find("RamAddr").text),
            "CATEGORY" : fuse.find("Category").text,
            "LOCKID" : lock_id,
            "BITFLAG" : None,
            "WIDTH" : process_value(fuse.find("FUSE_WIDTH").text),
        }

        lockbits.append(fuse_entry)

    return (lockbits)


# Wrapper method that locates the DirectFuses blob in the passed fusegen
# XML element and calls parse_lockout_values.
def get_lockout_values(tree, constants):
    local_constants = []
    rt = tree.getroot()
    assert rt.tag == "FuseGen"
    for el in rt:
        if el.tag == "DirectFuses":
            # breaking below logic into separate method due to line length
            # constraints
            local_constants = parse_lockout_values(el, constants)
            # no need to continue enumerating rt elements
            break

    return local_constants


# Locates the LVID "fuse" data and extracts the RAM address and fuse width
# values for each fuse category. Returns an updated version of the passsed
# "constants" dicts that contains populated address/width values.
def parse_lockout_values(tree, constants):
    for cur_const in constants:
        for fuse in tree:
            if (fuse.tag != "Fuse") and (fuse.tag != SOFT_STRAP):
                continue

            cur_name = fuse.find("name").text
            if (cur_name != cur_const["REG_NAME"]):
                continue

            # Uncomment below to see name of category lockout fuse.
            # print("Found register %s" % cur_const["REG_NAME"])

            # get required values out of the found fuse and update the
            # dict values
            cur_const["ADDR"] = process_value(fuse.find("RamAddr").text)
            cur_const["WIDTH"] = process_value(fuse.find("FUSE_WIDTH").text)

            # there is only one of these fuses per category, stop searching
            break

    return constants


def write_csv_file(filename, lockbits, names_only):
    outf = None
    try:
        outf = open(filename, "w")
    except:
        print("ERROR: Unable to open output file (",
              filename,
              ").")
        return False

    if (not names_only):
        outf.write("\"Name\",\"RamAddr\",\"Category\",\"CatLockoutId\",\"LockIdBit\"\n")
    else:
        print(f"names_only set; only writing fuse names to file {filename}...")

    for curbit in lockbits:
        lockidbit = ""

        curlockid = curbit["LOCKID"]
        if curlockid == -1:
            # skip "fuses" that don't have lockout bits, since they are
            # not real fuses.
            continue

        bitvalue = 1 << curlockid
        curbit["BITFLAG"] = hex(bitvalue)
        if not names_only:
            outf.write("\"%s\",%#06x,\"%s\",%s,\"%s\"\n" %
                    (curbit["NAME"],
                        curbit["ADDR"],
                        curbit["CATEGORY"],
                        curlockid,
                        curbit["BITFLAG"]))
        else:
            outf.write(f"{curbit['NAME']}\n")
    outf.close()
    return True

def write_compute_file(target_file, name_file, lockbits, constants):
    success = False
    outf = None
    inf = None

    try:
        inf = open(name_file, "r")
    except:
        print("ERROR: Unable to open input file (",
              name_file,
              ").")
        return False

    try:
        outf = open(target_file, "w")
    except:
        print("ERROR: Unable to open output file (",
              target_file,
              ").")
        # close input file handle
        inf.close()
        return False

    lines = inf.readlines()
    for cur_const in constants:
        # start with an empty category bit map
        cat_map = 0
        combined_width = 0

        lineout = "\nComputing %s LVID values..." % cur_const["REG"]
        print(lineout)
        outf.write(lineout + "\n")
        for cur_line in lines:
            found_match = False
            cur_name = cur_line.strip()
            if (len(cur_name) == 0):
                # skip blank lines
                continue
            for cur_fuse in lockbits:
                if (cur_fuse["CATEGORY"] != cur_const["REG"]):
                    # skip fuses for other categories
                    continue
                if (cur_fuse["LOCKID"] == -1):
                    # skip "fuses" that don't have a lockout id
                    continue
                if (cur_fuse["NAME"] != cur_name):
                    # skip fuses that don't match the name
                    continue
                else:
                    found_match = True
                    # stop searching, because we found a match in category
                    break

            if (found_match):
                # cumulatively combine bits from matching fuses
                cur_bit_map = 1 << cur_fuse["LOCKID"]
                combined_width += cur_fuse["WIDTH"]
                lineout = "%s lockout bit: %s" % (cur_name, hex(cur_bit_map))
                print(lineout)
                outf.write(lineout + "\n")
                cat_map = (cat_map | cur_bit_map)

        # the final value should be padded to the correct number of zeroes
        # for the width of this category's LockoutID row.
        # 1 zero for every 4 bits, plus 2 more characters for "0x"
        num_zeroes = (int(cur_const["WIDTH"] / 4)) + 2
        cat_map_fmt = f"{cat_map:#0{num_zeroes}x}"

        lineout = "%s value for %s fuses: %s" % (cur_const["REG_NAME"],
                                            cur_const["REG"],
                                            cat_map_fmt)
        print(lineout)
        outf.write(lineout + "\n")

        lineout = "Total width of %s fuses in bits: %d (%d bytes/%s hex)" % (cur_const["REG"],
            combined_width, (combined_width / 8), hex(int(combined_width / 8)))
        print(lineout)
        outf.write(lineout + "\n")

    lineout = "\nNOTE: Remove the \'0x\' prefix if pasting the LockoutID value into a fuse patch file.\n"
    print(lineout)
    outf.write(lineout)

    # do a final pass that ignores category in case user included a
    # bogus fuse name
    for cur_line in lines:
        found_match = False
        cur_name = cur_line.strip()
        if (len(cur_name) == 0):
            # skip blank lines
            continue
        for cur_fuse in lockbits:
            if (cur_fuse["NAME"] != cur_name):
                # skip fuses that don't match the name
                continue
            if (cur_fuse["NAME"] == cur_name):
                found_match = True
                # stop searching, because we found a match in category
                break

        if (False == found_match):
            # warn user of invalid fuse name and skip to next line
            print("WARNING: Could not find valid fuse named", cur_name,
                    "for any fuse category.")

    # if we're here, we succeeded
    success = True
    inf.close()
    outf.close()
    return success


# Wrapper that iterates through XML file and gets items with new-style groups.
def parse_for_high_groups(tree):
    root = tree.getroot()
    assert root.tag == "FuseGen"
    high_groups = []
    for el in root:
        if ((el.tag == "DirectFuses") or (el.tag == "SoftStraps")):
            high_groups = parse_high_groups(el, high_groups)
    return (high_groups)

# Get fuses and straps with non-standard group numbers.
def parse_high_groups(tree, high_groups):
    local_groups = high_groups

    for fuse in tree:
        type = fuse.find("Group").text
        groupnum = process_value(fuse.find("GroupNumber").text)
        name = fuse.find("name").text.strip()
        name = fixupFuseName(name)
        #print(f'{name}, {type}, {groupnum}')

        # make sure current item matches our requirements
        matches = False
        portid = 0
        if (type == SOFT_STRAP):
            # any group number other than 4 is non-standard
            if (groupnum != 4):
                matches = True
        elif (type == DIRECT_FUSE):
            # any group number greater than 3 qualifies
            if (groupnum > 3):
                matches = True

        # weed out items that don't have port ids
        if fuse.find("IOSFSBPortID").text.strip() != "":
            portid = process_value(fuse.find("IOSFSBPortID").text)
        else:
            # probably not a real strap or fuse (SOCFuseGen_reserved)
            #print(f'Item {name} has no valid IOSFSBPortID.')
            matches = False

        if (False == matches):
            # discard if no match
            continue

        # get rest of values
        addr = process_value(fuse.find("RamAddr").text)
        category = fuse.find("Category").text

        # build fuse entry item and add to list
        # category, SB id, fuse name, fuse address, type, group#
        fuse_entry = {
            "CATEGORY" : category,
            "PORTID" : portid,
            "NAME" : name,
            "ADDR" : addr,
            "TYPE" : type,
            "GROUPNUM" : groupnum
        }
        print(f'Adding {name}...')
        local_groups.append(fuse_entry)

    return local_groups


def write_groups_csv_file(filename, high_elements):
    outf = None
    try:
        outf = open(filename, "w")
    except:
        print("ERROR: Unable to open output file (",
              filename,
              ").")
        return False

        # <Category>, "CATEGORY"
        # <IOSFSBPortID>, "PORTID"
        # <name>, "NAME"
        # <RamAddr>, "ADDR"
        # <Group>, "TYPE"
        # <GroupNumber> "GROUPNUM"
    outf.write("\"CATEGORY\",\"PORTID\",\"NAME\",\"ADDR\",\"TYPE\",\"GROUPNUM\"\n")

    for curel in high_elements:
        outf.write("\"%s\",%#02x,\"%s\",%#06x,\"%s\",%d\n" %
                   (curel["CATEGORY"],
                    curel["PORTID"],
                    curel["NAME"],
                    curel["ADDR"],
                    curel["TYPE"],
                    curel["GROUPNUM"]))

    outf.close()
    return True

def parse_matches(tree, matches, lines):
    local_matches = matches

    for fuse in tree:
        name = fuse.find("name").text.strip()
        name = fixupFuseName(name)
        #print(f'{name}, {type}, {groupnum}')

        # make sure current item matches our requirements
        for cur_line in lines:
            stripped_line = cur_line.strip()
            if (name.find(stripped_line) != -1):
                # match found
                fuse_entry = {
                    "NAME" : name,
                    "ADDR" : process_value(fuse.find("RamAddr").text),
                    "STARTBIT" : process_value(fuse.find("StartBit").text),
                    "WIDTH" : process_value(fuse.find("FUSE_WIDTH").text),
                    "VALUE" : process_value(fuse.find("FuseDefaultValue").text),
                    "TYPE" : fuse.find("Group").text
                }
                local_matches.append(fuse_entry)

    return local_matches


def parse_for_matches(tree, lines):
    root = tree.getroot()
    assert root.tag == "FuseGen"
    matches = []
    for el in root:
        if ((el.tag == "DirectFuses") or (el.tag == "SoftStraps")):
            matches = parse_matches(el, matches, lines)
    return (matches)

def make_patch(input_tree, target_file, name_file):
    success = True

    # read name_file into list of lines
    inf = None
    try:
        inf = open(name_file, "r")
    except:
        print(f"ERROR: Unable to open input file {name_file}")
        return False
    lines = inf.readlines()
    inf.close()

    # for each entry in name_file, locate a matching fuse or strap and capture
    # the following:
    # <name>, "NAME"
    # <RamAddr>, "ADDR"
    # <StartBit> "STARTBIT"
    # <FUSE_WIDTH> "WIDTH"
    # <FuseDefaultValue> "VALUE"
    matches = parse_for_matches(input_tree, lines)

    if (False == save_patch_items(target_file, matches)):
        print(f"ERROR: Failed to create file {target_file}")
        return False

    # identify any fuses in name file not found in xml
    for cur_line in lines:
        found_match = False
        stripped_line = cur_line.strip()
        for cur_match in matches:
            cur_name = cur_match['NAME']
            if (cur_name.find(stripped_line) != -1):
                found_match = True
                break
        if (found_match == False):
            print(f"WARNING: Did not find \"{stripped_line}\" in fusegen file.")

    return success

def get_fuse_stats(tree, name_prefix):
    lowest_fuse = None
    highest_fuse = None
    root = tree.getroot()
    assert root.tag == "FuseGen"
    for el in root:
        if el.tag == "DirectFuses":
            for fuse in el:
                name = fuse.find("name").text.strip()
                if (not name.startswith(name_prefix)):
                    # skip if no match
                    continue
                # create an entry for this fuse
                fuse_entry = {
                    "NAME" : name,
                    "RAMADDR" : process_value(fuse.find("RamAddr").text),
                    "STARTBIT" : process_value(fuse.find("StartBit").text),
                    "WIDTH" : process_value(fuse.find("FUSE_WIDTH").text),
                    "RCVRADDR" : process_value(fuse.find("RcvrAddr").text),
                }
                if (lowest_fuse is None):
                    # no lowest recorded yet, use current
                    lowest_fuse = fuse_entry
                else:
                    if (lowest_fuse['RCVRADDR'] > fuse_entry['RCVRADDR']):
                        # lowest receiver address wins
                        lowest_fuse = fuse_entry
                    elif (lowest_fuse['RCVRADDR'] == fuse_entry['RCVRADDR']) and (lowest_fuse['STARTBIT'] > fuse_entry['STARTBIT']):
                        # same receiver address, but lower startbit wins
                        lowest_fuse = fuse_entry
                if (highest_fuse is None):
                    highest_fuse = fuse_entry
                else:
                    if (highest_fuse['RCVRADDR'] < fuse_entry['RCVRADDR']):
                        # highest receiver address wins
                        highest_fuse = fuse_entry
                    elif (highest_fuse['RCVRADDR'] == fuse_entry['RCVRADDR']) and (highest_fuse['STARTBIT'] < fuse_entry['STARTBIT']):
                        # same receiver address, but higher startbit wins
                        highest_fuse = fuse_entry

    return lowest_fuse, highest_fuse

def get_pcode_stats(tree):
    return get_fuse_stats(tree, "punit/punit_fw_fuses_")

def get_dcode_stats(tree):
    return get_fuse_stats(tree, "dmu_fuse/fw_fuses_")

def load_fuse_names(filepath):
    items = []
    try:
        inf = open(filepath, "r")
    except:
        print(f"ERROR: Unable to open input file {filepath}")
        return items

    lines = inf.readlines()
    inf.close()

    for cur_line in lines:
        stripped = cur_line.strip()
        line_parts = stripped.split(" ", 7)
        if line_parts[0][0] == "#":
            # skip commented lines
            continue

        descrip_part = line_parts[0]
        items.append(descrip_part)

    print(f"INFO: Found {len(items)} items in file {filepath}")
    return items

def load_patch_items(filepath, prefix = ""):
    items = []
    prefix_filter = False
    if (len(prefix) > 0):
        prefix_filter = True
    try:
        inf = open(filepath, "r")
    except:
        print(f"ERROR: Unable to open input file {filepath}")
        return items

    lines = inf.readlines()
    inf.close()

    for cur_line in lines:
        stripped = cur_line.strip()
        line_parts = stripped.split(" ", 7)
        if line_parts[0][0] == "#":
            # skip commented lines
            continue

        addr = int(line_parts[0], 16)
        startbit = int(line_parts[1], 10)
        numbits = int(line_parts[2], 10)
        fuses_val = int(line_parts[3], 16)
        # line_parts[4] is just a '#'
        descrip_part = line_parts[5]
        # print(f"descrip_part: >{descrip_part}<")

        if (prefix_filter):
            if (not name.descrip_part(prefix)):
                # skip this fuse; doesn't match filter
                continue

        item_type = "(fuse)"
        try:
            item_type = line_parts[6]
        except:
            item_type = "(fuse)"

        new_item = {
            "ADDR" : addr,
            "STARTBIT" : startbit,
            "WIDTH" : numbits,
            "VALUE" : fuses_val,
            "NAME" : descrip_part,
            "TYPE" : item_type,
            "CFGITEM" : False,
            "SKIP" : False
        }
        items.append(new_item)

    print(f"INFO: Found {len(items)} items in file {filepath}")
    return items

def update_patch(old_items, new_items, target_path):
    num_old_items = len(old_items)
    items_updated = 0
    items_not_found = 0
    items_skipped = 0
    tmp_items = []

    outf = None
    try:
        outf = open(target_file, "w")
    except:
        print(f"ERROR: Unable to create target file {target_file}")
        return False

    outf.write("# RamAddr (hex) StartBit (dec) Width (dec) Value (hex)\n")
    for cur_old in old_items:
        cur_new = find_by_name(cur_old["NAME"], new_items)
        if (cur_new is None):
            items_not_found += 1
            print(f"WARNING: Could not find item named {cur_old['NAME']} in default_values file.")
            continue

        # if this is a config.out item, skip it if the value isn't different from default
        if (cur_old['CFGITEM'] == True):
            if cur_old['VALUE'] == cur_new['VALUE']:
                cur_old['SKIP'] = True
                print(f"Skipping {cur_old['NAME']} since its value is same as default (0x{cur_old['VALUE']:x})")
                items_skipped += 1
                continue

        # update everything but name and type
        cur_old["ADDR"] = cur_new["ADDR"]
        cur_old["STARTBIT"] = cur_new["STARTBIT"]
        cur_old["WIDTH"] = cur_new["WIDTH"]
        cur_old["TYPE"] = cur_new["TYPE"]
        items_updated += 1
        tmp_items.append(cur_old)

    # sort fuses by bit position
    old_items = sorted(tmp_items, key=lambda elem: ((elem["ADDR"] * BYTE_BITS) + elem["STARTBIT"]))
    for cur_old in old_items:
        if (cur_old['ADDR'] == 0) and (cur_old['WIDTH'] == 0):
            # skip this item, as it lacks data
            continue
        if (cur_old['SKIP']):
            # this item has been flagged for skipping since its value isn't changed from default
            continue
        addr_fmt = '{:05x}'.format(cur_old['ADDR'])
        num_zeroes = 1
        if (cur_old['WIDTH'] > 4):
            num_zeroes = (int(cur_old['WIDTH'] / 4))
        # the value is the only thing we keep from the old patch file
        cur_val = cur_old['VALUE']
        #val_fmt = f"{cur_val:#0{num_zeroes}x}"
        zeroes_fmt = f":0{num_zeroes}x"
        zeroes_fmt = '{' + zeroes_fmt + '}'
        val_fmt = zeroes_fmt.format(cur_val)
        out_str = f"{addr_fmt} {cur_old['STARTBIT']} {cur_old['WIDTH']} {val_fmt} # {cur_old['NAME']} {cur_old['TYPE']}"
        outf.write(f"{out_str}\n")

    outf.close()
    print(f"Fuses updated: {items_updated} out of {num_old_items}")
    print(f"Fuses not updated (missing from default values file): {items_not_found} out of {num_old_items}")
    print(f"Fuses skipped because their values are the same as default: {items_skipped}")
    return True

def parse_cfg_out(source_filename):
    items = []

    # read in file
    inf = None
    try:
        inf = open(source_filename, "r")
    except:
        print(f"ERROR: Unable to open input file {source_filename}")
        return items
    lines = inf.readlines()
    inf.close()

    # choose a prefex depending on filename
    basename = os.path.basename(source_filename)
    prefix = "punit_punit_fw_fuses_"
    if (basename.lower().find("dcode") != -1):
        prefix = "dmu_fuse_fw_fuses_"

    STATE_LOCATING_CFG_FUSE = 0
    STATE_IN_CFG_FUSE = 1
    STATE_END_OF_CFG_FUSE = 2

    # locate cfg.fuse section
    cur_state = STATE_LOCATING_CFG_FUSE
    for cur_line in lines:
        if (cur_state == STATE_LOCATING_CFG_FUSE):
            if (cur_line.find("== cfg.fuse ==") != -1):
                cur_state = STATE_IN_CFG_FUSE
            # always continue
            continue
        elif (cur_state == STATE_END_OF_CFG_FUSE):
            break

        # if we're here, we're in STATE_IN_CFG_FUSE
        if (cur_line.find("===============") != -1):
            cur_state = STATE_END_OF_CFG_FUSE
            continue

        # if we're here, it's a parse-able line
        stripped = cur_line.strip()
        line_parts = stripped.split(":", 2)
        # parse each line into ["NAME"] and ["VALUE"] items.
        fuse_name = f"{prefix}{line_parts[0].upper()}"
        new_item = {
            "NAME" : fuse_name,
            "VALUE" : int(line_parts[1].strip())
        }
        items.append(new_item)

    # note: cfg_out values are all lower-case
    # note: need to identify prefixes to use (maybe use different prefix based on filename?)
    return items

def parse_default_ovrd(source_filename):
    items = []

    # read in file
    inf = None
    try:
        inf = open(source_filename, "r")
    except:
        print(f"ERROR: Unable to open input file {source_filename}")
        return items
    lines = inf.readlines()
    inf.close()

    for cur_line in lines:
        stripped = cur_line.strip()
        if len(stripped) == 0:
            continue

        if (stripped[0] == '#'):
            # discard commented lines
            continue

        # replace / with _
        #stripped = stripped.replace('/', '_')

        line_parts = stripped.split("=", 2)
        # parse each line into ["NAME"] and ["VALUE"] items.
        # fuse_name = f"{line_parts[0]}"
        fuse_name = fixupFuseName(line_parts[0].strip())
        new_item = {
            "NAME" : fuse_name,
            # "VALUE" : int(line_parts[1].strip(), 16)
            "VALUE" : process_value(line_parts[1].strip())
        }
        items.append(new_item)

    return items


def dump_blob(blob_file, default_values, target_file, start_address):
    success = False

    # dump blob mode
    if (len(target_file) == 0):
        print("ERROR: Please use the --target argument to pass the name of the output file.")
        return success
    elif (len(default_values) == 0):
        print("ERROR: Please use the --default_values argument to pass the path of an existing default_values file.")
        return success
    elif (len(start_address) == 0):
        print("ERROR: Please specify a --start_address for dumping contents.")
        return success

    try:
        outf = open(target_file, "w")
    except:
        print(f"ERROR: Unable to create target file {target_file}")
        return success

    try:
        inf = open(blob_file, "r")
    except:
        print("ERROR: Unable to open input file (",
              name_file,
              ").")
        outf.close()  # close opened file
        return success

    # load default_values file
    def_values = load_patch_items(default_values)
    if (len(def_values) == 0):
        print("ERROR: No default values found.")
        return success

    lines = inf.readlines()
    for cur_line in lines:
        # convert start address to numerical value
        cur_address = int(start_address, 16)
        # reject first 8 characters, as that's just the header
        new_line = cur_line[8:]
        new_line = new_line.strip()
        byte_num = 0
        # read 2 characters at a time into int values for processing
        for i in range(0, len(new_line), 2):
            cur_byte = int(new_line[i:i+2], 16)
            fusematches = ""
            for cur_val in def_values:
                if (cur_val['ADDR'] != cur_address):
                    # only look for fuses with same address
                    continue
                # if here, the address matches; add it to the string
                fusematches += f" {cur_val['NAME']} ({cur_val['STARTBIT']} {cur_val['WIDTH']}),"
            if (len(fusematches) == 0):
                # didn't find any exact matches. look for the most recent fuse that's less than
                # the current address
                last_item = def_values[0]
                for cur_val in def_values:
                    if (cur_val['ADDR'] > cur_address):
                        fusematches += f" {last_item['NAME']} (0x{last_item['ADDR']:03x} {last_item['STARTBIT']} {last_item['WIDTH']})"
                        break
                    # if we're here, we're still searching
                    last_item = cur_val
            # build output line: byte num, address, value, fuses
            out_line = f"{byte_num:03d}: a:0x{cur_address:03x} v:0x{cur_byte:02x},{fusematches}"
            cur_address += 1
            byte_num += 1
            outf.write(f"{out_line}\n")

    inf.close()
    outf.close()
    success = True
    return success

def extract_blob_data(blob_string):
    extracted_chunks = []
    PROCESS_HEADER = 1
    PROCESS_BYTES = 2
    HEADER_SIZE = 4
    BYTES_IN_DW = 4
    DWORD_FIELD = 3
    blob_bytes = bytes.fromhex(blob_string)
    num_bytes = len(blob_bytes)
    chunk_count = 0

    print(f"Blob: {blob_string}")

    cur_mode = PROCESS_HEADER
    cur_pos = 0
    cur_header = None
    cur_section = None
    bytes_to_extract = 0
    while cur_pos < num_bytes:
        if cur_mode == PROCESS_HEADER:
            cur_header = blob_bytes[cur_pos:cur_pos + HEADER_SIZE]
            print(f"Header: {cur_header.hex()}")
            dwords = cur_header[DWORD_FIELD]
            bytes_to_extract = BYTES_IN_DW * dwords
            print(f"- bytes_to_extract: {bytes_to_extract}")
            cur_pos += HEADER_SIZE
            cur_mode = PROCESS_BYTES
        if cur_mode == PROCESS_BYTES:
            cur_section = blob_bytes[cur_pos:cur_pos + bytes_to_extract]
            extracted_bytes = cur_section.hex()
            cur_pos += bytes_to_extract
            cur_mode = PROCESS_HEADER
            print(f"- chunk {chunk_count}: {extracted_bytes}")
            chunk_count += 1
            extracted_chunks.append(extracted_bytes)

    return extracted_chunks

def load_text_blob(blob_file):
    blobstring = ""

    try:
        inf = open(blob_file, "r")
    except:
        print(f"ERROR: Unable to open file {blob_file}")
        return blobstring

    lines = inf.readlines()
    inf.close()
    blobstring = lines[0].strip()

    return extract_blob_data(blobstring)

def load_int_blob(blob_file):
    blobstring = ""

    try:
        inf = open(blob_file, "r")
    except:
        print(f"ERROR: Unable to open file {blob_file}")
        return blobstring

    lines = inf.readlines()
    inf.close()

    for cur_line in lines:
        cur_int = int(cur_line)
        cur_byte = f'{cur_int:02x}'
        blobstring += cur_byte

    return extract_blob_data(blobstring)


def filter_values(default_values, prefix, base_address, data_size):
    filtered_values = []
    MAX_BITS = data_size * BYTE_BITS

    # default_values does not contain group number or item type.
    # (it will either be all fuses or all softstraps)
    # must filter by base address instead of group or type
    total_bits = 0
    for cur_value in default_values:
        if cur_value['NAME'].startswith(prefix) != True:
            # skip values without prefix
            continue
        if cur_value['ADDR'] < base_address:
            # skip fuses with lower base address values than requested
            continue
        # if here, add fuse to the list
        if total_bits < MAX_BITS:
            filtered_values.append(cur_value)
            total_bits += cur_value['WIDTH']
            print(f"total_bits {total_bits} of {MAX_BITS}")
        else:
            # reached maximum data size for this chunk
            break

    return filtered_values


def filter_dlut(dlut_list, instance_name, group, type_softstrap):
    filtered_list = []

    type_string = DIRECT_FUSE
    if type_softstrap:
        type_string = SOFT_STRAP

    for cur_entry in dlut_list:
        if cur_entry['INSTANCE'] != instance_name:
            continue
        if cur_entry['GROUP'] != group:
            continue
        if cur_entry['TYPE'] != type_string:
            continue

        # if we're here, it's valid
        filtered_list.append(cur_entry)

    return filtered_list


def import_blob(blob_strings, default_values, dlut_list, target_file, prefix, group, type_softstrap):
    success = False

    # check requirements
    if (len(target_file) == 0):
        print("ERROR: Please use the --target_file argument to specify an output file.")
        return success
    elif (len(default_values) == 0):
        print("ERROR: Please use the --default_values argument to pass the path of an existing dafault_values file.")
        return success
    elif (len(prefix) == 0):
        print("ERROR: Please use the --prefix argument to specify an IP name or prefix to use (punit_punit_fw_fuses or dmu_fuse_fw_fuses, etc).")
        return success
    elif (group == INVALID_GROUP):
        print("ERROR: Please use the --group argument to specify which fuse or softstrap group to decode.")

    # load default_values file
    def_values = load_patch_items(default_values)
    if (len(def_values) == 0):
        print("ERROR: No default values found.")
        return success

    # get subset of dlut entries matching prefix, group, and type
    type_string = DIRECT_FUSE
    if type_softstrap:
        type_string = SOFT_STRAP
    dlut_chunks = filter_dlut(dlut_list, prefix, group, type_softstrap)
    if (len(dlut_chunks) == 0):
        print(f"ERROR: No {type_string} DLUT entries found for {prefix} at group {group}")
        return success

    # start output file
    outf = None
    try:
        outf = open(target_file, "w")
    except:
        print(f"ERROR: Unable to create target file {target_file}")
        return success
    outf.write("# RamAddr (hex) StartBit (dec) Width (dec) Value (hex)\n")

    # set up constants
    chunk_count = 0
    for blob_string in blob_strings:
        # get starting address for this group
        base_address = dlut_chunks[chunk_count]['RAM_ADDR']
        print(f"Chunk {chunk_count} base_address: 0x{base_address:04x}, size: {dlut_chunks[chunk_count]['SIZE']}")

        # get a subset of matching fuse/softstrap items
        group_rows = filter_values(def_values, prefix, base_address, dlut_chunks[chunk_count]['SIZE'])
        if (len(group_rows) == 0):
            print(f"ERROR: No {type_string} default entries found for {prefix} at or above 0x{base_address:04x}")
            return success

        # get start address for this group/type/ip
        address_diff = base_address
        blob_bytes = bytes.fromhex(blob_string)
        blob_length = len(blob_bytes)

        #TODO why are the fuses 1 byte different from expected?

        for cur_value in group_rows:
            # print(f"addr: 0x{cur_value['ADDR']:04x} start: {cur_value['STARTBIT']} bits: {cur_value['WIDTH']} - {cur_value['NAME']}")
            byte_position = (cur_value['ADDR'] - address_diff)
            bit_position = (byte_position * BYTE_BITS) + (cur_value['STARTBIT'])
            end_position = bit_position + cur_value['WIDTH']
            startbit = cur_value['STARTBIT']
            numbits = cur_value['WIDTH']
            bytes_cnt = int(math.ceil(float(numbits + startbit) / BYTE_BITS))
            bit_string = ""
            total_bits = (bytes_cnt * BYTE_BITS)
            end_bit = startbit + numbits
            for i in range(total_bits):
                if (i >= startbit) and (i < end_bit):
                    bit_string += "1"
                else:
                    bit_string += "0"
            bit_string = bit_string[::-1]
            mask = int(bit_string, 2)
            print(f"Fuse: {cur_value['NAME']}")
            print(f"- length: {blob_length} bp: {byte_position} addr: 0x{byte_position + address_diff:x} cnt: {bytes_cnt} start: {startbit} numbits: {numbits}")
            tmp_bytes = blob_bytes[byte_position:byte_position + bytes_cnt]
            tmp_int = int.from_bytes(tmp_bytes, 'little')
            value_int = (tmp_int & mask) >> startbit
            print(f"- exlen: {len(tmp_bytes)} bytes: {tmp_bytes.hex()} value: 0x{value_int:x}")
            print(f"- {mask:b}")

            if (cur_value['VALUE'] != value_int):
                # record that this is a new value in output and write it to output file
                cur_value['TYPE'] = f"(0x{cur_value['VALUE']:x})"
                cur_value['VALUE'] = value_int
            else:
                # just standardize on type field for unchanged values
                cur_value['TYPE'] = "(fuse)"
            addr_fmt = '{:05x}'.format(cur_value['ADDR'])
            num_zeroes = 1
            if (cur_value['WIDTH'] > 4):
                num_zeroes = (int(cur_value['WIDTH'] / 4))
            cur_val = cur_value['VALUE']
            zeroes_fmt = f":0{num_zeroes}x"
            zeroes_fmt = '{' + zeroes_fmt + '}'
            val_fmt = zeroes_fmt.format(cur_val)
            out_str = f"{addr_fmt} {cur_value['STARTBIT']} {cur_value['WIDTH']} {val_fmt} # {cur_value['NAME']} {cur_value['TYPE']}\n"
            outf.write(out_str)
        # proceed to next chunk
        chunk_count += 1

    # if here we're successful
    success = True
    return success

def find_by_name(fuse_name, fuse_items):
    for cur_item in fuse_items:
        if (cur_item['NAME'] == fuse_name):
            return cur_item

    # if we're here, we didn't find a match
    return None

def save_patch_items(target_file, fuse_items):
    # start output file
    outf = None
    try:
        outf = open(target_file, "w")
    except:
        print(f"ERROR: Unable to create target file {target_file}")
        return False

    # sort the list before writing
    fuse_items = sorted(fuse_items, key=lambda elem: ((elem["ADDR"] * BYTE_BITS) + elem["STARTBIT"]))

    outf.write("# RamAddr (hex) StartBit (dec) Width (dec) Value (hex)\n")
    for cur_item in fuse_items:
        addr_fmt = '{:05x}'.format(cur_item['ADDR'])
        num_zeroes = 1
        if (cur_item['WIDTH'] > 4):
            num_zeroes = (int(cur_item['WIDTH'] / 4))
        cur_val = cur_item['VALUE']
        zeroes_fmt = f":0{num_zeroes}x"
        zeroes_fmt = '{' + zeroes_fmt + '}'
        val_fmt = zeroes_fmt.format(cur_val)
        # prevent nested parens
        type_fmt = cur_item['TYPE'].replace('(', '').replace(')', '')
        out_str = f"{addr_fmt} {cur_item['STARTBIT']} {cur_item['WIDTH']} {val_fmt} # {cur_item['NAME']} ({type_fmt})"
        outf.write(f"{out_str}\n")

    outf.close()
    print(f"Saved output to {target_file}.")
    return True

def load_xml_items(filepath, prefix = ""):
    items = []
    prefix_filter = False
    if (len(prefix) > 0):
        prefix_filter = True

    # get xml tree
    try:
        input_tree = etree.parse(open(filepath, "rb"))
    except FileNotFoundError:
        print("ERROR: Fusegen file not found (", source_xml,
            ") Please specify a valid fusegen XML file as input.")
        return items

    root = input_tree.getroot()
    assert root.tag == "FuseGen"
    for el in root:
        if el.tag == "DirectFuses":
            for fuse in el:
                # applies only to fuses, not straps
                if (fuse.tag != "Fuse"): continue

                tmpname = fuse.find("name").text.strip()
                name = fixupFuseName(tmpname)

                if (prefix_filter):
                    if (not name.startswith(prefix)):
                        # skip this fuse; doesn't match filter
                        continue

                fuse_entry = {
                    "NAME" : name,
                    "ADDR" : process_value(fuse.find("RamAddr").text),
                    "CATEGORY" : fuse.find("Category").text,
                    "WIDTH" : process_value(fuse.find("FUSE_WIDTH").text),
                    "RAMADDR" : process_value(fuse.find("RamAddr").text),
                    "STARTBIT" : process_value(fuse.find("StartBit").text),
                    "WIDTH" : process_value(fuse.find("FUSE_WIDTH").text),
                    "RCVRADDR" : process_value(fuse.find("RcvrAddr").text),
                    "VALUE" : process_value(fuse.find("FuseDefaultValue").text),
                    "TYPE" : fuse.find("Group").text
                }
                items.append(fuse_entry)

    return items

# TODO: Option to pass patch file for updated values?
def compare_patch(old_patch_file, new_patch_file, load_fusegen, prefix = ""):
    if (len(old_patch_file) == 0):
        print("ERROR: Please use --old_patch argument to pass path of an old patch file.")
        return False
    if (len(new_patch_file) == 0):
        print("ERROR: Please use --new_patch argument to pass path of a new patch file.")
        return False
    old_items = []
    new_items = []
    if not load_fusegen:
        old_items = load_patch_items(args.old_patch, prefix)
        new_items = load_patch_items(args.new_patch, prefix)
    else:
        old_items = load_xml_items(args.old_patch, prefix)
        new_items = load_xml_items(args.new_patch, prefix)
    if (len(old_items) == 0):
        print(f"ERROR: No items loaded from {args.old_patch}")
        return False
    if (len(new_items) == 0):
        print(f"ERROR: No items loaded from {args.new_patch}")
        return False

    only_old = []  # items only in old patch
    only_new = []  # items only in new patch
    same_values = []  # in both, same value
    diff_values = []  # in both, different values - should be a tuple
    diff_templates = [] # in both, different receiver address, size, startbit, etc.

    # search for old items in new patch
    for cur_old in old_items:
        # mutually exclusive comparisons
        found_new = find_by_name(cur_old['NAME'], new_items)
        if (found_new is None):
            only_old.append(cur_old)
        elif (cur_old['VALUE'] == found_new['VALUE']):
            same_values.append(cur_old)
        else:
            # different values
            diff_item = {
                'OLD' : cur_old,
                'NEW' : found_new
            }
            diff_values.append(diff_item)

        if (load_fusegen and (not found_new is None)):
            # xml mode and there are two items
            add_diff = False
            if cur_old["ADDR"] != found_new["ADDR"]:
                add_diff = True
            if cur_old["WIDTH"] != found_new["WIDTH"]:
                add_diff = True
            if cur_old["STARTBIT"] != found_new["STARTBIT"]:
                add_diff = True
            if cur_old["RCVRADDR"] != found_new["RCVRADDR"]:
                add_diff = True
            if (add_diff):
                diff_item = {
                    'OLD' : cur_old,
                    'NEW' : found_new
                }
                diff_templates.append(diff_item)

    # search for items only in new patch
    for cur_new in new_items:
        found_old = find_by_name(cur_new['NAME'], old_items)
        if (found_old is None):
            only_new.append(cur_new)

    print(f"Items only in old patch ({len(only_old)}):")
    for cur_item in only_old:
        print(f"\t{cur_item['NAME']}, val: 0x{cur_item['VALUE']:x}")
    print("\n")
    print(f"Items only in new patch ({len(only_new)}):")
    for cur_item in only_new:
        print(f"\t{cur_item['NAME']}, val: 0x{cur_item['VALUE']:x}")
    print("\n")
    print(f"Items with same values in both ({len(same_values)}):")
    for cur_item in same_values:
        print(f"\t{cur_item['NAME']}, val: 0x{cur_item['VALUE']:x}")
    print("\n")
    print(f"Items with different values ({len(diff_values)}):")
    for cur_item in diff_values:
        print(f"\t{cur_item['OLD']['NAME']}, old: 0x{cur_item['OLD']['VALUE']:x}, new: 0x{cur_item['NEW']['VALUE']:x}")
    print("\n")
    print(f"Items with different templates ({len(diff_templates)}):")
    for cur_item in diff_templates:
        diffstring = ""
        if cur_item['OLD']['ADDR'] != cur_item['NEW']['ADDR']:
            diffstring += f"Addr: 0x{cur_item['OLD']['ADDR']:x}->0x{cur_item['NEW']['ADDR']:x} "
        if cur_item['OLD']['RCVRADDR'] != cur_item['NEW']['RCVRADDR']:
            diffstring += f"RcvrAddr: 0x{cur_item['OLD']['RCVRADDR']:x}->0x{cur_item['NEW']['RCVRADDR']:x} "
        if cur_item['OLD']['STARTBIT'] != cur_item['NEW']['STARTBIT']:
            diffstring += f"StartBit: {cur_item['OLD']['STARTBIT']}->{cur_item['NEW']['STARTBIT']} "
        if cur_item['OLD']['WIDTH'] != cur_item['NEW']['WIDTH']:
            diffstring += f"NumBits: {cur_item['OLD']['WIDTH']}->{cur_item['NEW']['WIDTH']} "

        print(f"\t{cur_item['OLD']['NAME']}, {diffstring}")
    print("\n")

    return True


def get_instance_by_portid(ip_info, portid_full):
    instance = ""
    foundit = False
    for entry in ip_info:
        if entry["PORTID_FULL"] == portid_full:
            foundit = True
            instance = entry["INSTANCE"]
            break

    if not foundit:
        print(f"WARNING: No instance found matching portid 0x{portid_full:04x}")

    return instance


def get_dlut(tree, ip_info):
    dlut_entries = []
    root = tree.getroot()
    assert root.tag == "FuseGen"
    dlut = None
    for el in root:
        if el.tag == "DistributionLUT":
            dlut = el
            break

    if (dlut is None):
        print("ERROR: No DistributionLUT element found in fusegen XML!")
        return dlut_entries

    for entry in dlut:
        sbep = process_value(entry.attrib['IOSFSBEP'])
        portid_hi = process_value(entry.attrib['IOSFSBHierarchicalPortID'])
        portid_lo = process_value(entry.attrib['IOSFSBPortID'])
        group = process_value(entry.attrib['GroupNumber'])
        entry_type = entry.attrib['Group']
        count = process_value(entry.attrib['Count'])
        rcvr_addr = process_value(entry.attrib['RcvrAddr'])
        bar = entry.attrib['BAR']
        ram_addr = process_value(entry.attrib['RamAddr'])
        size = process_value(entry.attrib['DataSize'])
        lockout_position = process_value(entry.attrib['LockoutIDBitPosition'])
        lockout_address = process_value(entry.attrib['LockoutIDRowAddress'])
        portid_full = combine_portid(portid_hi, portid_lo)
        instance = get_instance_by_portid(ip_info, portid_full)
        # sort key:
        # 16 bits - portid (<<24)
        # 4 bits - sbep (<<20)
        # 4 bits - type (<<16)
        # 8 bits - group (<<8)
        # 8 bits - count
        typebit = 1
        if (entry_type == DIRECT_FUSE):
            typebit = 0
        sort_key = (portid_full << 24) | (sbep << 20) | (typebit << 16) | (group << 8) | (count)
        # print(f"sort_key: 0x{sort_key:x}")
        new_entry = {
            "INSTANCE" : instance,
            "PORTID_FULL" : portid_full,
            "HIPORTID" : portid_hi,
            "LOPORTID" : portid_lo,
            "SBEP" : sbep,
            "GROUP" : group,
            "TYPE" : entry_type,
            "COUNT" : count,
            "RAM_ADDR" : ram_addr,
            "RCVR_ADDR" : rcvr_addr,
            "BAR" : bar,
            "SIZE" : size,
            "LOCKOUTPOS" : lockout_position,
            "LOCKOUTADDR" : lockout_address,
            "SORTKEY" : sort_key
        }
        dlut_entries.append(new_entry)

    dlut_entries = sorted(dlut_entries, key=lambda elem: (elem["SORTKEY"]))

    return dlut_entries


def dump_dlut(dlut_list, target_file):
    success = False
    try:
        outf = open(target_file, "w")
    except:
        print(f"ERROR: Unable to create target file {target_file}")
        return success

    line = f'"INSTANCE","PORTID_FULL","HIPORTID","LOPORTID","SBEP","GROUP","TYPE","COUNT","RAM_ADDR","RCVR_ADDR","BAR","SIZE","LOCKOUTPOS","LOCKOUTADDR","SORTKEY"\n'
    outf.write(line)
    for entry in dlut_list:
        line = f'"{entry["INSTANCE"]}",0x{entry["PORTID_FULL"]:04x},0x{entry["HIPORTID"]:02x},0x{entry["LOPORTID"]:02x},{entry["SBEP"]},{entry["GROUP"]},"{entry["TYPE"]}",{entry["COUNT"]},0x{entry["RAM_ADDR"]:02x},0x{entry["RCVR_ADDR"]:02x},"{entry["BAR"]}",{entry["SIZE"]},0x{entry["LOCKOUTPOS"]:02x},0x{entry["LOCKOUTADDR"]:02x},0x{entry["SORTKEY"]:x}\n'
        outf.write(line)

    outf.close()
    return success


def combine_portid(portid_hi, portid_lo):
    BITS_IN_BYTE = 8
    combined_id = (portid_hi << BITS_IN_BYTE)
    combined_id = (combined_id | portid_lo)
    return combined_id


def get_ip_info(tree):
    info_entries = []
    root = tree.getroot()
    assert root.tag == "FuseGen"
    dlut = None
    for el in root:
        if el.tag == "SOC":
            dlut = el
            break

    if (dlut is None):
        print("ERROR: No SOC element found in fusegen XML!")
        return info_entries

    for entry in dlut:
        ip = entry.attrib['IP']
        instance = entry.attrib['Instance']
        sbep = process_value(entry.attrib['IOSFSBEP'])
        portid_hi = process_value(entry.attrib['IOSFSBHierarchicalPortID'])
        portid_lo = process_value(entry.attrib['IOSFSBPortID'])
        pull_trigger = entry.attrib['PullTrigger']
        # note: The difference between IP and INSTANCE fields is that INSTANCE fields are always unique
        #       while IP value can be duplicated.
        new_entry = {
            "IP" : ip,
            "INSTANCE" : instance,
            "HIPORTID" : portid_hi,
            "LOPORTID" : portid_lo,
            "PORTID_FULL" : combine_portid(portid_hi, portid_lo),
            "SBEP" : sbep,
            "PULL_TRIGGER" : pull_trigger
        }
        info_entries.append(new_entry)

    return info_entries


def dump_ip_info(info_list, target_file):
    success = False
    try:
        outf = open(target_file, "w")
    except:
        print(f"ERROR: Unable to create target file {target_file}")
        return success

    line = f'"IP","INSTANCE","HIPORTID","LOPORTID","PORTID_FULL","SBEP","PULL_TRIGGER"\n'
    outf.write(line)
    for entry in info_list:
        line = f'"{entry["IP"]}","{entry["INSTANCE"]}",0x{entry["HIPORTID"]:02x},0x{entry["LOPORTID"]:02x},0x{entry["PORTID_FULL"]:04x},{entry["SBEP"]},"{entry["PULL_TRIGGER"]}"\n'
        outf.write(line)

    outf.close()
    return success


def get_stats(dlut_list):
    stats_entries = {}

    class InstanceTemplate:
        def __init__(self, instance, portid_full, sbep):
            self.instance = instance
            self.portid_full = portid_full
            self.sbep = sbep
            self.fuse_groups = {}
            self.strap_groups = {}

    class GroupTemplate:
        def __init__(self, group):
            self.group = 0
            self.size_total = 0
            self.rows = 0
            self.base_ram_addr = 0xFFFFFFFF  # start with max address value
            self.base_rcvr_addr = 0xFFFFFFFF  # start with max address value

    #debug_max = 34
    #debug_count = 0

    for cur_entry in dlut_list:
    #     # DEBUG ONLY!
    #     debug_count += 1
    #     if debug_count > debug_max:
    #         return stats_entries

        # get existing entry if exists; otherwise create and add new
        cur_instance = None
        try:
            cur_instance = stats_entries[cur_entry["INSTANCE"]]
            # print(f"Got existing instance {cur_entry["INSTANCE"]}")
        except KeyError:
            cur_instance = InstanceTemplate(cur_entry["INSTANCE"], cur_entry["PORTID_FULL"], cur_entry["SBEP"])
            stats_entries[cur_entry["INSTANCE"]] = cur_instance
            # print(f"Created new instance {cur_entry["INSTANCE"]}")

        # ensure we use the right group
        is_fuse = True
        if cur_entry["TYPE"] == SOFT_STRAP:
            is_fuse = False

        cur_group = None
        if is_fuse:
            try:
                cur_group = cur_instance.fuse_groups[cur_entry["GROUP"]]
                # print(f"Got existing fuse group {cur_entry["GROUP"]}")
            except KeyError:
                cur_group = GroupTemplate(cur_entry["GROUP"])
                cur_instance.fuse_groups[cur_entry["GROUP"]] = cur_group
                # print(f"Created new fuse group {cur_entry["GROUP"]}")
        else:
            try:
                cur_group = cur_instance.strap_groups[cur_entry["GROUP"]]
                # print(f"Got existing strap group {cur_entry["GROUP"]}")
            except KeyError:
                cur_group = GroupTemplate(cur_entry["GROUP"])
                cur_instance.strap_groups[cur_entry["GROUP"]] = cur_group
                # print(f"Created new strap group {cur_entry["GROUP"]}")

        # compute running stats
        cur_group.size_total += cur_entry["SIZE"]
        cur_group.rows += 1
        if (cur_entry["RAM_ADDR"] < cur_group.base_ram_addr):
            cur_group.base_ram_addr = cur_entry["RAM_ADDR"]
        if (cur_entry["RCVR_ADDR"] < cur_group.base_rcvr_addr):
            cur_group.base_rcvr_addr = cur_entry["RCVR_ADDR"]

    return stats_entries


def print_stats(stats_entries):
    if len(stats_entries) == 0:
        print("ERROR: No stats to print!")
        return False

    for key in stats_entries:
        cur_entry = stats_entries[key]
        print(f'{cur_entry.instance} (SBID 0x{cur_entry.portid_full:04x}, SBEP {cur_entry.sbep})')
        for group in cur_entry.fuse_groups:
            cg = cur_entry.fuse_groups[group]
            print(f' - Fuse group {group}, size: {cg.size_total}, rows: {cg.rows}, base RAM addr: 0x{cg.base_ram_addr:04x}, base RCVR addr: 0x{cg.base_rcvr_addr:04x}')
        for group in cur_entry.strap_groups:
            cg = cur_entry.strap_groups[group]
            print(f' - Strap group {group}, size: {cg.size_total}, rows: {cg.rows}, base RAM addr: 0x{cg.base_ram_addr:04x}, base RCVR addr: 0x{cg.base_rcvr_addr:04x}')

    return True

def merge_values(default_values, config_out_items, target, changes_only):
    if (len(default_values) == 0):
        print("ERROR: No --default_values file specified!")
        return False
    if (len(config_out_items) == 0):
        print("ERROR: No items found in --fuse_default_ovrd file!")
        return False
    if (len(target) == 0):
        print("ERROR: No --target file specified!")
        return False

    items_not_found = [] # names only
    items_updated = [] # dicts of items that had new values
    items_skipped = 0

    default_items = load_patch_items(default_values)
    if (len(default_items) == 0):
        print(f"ERROR: {default_values} contained no entries!")
        return False

    for config_item in config_out_items:
        matching = next((default_item for default_item in default_items if default_item['NAME'] == config_item['NAME']), None)
        if matching is None:
            items_not_found.append(config_item['NAME'])
        else:
            if matching['VALUE'] != config_item['VALUE']:
                matching['TYPE'] = f'{matching['VALUE']:x}'
                matching['VALUE'] = config_item['VALUE']
                items_updated.append(matching)
            else:
                items_skipped += 1

    if (changes_only):
        if (save_patch_items(target, items_updated) == False):
            print(f"ERROR: Failed to write changed items to file {target}!")
            return False
    else:
        if (save_patch_items(target, default_items) == False):
            print(f"ERROR: Failed to write updated defaults list to file {target}!")
            return False

    print(f"Items from override file not found in default_values ({len(items_not_found)}):")
    for cur_item in items_not_found:
        print(f" - {cur_item}")
    print(f"\nOverride items with updated values ({len(items_updated)}):")
    for cur_item in items_updated:
        print(f" - {cur_item['NAME']} = {cur_item['VALUE']}")
    print(f"\nItems with unchanged values: {items_skipped}")
    return True

def merge_patches(old_patch, new_patch, locked_fuses, target):
    unchanged_values = 0
    changed_values = 0
    new_fuses = 0
    skipped_locked = 0

    # load old patch
    old_items = load_patch_items(old_patch)
    if (len(old_items) == 0):
        print(f"ERROR: No items found in old patch {old_patch}")
        return False

    # load new patch
    new_items = load_patch_items(new_patch)
    if (len(new_items) == 0):
        print(f"ERROR: No items found in new patch {new_patch}")
        return False

    # load locked fuses
    keep_locked = False
    locked_items = []
    if (len(locked_fuses) == 0):
        print("INFO: No locked_fuses file specified. Using all new values when found...")
    else:
        locked_items = load_fuse_names(locked_fuses)
        if (len(locked_items) == 0):
            print(f"WARNING: No items found in locked_fuses file {locked_fuses}. Ignoring...")
        else:
            keep_locked = True

    # for each old_item:
    # - copy all items to new list
    merged_list = old_items

    # for each new_item:
    for cur_item in new_items:
        # - check if in locked_items. skip if it is.
        if (keep_locked and cur_item['NAME'] in locked_items):
            print(f"INFO: {cur_item['NAME']} is a locked item.")
            skipped_locked += 1
            continue

        # - check if already in new list.
        # -- if found in new list, update item (if we're here we've already passed locked_items check)
        found_item = find_by_name(cur_item['NAME'], merged_list)
        if found_item is None:
            # no match found; just add this item
            merged_list.append(cur_item)
            new_fuses += 1
        else:
            if found_item['VALUE'] != cur_item['VALUE']:
                # new value; update type and value fields
                found_item['TYPE'] = str(found_item['VALUE'])
                found_item['VALUE'] = cur_item['VALUE']
                changed_values += 1
            else:
                unchanged_values += 1

    if (False == save_patch_items(target, merged_list)):
        print(f"ERROR: Failed to save file {target}")
        return False

    print(f"Matching items that were unchanged: {unchanged_values}")
    print(f"Matching items with new values: {changed_values}")
    print(f"Newly-added items: {new_fuses}")
    print(f"Items skipped because they are locked: {skipped_locked}")
    print(f"Total items returned: {len(merged_list)}")

    return True

if __name__ == "__main__":
    args = parse_args()

    source_xml = args.source
    target_file = args.target
    input_tree = None
    name_file = args.name_file
    success = False
    need_fusegen = True

    # some features don't require fusegen:
    if (args.reconcile_patch):
        need_fusegen = False
    if (args.update_patch):
        need_fusegen = False
    if (len(args.dump_blob) > 0):
        need_fusegen = False
    if (args.prune_patch):
        need_fusegen = False
    if (args.compare_patch):
        need_fusegen = False
    if (args.compare_xml):
        need_fusegen = False
    if (args.merge_values):
        need_fusegen = False
    if (args.prune_patch):
        need_fusegen = False
    if (args.merge_patches):
        need_fusegen = False

    ip_info = []
    dlut_list = []
    if (need_fusegen):
        # get xml tree from passed file
        try:
            input_tree = etree.parse(open(source_xml, "rb"))
        except FileNotFoundError:
            print("ERROR: Fusegen file not found (", source_xml,
                ") Please specify a valid fusegen XML file as input.")
            quit()

        # get list of fusegen IPs
        ip_info = get_ip_info(input_tree)
        if (len(ip_info) == 0):
            print(f"ERROR: No SOC Instances read from {args.target}")
            quit()

        # get dlut
        dlut_list = get_dlut(input_tree, ip_info)
        if (len(dlut_list) == 0):
            print(f"ERROR: No DLUT read from {args.target}")
            quit()

    config_out_items = []
    if len(args.config_out) > 0:
        print(f"args.config_out: {args.config_out}")
        config_out_items = parse_cfg_out(args.config_out)
    elif len(args.fuse_default_ovrd) > 0:
        print(f"args.fuse_default_ovrd: {args.fuse_default_ovrd}")
        config_out_items = parse_default_ovrd(args.fuse_default_ovrd)


    if (args.high_groups):
        # high groups mode

        # parse for fuses/straps that fall outside of the old standard
        high_elements = parse_for_high_groups(input_tree)

        # write a csv that includes the following:
        # category, SB id, fuse name, fuse address, type, group
        success = write_groups_csv_file(target_file, high_elements)
    elif (args.make_patch):
        # make patch mode

        # make sure a name file is specified
        if (len(name_file) == 0):
            print("ERROR: Please use the --name_file argument to pass a file with fuse names to include in patch.")
            success = False
        else:
            success = make_patch(input_tree, target_file, name_file)
    elif (args.pcode_stats):
        low_fuse, high_fuse = get_pcode_stats(input_tree)
        print("Low PUNIT fuse:")
        print(low_fuse)
        print("High PUNIT fuse:")
        print(high_fuse)
    elif (args.dcode_stats):
        low_fuse, high_fuse = get_dcode_stats(input_tree)
        print("Low DMU fuse:")
        print(low_fuse)
        print("High DMU fuse:")
        print(high_fuse)
    elif (args.compare_patch):
        # 3rd argument is for patch files vs fusegen XML
        success = compare_patch(args.old_patch, args.new_patch, False)
        quit()
    elif (args.compare_xml):
        # 3rd argument is for patch files vs fusegen XML
        success = compare_patch(args.old_patch, args.new_patch, True, args.prefix)
        quit()
    elif (args.merge_values):
        success == merge_values(args.default_values, config_out_items, args.target, args.changes_only)
        quit()
    elif (args.merge_patches):
        success == merge_patches(args.old_patch, args.new_patch, args.locked_fuses, args.target)
        quit()
    elif (args.prune_patch):
        if (len(args.old_patch) == 0):
            print("ERROR: Please use the --old_patch argument to pass the path of an existing patch file.")
            success = False
            quit()
        elif (len(args.default_values) == 0):
            print("ERROR: Please use the --default_values argument to pass the default_fuse_values.txt file.")
            success = False
            quit()

        num_not_found = 0
        num_discarded = 0
        # num_kept = 0 - just use size of kept list

        kept_items = []
        # load old patch
        old_items = load_patch_items(args.old_patch)
        if (len(old_items) == 0):
            print(f"ERROR: No items loaded from {args.old_patch}")
            quit()

        # load default values
        default_items = load_patch_items(args.default_values)
        if (len(default_items) == 0):
            print(f"ERROR: No items loaded from {args.default_values}")
            quit()

        # for each value in patch, find match by name in default values
        for cur_old in old_items:
            find_res = find_by_name(cur_old['NAME'], default_items)
            if (find_res is None):
                print(f"WARNING: Unable to find {cur_old['NAME']} in {args.default_values}. Keeping.")
                num_not_found += 1
                cur_old['TYPE'] = "no default"
                kept_items.append(cur_old)
            else:
                if (find_res['VALUE'] != cur_old['VALUE']):
                    # if default value is different from patch value, add patch value to "keep" list and update type to default value
                    cur_old['TYPE'] = f"0x{find_res['VALUE']:x}"
                    kept_items.append(cur_old)
                else:
                    # values are the same; discard from list
                    print(f"Discarding {cur_old['NAME']} since its value 0x{cur_old['VALUE']:x} is same as default.")
                    num_discarded += 1

        # write keep list as target filename
        if (False == save_patch_items(target_file, kept_items)):
            print(f"ERROR: Failed to save file {target_file}")
            quit()

        # keep count of kept vs pruned items
        print(f"Items discarded from old patch: {num_discarded}")
        print(f"Items not found in default_fuse_values: {num_not_found}")
        print(f"Total items from old patch kept: {len(kept_items)}")
    elif (args.update_patch):
        # update patch mode
        if (len(args.old_patch) == 0):
            print("ERROR: Please use the --old_patch argument to pass the path of an existing patch file.")
            quit()
        elif (len(args.default_values) == 0):
            print("ERROR: Please use the --default_values argument to pass the default_fuse_values.txt file.")
            quit()

        # load patch file into list. values from this list are preseved, while other fields might change
        old_items = load_patch_items(args.old_patch)
        if (len(old_items) == 0):
            print(f"ERROR: No items loaded from {args.old_patch}")
            quit()

        # load default_values into list. address/startbit/size of fuses come from here.
        new_items = load_patch_items(args.default_values)
        if (len(new_items) == 0):
            print(f"ERROR: No items loaded from {args.default_values}")
            quit()

        # optionally load a list of fuses whose values should never be updated
        keep_locked = False
        locked_fuses = []
        if (len(args.locked_fuses) > 0):
            locked_fuses = load_fuse_names(args.locked_fuses)
            if (len(locked_fuses) == 0):
                print(f"ERROR: No items loaded from {args.locked_fuses}")
                quit()
            else:
                keep_locked = True

        locked_kept = 0
        unlocked_kept = 0
        unlocked_changed = 0
        new_added = 0
        if (len(args.imported_values) > 0):
            print(f"Importing new items from {args.imported_values}...")
            imported_items = load_patch_items(args.imported_values)
            if (len(imported_items) == 0):
                print(f"ERROR: No items loaded from {args.imported_values}")
                quit()
            for cur_item in imported_items:
                found_in_old = False
                for cur_old in old_items:
                    if (cur_old['NAME'] == cur_item['NAME']):
                        # found pre-existing patch item. keep that one, but allow value updates for any non-locked fuse
                        if keep_locked:
                            if (cur_old['NAME'] in locked_fuses):
                                print(f"- Keeping value of locked fuse {cur_old['NAME']} (0x{cur_old['VALUE']:x})")
                                locked_kept += 1
                            elif (cur_old['VALUE'] != cur_item['VALUE']):
                                # update value for non-locked fuse
                                cur_old['VALUE'] = cur_item['VALUE']
                                print(f"- Updating value of unlocked fuse {cur_old['NAME']} (0x{cur_old['VALUE']:x})")
                                unlocked_changed += 1
                            else:
                                print(f"- No value change in unlocked fuse {cur_old['NAME']} (0x{cur_old['VALUE']:x})")
                                unlocked_kept += 1
                        found_in_old = True
                        break
                if (not found_in_old):
                    # didn't find a pre-existing item; add this one to the patch list (will keep its value)
                    old_items.append(cur_item)
                    new_added += 1
            print(f"Locked fuses with preserved values: {locked_kept}")
            print(f"Unlocked fuses with unchanged values: {unlocked_kept}")
            print(f"Unlocked fuses with new values: {unlocked_changed}")
            print(f"Newly imported fuses: {new_added}")

        # begin config.out modifications
        # first, update old item list with all useable fuses from config.out file. only the name and value
        # will be kept; all other details will be updated from default values file. items from config.out
        # that aren't located in default_values will not be written to the patch file (since we have zero
        # info on the address/startbit/size of the given fuse)
        stub_items = []
        if config_out_items != None:
            for cur_cfg_item in config_out_items:
                found_old_item = False
                for cur_old_item in old_items:
                    if (cur_old_item['NAME'] == cur_cfg_item['NAME']):
                        found_old_item = True
                        # we chould keep the existing item if it's already in the patch, but we should
                        # also report out the difference, in case it's significant.
                        if cur_cfg_item['VALUE'] != cur_old_item['VALUE']:
                            print(f"NOTE: Keeping patch value 0x{cur_old_item['VALUE']:x}, instead of config value 0x{cur_cfg_item['VALUE']:x} for {cur_cfg_item['NAME']}")
                # if item not found, add a stub entry to the old list so it gets populated at stitch time
                if (found_old_item == False):
                    new_item = {
                        "ADDR" : 0,
                        "STARTBIT" : 0,
                        "WIDTH" : 0,
                        "VALUE" : cur_cfg_item['VALUE'],
                        "NAME" : cur_cfg_item['NAME'],
                        "TYPE" : "(fuse)",
                        "CFGITEM" : True,
                        "SKIP" : False
                    }
                    print(f"NOTE: Adding {cur_cfg_item['NAME']} = 0x{cur_cfg_item['VALUE']:02x} to the patch list.")
                    stub_items.append(new_item)
            # append stub items to old_items list
            if (stub_items != None):
                print(f"Adding {len(stub_items)} stub items to old item list...")
                old_items += stub_items

            print(f"cfg items {len(config_out_items)}, old_items {len(old_items)}, new_items {len(new_items)}")
        # end config.out modifications

        # create new patch using values from old patch and everything else from new
        success = update_patch(old_items, new_items, target_file)
    elif (args.reconcile_patch):
        if (len(args.old_patch) == 0):
            print("ERROR: Please use the --old_patch argument to pass the path of an existing patch file.")
            success = False
        elif (len(args.default_values) == 0):
            print("ERROR: Please use the --default_values argument to pass the path of an existing patch file.")
            success = False
        else:
            # load patch file into list
            old_items = load_patch_items(args.old_patch)

            # load default_values into list
            default_items = load_patch_items(args.default_values)

            item_pairs = []
            TYPE_EXACT = 0
            TYPE_CLOSEST = 1
            TYPE_NONE = 2
            for cur_old in old_items:
                found_match = False
                last_default = None
                for cur_default in default_items:
                    if cur_old['ADDR'] == cur_default['ADDR']:
                        last_default = cur_default
                        if (cur_old['STARTBIT'] == cur_default['STARTBIT']):
                            found_match = True
                            new_pair = {
                                'OLD' : cur_old,
                                'DEFAULT' : cur_default,
                                'MTYPE' : TYPE_EXACT
                            }
                            item_pairs.append(new_pair)
                if (not found_match):
                    if (last_default is not None):
                        new_pair = {
                            'OLD' : cur_old,
                            'DEFAULT' : last_default,
                            'MTYPE' : TYPE_CLOSEST
                        }
                        item_pairs.append(new_pair)
                    else:
                        new_pair = {
                            'OLD' : cur_old,
                            'DEFAULT' : cur_old,
                            'MTYPE' : TYPE_NONE
                        }
                        item_pairs.append(new_pair)

            outf = None
            try:
                outf = open(target_file, "w")
            except:
                print(f"ERROR: Unable to create default values file {target_file}")
                success = False
                quit()

            outf.write("# RamAddr (hex) StartBit (dec) Width (dec) Value (hex)\n")

            final_list = []
            for cur_pair in item_pairs:
                samevals = (cur_pair['OLD']['VALUE'] == cur_pair['DEFAULT']['VALUE'])
                # get backup of default value
                orig_val = cur_pair['DEFAULT']['VALUE']
                orig_name = cur_pair['OLD']['NAME']
                # always set name field
                cur_pair['OLD']['NAME'] = cur_pair['DEFAULT']['NAME']
                if (cur_pair['MTYPE'] == TYPE_EXACT):
                    if (samevals):
                        cur_pair['OLD']['TYPE'] = f"(exact, {orig_name})"
                    else:
                        cur_pair['OLD']['TYPE'] = f"(exact, {orig_name}, ov: 0x{orig_val:x})"
                elif (cur_pair['MTYPE'] == TYPE_CLOSEST):
                    if (samevals):
                        cur_pair['OLD']['TYPE'] = f"(closest, {orig_name}, s:{cur_pair['DEFAULT']['STARTBIT']} w:{cur_pair['DEFAULT']['WIDTH']})"
                    else:
                        cur_pair['OLD']['TYPE'] = f"(closest, {orig_name}, s:{cur_pair['DEFAULT']['STARTBIT']} w:{cur_pair['DEFAULT']['WIDTH']} v:0x{orig_val:x})"
                elif (cur_pair['MTYPE'] == TYPE_NONE):
                    cur_pair['DEFAULT']['TYPE'] = f"(no match, keeping original fuse)"


                cur_item = cur_pair['OLD']
                addr_fmt = '{:05x}'.format(cur_item['ADDR'])
                num_zeroes = 1
                if (cur_item['WIDTH'] > 4):
                    num_zeroes = (int(cur_item['WIDTH'] / 4))
                cur_val = cur_item['VALUE']
                zeroes_fmt = f":0{num_zeroes}x"
                zeroes_fmt = '{' + zeroes_fmt + '}'
                val_fmt = zeroes_fmt.format(cur_val)
                out_str = f"{addr_fmt} {cur_item['STARTBIT']} {cur_item['WIDTH']} {val_fmt} # {cur_item['NAME']} {cur_item['TYPE']}"
                outf.write(f"{out_str}\n")

            outf.close()
            print(f"Reconciled patch written to: {target_file}")
            success = True
    elif (len(args.dump_blob) > 0):
        success = dump_blob(args.dump_blob, args.default_values, args.target, args.start_address)
    elif (len(args.import_text_blob) > 0):
        blob_strings = load_text_blob(args.import_text_blob)
        if (len(blob_strings) > 0):
            success = import_blob(blob_strings, args.default_values, dlut_list, args.target, args.prefix, args.group, args.type_softstrap)
    elif (len(args.import_int_blob) > 0):
        blob_strings = load_int_blob(args.import_int_blob)
        if (len(blob_strings) > 0):
            success = import_blob(blob_strings, args.default_values, dlut_list, args.target, args.prefix, args.group, args.type_softstrap)
    elif (args.dump_dlut):
        success = dump_dlut(dlut_list, args.target)
        quit()
    elif (args.dump_ip_info):
        success = dump_ip_info(ip_info, args.target)
        quit()
    elif (args.print_fuse_stats):
        # next build statistics on the dlut data
        stats_list = get_stats(dlut_list)
        if (len(stats_list) == 0):
            print(f"ERROR: No stats read from {args.target} data")
            quit()

        # finally, print the resulting output
        success = print_stats(stats_list)
        quit()
    else:
        # lockbits mode
        constants = parse_for_constants(input_tree)

        # Find lockout bits for the different fuse categories (reparse fuses)
        constants = get_lockout_values(input_tree, constants)
        # print(constants)

        lockbits = parse_for_lockbits(input_tree)
        # print(lockbits)

        if (len(name_file) == 0):
            # no name_file specified; default behavior is to dump all fuse info
            # to CSV
            success = write_csv_file(target_file, lockbits, args.names_only)
        else:
            success = write_compute_file(target_file, name_file, lockbits,
                                         constants)

    if (success):
        print("Operation succeeded!")
    else:
        print("Operation failed.")