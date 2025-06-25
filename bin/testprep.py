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
    # if we want to actually INSTALL xtensa we should do "source setupxtensa" instead
fi

echo ">>> Making pkg-prep..."
# using "-j1" because there is some duplicate work done here that can error out if done simultaneously
gmake -j1 pkg-prep-7444 pkg-prep-7440 pkg-prep-7960 pkg-prep-7446 pkg-prep-7938 pkg-prep-7319 pkg-prep-7443 pkg-prep-7967 pkg-prep-7937 -k
# gmake -j10 pkg-prep-7444
if [ $? -ne 0 ]
then
#    die "ERROR: Failed to run pkg-prep-7444."
    echo "WARNING: Failed to run pkg-prep-7444 (et al)."
fi

