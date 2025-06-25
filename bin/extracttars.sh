#!/bin/bash

# 2022.04.04 - no longer errors if no match found.
# 2022.02.14 - added gzip support
# 2018.06.28 - first version

die() {
        echo >&2 "$@"
        exit 1;
}


# search for normal tars
echo "Searching for tar files to expand..."
#for CURTAR in `ls *.tar`
for CURTAR in *.tar *.ostar *.sostar
do
	if [ -f ${CURTAR} ]
	then
		echo "${CURTAR}..."	
		tar xvf ${CURTAR}
		if [ $? -ne 0 ]
		then
			die "Failed to extract ${CURTAR}."
		fi
	fi
done

# search for gzip tars
echo "Searching for tgz files to expand..."
#for CURTAR in `ls *.tgz`
for CURTAR in *.tgz
do
	if [ -f ${CURTAR} ]
	then
		echo "${CURTAR}..."	
		tar xzvf ${CURTAR}
		if [ $? -ne 0 ]
		then
			die "Failed to extract ${CURTAR}."
		fi
	fi
done

#search for *.tar.gz....
# search for gzip tars
echo "Searching for tar.gz files to expand..."
#for CURTAR in `ls *.tar.gz`
for CURTAR in *.tar.gz
do
	if [ -f ${CURTAR} ]
	then
		echo "${CURTAR}..."	
		tar xzvf ${CURTAR}
		if [ $? -ne 0 ]
		then
			die "Failed to extract ${CURTAR}."
		fi
	fi
done
