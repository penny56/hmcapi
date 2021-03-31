'''
created on 11/13/2017

This script intends to decrease Crypto Configuration for target partition
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

# Crypto Adapter name or list will be removed (M90 "CCA 0188 Z15B-03,CCA 01bc Z15B-19")
adapName=[]

#Index of domains which will be removed from current configuration.
domIndex=[]

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
    global parName, adapName, domIndex
    global logDir, logLevel
    parser = argparse.ArgumentParser(description="create zEDC virtual function for specified partitions")
    parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
    parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
    parser.add_argument('-parName','--parName',metavar='<partition name>',
                        help='set target partition name')
    parser.add_argument('-adapName','--adapName',metavar='<adapter name>',
                        help='set adapter name which will be decreased: zEDC 017c Z22B-38')
    parser.add_argument('-domIndex','--domIndex',metavar='<Index number of Domains>',
                        help='select domain index which will be removed from current config')
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
    if adapName:
        adapName = adapName.split(',')
    
    #domain index
    _domIndex = assertValue(pyObj=args, key='domIndex', listIndex=0, optionalKey=True)
    domIndex = checkValue('domIndex', _domIndex, domIndex)
    if domIndex:
        domIndex = domIndex.split(',')
        
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
    if adapName:
        print("\tCrypto Adapter will be removed ->  %s"%adapName)
    if domIndex:
        print("\tDomain Index will be removed   ->  %s"%domIndex)
# ------------------------------------------------------------------ #
# --------- End of printParams function ---------------------------- #
# ------------------------------------------------------------------ #

# start _main_ from here

hmc = None
removalCrypCfg = {} # Dictionary to store removal information

adapURIList = list() # adap URI list
domIndexList = list() # list of domain index number



inputParNameList = list() # user-input partition name list
inputParURIList = list() # user-input partition URI list

try:
    parseArgs()
    setupLoggers(logDir=logDir, logLevel=logLevel)
    
    print "*****************************************************"
    print "Decrease Crypto configuration for specified partition"
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
    
    #Get available Adapter URI list for removal
    if adapName:
        for _adapName in adapName:
            adap = selectAdapter(hmc, _adapName, cpcID)
            adapURIList.append(assertValue(pyObj=adap, key=KEY_ADAPTER_URI))
           
    #if not adapURIList:
    #print 'Warning: Please ensure if input adapters <%s> are correct or not'%adapName
        
    # Prepare crypto config info for removal.
    if domIndex:
        for indexNum in domIndex:
            domIndexList.append(int(indexNum))
    removalCrypCfg['crypto-adapter-uris'] = adapURIList
    removalCrypCfg['crypto-domain-indexes'] = domIndexList
    
    if not adapURIList and not domIndexList:
        print 'Please provide cryto settings <adapName or domIndex> for removal...'
    
    else:
        for parInfo in parResObj:
            _parName = assertValue(pyObj=parInfo,key='name')
            if _parName in parName:
                inputParURIList.append(assertValue(pyObj=parInfo,key='object-uri'))
                inputParNameList.append(_parName)
    
        for inputParURI in inputParURIList:
            res = decreaseCryptoConfig(hmc,parURI=inputParURI,cryptCfgProps=removalCrypCfg)
            print 'Crypto Setting was decreased successfully for Partition <%s:%s>'%(cpcName,parName)
 
except Exception as exc:
    print exc
  
finally:
    # cleanup
    if hmc != None:
        hmc.logoff()

