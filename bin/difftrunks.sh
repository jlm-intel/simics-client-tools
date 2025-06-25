#!/bin/bash

die() {
        echo >&2 "$@"
        exit 1;
}


if [ -z "$1" ]
then
	die "Please pass a file of paths to diff."
fi

if [ -z "$2" ]
then
  die "Please pass the first directory to diff."
fi

if [ -z "$3" ]
then
  die "Please pass the second directory to diff."
fi

PATHFILE=$1
FIRSTDIR=$2
SECONDDIR=$3

if [ ! -f "$PATHFILE" ]
then
  die "File not found: $PATHFILE"
fi

if [ ! -d "$FIRSTDIR" ]
then
  die "Dir not found: $FIRSTDIR"
fi

if [ ! -d "$SECONDDIR" ]
then
  die "Dir not found: $SECONDDIR"
fi

for CURPATH in `cat $1`
do
  echo "Current path: $CURPATH"
  diff "${FIRSTDIR}/${CURPATH}" "${SECONDDIR}/${CURPATH}"
done

