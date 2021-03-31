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


#operation type
operType=None

# hmc and CPC
hmcHost = None
cpcName = None

# parRange
parRange= None

# configuration file
configFilename = '/SystemzSolutionTest/prsm2ST/startOrStopPartition.cfg'

# common logging objects
logDir = None
logLevel = None

# log levels
sysoutLogLevel = logging.ERROR
defaultLogLevel = logging.INFO
logLevel = defaultLogLevel

#All the partitions that you input, but what you specified may be not on the CPC or not in the correct state to operate
inputParNamesList = []
  
#whole partitions on the cpc you specified
wholeParNamesList=[]
wholeParURIsList = []
  
#stopped state partition list
stopedStateParNamesList=[]
stopedStateParURIsList = []
  
#active state partition list
activeStateParNamesList=[]
activeStateParURIsList=[]
 
#Partitions that are not in the right state to operate 
middleStateParNamesList=[]  

#Partitions that do not exist on the specified CPC among your input 
notExistParNamesList=[]
#Partitions that are not in the right state to operate among your input 
wrongStateParNamesList=[]
#valid Partitions that can be operated
validParNamesList=[]
validParURIsList=[]


#valid partition status list
validParStatusList=[]
#corretFinishedList:operation finished correctly
correctFinishedList=[]
#incorrectFinishedList:operation finished incorrectly
incorrectFinishedDic={}
#job URI list
jobURIsList=[]



# --------- Start of setupLoggers function ------------------------- #
# ------------------------------------------------------------------ #
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

# print input parameters
def printParams():
  print("\tParameters were input:")
  print("\tHMC system IP\t%s"%hmcHost)
  print("\tCPC name\t%s"%cpcName)
  print("\tpartition range\t%s"%parRange)
  print("\toperation type\t%s"%operType)
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
# --------- Start of parseArgs function ---------------------------- #
# ------------------------------------------------------------------ #

def parseArgs():
  
  global operType
  global hmcHost, cpcName
  global parRange
  global logDir, logLevel, configFilename
  parser = argparse.ArgumentParser(description='operate prsm2 partition')
  
  parser.add_argument('-operType','--operType',metavar='<operation type>', help='operation type start or stop')
  parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
  parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
  parser.add_argument('-parRange','--parRange',metavar='<the range of partitions to be operated>',help='the range of partitions to be operated')
  parser.add_argument('-logLevel', '--logLevel', metavar='<log level name>', help='Logging level. Can be one of {debug, info, warn, error, critical}', 
                      choices=['debug', 'info', 'warn', 'error', 'critical'])
  parser.add_argument('-logDir', '--logDir', metavar='<log directory>', help='set log directory')
  parser.add_argument('-c', '--config', metavar='<file name>', help='Configuration file name (path)')
  
  args = vars(parser.parse_args())

# operation type
  _operType = assertValue(pyObj=args, key='operType', 
                         listIndex=0, optionalKey=True)
  operType = checkValue('operType', _operType , operType)
  
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
# --------- Start of parse partition range function ---------------- #
# ------------------------------------------------------------------ #
def parsePartitionRange(parRange):
  global inputParNamesList    
  #desolve parRange to seperate partitions,and put it in the operation partitions name list operParList
  if parRange!=None:
    inputParNamesList=parRange.split(',')
  else :
    exc = HMCException("startOrStopPartition", 
                          "At least specify the partitions you want to operate. To do this, please input the value of 'parRange'.")
    raise exc
  prefix=None
  startNum=None
  endNum=None
  
  for inputPar in inputParNamesList:    
    if '-' in inputPar:         
      beginAndEndParNameList=inputPar.split('-')
      
      prefix1=beginAndEndParNameList[0][0:-2]
      prefix2=beginAndEndParNameList[1][0:-2]
      if prefix1!=prefix2:
        continue
      else:
        inputParNamesList.remove(inputPar)  
        prefix=prefix1
        
      startNum=int(string.lstrip(beginAndEndParNameList[0][-2:],'0'))
      endNum= int(string.lstrip(beginAndEndParNameList[1][-2:],'0'))
      if startNum>endNum:
        startNum,endNum=endNum,startNum
              
      while startNum<=endNum:
        wholeName=prefix+"%02d"%startNum
        inputParNamesList.append(wholeName)
        startNum+=1
        
      inputParNamesList = list(set(inputParNamesList))
      inputParNamesList=sorted(inputParNamesList,key = str.upper)

# ------------------------------------------------------------------ #
# --------- End of parse partition range function ------------------ #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of get states of partitions on CPC range function ---- #
# ------------------------------------------------------------------ #
def getPartitionsStatesOnCPC(hmc,cpcID):
  global wholeParNamesList,wholeParURIsList
  global stopedStateParNamesList,stopedStateParURIsList
  global activeStateParNamesList,activeStateParURIsList
  global middleStateParNamesList
       
  parRet = getCPCPartitionsList(hmc, cpcID)
    
  for parInfo in parRet:    
    wholeParNamesList.append(assertValue(pyObj=parInfo, key='name'))
    wholeParURIsList.append(assertValue(pyObj=parInfo, key='object-uri'))
    if assertValue(pyObj=parInfo, key='status')=='stopped' :
      stopedStateParNamesList.append(assertValue(pyObj=parInfo, key='name'))
      stopedStateParURIsList.append(assertValue(pyObj=parInfo, key='object-uri'))
    if assertValue(pyObj=parInfo, key='status')=='active' :
      activeStateParNamesList.append(assertValue(pyObj=parInfo, key='name'))
      activeStateParURIsList.append(assertValue(pyObj=parInfo, key='object-uri'))
  
  middleStateParNamesList=list(set(wholeParNamesList)-set(stopedStateParNamesList)-set(activeStateParNamesList))
# ------------------------------------------------------------------ #
# ----- End of get states of partitions on CPC range function ---- #
# ------------------------------------------------------------------ #

# main function
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
  msg = "startOrStop PRSM2 partitions"
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

    
  getPartitionsStatesOnCPC(hmc,cpcID)
  parsePartitionRange(parRange)
  
  notExistParNamesList=list(set(inputParNamesList)-set(wholeParNamesList))
  
  print 'These are the partitions you want to operate : ',inputParNamesList
  
  if len(notExistParNamesList)!=0:      
    print 'These partitions do not exist on %s : %s'%(cpcName,notExistParNamesList)

  if operType==None:
    exc = HMCException("startOrStopPartition", 
                          "Please specify the operation type.")
    raise exc
  elif operType=='start':
    #select the valid partitions you can start
    for inputPar in inputParNamesList:
      if inputPar in stopedStateParNamesList:            
        index = stopedStateParNamesList.index(inputPar)
        inputParURI = stopedStateParURIsList[index]           
        validParNamesList.append(inputPar)
        validParURIsList.append(inputParURI)
    invalidStateParNameList=[]
    invalidStateParNameList=list(set(inputParNamesList)-set(notExistParNamesList)-set(validParNamesList))
    if len(invalidStateParNameList)!=0:
      print 'These partitions are not in the correct status to start :',invalidStateParNameList  
    num=len(validParURIsList)
    
    if num!=0:
        
      for validPar in validParNamesList:
        index= validParNamesList.index(validPar)
        parURI=validParURIsList[index]
        jobURIsList.append(startPartition(hmc,parURI))

      
      time.sleep(1)
      intervalCount=0
      finishedCount=0
      while intervalCount!=120:          
        index=0
        while index<num:
          if validParNamesList[index] in correctFinishedList:
            sys.stdout.write('%s has been successfully started up!\r\n'%validParNamesList[index])
            sys.stdout.flush()
          elif validParNamesList[index] in incorrectFinishedDic.keys():
            sys.stdout.write(incorrectFinishedDic[validParNamesList[index]])
            sys.stdout.flush()
          else:         
            jobStatus = queryJobStatus(hmc, jobURI=jobURIsList[index])
            status = assertValue(pyObj=jobStatus, key='status')
            # check job status
            if status == JOB_STATUS_COMPLETE:
              finishedCount+=1  
              # job successfully completed -> check next job
              if assertValue(pyObj=jobStatus, key='job-status-code') == 200:
                correctFinishedList.append(validParNamesList[index])
                sys.stdout.write('%s has been successfully started up!\r\n'%validParNamesList[index])
                sys.stdout.flush() 
              # job failed
              else:
                vsName = validParNamesList[index]
                incorrectFinishedDic[vsName] = "%s start failed with job-status-code=[%s], job-reason-code=[%s]\r\n"%(
                                    vsName,                                                                              
                                    assertValue(pyObj=jobStatus, key='job-status-code'), 
                                    assertValue(pyObj=jobStatus, key='job-reason-code'))
                sys.stdout.write(incorrectFinishedDic[vsName])
                sys.stdout.flush()
            else:
              sys.stdout.write('%s is starting, please wait...:%ss\r\n'%(validParNamesList[index],intervalCount*5))
              sys.stdout.flush()
          index+=1
        print 'finishedCount : ',finishedCount,', num=',num  
        sys.stdout.write('*******************************************************\r\n')
        sys.stdout.flush()        
        if finishedCount==num:  
          break
        intervalCount+=1
        time.sleep(5)
      if len(correctFinishedList)!=0:
        print 'These paritions are correctly started up',sorted(correctFinishedList,key=str.upper)
      if len(list(set(validParNamesList).difference(set(correctFinishedList))))!=0:
        print 'These partitions are not correctly started up :',sorted(list(set(validParNamesList).difference(set(correctFinishedList))),key=str.upper)          
  
    else:
      print 'There are no valid partitions to start.'  
  
  elif operType=='stop':
    #select the valid partitions you can start
    for inputPar in inputParNamesList:
      if inputPar in activeStateParNamesList:            
        index = activeStateParNamesList.index(inputPar)
        inputParURI = activeStateParURIsList[index]           
        validParNamesList.append(inputPar)
        validParURIsList.append(inputParURI)
        
    invalidStateParNameList=[]
    invalidStateParNameList=list(set(inputParNamesList)-set(notExistParNamesList)-set(validParNamesList))
    if len(invalidStateParNameList)!=0:
      print 'These partitions are not in the correct status to stop :',invalidStateParNameList  
    
    num=len(validParURIsList)
    
    if num!=0:
        
      for validPar in validParNamesList:
        index= validParNamesList.index(validPar)
        parURI=validParURIsList[index]
        jobURIsList.append(stopPartition(hmc,parURI))

     
      time.sleep(1)
      intervalCount=0
      finishedCount=0
      while intervalCount!=120:          
        index=0
        while index<num:
          if validParNamesList[index] in correctFinishedList:
            sys.stdout.write('%s has been successfully stopped!\r\n'%validParNamesList[index])
            sys.stdout.flush()
          elif validParNamesList[index] in incorrectFinishedDic.keys():
            sys.stdout.write(incorrectFinishedDic[validParNamesList[index]])
            sys.stdout.flush()
          else:         
            jobStatus = queryJobStatus(hmc, jobURI=jobURIsList[index])
            status = assertValue(pyObj=jobStatus, key='status')
            # check job status
            if status == JOB_STATUS_COMPLETE:
              finishedCount+=1  

              if assertValue(pyObj=jobStatus, key='job-status-code') == 200:
                correctFinishedList.append(validParNamesList[index])
                sys.stdout.write('%s has been successfully stopped!\r\n'%validParNamesList[index])
                sys.stdout.flush()
              # job failed
              else:
                vsName = validParNamesList[index]
                incorrectFinishedDic[vsName] = "%s stop failed with job-status-code=[%s], job-reason-code=[%s]\r\n"%(
                                    vsName,                                                                              
                                    assertValue(pyObj=jobStatus, key='job-status-code'), 
                                    assertValue(pyObj=jobStatus, key='job-reason-code'))
                sys.stdout.write(incorrectFinishedDic[vsName])
                sys.stdout.flush()
            else:
              sys.stdout.write('%s is stopping, please wait...%ss\r\n'%(validParNamesList[index],intervalCount*5))
              sys.stdout.flush()
          index+=1                    
        sys.stdout.write("*******************************************************\r\n")
        sys.stdout.flush()
        if finishedCount==num:
          break
        intervalCount+=1
        time.sleep(5)
      if len(correctFinishedList)!=0:
        print 'These paritions are correctly stopped :',sorted(correctFinishedList,key=str.upper)
      if len(list(set(validParNamesList).difference(set(correctFinishedList))))!=0:
        print 'These partitions are not correctly stopped :',sorted(list(set(validParNamesList).difference(set(correctFinishedList))),key=str.upper) 
    else:
      print 'There is no valid partitions to stop.'  
  else:
    exc = HMCException("startOrStopPartition", 
                          "Please indicate the right operation.")
    raise exc  
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
