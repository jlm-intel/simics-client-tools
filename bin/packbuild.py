#!/bin/bash

#set -x

die() {
        echo >&2 "$@"
        exit 1;
}

export SKIP_MISSING_FILES=yes
export SKIP_MISSING_MODULES=yes
export TOOLSDIR=../_tools
echo ">>> TOOLSDIR=${TOOLSDIR}"

if [ "$XTENSA_DIR" != "/nfs/site/proj/simics/simics_extensions/xtensa" ]
then
    echo ">>> Setting Xtensa Vars..."
    source varsxtensa
fi

echo ">>> Making pkg-prep..."
gmake -j10 pkg-prep-7444 pkg-prep-7440 pkg-prep-7960 pkg-prep-7446 pkg-prep-7938 pkg-prep-7319 pkg-prep-7443 pkg-prep-7967 pkg-prep-7937 -k
# gmake -j10 pkg-prep-7444
if [ $? -ne 0 ]
then
#    die "ERROR: Failed to run pkg-prep-7444."
    echo "WARNING: Failed to run pkg-prep-7444 (et al)."
fi

if [ ! -d "../_tools" ]
then
    die "ERROR: ../_tools not found. Make sure you run from project dir. Ex: vp/adl"
fi
if [ -d "./_tools" ]
then
    echo ">>> Removing local ./_tools directory."
#    echo ">>> (SKIPPING THIS STEP)"
    rm -rf "./_tools"
fi
echo ">>> Running test_docbuild..."
python ../_tools/test_docbuild.py --simics-version 6.0  --pkg-nums 7444 --verbose

if [ ! -d "../_tools" ]
then
    die "ERROR: ../_tools not found. Make sure you run from project dir. Ex: vp/adl"
fi
if [ -d "./_tools" ]
then
    echo ">>> Removing local ./_tools directory."
#    echo ">>> (SKIPPING THIS STEP)"
    rm -rf "./_tools"
fi
echo ">>> Running setperms.sh..."
setperms.sh
echo ">>> Running test_packaging..."
python ../_tools/test_packaging.py --simics-version 6.0 --pkg-nums 7444 --verbose
