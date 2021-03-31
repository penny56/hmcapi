'''
created on 11/15/2017

This script intends to update Crypto Domain Configuration for target partition
@author: Daniel Wu <yongwubj@cn.ibm.com>
'''
from prsm2api import *
from wsaconst import *
import hmcUtils
import argparse
import datetime, readConfig, logging
import string

# hmc host IP and cpc name 
hmcHost = None
cpcName = None

# partition name (increase configuration only supports single partition)
parName = None

# Crypto Adapter name or list (M90 "CCA 0188 Z15B-03,CCA 01bc Z15B-19")

#Domain index 
domIndex=None

#Domain access mode <control or usage>
domAcesMode=None

# Logging params 
logDir = None
logLevel = None

# common logging objects
log = logging.getLogger(HMC_API_LOGGER)
logDir = None
logLevel = None

# log levels
sysoutLogLevel = logging.ERROR
defaultLogLevel = logging.INFO
logLevel = defaultLogLevel

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
    '''
    - parse arguments input for this script
    '''
    global hmcHost, cpcName
    global parName, domIndex, domAcesMode
    global logDir, logLevel
    parser = argparse.ArgumentParser(description="create zEDC virtual function for specified partitions")
    parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
    parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
    parser.add_argument('-parName','--parName',metavar='<partition name>',
                        help='set target partition name')
    parser.add_argument('-domIndex','--domIndex',metavar='<domain index number>',
                        help='select a value from 1 to 84')
    parser.add_argument('-domAcesMode','--domAcesMode',metavar='<Domain Access Mode>',
                        help='set mode as control or usage')
    parser.add_argument('-logLevel', '--logLevel', metavar='<log level name>',
                        help='Logging level. Can be one of {debug, info, warn, error, critical}',
                        choices=['debug', 'info', 'warn', 'error', 'critical'])
    parser.add_argument('-logDir', '--logDir', metavar='<log directory>', help='set log directory')
    args = vars(parser.parse_args())
    #hmc host
    _hmcHost = assertValue(pyObj=args, key='hmc', listIndex=0, optionalKey=True)
    hmcHost = checkValue('hmcHost', _hmcHost , hmcHost)
    if hmcHost == None:
        msg = "hmc host IP should be provided"
        print msg
    #cpc name
    _cpcName = assertValue(pyObj=args, key='cpcName', listIndex=0, optionalKey=True)
    cpcName = checkValue('cpcName', _cpcName, cpcName)
    if cpcName == None:
        msg = "cpc name should be provided"
        print msg
    #partition name
    _parName = assertValue(pyObj=args, key='parName', listIndex=0, optionalKey=True)
    parName = checkValue('parName', _parName, parName)
    if parName == None:
        msg = "partition name should be provided"
        print msg

    #domain index
    _domIndex = assertValue(pyObj=args, key='domIndex', listIndex=0, optionalKey=True)
    domIndex = checkValue('domIndex', _domIndex, domIndex)
        
    #domain access mode
    _domAcesMode = assertValue(pyObj=args, key='domAcesMode', listIndex=0, optionalKey=True)
    domAcesMode = checkValue('domAcesMode', _domAcesMode, domAcesMode)
    
    # log
    _logDir = assertValue(pyObj=args, key='logDir', listIndex=0, optionalKey=True)
    logDir = checkValue('logDir', _logDir, logDir)
    
    _logLevel = assertValue(pyObj=args, key='logLevel', listIndex=0, optionalKey=True)
    logLevel = checkValue('logLevel', _logLevel, logLevel)
# ------------------------------------------------------------------ #
# --------- End of parseArgs function ------------------------------ #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------- Start of checkIfParCrypt  function --------------------- #
# ------------------------------------------------------------------ #
def checkIfParCrypt(hmcConn,
                    parURI = None,
                    inputIndex = None):
    log.debug('Entered')
    _crptCfg = {}
    _crptDomCfg = list()
    _domIndexList = list()
    ifParCrypt = False
    try:
        if parURI == None:
            print 'parURI should be provided'
        res = getPartitionProperties(hmcConn, parURI=parURI)
 
        _crptCfg = res['crypto-configuration']
        _crptDomCfg = _crptCfg['crypto-domain-configurations']
        
        if _crptDomCfg:
            for domCfg in _crptDomCfg:
                _domIndexList.append(domCfg['domain-index'])
        else:
            print 'Partition <%s> did not have crypto domain configuration'%parURI
        
        if inputIndex in _domIndexList:
            ifParCrypt = True
    finally:
        log.debug("Completed")
        return ifParCrypt 
# ------------------------------------------------------------------ #
# ----------- End of checkIfParCrypt  function --------------------- #
# ------------------------------------------------------------------ #
        
# ------------------------------------------------------------------ #
# --------- Start of printParams function -------------------------- #
# ------------------------------------------------------------------ #
def printParams():
    print("\t#Parameters were input:")
    print("\tHMC system IP\t%s"%hmcHost)
    print("\tCPC name\t%s"%cpcName)
    print("\tPartition\t%s"%parName)
    print("\tDomain Index       -> %s"%domIndex)
    print("\tDomain Access Mode -> %s"%domAcesMode)
    if domIndex == None or domAcesMode == None:
        print 'Domain index number and access mode should be provided'
# ------------------------------------------------------------------ #
# --------- End of printParams function ---------------------------- #
# ------------------------------------------------------------------ #

# start _main_ from here

hmc = None
crypDomChange = {} # Dictionary to store Crypto Domain Changes

domIndexList= list()
domIndexChangeList = list()

KEY_ACCESS_MODE = 'access-mode'
KEY_DOMAIN_INDEX = 'domain-index'
accessMode = None 

inputParNameList = list() # user-input partition name list
inputParURIList = list() # user-input partition URI list

try:
    parseArgs()
    setupLoggers(logDir=logDir, logLevel=logLevel)
    
    print "*****************************************************"
    print "Update Crypto configuration for specified partition"
    printParams()
    print "*****************************************************"
    
    # Access HMC system and create HMC connection 
    hmc = createHMCConnection(hmcHost=hmcHost)
    cpc = selectCPC(hmc, cpcName)
    cpcURI = assertValue(pyObj=cpc, key=KEY_CPC_URI)
    cpcName = assertValue(pyObj=cpc, key=KEY_CPC_NAME)
    cpcStatus = assertValue(pyObj=cpc, key=KEY_CPC_STATUS)
    
    # Get CPC UUID
    cpcID = cpcURI.replace('/api/cpcs/','')
    #Get partitions JSON object on this CPC
    parResObj = getCPCPartitionsList(hmc, cpcID)
    
    #Generate user-input partitions URI and Name list
    for parInfo in parResObj:
        _parName = assertValue(pyObj=parInfo,key='name')
        if _parName in parName:
            inputParURIList.append(assertValue(pyObj=parInfo,key='object-uri'))
            inputParNameList.append(_parName)
            
    # check if selected partition had crypto config or not 
    # check if input domain index existed in current crpto configurations. 
    for inputParURI in inputParURIList:
        ret = checkIfParCrypt(hmc, inputParURI, int(domIndex))
        
    if not ret:
        print 'Input index number did not have domain configuration on this partition, please select new one'
        exit(1)
    else:
        # Prepare both usage and control domain data
        if domIndex != None and domAcesMode == 'control':
            accessMode= 'control'

        elif domIndex != None and domAcesMode == 'usage':
            accessMode = 'control-usage'
        
        else:
            print "Warning: Please provide correct inputs for domIndex and domAcesMode"
            exit(1)
    
        for inputParURI in inputParURIList:
            res = changeCryptoDomConfig(hmc,parURI=inputParURI,domIndex=int(domIndex), accessMode=accessMode)
            print 'Crypto Domain Changes have been made successfully for Partition <%s:%s>'%(cpcName,parName)
except Exception as exc:
    print exc
  
finally:
    # cleanup
    if hmc != None:
        hmc.logoff()

