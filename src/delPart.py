import sys
import time

import zhmcclient
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()

host = '9.12.35.134'
userid = 'apiuser'
password = 'apiuser'
verify_cert = False
cpcName = 'T257'
partName = 'hi'

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

    partObj = cpc.partitions.find(name = partName)

    print ("Got the partition object: " + str(partObj))

    if str(partObj.get_property('status')) == 'stopped':
        partObj.delete()
        print ("Partition delete done.")
    else:
        print ("Not in stopped state.")

except Exception as e:
    print ("except --> " + str(e))

finally:
    print("Logging off ...")
    session.logoff()