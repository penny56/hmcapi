'''
created on 11/09/2017

This script intends to increase Crypto Configuration for target partition
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
adapName=[]

#Usage domain index 
usageDomIndex=None

#Control domain index list
controlDomIndex=None

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
    global parName, adapName, usageDomIndex, controlDomIndex
    global logDir, logLevel
    parser = argparse.ArgumentParser(description="create zEDC virtual function for specified partitions")
    parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
    parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
    parser.add_argument('-parName','--parName',metavar='<partition name>',
                        help='set target partition name')
    parser.add_argument('-adapName','--adapName',metavar='<adapter name>',
                        help='set adapter name as sample: zEDC 017c Z22B-38')
    parser.add_argument('-usageDomIndex','--usageDomIndex',metavar='<Index number of Usage Domain>',
                        help='select a value from 1 to 84')
    parser.add_argument('-controlDomIndex','--controlDomIndex',metavar='<Index number of Control Domain>',
                        help='select one value or multiple from 1 to 84')
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
    #adapter name
    _adapName = assertValue(pyObj=args, key='adapName', listIndex=0, optionalKey=True)
    adapName = checkValue('adapterName', _adapName, adapName)
    if adapName == None:
        msg = "adapter name should be provided"
        print msg
    adapName = adapName.split(',')
    
    #usage domain index
    _usageDomIndex = assertValue(pyObj=args, key='usageDomIndex', listIndex=0, optionalKey=True)
    usageDomIndex = checkValue('usageDomIndex', _usageDomIndex, usageDomIndex)
    
    #control domain index
    _controlDomIndex = assertValue(pyObj=args, key='controlDomIndex', listIndex=0, optionalKey=True)
    controlDomIndex = checkValue('controlDomIndex', _controlDomIndex, controlDomIndex)
    controlDomIndex = controlDomIndex.split(',')
    
    # log
    _logDir = assertValue(pyObj=args, key='logDir', listIndex=0, optionalKey=True)
    logDir = checkValue('logDir', _logDir, logDir)
    
    _logLevel = assertValue(pyObj=args, key='logLevel', listIndex=0, optionalKey=True)
    logLevel = checkValue('logLevel', _logLevel, logLevel)
# ------------------------------------------------------------------ #
# --------- End of parseArgs function ------------------------------ #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------- Start of printParams function -------------------------- #
# ------------------------------------------------------------------ #
def printParams():
    print("\t#Parameters were input:")
    print("\tHMC system IP\t%s"%hmcHost)
    print("\tCPC name\t%s"%cpcName)
    print("\tPartition\t%s"%parName)
    print("\tCrypto Adapter Name\t%s"%adapName)
    print("\tUsage Domain Index\t%s"%usageDomIndex)
    print("\tControl Domain Index\t%s"%controlDomIndex)
    if adapName == None or usageDomIndex == None or controlDomIndex == None:
        print 'Crypto adapName , usageDomIndex and controlDomIndex should be provided'
# ------------------------------------------------------------------ #
# --------- End of printParams function ---------------------------- #
# ------------------------------------------------------------------ #

# start _main_ from here

hmc = None
crypCfg = {} # Dictionary to store Crypto configuration
crypDomCfg = []

adapURIList = list()
adapStatusList = list()
adapNameList = list()

KEY_ACCESS_MODE = 'access-mode'
KEY_DOMAIN_INDEX = 'domain-index'
accessMode = None 

inputParNameList = list() # user-input partition name list
inputParURIList = list() # user-input partition URI list

try:
    parseArgs()
    setupLoggers(logDir=logDir, logLevel=logLevel)
    
    print "*****************************************************"
    print "Increase Crypto configuration for specified partition"
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
    
    #Get available Adapter URI list for increasing crypto configuration
    for _adapName in adapName:
        adap = selectAdapter(hmc, _adapName, cpcID)
        adapURIList.append(assertValue(pyObj=adap, key=KEY_ADAPTER_URI))
        adapStatusList.append(assertValue(pyObj=adap, key=KEY_ADAPTER_STATUS))
        adapNameList.append(assertValue(pyObj=adap, key=KEY_ADAPTER_NAME))
    for adapStatus in adapStatusList:
        if adapStatus != 'active':
            # if adapter was not active, will remove from available adapter list
            index=adapStatusList.index(adapStatus)
            invalidAdapName = adapNameList[index]
            adapURIList.remove(adapURIList[index])
            print 'Warning: Crypto Adapter <%s> is not Active, please double check'%invalidAdapName
            
    if not adapURIList:
        print 'Warning: Please ensure if input adapters <%s> are active to use'%adapName
    
    # Prepare both usage and control domain data
    if usageDomIndex != None:
        accessMode = 'control-usage'
        usageDom = {}
        usageDom[KEY_ACCESS_MODE] = accessMode
        usageDom[KEY_DOMAIN_INDEX] = int(usageDomIndex)
        crypDomCfg.append(usageDom)
    if controlDomIndex:
        accessMode = 'control'
        for indexNum in controlDomIndex:
            controlDom = {}
            controlDom[KEY_ACCESS_MODE] = accessMode
            controlDom[KEY_DOMAIN_INDEX] = int(indexNum)
            crypDomCfg.append(controlDom)
            
    # Prepare crypto configuration data
    crypCfg['crypto-domain-configurations'] = crypDomCfg
    crypCfg['crypto-adapter-uris'] = adapURIList
    
    #Generate user-input partitions URI and Name list
    for parInfo in parResObj:
        _parName = assertValue(pyObj=parInfo,key='name')
        if _parName in parName:
            inputParURIList.append(assertValue(pyObj=parInfo,key='object-uri'))
            inputParNameList.append(_parName)
    
    for inputParURI in inputParURIList:
        res = increaseCryptoConfig(hmc,parURI=inputParURI,cryptCfgProps=crypCfg)
    print 'Crypto configuration was increased successfully for Partition <%s:%s>'%(cpcName,parName)
 
except Exception as exc:
    print exc
  
finally:
    # cleanup
    if hmc != None:
        hmc.logoff()

