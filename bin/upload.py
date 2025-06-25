#!/usr/intel/bin/python3.7.4

import sys
import urllib.parse
import os
import subprocess

# sample local url
# https://af02p-or.devtools.intel.com/ui/native/simics-local/vp-release/6.0/arrowlake-s/Bronze/2023ww05.4.00_42/
# sample generic url
# https://simics-artifactory.devtools.intel.com/artifactory/simics-repos/vp-release/6.0/arrowlake-s/Bronze/2023ww05.4.00_42/

# note: Urls must be generic form (see above); local urls will fail to upload
urls_list = [
    ["TEST uploads", "https://simics-artifactory.devtools.intel.com/artifactory/simics-repos/pub/jlmayfie/test"],
    ["Josh NVL-S uploads", "https://simics-artifactory.devtools.intel.com/artifactory/simics-local/ts/shared/nvl-s/"],
    ["Josh NVL-P uploads", "https://simics-artifactory.devtools.intel.com/artifactory/simics-local/ts/shared/nvl-p/"],
    ["ARL-S IFWI uploads", "https://simics-artifactory.devtools.intel.com/artifactory/simics-repos/ts/bios/arls/ifwi_release/"],
    ["ARL-S craff images", "https://simics-artifactory.devtools.intel.com/artifactory/simics-repos/ts/images/arl/"],
    ["MTL-S regs and fuses", "https://simics-artifactory.devtools.intel.com/artifactory/simics-repos/ts/dumps/mtl/"],
]

def print_url_options(filename):
    # print upload dir list
    print("Where do you want to upload file " + filename + "?")
    index = 0
    for i in urls_list:
        print(str(index) + ": " + urls_list[index][0] + " - " + urls_list[index][1])
        index += 1

    # get and validate user input
    updir = int(input())
    if (updir < 0) or (updir > index):
        print("ERROR: Invalid selection entered: " + str(updir))
        return 1

    # validate file existence
    if (not os.path.isfile(filename)):
        print("ERROR: Not a valid file: " + filename)
        return 1

    # upload selected file
    #cmd = "hpm.py up " + filename
    retcode = subprocess.call(["artifactory-helper", "up", urls_list[updir][1], filename])
    #retcode = subprocess.call(["hpm.py", "up", urls_list[updir][1], filename])
    if (retcode > 0):
        print("ERROR: hpm returned error " + str(retcode))
    return retcode


n = len(sys.argv)
if (n < 2):
    print("Please pass at least one file to upload to artifactory.")
    sys.exit(1)
x = 0
for i in sys.argv:
    if (x > 0):
        print_url_options(i)
    x += 1


