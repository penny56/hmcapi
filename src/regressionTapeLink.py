'''
Created on June 23, 2022

1) List all Tape links.
2) Create a tape link named 'T257-Tapelink-Regression', verify it's in pending state
3) Create a partition, 'T257-Tapelink-Partition-Regression'
4) AttachT257-Tapelink-Regression to T257-Tapelink-Regression
5) Detach 
6) Delete the partition
7) modify the tape link
8) delete the tape link

Example:
-hmc 9.12.35.135 -cpc T257

@author: mayijie
'''

from CommonAPI.prsm2api import *
from CommonAPI.wsaconst import *
import argparse
import time

hmcHost = None
cpcName = None

tlName = "T257-Tapelink-Regression"
tlParName = 'T257-Tapelink-Partition-Regression'

# ------------------------------------------------------------------ #
# --------- Start of parseArgs function ---------------------------- #
# ------------------------------------------------------------------ #
def parseArgs():
  global hmcHost, cpcName
  global logDir, logLevel, configFilename
  parser = argparse.ArgumentParser(description='NVMe storage group regression test.')
  parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
  parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')

  parser.add_argument('-logLevel', '--logLevel', metavar='<log level name>', help='Logging level. Can be one of {debug, info, warn, error, critical}', 
                      choices=['debug', 'info', 'warn', 'error', 'critical'])

  parser.add_argument('-logDir', '--logDir', metavar='<log directory>', help='set log directory')
  parser.add_argument('-c', '--config', metavar='<file name>', help='Configuration file name (path)')
  args = vars(parser.parse_args())
  
  # HMC host
  _hmcHost = assertValue(pyObj=args, key='hmc', listIndex=0, optionalKey=True)
  hmcHost = checkValue('hmcHost', _hmcHost , hmcHost)
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

# ------------------------------------------------------------------ #
# --------- Start of printParams function -------------------------- #
# ------------------------------------------------------------------ #
def printParams():
  print("\tParameters were input:")
  print("\tHMC system IP\t%s"%hmcHost)
  print("\tCPC name\t\t%s"%cpcName)

  print("\ttape link name\t%s"%tlName)
  print("\ttape link partition name\t%s"%tlParName)

# main function
hmc = None
success=True

try:
  parseArgs()
  
  print ("******************************")
  msg = "Tape link regression test"
  print (msg)
  printParams()
  print ("******************************")

  # Access HMC system and create HMC connection 
  hmc = createHMCConnection(hmcHost=hmcHost)
  cpc = selectCPC(hmc, cpcName)
  cpcURI = assertValue(pyObj=cpc, key=KEY_CPC_URI)
  cpcName = assertValue(pyObj=cpc, key=KEY_CPC_NAME)
  cpcStatus = assertValue(pyObj=cpc, key=KEY_CPC_STATUS)
  
  # Get CPC UUID
  cpcID = cpcURI.replace('/api/cpcs/','')
  
  # list the current tape link
  tplist = listTapeLinks(hmc)
  print ("there have: " + str(len(tplist)) + " tape links in this system.")

  # Create a tape link
  tlTempl = dict()
  tlTempl['name'] = tlName
  tlTempl['cpc-uri'] = cpcURI
  tlTempl['description'] = "Tape link description."
  tlRet = createTapeLink(hmc, tlTempl)
  print ("Tape link " + tlName + " created successfully!")
  time.sleep(1)

  # Verify the tape link state
  tlProp = getTapeLinkProperties(hmc, tlURI=tlRet)
  if (tlProp['fulfillment-state'] != 'pending'):
    exc = HMCException("Tape link not in pending state after creatation!")
    raise exc
  
  # Create a test partition
  partTempl = dict()
  partTempl['name'] = tlParName
  partTempl['ifl-processors'] = 1
  partTempl['initial-memory'] = 1024
  partTempl['maximum-memory'] = 1024
  partRet = createPartition(hmc, cpcID, partTempl)
  partID = partRet.replace('/api/partitions/','')
  print ("Test Partition created successfully!")
  time.sleep(1)

  # Attach tape link to partition
  tlTempl = dict()
  tlTempl['tape-link-uri'] = tlRet
  attachTapeLink(hmc, partID, tlTempl)
  print ("Tape link attached to partition successfully!")
  time.sleep(1)

  # Modify the tape link
  tlTempl = dict()
  tlTempl['description'] = "Description II."
  tlID = tlRet.replace('/api/tape-links/','')
  modifyTapeLinkProperties(hmc, tlID, tlTempl)
  print ("Tape link description modification successfully!")
  time.sleep(1)

  # Detach
  tlTempl = dict()
  tlTempl['tape-link-uri'] = tlRet
  detachTapeLinkFromPartition(hmc, partID, tlTempl)
  print ("Tape link detach from partition successfully!")
  time.sleep(1)

  # Delete the tape link
  tlTempl = dict()
  tlTempl['email-to-addresses'] = ['mayijie@cn.ibm.com']    # Actually this is a bug, the spec read this field is optional, but it's mandatory.
  deleteTapeLink(hmc, tlID, tlTempl)
  print ("Tape link deleted successfully!")
  time.sleep(1)

  # Delete the partition
  deletePartition(hmc, parID=partID)
  print ("Partition deleted successfully!")



except Exception as exc:
  print (exc)
  
finally:
  # cleanup
  if hmc != None:
    hmc.logoff()
