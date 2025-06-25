#!/bin/bash

die() {
        echo >&2 "$@"
        exit 1;
}

TOUCH_DIR=${SIMICSUSERDIR}

if [ -z $1 ]
then
    echo "No directory passed. Defaulting to: ${SIMICSUSERDIR}"
else
    echo "Using directory: ${1}"
    TOUCH_DIR="$1"
fi


if [ ! -d "${TOUCH_DIR}" ]
then
    die "ERROR: ${TOUCH_DIR} doesn't exist or isn't a directory."
fi

echo "Updating access times of all files under: ${TOUCH_DIR} This might take a while..."
find "${TOUCH_DIR}" -type f -exec touch -a -c {} \;
if [ $? -ne 0 ]
then
    echo "ERROR: Find returned code $?"
else
    echo "INFO: Find/Touch operation succeeded."
fi
