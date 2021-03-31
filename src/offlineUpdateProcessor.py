'''
Created on Jul 31, 2017

This module is aimed to update the processor type, mode and number of processor in off-line status.
If the partition is in active state, this module will first stop the partition, update the parameters and then turn the partition back to active.

Example:
-hmc 9.12.35.135 -cpc M90 -parRange LNXT02 -procMode shared -procType ifl -procNum 7 -execMode mt

@author: Ma, Yi Jie
'''

from prsm2api import *
from wsaconst import *
import hmcUtils
import argparse
import logging
import threading

hmcHost = None
cpcName = None
parRange = None
procMode = None
procType = None
procNum = None
execMode = None
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

# stopped state partition list
stopedStateParNamesList = []
stopedStateParURIsList = []

# active state partition list
activeStateParNamesList = []
activeStateParURIsList = []

failedDict = dict()
passedList = []

# for multi-thread write protection
lock = threading.Lock()

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
    global parRange, procMode, procType, procNum, execMode
    global logDir, logLevel, configFilename
    global argsDict
    parser = argparse.ArgumentParser(description='off-line update the Processor parameters for partition')
    parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
    parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
    parser.add_argument('-parRange', '--parRange', metavar='<the range of partitions to be operated>',
                        help='the range of partitions to be operated')
    parser.add_argument('-procMode', '--procMode', metavar='<Processor mode>',
                        help='processor mode can be shared or dedicated')
    parser.add_argument('-procType', '--procType', metavar='<processor type>', help='set IFL or CP as processor type')
    parser.add_argument('-procNum', '--procNum', metavar='<number of processor>',
                        help='set reasonable number of processor')
    parser.add_argument('-execMode', '--execMode', metavar='<sequential or multiple threads>', help='sequential or execute the updates simultaneous for multiple partitions',
                        choices=['se', 'mt'])
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
# Processor mode
    _procMode = assertValue(pyObj=args, key='procMode', listIndex=0, optionalKey=True)
    procMode = checkValue('procMode', _procMode, procMode)
    if procMode != None:
        argsDict['procMode'] = procMode
# processor type
    _procType = assertValue(pyObj=args, key='procType', listIndex=0, optionalKey=True)
    procType = checkValue('procType', _procType, procType)
    if procType != None:
        argsDict['procType'] = procType
# processor number
    _procNum = assertValue(pyObj=args, key='procNum', listIndex=0, optionalKey=True)
    procNum = checkValue('procNum', _procNum, procNum, valueType=int)
    if procNum != None:
        argsDict['procNum'] = procNum
# execution mode
    _execMode = assertValue(pyObj=args, key='execMode', listIndex=0, optionalKey=True)
    execMode = checkValue('execMode', _execMode, execMode)
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
    print("\tProcessor mode\t%s" % procMode)
    print("\tProcessor Type\t%s" % procType)
    print("\tNumber of Processor\t%s" % procNum)
    print("\tPath to save logs\t%s" % logDir)
# ------------------------------------------------------------------ #
# --------- End of printParams function ---------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------- Start of getPartitionsStatesOnCPC function ------------- #
# ------------------------------------------------------------------ #


def getPartitionsStatesOnCPC(hmc, cpcID):
    global stopedStateParNamesList, stopedStateParURIsList
    global activeStateParNamesList, activeStateParURIsList

    parRet = getCPCPartitionsList(hmc, cpcID)

    for parInfo in parRet:
        if assertValue(pyObj=parInfo, key='status') == 'stopped':
            stopedStateParNamesList.append(assertValue(pyObj=parInfo, key='name'))
            stopedStateParURIsList.append(assertValue(pyObj=parInfo, key='object-uri'))
        if assertValue(pyObj=parInfo, key='status') == 'active':
            activeStateParNamesList.append(assertValue(pyObj=parInfo, key='name'))
            activeStateParURIsList.append(assertValue(pyObj=parInfo, key='object-uri'))
        # for partitions in other state, please check in HMC and move them in active or stopped.

# ------------------------------------------------------------------ #
# ----- End of getPartitionsStatesOnCPC function ------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of stopThePartitionAndCheck function ----------------- #
# ------------------------------------------------------------------ #
# This function could stop a partition by partition Name, you should judge the partition state before enter it.
# This function will stop the partition and later check the status every 5 seconds till 24 times (2 minutes). if the server return the operation fail or time out, it return False
# If return success, return True.


def stopThePartitionAndCheck(parName, parURI):
    try:
        if lock.acquire():
            stopPartition(hmc, parURI)
            lock.release()

        intervalCount = 0
        while intervalCount != 24:
            if lock == None or lock.acquire():
                jobStatus = queryJobStatus(hmc, jobURI=parURI)
                if lock != None:
                    lock.release()
            status = assertValue(pyObj=jobStatus, key='status')
            if status == JOB_STATUS_STOPPED:
                sys.stdout.write('%s has been successfully stopped!\r\n' % parName)
                time.sleep(10)
                sys.stdout.flush()
                return True
            else:
                sys.stdout.write('%s is stopping, please wait...%ss\r\n' % (parName, intervalCount * 5))
                sys.stdout.flush()
            intervalCount += 1
            time.sleep(5)
        return False
    except HMCException as exc:
        raise exc
# ------------------------------------------------------------------ #
# ----- End of stopThePartitionAndCheck function ------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of startThePartitionAndCheck function ---------------- #
# ------------------------------------------------------------------ #


def startThePartitionAndCheck(parName, parURI):
    if lock == None or lock.acquire():
        startPartition(hmc, parURI)
        if lock != None:
            lock.release()

    intervalCount = 0
    while intervalCount != 24:
        if lock.acquire():
            jobStatus = queryJobStatus(hmc, jobURI=parURI)
            lock.release()
        status = assertValue(pyObj=jobStatus, key='status')
        if status == JOB_STATUS_ACTIVE:
            sys.stdout.write('%s has been successfully started!\r\n' % parName)
            time.sleep(10)
            sys.stdout.flush()
            return True
        else:
            sys.stdout.write('%s is starting, please wait...%ss\r\n' % (parName, intervalCount * 5))
            sys.stdout.flush()
        intervalCount += 1
        time.sleep(5)
    return False
# ------------------------------------------------------------------ #
# ----- End of startThePartitionAndCheck function ------------------ #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of updatePartitionTemplate function ------------------ #
# ------------------------------------------------------------------ #


def updatePartitionTemplate(partitionPropsTemp):
    global partitionProps, argsDict
    parTempl = dict()

    # Update for the processor Mode
    if argsDict.has_key('procMode') and argsDict.get('procMode') != partitionPropsTemp['processor-mode']:
        parTempl['processor-mode'] = argsDict.get('procMode')

    # Update for the processor Type
    # assume the new type is different from the ori type
    oriProcType = 'ifl'
    oriProcTypeKey = 'ifl-processors'
    newProcTypeKey = 'cp-processors'
    if partitionPropsTemp['cp-processors'] != 0:
        oriProcType = 'cp'
        oriProcTypeKey = 'cp-processors'
        newProcTypeKey = 'ifl-processors'

    if argsDict.has_key('procTpye') and argsDict.get('procTpye') != oriProcType:
        if argsDict.has_key('procNum'):
            parTempl[newProcTypeKey] = argsDict.get('procTpye')
            parTempl[oriProcTypeKey] = 0
        else:
            parTempl[newProcTypeKey] = partitionPropsTemp[oriProcTypeKey]
            parTempl[oriProcTypeKey] = 0
    elif argsDict.has_key('procNum') and argsDict.get('procNum') != partitionPropsTemp[oriProcTypeKey]:
        # in this case, the procType not change, only update the number.
        parTempl[oriProcTypeKey] = argsDict.get('procNum')

    return parTempl
# ------------------------------------------------------------------ #
# ----- End of updatePartitionTemplate function -------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of postPartition function --------------------- #
# ------------------------------------------------------------------ #


def postPartition(parTempl, parURI):
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
        raise exc
    finally:
        log.debug("Completed")
# ------------------------------------------------------------------ #
# ----- End of postPartition function ----------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of procSinglePartition function ---------------------- #
# ------------------------------------------------------------------ #


def procSinglePartition(parName):
    global failedDict, passedList
    needStart = False
    if parName in activeStateParNamesList:
        needStart = True
        index = activeStateParNamesList.index(parName)
        parURI = activeStateParURIsList[index]

        stopStatus = stopThePartitionAndCheck(parName, parURI)
        if stopStatus == False and lock.acquire():
            failedDict[parName] = 'partition stop failed'
            lock.release()
    elif parName in stopedStateParNamesList:
        index = stopedStateParNamesList.index(parName)
        parURI = stopedStateParURIsList[index]
    else:
        print "Neither in Active nor in Stopped state."
        failedDict[parName] = 'Partition in invalid state!'

    # Get the current information and set them.
    if lock.acquire():
        partitionPropsTemp = getPartitionProperties(hmc, parURI=parURI)
        parTempl = dict()
        parTempl = updatePartitionTemplate(partitionPropsTemp)
        postPartition(parTempl, parURI)

        passedList.append(parName)
        lock.release()

    # start the previous stopped partitions
    if (needStart and parName in passedList):
        startThePartitionAndCheck(parName, parURI)

# ------------------------------------------------------------------ #
# ----- End of procSinglePartition function ------------------------ #
# ------------------------------------------------------------------ #

# main function
hmc = None
success = True

try:
    parseArgs()
    setupLoggers(logDir=logDir, logLevel=logLevel)

    print "******************************"
    msg = "offline DPM Processor Update PRSM2 partitions"
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
        exc = HMCException("offlineUpdateProcessor",
                           "At least specify one partition you want to operate. To do this, please input the value of 'parRange'.")
    print 'These are the partitions you are going to operate: ', inputParNamesList

    if execMode == 'se':
        print "The partitions will be executed by sequence!"
        for parName in inputParNamesList:
            procSinglePartition(parName)

    elif execMode == 'mt':
        print "The partitions will be executed simultaneously!"
        threads = []
        for parName in inputParNamesList:
            #thread.start_new_thread(procSinglePartition, (parName, threadLock,))
            t = threading.Thread(target=procSinglePartition, args=(parName,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    else:
        exc = HMCException("offlineUpdateProcessor",
                           "execMode set error, 'se' represents executing partitions by sequence, and 'mt' means execute simultaneously.")

except Exception as exc:
    print exc

finally:
    # cleanup
    if hmc != None:
        hmc.logoff()
    if success:
        msg = "\nScript finished successfully.\n"
        if len(passedList) != 0:
            print "the partitions have changed successfully:"
            for parName in passedList:
                print parName
        if failedDict:
            print "the partitions have been changed failed:"
            for parName in failedDict.items():
                print "failedDict[%s]=" % parName, failedDict[parName]
        log.info(msg)
        print msg
