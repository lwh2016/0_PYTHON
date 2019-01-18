# -*- coding: utf-8 -*-
# @file DbcAddNode.py
# @author guokonghui
# @description :add ECU Nodes to DBC Files
# @created Thu Oct 25 2018 15:01:53 GMT+0800 (中国标准时间)
# @last-modified Tue Nov 13 2018 14:42:10 GMT+0800 (中国标准时间)
#
import re
import os
from shutil import copyfile
from GetTargetFile import GetTargetFile


class DbcAddNode(object):
    def __init__(self, orgDbcFile):
        try:
            self.fr = open(orgDbcFile, 'r')
            self.dbcArrays = self.fr.readlines()
            self.fileName = orgDbcFile.split('.')[0].split('\\')[-1]
            self.filePath = os.path.dirname(os.path.realpath(orgDbcFile))
            self.motifiedFilePath = self.filePath + '\\addNodeDBCs\\'
            '''
            print(self.fileName)
            print(self.filePath)
            print(self.motifiedFilePath)
            '''
            if not os.path.exists(self.motifiedFilePath):
                os.makedirs(self.motifiedFilePath)
            copyfile(orgDbcFile,
                     self.motifiedFilePath + self.fileName + '.dbc')

        except IOError as e:
            print('Read File Error!')
            return

    def addNode(self, newNode='otherECUs'):
        for line in self.dbcArrays:
            if line.startswith('BU_: '):
                idd = self.dbcArrays.index(line)
                self.dbcArrays[idd] = 'BU_: iECU ' + newNode

            # add node
            if line.startswith('BO_ ') or line.startswith(' SG_ '):
                lineList = line.split(' ')
                idd = self.dbcArrays.index(line)

                if 'Vector__XXX' not in lineList[-1]:
                    if 'iECU' in lineList[-1]:
                        self.dbcArrays[idd] = self.dbcArrays[idd].replace(
                            lineList[-1], 'iECU')
                    else:
                        self.dbcArrays[idd] = self.dbcArrays[idd].replace(
                            lineList[-1], newNode)
                else:
                    self.dbcArrays[idd] = self.dbcArrays[idd].replace(
                        'Vector__XXX', newNode)
                    # print(self.dbcArrays[idd])

        dbcfile_motified = str(self.motifiedFilePath) + self.fileName + '.dbc'
        with open(dbcfile_motified, 'w') as f:
            for line in self.dbcArrays:
                f.write(line)


def main():
    dbcHandler = GetTargetFile('.dbc')
    dbcFileList = dbcHandler.getTarFile()

    for dbcfile in dbcFileList:
        addNodes = DbcAddNode(dbcfile)
        addNodes.addNode('otherECUs')


if __name__ == '__main__':
    main()
