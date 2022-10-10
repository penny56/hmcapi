import sys
import time

import zhmcclient
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()

'''
host = '9.12.16.95'
userid = 'mayijie@cn.ibm.com'
password = 'penny5656565bbb'
verify_cert = False
cpcName = 'A90'
'''
host = '9.12.16.95'
userid = 'mayijie@cn.ibm.com'
password = 'penny5656565bbb'
verify_cert = False
cpcName = 'A90'

print("Using HMC {} with userid {} ...".format(host, userid))

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
    cpcs = client.cpcs.list(filter_args={'dpm-enabled': True})
    if not cpcs:
        print("Error: HMC at {} does not manage any CPCs in DPM mode".
              format(host))
        sys.exit(1)

    for cpc in cpcs:
        if cpc.name == cpcName:
            break
    print("Using CPC {}".format(cpc.name))

    print("Listing storage groups of CPC {} ...".format(cpc.name))
    
    cnt = 50
    while cnt > 1:
        try:
            storage_groups = cpc.list_associated_storage_groups()
        except zhmcclient.Error as exc:
            print("Error: Cannot list storage groups of CPC {}: {}: {}".
                format(cpc.name, exc.__class__.__name__, exc))
            sys.exit(1)
        print (cnt)
        cnt -= 1
        time.sleep(1)

finally:
    print("Logging off ...")
    session.logoff()