'''
Created on Nov 6, 2017

Specify the NIC name, which is mandatory to locate the NIC entity. You could update the NIC name, NIC description, 
adapter entity and adapter port (must appear in the same time), and the device number.
Of course, the properties should be reasonable, for example, the adapter name and port should be installed and configured in the CPC.
Only the partition name and the NIC name are mandatory.

Example:
-hmc 9.12.35.135 -cpc M90 -parName LNXT01 -nicName m90lt01_*** -adaName "OSD 0108 Z22B-03" -adaPort 1

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
parName = None
nicName = None
newNicName = None
devNum = None
nicDesc = None
vlanID = None
MACAdd = None
adaName = None
adaPort = None
logDir = None
logLevel = None
configFile = None
configFilename = None

nicUri = None
adapterUri = None
vsUri = None

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
    global parName, nicName, newNicName, devNum, nicDesc, vlanID, MACAdd, adaName, adaPort
    global logDir, logLevel, configFilename
    parser = argparse.ArgumentParser(description='Create a new NIC for partition')
    parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
    parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
    parser.add_argument('-parName', '--parName', metavar='<the name of partition to be operated>',
                        help='the name of partition to be operated')
    parser.add_argument('-nicName', '--nicName', metavar='<the name of NIC to be operated>',
                        help='the name of NIC to be operated')
    parser.add_argument('-newNicName', '--newNicName', metavar='<the new NIC name to be updated>',
                        help='the new name of NIC to be updated')
    parser.add_argument('-devNum', '--devNum', metavar='<the device number of the new created NIC>',
                        help='the device number of NIC to be operated (Possible range: 0001-ffff)')
    parser.add_argument('-nicDesc', '--nicDesc', metavar='<the description of new created NIC>',
                        help='the description of NIC to be operated')
    parser.add_argument('-adaName', '--adaName', metavar='<the name of the backing adapter>',
                        help='the name of the backing adapter')
    parser.add_argument('-adaPort', '--adaPort', metavar='<the port of the backing adapter>',
                        help='the port of the backing adapter')
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
# partion name
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
# newNIC name
    _newNicName = assertValue(pyObj=args, key='newNicName', listIndex=0, optionalKey=True)
    newNicName = checkValue('newNicName', _newNicName, newNicName)
# adapter name
    _adaName = assertValue(pyObj=args, key='adaName', listIndex=0, optionalKey=True)
    adaName = checkValue('adaName', _adaName, adaName)
# adapter port
    _adaPort = assertValue(pyObj=args, key='adaPort', listIndex=0, optionalKey=True)
    adaPort = checkValue('adaPort', _adaPort, adaPort)
# Device Number
    _devNum = assertValue(pyObj=args, key='devNum', listIndex=0, optionalKey=True)
    devNum = checkValue('devNum', _devNum, devNum)
# NIC Description
    _nicDesc = assertValue(pyObj=args, key='nicDesc', listIndex=0, optionalKey=True)
    nicDesc = checkValue('nicDesc', _nicDesc, nicDesc)
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
    print("\tnew NIC name\t%s" % newNicName)
    print("\tAdapter name\t%s" % adaName)
    print("\tAdapter port\t%s" % adaPort)
    print("\tDevice Number\t%s" % devNum)
    print("\tNIC Description\t%s" % nicDesc)

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

# ------------------------------------------------------------------ #
# ----- Start of getAdaptersOnCPC function ------------------------- #
# ------------------------------------------------------------------ #
# Get the adapter URI by given adapter name


def getAdaptersOnCPC(hmc, cpcID):
    global adapterUri
    adaRet = getCPCAdaptersList(hmc, cpcID)

    for adaInfo in adaRet:
        adaPropsTemp = getAdapterProperties(hmc, adaURI=adaInfo["object-uri"])
        if adaPropsTemp["name"] == adaName.decode("utf-8"):
            adapterUri = adaPropsTemp["object-uri"]
            return

# ------------------------------------------------------------------ #
# ----- End of getAdaptersOnCPC function --------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of getVirtualSwitchesOnCPC function ------------------ #
# ------------------------------------------------------------------ #


def getVirtualSwitchesOnCPC(hmc, cpcID):
    global adapterUri, vsUri, adaPort
    vsRet = getCPCVirtualSwitchesList(hmc, cpcID)

    for vsInfo in vsRet:
        vsPropsTemp = getVirtualSwitchProperties(hmc, vsURI=vsInfo["object-uri"])
        if vsPropsTemp["backing-adapter-uri"] == adapterUri.decode("utf-8") and vsPropsTemp["port"] == int(adaPort):
            vsUri = vsPropsTemp["object-uri"]

# ------------------------------------------------------------------ #
# ----- End of getVirtualSwitchesOnCPC function -------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of updateNicTemplate function ------------------------ #
# ------------------------------------------------------------------ #


def updateNicTemplate(hmc, partitionPropsTemp):
    global nicName, newNicName, nicUri, adapterUri, vsUri
    nicFound = False
    nicTempl = dict()
    
    for iNicUri in partitionPropsTemp['nic-uris']:
        nicEntity = getNICProperties(hmc, nicURI = iNicUri)
        if nicEntity['name'] == nicName:
            nicFound = True
            nicUri = iNicUri
            break

    if nicFound:
        if newNicName != None:
            nicTempl['name'] = newNicName
        if nicDesc != None:
            nicTempl['description'] = nicDesc
        if devNum != None:
            nicTempl['device-number'] = devNum
        if adaName != None and adaPort != None:
            getAdaptersOnCPC(hmc, cpcID)
            if adapterUri != None:
                getVirtualSwitchesOnCPC(hmc, cpcID)
            else:
                exc = HMCException("The indicated Adapter Name doesn't exist in this CPC, or couldn't get the adapter entity.")
                raise exc
            if vsUri != None:
                nicTempl['virtual-switch-uri'] = vsUri
    else:
        exc = Exception("The NIC you indicated does not exist in the partition, please check the NIC name!")
        raise exc

    return nicTempl

# ------------------------------------------------------------------ #
# ----- End of updateNicTemplate function -------------------------- #
# ------------------------------------------------------------------ #

# main function
hmc = None
success = True

try:
    parseArgs()
    setupLoggers(logDir=logDir, logLevel=logLevel)

    print "******************************"
    msg = "Update NIC in the partition"
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
    
    '''
    partitionPropsTemp = getPartitionProperties(hmc, parURI=parURI)
    
    nicTemp = updateNicTemplate(hmc, partitionPropsTemp)

    try:
        if len(nicTemp) != 0:
            if updateNICProperties(hmc, nicURI = nicUri, nicProp = nicTemp):
                print "Update NIC successfully! "
    except Exception as exc:
        excResponse = eval(exc.httpResponse)
        print "Update NIC Failed!, the reason is: " + excResponse["message"]
    '''
    
    partitionTempl = dict()
    partitionTempl["ifl-processors"] = 2
    #partitionTempl["initial-memory"] = oldMemory + (int(memoryDelta) * 1024)
    
    updatePartitionProperties(hmc, parURI=parURI, parProp = partitionTempl)
    
    
    
except Exception as exc:
    print exc

finally:
    # cleanup
    if hmc != None:
        hmc.logoff()
