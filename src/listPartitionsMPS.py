'''
Created on Oct 12, 2017

List the required partition(s)'s Manage Processor Sharing information. If the partition(s) range indicated explicitly, list the information, or if no partition indicated,
list all shared partitions' information in the CPC.

Example:
-hmc 9.12.35.135 -cpc M90

@author: mayijie
'''

from prsm2api import *
from wsaconst import *
import hmcUtils
import argparse
import logging
import sys

hmcHost = None
cpcName = None
parRange = None
logDir = None
logLevel = None
configFile = None
configFilename = None

# partition properties, new and original
argsDict = dict()
partitionProps = dict()
parState = dict()

# log levels
sysoutLogLevel = logging.ERROR
defaultLogLevel = logging.INFO
logLevel = defaultLogLevel

# partition list only for the partition(s) in shared mode
wholeParNamesList = []
wholeParURIsList = []

# do we need to list all the CPC partitions
listAll = False
inputParNamesList = []

# To construct a table
TAB = 11
colWidth = TAB * 2
colOrder = ('Partition', 'State', 'Number of Processors', 'Weight',
            'Weight Capping', 'Absolute Capping', 'Absolute Capping Value')

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
    global parRange
    global logDir, logLevel, configFilename
    global argsDict
    parser = argparse.ArgumentParser(description='off-line update the Processor parameters for partition')
    parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
    parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
    parser.add_argument('-parRange', '--parRange', metavar='<the range of partitions to be operated>',
                        help='the range of partitions to be operated')
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
# partion range
    _parRange = assertValue(pyObj=args, key='parRange', listIndex=0, optionalKey=True)
    parRange = checkValue('parRange', _parRange, parRange)
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
    print("\tPartitions\t%s" % parRange)
# ------------------------------------------------------------------ #
# --------- End of printParams function ---------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------- Start of getPartitionsStatesOnCPC function ------------- #
# ------------------------------------------------------------------ #


def getPartitionsOnCPC(hmc, cpcID):
    global sharedModeParNamesList, sharedModeParURIsList, parState

    parRet = getCPCPartitionsList(hmc, cpcID)

    for parInfo in parRet:
        wholeParNamesList.append(assertValue(pyObj=parInfo, key='name'))
        wholeParURIsList.append(assertValue(pyObj=parInfo, key='object-uri'))
        parState[parInfo['name']] = parInfo['status']

# ------------------------------------------------------------------ #
# ----- End of getPartitionsStatesOnCPC function ------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------- Start of listMPSInformation function ------------------- #
# ------------------------------------------------------------------ #


def listMPSInformation():
    global listAll, inputParNamesList, parState
    global wholeParNamesList, wholeParURIsList

    for curCol in colOrder:
        sys.stdout.write(curCol + ' ' * (colWidth - len(curCol) - 1) + '|')
    print
    print '#' * colWidth * len(colOrder)
    sys.stdout.flush()
    for parName in wholeParNamesList:
        if listAll or parName in inputParNamesList:
            index = wholeParNamesList.index(parName)
            parURI = wholeParURIsList[index]

            partitionPropsTemp = getPartitionProperties(hmc, parURI=parURI)
            if partitionPropsTemp['processor-mode'] == 'shared':
                # shared mode, list the MPS information
                mpsInfo = dict()
                mpsInfo['Partition'] = parName
                mpsInfo['State'] = parState[parName]
                if partitionPropsTemp['cp-processors'] != 0:
                    mpsInfo['Number of Processors'] = str(partitionPropsTemp['cp-processors'])
                    mpsInfo['Weight'] = str(partitionPropsTemp['initial-cp-processing-weight'])
                    mpsInfo['Weight Capping'] = str(partitionPropsTemp['cp-processing-weight-capped'])
                    mpsInfo['Absolute Capping'] = str(partitionPropsTemp['cp-absolute-processor-capping'])
                    mpsInfo['Absolute Capping Value'] = str(partitionPropsTemp['cp-absolute-processor-capping-value'])
                else:
                    mpsInfo['Number of Processors'] = str(partitionPropsTemp['ifl-processors'])
                    mpsInfo['Weight'] = str(partitionPropsTemp['initial-ifl-processing-weight'])
                    mpsInfo['Weight Capping'] = str(partitionPropsTemp['ifl-processing-weight-capped'])
                    mpsInfo['Absolute Capping'] = str(partitionPropsTemp['ifl-absolute-processor-capping'])
                    mpsInfo['Absolute Capping Value'] = str(partitionPropsTemp['ifl-absolute-processor-capping-value'])

                tableFixWidthPrint(mpsInfo)

# ------------------------------------------------------------------ #
# --------- End of listMPSInformation function --------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------- Start of tableFixWidthPrint function ------------------- #
# ------------------------------------------------------------------ #


def tableFixWidthPrint(propDict):
    global colWidth, colOrder
    newLine = ""

    for curCol in colOrder:
        if len(propDict[curCol]) < colWidth:
            sys.stdout.write(propDict[curCol] + ' ' * (colWidth - len(propDict[curCol]) - 1) + '|')
            newLine += ' ' * (colWidth - 1) + '|'
        else:
            sys.stdout.write(propDict[curCol][:colWidth - 1] + '|')
            newLine += propDict[curCol][colWidth - 1:] + ' ' * \
                (colWidth - len(propDict[curCol][colWidth - 1:]) - 1) + '|'
    sys.stdout.flush()
    print
    if (len(newLine.replace(' ', '')) != len(colOrder)):
        sys.stdout.write(newLine)
        print

# ------------------------------------------------------------------ #
# --------- End of tableFixWidthPrint function --------------------- #
# ------------------------------------------------------------------ #

# main function
hmc = None
success = True

try:
    parseArgs()
    setupLoggers(logDir=logDir, logLevel=logLevel)

    print "******************************"
    msg = "list partition Manage Processor Sharing information"
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

    if parRange != None:
        inputParNamesList = parRange.split(',')
    else:
        listAll = True

    listMPSInformation()

except Exception as exc:
    print exc

finally:
    # cleanup
    if hmc != None:
        hmc.logoff()
