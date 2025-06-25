#!/usr/intel/pkgs/bash/3.0/bin/bash
export http_proxy=http://proxy-chain.intel.com:911
export https_proxy=http://proxy-chain.intel.com:912
./_tools/pretest.py
echo $?
