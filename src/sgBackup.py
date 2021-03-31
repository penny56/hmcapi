'''
This script intends to generally back up Storage Groups configurations on a CPC and save them
into a config file for later restoration.

Updated on Oct 26, 2020 --- Add 'unit-address' property in backup config file, no special use on restore, just record the FICON fulfilled volume ID
Updated on Aug 6, 2020 --- Support NVMe storage group
Updated on Jun 4, 2020 --- Add fulfillment state of storage group, this property will not be used when restore
Updated on Mar 2, 2020 --- Just print the storage groups back up failed, not all back up job failure
Updated on Feb 29, 2020 --- Set the default encoding from ascii to utf-8
Updated on August 10, 2018 --- Re-factory, del un-used method and move some
Updated on August 2, 2018 --- API change the 'adapter-count' field in "create storage group request body contents" to 'connectivity'
Updated on July 15, 2018 --- Back up the FICON storage groups

@author: Daniel Wu <yongwubj@cn.ibm.com> 03/21/2018
e.g: sgBackup.py -hmc 9.12.35.134 -cpc M90 -bakDir /tmp/m90-backup
'''
from prsm2api import *
from wsaconst import *
import hmcUtils
import argparse
import ConfigParser, os, sys
import datetime, readConfig, logging, string
import json

# to handle the Non ascii code, transfer python default coding from ascii to utf-8
reload(sys)
sys.setdefaultencoding('utf-8')

# hmc host IP and cpc name 
hmcHost = None
cpcName = None

# Dirs to save backup file
backupDir = None

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
    global hmcHost, cpcName,backupDir
    global logDir, logLevel
    parser = argparse.ArgumentParser(description="Back up Storage Group configurations on specified CPC")
    parser.add_argument('-hmc', '--hmc', metavar='<HMC host IP>', help='HMC host IP')
    parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
    parser.add_argument('-bakDir', '--backupDir', metavar='<backup directory>',
                        help='Directory to save backup file')
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

    #Backup directory
    _backupDir = assertValue(pyObj=args, key='backupDir', listIndex=0, optionalKey=True)
    backupDir = checkValue('backupDir', _backupDir, backupDir)
         
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
    global backupDir
    print("\tParameters were input:")
    print("\tHMC IP\t\t%s"%hmcHost)
    print("\tCPC name\t\t%s"%cpcName)
    if backupDir:
        print("\tBackup Directory --> %s"%backupDir)
    else:
        currentPath = os.getcwd()
        backupDir = currentPath
        print("\tBackup Directory --> %s"%currentPath)
# ------------------------------------------------------------------ #
# --------- End of printParams function ---------------------------- #
# ------------------------------------------------------------------ #


# Start main from here
hmc = None
# configuration for all Storage Groups on specified CPC
bakSGsConfig = dict()
# record for all storage groups get exception
bakSGsFailed = dict()

try:
    parseArgs()
    setupLoggers(logDir=logDir, logLevel=logLevel)
    
    print "*****************************************************"
    print "Back up all Storage Groups on specified CPC"
    printParams()
    print "*****************************************************"
    # initiate hmc connection 
    hmc = createHMCConnection(hmcHost=hmcHost)
    cpc = selectCPC(hmc, cpcName)
    cpcURI = assertValue(pyObj=cpc, key=KEY_CPC_URI)
    cpcName = assertValue(pyObj=cpc, key=KEY_CPC_NAME)
    cpcID = cpcURI.replace('/api/cpcs/','')
    
    # Get all storage groups 
    sgURIListByCPC = []
    sgNameListByCPC = []
    sgList = getStorageGroupList(hmc)
    for sg in sgList:
        if sg['cpc-uri'] == cpcURI:
            sgURIListByCPC.append(sg['object-uri'])
            sgNameListByCPC.append(sg['name'])
    
    for sgName in sgNameListByCPC:
        try:
            # Dict to store configuration data for single storage group
            bakSGCfg = {'sgDesc':None, #storage group description
                        'storType':None, #storage type eg: fcp or ficon
                        'sgShared':None, # Boolean, True for shared and False for dedicated
                        'sgState':None, # fulfillment state of the storage group
                        'numOfPaths':None, # number of connectivity paths aka "active adapter count". 
                        'maxNumOfPars':None, # maximum number of shared partitions.
                        'sgStorVolsCfg':None, # an array to store storage volumes config in current SG.
                        }

            sgURI = sgURIListByCPC[sgNameListByCPC.index(sgName)]
            sgProps = getStorageGroupProperties(hmc, sgURI=sgURI)
            sgStorType = assertValue(pyObj=sgProps, key='type')

            # for common properties
            bakSGCfg['sgDesc'] = assertValue(pyObj=sgProps, key='description')
            bakSGCfg['storType'] = assertValue(pyObj=sgProps, key='type')
            bakSGCfg['sgShared'] = assertValue(pyObj=sgProps, key='shared')
            bakSGCfg['sgState'] = assertValue(pyObj=sgProps, key='fulfillment-state')
            
            # for fcp and fc only properties
            if sgStorType == 'fcp' or sgStorType == 'fc':
                bakSGCfg['numOfPaths'] = assertValue(pyObj=sgProps, key='connectivity')
            
            # for fcp only properties 
            if sgStorType == 'fcp':
                bakSGCfg['maxNumOfPars'] = assertValue(pyObj=sgProps, key='max-partitions')
            
            # Retrieve storage volumes config info
            sgStorVolsCfg = []
            sgStorVolURIDict = getStorVolListOfSG(hmc, sgURI)
            sgStorVolURIList = sgStorVolURIDict['storage-volumes']
            
            for sgStorVolDict in sgStorVolURIList:
                # Dict to store single storage volume configuration
                bakStorVolCfg = {'storVolDesc':None, #storage volume description
                                 'storVolSize':None, #storage volume size
                                 'storVolUse':None,  #two choices, data or bootNone
                                 'storVolModel':None, # for FICON only
                                 'storVolDevNum':None, # for FICON only
                                 'storVolECKDtype':None, # for FICON only
                                 'storVolAdaId':None # for NVMe only
                             }
                sgStorVolURI = sgStorVolDict['element-uri']
                sgStorVolProp = getStorVolProperties(hmc, sgStorVolURI)
                
                # for common properties
                bakStorVolCfg['storVolDesc'] = assertValue(pyObj=sgStorVolProp, key='description')
                bakStorVolCfg['storVolUse'] = assertValue(pyObj=sgStorVolProp, key='usage')
                
                # for fcp and ficon only properties
                if sgStorType == 'fcp' or sgStorType == 'fc':
                    bakStorVolCfg['storVolSize'] = assertValue(pyObj=sgStorVolProp, key='size')
                
                # for ficon only properties 
                if sgStorType == 'fc':
                    # the FICON storage volume decicated properties
                    if assertValue(pyObj=sgStorVolProp, key='eckd-type') != 'base':
                        # only back up the 'base' volumes
                        continue
                    # 'unit-address' is the ID of the fulfilled volume (LCU#+VOL#), un-fulfilled volume doesn't have this property
                    bakStorVolCfg['storVolID'] = assertValue(pyObj=sgStorVolProp, key='unit-address')
                    bakStorVolCfg['storVolModel'] = assertValue(pyObj=sgStorVolProp, key='model')
                    # in FICON, only model = EAV could have the size property, otherwise the size property must not be specified
                    if bakStorVolCfg['storVolModel'] != 'EAV':
                        bakStorVolCfg.pop('storVolSize')
        
                # for ficon and nvme
                if sgStorType == 'fc' or sgStorType == 'nvme':
                    bakStorVolCfg['storVolDevNum'] = assertValue(pyObj=sgStorVolProp, key='device-number')
                
                # for nvme only properties
                if sgStorType == 'nvme':
                    adaUri = assertValue(pyObj=sgStorVolProp, key='adapter-uri')
                    adaProp = getAdapterProperties(hmc, adaURI=adaUri)
                    bakStorVolCfg['storVolAdaId'] = assertValue(pyObj=adaProp, key='adapter-id')
                    bakStorVolCfg['storVolSerNum'] = assertValue(pyObj=sgStorVolProp, key='serial-number')
    
                # Remove the properties not used
                for k, v in bakStorVolCfg.items():
                    if v == None: bakStorVolCfg.pop(k)
                # add above storage volume config to sgStorVolsCfg array.
                sgStorVolsCfg.append(bakStorVolCfg)
            bakSGCfg['sgStorVolsCfg'] = sgStorVolsCfg

            print "[%s] -> %s storage, back up..." % (sgName, sgStorType)
            # add bakSGCfg to bakSGsCfg
            bakSGsConfig[sgName] = bakSGCfg
        except Exception as exc:
            if bakSGsConfig.has_key(sgName):
                del bakSGsConfig[sgName]
            bakSGsFailed[sgName] = exc
            continue

    # Generate backup config file 
    sgConfig = ConfigParser.ConfigParser(allow_no_value=True)
    for key1 in sorted(bakSGsConfig.keys()):
        sgConfig.add_section(key1)
        for key2 in sorted(bakSGsConfig[key1].keys()):
            if bakSGsConfig[key1][key2] != None:
                if "sgDesc" in key2:
                    sgConfig.set(key1, '#Storage Group Description')
                    sgConfig.set(key1, key2 ,bakSGsConfig[key1][key2])
                elif "storType" in key2:
                    sgConfig.set(key1, '#Storage Group Type')
                    sgConfig.set(key1, key2 ,bakSGsConfig[key1][key2])
                elif "sgShared" in key2:
                    sgConfig.set(key1, '#Storage Group shared or not')
                    sgConfig.set(key1, key2 ,bakSGsConfig[key1][key2])
                elif "sgState" in key2:
                    sgConfig.set(key1, '#Storage Group fulfillment state')
                    sgConfig.set(key1, key2 ,bakSGsConfig[key1][key2])
                elif "numOfPaths" in key2:
                    sgConfig.set(key1, '#Number of paths or adapters')
                    sgConfig.set(key1, key2 ,bakSGsConfig[key1][key2])
                elif "maxNumOfPars" in key2:
                    sgConfig.set(key1, '#Maximum number of partitions')
                    sgConfig.set(key1, key2 ,bakSGsConfig[key1][key2])
                elif "sgStorVolsCfg" in key2:
                    sgConfig.set(key1, '#Storage volume configs')
                    sgConfig.set(key1, key2 ,bakSGsConfig[key1][key2])

    # check if backupDir existed or not
    if os.path.exists(backupDir) is False:
        os.makedirs(backupDir)
    
    # Write backup configs into a file
    filePath = backupDir + '/' + cpcName + '-StorGroups-' + time.strftime("%Y%m%d-%H%M%S", time.localtime()) + '.cfg'

    with open(filePath, 'wb') as configfile:
        sgConfig.write(configfile)
    
    if sgConfig :
        print "\nAbove %s Storage-Groups on %s were saved into below file successfully."%(len(bakSGsConfig),cpcName)
        print "%s"%filePath
    else:
        print "\nStorage Group backup failed, please check the environment by manual"
    
    if bakSGsFailed:
        print "\nBelow %s Storage-Groups on %s back up failed." %(len(bakSGsFailed),cpcName)
        for k, v in bakSGsFailed.items():
            print "[%s] -> reason: %s" %(k, v)
    
except Exception as exc:
    print exc
  
finally:
    # cleanup
    if hmc != None:
        hmc.logoff()