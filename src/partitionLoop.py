'''
Created on Jun 13, 2018 

Updated on July 30, 2018 --- add the partitionLoopStart.sh

This script is to verify the whole life cycle of a partition, from create, offline resource update, start the partition, 
dynamic resource change, stop the partition, and at last, delete the partition.

There is a flag in the file to indicate if the loop continue or stop. We use a rundeck job to configure the flag. If you run
the start job, the job will start this script and set the flag to 1, the script will run the loop once a while and once again
after a interval. If you run the stop job, the job will set the flag to 0 and the script will stop after a entile loop.

Example:
-hmc 9.12.35.135 -cpc M90 -config partitionLoop.cfg

config file example:
[KVMP101]
par_desc = This is a des of 101
par_type = linux
proc_mode = dedicated
proc_type = ifl
proc_num = 1
init_mem = 1
max_mem = 1

@author: mayijie
'''

from prsm2api import *
from wsaconst import *
import hmcUtils
import sys, ConfigParser, logging, threading, os, argparse, traceback, re, time

hmc = None
cpcID = None

hmcHost = None
cpcName = None
configFile = None

# the key is 'common' and partition name, the value is the properties of the partition, by dict format
sectionDict = dict()
parUri = None
parName = None

# each loop interval (second) between partition create / delete / create.
loop_interval = 60
# logs stored in the folder ./partitionLoopLog/
log_directory = 'partitionLoopLog'
loopFlagCode = 0
loopFlagFile = 'loopFlag.cfg'

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

def loadConfig(configFile):
    print ">>> loading the config file..."
    global sectionDict
    
    try:
        # read the config file
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
    except Exception as exc:
        print "[EXCEPTION loadConfig]", exc.message
    finally:
        print ">>> loading config file complete!"

def setLoopFlagCode():
    print ">>> setting the loop flag file..."
    global loopFlagFile
    
    try:
        # read the flag file
        if '/' not in loopFlagFile:
            loopFlagFile = os.path.join(sys.path[0], loopFlagFile)
        # open the file, if the file not exist, just create
        fileObj = open(loopFlagFile, 'w')
        fileObj.write('1')

    except IOError as exc:
        print "[EXCEPTION setLoopFlagCode] Cannot open the flag file [%s]: %s"%(loopFlagFile, exc)  
        raise exc
    except Exception as exc:
        print "[EXCEPTION setLoopFlagCode]", exc.message
    finally:
        print ">>> setting the flag file complete!"
        if fileObj:
            fileObj.close()

def getLoopFlagCode():
    print ">>> getting the loop flag file..."
    global loopFlagFile
    
    try:
        # read the flag file
        if '/' not in loopFlagFile:
            loopFlagFile = os.path.join(sys.path[0], loopFlagFile)
        # open the file, if the file not exist, just create
        fileObj = open(loopFlagFile, 'r')
        line = fileObj.readline()
        
        # finally could also be executed
        return line
    except IOError as exc:
        print "[EXCEPTION getLoopFlagCode] Cannot open the flag file [%s]: %s"%(loopFlagFile, exc)  
        raise exc
    except Exception as exc:
        print "[EXCEPTION getLoopFlagCode]", exc.message
    finally:
        if fileObj:
            fileObj.close()

def parseCommonParameters(commonDict):
    global loop_interval
    loop_interval = commonDict['loop_interval']
    log_directory = commonDict['log_directory']

def createPartitionTemplate(parName, parDict):
    iProcNum = None
    iProcType = None
    partitionTempl = dict()
    
    try:
        for (propName, propValue) in parDict.items():
            # partition properties
            partitionTempl['name'] = parName
            if propName == 'par_type':
                partitionTempl['type'] = propValue
            if propName == 'par_desc':
                partitionTempl['description'] = propValue
            if propName == 'par_reserveresources':
                partitionTempl['reserve-resources'] = True if (propValue.lower() == 'true') else False
            
            # processor properties
            if propName == 'proc_mode':
                partitionTempl['processor-mode'] = propValue
            if propName == 'proc_type':
                if iProcNum == None:
                    iProcType = propValue.lower()
                else:
                    if propValue.lower() == 'cp':
                        partitionTempl['cp-processors'] = iProcNum
                    elif propValue.lower() == 'ifl':
                        partitionTempl['ifl-processors'] = iProcNum
                    else:
                        exc = Exception("The procType should either be 'cp' or be 'ifl', other values invalid!")
                        raise exc
            if propName == 'proc_num':
                if iProcType == None:
                    iProcNum = int(propValue)
                else:
                    if iProcType == 'cp':
                        partitionTempl['cp-processors'] = int(propValue)
                    elif iProcType == 'ifl':
                        partitionTempl['ifl-processors'] = int(propValue)
                    else:
                        exc = Exception("The procType should either be 'cp' or be 'ifl', other values invalid!")
                        raise exc
            
            # memory properties
            if propName == 'init_mem':
                partitionTempl['initial-memory'] = int(propValue)
            if propName == 'max_mem':
                partitionTempl['maximum-memory'] = int(propValue)
    
    except  Exception as exc:
        print "[EXCEPTION createPartitionTemplate]", exc
        raise exc
    
    return partitionTempl

def createPartition(hmc, cpcID, parTemp):
    print ">>> creating the partition..."
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

def verifyPartitionExistence(hmc, cpcID, parName):
    print ">>> verifying the partition existence.."
    global parUri
    try:
        parListOnCpc = getCPCPartitionsList(hmc, cpcID)
        for parInfo in parListOnCpc:
            if assertValue(pyObj=parInfo, key='name') == parName:

                # record the partition ID, for the partition delete use
                parUri = assertValue(pyObj=parInfo, key='object-uri')
                return True
        parUri = None
        return False
        
    except Exception as exc:
        print "[EXCEPTION verifyPartitionCreated]", exc.message

def logToFile(message):
    global log_directory
    
    try:
        if '/' not in log_directory:
                log_directory = os.path.join(sys.path[0], log_directory)
        if not os.path.exists(log_directory):
            os.mkdir(log_directory) 
    
        (iDate, iTime) =  (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())).split()
        
        logFile = log_directory + '/' + iDate + '.log'
        line = iTime + ' >>> ' + message
        # 'a+' open a file with appending mode, 'w+' will judge if the file exist, delete the file.
        fileObj = open(logFile, 'a+')
        fileObj.writelines([line])
        fileObj.write('\n')

    except IOError as exc:
        print "[IOEXCEPTION logToFile] Cannot open the flag file [%s]: %s"%(logToFile, exc)  
        raise exc
    except Exception as exc:
        print "[EXCEPTION logToFile]", exc.message
    finally:
        if fileObj:
            fileObj.close()


# main function

try:
    parseArgs()
    loadConfig(configFile)
    setLoopFlagCode()
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
    
    while (1):
        # get the loop flag to check if the loop still on
        loopFlagCode = getLoopFlagCode()
        print ">>> getting the loop flag code complete!"

        if int(loopFlagCode) == 0:
            print ">>> The loopFlagCode is 0, stop the loop!!!"
            break
        
        # analysis the configure data, and construct the partition template
        for key in sectionDict.keys():
            if key == 'common':
                # parse the common parameters
                parseCommonParameters(sectionDict[key])
            else:
                # parse the partition parameters
                parName = key
                parTemp = createPartitionTemplate(parName, sectionDict[key])
        
        # delete the partition if already exist
        if verifyPartitionExistence(hmc, cpcID, parName):
            print ">>> The partition already exist, delete!"
            if parUri != None:
                deletePartition(hmc, parURI = parUri)
            logToFile("Partition already exist --> Delete!")
        
        # create the partition
        createPartition(hmc, cpcID, parTemp)
        print ">>> Creating partition complete!"
        logToFile("Partition Created...")
        
        print ">>> sleep", loop_interval, "seconds..."
        time.sleep(float(loop_interval))
        
        # verify the partition is already in the list
        if verifyPartitionExistence(hmc, cpcID, parName):
            print ">>> verified, the partition exists in the cpc!"
            logToFile("Partition Created. --> Verified success!")
        else:
            # record
            print ">>> verified failed, the partition NOT exists in the cpc!!!"
            logToFile("Partition Created. --> Verified failed!")
        
        print ">>> sleep", loop_interval, "seconds..."
        time.sleep(float(loop_interval))
        if parUri != None:
            print ">>> Deleting the partition..."
            deletePartition(hmc, parURI = parUri)
            print ">>> Deleting the partition complete!"
            logToFile("Partition Deleted...")

        print ">>> sleep", loop_interval, "seconds..."
        time.sleep(float(loop_interval))
        # verify the partition is removed in the list
        if not verifyPartitionExistence(hmc, cpcID, parName):
            print ">>> verified, the partition has been removed successfully!"
            logToFile("Partition Deleted. --> Verified success!")
        else:
            print ">>> verified failed, the partition still in the CPC!!!"
            logToFile("Partition Deleted. --> Verified failed!")
        
except IOError as exc:
    print "[EXCEPTION] Configure file read error!", exc
except Exception as exc:
    print "[EXCEPTION]", exc.message
  
finally:
    if hmc != None:
        hmc.logoff()
    print "Script run completed!!!"