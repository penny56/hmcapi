'''
Created on 11/08/2017 
This script intends to update Virtual Function settings per user's input,which currently only allow changing VF properties for single partition.

@auther : Daniel Wu <yongwubj@cn.ibm.com>
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

# partition name
parName = None

# virtual function name
vfName=None

# virtual function new name
vfNewName=None

# virtual function new description 
vfNewDesc=None

# virtual function new device number
vfNewDevNum=None

# new adapter backing this virtual function
vfNewAdapName=None

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
    global parName, vfName, vfNewName, vfNewDesc, vfNewDevNum, vfNewAdapName
    global logDir, logLevel
    parser = argparse.ArgumentParser(description="update zEDC virtual function for single partition")
    parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
    parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
    parser.add_argument('-parName','--parName',metavar='<single partition name allowed only>',
                        help='set a partition name')
    parser.add_argument('-vfName','--vfName',metavar='<virtual function name>', 
                        help='specify virtual function name associated with input partition')
    parser.add_argument('-vfNewName','--vfNewName', metavar='<virtual function new name>',
                        help='set new virtual function name you will change')
    parser.add_argument('-vfNewDesc','--vfNewDesc', metavar='<virtual function new description>',
                        help='set virtual function new description')
    parser.add_argument('-vfNewDevNum','--vfNewDevNum', metavar='<virtual function new device number>',
                        help='set virtual function new device number you will change')
    parser.add_argument('-vfNewAdapName','--vfNewAdapName', metavar='<virtual function new adapter name>',
                        help='set new adapter name you will change to switch')    
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
        msg = 'partition name should be provided'
        print msg
        
    #virtual function name
    _vfName = assertValue(pyObj=args, key='vfName', listIndex=0, optionalKey=True)
    vfName = checkValue('vfName', _vfName, vfName)
    if vfName == None:
        print 'virtual function name should be provided'
        
    #virtual function new name
    _vfNewName = assertValue(pyObj=args, key='vfNewName', listIndex=0, optionalKey=True)
    vfNewName = checkValue('vfNewName', _vfNewName, vfNewName)
    
    #virtual function new description 
    _vfNewDesc = assertValue(pyObj=args, key='vfNewDesc', listIndex=0, optionalKey=True)
    vfNewDesc = checkValue('vfNewDesc', _vfNewDesc, vfNewDesc)
    
    #virtual function new device number
    _vfNewDevNum = assertValue(pyObj=args, key='vfNewDevNum', listIndex=0, optionalKey=True)
    vfNewDevNum = checkValue('vfNewDevNum', _vfNewDevNum, vfNewDevNum)
    
    #virtual function new adapter name
    _vfNewAdapName = assertValue(pyObj=args, key='vfNewAdapName', listIndex=0, optionalKey=True)
    vfNewAdapName = checkValue('vfNewAdapName', _vfNewAdapName, vfNewAdapName)
    
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
    if vfName == None:
        print 'virtual function name must be provided'
    else:
        print("\tVF Name\t\t%s\n"%vfName)
    if vfNewName == None and vfNewDesc == None and vfNewDevNum == None and vfNewAdapName == None:
        print 'At lease provide one param for <vfNewName, vfNewDesc, vfNewDevNum, vfNewAdapName> to proceed VF change'
        exit(1)
    else:
        if vfNewName != None:
            print("\tVF new name          -> %s"%vfNewName)
        if vfNewDesc != None:
            print("\tVF new description   -> %s"%vfNewDesc)
        if vfNewDevNum != None:
            print("\tVF new device number -> %s"%vfNewDevNum)
        if vfNewAdapName != None:
            print("\tVF new adapter name  -> %s"%vfNewAdapName)
            
# ------------------------------------------------------------------ #
# --------- End of printParams function ---------------------------- #
# ------------------------------------------------------------------ #

# start _main_ from here
hmc = None
vfName = None
vfNewProp = {}
vfDevNumList = list()

success = True

try:
    parseArgs()
    setupLoggers(logDir=logDir, logLevel=logLevel)
    
    print "***********************************"
    print "Update virtual function for specified partition"
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
    # Get partitions JSON object on this CPC
    parResObj = getCPCPartitionsList(hmc, cpcID)
    
    # locate partition and get partition URI
    for parInfo in parResObj:
        _parName = assertValue(pyObj=parInfo,key='name')
        if _parName == parName:
            parURI = assertValue(pyObj=parInfo,key='object-uri')
            
    if parURI != None:
        parID = parURI.replace('/api/partitions/','')
    else:
        print 'partition <%s> was not found on cpc <%s>'%(parName,cpcName)
    # locate virtual function and get current VF properties
    ret = selectVirtFunc(hmc,parID,vfName)
    
    vfOldURI = assertValue(pyObj=ret, key=KEY_VF_URI)
    vfOldDevNum = assertValue(pyObj=ret, key=KEY_VF_DEV_NUM)
    
    if vfOldURI == None:
        print 'Warning: virtual function <%s> was not found in this partition <%s>'%(vfName,parName)
    else:        
        # Determine if changes need be made or not and fill new VF properties dictionary
        if vfNewName != None:
            vfNewProp['name'] = vfNewName
        # No need handle if description existed or not, lower priority.
        if vfNewDesc != None:
            vfNewProp['description'] = vfNewDesc
        # if no new adapter provided, will not change it
        if vfNewAdapName != None:
            # if new adapter provided, Get new adapter URI
            newAdapRet = selectAdapter(hmc,vfNewAdapName,cpcID)
            newAdapURI = assertValue(pyObj=newAdapRet, key=KEY_ADAPTER_URI)
            vfNewProp['adapter-uri'] = newAdapURI    
        # if no new device number provided, will not change it
        if vfNewDevNum != None:
            # Get a list of all virtual function device number on this partition
            parRet = getPartitionProperties(hmc,parID=parID)
            vfAllURIs = assertValue(pyObj=parRet, key='virtual-function-uris')
            for vfURI in vfAllURIs:
                vfRet = getVirtFuncProperties(hmc,vfURI)
                _vfDevNum = assertValue(pyObj=vfRet, key='device-number')
                vfDevNumList.append(_vfDevNum)
            # pop out device number used by current VF
            # vfDevNumList.remove(vfOldDevNum)
            # if input device number is equal to current, keep using it
            if vfNewDevNum == vfOldDevNum:
                vfNewProp['device-number'] = vfOldDevNum
            else:
                # check if device number was used or not in existing device number list
                if vfNewDevNum not in vfDevNumList:
                    vfNewProp['device-number'] = vfNewDevNum
                else:
                    print 'Warning:VF Device Number %s was used by other virtual function, please set new one'%vfNewDevNum
        if vfNewProp:
            # update new VF properties
            ret = updateVirtFuncProperties(hmc, virtFuncURI=vfOldURI, virtFuncProp=vfNewProp)
            print 'Virtual Function <%s> in this partition <%s:%s> has been modified successfully'%(vfName, cpcName, parName)
        else:
            print 'Warning: Please issue <--help or -h> to enter correct values for VF changes'
except Exception as exc:
    print exc
  
finally:
    # cleanup
    if hmc != None:
        hmc.logoff()
