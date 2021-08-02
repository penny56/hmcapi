'''
Created on Dec 5, 2017

Updated on Jul 30, 2021 --- Add secure boot to partition restore script
                        --- Comment out the --Adapter-- description field
Updated on May 7, 2021 --- Change the weird vNic store style
Updated on Apr 20, 2021 --- Support for tape links
Updated on Mar 31, 2021 --- Move to github
Updated on Aug 25, 2020 --- Support for NVMe storage groups
Updated on Aug 11, 2020 --- Ahead restore the adapter description field before restore partitions
Updated on Jul 7, 2020 --- Set the default encoding from ascii to utf-8
Updated on Jul 1, 2020 --- Restore adapter description field by [--adapter--] section in config file.
Updated on Jun 4, 2020 --- Change adapter Name to adapter ID property in the backup config file.
Updated on Mar 6, 2020 --- Add the partition name in the exception messages
Updated on Mar 6, 2020 --- Fix the bug when set device numbers in a storage group in pending state.
Updated on Feb 29, 2020 --- Fix the bug, attached sg1 has vsr[0001, 0002], sg2 has vsr [0003, 0004], but in set device number, sg1 = [0003, 0004], sg2 = [0001, 0002]
    I'd like to combine attach storage group and set device number, after attach one storage group, set its device numbers, then attach the other storage groups.
Updated on Jan 23, 2020 --- For the last update for "update devnum", there still a bug, the last update just consider the conflict devnum
    within a storage group, but not consider the devnum exists in other kind of devices, like different sg, vNic, etc.
    We have no workaround for this bug, just update it manually after the exception.
Updated on Aug 9, 2019 --- Judge the device number already exist in the vsr, skip devnum seting if exist.
Updated on Jun 4, 2019 --- Add trace for create vNic exception. One defect is the vNic creation process will abort if one vNic exception occurred.
Updated on February 22, 2019 --- Only set boot section for linux partitions, escape the ssc and zvm partitions.
                             --- Show more detailed information when the storage group not exist in the system.
                             --- refine the devnum setting, make the Cisco vhba set to smaller number (7000/8000/9000...) and Brocade vhba set to the bigger one (7100/8100/9100...)
                             --- The adapters belong to Cisco/Brocade are classified by the adapter description field.
Updated on September 10, 2018 --- Just restore the boot option, remove the start part
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

Example:        --> unlike sgRestore, no email option.
-hmc 9.12.35.135 -cpc T257 -config ./cfg/T257-Part.cfg

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

from CommonAPI.prsm2api import *
from CommonAPI.wsaconst import *
import CommonAPI.hmcUtils
import sys, ConfigParser, logging, threading, os, argparse, traceback, re

# to handle the Non ascii code, transfer python default coding from ascii to utf-8
reload(sys)
sys.setdefaultencoding('utf-8')

hmc = None
cpcID = None

hmcHost = None
cpcName = None
configFile = None
createPass = list()
createFail = list()

# the key is the partition name, the value is the properties of the partition, by dict format
sectionDict = dict()

# default SSC partition master password
SSC_MASTER_PASSWORD = 'passw0rd'

# the key is the key from config file, the value is the standard API field name
# All option names are passed through the optionxform() method. Its default implementation converts option names to lower case. So the keys use lower case here!
PARTITION_API_MAP = {'par_type' : 'type',
                     'par_desc' : 'description',
                     'par_reserveresources' : 'reserve-resources',      # boolean
                     'par_secureboot' : 'secure-boot',
                     'proc_mode' : 'processor-mode',
                     'proc_type' : None,
                     'proc_num' : ['cp-processors', 'ifl-processors'],
                     'init_mem' : 'initial-memory',
                     'max_mem' : 'maximum-memory',
                     'vnics' : None,
                     'sgdevnum' : None, 
                     'sgficon' : None,
                     'sgnvme' : None,
                     'tapelink' : None,
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
def loadConfig(configFile):
    print ">>> loading the config file..."
    global sectionDict
    
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
            sectionDict[section] = itemDict

    except IOError as exc:
        print ">>> [EXCEPTION loadConfig] Cannot load configuration file [%s]: %s"%(configFile, exc)  
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
            (parTemp, vnicList, sgDevNumDict, ficonList, nvmeList, tlDict, acceList, cryptoDict, bootOptionDict) = createPartitionTemplate(parName, partitionDict)
            lock.release()
        if lock.acquire():
            partRet = createPartition(hmc, cpcID, parTemp)
            lock.release()
        if lock.acquire():
            if partRet != None:
                createPass.append(parName)
                if len(vnicList) != 0:
                    constructVnics(partRet, parName, vnicList)
                if len(sgDevNumDict) != 0:
                    # combine the two steps as one
                    #constructStorageGroups(partRet, parName, sgDevNumDict=sgDevNumDict)
                    #setDeviceNumber(partRet, parName, sgDevNumDict)
                    constructStorageGroupsAndSetDevNum(partRet, parName, sgDevNumDict=sgDevNumDict)
                if len(ficonList) != 0:
                    #constructStorageGroups(partRet, parName, ficonList=ficonList)
                    constructStorageGroupsAndSetDevNum(partRet, parName, ficonList=ficonList)
                if len(nvmeList) != 0:
                    constructStorageGroupsAndSetDevNum(partRet, parName, nvmeList=nvmeList)
                if len(tlDict) != 0:
                    constructTapelinks(partRet, parName, tlDict)
                if len(acceList) != 0:
                    constructAccelerators(partRet, parName, acceList)
                if len(cryptoDict) != 0:
                    constructCryptos(partRet, parName, cryptoDict)
                if len(bootOptionDict) != 0:
                    couldStart = setBootOption(partRet, parName, bootOptionDict)
            else:
                createFail.append(parName)
            lock.release()
    except Exception as exc: 
        print "[EXCEPTION procSinglePartition] partition", parName
        print

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
    vnicList = []
    sgDevNumDict = dict()
    ficonList = []
    nvmeList = []
    tapelink = dict()
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
                # place the secure boot property to bootOptionDict rather than partitionTempl
                elif (propertyKey == 'par_secureboot'):
                    bootOptionDict[PARTITION_API_MAP[propertyKey]] = True if (partitionDict[propertyKey].lower() == 'true') else False
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
                elif (propertyKey == 'vnics'):
                    vnicList = eval(partitionDict[propertyKey])
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
                elif (propertyKey == 'sgnvme'):
                    nvmeList = eval(partitionDict[propertyKey])
                elif (propertyKey == 'tapelink'):
                    tlDict = eval(partitionDict[propertyKey])
                elif (propertyKey == 'zaccelerators'):
                    acceList = eval(partitionDict[propertyKey])
                elif (propertyKey == 'zcryptos'):
                    cryptoDict = eval(partitionDict[propertyKey])
                elif (propertyKey == 'zzbootopt'):
                    # bootOptionDict already exist secure boot property here, so use 'update' method here
                    bootOptionDict.update(eval(partitionDict[propertyKey]))
                else:
                    # Oops
                    pass
            else:
                # the properties that not exist in the config file, it should be optional, or else, it will throw exception while creating partition
                pass
        
    except  Exception as exc:
        print "[EXCEPTION createPartitionTemplate: %s]" %parName, exc
        raise exc
    return (partitionTempl, vnicList, sgDevNumDict, ficonList, nvmeList, tlDict, acceList, cryptoDict, bootOptionDict)

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
        print "[HMCEXCEPTION createPartition: %s]" %parTemp['name'], exc.message
        if exc.httpResponse != None:
            print "[HMCEXCEPTION createPartition: %s]" %parTemp['name'], eval(exc.httpResponse)['message']
        raise exc
    except Exception as exc:
        print "[EXCEPTION createPartition: %s]" %parTemp['name'], exc
        raise exc

# ------------------------------------------------------------------ #
# ----- End of createPartition function ---------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of constructVnics function --------------------------- #
# ------------------------------------------------------------------ #
def constructVnics(partUri, partName, vnicList):
    global hmc, cpcID
    partID = partUri.replace('/api/partitions/','')
    try:
        for vnicDict in vnicList:
            if vnicDict.has_key("adapter-id"):                
                # locate the backing adapter
                query = 'adapter-id' + '=' + vnicDict["adapter-id"]
                adapters = listAdaptersOfACpc(hmc, cpcID, query)
                if len(adapters) == 0:
                    print ">>> Create vNIC for %s failed: Adapter ID: %s not found in the system." %(partName, vnicDict["adapter-id"])
                    continue
                # get the virtual switch uri according to the given adapter uri (as the vs's backing adapter) and adapter port
                virtual_switch_uri = selectVirtualSwitch(hmc, cpcID, adapters[0]["object-uri"], vnicDict["port"])
                
                nicTemp = dict()
                nicTemp["name"] = vnicDict["name"]
                nicTemp["description"] = vnicDict["description"]
                nicTemp["virtual-switch-uri"] = virtual_switch_uri
                nicTemp["device-number"] = vnicDict["device-number"]
                
                if vnicDict.has_key("ssc-ip-address-type"):
                    nicTemp['ssc-management-nic'] = True
                    nicTemp["ssc-ip-address-type"] = vnicDict["ssc-ip-address-type"]
                    nicTemp["ssc-ip-address"] = vnicDict["ssc-ip-address"]
                    nicTemp["ssc-mask-prefix"] = vnicDict["ssc-mask-prefix"]
                    if vnicDict.has_key("vlan-id"):
                        nicTemp["vlan-id"] = vnicDict["vlan-id"]
                        # API doc V2.14.0, This value can not be set when the partition's type is "ssc"
                        nicTemp["vlan-type"] = None
                
                # create the Nic
                nicRet = createNIC(hmc, partID, nicTemp)
                print ">>> Create vNIC for %s successfully: Adapter ID: %s" %(partName, vnicDict["adapter-id"])
            else:
                # the vNic with the card type is "HiperSockets", not "OSA", don't have the adapter, we don't consider this, just print
                print ">>> Create vNIC for %s failed: %s, only support OSA card this time" %(partName, vnicDict['name'])

    except HMCException as exc:
        if exc.httpResponse != None:
            print "[HMCEXCEPTION constructVnics: %s]" %partName, json.loads(exc.httpResponse)['message']
        print "[HMCEXCEPTION constructVnics: %s] exc.message: " %partName, exc.message
        print "[HMCEXCEPTION constructVnics: %s] vNic template: " %partName, nicTempl
    except Exception as exc:
        print "[EXCEPTION constructVnics: %s] Create vNIC failed" %partName, exc.message

# ------------------------------------------------------------------ #
# ----- End of constructVnics function ----------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of constructStorageGroups function ------------------- #
# ------------------------------------------------------------------ #
#def constructStorageGroups(partUri, parName, sgDevNumDict=None, ficonList=None):
def constructStorageGroupsAndSetDevNum(partUri, parName, sgDevNumDict=None, ficonList=None, nvmeList=None):
    global hmc
    partID = partUri.replace('/api/partitions/','')
    sgNameList = []
    if sgDevNumDict != None:
        sgNameList = sgDevNumDict.keys()
    elif ficonList != None: 
        sgNameList = ficonList
    elif nvmeList != None: 
        sgNameList = nvmeList
    else:
        # have attached no storage group
        pass
    
    try:
        for sgName in sgNameList:
            # should we check the status of sg here? I think no.
            sgUri = selectStorageGroup(hmc, sgName)
            if (sgUri == None):
                exc = Exception("Storage group attachment failed. The indicated storage group: " + sgName + " not exist (restored failed or been removed before partition restore) in the system.")
                raise exc
            # create storage group template
            sgTempl = dict()
            sgTempl['storage-group-uri'] = sgUri
            sgRet = attachStorageGroup(hmc, partID, sgTempl)
            print ">>> Construct storage group for %s successfully: %s" %(parName, sgName)
            
            # set device number for FCP storage group
            if sgDevNumDict != None:
                setDeviceNumber(partUri, parName, sgName, sgDevNumDict)

    except Exception as exc:
        print "[EXCEPTION constructStorageGroups: %s] Attach storage group: %s failed!" %(partName, sgName), exc.message

# ------------------------------------------------------------------ #
# ----- End of constructStorageGroups function --------------------- #
# ------------------------------------------------------------------ #

def constructTapelinks(partUri, parName, tlDict):
    global hmc, cpcID, cpcURI
    partID = partUri.replace('/api/partitions/','')
    
    try:
        for (tlName, devnumList)in tlDict.items():
            query = 'cpc-uri' + '=' + cpcURI + '&' + 'name' + '=' + tlName
            tls = listTapeLinks(hmc, query)
            if (len(tls) == 0):
                exc = Exception("Attach tape link failed. The indicated tape link: " + tlName + " not exist (restored failed or been removed before partition restore) in the system.")
                raise exc
            tlTempl = dict()
            tlTempl['tape-link-uri'] = tls[0]['object-uri']
            attachTapeLink(hmc, partID, tlTempl)
            if devnumList != None:
                setTapeLinkDeviceNumber(partUri, parName, tls[0]['object-uri'], tlName, devnumList)
        print ">>> Construct tape link for %s successfully: %s" %(parName, tlDict.keys())
    except Exception as exc:
        print "[EXCEPTION constructTapelinks: %s] Construct tape links: %s failed!" %(parName, tlDict.keys()), exc.message

# ----- obsoleted in DPM R4.2 ----- #
def constructAccelerators(partUri, parName, acceList):
    global hmc, cpcID
    partID = partUri.replace('/api/partitions/','')
    
    try:
        for acceDict in acceList:
            # change the adapter-name to the adapter-uri in the dict
            adapterName = acceDict.pop('adapter-name')
            # adapterUri = selectAdapter(hmc, adapterName, cpcID)[KEY_ADAPTER_URI]
            acceDict['adapter-uri'] = adapterUri
            
            vfRet = createVirtualFunction(hmc, partID, acceDict)
            print ">>> Construct accelerator virtual function for %s successfully: %s" %(parName, acceDict['name'])
    except Exception as exc:
        print "[EXCEPTION constructAccelerators: %s] Construct accelerator: % failed!" %(parName, acceDict['name']), exc.message
        

def constructCryptos(partUri, parName, cryptoDict):
    global hmc, cpcID
    partID = partUri.replace('/api/partitions/','')
    
    try:
        adapterIDList = cryptoDict.pop('crypto-adapter-ids')
        adapterUriList = []
        # if there is adapterID not exist in the system, the script could do nothing just ignore.
        for adapterID in adapterIDList:
            for adapter in getCPCAdaptersList(hmc, cpcID):
                if adapterID == str(adapter['adapter-id']):
                    adapterUri = str(adapter['object-uri'])
                    adapterUriList.append(adapterUri)
                    break
        cryptoDict['crypto-adapter-uris'] = adapterUriList
        increaseCryptoConfiguration(hmc, partID, cryptoDict)
        print ">>> Construct cryptos for %s successfully: %s" %(parName, adapterIDList)
    except Exception as exc:
        print "[EXCEPTION constructCryptos: %s] Construct cryptos: %s failed!" %(parName, adapterIDList), exc.message


# ------------------------------------------------------------------ #
# ----- Start of setDeviceNumber function -------------------------- #
# ------------------------------------------------------------------ #
def setDeviceNumber(partUri, parName, sgName, sgDevNumDict):
    global hmc
    try:
        # should we check the status of sg here? I think no.
        sgUri = selectStorageGroup(hmc, sgName)
        if (sgUri == None):
            exc = Exception("The indicated storage group name: " + sgName + " not exist in the system, please double check!")
            raise exc
        sgID = sgUri.replace('/api/storage-groups/', '')
        vsrList = listVirtualStorageResourcesOfStorageGroup(hmc, sgID)
        
        uniqueVsrList = []
        for vsr in vsrList:
            if vsr['partition-uri'] == partUri:
                if str(vsr['device-number']) in sgDevNumDict[sgName]:
                    sgDevNumDict[sgName].remove(str(vsr['device-number']))
                    print ">>> Set device number for %s already exist: %s, no need to set" %(sgName, str(vsr['device-number']))
                else:
                    uniqueVsrList.append(vsr)
        
        for uniVsr in uniqueVsrList:
            vsrTempl = dict()
            
            # we only judge adapter belongs to Cisco or Brocade if only sg in complete state
            # if a sg in pending state, no adapter assigned to this sg, in this case, just set the devnum randomly
            if str(uniVsr['adapter-port-uri']) != "None":
                adapterObj = getAdapterProperties(hmc, uniVsr['adapter-port-uri'].split('/storage-ports/')[0])
                adapterDesc = adapterObj['description']
                
                if "Cisco" in adapterDesc.split(' '):
                    sgDevNumDict[sgName].sort(reverse=True)
                elif "Brocade" in adapterDesc.split(' '):
                    sgDevNumDict[sgName].sort()
            
            # here if the number of path is greater then the device number count in the config file
            # exception will occur due to no item could be pop out
            vsrTempl['device-number'] = sgDevNumDict[sgName].pop()
            if updateVirtualStorageResourceProperties(hmc, str(uniVsr['element-uri']), vsrTempl):
                print ">>> Set device number for %s successfully: %s" %(sgName, vsrTempl['device-number'])

    except Exception as exc:
        print "[EXCEPTION setDeviceNumber: %s] Device number: %s set for storage group: % failed!" %(parName, sgName, vsrTempl['device-number']), exc.message
# ------------------------------------------------------------------ #
# ----- End of setDeviceNumber function ---------------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of setTapeLinkDeviceNumber function ------------------ #
# ------------------------------------------------------------------ #
def setTapeLinkDeviceNumber(partUri, parName, tlUri, tlName, devnumList):
    global hmc
    try:
        query = 'partition-uri' + '=' + partUri
        vtrs = listVirtualTapeResourcesOfaTapeLink(hmc, tlUri, query)
        
        for vtr in vtrs:
            vtrUri = vtr['element-uri']
            vtrTempl = dict()
            vtrTempl['device-number'] = devnumList.pop()
            if updateVirtualTapeResourceProperties(hmc, vtrUri, vtrTempl):
                print ">>> Set Tape link device number for %s successfully: %s" %(tlName, vtrTempl['device-number'])
    except Exception as exc:
        print "[EXCEPTION setTapeLinkDeviceNumber: %s] %s set for partition: %s failed!" %(tlName, devnumList, parName), exc.message
# ------------------------------------------------------------------ #
# ----- End of setTapeLinkDeviceNumber function -------------------- #
# ------------------------------------------------------------------ #

def setBootOption(partUri, parName, bootOptionDict):
    global hmc
    
    try:
        # only set the boot option section for the Linux partitions
        partObj = getPartitionProperties(hmcConn=hmc, parURI=partUri)
        if str(partObj['type']) != "linux":
            return False
        
        # only set the boot option when boot from SAN
        if bootOptionDict['boot_device'] != 'storage-volume':
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
            # for NVMe storage group, set the NVMe only properties
            elif assertValue(pyObj=sgRet, key='type') == 'nvme':
                if svRet['usage'] == 'boot' and svRet['serial-number'] == bootOptionDict['nvme-serial-number']:
                    bootTempl['boot-storage-volume'] = sgVolUri
            else:
                # Oops
                pass
        
        if 'boot-storage-volume' in bootTempl:
            if updatePartitionProperties(hmcConn=hmc, parURI=partUri, parProp=bootTempl):
                print ">>> Set boot option for", parName,  "successfully!!!"
                bootTempl2 = dict()
                bootTempl2['boot-device'] = 'storage-volume'
                
                # set the secure boot property
                if bootOptionDict['secure-boot']:
                    bootTempl2['secure-boot'] = True
                
                updatePartitionProperties(hmcConn=hmc, parURI=partUri, parProp=bootTempl2)
                return True
            else:
                print ">>> Set boot option for", parName, "failed!!!"
                return False
        else:
            print ">>> Set boot option for", parName, "failed: couldn't find the target storage volume!!!"
            return False
        
        
    except Exception as exc:
        print "[EXCEPTION setBootOption: %s] Boot option set failed!" %parName, exc.message


def restoreAdapterDescription(backupAdapterDict):
    global hmc, cpcID
    
    try:
        for adaDict in getCPCAdaptersList(hmc, cpcID):
            adaProp = getAdapterProperties(hmc, adaDict['object-uri'])
            if str(adaProp['description']) == "" and backupAdapterDict.has_key(str(adaProp['adapter-id'])) and str(eval(backupAdapterDict[str(adaProp['adapter-id'])])['description']) != "":
                # update the adapter description field by description in backup config file
                #     if the current adapter description field is null
                # and if the adapter id is exist in the backup config file
                # and if the adapter have description field not null in the backup config file
                descTemp = dict()
                descTemp['description'] = str(eval(backupAdapterDict[adaProp['adapter-id']])['description'])
                updateAdapterProperties(hmc, str(adaProp['object-uri']), descTemp)
                print ">>> restoreAdapterDescription for adapter", adaProp['adapter-id'], "successfully"

    except Exception as exc:
        print "[EXCEPTION restoreAdapterDescription] failed!", exc.message

# main function
try:
    parseArgs()
    loadConfig(configFile)

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

    # restore adapter description field (No need to do this)
    #if sectionDict.has_key('--adapter--'):
    #    restoreAdapterDescription(sectionDict['--adapter--'])

    threads = []
    for parName in sectionDict.keys():
        if parName != "--adapter--":
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