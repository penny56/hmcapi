'''
Created on Sept 26, 2022

Example:
-hmc 9.12.35.135 -cpc A90

@author: mayijie
'''

from CommonAPI.prsm2api import *
from CommonAPI.wsaconst import *
import CommonAPI.hmcUtils
import argparse
import logging
import sys

hmcHost = None
cpcName = None
parRange = None
logDir = None
logLevel = None
configFile = None
configFilename = None

# partition properties, new and original
argsDict = dict()
partitionProps = dict()
parState = dict()

# log levels
sysoutLogLevel = logging.ERROR
defaultLogLevel = logging.INFO
logLevel = defaultLogLevel

# partition list only for the partition(s) in shared mode
wholeParNamesList = []
wholeParURIsList = []

# do we need to list all the CPC partitions
listAll = False
inputParNamesList = []

# To construct a table
TAB = 13
colWidth = TAB * 2
colOrder = ('Partition Name', 'Name', 'Device Number', 'Adapter Name', 'Adapter Port',
            'Card Type', 'VLAN ID & Type', 'MAC Address', 'Description')

# ------------------------------------------------------------------ #
# --------- Start of parseArgs function ---------------------------- #
# ------------------------------------------------------------------ #


def parseArgs():
    global hmcHost, cpcName
    global parRange
    global logDir, logLevel, configFilename
    global argsDict
    parser = argparse.ArgumentParser(description='off-line update the Processor parameters for partition')
    parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
    parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')

    args = vars(parser.parse_args())

    # HMC host
    _hmcHost = assertValue(pyObj=args, key='hmc', listIndex=0, optionalKey=True)
    hmcHost = checkValue('hmcHost', _hmcHost, hmcHost)
    if hmcHost == None:
        exc = HMCException("checkParams", "You should specify HMC Host name/ip address")
        print (exc.message)
        raise exc
    # CPC name
    _cpcName = assertValue(pyObj=args, key='cpcName', listIndex=0, optionalKey=True)
    cpcName = checkValue('cpcName', _cpcName, cpcName)
    if cpcName == None:
        exc = HMCException("checkParams", "You should specify CPC name")
        print (exc.message)
        raise exc
# ------------------------------------------------------------------ #
# --------- End of parseArgs function ------------------------------ #
# ------------------------------------------------------------------ #


# main function
hmc = None
success = True

try:
    parseArgs()

    # Access HMC system and create HMC connection
    hmc = createHMCConnection(hmcHost=hmcHost)
    cpc = selectCPC(hmc, cpcName)
    cpcURI = assertValue(pyObj=cpc, key=KEY_CPC_URI)
    cpcName = assertValue(pyObj=cpc, key=KEY_CPC_NAME)
    cpcStatus = assertValue(pyObj=cpc, key=KEY_CPC_STATUS)

    # Get CPC UUID
    cpcID = cpcURI.replace('/api/cpcs/', '')
    # Get storage group list
    

    cnt = 50
    while cnt > 1:
        try:
            sgList = getStorageGroupList(hmc)
        except Exception as exc:
            print("Error: Cannot list storage groups of CPC")
            sys.exit(1)
        print (cnt)
        cnt -= 1
        time.sleep(1)

except Exception as exc:
    print (exc)

finally:
    # cleanup
    if hmc != None:
        hmc.logoff()
