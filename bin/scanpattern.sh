#!/usr/intel/pkgs/bash/3.0/bin/bash

die() {
        echo >&2 "$@"
        exit 1;
}

if [ -z "$1" ]
then
  die "ERROR: Please pass a Simics C file to parse."
fi

IMPFILE="$1"
if [ ! -f "$IMPFILE" ]
then
  die "ERROR: File $[IMPFILE] not found!"
fi

if [ -z "$2" ]
then
  die "ERROR: No search pattern specified!"
fi

# " *   /"
while IFS= read -r line
do
  # somehow the " *   /" at the beginning of comment lines gets truncated down to "* /" WHY???
  grep -q '\*\s/' <<< ${line}
  if [ $? -eq 0 ]
  # remove first 2 characters
  then
    newfile="${line:5}"
    #echo $newfile
    grep "$2" "$newfile" /dev/null
  fi

  # stop once the initial comment block is finished, otherwise we could be searching for minutes
  if grep -q '\*/' <<< ${line}
  then
    echo "Stopping read!"
    exit 0;
  fi

done < "$IMPFILE"

