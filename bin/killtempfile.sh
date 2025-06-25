#!/bin/bash

die() {
        echo >&2 "$@"
        exit 1;
}

if [ ! -f "$1" ]
then
    die "ERROR: ${1} doesn't exist or isn't a file."
fi

git ls-files --error-unmatch ${1} 2>/dev/null 1>/dev/null 0>/dev/null
lsfiles_result=$?

if [ $lsfiles_result -eq 0 ]
then
    echo "Skipping file (checked into Git): ${1}"
else
    echo "Removing file ${1}..."
    rm "${1}"
fi
