#!/usr/intel/pkgs/bash/3.0/bin/bash

for TARGETSERVER in plxcg8099 plxcg8100 plxcg8101 plxcg8102 plxcg8103  plxcg8104 plxcg8105 plxcq8062 plxcq8063 plxcq8064 plxcq8067 plxcq8068 plxcq8069 plxcq8070 plxcg8106 plxcg8107 plxcg8108 plxcg8109 plxcg8110 plxcg8111 plxcg8112 plxcq8057 plxcq8058 plxcq8059 plxcq8060 plxcq8061 plxcq8065 plxcq8066 plxcz1001
do
  echo "${TARGETSERVER}..."
  ssh ${USER}@${TARGETSERVER}.pdx.intel.com
done
