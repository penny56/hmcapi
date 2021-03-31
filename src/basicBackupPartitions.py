'''
This script intends to back up general partition settings and configurations on a CPC and save them
into a config file for partition restore use.

@author: Daniel Wu <yongwubj@cn.ibm.com>
'''
from prsm2api import *
from wsaconst import *
import hmcUtils
import argparse
import ConfigParser, os, sys
import datetime, readConfig, logging, string

# General params 
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

#Constants
WSA_URI_STORAGE_GROUP_LIST_CPC='/api/cpcs/%s/storage-groups'

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
    parser = argparse.ArgumentParser(description="Back up basic configs for all partitions on specified CPC")
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
    print("\t#Parameters were input:")
    print("\tHMC system IP\t%s"%hmcHost)
    print("\tCPC name\t%s"%cpcName)
    if backupDir:
        print("\tBackup Directory --> %s"%backupDir)
    else:
        currentPath = os.getcwd()
        backupDir = currentPath
        print("\tBackup Directory --> %s"%currentPath)
# ------------------------------------------------------------------ #
# --------- End of printParams function ---------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----------------- Start of getHBAProperties ---------------------- #
# ------------------------------------------------------------------ #
def getHBAProperties(hmcConn,
                     hbaURI=None,
                     hbaID=None,
                     parID=None):
    log.debug("Entered")
    try:
        # Check input params
        if hbaURI != None:
            URI = hbaURI
        elif hbaID != None and parID != None:
            URI = WSA_URI_HBA%parID%hbaID
        else:
            exc = HMCException("getHBAProperties",
                               "you should specify either hbaURI or both hbaID and parID")
        # get NIC properties
        return getHMCObject(hmcConn,
                            URI,
                            "Get HBA properties")
    except HMCException as exc:   # raise HMCException
        exc.setMethod("getHBAProperties")
        raise exc
    finally:
        log.debug("Completed")
# ------------------------------------------------------------------ #
# ------------------- End of getHBAProperties ---------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ------------ Start of getStorPortProperties ---------------------- #
# ------------------------------------------------------------------ #
def getStorPortProperties(hmcConn,
                     storPortURI=None,
                     adapID=None,
                     storPortID=None):
    log.debug("Entered")
    try:
        # Check input params
        if storPortURI != None:
            URI = storPortURI
        elif adpaID != None and storPortID != None:
            URI = WSA_URI_STORAGE_PORT%adapID%storPortID
        else:
            exc = HMCException("getStorPortProperties",
                               "you should specify either storPortURI or both adapID and storPortID")
        # get NIC properties
        return getHMCObject(hmcConn,
                            URI,
                            "Get Storage Port properties")
    except HMCException as exc:   # raise HMCException
        exc.setMethod("getStorPortProperties")
        raise exc
    finally:
        log.debug("Completed")
# ------------------------------------------------------------------ #
# ------------------- End of getStorPortProperties ----------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# --------------- Start of getStorageGroupListOfCPC----------------- #
# ------------------------------------------------------------------ #
def getStorageGroupListOfCPC(hmcConn,
                     cpcURI=None,
                     cpcID=None):
    log.debug("Entered")
    try:
        # Check input params
        if cpcURI != None:
            URI = cpcURI
        elif cpcID != None and cpcURI == None:
            URI = WSA_URI_STORAGE_GROUP_LIST_CPC%cpcID
        else:
            exc = HMCException("getStorageGroupListOfCPC",
                               "you should specify either cpcURI or cpcID")
        # get list of storage groups on a CPC
        return getHMCObject(hmcConn,
                            URI,
                            "Get list of storage groups on a CPC")
    except HMCException as exc:   # raise HMCException
        exc.setMethod("getStorageGroupListOfCPC")
        raise exc
    finally:
        log.debug("Completed")
# ------------------------------------------------------------------ #
# ---------------- End of getStorageGroupListOfCPC ----------------- #
# ------------------------------------------------------------------ #



# start _main_ from here
hmc = None
allParNamesList = list() # all partition names list on target CPC
allParURIsList = list() # all partition URIs list on target CPC
# Dictionary to save all partition basic configs on target CPC
allParsCfg = {} 

vHBAsCfg = dict() # Dictionary to save basic configs for all vHBAs on each partition

success = True

try:
    parseArgs()
    setupLoggers(logDir=logDir, logLevel=logLevel)
    
    print "********************************************************"
    print "Back up basic configs for all partitions on specified CPC"
    printParams()
    print "********************************************************"

    # Access HMC system and create HMC connection 
    hmc = createHMCConnection(hmcHost=hmcHost)
    cpc = selectCPC(hmc, cpcName)
    cpcURI = assertValue(pyObj=cpc, key=KEY_CPC_URI)
    cpcName = assertValue(pyObj=cpc, key=KEY_CPC_NAME)
    cpcStatus = assertValue(pyObj=cpc, key=KEY_CPC_STATUS)
    
    # HMC version check
    apiMajVer = hmc.apiMajorVer
    apiMinVer = hmc.apiMinorVer
    
    # current HMC API minor version is 22. 
    if apiMinVer >= 22:
        sgIsAvai = True
    else: 
        sgIsAvai = False
        
    # Get CPC UUID
    cpcID = cpcURI.replace('/api/cpcs/','')
    
    # Get partitions JSON object on this CPC
    parResObj = getCPCPartitionsList(hmc, cpcID)

    # Generate all partitions list on this CPC
    for parInfo in parResObj:
        _parName = assertValue(pyObj=parInfo,key='name')
        _parURI = assertValue(pyObj=parInfo,key='object-uri')
        allParNamesList.append(_parName)
        allParURIsList.append(_parURI)
        
    # Retrieve Processor and Memeory settings for all partitions
    for parName in allParNamesList:
        # Dictionary to save basic configs for each partition
        parBasicCfg = {}
        parIndex = allParNamesList.index(parName)
        parURI = allParURIsList[parIndex]
        # Get partition properties
        parProp = getPartitionProperties(hmc, parURI=parURI)
        # Save partition name, description and type
        parBasicCfg['par_desc'] = assertValue(pyObj=parProp, key='description').replace("\n", "")
        parBasicCfg['par_type'] = assertValue(pyObj=parProp, key='type')
        parBasicCfg['par_reserveResources'] = assertValue(pyObj=parProp, key='reserve-resources')

        # if ssc partition add following settings
        if assertValue(pyObj=parProp, key='type') == 'ssc':
            parBasicCfg['par_sscHostName'] = assertValue(pyObj=parProp, key='ssc-host-name')
            parBasicCfg['par_sscMasterUserid'] = assertValue(pyObj=parProp, key='ssc-master-userid')
            
            # Failed to get user pwd since it's protected and 'default' pwd returned for customization 
            parBasicCfg['par_sscMasterPW'] = 'passw0rd'
          
            if assertValue(pyObj=parProp, key='ssc-ipv4-gateway'):
                parBasicCfg['par_sscIPv4GW'] = assertValue(pyObj=parProp, key='ssc-ipv4-gateway')
            # dns servers is an array
            if assertValue(pyObj=parProp, key='ssc-dns-servers'):
                parBasicCfg['par_sscDNS'] = ','.join(assertValue(pyObj=parProp, key='ssc-dns-servers'))

        # Save Processor
        ifl_proc_num = assertValue(pyObj=parProp, key='ifl-processors')
        cp_proc_num = assertValue(pyObj=parProp, key='cp-processors')
        if ifl_proc_num > 0:
            proc_type = 'ifl'
            proc_num = ifl_proc_num
        elif cp_proc_num > 0:
            proc_type = 'cp'
            proc_num = cp_proc_num
        parBasicCfg['proc_type'] = proc_type
        parBasicCfg['proc_mode'] = assertValue(pyObj=parProp, key='processor-mode')
        parBasicCfg['proc_num'] = proc_num
        
        #Save Memory
        parBasicCfg['init_mem'] = assertValue(pyObj=parProp, key='initial-memory')
        parBasicCfg['max_mem'] = assertValue(pyObj=parProp, key='maximum-memory')

        #vNIC
        # get vNIC URIs list for target partition
        nicURIs = assertValue(pyObj=parProp, key='nic-uris')
        # Dictionary to save basic configs for all vNICs on each partition 
        vNICsCfg = dict()
        i=0
        for nicURI in nicURIs:
            # Dictionary to save each vNIC configurations
            nicCfg = dict()
            i+=1
            #get vNIC properties
            nicProp = getNICProperties(hmc, nicURI=nicURI)
            
            nicCfg['name'] = assertValue(pyObj=nicProp, key='name')
            nicCfg['desc'] = assertValue(pyObj=nicProp, key='description').replace("\n", "")
            nicCfg['devNum'] = assertValue(pyObj=nicProp, key='device-number')
             
            # if ssc partition add ssc related vNIC settings
            if assertValue(pyObj=parProp, key='type') == 'ssc':
                if bool(assertValue(pyObj=nicProp, key='ssc-management-nic')) == True:
                    nicCfg['sscIPAddrType'] = assertValue(pyObj=nicProp, key='ssc-ip-address-type')
                    nicCfg['sscIPAddr'] = assertValue(pyObj=nicProp, key='ssc-ip-address')
                    nicCfg['sscMaskPrefix'] = assertValue(pyObj=nicProp, key='ssc-mask-prefix')
                   
                    if assertValue(pyObj=nicProp, key='vlan-id'):
                        nicCfg['vlanID'] = assertValue(pyObj=nicProp, key='vlan-id')
            # if backing adapter type is OSD 
            if assertValue(pyObj=nicProp, key='type') == 'osd':
                #Get virtual switch properties to retrieve adapter settings.
                vsProp = getVirtualSwitchProperties(hmc, vsURI=assertValue(pyObj=nicProp, key='virtual-switch-uri'))
                adapURI = assertValue(pyObj=vsProp, key='backing-adapter-uri')
                # add adapter port
                nicCfg['adapPort'] = assertValue(pyObj=vsProp, key='port')
                # get backing adapter name
                adapProp = getAdapterProperties(hmc, adaURI=adapURI)
                nicCfg['adapName'] = assertValue(pyObj=adapProp, key='name')
            vNICsCfg['vNIC'+ str(i)] = nicCfg
        parBasicCfg['vNICs'] = vNICsCfg
        
        #Identify HMC version that Storage Group feature was available. 
        if sgIsAvai == True:
            print 'Warning: [%s] storage groups will not be backed up this time'%parName
        elif sgIsAvai == False:
            # Deal with old vHBA storage design.
            # Get vHBA URIs list for target partition
            hbaURIs = assertValue(pyObj=parProp, key='hba-uris')
            # Dictionary to save basic configs for all vHBAs on each partition 
            vHBAsCfg = dict()
            i=0
            for hbaURI in hbaURIs:
                # Dictionary to save each vHBA configurations
                hbaCfg = dict()
                i+=1
                #get vHBA properties
                hbaProp = getHBAProperties(hmc, hbaURI=hbaURI)
                
                hbaCfg['name'] = assertValue(pyObj=hbaProp, key='name')
                hbaCfg['desc'] = assertValue(pyObj=hbaProp, key='description').replace("\n", "")
                hbaCfg['devNum'] = assertValue(pyObj=hbaProp, key='device-number')
                adapPortURI = assertValue(pyObj=hbaProp, key='adapter-port-uri')
                # get storage port properties
                storPortProp = getStorPortProperties(hmc, storPortURI=adapPortURI)
                adapURI = assertValue(pyObj=storPortProp, key='parent')
                # get backing adapter name
                adapProp = getAdapterProperties(hmc, adaURI=adapURI)
                hbaCfg['adapName'] = assertValue(pyObj=adapProp, key='name')
                
                vHBAsCfg['vHBA'+ str(i)] = hbaCfg
            parBasicCfg['vHBAs'] = vHBAsCfg
        #fill allParsCfg dictionary
        allParsCfg[parName] = parBasicCfg     
        
    # Generate backup config file
    allConfig = ConfigParser.ConfigParser(allow_no_value=True)
    for key1 in sorted(allParsCfg.keys()):
        allConfig.add_section(key1)
        for key2 in sorted(allParsCfg[key1].keys()):
            if "par" in key2:
                allConfig.set(key1, '#partition')
                allConfig.set(key1, key2 ,allParsCfg[key1][key2])
            elif "proc" in key2:
                allConfig.set(key1, '#processor')
                allConfig.set(key1, key2 ,allParsCfg[key1][key2])
            elif "mem" in key2:
                allConfig.set(key1, '#memory')
                allConfig.set(key1, key2 ,allParsCfg[key1][key2])
            elif "vNICs" in key2:
                allConfig.set(key1, '#virtual NICs')
                for key3 in sorted(allParsCfg[key1][key2].keys()):
                    for key4 in sorted(allParsCfg[key1][key2][key3].keys()):
                        allConfig.set(key1, key3 + '_' + key4, allParsCfg[key1][key2][key3][key4])
            elif "vHBAs" in key2:
                allConfig.set(key1, '#virtual HBAs')
                for key3 in sorted(allParsCfg[key1][key2].keys()):
                    for key4 in sorted(allParsCfg[key1][key2][key3].keys()):
                        allConfig.set(key1, key3 + '_' + key4, allParsCfg[key1][key2][key3][key4])
    
    # check if backupDir existed or not
    if os.path.exists(backupDir) is False:
        os.makedirs(backupDir)
            
    # Write backup configs into a file
    filePath = backupDir + '/' + cpcName + '-Partitions-' + time.strftime("%Y%m%d-%H%M%S", time.localtime()) + '.cfg'

    with open(filePath, 'wb') as configfile:
        allConfig.write(configfile)
    
    if allConfig :
        print ("%s partitions' configuration were saved in below file successfully."%cpcName)
        print filePath
    else:
        print "Partition backup failed, please check the environment by manual"
        
except Exception as exc:
    print exc
  
finally:
    # cleanup
    if hmc != None:
        hmc.logoff()



