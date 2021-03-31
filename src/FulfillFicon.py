'''
Created on Oct 19, 2017

List the required partition(s)'s vNIC(s) information. If the partition(s) range indicated explicitly, list the information, or if no partition indicated,
list all shared partitions' information in the CPC.

Example:
-hmc 9.12.35.135 -cpc M90

@author: mayijie
'''

from CommonAPI.prsm2api import *
from CommonAPI.wsaconst import *
import CommonAPI.hmcUtils
import argparse
import logging
import sys
from prsm2api import selectStorageGroup
from timeit import default_timer as timer

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
TAB = 13
colWidth = TAB * 2
colOrder = ('Partition Name', 'Name', 'Device Number', 'Adapter Name', 'Adapter Port',
            'Card Type', 'VLAN ID & Type', 'MAC Address', 'Description')

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
# --------- Start of getPartitionsOnCPC function ------------------- #
# ------------------------------------------------------------------ #


def getPartitionsOnCPC(hmc, cpcID):
    global sharedModeParNamesList, sharedModeParURIsList, parState

    parRet = getCPCPartitionsList(hmc, cpcID)

    for parInfo in parRet:
        wholeParNamesList.append(assertValue(pyObj=parInfo, key='name'))
        wholeParURIsList.append(assertValue(pyObj=parInfo, key='object-uri'))
        parState[parInfo['name']] = parInfo['status']

# ------------------------------------------------------------------ #
# ----- End of getPartitionsOnCPC function ------------------------- #
# ------------------------------------------------------------------ #

def ffill():
    sg_uri = selectStorageGroup(hmc, "T90_B00C_FICON_SG")
    sg_id = sg_uri.replace('/api/storage-groups/', '')
    
    svs = listStorageVolumeOfStorageGroup(hmc, sg_id)
    for sv_dict in svs:
        sv_uri = sv_dict['element-uri'].encode('utf-8')
        
        #sv_id = sv_uri.split('/storage-volumes/')[1]
        #print "sv id = ", sv_id
        
        #storVolRet = getStorVolProperties(hmc, sv_uri)
        
        svTempl = dict()
        #svTempl['control-unit-uri'] = assertValue(pyObj=storVolRet, key='control-unit-uri')
        #svTempl['unit-address'] = assertValue(pyObj=storVolRet, key='unit-address')
        svTempl['control-unit-uri'] = '/api/storage-control-units/b2e4d6a6-8174-11e9-b704-00106f240da2'
        svTempl['unit-address'] = '0c'
        start = timer()
        if fulfillFiconStorageVolume(hmc, sv_uri, svTempl):
            print "fulfill success!"
        else:
            print "fulfill failed!"
        end = timer()
        
        print "cost = ", (end - start)

def ffills():
    sg_uri = selectStorageGroup(hmc, "T90_B00C_FICON_SG")
    sg_id = sg_uri.replace('/api/storage-groups/', '')
    
    svs = listStorageVolumeOfStorageGroup(hmc, sg_id)
    
    fulfillmentInfoArray = []
    #unit_add = ['16', '17', '18', '19', '1a']
    unit_add = ['16', '17']
    for sv_dict in svs:
        # volume-fulfillment-info object 
        vfi = dict()
        vfi['storage-volume-uri'] = sv_dict['element-uri'].encode('utf-8')
        
        # the control-unit-uri could get from any fulfilled storage group's volume property in the same CPC
        vfi['control-unit-uri'] = '/api/storage-control-units/b2e4d6a6-8174-11e9-b704-00106f240da2'
        vfi['unit-address'] = unit_add.pop()
        fulfillmentInfoArray.append(vfi)
    
    bodyTempl = dict()
    bodyTempl['fulfillment-info'] = fulfillmentInfoArray
    
    print "ffills bodyTempl =", bodyTempl
    
    start = timer()
    if fulfillFiconStorageVolumes(hmc, sg_uri, bodyTempl):
        print "fulfill success!"
    else:
        print "fulfill failed!"
    end = timer()
    
    print "cost = ", (end - start)

# 927464 DPM API: An API client should not be able to modify the usage property of a FICON alias volume
def modifyFICON():

    sg_uri = selectStorageGroup(hmc, "T90_B002_FICON_Data_SG")
    sg_id = sg_uri.replace('/api/storage-groups/', '')
    
    sgProps = getStorageGroupProperties(hmc, sgURI=sg_uri)
    
    print "sg properties is: ", sgProps
    
    svs = listStorageVolumeOfStorageGroup(hmc, sg_id)
    sv_uri = '/api/storage-groups/29ba310c-2504-11eb-9975-00106f24cbe8/storage-volumes/122a1bda-2507-11eb-9f39-00106f24cbe8'
    for sv_dict in svs:
        if sv_dict['element-uri'].encode('utf-8') == sv_uri :
            sv_ret = getStorageVolumeProperties(hmc, sv_uri)
            print sv_ret
        
    sgTempl = dict()
    sgTempl = {u'storage-volumes': [{u'operation': u'modify', u'element-uri': u'/api/storage-groups/29ba310c-2504-11eb-9975-00106f24cbe8/storage-volumes/122a1bda-2507-11eb-9f39-00106f24cbe8', u'model': '3'}]}
    
    modifyStorageGroup(hmc, sg_id, sgTempl)
    
    print "after modify"
    
    for sv_dict in svs:
        if sv_dict['element-uri'].encode('utf-8') == sv_uri :
            sv_ret = getStorageVolumeProperties(hmc, sv_uri)
            print sv_ret
        
# main function
hmc = None
success = True

try:
    parseArgs()
    setupLoggers(logDir=logDir, logLevel=logLevel)

    print "******************************"
    msg = "list partition vNICs condition"
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

    # ffill()
    # ffills()
    modifyFICON()

except Exception as exc:
    print exc

finally:
    # cleanup
    if hmc != None:
        hmc.logoff()
