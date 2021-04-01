'''
This script intends to back up general partition (and adapters) settings and configurations on a CPC and save them
into a config file for partition restore use.

Updated on Mar 31, 2021 --- Move to github
Updated on Aug 21 2020 --- Support for NVMe storage group, device number info will record in storage group backup config file, not in the partition config file
Updated on Jul 1, 2020 --- backup the adapter information after partition information, just for restore the description field at the time
                           [--adapter--]
                           100 = {'status': u'active', 'name': u'FCP 0100 A01B-02', 'adapter-family': u'ficon', 'state': u'online', 'type': u'fcp', 'description': u''}
Updated on Jun 4, 2020 --- Change adapter Name to adapter ID property in the backup config file.
Updated on Feb 11, 2020 --- Set the default encoding from ascii to utf-8
Updated on July 24, 2019 --- Update api major version to make the script support DPM R4.0
Updated on August 13, 2018 --- Add back up the boot option
                                Note, the boot dict is difference according to the boot storage group type is FCP or FICON
                                The FCP boot storage group contain {'fcp-boot-configuration-selector': 0, 'fcp-volume-uuid': '0017380030BB05FC'}
                                The FICON boot storage group contain {'fc-logical-address': '20', 'fc-unit-address': '2F'}
Updated on August 10, 2018 --- Re-factory, del un-used method and move some
Updated on August 3, 2018 --- Back up the accelerator virtual function and crypto configuration
Updated on July 23, 2018 --- Back up the FICON storage groups

@author: Daniel Wu <yongwubj@cn.ibm.com>
e.g: parsBackup.py -hmc 9.12.35.135 -cpc T257 -bakDir ./cfg
'''

from CommonAPI.prsm2api import *
from CommonAPI.wsaconst import *
from CommonAPI.readConfig import *
import CommonAPI.hmcUtils
import os, sys, datetime, logging, string, argparse

# to handle the Non ascii code, transfer python default coding from ascii to utf-8
reload(sys)
sys.setdefaultencoding('utf-8')

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
    print("\tParameters were input:")
    print("\tHMC system IP\t%s"%hmcHost)
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


# start _main_ from here
hmc = None
allParNamesList = [] # all partition names list on target CPC
allParURIsList = [] # all partition URIs list on target CPC
# Dictionary to save all partition basic configs on target CPC
allParsCfg = {}

vHBAsCfg = {} # Dictionary to save basic configs for all vHBAs on each partition

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

    # current HMC API minor version is 22, and major version greater than 2.
    if apiMinVer >= 2:
        sgIsAvai = True
    else:
        sgIsAvai = False

    # Get CPC UUID
    cpcID = cpcURI.replace('/api/cpcs/','')

    # Get all storage groups
    sgURIListByCPC = []
    sgNameListByCPC = []
    sgList = getStorageGroupList(hmc)
    for sg in sgList:
        if sg['cpc-uri'] == cpcURI:
            sgURIListByCPC.append(sg['object-uri'])
            sgNameListByCPC.append(sg['name'])
    # Define a dict to store attached SGs' info
    attachedSGs = {}
    for sgName in sgNameListByCPC:
        sgURI = sgURIListByCPC[sgNameListByCPC.index(sgName)]
        sgProps = getStorageGroupProperties(hmc, sgURI=sgURI)
        sgStorType = assertValue(pyObj=sgProps, key='type')
 
        if sgStorType == 'fcp':
            # Get virtual-storage-resource uri lists
            sgVSRsResp = getVSRsOfSG(hmc, sgURI)
            sgVSRsPropList = assertValue(pyObj=sgVSRsResp, key='virtual-storage-resources')
            # Prepare a  to store partition and SG-devNum relationship.
            attachedParDevList = []
            if sgVSRsPropList != None:
                # if VSR is not null, SG was attached and put it into attached list
                for sgVSR in sgVSRsPropList:
                    parURI = assertValue(pyObj=sgVSR, key='partition-uri')
                    devNum = assertValue(pyObj=sgVSR, key='device-number')
                    parProp = getPartitionProperties(hmc, parURI=parURI)
                    parName = assertValue(pyObj=parProp, key='name')
                    # fill attached partition names and related devNum into a list
                    attachedParDevList.append(parName+':'+devNum)
                attachedSGs[sgName] = attachedParDevList
        elif sgStorType == 'fc' or sgStorType == 'nvme':
            # FICON and NVMe storage group will not backup device numbers in partition backup config file
            pass
 
    # Define two list to store attached partition name and SG-DevNum info
    attachedSGDevList = []
    attachedParList = []
 
    for k,v in attachedSGs.items():
        for parDev in v:
            attachedParList.append(parDev.split(':')[0])
            attachedSGDevList.append(k+':'+parDev.split(':')[1])
 
    # Get partitions JSON object on this CPC
    parResObj = getCPCPartitionsList(hmc, cpcID)
 
    # Generate all partitions list on this CPC
    for parInfo in parResObj:
        _parName = assertValue(pyObj=parInfo,key='name')
        _parURI = assertValue(pyObj=parInfo,key='object-uri')
        allParNamesList.append(_parName)
        allParURIsList.append(_parURI)
   
    # Retrieve Processor and Memory settings for all partitions
    for parName in allParNamesList:

        # Dictionary to save basic configs for each partition
        parBasicCfg = dict()
        parIndex = allParNamesList.index(parName)
        parURI = allParURIsList[parIndex]
        # Get partition properties
        parProp = getPartitionProperties(hmc, parURI=parURI)
        # Save partition name, description and type
        parBasicCfg['par_desc'] = assertValue(pyObj=parProp, key='description').replace("\n", "")
        parBasicCfg['par_type'] = assertValue(pyObj=parProp, key='type')
        parBasicCfg['par_status'] = assertValue(pyObj=parProp, key='status')
        parBasicCfg['par_reserveResources'] = assertValue(pyObj=parProp, key='reserve-resources')

        # secure boot and secure execution
        parBasicCfg['par_secureboot'] = assertValue(pyObj=parProp, key='secure-boot')
        parBasicCfg['par_secureexecution'] = assertValue(pyObj=parProp, key='secure-execution')
        
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
                # get backing adapter ID
                adapProp = getAdapterProperties(hmc, adaURI=adapURI)
                #nicCfg['adapName'] = assertValue(pyObj=adapProp, key='name')
                nicCfg['adapID'] = assertValue(pyObj=adapProp, key='adapter-id')
            vNICsCfg['vNIC'+ str(i)] = nicCfg
        parBasicCfg['vNICs'] = vNICsCfg
 
        #Identify HMC version that Storage Group feature was available.
        if sgIsAvai == True:
            # For FCP storage groups
            parSGDevList = []
            for i,v in enumerate(attachedParList):
                if v == parName:
                    parSGDevList.append(str(attachedSGDevList[i]))
            parBasicCfg['sgDevNum'] = parSGDevList
 
            # For FICON and NVMe storage groups
            parFICONList = []
            parNVMeList = []
            parSGUriList = assertValue(pyObj=parProp, key='storage-group-uris')
            for parSGUri in parSGUriList:
                sgProperties = getStorageGroupProperties(hmc, sgURI=parSGUri)
                if assertValue(pyObj=sgProperties, key='type') == 'fc':
                    parFICONList.append(assertValue(pyObj=sgProperties, key='name'))
                elif assertValue(pyObj=sgProperties, key='type') == 'nvme':
                    parNVMeList.append(assertValue(pyObj=sgProperties, key='name'))
            parBasicCfg['sgFICON'] = parFICONList 
            parBasicCfg['sgNVMe'] = parNVMeList 
 
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
 
        # YJ add for the virtual function for accelerator section
        virtualFuncUriList = assertValue(pyObj=parProp, key='virtual-function-uris')
        vfCfgList = []
        for vfUri in virtualFuncUriList:
            vfRet = getVirtFuncProperties(hmc, vfUri)
            vfCfg = dict()
            vfCfg['name'] = assertValue(pyObj=vfRet, key='name')
            vfCfg['description'] = assertValue(pyObj=vfRet, key='description')
            vfCfg['device-number'] = assertValue(pyObj=vfRet, key='device-number')
 
            # I'd like to add the 'adapter-name' property in the config file, rather than the 'adapter-uri'
            # since the adapter might be changed after the MCL or JeMT roll
            # vfCfg['adapter-uri'] = assertValue(pyObj=vfRet, key='adapter-uri')
            adapProp = getAdapterProperties(hmc, adaURI=assertValue(pyObj=vfRet, key='adapter-uri'))
            vfCfg['adapter-name'] = assertValue(pyObj=adapProp, key='name')
            vfCfgList.append(vfCfg)
        parBasicCfg['zAccelerators'] = vfCfgList
 
        # YJ add the crypto-configuration for crypto
        cryptoCfg = []
        if assertValue(pyObj=parProp, key='crypto-configuration') != None:
            cryptoCfg = assertValue(pyObj=parProp, key='crypto-configuration')
            #adapNameList = []
            adapIDList = []
            for cryptoAdapterUri in cryptoCfg['crypto-adapter-uris']:
                adapProp = getAdapterProperties(hmc, adaURI=cryptoAdapterUri)
                #adapNameList.append(assertValue(pyObj=adapProp, key='name'))
                adapIDList.append(assertValue(pyObj=adapProp, key='adapter-id'))
 
            # remove the adapter uri array just add adapter ID array
            cryptoCfg.pop('crypto-adapter-uris')
            #cryptoCfg['crypto-adapter-names'] = adapNameList
            cryptoCfg['crypto-adapter-ids'] = adapIDList
        parBasicCfg['zCryptos'] = cryptoCfg
 
        # YJ add for the boot option
        bootOptCfg = dict()
        bootOptCfg['boot_device'] = assertValue(pyObj=parProp, key='boot-device')
        # only add the other properties when the boot_device is "storage group"
        if bootOptCfg['boot_device'] == 'storage-volume':
            # add the boot option parameters
            bootOptCfg['boot-timeout'] = assertValue(pyObj=parProp, key='boot-timeout')
 
            bootStorVolUri = assertValue(pyObj=parProp, key='boot-storage-volume')
            
            # defect 923564 there is a bug we have this uri equals None
            if bootStorVolUri != None:
                storVolRet = getStorVolProperties(hmc, bootStorVolUri)
     
                # add the following three useful properties of the volume
                bootOptCfg['volume_description'] = assertValue(pyObj=storVolRet, key='description')
                bootOptCfg['volume_size'] = assertValue(pyObj=storVolRet, key='size')
     
                # get the volume's parent storage group name
                bootStorGroupUri = bootStorVolUri.split('/storage-volumes/')[0]
                storGroupRet = getStorageGroupProperties(hmc, sgURI=bootStorGroupUri)
                bootOptCfg['storage_group_name'] = assertValue(pyObj=storGroupRet, key='name')
                bootOptCfg['storage_group_type'] = assertValue(pyObj=storGroupRet, key='type')
     
                # add the FCP specified parameters: boot program selector and volume uuid
                if assertValue(pyObj=storGroupRet, key='type') == 'fcp':
                    bootOptCfg['fcp-boot-configuration-selector'] = assertValue(pyObj=parProp, key='boot-configuration-selector')
                    bootOptCfg['fcp-volume-uuid'] = assertValue(pyObj=storVolRet, key='uuid')
                # add the FICON specified parameters: logical address and unit address
                elif assertValue(pyObj=storGroupRet, key='type') == 'fc':
                    ctrlUnitUri = assertValue(pyObj=storVolRet, key='control-unit-uri')
                    ctrlUnitRet = getStorageControlUnitProperties(hmc, ctrlUnitUri)
     
                    bootOptCfg['fc-logical-address'] = assertValue(pyObj=ctrlUnitRet, key='logical-address')
                    bootOptCfg['fc-unit-address'] = assertValue(pyObj=storVolRet, key='unit-address')
                # add the NVMe specified parameters: serial number
                elif assertValue(pyObj=storGroupRet, key='type') == 'nvme':
                    bootOptCfg['nvme-serial-number'] = assertValue(pyObj=storVolRet, key='serial-number')
                else:
                    # Oops
                    pass
 
        parBasicCfg['zzBootOpt'] = bootOptCfg
 
        print "%s backup is Done."%parName
        #fill allParsCfg dictionary
        allParsCfg[parName] = parBasicCfg

    # backup the adapter information (description)
    adapterDict = dict()
    for adaDict in getCPCAdaptersList(hmc, cpcID):
        adaUri = adaDict['object-uri']
        adaProp = getAdapterProperties(hmc, adaUri)
        
        adaKeyProp = dict()
        adaKeyProp['name'] = adaProp['name']
        adaKeyProp['state'] = adaProp['state']
        adaKeyProp['status'] = adaProp['status']
        adaKeyProp['adapter-family'] = adaProp['adapter-family']
        adaKeyProp['type'] = adaProp['type']
        adaKeyProp['description'] = adaProp['description']
        
        adapterDict[adaProp['adapter-id']] = adaKeyProp

    # Generate backup config file
    allConfig = ConfigParser.ConfigParser(allow_no_value=True)
    # 1. partition part
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
            elif "sgDevNum" in key2:
                allConfig.set(key1, '#FCP Storage-Groups')
                allConfig.set(key1, key2 ,allParsCfg[key1][key2])
            elif "sgFICON" in key2:
                allConfig.set(key1, '#FICON Storage-Groups')
                allConfig.set(key1, key2 ,allParsCfg[key1][key2])
            elif "sgNVMe" in key2:
                allConfig.set(key1, '#NVMe Storage-Groups')
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
            elif "zAccelerators" in key2:
                allConfig.set(key1, '#accelerator virtual functions')
                allConfig.set(key1, key2 ,allParsCfg[key1][key2])
            elif "zCryptos" in key2:
                allConfig.set(key1, '#cryptos')
                allConfig.set(key1, key2 ,allParsCfg[key1][key2])
            elif "zzBootOpt" in key2:
                allConfig.set(key1, '#boot option')
                allConfig.set(key1, key2 ,allParsCfg[key1][key2])
    # 2. adapter part
    allConfig.add_section('--adapter--')
    for key in sorted(adapterDict.keys()):
        allConfig.set('--adapter--', key, adapterDict[key])
    print "Adapters backup is Done."
    
    # check if backupDir existed or not
    if os.path.exists(backupDir) is False:
        os.makedirs(backupDir)

    # Write backup configs into a file
    filePath = backupDir + '/' + cpcName + '-Partitions-' + time.strftime("%Y%m%d-%H%M%S", time.localtime()) + '.cfg'

    with open(filePath, 'wb') as configfile:
        allConfig.write(configfile)

    if allConfig :
        print ("\n%s partitions' and adapters' configuration data are saved in below file successfully."%cpcName)
        print filePath
    else:
        print "Partition and adapters backup failed, please check the environment manually."

except Exception as exc:
    print exc
    if exc.message != None:
        print exc.message

finally:
    # cleanup
    if hmc != None:
        hmc.logoff()
