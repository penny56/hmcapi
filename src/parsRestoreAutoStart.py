'''
Created on Dec 5, 2017

Updated on August 31, 2018 --- Update set device number method and auto start method. Will update according to the FCPAdapters.cfg file
                               In the config file, will list all the adapters in each cpc, and the preferred device numbers for cisco and brocade
                               The config file looks like:
                                [M90]
                                # adapters in M90, the section title should exactly match the cpcName
                                164 = cisco
                                1d8 = cisco
                                158 = cisco
                                118 = cisco
                                1e5 = brocade
                                1a4 = brocade
                                1e4 = brocade
                                124 = brocade
                                
                                [M257]
                                # adapters in M257
                                168 = cisco
                                148 = cisco
                                108 = cisco
                                128 = cisco
                                16c = brocade
                                12c = brocade
                                14c = brocade
                                10c = brocade
                                
                                [cisco]
                                # hare must have a section named following the values in the cpc sections
                                6000 =
                                7000 =
                                8000 =
                                9000 =
                                
                                [brocade]
                                6100 =
                                7100 =
                                8100 =
                                9100 =
Updated on August 14, 2018 --- Restore the boot option and try to start the partition automatically
Updated on August 7, 2018 --- Restore the accelerator virtual function and crypto configuration
Updated on July 24, 2018 --- Add support for FICON Storage Group, no need to consider the device number for FICON storage groups
Updated on Mar 6, 2018 --- Add support for Storage Group in DPM R3.1.
    Here in the cfg file, we add the section for storage group, it indicate the storage group names.
    And boot lun in the boot option section.
Updated on Apr 23, 2018 --- Rename from createPartitions_sg to parsRestore
Updated on Apr 24, 2018 --- cfg file update the sg format to
    #storage groups
    sgdevnum = ['M90_KVMT02_XIV_Dedicated_SG:9000', 'M90_KVMT02_XIV_Dedicated_SG:9100', 'M90_XIV_Shared_Products_SG:7000', 'M90_KVMTestPartition_LGM_XIV_SG:6000', 'M90_KVMTestPartition_LGM_XIV_SG:6100']
    In this version, we forgive to set the boot option, since the volume ID maight be changed after jmet roll, so we decide to update the boot option manually before we start the partition
    For the device number, if a storage group is 2-path, there will be 2 vhba in the partition.
    In this case, the script just set the two device number random for each vhba, please update it manually if needed.
Updated on May 9, 2018 --- enable the update device number function.

This script is one step for the whole backup / restore process loop. The loop include:
-- Back up the current partition information and storage group information to cfg files (sgBackup, parsBackup)
-- JMeT roll or something
-- Restore the storage group information, this process will send storage request to the storage admin (sgRestore.py)
-- Wait until the storage group request are all fulfilled and in complete state
-- Restore the partition information, this process will create the partition, add vNics and attach storage groups (parsRestore.py)

This script is to create partitions by configure file. Only the baic information - processor and memory - will be set in this script.
vNIC, vHBA and others would be added manually in this stage.
All the partition information will be created simultaneously by multi-threading.

You couldn't indicate the 'cp' processor type in a 'ifl' only cpc (M90), or you will encounter a "Cp processor is not available" exception!

Example:
-hmc 9.12.35.135 -cpc M90 -config createP2Partition.cfg

config file example:
[M257-KVMP11-0823]
#memory
init_mem = 102400
max_mem = 204800
#partition
par_desc = KVMP11 - Production: KVM for IBM z Systems 1.1.3-beta4.2 (Zeus) | Reserve Checked
par_reserveresources = False
par_status = active
par_type = linux
#processor
proc_mode = shared
proc_num = 8
proc_type = ifl
#fcp storage-groups
sgdevnum = ['M257_Shared_Products_XIV_SG:7000', 'M257_Shared_Products_XIV_SG:7100', 'M257_M90_KVMProdPart_LGM_XIV_SG:6000', 'M257_M90_KVMProdPart_LGM_XIV_SG:6100', 'M257_KVMP11_Dedicated_XIV_SG:9000', 'M257_KVMP11_Dedicated_XIV_SG:9100']
#ficon storage-groups
sgficon = []
#virtual nics
vnic1_adapname = OSD 0174 A01B-18
vnic1_adapport = 0
vnic1_desc = 10 Dot Network Access Mode VLAN 1292
vnic1_devnum = 1000
vnic1_name = m257kp11_10DotNetwork_AccessMode_VLAN1292
vnic2_adapname = OSD 0150 A01B-07
vnic2_adapport = 0
vnic2_desc = OVSBridge
vnic2_devnum = 1100
vnic2_name = m257kp11_OVSBridge
vnic3_adapname = OSD 0154 A01B-08
vnic3_adapport = 0
vnic3_desc = MACVTAP
vnic3_devnum = 1003
vnic3_name = m257kp11_MACVTAP
#accelerator virtual functions
zaccelerators = []
#cryptos
zcryptos = []
#boot option
zzbootopt = {'fcp-boot-configuration-selector': 0, 'fcp-volume-uuid': '0017380030BB1117', 'volume_description': 'M257_KVMP11_Boot_Volume', 'storage_group_type': 'fcp', 'volume_size': 48.08, 'storage_group_name': 'M257_KVMP11_Dedicated_XIV_SG', 'boot_device': 'storage-volume', 'boot-timeout': 60}


@author: mayijie
'''

from prsm2api import *
from wsaconst import *
import hmcUtils
import sys, ConfigParser, logging, threading, os, argparse, traceback, re

hmc = None
cpcID = None

hmcHost = None
cpcName = None
configFile = None
createPass = list()
createFail = list()
couldStart = dict()

# the key is the partition name, the value is the properties of the partition, by dict format
sectionDict = dict()

# default SSC partition master password
SSC_MASTER_PASSWORD = 'passw0rd'

# the key is the key from config file, the value is the standard API field name
# All option names are passed through the optionxform() method. Its default implementation converts option names to lower case. So the keys use lower case here!
PARTITION_API_MAP = {'par_type' : 'type',
                     'par_desc' : 'description',
                     'par_reserveresources' : 'reserve-resources',      # boolean
                     'proc_mode' : 'processor-mode',
                     'proc_type' : None,
                     'proc_num' : ['cp-processors', 'ifl-processors'],
                     'init_mem' : 'initial-memory',
                     'max_mem' : 'maximum-memory',
                     'vnic' : None,
                     'sgdevnum' : None, 
                     'sgficon' : None,
                     'zaccelerators' : None,
                     'zcryptos' : None,
                     'zzbootopt' : None
                    }

# additional properties for the SSC partition
SSC_API_MAP = {'par_sschostname' : 'ssc-host-name',
               'par_sscmasteruserid' : 'ssc-master-userid',
               'par_sscmasterpw' : 'ssc-master-pw',
               # following are optional
               'par_sscdns' : 'ssc-dns-servers',                 # Array of string
               'par_sscipv4gw' : 'ssc-ipv4-gateway',
              }

# properties for the nic object
NIC_API_MAP = {'name' : 'name',
               'adapname' : None,
               'adapport' : None,
               'devnum' : 'device-number',
               'desc' : 'description',
               # following properties are for ssc partitions
               'sscipaddr' : 'ssc-ip-address',
               'sscipaddrtype' : 'ssc-ip-address-type',
               'sscmaskprefix' : 'ssc-mask-prefix',
               'vlanid' : 'vlan-id'
              }

# for FCP storage groups device number setting
FCP_CONFIG_FILE = 'FCPAdapters.cfg'
fcpAdapterDict = dict()

# for multi-thread write protection
lock = threading.Lock()

# ------------------------------------------------------------------ #
# ----- Start of parseArgs function -------------------------------- #
# ------------------------------------------------------------------ #
def parseArgs():
    print ">>> parsing the input parameters..."
    global hmcHost, cpcName, configFile
    
    parser = argparse.ArgumentParser(description='create partitions by configure file')
    parser.add_argument('-hmc', '--hmcHost', metavar='<HMC host IP>', help='HMC host IP')
    parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
    parser.add_argument('-config', '--configFile', metavar='<configure file name>', help='indicate configure file name / location')
    try:
        # return the dict of all the input parameters
        args = vars(parser.parse_args())
        _hmcHost = assertValue(pyObj=args, key='hmcHost', listIndex=0, optionalKey=True)
        hmcHost = checkValue('hmcHost', _hmcHost , hmcHost)
        if hmcHost == None:
            exc = Exception("You should specify the HMC eHost IP")
            raise exc
        _cpcName = assertValue(pyObj=args, key='cpcName', listIndex=0, optionalKey=True)
        cpcName = checkValue('cpcName', _cpcName, cpcName)
        if cpcName == None:
            exc = Exception("You should specify the CPC Name")
            raise exc
        _configFile = assertValue(pyObj=args, key='configFile', listIndex=0, optionalKey=True)
        configFile = checkValue('configFile', _configFile, configFile)
        if configFile == None:
            exc = Exception("You should specify the configure file name / path")
            raise exc
    except Exception as exc:
        print "[EXCEPTION parseArgs] Mandatory parameter missed:", exc 
        raise exc
    finally:
        print ">>> Parsing parameters complete!"

# ------------------------------------------------------------------ #
# ----- End of parseArgs function ---------------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of loadConfig function ------------------------------- #
# ------------------------------------------------------------------ #
def loadConfig(configFile, dic):
    print ">>> loading the config file..."
    
    try:
        if configFile == None:
            exc = IOError("Empty file or directory name")
            exc.errno = 2
            raise exc
        if '/' not in configFile:
            configFile = os.path.join(sys.path[0], configFile)
        config = ConfigParser.RawConfigParser()
        config.readfp(open(configFile))
        
        sections = config.sections()
        for section in sections:
            itemDict = dict()
            items = config.items(section)
            for key, value in items:
                itemDict[key] = value
            dic[section] = itemDict

    except IOError as exc:
        print "[EXCEPTION IOError loadConfig] Cannot load configuration file [%s]: %s"%(configFile, exc)  
        raise exc
    except Exception as exc:
        print "[EXCEPTION loadConfig] Cannot load configuration file [%s]: %s"%(configFile, exc)  
        raise exc
    finally:
        print ">>> loading config file complete!"

# ------------------------------------------------------------------ #
# ----- End of loadConfig function --------------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of procSinglePartition function ---------------------- #
# ------------------------------------------------------------------ #
def procSinglePartition(parName):
    global sectionDict
    try:
        if lock.acquire():
            partitionDict = sectionDict[parName]
            (parTemp, vnicDict, sgDevNumDict, ficonList, acceList, cryptoDict, bootOptionDict) = createPartitionTemplate(parName, partitionDict)
            lock.release()
        if lock.acquire():
            partRet = createPartition(hmc, cpcID, parTemp)
            lock.release()
        if lock.acquire():
            if partRet != None:
                couldStart = False
                createPass.append(parName)
                if len(vnicDict) != 0:
                    constructVnics(partRet, parName, vnicDict)
                if len(sgDevNumDict) != 0:
                    constructStorageGroups(partRet, parName, sgDevNumDict=sgDevNumDict)
                    setDeviceNumber(partRet, parName, sgDevNumDict)
                if len(ficonList) != 0:
                    constructStorageGroups(partRet, parName, ficonList=ficonList)
                if len(acceList) != 0:
                    constructAccelerators(partRet, parName, acceList)
                if len(cryptoDict) != 0:
                    constructCryptos(partRet, parName, cryptoDict)
                if len(bootOptionDict) != 0:
                    couldStart = setBootOption(partRet, parName, bootOptionDict)
                if partitionDict['par_status'] == 'active' and couldStart:
                    startThePartitionAndCheck(partRet, parName)
            else:
                createFail.append(parName)
            lock.release()
    except Exception as exc: 
        print "[EXCEPTION procSinglePartition] partition", parName
        print
        '''
        print '-'*60
        traceback.print_exc(file=sys.stdout)
        print '-'*60
        '''
        # no need to add "if lock.acquire():" here since the lock must be occupied, just release.
        createFail.append(parName)
        lock.release()

# ------------------------------------------------------------------ #
# ----- End of procSinglePartition function ------------------------ #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of createPartitionTemplate function ------------------ #
# ------------------------------------------------------------------ #
def createPartitionTemplate(parName, partitionDict):
    global PARTITION_API_MAP
    iProcNum = None
    iProcType = None
    partitionTempl = dict()
    vnicDict = dict()
    sgDevNumDict = dict()
    ficonList = []
    acceList = []
    cryptoDict = dict()
    bootOptionDict = dict()
    
    try:
        partitionTempl['name'] = parName
        # retrieve all the fields we want, to product a partition
        for propertyKey in PARTITION_API_MAP.keys():
            if partitionDict.has_key(propertyKey):
                # the config file section include this property
                if (propertyKey == 'par_type'): 
                    partitionTempl[PARTITION_API_MAP[propertyKey]] = partitionDict[propertyKey]
                    if (partitionDict[propertyKey] == "ssc"):
                        for sscKey in SSC_API_MAP.keys():
                            if partitionDict.has_key(sscKey):
                                if sscKey == 'par_sscdns':
                                    # par_sscdns is a String Array
                                    partitionTempl[SSC_API_MAP[sscKey]] = partitionDict[sscKey].split(',')
                                else:
                                    partitionTempl[SSC_API_MAP[sscKey]] = partitionDict[sscKey]
                            elif sscKey == 'par_sscmasterpw':
                                # set a default ssc master password if it not indicated in the config file
                                partitionTempl[SSC_API_MAP[sscKey]] = SSC_MASTER_PASSWORD
                            else:
                                # only [hostname, masterid, masterpwd] are mandatory, others are optional
                                pass
                elif (propertyKey == 'proc_mode' or propertyKey == 'par_desc'):
                    partitionTempl[PARTITION_API_MAP[propertyKey]] = partitionDict[propertyKey]
                elif (propertyKey == 'par_reserveresources'):
                    partitionTempl[PARTITION_API_MAP[propertyKey]] = True if (partitionDict[propertyKey].lower() == 'true') else False
                elif (propertyKey == 'init_mem' or propertyKey == 'max_mem'):
                    if (int(partitionDict[propertyKey]) < 1024):
                        partitionTempl[PARTITION_API_MAP[propertyKey]] = int(partitionDict[propertyKey]) * 1024
                    else:
                        partitionTempl[PARTITION_API_MAP[propertyKey]] = int(partitionDict[propertyKey])
                elif (propertyKey == 'proc_type'):
                    if iProcNum == None:
                        # the processor number has not been set, store this type and set the value when parse the processor number
                        iProcType = partitionDict[propertyKey].lower()
                    else:
                        if partitionDict[propertyKey].lower() == 'cp':
                            partitionTempl[PARTITION_API_MAP['proc_num'][0]] = iProcNum
                        elif partitionDict[propertyKey].lower() == 'ifl':
                            partitionTempl[PARTITION_API_MAP['proc_num'][1]] = iProcNum
                        else:
                            exc = Exception("The procType should either be 'cp' or be 'ifl', other values invalid!")
                            raise exc
                elif (propertyKey == 'proc_num'):
                    if iProcType == None:
                        iProcNum = int(partitionDict[propertyKey])
                    else:
                        if iProcType == "cp":
                            partitionTempl[PARTITION_API_MAP['proc_num'][0]] = int(partitionDict[propertyKey])
                        elif iProcType == "ifl":
                            partitionTempl[PARTITION_API_MAP['proc_num'][1]] = int(partitionDict[propertyKey])
                        else:
                            exc = Exception("The procType should either be 'cp' or be 'ifl', other values invalid!")
                            raise exc
                elif (propertyKey == 'sgdevnum'):
                    vhbaList = eval(partitionDict[propertyKey])
                    for vhba in vhbaList:
                        # e.g. vhba = 'M90_KVMT02_XIV_Dedicated_SG:9000'
                        vhbaProp = vhba.split(':')
                        if sgDevNumDict.has_key(vhbaProp[0]):
                            sgDevNumDict[vhbaProp[0]].append(vhbaProp[1])
                        else:
                            sgDevNumDict[vhbaProp[0]] = [vhbaProp[1]]
                elif (propertyKey == 'sgficon'):
                    ficonList = eval(partitionDict[propertyKey])
                elif (propertyKey == 'zaccelerators'):
                    acceList = eval(partitionDict[propertyKey])
                elif (propertyKey == 'zcryptos'):
                    cryptoDict = eval(partitionDict[propertyKey])
                elif (propertyKey == 'zzbootopt'):
                    bootOptionDict = eval(partitionDict[propertyKey])
                    
                else:
                    # parse vNIC
                    pass
            elif propertyKey == 'vnic':
                for key in partitionDict.keys():
                    if re.match('^vnic\d-*', key):
                        # if the property name is start by vnic***
                        vnicDict[key] = partitionDict[key]
            else:
                # the properties that not exist in the config file, it should be optional, or else, it will throw exception while creating partition
                pass
        
    except  Exception as exc:
        print "[EXCEPTION createPartitionTemplate]", exc
        raise exc
    return (partitionTempl, vnicDict, sgDevNumDict, ficonList, acceList, cryptoDict, bootOptionDict)

# ------------------------------------------------------------------ #
# ----- End of createPartitionTemplate function -------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of createPartition function -------------------------- #
# ------------------------------------------------------------------ #
def createPartition(hmc, cpcID, parTemp):
    try:
        # prepare HTTP body as JSON
        httpBody = json.dumps(parTemp)
        # create workload
        resp = getHMCObject(hmc, 
                            WSA_URI_PARTITIONS_CPC%cpcID, 
                            "Create Partition", 
                            httpMethod = WSA_COMMAND_POST, 
                            httpBody = httpBody, 
                            httpGoodStatus = 201,           # HTTP created
                            httpBadStatuses = [400, 403, 404, 409, 503])
        return assertValue(pyObj=resp, key='object-uri')
    except HMCException as exc:   # raise HMCException
        print "[HMCEXCEPTION createPartition]", exc.message
        if exc.httpResponse != None:
            print "[HMCEXCEPTION createPartition]", eval(exc.httpResponse)['message']
        raise exc
    except Exception as exc:
        print "[EXCEPTION createPartition]", exc
        raise exc

# ------------------------------------------------------------------ #
# ----- End of createPartition function ---------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of constructVnics function --------------------------- #
# ------------------------------------------------------------------ #
def constructVnics(partUri, partName, vnicDict):
    global hmc, cpcID
    vnicNameSet = set()
    partID = partUri.replace('/api/partitions/','')
    # find how many vNic should we construct
    try:
        for key in vnicDict.keys():
            if re.match('.*_name$', key):
                vnicNameSet.add(key)
        
        for vnicName in vnicNameSet:
            vnicPrefix = vnicName[:5]
            vnicPrefixDict = dict()
            for key in vnicDict.keys():
                pattern = '^'+vnicPrefix
                if re.match(pattern, key):
                    vnicPrefixDict[key[6:]] = vnicDict[key]
            if (vnicPrefixDict.has_key("adapname")):
                # in vnicPrefixDict dict, this include all the properties to create a new nic.
                # there will throw a exception while couldn't find the adapter entity by adapter name
                adapterDict = selectAdapter(hmc, vnicPrefixDict["adapname"], cpcID)
                # get the virtual switch according to the given adapter uri (as the vs's backing adapter) and adapter port
                vsUri = selectVirtualSwitch(hmc, cpcID, adapterDict[KEY_ADAPTER_URI], vnicPrefixDict["adapport"])
                # create Nic template
                nicTempl = dict()
                nicTempl[NIC_API_MAP['name']] = vnicPrefixDict['name']
                nicTempl['virtual-switch-uri'] = vsUri
                if vnicPrefixDict.has_key('devnum'):
                    nicTempl[NIC_API_MAP['devnum']] = vnicPrefixDict['devnum']
                if vnicPrefixDict.has_key('desc'):
                    nicTempl[NIC_API_MAP['desc']] = vnicPrefixDict['desc'] 
                # for SSC vNICs, add the ssc properties
                if vnicPrefixDict.has_key('sscipaddr'):
                    nicTempl['ssc-management-nic'] = True
                    nicTempl[NIC_API_MAP['sscipaddr']] = vnicPrefixDict['sscipaddr']
                    nicTempl[NIC_API_MAP['sscipaddrtype']] = vnicPrefixDict['sscipaddrtype']
                    nicTempl[NIC_API_MAP['sscmaskprefix']] = vnicPrefixDict['sscmaskprefix']
                    if vnicPrefixDict.has_key('vlanid'):
                        nicTempl[NIC_API_MAP['vlanid']] = int(vnicPrefixDict['vlanid'])
                        # API doc V2.14.0, This value can not be set when the partition's type is "ssc"
                        nicTempl['vlan-type'] = None
                # create the Nic
                nicRet = createNIC(hmc, partID, nicTempl)
                print ">>> Create vNIC for %s successfully: %s" %(partName, vnicPrefixDict["name"])
            else:
                # the vNic with the card type is "HiperSockets", not "OSA", don't have the adapter, we don't consider this, just print
                print ">>> Create vNIC for %s failed: %s, only support OSA card this time" %(partName, vnicPrefixDict["name"])
    except HMCException as exc:
        if exc.httpResponse != None:
            print "[HMCEXCEPTION constructVnics]", json.loads(exc.httpResponse)['message']
        print "[HMCEXCEPTION constructVnics]", exc.message
    except Exception as exc:
        print "[EXCEPTION constructVnics] Create vNIC for %s failed" %partName, exc.message

# ------------------------------------------------------------------ #
# ----- End of constructVnics function ----------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of constructStorageGroups function ------------------- #
# ------------------------------------------------------------------ #
def constructStorageGroups(partUri, parName, sgDevNumDict=None, ficonList=None):
    global hmc
    partID = partUri.replace('/api/partitions/','')
    sgNameList = []
    if sgDevNumDict != None:
        sgNameList = sgDevNumDict.keys()
    elif ficonList != None: 
        sgNameList = ficonList
    else:
        exc = Exception("[EXCEPTION constructStorageGroups] sgDevNumDict and ficonList should have at least one is not None!")
        raise exc
    
    try:
        for sgName in sgNameList:
            # should we check the status of sg here? I think no.
            sgUri = selectStorageGroup(hmc, sgName)
            if (sgUri == None):
                exc = Exception("The indicated storage group name: " + sgName + " not exist in the system, please double check!")
                raise exc
            # create storage group template
            sgTempl = dict()
            sgTempl['storage-group-uri'] = sgUri
            sgRet = attachStorageGroup(hmc, partID, sgTempl)
            print ">>> Construct storage group for %s successfully: %s" %(parName, sgName)
    except Exception as exc:
        print "[EXCEPTION constructStorageGroups] Attach storage group failed!", exc.message

# ------------------------------------------------------------------ #
# ----- End of constructStorageGroups function --------------------- #
# ------------------------------------------------------------------ #

def constructAccelerators(partUri, parName, acceList):
    global hmc, cpcID
    partID = partUri.replace('/api/partitions/','')
    
    try:
        for acceDict in acceList:
            # change the adapter-name to the adapter-uri in the dict
            adapterName = acceDict.pop('adapter-name')
            adapterUri = selectAdapter(hmc, adapterName, cpcID)[KEY_ADAPTER_URI]
            acceDict['adapter-uri'] = adapterUri
            
            vfRet = createVirtualFunction(hmc, partID, acceDict)
            print ">>> Construct accelerator virtual function for %s successfully: %s" %(parName, acceDict['name'])
    except Exception as exc:
        print "[EXCEPTION constructAccelerators] Construct accelerator failed!", exc.message
        

def constructCryptos(partUri, parName, cryptoDict):
    global hmc, cpcID
    partID = partUri.replace('/api/partitions/','')
    
    try:
        adapterNameList = cryptoDict.pop('crypto-adapter-names')
        adapterUriList = []
        for adapterName in adapterNameList:
            adapterUri = selectAdapter(hmc, adapterName, cpcID)[KEY_ADAPTER_URI]
            adapterUriList.append(adapterUri)
        cryptoDict['crypto-adapter-uris'] = adapterUriList
        
        increaseCryptoConfiguration(hmc, partID, cryptoDict)
        print ">>> Construct cryptos for %s successfully: %s" %(parName, adapterNameList)
    except Exception as exc:
        print "[EXCEPTION constructCryptos] Construct cryptos failed!", exc.message


def setDeviceNumber(partUri, parName, sgDevNumDict):
    global hmc, cpcName, FCP_CONFIG_FILE, fcpAdapterDict
    partID = partUri.replace('/api/partitions/','')
    
    loadConfig(FCP_CONFIG_FILE, fcpAdapterDict)
    
    if fcpAdapterDict.has_key(cpcName):
        adapter_map = fcpAdapterDict[cpcName]
    else:
        exc = Exception("[EXCEPTION setDeviceNumber] The cpc" + cpcName + "should be placed in the config file: " + FCP_CONFIG_FILE + " to complete the device number setting!")
        raise exc
    
    try:
        for sgName in sgDevNumDict.keys():
            # should we check the status of sg here? I think no.
            sgUri = selectStorageGroup(hmc, sgName)
            if (sgUri == None):
                exc = Exception("The indicated storage group name: " + sgName + " not exist in the system, please double check!")
                raise exc
            sgID = sgUri.replace('/api/storage-groups/', '')
            vsrList = listVirtualStorageResourcesOfStorageGroup(hmc, sgID)
            
            for vsr in vsrList:
                if vsr['partition-uri'] == partUri:
                    vsrTempl = dict()
                    adapterUri = vsr['adapter-port-uri'].split('/storage-ports/')[0]
                    adapterRet = getAdapterProperties(hmc, adapterUri)
                    if adapterRet['adapter-id'] in adapter_map.keys():
                        if fcpAdapterDict.has_key(adapter_map[adapterRet['adapter-id']]):
                            for devNum in sgDevNumDict[sgName]:
                                if devNum in fcpAdapterDict[adapter_map[adapterRet['adapter-id']]]:
                                    sgDevNumDict[sgName].remove(devNum)
                                    vsrTempl['device-number'] = devNum
                                    break
                    else:
                        exc = Exception("[EXCEPTION setDeviceNumber] the adapter ID: " + adapterRet['adapter-id'] + "not exist in the" + FCP_CONFIG_FILE + ", please check and add the adapter!")
                        raise exc
                    
                    # if the device number not record either in cisco section and brocade section in the config file, just pop one randomly
                    if len(vsrTempl) == 0:
                        vsrTempl['device-number'] = sgDevNumDict[sgName].pop()
                    
                    if updateVirtualStorageResourceProperties(hmc, str(vsr['element-uri']), vsrTempl):
                        print ">>> Set device number for %s successfully: %s" %(sgName, vsrTempl['device-number'])
                    else:
                        print ">>> Set device number for %s failed: %s" %(sgName, vsrTempl['device-number'])
    except Exception as exc:
        print "[EXCEPTION setDeviceNumber] Device number set failed!", exc.message

def setBootOption(partUri, parName, bootOptionDict):
    global hmc
    
    try:
        if bootOptionDict['boot_device'] != 'storage-volume':
            # only set the boot option when boot from SAN
            print ">>> Set boot option for ", parName,  "failed: backup boot option not SAN!"
            return False
        
        bootTempl = dict()
        bootTempl['boot-timeout'] = int(bootOptionDict['boot-timeout'])
        
        # get the boot storage group.
        bootSgName = bootOptionDict['storage_group_name']
        bootSgUri = selectStorageGroup(hmc, bootSgName)
        # check the storage group exist
        if bootSgUri == None:
            print ">>> Set boot option for %s failed: the boot storage group %s not exist!" %(parName, bootSgName)
            return False
        # check the storage group statue is complete
        sgRet = getStorageGroupProperties(hmc, sgURI=bootSgUri)
        if assertValue(pyObj=sgRet, key='fulfillment-state') != 'complete':
            print ">>> Set boot option for %s failed: the boot storage group is in %s state!" %(parName, assertValue(pyObj=sgRet, key='fulfillment-state'))
            return False

        # check the storage group have already attached to this partition
        # since the virtual storage resource only exist in FCP and we couldn't judge a FICON storage group already attached or not, I discard the judge about attached or not
        '''
        attached = False
        for sgVsrUri in assertValue(pyObj=sgRet, key='virtual-storage-resource-uris'):
            vsrRet = getVirtualStorageResourceProperties(hmc, sgVsrUri)
            iPartUri = assertValue(pyObj=vsrRet, key='partition-uri')
            if partUri == iPartUri:
                attached = True
                break
        if not attached:
            print ">>> Set boot option for %s failed: the boot storage group %s have not attached to the partition yet!" %(parName, bootSgName)
            return
        '''

        for sgVolUri in assertValue(pyObj=sgRet, key='storage-volume-uris'):
            svRet = getStorVolProperties(hmc, sgVolUri)
            # for FCP storage group, set the boot volume uuid by UUID and set the boot-configuration-selector
            if assertValue(pyObj=sgRet, key='type') == 'fcp':
                if svRet['usage'] == 'boot' and svRet['uuid'] == bootOptionDict['fcp-volume-uuid']:
                    bootTempl['boot-storage-volume'] = sgVolUri
                    bootTempl['boot-configuration-selector'] = int(bootOptionDict['fcp-boot-configuration-selector'])
                    break
            # for FICON storage group, set the FICON only properties
            elif assertValue(pyObj=sgRet, key='type') == 'fc':
                # get the control unit
                ctrlUnitUri = assertValue(pyObj=svRet, key='control-unit-uri')
                ctrlUnitRet = getStorageControlUnitProperties(hmc, ctrlUnitUri)
                if svRet['usage'] == 'boot' and svRet['eckd-type'] == 'base' and assertValue(pyObj=ctrlUnitRet, key='logical-address') == bootOptionDict['fc-logical-address'] and svRet['unit-address'] == bootOptionDict['fc-unit-address']:
                    bootTempl['boot-storage-volume'] = sgVolUri
                    break
            else:
                # Oops
                pass
        
        if 'boot-storage-volume' in bootTempl:
            if updatePartitionProperties(hmcConn=hmc, parURI=partUri, parProp=bootTempl):
                print ">>> Set boot option for", parName,  "successfully!!!"
                bootTempl2 = dict()
                bootTempl2['boot-device'] = 'storage-volume'
                updatePartitionProperties(hmcConn=hmc, parURI=partUri, parProp=bootTempl2)
                return True
            else:
                print ">>> Set boot option for", parName, "failed!!!"
                return False
        else:
            print ">>> Set boot option for", parName, "failed: couldn't find the target storage volume!!!"
            return False
        
        
    except Exception as exc:
        print "[EXCEPTION setBootOption] Boot option set failed!", exc.message


def startThePartitionAndCheck(parURI, parName):
    global hmc
    
    startPartition(hmc, parURI)

    intervalCount = 0
    while intervalCount != 24:
        jobStatus = queryJobStatus(hmc, jobURI=parURI)
        status = assertValue(pyObj=jobStatus, key='status')
        if status == JOB_STATUS_ACTIVE:
            print ">>>", parName, "has been successfully started!"
            time.sleep(10)
            return True
        else:
            print ">>> %s is starting, please wait...%ss" % (parName, intervalCount * 5)
        intervalCount += 1
        time.sleep(5)
    return False

# main function
try:
    parseArgs()
    loadConfig(configFile, sectionDict)

    # Access HMC system and create HMC connection 
    print ">>> Creating HMC connection..."
    hmc = createHMCConnection(hmcHost=hmcHost)
    cpc = selectCPC(hmc, cpcName)
    cpcURI = assertValue(pyObj=cpc, key=KEY_CPC_URI)
    cpcName = assertValue(pyObj=cpc, key=KEY_CPC_NAME)
    cpcStatus = assertValue(pyObj=cpc, key=KEY_CPC_STATUS)

    # Get CPC UUID
    cpcID = cpcURI.replace('/api/cpcs/','')
    print ">>> HMC connection created!"
    threads = []
    for parName in sectionDict.keys():
        t = threading.Thread(target=procSinglePartition, args=(parName,))
        print ">>> Creating partition: " + parName + "..."
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
except IOError as exc:
    print "[EXCEPTION] Configure file read error!", exc
except Exception as exc:
    print "[EXCEPTION]", exc.message
  
finally:
    if hmc != None:
        hmc.logoff()
    if (len(createPass) != 0):
        print "Here are the partition(s) be created successfully:", createPass
    if (len(createFail) != 0):
        print "Here are the partition(s) be created failed:", createFail
    print "Script run completed!!!"