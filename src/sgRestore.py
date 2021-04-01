'''
Created on Mar 30, 2018

This script is to submit a storage request to storage admin "SAM".

Example:
-hmc 9.12.35.135 -cpc T257 -config T257-sg.cfg -email xxx@cn.ibm.com

Updated on Mar 31, 2021 --- Move to github
Updated on August 6, 2020 --- Add support to NVMe storage group
                              We need to update the NVMe adapter ID if any changed
Updated on September 10, 2018 --- Add SAM's email address as a input parameter
Updated on August 2, 2018 --- API change the 'adapter-count' field in "create storage group request body contents" to 'connectivity'
Updated on July 20, 2018 --- Add restore the FICON storage group
                             Note, the FICON device number is set when the storage groups are restored
                             But , the FCP device number is set when the storage groups are attached
Updated on May 18, 2018 --- Add 'email to addr' property in the storage group request

config file example:
[M257_KVMP10_auto]
#maximum number of partitions
maxnumofpars = 1
#number of paths or adapters
numofpaths = 2
#storage group description
sgdesc = This is the test description
#storage group shared or not
sgshared = False
#storage volume configs
sgstorvolscfg = [{'storVolDesc': 'M257_KVMP10_Boot_Volume', 'storVolName': '17.00 GiB Boot', 'storVolUse': 'boot', 'storVolSize': 16.03}, 
                 {'storVolDesc': 'M257_KVMP10_120GB_Data_Volume', 'storVolName': '120.00 GiB Data', 'storVolUse': 'data', 'storVolSize': 112.18}, 
                 {'storVolDesc': 'M257_KVMP10_512GB_Data_Volume', 'storVolName': '512.00 GiB Data', 'storVolUse': 'data', 'storVolSize': 480.79}]
#storage group type
stortype = fcp

@author: mayijie
'''

from CommonAPI.prsm2api import *
from CommonAPI.wsaconst import *
import CommonAPI.hmcUtils
import sys, ConfigParser, logging, threading, os, argparse, traceback, re

hmc = None
cpcID = None

hmcHost = None
cpcName = None
configFile = None
emailList = None
createPass = list()
createFail = list()

# the key is the sg name, the value is the properties of the sg, by dict format
sectionDict = dict()

# for multi-thread write protection
lock = threading.Lock()

# ------------------------------------------------------------------ #
# ----- Start of parseArgs function -------------------------------- #
# ------------------------------------------------------------------ #
def parseArgs():
    print ">>> parsing the input parameters..."
    global hmcHost, cpcName, configFile, emailList
    
    parser = argparse.ArgumentParser(description='create storage groups by configure file')
    parser.add_argument('-hmc', '--hmcHost', metavar='<HMC host IP>', help='HMC host IP')
    parser.add_argument('-cpc', '--cpcName', metavar='<cpc name>', help='cpc name')
    parser.add_argument('-config', '--configFile', metavar='<configure file name>', help='indicate configure file name / location')
    parser.add_argument('-email', '--emailList', metavar='<email address list>', help='split the email addresses with comma')
    
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
        _emailList = assertValue(pyObj=args, key='emailList', listIndex=0, optionalKey=True)
        emailList = checkValue('emailList', _emailList , emailList)
        if emailList == None:
            exc = Exception("You should specify the email list of SAM")
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
# ----- Start of procSingleStorageGroup function ------------------- #
# ------------------------------------------------------------------ #
def procSingleStorageGroup(sgName):
    global sectionDict
    try:
        if lock.acquire():
            sgDict = sectionDict[sgName]
            sgTemp = constructSgTemplate(sgName, sgDict)
            if sgTemp == None:
                # TODO: need add error handling here
                print "[procSingleStorageGroup fail] storage group", sgName
            lock.release()
        if lock.acquire():
            sgRet = createStorageGroup(hmc, sgTemp)
            lock.release()
    except Exception as exc: 
        print "[EXCEPTION procSingleStorageGroup] storage group", sgName
        '''
        print '-'*60
        traceback.print_exc(file=sys.stdout)
        print '-'*60
        '''
        # no need to add "if lock.acquire():" here since the lock must be occupied, just release.
        createFail.append(sgName)
        lock.release()

# ------------------------------------------------------------------ #
# ----- End of procSingleStorageGroup function --------------------- #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of constructSgTemplate function ---------------------- #
# ------------------------------------------------------------------ #
def constructSgTemplate(sgName, sgDict):
    global cpcURI, emailList
    sgTempl = dict()
    svTempl = dict()
    
    try:
        sgTempl['name'] = sgName
        sgTempl['cpc-uri'] = cpcURI
        
        # for common properties
        if (sgDict.has_key('sgdesc') and sgDict['sgdesc'] != ''):
            sgTempl['description'] = sgDict['sgdesc']
        sgTempl['type'] = sgDict['stortype']
        if (sgDict['sgshared'] == "True"):
            sgTempl['shared'] = True
        else:
            sgTempl['shared'] = False
        
        # for fcp and fc only properties
        if (sgTempl['type'] == 'fcp' or sgTempl['type'] == 'fc'):
            sgTempl['connectivity'] = int(sgDict['numofpaths'])
            sgTempl['email-to-addresses'] = emailList.split(',')
        
        # for fcp only properties
        if (sgTempl['type'] == 'fcp'):
            sgTempl['max-partitions'] = int(sgDict['maxnumofpars'])

        svsTempl = constructSvTemplate(eval(sgDict['sgstorvolscfg']))
        sgTempl['storage-volumes'] = svsTempl
        
    except  Exception as exc:
        print "[EXCEPTION constructSgTemplate]", exc
        raise exc
    return sgTempl

# ------------------------------------------------------------------ #
# ----- End of constructSgTemplate function ------------------------ #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# ----- Start of constructSvTemplate function --------table 10------ #
# ------------------------------------------------------------------ #
def constructSvTemplate(svCfgList):
    svsTempl = list()
    
    try:
        for sv in svCfgList:
            svTempl = dict()
            svTempl['operation'] = 'create'
            
            # for common properties
            if (sv.has_key('storVolDesc') and sv['storVolDesc'] != ''):
                svTempl['description'] = sv['storVolDesc']
            svTempl['usage'] = sv['storVolUse']

            # for FCP and FICON storage groups
            # in FICON, if model != EAV, the size property will not exist in the dict
            if (sv.has_key('storVolSize')):
                svTempl['size'] = float(sv['storVolSize'])
            
            # if the sg is for FICON, construct the FICON only properties
            if sv.has_key('storVolModel'):
                svTempl['model'] = sv['storVolModel']
            
            if sv.has_key('storVolDevNum'):
                svTempl['device-number'] = sv['storVolDevNum']
                
            # for nvme storage groups
            if sv.has_key('storVolAdaId'):
                svTempl['adapter-uri'] = selectAdapter(hmcConn=hmc, adapterID=sv['storVolAdaId'], cpcID=cpcID)[KEY_ADAPTER_URI]

            svsTempl.append(svTempl)
    except  Exception as exc:
        print "[EXCEPTION constructSvTemplate]", exc
        raise exc
    return svsTempl

# ------------------------------------------------------------------ #
# ----- End of constructSvTemplate function ------------------------ #
# ------------------------------------------------------------------ #

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
    
    threads = []
    for sgName in sectionDict.keys():
        t = threading.Thread(target=procSingleStorageGroup, args=(sgName,))
        print ">>> Requesting Storage Group: " + sgName + "..."
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
        print "Here are the storage group(s) be created successfully:", createPass
    if (len(createFail) != 0):
        print "Here are the storage group(s) be created failed:", createFail
    print "Script run completed!!!"