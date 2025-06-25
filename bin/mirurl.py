#!/usr/intel/bin/python3.7.4

import sys
from urllib.parse import urljoin
from urllib.request import Request, urlopen

# sample local url
# https://af02p-or.devtools.intel.com/ui/native/simics-local/vp-release/6.0/arrowlake-s/Bronze/2023ww05.4.00_42/
# sample generic url
# https://simics-artifactory.devtools.intel.com/artifactory/simics-repos/vp-release/6.0/arrowlake-s/Bronze/2023ww05.4.00_42/

# generic: https://simics-artifactory.devtools.intel.com/artifactory/simics-repos/ts/cpuids/cwf/cwf-cpuid-specs-23ww09.tar.gz
# mirror1: https://af02p-or.devtools.intel.com/ui/native/simics-repos/ts/cpuids/cwf/cwf-cpuid-specs-23ww09.tar.gz
# mirror2: https://af01p-il.devtools.intel.com/ui/native/simics-repos/ts/cpuids/cwf/cwf-cpuid-specs-23ww09.tar.gz

# global constants
TYPE_UNKNOWN = 0
TYPE_GENERIC = 1
TYPE_LOCALIZED = 2
LOCALIZED_URLS = [
    "https://af01p-ba.devtools.intel.com/ui/native/",
    "https://af01p-il.devtools.intel.com/ui/native/",
    "https://af01p-ir.devtools.intel.com/ui/native/",
    "https://af02p-or.devtools.intel.com/ui/native/"
]

# indicates what kind of artifactory url is passed, if any
def get_url_type(in_url):
    if (in_url.find("/artifactory/simics-repos/") != -1):
        return TYPE_GENERIC
    if (in_url.find("/ui/native/simics-repos/") != -1):
        return TYPE_LOCALIZED
    return TYPE_UNKNOWN

def convert_url(in_url):
    ret_list = []

    # if find "simics-local", replace with "simics-repos"
    in_url = in_url.replace("simics-local", "simics-repos")

    # if no "simics-repos", not a valid url
    rep_index = in_url.find("simics-repos")
    if (-1 == rep_index):
        (print("(not a valid artifactory url)"))
        return None

    # replace everything up to "simics-repos" with generic root
    out_suffix = in_url[rep_index:]

    for i in LOCALIZED_URLS:
        new_url = urljoin(i, out_suffix)
        print(new_url)
        #req = Request(new_url)
        errorcode = 0
        try:
            urlobj = urlopen(new_url)
            print(urlobj.read())
            print(urlobj.status)
            print(urlobj.url)
        except urllib.error.HTTPError as e:
            errorcode = e.code
        except urllib.error.URLError as e:
            errorcode = e.code

        if (errorcode) == 200:
            print(f'{new_url} - found {errorcode}')
        else:
            print(f'{new_url} - NOT FOUND {errorcode}')
    #out_url = "https://simics-artifactory.devtools.intel.com/artifactory/" + out_suffix
    #print(out_url)

n = len(sys.argv)
if (n < 2):
    print("Please pass at least one artifactory url to genericize.")
    sys.exit(1)
for i in sys.argv:
    urltype = get_url_type(i)
    convert_url(i)
