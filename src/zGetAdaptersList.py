'''
Created on 20200306

Get different type of adapter list

@auther : Ma, Yi Jie
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

# partition name List
parNames = None

# zEDC Adapter name
adapName=None

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
    global parNames, adapName
    global logDir, logLevel
    parser = argparse.ArgumentParser(description="create zEDC virtual function for specified partitions")
    parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
    parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
    parser.add_argument('-parNames','--parNames',metavar='<partition name or list>',
                        help='set target partition whose value can be single or a list with comma only')
    parser.add_argument('-adapName','--adapName',metavar='<adapter name>', help='set adapter name as sample: zEDC 017c Z22B-38')
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
    #partition names
    _parNames = assertValue(pyObj=args, key='parNames', listIndex=0, optionalKey=True)
    parNames = checkValue('parNames', _parNames, parNames)
    if parNames == None:
        msg = "partition name should be provided"
        print msg
    if parNames != None:
        parNames = parNames.split(',')
    #adapter name
    _adapName = assertValue(pyObj=args, key='adapName', listIndex=0, optionalKey=True)
    adapName = checkValue('adapterName', _adapName, adapName)
    if adapName == None:
        msg = "adapter name should be provided"
        print msg
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
    print("\tParameters were input:")
    print("\tHMC system IP\t%s"%hmcHost)
    print("\tCPC name\t%s"%cpcName)
    print("\tPartitions\t%s"%parNames)
    print("\tAdapter name\t%s"%adapName)
# ------------------------------------------------------------------ #
# --------- End of printParams function ---------------------------- #
# ------------------------------------------------------------------ #

# start _main_ from here
hmc = None
vfName = None
success = True
inputParNameList = list() # user-input partition name list
inputParURIList = list() # user-input partition URI list

try:
    parseArgs()
    setupLoggers(logDir=logDir, logLevel=logLevel)
    
    print "***********************************"
    print "Create virtual function for specified partitions"
    printParams()
    print "***********************************"
    
    # Access HMC system and create HMC connection 
    hmc = createHMCConnection(hmcHost=hmcHost)
    cpc = selectCPC(hmc, cpcName)
    cpcURI = assertValue(pyObj=cpc, key=KEY_CPC_URI)
    cpcName = assertValue(pyObj=cpc, key=KEY_CPC_NAME)
    cpcStatus = assertValue(pyObj=cpc, key=KEY_CPC_STATUS)
    
    # Get CPC UUID
    cpcID = cpcURI.replace('/api/cpcs/','')
    
    # get adapter list
    adaList = getCPCAdaptersList(hmc, cpcID)
    
    for ada in adaList:
        
        #################### update here ###########################
        # we have type = 
        # network: osd, roce, osm
        # storage: fcp, fc
        # crypto: crypto
        # unknow: not-configured
        
        if str(ada['type']) == 'osd':
            print ada
        
except Exception as exc:
    print exc
  
finally:
    # cleanup
    if hmc != None:
        hmc.logoff()