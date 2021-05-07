'''
Created on Oct 24, 2017

Since "Virtual switches are generated automatically every time a new network adapter is detected and configured."
So that we don't need to "create" a "virtual switch" when we want to create a new vNIC, 
we just find the vNIC belonging to the adapter/port and link it the the new created NIC

Only four parameters are mandatory: partition name, NIC name, adapter name and adapter port, VLAN ID and MAC Address are not support in the current version.

Example:
-hmc 9.12.35.135 -cpc M90 -parName LNXT01 -nicName m90lt01_*** -adaName "OSD 0174 Z22B-36" -adaPort 0

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
parName = None
nicName = None
devNum = None
nicDesc = None
vlanID = None
MACAdd = None
adaName = None
adaPort = None
logDir = None
logLevel = None
configFile = None
configFilename = None

adapterUri = None
vsUri = None

# log levels
sysoutLogLevel = logging.ERROR
defaultLogLevel = logging.INFO
logLevel = defaultLogLevel

#partition list only for the partition in shared mode
wholeParNamesList=[]
wholeParURIsList=[]

# ------------------------------------------------------------------ #
# --------- Start of setupLoggers function ------------------------- #
# ------------------------------------------------------------------ #
# - Configures loggers for this script
def setupLoggers(
                 logDir=None, 
                 logLevel=defaultLogLevel
                 ):
  '''
    - Configures loggers for this script
  '''
  # set log level
  levelsDict = {"debug":    logging.DEBUG, 
                "info":     logging.INFO, 
                "warn":     logging.WARN, 
                "error":    logging.ERROR, 
                "critical": logging.CRITICAL}
  if logLevel in levelsDict.keys():
    logLevel = levelsDict[logLevel]
  else:
    logLevel = defaultLogLevel
  log.setLevel(logLevel)
  
  # add log file handler if specified
  if logDir != None:
    st = checkDirectory(logDir, createIfNonExist=True, silentCreate=True)
    if not st[KEY_RETURN_STATUS]:
      msg = "Logging directory [%s] doesn't exist. Skipping.."%(logDir)
      print msg
    else:
    # prepare file name
      scriptName = os.path.basename(sys.argv[0])
      logFileName = scriptName.replace('.py', '')
    # prepare time suffix for directory
      strTime = time.strftime("-%Y%m%d", time.localtime())

      logFileName = cpcName + "-" + logFileName + strTime + '.log'
      hdlr = logging.FileHandler(logDir + os.sep + logFileName)
      formatter = logging.Formatter('%(asctime)-23s %(message)s')
      hdlr.setFormatter(formatter)
      hdlr.setLevel(logLevel)#flogLevel)
      log.addHandler(hdlr)
  sysoutLogHandler = logging.StreamHandler(sys.stdout)
  logFormatter = logging.Formatter('%(message)s')
  sysoutLogHandler.setFormatter(logFormatter)
  sysoutLogHandler.setLevel(sysoutLogLevel)
  log.addHandler(sysoutLogHandler)
# ------------------------------------------------------------------ #
# --------- End of setupLoggers function --------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------- Start of parseArgs function ---------------------------- #
# ------------------------------------------------------------------ #
def parseArgs():
  global hmcHost, cpcName
  global parName, nicName, devNum, nicDesc, vlanID, MACAdd, adaName, adaPort
  global logDir, logLevel, configFilename
  parser = argparse.ArgumentParser(description='Create a new NIC for partition')
  parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
  parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
  parser.add_argument('-parName','--parName',metavar='<the name of partition to be operated>',help='the name of partition to be operated')
  parser.add_argument('-nicName','--nicName',metavar='<the name of NIC to be operated>',help='the name of NIC to be operated')
  parser.add_argument('-devNum','--devNum',metavar='<the device number of the new created NIC>',
                      help='the device number of NIC to be operated (Possible range: 0001-ffff)')
  parser.add_argument('-nicDesc','--nicDesc',metavar='<the description of new created NIC>',help='the description of NIC to be operated')
  parser.add_argument('-vlanID','--vlanID',metavar='<the VLAN ID of the new created NIC>',help='the VLAN ID of the new created NIC (Possible range: 1-4094)')
  parser.add_argument('-MACAdd','--MACAdd',metavar='<the MAC Address of the new created NIC>',help='the MAC Address of the new created NIC (Example: 02:ff:12:34:56:78')
  parser.add_argument('-adaName','--adaName',metavar='<the name of the backing adapter>',help='the name of the backing adapter')
  parser.add_argument('-adaPort','--adaPort',metavar='<the port of the backing adapter>',help='the port of the backing adapter')  
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
    print exc.message
    raise exc
# CPC name 
  _cpcName = assertValue(pyObj=args, key='cpcName', listIndex=0, optionalKey=True)
  cpcName = checkValue('cpcName', _cpcName, cpcName)
  if cpcName == None:
    exc = HMCException("checkParams", "You should specify CPC name")
    print exc.message
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
  print("\tpartition\t%s"%parName)
  print("\t---- <Partition Settings> ----")
  print("\tNIC name\t%s"%nicName)
  print("\tAdapter name\t%s"%adaName)
  print("\tAdapter port\t%s"%adaPort)
  print("\tDevice Number\t%s"%devNum)
  print("\tNIC Description\t%s"%nicDesc)
  print("\tvlanID (unsupported)\t%s"%vlanID)
  print("\tMAC Address (unsupported)\t%s"%MACAdd)
# ------------------------------------------------------------------ #
# --------- End of printParams function ---------------------------- #
# ------------------------------------------------------------------ #



# main function
hmc = None
success=True

try:
  parseArgs()
  setupLoggers(logDir=logDir, logLevel=logLevel)
  
  print "******************************"
  msg = "Create new NIC in the partition"
  print msg  
  printParams()
  print "******************************"

  # Access HMC system and create HMC connection 
  hmc = createHMCConnection(hmcHost=hmcHost)
  cpc = selectCPC(hmc, cpcName)
  cpcURI = assertValue(pyObj=cpc, key=KEY_CPC_URI)
  cpcName = assertValue(pyObj=cpc, key=KEY_CPC_NAME)
  cpcStatus = assertValue(pyObj=cpc, key=KEY_CPC_STATUS)
  
  # Get CPC UUID
  cpcID = cpcURI.replace('/api/cpcs/','')
  
  sguri = selectStorageGroup(hmc, "T90-UBUNTU-19.10_Boot_Signed_SG")
  print "sguri = " + sguri
  
  #sgobj = getStorageGroupProperties(hmc, sgURI=sguri)
  #print "sgobj = " + sgobj

except Exception as exc:
  print exc
  
finally:
  # cleanup
  if hmc != None:
    hmc.logoff()
