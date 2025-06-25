#!/usr/intel/bin/python3.7.4

import sys

# sample local url
# https://af02p-or.devtools.intel.com/ui/native/simics-local/vp-release/6.0/arrowlake-s/Bronze/2023ww05.4.00_42/
# sample generic url
# https://simics-artifactory.devtools.intel.com/artifactory/simics-repos/vp-release/6.0/arrowlake-s/Bronze/2023ww05.4.00_42/

def convert_url(in_url):
    # if find "simics-local", replace with "simics-repos"
    in_url = in_url.replace("simics-local", "simics-repos")

    # if no "simics-repos", not a valid url
    rep_index = in_url.find("simics-repos")
    if (-1 == rep_index):
        (print("(not a valid artifactory url)"))
        return

    # replace everything up to "simics-repos" with generic root
    out_suffix = in_url[rep_index:]

    out_url = "https://simics-artifactory.devtools.intel.com/artifactory/" + out_suffix
    print(out_url)

n = len(sys.argv)
if (n < 2):
    print("Please pass at least one artifactory url to genericize.")
    sys.exit(1)
for i in sys.argv:
    print("(original) " + i)
    convert_url(i)
print(str(n))
