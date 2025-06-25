#!/usr/intel/bin/python
#def reg_arr_value_bits(byte_arr, offset, msb, lsb):
try:
    import os # path functions
    import sys # argument processing

    import glob # filename expansion
#    import datetime # date and time functions
    from shutil import copyfile # copy files when needed

    #from lxml import etree # xml parsing
#    import xml.etree.ElementTree as etree

#    import cdb_classes # SrcBank, Register, Field, etc.
#    from crif import parse
except:
    print("ERROR: Problem importing dependencies.")
    quit()


# main function for testing
def main(*args):

    if (len(args) < 2):
        print("ERROR: Please pass a source transform directory and a target strip directory.")
        quit()

    sourcedir = args[0]
    targetdir = args[1]
    print("source: {0}, target: {1}".format(sourcedir, targetdir))
    if not os.path.exists(sourcedir):
        print("ERROR: path {0} does not exist!".format(sourcedir))
        quit()
    if not os.path.exists(targetdir):
        print("ERROR: path {0} does not exist!".format(targetdir))
        quit()
    if sourcedir == targetdir:
        print("ERROR: source and target path cannot be the same!")
        quit()

    sourcelist = glob.glob(os.path.join(sourcedir, "*.py")
    if (len(sourcelist) == 0:
        print("ERROR: No python files found in {0}.".format(sourcedir))
        quit()


if __name__== "__main__":
    main(*sys.argv[1:])