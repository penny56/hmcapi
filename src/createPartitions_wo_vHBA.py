'''
Created on Dec 5, 2017

This script is to create partitions by configure file. Only the baic information - processor and memory - will be set in this script.
vNIC, vHBA and others would be added manually in this stage.
All the partition information will be created simultaneously by multithreading.

You couldn't indicate the 'cp' processor type in a 'ifl' only cpc (M90), or you will encounter a "Cp processor is not available" exception!

Example:
-hmc 9.12.35.135 -cpc M90 -config createP2Partition.cfg

config file example:
[KVMP101]
par_desc = This is a des of 101
par_type = linux
proc_mode = dedicated
proc_type = ifl
proc_num = 1
init_mem = 1
max_mem = 1
vnic1_name = vn--this is name
vnic1_desc = this is the descr
vnic1_devNum = 1100
vnic1_adapName = OSD 0110 Z22B-
vnic1_adapPort = 0
vhba1_name = vhba name
vhba1_desc = this is the description
vhba1_devnum = 1000
vhba1_adapname = FCP 01e5 Z15B-31

Updated on Mar 6, 2018

Add support for Storage Group in DPM R3.1.

Here in the cfg file, we add the section for storage group, it indicate the storage group names.
And boot lun in the boot option section.

@author: mayijie
'''

from prsm2api import *
from wsaconst import *
import hmcUtils
import sys, ConfigParser, logging, threading, os, argparse, traceback, re

hmc = None
cpcID = None

hmcHost = None
hmcVersion = None
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
                     'proc_mode' : 'processor-mode',
                     'proc_type' : None,
                     'proc_num' : ['cp-processors', 'ifl-processors'],
                     'init_mem' : 'initial-memory',
                     'max_mem' : 'maximum-memory',
                     'vnic' : None
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
            (parTemp, vnicDict) = createPartitionTemplate(parName, partitionDict)
            lock.release()
        if lock.acquire():
            partRet = createPartition(hmc, cpcID, parTemp)
            lock.release()
        if lock.acquire():
            if partRet != None:
                createPass.append(parName)
                if len(vnicDict) != 0:
                    addVnics(partRet, parName, vnicDict)
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
    global PARTITION_API_MAP, hmcVersion
    iProcNum = None
    iProcType = None
    partitionTempl = dict()
    vnicDict = dict()
    
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
                else:
                    # parse vNIC or vHBA
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
    return (partitionTempl, vnicDict)

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
# ----- Start of addVnics function --------------------------------- #
# ------------------------------------------------------------------ #
def addVnics(partUri, partName, vnicDict):
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
            print "[HMCEXCEPTION addVnics]", json.loads(exc.httpResponse)['message']
        print "[HMCEXCEPTION addVnics]", exc.message
    except Exception as exc:
        print "[EXCEPTION addVnics] Create vNIC for %s failed" %partName, exc.message

# ------------------------------------------------------------------ #
# ----- End of addVnics function ----------------------------------- #
# ------------------------------------------------------------------ #

# main function
try:
    parseArgs()
    loadConfig(configFile)

    # Access HMC system and create HMC connection 
    print ">>> Creating HMC connection..."
    hmc = createHMCConnection(hmcHost=hmcHost)
    hmc.getAPIVersion()
    # get the DPM version for the Storage Group will online in R3
    hmcVersion = hmc.apiMajorVer
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