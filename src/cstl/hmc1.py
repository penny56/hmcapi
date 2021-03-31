#/usr/bin/python
# encoding: utf-8

import os.path
import re

# YJ: 20210106 Search and extract a string from all files in a folder

def eachFile(filepath):
    pathDir =  os.listdir(filepath)
    for allDir in pathDir:
        child = os.path.join('%s/%s' % (filepath, allDir))
        if os.path.isfile(child):
            readFile(child)
            continue
        eachFile(child)

def readFile(filenames):
        fopen = open(filenames, 'rb') # r 代表read
        fileread = fopen.read()
        fopen.close()
        
        # Search a whole file
        '''
        t=re.search(b'List the volumes',fileread)
        if t:
            print ":"+filenames
            arr.append(filenames)
        '''

        # Search a file line by line, get the text string followed by the pattern: 'TC_TITLE :'
        lines = fileread.split('\n')
        for line in lines:
            t=re.search(b'TC_TITLE :',line)
            if t:
                print filenames.split('/')[-1] + ' :' + line.split(':')[1]

if __name__ == "__main__":
    filenames = '/Users/mayijie/git/zrobot/zRobot_WSAPI/libraries/sge'
    arr=[]
    eachFile(filenames)
    '''
    for i in arr:
        print i
    '''
