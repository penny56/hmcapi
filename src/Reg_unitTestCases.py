'''
Created on Oct 11, 2018

@author: mayijie
'''
from prsm2api import *
from wsaconst import *
import hmcUtils
import argparse
import ConfigParser, os, sys
import datetime, readConfig, logging, string

# the key is the partition name, the value is the properties of the partition, by dict format
sectionDict = dict()

ConfigFile = None

hmc = None
cpc = None
cpcURI = None
cpcName = None
cpcStatus = None

partRet = None

def reg_parseArgs():
    print ">>> parsing the input parameters..."
    global configFile
    
    parser = argparse.ArgumentParser(description='regression test by configure file')
    parser.add_argument('-config', '--configFile', metavar='<configure file name>', help='indicate configure file name / location')
    try:
        # return the dict of all the input parameters
        args = vars(parser.parse_args())
        configFile = assertValue(pyObj=args, key='configFile', listIndex=0, optionalKey=True)
        if configFile == None:
            exc = Exception("You should specify the configure file name / path")
            raise exc
    except Exception as exc:
        print "[EXCEPTION parseArgs] Mandatory parameter missed:", exc 
        raise exc
    finally:
        print ">>> Parsing parameters complete!"


def reg_loadConfig():
    print ">>> loading the config file..."
    global sectionDict, configFile
    
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


def constructHMCConnection():
    global sectionDict, hmc, cpcURI
    
    connectionDict = sectionDict['connection']
    
    hmc = createHMCConnection(hmcHost = connectionDict['hmc'])
    cpc = selectCPC(hmc, connectionDict['cpc'])
    cpcURI = assertValue(pyObj=cpc, key=KEY_CPC_URI)
    cpcName = assertValue(pyObj=cpc, key=KEY_CPC_NAME)
    cpcStatus = assertValue(pyObj=cpc, key=KEY_CPC_STATUS)
    
    
def destructHMCConnection():
    if hmc != None:
        hmc.logoff()


def createPartitionTemplate(partitionDict):
    partitionTempl = dict()
    
    try:
        partitionTempl['name'] = partitionDict['par_name']
        partitionTempl['type'] = partitionDict['par_type']
        partitionTempl['description'] = partitionDict['par_desc']
        partitionTempl['reserve-resources'] = True if (partitionDict['par_reserveresources'].lower() == 'true') else False
        
        partitionTempl['processor-mode'] = partitionDict['proc_mode']
        # the processor type is ifl, hard code here by identity the ifl processor number
        partitionTempl['ifl-processors'] = int(partitionDict['proc_num'])
        partitionTempl['initial-memory'] = int(partitionDict['init_mem']) * 1024
        partitionTempl['maximum-memory'] = int(partitionDict['max_mem']) * 1024
   
    except  Exception as exc:
        print "[EXCEPTION createPartitionTemplate]", exc
        raise exc
    return partitionTempl

def tc_createPartition():
    global hmc, cpcURI, partRet
    
    cpcID = cpcURI.replace('/api/cpcs/','')
    partitionDict = sectionDict['partition']
    parTemp = createPartitionTemplate(partitionDict)
    partRet = createPartition(hmc, cpcID, parTemp)
    if partRet != None:
        return 1
    else:
        return 0


def tc_addVnic():
    global hmc, cpcURI, partRet
    
    cpcID = cpcURI.replace('/api/cpcs/','')
    partID = partRet.replace('/api/partitions/','')
    
    if partRet == None:
        return 0
    else:
        vNicDict = sectionDict['vnic']
        adapterDict = selectAdapter(hmc, vNicDict["vnic_adapterid"], cpcID)
        vsUri = selectVirtualSwitch(hmc, cpcID, adapterDict[KEY_ADAPTER_URI], vNicDict["vnic_adapterport"])
        
        # construct the template
        nicTempl = dict()
        nicTempl['name'] = vNicDict['vnic_name']
        nicTempl['description'] = vNicDict['vnic_description'] 
        nicTempl['virtual-switch-uri'] = vsUri
        nicTempl['device-number'] = vNicDict['vnic_devnum']
        
        # create the Nic
        nicRet = createNIC(hmc, partID, nicTempl)
        if nicRet != None:
            return 1
        else:
            return 0


def tc_AttachFCPStorageGroup():
    global hmc, cpcURI, partRet
    
    cpcID = cpcURI.replace('/api/cpcs/','')
    partID = partRet.replace('/api/partitions/','')
    '''
    if partRet == None:
        return 0
    else:    
    '''   


def tc_DynamicChangePartitionResource():
    print "bbbbbbbbbb"
    return 0


def tc_ModifyFCPStorageGroup():
    return 1


def tc_DetachFCPStorageGroup():
    return 1


def tc_AttachFICONStorageGroup():
    return 1


def tc_DetachFICONStorageGroup():
    return 1