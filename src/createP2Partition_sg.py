#! /usr/bin/env python 
# Created by Daniel Wu (yongwubj@cn.ibm.com) at 10/16/2015

# imports
from prsm2api import *
from wsaconst import *
import hmcUtils
import argparse
import datetime, readConfig, logging
import string

# Default values

# hmc and CPC
hmcHost = None
cpcName = None

# partition params
parType = None
testEnv = None
parNum = None

procMode = None
procType = None
procNum = None

initMem = None
maxMem = None

autoStart = None
bootDev = None

# common logging objects
log = logging.getLogger(HMC_API_LOGGER)
logDir = None
logLevel = None


# log levels
sysoutLogLevel = logging.ERROR
defaultLogLevel = logging.INFO
logLevel = defaultLogLevel

# configuration file
configFilename = '/SystemzSolutionTest/prsm2ST/createP2Partition.cfg'

# ------------------------------------------------------------------ #
# --------- Start of parseArgs function ---------------------------- #
# ------------------------------------------------------------------ #

def parseArgs():
  global hmcHost, cpcName, parType, testEnv, parNum
  global procMode, procType, procNum, initMem, maxMem
  global autoStart, bootDev
  global logDir, logLevel, configFilename
  parser = argparse.ArgumentParser(description='create prsm2 partition')
  parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
  parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
  parser.add_argument('-parType', '--parType', metavar='<partition type>', help='set kvm or lnx partition')
  parser.add_argument('-env', '--testEnv', metavar='<test env>', help='set sandbox, test or prod')
  parser.add_argument('-parNum', '--parNum', metavar='<number of partition>', help='set number of partition in an integer')
  parser.add_argument('-procMode', '--procMode', metavar='<Processor mode>', help='processor mode can be shared or dedicated')
  parser.add_argument('-procType', '--procType', metavar='<processor type>', help='set IFL or CP as processor type')
  parser.add_argument('-procNum', '--procNum', metavar='<number of processor>', help='set reasonable number of processor')
  parser.add_argument('-initMem', '--initMem', metavar='<initial memory size>', help='set initial memory size in Mb unit')
  parser.add_argument('-maxMem', '--maxMem', metavar='<maximum memory size>', help='set maximum memory size in Mb unit')
  parser.add_argument('-autoStart', '--autoStart', metavar='<auto start partition>', help='Set true or flase for this option')
  parser.add_argument('-bootDev', '--bootDev', metavar='<boot option>', help='set boot option for the partition')
  parser.add_argument('-logLevel', '--logLevel', metavar='<log level name>', help='Logging level. Can be one of {debug, info, warn, error, critical}', 
                      choices=['debug', 'info', 'warn', 'error', 'critical'])
  parser.add_argument('-logDir', '--logDir', metavar='<log directory>', help='set log directory')
  parser.add_argument('-c', '--config', metavar='<file name>', help='Configuration file name (path)')
  args = vars(parser.parse_args())
  
# HMC host
  _hmcHost = assertValue(pyObj=args, key='hmc', 
                         listIndex=0, optionalKey=True)
  hmcHost = checkValue('hmcHost', _hmcHost , hmcHost)
# CPC name 
  _cpcName = assertValue(pyObj=args, key='cpcName', 
                         listIndex=0, optionalKey=True)
  cpcName = checkValue('cpcName', _cpcName, cpcName)
# Partition type
  _parType = assertValue(pyObj=args, key='parType', 
                         listIndex=0, optionalKey=True)
  parType = checkValue('parType', _parType, parType)
# Test environment
  _testEnv = assertValue(pyObj=args, key='testEnv', 
                         listIndex=0, optionalKey=True)
  testEnv = checkValue('testEnv', _testEnv, testEnv)
# Partition number 
  _parNum = assertValue(pyObj=args, key='parNum', 
                         listIndex=0, optionalKey=True)
  if _parNum != None:
   parNum = checkValue('parNum', _parNum, parNum)
   
# Processor mode
  _procMode = assertValue(pyObj=args, key='procMode', 
                         listIndex=0, optionalKey=True)
  if _procMode != None:
   procMode = checkValue('procMode', _procMode, procMode)

# processor type
  _procType = assertValue(pyObj=args, key='procType',
                      listIndex=0, optionalKey=True)
  procType = checkValue('procType', _procType, procType)
  
# processor number
  _procNum = assertValue(pyObj=args, key='procNum',
                      listIndex=0, optionalKey=True)
  procNum = checkValue('procNum', _procNum, procNum, valueType=int)

# initial memory
  _initMem = assertValue(pyObj=args, key='initMem', 
                           listIndex=0, optionalKey=True)
  initMem = checkValue('initMem', _initMem, initMem, valueType=int)
  
# maximum memory
  _maxMem = assertValue(pyObj=args, key='maxMem', 
                           listIndex=0, optionalKey=True)
  maxMem = checkValue('maxMem', _maxMem, maxMem, valueType=int)

# Auto start 
  _autoStart = assertValue(pyObj=args, key='autoStart', 
                           listIndex=0, optionalKey=True)
  autoStart = checkValue('autoStart', _autoStart, autoStart, valueType=bool)
  
# Boot device
  _bootDev = assertValue(pyObj=args, key='bootDev', 
                           listIndex=0, optionalKey=True)
  bootDev = checkValue('bootDev', _bootDev, bootDev)
  
# log
  _logDir = assertValue(pyObj=args, key='logDir', 
                       listIndex=0, optionalKey=True)
  logDir = checkValue('logDir', _logDir, logDir)
  
  _logLevel = assertValue(pyObj=args, key='logLevel', 
                         listIndex=0, optionalKey=True)
  logLevel = checkValue('logLevel', _logLevel, logLevel)
# configuration file name
  configFile = assertValue(pyObj=args, key='config', 
                           listIndex=0, optionalKey=True)
  configFilename = checkValue('configFilename', configFile, configFilename)
# ------------------------------------------------------------------ #
# --------- End of parseArgs function ------------------------------ #
# ------------------------------------------------------------------ #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------- Start of loadConfig function --------------------------- #
# ------------------------------------------------------------------ #
def loadConfig(
               configFile          # configuration file name (string)
               ):
  '''
    - Loads configuration data from .cfg file
    - @param configFile:    configuration file name (string)
    - @param printConfig:   print loaded data table (boolean)
  '''
  global hmcHost, cpcName, parType, testEnv, parNum
  global procMode, procType, procNum, initMem, maxMem
  global autoStart, bootDev
  global logDir, logLevel
  
# load settings from configuration file
  configDict = readConfig.readConfig(fileName=configFilename)
# load top section data
  cmnSect = assertValue(pyObj=configDict, 
                        key=readConfig.COMMON_SECTION, 
                        optionalKey=True)
# and logging section data
  logSect = assertValue(pyObj=configDict, 
                        key=readConfig.LOGGING_SECTION, 
                        optionalKey=True)
# HMC host name
  if hmcHost == None:
    _hmcHost = assertValue(pyObj=cmnSect, key='hmc-host', 
                              listIndex=0, optionalKey=True)
    hmcHost = checkValue('hmcHost', _hmcHost, None)
    
# CPC name
  if cpcName == None:
    _cpcName = assertValue(pyObj=cmnSect, key='cpc-name', 
                          listIndex=0, optionalKey=True)
    cpcName = checkValue('cpcName', _cpcName, None)
    
# Partition type
  if parType == None:
    _parType = assertValue(pyObj=cmnSect, key='par-type', 
                             listIndex=0, optionalKey=True)
    parType  = checkValue('parType', _parType, None)

# Test env
  if testEnv == None:
    _testEnv = assertValue(pyObj=cmnSect, key='test-env', 
                             listIndex=0, optionalKey=True)
    testEnv  = checkValue('testEnv', _testEnv, None)
    
# Partition number
  if parNum == None:
    _parNum = assertValue(pyObj=cmnSect, key='par-num', 
                             listIndex=0, optionalKey=True)
    parNum  = checkValue('parNum', _parNum, None, valueType=int)

# Processor Mode
  if procMode == None:
    _procMode = assertValue(pyObj=cmnSect, key='processor-mode', 
                          listIndex=0, optionalKey=True)
    procMode = checkValue('procMode', _procMode, None)
    
# Processor Type
  if procType == None:
    _procType = assertValue(pyObj=cmnSect, key='processor-type', 
                          listIndex=0, optionalKey=True)
    procType = checkValue('procType', _procType, None)

# Processor number 
  if procNum == None:
    _procNum = assertValue(pyObj=cmnSect, key='processor-num',
                          listIndex=0)
    procNum = checkValue('procNum', _procNum, None, valueType=int)
    
# Initial memory (xxx Mb)
  if initMem == None:
    _initMem = assertValue(pyObj=cmnSect, key='init-mem',
                          listIndex=0, optionalKey=True)
    initMem = checkValue('initMem', _initMem, None, valueType=int)
    
# Maximum memory
  if maxMem == None:
    _maxMem = assertValue(pyObj=cmnSect, key='max-mem',
                          listIndex=0, optionalKey=True)
    maxMem = checkValue('maxMem', _maxMem, None, valueType=int)
    
# auto start 
  if autoStart == None:
    _autoStart = assertValue(pyObj=cmnSect, key='auto-start',
                          listIndex=0, optionalKey=True)
    autoStart = checkValue('autoStart', _autoStart, defValue=False, valueType=bool)
    
# boot device
  if bootDev == None:
    _bootDev = assertValue(pyObj=cmnSect, key='boot-dev',
                          listIndex=0, optionalKey=True)
    bootDev = checkValue('bootDev', _bootDev, None)

# logging 
  if logDir == None:
    _logDir = assertValue(pyObj=logSect, key='log-dir', 
                         listIndex=0, optionalKey=True)
    logDir = checkValue('logDir', _logDir, None)
    
  if logLevel == None:
    _logLevel = assertValue(pyObj=logSect, key='log-level', 
                           listIndex=0, optionalKey=True)
    logLevel = checkValue('logLevel', _logLevel, None)
    
# ------------------------------------------------------------------ #
# --------- End of loadConfig function ----------------------------- #
# ------------------------------------------------------------------ #


# print input parameters
def printParams():
  print("\tParameters were input:")
  print("\tHMC system IP\t%s"%hmcHost)
  print("\tCPC name\t%s"%cpcName)
  print("\tTest environment\t%s"%testEnv)
  print("\tPartition type\t%s"%parType)
  print("\tNumber of Partitions will be created\t%s"%parNum)
  print("\t---- <Partition Settings> ----")
  print("\tProcessor mode\t%s"%procMode)
  print("\tProcessor Type\t%s"%procType)
  print("\tNumber of Processor\t%s"%procNum)
  print("\tInitial memory size\t%s"%initMem)
  print("\tMaximum memory size\t%s"%maxMem)
  print("\tBoot option\t%s"%bootDev)
  print("\tAuto start\t%s"%autoStart)
  print("\tPath to save logs\t%s"%logDir)

# ------------------------------------------------------------------ #
# --------- Start of checkParams function -------------------------- #
# ------------------------------------------------------------------ #
# - Checks if all necessary parameters were entered
# ------------------------------------------------------------------ #
def checkParams(
                silentMode
                ):
  global hmcHostname, VSFastName, VSModrName, nodeName, blade2Validate, logDir
  if hmcHostname == None:
    exc = HMCException("checkParams", 
                       "You should specify HMC Host name/ip address")
    raise exc
  if len(VSFastName) < 1:
    exc = HMCException("checkParams", 
                       "You should specify List of Virtual Server name for Fastest SC")
    raise exc
  if len(VSModrName) < 1:
    exc = HMCException("checkParams", 
                       "You should specify List of Virtual Server name for Moderate SC")
    raise exc
  if nodeName == None:
    exc = HMCException("checkParams", 
                       "You should specify Node name")
    raise exc
  if blade2Validate == None:
    exc = HMCException("checkParams", 
                       "You should specify Blade name")
    raise exc
# ------------------------------------------------------------------ #
# --------- End of checkParams function ---------------------------- #
# ------------------------------------------------------------------ #

# --------- Start of setupLoggers function ------------------------- #
# ------------------------------------------------------------------ #
# - Configures loggers for this script
# ------------------------------------------------------------------ #
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
# -------------- Start of getCPCsList function --------------------- #
# ------------------------------------------------------------------ #
def getCPCsList(hmcConn):
  log.debug("Entered")
  try:
    URI = WSA_URI_CPCS
    # get CPCs list
    return getHMCObjectList(hmcConn, URI, 
                            "List CPCs", 
                            "cpcs", 
                            httpBadStatuses = [400])
  except HMCException as exc: # raise HMCException
    exc.setMethod("getCPCsList")
    raise exc
  finally:
    log.debug("Completed")
# ------------------------------------------------------------------ #
# -------------- End of getCPCsList function ----------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# -------------- Start of selectCPC function ----------------------- #
# ------------------------------------------------------------------ #
def selectCPC(hmcConn, 
              cpcName=None):
  log.debug("Entered")
  try:
    log.debug("Getting CPCs list..")
# check input parameters
    if hmcConn == None:
      exc = HMCException("selectCPC", 
                         "You should specify hmcConn parameter!")
      raise exc
  # get CPCs list 
    cpcs = getCPCsList(hmcConn)
  # check CPCs list
    if len(cpcs) == 0:
      if cpcName != None:
        msg = "No such CPC %s. Exiting..."%(cpcName)
      else:
        msg = "No CPC found. Exiting..."
      log.warning(msg)
      return None
  
  # prepare CPCs list..
    cpcURIs = []
    cpcNames = []
    cpcStatuses = []
    for cpcInfo in cpcs:
      _cpcName = assertValue(pyObj=cpcInfo, key='name')
      _cpcURI = assertValue(pyObj=cpcInfo, key='object-uri')
      _cpcStatus = assertValue(pyObj=cpcInfo, key='status')
      # append cpc name , URI, Status into array
      cpcURIs.append(_cpcURI)
      cpcNames.append(_cpcName)
      cpcStatuses.append(_cpcStatus)
      
    if cpcName != None:
      if cpcName in cpcNames:
        index = cpcNames.index(cpcName)
        cpcURI = cpcURIs[index]
        cpcStatus = cpcStatuses[index]
      else:
        exc = HMCException("selectCPC", 
                           "Cannot find CPC '%s' in available CPCs list %s!"%(cpcName,cpcNames))
        raise exc
     
  except HMCException as exc:   # raise HMCException
    exc.setMethod("selectCPC")
    raise exc
  except Exception as exc:
    exc = HMCException("selectCPC", 
                       "An exception catched while selecting CPC", 
                        origException=exc)
    raise exc
  finally:
    log.debug("Completed")
  return {KEY_CPC_NAME: cpcName, KEY_CPC_URI: cpcURI, KEY_CPC_STATUS: cpcStatus}

# ------------------------------------------------------------------ #
# ---------------- End of selectCPC function ----------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ------- Start of getCPCPartitionsList function ------------------- #
# ------------------------------------------------------------------ #
def getCPCPartitionsList(hmcConn, 
                         cpcID
                         ):
  log.debug("Entered")
  try:
  # get partition list of a cpc
    return getHMCObjectList(hmcConn, 
                            WSA_URI_PARTITIONS_CPC%cpcID, 
                            "List Partitions of a CPC", 
                            "partitions", 
                            httpBadStatuses = [400])
  except HMCException as exc:   # raise HMCException
    exc.setMethod("getCPCPartitionsList")
    raise exc
  finally:
    log.debug("Completed")
# ------------------------------------------------------------------ #
# --------- End of getCPCPartitionsList function ------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------- Start of createPartitionTemplate function -------------- #
# ------------------------------------------------------------------ #
def createPartitionTemplate(parName,
                            procMode,
                            procType,
                            procNum,
                            initMem,
                            maxMem,
                            autoStart,
                            bootDev
                            ):
  log.debug("Entered")
  parDesc = 'Created from API'
  parTempl = dict()
  if procType == 'IFL':
    procNumKey = 'ifl-processors'
  elif procType == 'CP':
    procNumKey = 'cp-processors'
  else:
    exc = HMCException("createPartitionTemplate",
                       "This processor type [%s] is not supported now"%procType)
    raise exc
  # Create partition template dictionary
  parTempl['name'] = parName
  parTempl['description'] = parDesc
  parTempl['processor-mode'] = procMode
  parTempl[procNumKey] = procNum
  parTempl['initial-memory'] = initMem
  parTempl['maximum-memory'] = maxMem
  parTempl['auto-start'] = autoStart
  parTempl['boot-device'] = bootDev
  
  return parTempl   
# ------------------------------------------------------------------ #
# --------- End of createPartitionTemplate function ---------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# -------------- Start of createPartition function ----------------- #
# ------------------------------------------------------------------ #
def createPartition(hmcConn, # HMCConnection object 
                   cpcID,   # CPC ID
                   parTempl  # Partition object (stored in JSON notation) to be used as a template
                   ):
  log.debug("Entered")
  try:
  # prepare HTTP body as JSON
    httpBody = json.dumps(parTempl)
  # create workload
    resp = getHMCObject(hmcConn, 
                        WSA_URI_PARTITIONS_CPC%cpcID, 
                        "Create Partition", 
                        httpMethod = WSA_COMMAND_POST, 
                        httpBody = httpBody, 
                        httpGoodStatus = 201,           # HTTP created
                        httpBadStatuses = [400,403,404])
    return assertValue(pyObj=resp, key='object-uri')
  except HMCException as exc:   # raise HMCException
    exc.setMethod("createPartition")
    raise exc
  finally:
    log.debug("Completed")
# ------------------------------------------------------------------ #
# --------- End of createWorkload function ------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------- Start of getPartitionProperties function --------------- #
# ------------------------------------------------------------------ #
def getPartitionProperties(hmcConn,
                           parID=None,
                           parURI=None):
  log.debug("Entered")
  try:
    # check input params
    if parURI != None:
      URI = parURI
    elif parID != None:
      URI = WSA_URI_PARTITION%parID
    else:
      exc = HMCException("getPartitionProperties", 
                        "You should specify either parURI or parID parameters")
      raise exc
    # get partition properties
    return getHMCObject(hmcConn, URI, 
                        "Get Partition Properties")
  except HMCException as exc:   # raise HMCException
    exc.setMethod("getPartitionProperties")
    raise exc
  finally:
    log.debug("Completed")
# ------------------------------------------------------------------ #
# ----------- End of getPartitionProperties function --------------- #
# ------------------------------------------------------------------ #
   
# Start _Main_ from here
hmc = None
success = True
parURIsList = list()  # list all partition URIs

try:
  parseArgs()  
  # load configuration data from configuration file
  try:
    loadConfig(configFile=configFilename)
  except IOError as exc:
    print"Cannot load configuration file [%s]: %s"%(configFilename, exc)
  # setup loggers
  setupLoggers(logDir=logDir, logLevel=logLevel)
  msg= "******************************"
  log.info(msg)
  print msg
  msg = "Create PRSM2 partitions"
  log.info(msg)
  print msg  
  printParams()
  
  # Access HMC system and create HMC connection 
  hmc = createHMCConnection(hmcHost=hmcHost)
  cpc = selectCPC(hmc, cpcName)
  cpcURI = assertValue(pyObj=cpc, key=KEY_CPC_URI)
  cpcName = assertValue(pyObj=cpc, key=KEY_CPC_NAME)
  cpcStatus = assertValue(pyObj=cpc, key=KEY_CPC_STATUS)
  # Get CPC UUID
  cpcID = cpcURI.replace('/api/cpcs/','')
       
  # Construct partition name prefix like "KVMP01"
  if parType in ['kvm','KVM']:
    parT = 'KVM'
  elif parType in ['linux','lnx']:
    parT = 'LNX'
  else:
    exc = HMCException("determine Partition Type",
                       "This partition type [%s] is not supported now"%parType)
    raise exc
  if testEnv in ['sandbox', 'test', 'production']:
    testE =  testEnv[0:1].upper()
  else:     
    exc = HMCException("determine test environment",
                       "This test env [%s] is not supported now"%testEnv)
    raise exc  
  parNamePre = parT + testE

  # Get existing partitions name list
  parUsedNames = []
  parRemained = []
  parCreated = []
  ret = getCPCPartitionsList(hmc, cpcID)
  for parInfo in ret:
    parUsedNames.append(assertValue(pyObj=parInfo,key='name'))
    
  # create partitions
  parNumb = int(parNum)
  i=1
  while i <= parNumb :

    if i >= 10:
      parIndex = '%d'%i 
    elif i < 10:
      parIndex = '0'+ '%d'%i
    parName = parNamePre + parIndex

    if parName in parUsedNames:
     # print("\nPartition <%s> was already created, proceed next one ..."%parName)
      parNumb+=1
      i+=1
      parRemained.append(parName)
    else:
      # create partition template
      parTemp = createPartitionTemplate(parName,procMode,procType,procNum,initMem,maxMem,autoStart,bootDev)
      # create partition 
      partRet = createPartition(hmc, cpcID, parTemp)
      i+=1
      parCreated.append(parName)
      print("\nPartition <%s> was created: %s"%(parName, partRet))
      
   # Summary 
  if parCreated != None:
    parTotal = len(parCreated)
    msg = "\n Total <%s> partitions have been created and please verify them from HMC"%parTotal
    print msg
  else:
    success = False
    print "Create partition(s) failed"

except hmcUtils.HMCException as hmcExc:
  success = False
  msg=  "Script terminated!"
  log.info(msg)
  print msg
  hmcExc.printError()
except Exception as exc:
  print exc
  success = False
  msg=  "Script terminated!"
  log.info(msg)
  print msg
  log.error('Exception %s happened: %s', type(exc), exc)
  msg="trace=%s"%(traceback.format_tb( sys.exc_info()[2] ))
  log.info(msg)
  print msg
finally:
# cleanup
  if hmc != None:
    hmc.logoff()
  if success:
    msg=  "Script finished successfully."
    log.info(msg)
    print msg
  else:
    exit(1)