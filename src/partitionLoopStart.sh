#! /bin/bash

# hmc ip
hmc_ip=$1

# cpc name
cpc_name=$2

# config file name
config_file=$3


cd /SystemzSolutionTest/prsm2ST/

# set the partition loop flag file to 1
echo 1 > loopFlag.cfg

# run
`python partitionLoop.py -hmc $hmc_ip -cpc $cpc_name -config $config_file` &