'''
Created on Sep 23, 2015
@author: sijun
'''
import httplib, os, time, ssl, socket,json
from prsm2api import *
from wsaconst import *
import hmcUtils
import argparse
import datetime, readConfig, logging


# hmc and CPC
hmcHost = None
cpcName = None

# configuration file
configFilename = '/SystemzSolutionTest/prsm2ST/listPartitionsInfo.cfg'

# common logging objects
logDir = None
logLevel = None

# log levels
sysoutLogLevel = logging.ERROR
defaultLogLevel = logging.INFO
logLevel = defaultLogLevel

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

# ------------------------------------------------------------------ #
# --------- Start of parseArgs function ---------------------------- #
# ------------------------------------------------------------------ #

def parseArgs():
  

  global hmcHost, cpcName

  global logDir, logLevel, configFilename
  parser = argparse.ArgumentParser(description='delete prsm2 partition')
  
 
  parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
  parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
 
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

# print input parameters
def printParams():
  print("\tParameters were input:")
  print("\tHMC system IP\t%s"%hmcHost)
  print("\tCPC name\t%s"%cpcName)
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
  
cpcNames=[]
cpcURIs=[]
cpcStatuses=[]
wholeParNamesList=[]
wholeParURIsList=[]
wholeParStatusList=[]
sortedWholeParNamesList=[]
sortedWholeParURIsList=[]
sortedWholeParStatusList=[]
userid= 'ensadmin'
password='password'


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
msg = "list PRSM2 partitions"
log.info(msg)
print msg  
printParams()
print "******************************" 
  
#make the connection and get api-session ID
hmcConn=httplib.HTTPSConnection(hmcHost,'6794')
headers={"Content-type":"application/json","Accept":"*/*"}
body = '{"userid":"%s", "password":"%s"}'%(userid,password)

try:
  log.info('prepare to connect to HMC')        
  hmcConn.request('POST','/api/session',body,headers)
  response=hmcConn.getresponse()
  log.info('connect HMC complete')
except Exception as exc:
  log.info('connect to HMC failed')  
  exc = HMCException("connect to HMC", 
                         "connect to HMC failed", 
                         origException=exc)
  raise exc  
respBody=response.read()
#decode json object to python object and get the value of key 'api-session'
decode=json.loads(respBody)
sessionID=decode['api-session']
headers["X-API-Session"] = sessionID

try:                  
  #get cpcs List
  log.info('prepare to get cpcs')
  hmcConn.request('GET', '/api/cpcs', None, headers)
  response = hmcConn.getresponse()
  respBody=response.read()
  #decode the response to python object
  decode=json.loads(respBody)
  #get the cpcs in the response,the key is 'cpcs'
  cpcs= decode['cpcs']
  log.info('get cpcs complete')
except Exception as exc:
  log.info('get cpcs failed')  
  exc = HMCException("get cpcs list", 
                         "connect to HMC failed", 
                         origException=exc)
  raise exc   
                         
              
#extract the information from cpcs
for cpcInfo in cpcs:
  _cpcName = cpcInfo['name']
  _cpcURI = cpcInfo['object-uri']
  _cpcStatus = cpcInfo['status']
  # append cpc name , URI, Status into array
  cpcURIs.append(_cpcURI)
  cpcNames.append(_cpcName)
  cpcStatuses.append(_cpcStatus)
#  
#get cpc status,in the case I tested yesterday, I used 'S90'
if cpcName in cpcNames:
  index = cpcNames.index(cpcName)
  cpcURI = cpcURIs[index]
  cpcStatus = cpcStatuses[index]
else :
  exc= HMCException("get cpcs list", 
                         "your CPC name do not exist")
  raise exc      
              
#cpcID is a long string
cpcID = cpcURI.replace('/api/cpcs/','')
              
#get partitions in this cpc(cpcID) 
try:
  log.info('prepare to get partitions')  
  hmcConn.request('GET','/api/cpcs/%s/partitions'%cpcID,None,headers)
  response=hmcConn.getresponse()
  respBody=response.read()
  log.info('get partitions finished')
except Exception as exc:
  log.info('get partitions failed')  
  exc= HMCException("get partitions", 
                         "get partitions failed")
  raise exc    
  
#decode the response to python object
decode=json.loads(respBody)
  
#get partitions' information in the respBody, the key is 'partitions'
decode=decode['partitions']
partitions=decode
print '\n\npartitions on %s:'%cpcName
for parInfo in partitions:
  name=parInfo['name']
  name=name.encode("utf-8")
  uri=parInfo['object-uri']
  uri=uri.encode("utf-8")
  status=parInfo['status']
  status=status.encode("utf-8") 
  wholeParNamesList.append(name)
  wholeParURIsList.append(uri)
  wholeParStatusList.append(status)

sortedWholeParNamesList=sorted(wholeParNamesList, key=str.upper)
num=len(wholeParNamesList)
index=0
while index<num:
  sortedIndex=wholeParNamesList.index(sortedWholeParNamesList[index])
  sortedWholeParURIsList.append(wholeParURIsList[sortedIndex])
  sortedWholeParStatusList.append(wholeParStatusList[sortedIndex])
  index+=1  

index=0  
print 'Partition-name',35*' ','Partition-UUID',30*' ','Partition-Status' 
while index<num:
  nameLength=len(sortedWholeParNamesList[index]) 
  print 2*' ',sortedWholeParNamesList[index],(30-nameLength)*' ',sortedWholeParURIsList[index],11*' ',sortedWholeParStatusList[index]
  index+=1
print "\nTotally <%s> partitions on %s \n"%(num,cpcName)  
#   
#   

#extract the valid partitions in respBody(),in yesterday's case,the stopped state is the valid partitions,validStateParNamesList= ['KVMP55','KVMP56','KVMP57','KVMP58','KVMP59','KVMP60']
              
# for validStateParName in validStateParNamesList:
#   index=wholeParNamesList.index(validStateParName)
#   validStateParURIsList.append(wholeParURIsList[index])
# 
#       
# print validStateParURIsList       
# 
#               
# #delete the valid partitions
#   
# num=len(validStateParNamesList)
# if num!=0:
#   index=0
#   while index<num:
#      
#     hmcConn.request('DELETE',validStateParURIsList[index],None,headers)
#     response=hmcConn.getresponse()
#     response.read()
#     print 'Response status code: ',response.status
#     index+=1  
#     time.sleep(5)
# else: 
#   print "\nThere is no valid partition name that can be deleted."
