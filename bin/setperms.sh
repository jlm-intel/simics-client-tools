#!/bin/bash

die() {
        echo >&2 "$@"
        exit 1;
}

#set -x

if [ ! -d "../_tools" ]
then
    die "ERROR: ../_tools not found. Please run from inside project directory (vp/adl)."
fi

chmod o+x ../common/targets/sw-common.include
echo ">>> Setting perms on original test_utils files..."
chmod o+x ../_tools/test_utils/_common/compare_bmp_palette.py
chmod o+x ../_tools/test_utils/_common/difflib_patched.py
chmod o+x ../_tools/test_utils/_common/keycodes.include
chmod o+x ../_tools/test_utils/_common/select_tests.py
chmod o+x ../_tools/test_utils/psutil/_psutil_linux.cpython-37m-x86_64-linux-gnu.so
chmod o+x ../_tools/test_utils/psutil/_psutil_posix.cpython-37m-x86_64-linux-gnu.so
chmod o+x ../_tools/test_utils/runtest.py
echo ">>> Setting perms on local test_utils files..."
chmod o+x _tools/test_utils/_common/compare_bmp_palette.py
chmod o+x _tools/test_utils/_common/difflib_patched.py
chmod o+x _tools/test_utils/_common/keycodes.include
chmod o+x _tools/test_utils/_common/select_tests.py
chmod o+x _tools/test_utils/psutil/_psutil_linux.cpython-37m-x86_64-linux-gnu.so
chmod o+x _tools/test_utils/psutil/_psutil_posix.cpython-37m-x86_64-linux-gnu.so
chmod o+x _tools/test_utils/runtest.py
chmod o+x targets/adl-extensions/wb/ec/adl-ec-wb-post.include
chmod o+x targets/adl-extensions/wb/ec/adl-ec-wb-pre.include
chmod o+x targets/adl-extensions/wb/ec/adl-ec-wb-wa.include
chmod o+x targets/adl-extensions/wb/pmc/adl-pmc-wb-post.include
chmod o+x targets/adl-extensions/wb/pmc/adl-pmc-wb-pre.include
chmod o+x targets/adl-extensions/wb/pmc/adl-pmc-wb-wa.include
chmod o+x targets/adl-extensions/wb/pmc/adp-pmc-wb-h.simics
chmod o+x targets/adl-extensions/wb/pmc/images/ARCBootstrap_adl_s_rtl1_p0_a0_frzn.bin
chmod o+x targets/adl-extensions/wb/pmc/images/ARCRuntime_p8f.bin
chmod o+x targets/adl-extensions/wb/pmc/images/chipinit.bin
chmod o+x targets/adl-extensions/wb/pmc/images/er_table.bin
chmod o+x targets/adl-extensions/wb/pmc/images/fivr_lut.bin
chmod o+x targets/adl-extensions/wb/pmc/images/smip.bin
chmod o+x targets/adl-extensions/wb/pmip/adl-pmip-wb-wa.include
chmod o+x targets/adl-extensions/wb/punit/adl-punit-wb-wa.include
chmod o+x targets/adl/adl-sw.include
chmod o+x targets/adl/adl-system-pre.include
chmod o+x targets/adl/alderlake-s-a0-ifwi.json
chmod o+x targets/adl/alderlake-s-b0-ifwi.json
chmod o+x targets/adl/alderlake-sw.json
chmod o+x targets/adl/images/BIOSGuardModule_10.o
chmod o+x targets/adl/images/huffman_cnl.dic1
chmod o+x targets/adl/images/huffman_cnl.dic2
chmod o+x targets/adl/images/huffman_cnl.fsm
chmod o+x targets/sw-common.include
chmod o+x test/runtest.py

echo "Set permissions on files."
