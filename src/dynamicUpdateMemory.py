'''
Created on Oct 17, 2017

This module is aimed to update the initial memory when the partition is in active state. The maximum memory value is read-only in active state.
The new initial memory value should be greater than the current value, but less than the maximum memory value, and should be enabled it be command line:

chmem -e 2g

Example:
-hmc 9.12.35.135 -cpc M90 -parRange LNXT01,LNXT02 -initMem 70

@author: Ma, Yi Jie
'''

from CommonAPI.prsm2api import *
from CommonAPI.wsaconst import *
import CommonAPI.hmcUtils
import argparse
import logging
import time

hmcHost = None
cpcName = None
parRange = None
initMem = None
logDir = None
logLevel = None
configFile = None
configFilename = None

# partition properties, new and original
argsDict = dict()
partitionProps = dict()

# log levels
sysoutLogLevel = logging.ERROR
defaultLogLevel = logging.INFO
logLevel = defaultLogLevel

# active state partition list
activeStateParNamesList = []
activeStateParURIsList = []

failedDict = dict()
passedList = []

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
    global parRange, initMem
    global logDir, logLevel, configFilename
    global argsDict
    parser = argparse.ArgumentParser(description='dynamic update the Memory parameters for partition')
    parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
    parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
    parser.add_argument('-parRange', '--parRange', metavar='<the range of partitions to be operated>',
                        help='the range of partitions to be operated')
    parser.add_argument('-initMem', '--initMem', metavar='<initial memory size>',
                        help='set initial memory size in GB unit')
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
    if parRange == None:
        exc = HMCException("checkParams", "You should specify the partition(s) name")
        print exc.message
        raise exc
# initial memory
    _initMem = assertValue(pyObj=args, key='initMem', listIndex=0, optionalKey=True)
    initMem = checkValue('initMem', _initMem, initMem, valueType=int)
    if initMem != None:
        # update unit from GB to MB
        argsDict['initMem'] = initMem * 1024
    else:
        exc = HMCException("checkParams", "You should specify the new initial memory number")
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
    print("\tPartitions\t%s" % parRange)
    print("\t---- <Partition Settings> ----")
    print("\tNumber of Initial Memory\t%s" % initMem)
    print("\tPath to save logs\t%s" % logDir)
# ------------------------------------------------------------------ #
# --------- End of printParams function ---------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------- Start of getPartitionsStatesOnCPC function ------------- #
# ------------------------------------------------------------------ #


def getPartitionsStatesOnCPC(hmc, cpcID):
    global activeStateParNamesList, activeStateParURIsList
    parRet = getCPCPartitionsList(hmc, cpcID)
    for parInfo in parRet:
        # for dynamic update, only when the partition in active state
        if assertValue(pyObj=parInfo, key='status') == 'active':
            activeStateParNamesList.append(assertValue(pyObj=parInfo, key='name'))
            activeStateParURIsList.append(assertValue(pyObj=parInfo, key='object-uri'))

# ------------------------------------------------------------------ #
# ----- End of getPartitionsStatesOnCPC function ------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of updatePartitionTemplate function ------------------ #
# ------------------------------------------------------------------ #
# if the input parameters are acceptable (greater than the current value and less than the maximum value, and could be updated successfully,
# fill the parTempl and return the parTempl
# else if the input parameters are incorrect and could not be set, add the partition name and reason, and return None.


def updatePartitionTemplate(partitionPropsTemp):
    global partitionProps, argsDict, failedDict
    parTempl = dict()
    if partitionPropsTemp['initial-memory'] < argsDict['initMem'] and partitionPropsTemp['maximum-memory'] >= argsDict['initMem']:
        parTempl['initial-memory'] = argsDict['initMem']
    else:
        failedDict[partitionPropsTemp[
            'name']] = "The new initial memory should greater than the current initial memory and less than or equal to the maximum memory."
    return parTempl
# ------------------------------------------------------------------ #
# ----- End of updatePartitionTemplate function -------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of postPartition function ---------------------------- #
# ------------------------------------------------------------------ #
# use restful post API to update the partition properties


def postPartition(parTempl, parName, parURI):
    global failedDict
    try:
        # prepare HTTP body as JSON
        httpBody = json.dumps(parTempl)
        # create workload
        resp = getHMCObject(hmc,
                            parURI,
                            "Set Partition Properties",
                            httpMethod=WSA_COMMAND_POST,
                            httpBody=httpBody,
                            httpGoodStatus=204,           # HTTP created
                            httpBadStatuses=[400, 403, 404, 409, 503])
    except HMCException as exc:   # raise HMCException
        #raise exc
        # if there have an exception for the post operation, fill them in the failedDict dict with the reason.
        failedDict[parName] = eval(exc.httpResponse)['message']
    finally:
        log.debug("Completed")
# ------------------------------------------------------------------ #
# ----- End of postPartition function ------------------------------ #
# ------------------------------------------------------------------ #

# main function
hmc = None
success = True

try:
    parseArgs()
    setupLoggers(logDir=logDir, logLevel=logLevel)

    print "******************************"
    msg = "dynamic DPM Memory Update PRSM2 partitions"
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
    getPartitionsStatesOnCPC(hmc, cpcID)

    if parRange != None:
        inputParNamesList = parRange.split(',')
    else:
        exc = HMCException("dynamicUpdateMemory",
                           "At least specify one partition you want to operate. To do this, please input the value of 'parRange'.")
    print 'These are the partitions you are going to operate: ', inputParNamesList

    for parName in inputParNamesList:
        if parName in activeStateParNamesList:
            index = activeStateParNamesList.index(parName)
            parURI = activeStateParURIsList[index]

            partitionPropsTemp = getPartitionProperties(hmc, parURI=parURI)
            parTempl = dict()
            parTempl = updatePartitionTemplate(partitionPropsTemp)
            if len(parTempl) != 0:
                postPartition(parTempl, parName, parURI)
                # if the postPartition function have encounter a HMC exception and the
                # function don't have a return value, it just put the parName in the
                # failedDict dict
                if parName not in failedDict.keys():
                    passedList.append(parName)
            elif parName not in failedDict.keys():
                failedDict[parName] = "No need to update since the new value equal to the original one."
        else:
            failedDict[parName] = "Only active partitions could use dynamic update."

except Exception as exc:
    print exc

finally:
    # cleanup
    if hmc != None:
        hmc.logoff()
    if success:
        msg = "\nScript finished successfully.\n"
        if len(passedList) != 0:
            print "the partitions have changed SUCCESSFULLY:"
            for parName in passedList:
                print parName
        if failedDict:
            print "the partitions have been changed FAILED:"
            for (parName, reason) in failedDict.items():
                print "Partition '" + parName + "' update failed, with the reason: " + reason
        log.info(msg)
        print msg
