#!/usr/bin/env python
# Copyright 2018-2022 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Example that lists storage groups on a CPC in DPM mode.
"""

import sys
import requests.packages.urllib3

import zhmcclient
# from zhmcclient.testutils import hmc_definitions

requests.packages.urllib3.disable_warnings()

# Get HMC info from HMC inventory and vault files
#hmc_def = hmc_definitions()[0]
nickname = "HMC1"
host = "9.12.35.134"
userid = "apiuser"
password = "apiuser"
verify_cert = False
cpcName = "A257"

print(__doc__)

print("Using HMC {} at {} with userid {} ...".format(nickname, host, userid))

print("Creating a session with the HMC ...")
try:
    session = zhmcclient.Session(
        host, userid, password, verify_cert=verify_cert)
except zhmcclient.Error as exc:
    print("Error: Cannot establish session with HMC {}: {}: {}".
          format(host, exc.__class__.__name__, exc))
    sys.exit(1)

try:
    client = zhmcclient.Client(session)

    print("Finding a CPC in DPM mode ...")
    cpcs = client.cpcs.list(filter_args={'dpm-enabled': True, 'name': cpcName})
    if not cpcs:
        print("Error: HMC at {} does not manage any CPCs in DPM mode".
              format(host))
        sys.exit(1)
    cpc = cpcs[0]
    print("Using CPC {}".format(cpc.name))

    print("Listing storage groups of CPC {} ...".format(cpc.name))
    try:
        partitions = cpc.partitions.list()
        
    except zhmcclient.Error as exc:
        print("Error: Cannot list storage groups of CPC {}: {}: {}".
              format(cpc.name, exc.__class__.__name__, exc))
        sys.exit(1)

    parStatus = dict()
    for part in partitions:
        if part.get_property('status') in parStatus:
            parStatus[part.get_property('status')] += 1
        else:
            parStatus[part.get_property('status')] = 1
    print (parStatus)

    try:
        partObj = cpc.partitions.find(name = "A257-SUSE02")

    except Exception as exc:
            print (exc)
    
    try:
        partObj.start(wait_for_completion = True, operation_timeout = 600, status_timeout = 600)
    except Exception as exc:
        print (exc)


finally:
    print("Logging off ...")
    session.logoff()