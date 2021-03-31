#! /usr/bin/env python

# imports
from prsm2api import *
from wsaconst import *
import hmcUtils
import argparse
import datetime, readConfig, logging
import string
import threading  
import time

# hmc and CPC
hmcHost = None
cpcName = None

# parRange
parRange= None

# configuration file
configFilename = '/SystemzSolutionTest/prsm2ST/deletePartition.cfg'

# common logging objects
logDir = None
logLevel = None

# log levels
sysoutLogLevel = logging.ERROR
defaultLogLevel = logging.INFO
logLevel = defaultLogLevel

# indicate that whether the whole delete process terminates correctly
boolDelete=True

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

# print input parameters
def printParams():
  print("\tParameters were input:")
  print("\tHMC system IP\t%s"%hmcHost)
  print("\tCPC name\t%s"%cpcName)
  print("\tpartition range\t%s"%parRange)
  print("\tPath to save logs\t%s"%logDir)
  
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
  global hmcHost, cpcName
  global parRange
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
    
# CPC name
  if parRange == None:
    _parRange = assertValue(pyObj=cmnSect, key='parRange', 
                          listIndex=0, optionalKey=True)
    parRange = checkValue('parRange', _parRange, None)

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

# ------------------------------------------------------------------ #
# --------- Start of parseArgs function --------------------------- #
# ------------------------------------------------------------------ #

def parseArgs():
  
  global hmcHost, cpcName
  global parRange
  global logDir, logLevel, configFilename
  parser = argparse.ArgumentParser(description='delete prsm2 partition')
  
  parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
  parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
  parser.add_argument('-parRange','--parRange',metavar='<the range of partitions to be deleted>',help='the range of partitions to be deleted')
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
# partion range
  _parRange= assertValue(pyObj=args, key='parRange', 
                         listIndex=0, optionalKey=True)
  parRange= checkValue('parRange', _parRange , parRange)
# log
  _logDir = assertValue(pyObj=args, key='logDir', 
                       listIndex=0, optionalKey=True)
  _logLevel = assertValue(pyObj=args, key='logLevel', 
                         listIndex=0, optionalKey=True)
  logLevel = checkValue('logLvl', _logLevel, logLevel)
# configuration file name
  configFile = assertValue(pyObj=args, key='config', 
                           listIndex=0, optionalKey=True)
  configFilename = checkValue('configFilename', configFile, configFilename)

# ------------------------------------------------------------------ #
# --------- End of parseArgs function ------------------------------ #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------- Start of deletePartition function ---------------------- #
# ------------------------------------------------------------------ #  

def deletePartition(hmcConn,
                   parURI=None,
                   parID=None,
                   ):
  log.debug("Entered")
  global boolDelete
  
  try:
    
    if parURI==None:  
      if parID != None:
        URI = "%s"%(WSA_URI_PARTITION%parID)
      else:
        exc = HMCException("deletePartition", 
                          "You should specify either parURI or parID parameters")
        raise exc
    else:
      URI=parURI
    
  # delete partition
    getHMCObject(hmcConn,URI, 
                 "Delete Partition", 
                 httpMethod = WSA_COMMAND_DELETE, 
                 httpGoodStatus = 204,           # HTTP accepted
                 httpBadStatuses = [400,403,404,503])
    boolDelete=True
  except HMCException as exc:   # raise HMCException
    boolDelete=False  
    exc.setMethod("deletePartition")
    raise exc
  except Exception:
      boolDelete=False
      exc = HMCException("getHMCObject", 
                       "Unknown failure happened", 
                        httpResponse=response, 
                        origException=exc)
      raise exc
  finally:
    log.debug("Completed")

# ------------------------------------------------------------------ #
# --------- End of deletePartition function ---------------------- #
# ------------------------------------------------------------------ #  
    
#The delePartition class is derived from the class threading.Thread      
class delePartition(threading.Thread): 
  def __init__(self, hmc,validParNamesList, validParURIsList):  
    threading.Thread.__init__(self)  
    self.validParNamesList= validParNamesList
    self.validParURIsList = validParURIsList 
    self.thread_stop = False  
        
  def run(self): #Overwrite run() method, put what you want the thread do here  
    for delPar in validParNamesList:
      index=validParNamesList.index(delPar)
      parURI=validParURIsList[index]
      deletePartition(hmc,parURI)    
    
# Start _Main_ from here
hmc = None
success=True

try :
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
  msg = "Delete PRSM2 partitions"
  log.info(msg)
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

  parRet = getCPCPartitionsList(hmc, cpcID)

  #All the partitions that you want to delete, but what you specified maybe not on the CPC or in the correct state to delete 
  wholeParNamesList = []
  
  #valide partition list that can be deleted, partition only in 'stopped' status can be deleted 
  stopedStateParNamesList=[]
  stopedStateParURIsList = []
  
  #Partitions that do not exist on the specified CPC among your input 
  notExistParNamesList=[]
  #Partitions that are not in the right state to delete among your input 
  wrongStateParNamesList=[]
  #valid Partitions that can be deleted
  validParNamesList=[]
  validParURIsList=[]
  
  for parInfo in parRet:    
    wholeParNamesList.append(assertValue(pyObj=parInfo, key='name'))
    if assertValue(pyObj=parInfo, key='status')=='stopped' :
      stopedStateParNamesList.append(assertValue(pyObj=parInfo, key='name'))
      stopedStateParURIsList.append(assertValue(pyObj=parInfo, key='object-uri'))
  
  #desolve parRange to seperate partitions
  if parRange!=None:
    delParList=parRange.split(',')
  else :
    exc = HMCException("deletePartition", 
                          "At least specify the partitions you want to delete. To do this, please input the value of 'parRange'.")
    raise exc
  prefix=None
  startNum=None
  endNum=None

  for delPar in delParList:
   
    if '-' in delPar:   
            
      delParList.remove(delPar)
      beginAndEndParNameList=delPar.split('-')
      prefix1=beginAndEndParNameList[0][0:-2]
      prefix2=beginAndEndParNameList[1][0:-2]
      if prefix1!=prefix2:
        exc = HMCException("deletePartition", 
                          "If you  use '-' in your parameter, you should specify the same name prefix on the both side of '-'")
        raise exc
      else:
        prefix=prefix1
      startNum=int(string.lstrip(beginAndEndParNameList[0][-2:],'0'))
      endNum= int(string.lstrip(beginAndEndParNameList[1][-2:],'0'))
      if startNum>endNum:
        startNum,endNum=endNum,startNum
              
      while startNum<=endNum:
        wholeName=prefix+"%02d"%startNum
        delParList.append(wholeName)
        startNum+=1
      delParList = list(set(delParList))
      delParList=sorted(delParList,key = str.upper)
       
  print '\nThese are the partitions you want to delete: %s'%delParList

  #select the valid partitions you can delete
  for delPar in delParList:
    if delPar not in wholeParNamesList:
      notExistParNamesList.append(delPar)
    else:
            
      if delPar in stopedStateParNamesList:
        index = stopedStateParNamesList.index(delPar)
        parURI = stopedStateParURIsList[index]  
        #deletePartition(hmc,parURI)
        validParNamesList.append(delPar)
        validParURIsList.append(parURI)
        
        #print "Delete partition '%s' request has been sent out"%delPar
      else:
        wrongStateParNamesList.append(delPar)  
     
  if len(notExistParNamesList)!=0:
    print ""   
    print "Partitions %s do not exist on the CPC:%s"%(notExistParNamesList,cpcName)
  
  if len(wrongStateParNamesList)!=0:
    print ""  
    print "Partitions %s are in the wrong state to be deleted"%wrongStateParNamesList
  
  #count the time that elapse
  timeCount=0
  waitIndicator=False
  if len(validParNamesList)!=0:
    
    #start the deletePartitin function in another thread
    delPar=delePartition(hmc,validParNamesList,validParURIsList)
    delPar.setDaemon(True)
    delPar.start()
  
    sys.stdout.write('\nStart to delete,please wait : ')
    sys.stdout.flush()

    while timeCount<300 and boolDelete!=False:
    
      sys.stdout.write('%3ds'%timeCount)
      sys.stdout.flush()
      waitIndicator=False  
        
      if timeCount%6==5:
        parRet = getCPCPartitionsList(hmc, cpcID)
        wholeParNamesList=[]  
        for parInfo in parRet:    
          wholeParNamesList.append(assertValue(pyObj=parInfo, key='name'))
        
        for parName in validParNamesList:
          if parName in wholeParNamesList:
            waitIndicator=True
            break
        if waitIndicator==False:
          break
    
      timeCount+=1
      time.sleep(1)
      sys.stdout.write('\b\b\b\b') 
      sys.stdout.flush()
    
    print ""
    if timeCount<300 and boolDelete!=False:
      print "\nDelete operation completes"
      print "\nThe following partitions have already been deleted: %s"%validParNamesList
    else :
      print "\ndeletion failure"
  else: 
    print "\nThere is no valid partition name that can be deleted."    
     
except hmcUtils.HMCException as hmcExc:
  success = False
  msg=  "\nScript terminated!"
  log.info(msg)
  print msg
  hmcExc.printError()
except Exception as exc:
  print exc
  success = False
  msg=  "\nScript terminated!"
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
    msg=  "\nScript finished successfully.\n"
    log.info(msg)
    print msg

  else:
    exit(1)









