'''
Created on June 9, 2022

1) Search all the NVMe SSD adapters, get an available one.
2) Create a nvme storage group named 'A90-NVMe-Regression-SG'
3) Create a partition, 'A90-NVMe-Regression-test'
4) Attach A90-NVMe-Regression-SG to A90-NVMe-Regression-test
5) Detach 
6) Delete the partition
7) delete the nvme sg

Example:
-hmc 9.12.35.135 -cpc M90

@author: mayijie
'''

from CommonAPI.prsm2api import *
from CommonAPI.wsaconst import *
import argparse
import time

hmcHost = None
cpcName = None

nvmeSgName = "A90-nvme-sg"
nvmeParName = 'A90-NVME-PARTITION'
# the partition id should not state here, it shoud be get from partition name
nvmeParID = 'd2f95e62-e580-11ec-96d2-00106f258eea'
nvmeAdapterName = 'NVMe 0194 B25B-08'


# ------------------------------------------------------------------ #
# --------- Start of parseArgs function ---------------------------- #
# ------------------------------------------------------------------ #
def parseArgs():
  global hmcHost, cpcName
  global logDir, logLevel, configFilename
  parser = argparse.ArgumentParser(description='Create a new NIC for partition')
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

  print("\tnvme storage group name\t%s"%nvmeSgName)
  print("\tnvme partition name\t%s"%nvmeParName)

# main function
hmc = None
success=True

try:
  parseArgs()
  
  print ("******************************")
  msg = "Create new NIC in the partition"
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
  
  # Get the NVMe adapter uri by adapter name
  adapterUri = selectAdapter(hmcConn=hmc, adapterName=nvmeAdapterName, cpcID=cpcID)[KEY_ADAPTER_URI]

  # minimum properties settings for nvme sg.
  svsTempl = list()
  svTempl = dict()
  svTempl['operation'] = 'create'
  svTempl['adapter-uri'] = adapterUri
  svsTempl.append(svTempl)

  sgTempl = dict()
  sgTempl['name'] = nvmeSgName
  sgTempl['cpc-uri'] = cpcURI

  # for common properties
  sgTempl['type'] = 'nvme'
  sgTempl['shared'] = False
  sgTempl['storage-volumes'] = svsTempl

  sgUri = createStorageGroup(hmc, sgTempl)
  print ("NVMe storage group created!")
  time.sleep(1)
  # Get the partition id


  # Attach the nvme sg to the partition
  sgTempl = dict()
  sgTempl['storage-group-uri'] = sgUri

  attachStorageGroup(hmc, partID=nvmeParID, sgProp=sgTempl)
  print ("NVMe storage group attached!")
  time.sleep(1)

  # Verify the storage group attached
  sgID = sgUri.replace('/api/storage-groups/','')
  partDict = dict()

  partDict = getPartitionsForAStorageGroup(hmc, sgID)
  if len(partDict) != 1:
    exc = HMCException("NVMe storage group attach failed!")
    raise exc
  print ("Verified!")
  time.sleep(1)

  # Detach the nvme sg from the partition
  detachStorageGroup(hmc, partID=nvmeParID, sgProp=sgTempl)
  print ("NVMe storage group detached!")
  time.sleep(1)

  # Verify the storage group detached
  partDict = getPartitionsForAStorageGroup(hmc, sgID)
  if len(partDict) != 0:
    exc = HMCException("NVMe storage group detach failed!")
    raise exc
  print ("Verified!")
  time.sleep(1)

  # Delete the nvme storage group
  deleteStorageGroup(hmc, sgID)
  print ("NVMe storage group deleted!")
  time.sleep(1)

except Exception as exc:
  print (exc)
  
finally:
  # cleanup
  if hmc != None:
    hmc.logoff()
