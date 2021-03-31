'''
Created on Nov 9, 2017

Delete a NIC in a partition, you should specify the NIC name and partition name in the input parameters.

Example:
-hmc 9.12.35.135 -cpc M90 -parName LNXT01 -nicName m90lt01_***

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
logDir = None
logLevel = None
configFile = None
configFilename = None

nicUri = None

# log levels
sysoutLogLevel = logging.ERROR
defaultLogLevel = logging.INFO
logLevel = defaultLogLevel

# partition list only for the partition in shared mode
wholeParNamesList = []
wholeParURIsList = []

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
            msg = "Logging directory [%s] doesn't exist. Skipping.." % (logDir)
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
            hdlr.setLevel(logLevel)  # flogLevel)
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
    global parName, nicName
    global logDir, logLevel, configFilename
    parser = argparse.ArgumentParser(description='Create a new NIC for partition')
    parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
    parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
    parser.add_argument('-parName', '--parName', metavar='<the name of partition to be operated>',
                        help='the name of partition to be operated')
    parser.add_argument('-nicName', '--nicName', metavar='<the name of NIC to be operated>',
                        help='the name of NIC to be operated')
    parser.add_argument('-logLevel', '--logLevel', metavar='<log level name>', help='Logging level. Can be one of {debug, info, warn, error, critical}',
                        choices=['debug', 'info', 'warn', 'error', 'critical'])
    parser.add_argument('-logDir', '--logDir', metavar='<log directory>', help='set log directory')
    parser.add_argument('-c', '--config', metavar='<file name>', help='Configuration file name (path)')
    args = vars(parser.parse_args())

    # HMC host
    _hmcHost = assertValue(pyObj=args, key='hmc', listIndex=0, optionalKey=True)
    hmcHost = checkValue('hmcHost', _hmcHost, hmcHost)
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
# partition name
    _parName = assertValue(pyObj=args, key='parName', listIndex=0, optionalKey=True)
    parName = checkValue('parName', _parName, parName)
    if parName == None:
        exc = HMCException("checkParams", "You should specify the partition name")
        print exc.message
        raise exc
# NIC name
    _nicName = assertValue(pyObj=args, key='nicName', listIndex=0, optionalKey=True)
    nicName = checkValue('nicName', _nicName, nicName)
    if nicName == None:
        exc = HMCException("checkParams", "You should specify nic name")
        print exc.message
        raise exc
# log
    _logDir = assertValue(pyObj=args, key='logDir', listIndex=0, optionalKey=True)
    logDir = checkValue('logDir', _logDir, logDir)
    _logLevel = assertValue(pyObj=args, key='logLevel', listIndex=0, optionalKey=True)
    logLevel = checkValue('logLevel', _logLevel, logLevel)
# configuration file name
    configFile = assertValue(pyObj=args, key='config', listIndex=0, optionalKey=True)
# log level
    configFilename = checkValue('configFilename', configFile, configFilename)

# ------------------------------------------------------------------ #
# --------- End of parseArgs function ------------------------------ #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------- Start of printParams function -------------------------- #
# ------------------------------------------------------------------ #


def printParams():
    print("\tParameters were input:")
    print("\tHMC system IP\t%s" % hmcHost)
    print("\tCPC name\t\t%s" % cpcName)
    print("\tpartition\t%s" % parName)
    print("\t---- <Partition Settings> ----")
    print("\tNIC name\t%s" % nicName)

# ------------------------------------------------------------------ #
# --------- End of printParams function ---------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------- Start of getPartitionsOnCPC function ------------------- #
# ------------------------------------------------------------------ #


def getPartitionsOnCPC(hmc, cpcID):
    global wholeParNamesList, wholeParURIsList

    parRet = getCPCPartitionsList(hmc, cpcID)

    for parInfo in parRet:
        wholeParNamesList.append(assertValue(pyObj=parInfo, key='name'))
        wholeParURIsList.append(assertValue(pyObj=parInfo, key='object-uri'))

# ------------------------------------------------------------------ #
# ----- End of getPartitionsOnCPC function ------------------------- #
# ------------------------------------------------------------------ #

# main function
hmc = None
success = True

try:
    parseArgs()
    setupLoggers(logDir=logDir, logLevel=logLevel)

    print "******************************"
    msg = "Delete NIC in the partition"
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
    cpcID = cpcURI.replace('/api/cpcs/', '')
    getPartitionsOnCPC(hmc, cpcID)
    
    index = wholeParNamesList.index(parName)
    parURI = wholeParURIsList[index]
    if (parURI == None):
        exc = HMCException("The partition name: " + parName + " not exist in the CPC!")
        raise exc
    partitionPropsTemp = getPartitionProperties(hmc, parURI=parURI)
    
    for iNicUri in partitionPropsTemp['nic-uris']:
        nicEntity = getNICProperties(hmc, nicURI = iNicUri)
        if str(nicEntity['name']) == nicName:
            nicUri = iNicUri
            break
    
    if nicUri == None:
        exc = Exception("Couldn't find the nic: " + nicName)
        raise exc
    
    try:
        deleteNIC(hmc, nicURI = nicUri)
        print "Delete NIC successfully! "
    except Exception as exc:
        excResponse = eval(exc.httpResponse)
        print "Delete NIC Failed!, the reason is: " + excResponse["message"]

except Exception as exc:
    print exc

finally:
    # cleanup
    if hmc != None:
        hmc.logoff()
