# -*- coding: utf-8 -*-
# @file updateAdasToolsPy.py
# @author guokonghui
# @description：using for update Info from New PIE to ADAS/MotionWise Tools
# @created Thu Nov 01 2018 15:20:26 GMT+0800 (中国标准时间)
# @last-modified Thu Nov 15 2018 09:07:55 GMT+0800 (中国标准时间)
#

import os
import sys
from shutil import move
from shutil import copyfile
from shutil import rmtree
import configparser
'''
__init__()中
self.midPath: 解压得到的文件的暂存路径, 执行完毕后会自动删除
self.cmdPath：解压软件Bandizip中bc.exe的绝对路径
self.newPiePath：新PIE包的路径
self.dataSorPath： = self.midPath
self.TargetPath：执行当前脚本的Python的安装路径

update()中
dataSorPath：解压后的的data文件夹下的文件相对路径
dataTarPath：上述路径data文件夹中的文件被移动到的位置

RaTypeSorPath：新PIE包中的Ra_Type.py的相对路径
RaTypeTarPath：新PIE包中的Ra_Type.py的被移动到的位置

'''


class updateAdasToolPackages(object):
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(
            os.path.dirname(os.path.realpath(__file__)) +
            "\\UpdatePieInfo.ini")

        self.midPath = self.config.get('MidInfo', 'midPath')
        if not os.path.exists(self.midPath):
            os.makedirs(self.midPath)
        self.cmdPath = self.config.get('CmdInfo', 'cmdPath')
        self.newPiePath = self.config.get('SorInfo', 'newPiePath')
        self.dataSorPath = self.midPath
        # self.TargetPath = sys.path[5]
        self.TargetPath = "E:\\Python"

    def copyAdasTools2Target(self, sorPath, targetPath):
        sorList = os.listdir(sorPath)
        if not os.path.exists(targetPath):
            os.makedirs(targetPath)
        for f in sorList:
            aa, bb = f.split('.')
            f = sorPath + aa + "." + bb
            targetFile = targetPath + aa + "." + bb
            move(f, targetFile)
        os.removedirs(sorPath)

    def copyRaType2Target(self):
        RaTypeSorPath = self.config.get('SorInfo', 'RaTypeSorPath')
        RaTypeTarPath = self.config.get('TargetInfo', 'RaTypeTarPath')
        sorPath = self.newPiePath + RaTypeSorPath
        tarPath = self.TargetPath + RaTypeTarPath
        Ra_typeList = []
        for roots, dirs, files in os.walk(sorPath):
            for divs in dirs:
                if 'CtAp' in divs or 'CtCd' in divs:
                    curSorPath = sorPath + str(divs) + "\\ContractHeader"
                    fList = os.listdir(curSorPath)
                    for f in fList:
                        if f == 'Ra_Type.py':
                            targetFile = tarPath + str(divs) + "\\"
                            if not os.path.exists(targetFile):
                                os.makedirs(targetFile)
                            f = os.path.join(curSorPath, f)
                            print(f)
                            targetFile = targetFile + "Ra_Type.py"
                            copyfile(f, targetFile)
                            break

    def update(self):
        AdasToolsPath = self.config.get('SorInfo', 'adasToolPath')
        exeFilePath = self.newPiePath + AdasToolsPath
        os.system(self.cmdPath + ' ' + exeFilePath + ' ' + self.midPath)

        osList = []

        dataSorPath = self.config.get('SorInfo', 'dataSorPath')
        dataTarPath = self.config.get('TargetInfo', 'dataTarPath')
        osList.append((self.dataSorPath + dataSorPath,
                       self.TargetPath + dataTarPath))

        scriptSorPath = self.config.get('SorInfo', 'scriptSorPath')
        scriptTarPath = self.config.get('TargetInfo', 'scriptTarPath')
        osList.append((self.dataSorPath + scriptSorPath,
                       self.TargetPath + scriptTarPath))

        binSorPath = self.config.get('SorInfo', 'binSorPath')
        binTarPath = self.config.get('TargetInfo', 'binTarPath')
        osList.append((self.dataSorPath + binSorPath,
                       self.TargetPath + binTarPath))

        csvSorPath = self.config.get('SorInfo', 'csvSorPath')
        csvTarPath = self.config.get('TargetInfo', 'csvTarPath')
        osList.append((self.dataSorPath + csvSorPath,
                       self.TargetPath + csvTarPath))

        pmSorPath = self.config.get('SorInfo', 'pmSorPath')
        pmTarPath = self.config.get('TargetInfo', 'pmTarPath')
        osList.append((self.dataSorPath + pmSorPath,
                       self.TargetPath + pmTarPath))

        motionwiseSorPath = self.config.get('SorInfo', 'motionwiseSorPath')
        motionwiseTarPath = self.config.get('TargetInfo', 'motionwiseTarPath')
        osList.append((self.dataSorPath + motionwiseSorPath,
                       self.TargetPath + motionwiseTarPath))

        for i in osList:
            self.copyAdasTools2Target(i[0], i[1])

        self.copyRaType2Target()
        print("******New PIE Packages is updated!******")
        rmtree(self.midPath)


def main():
    upadas = updateAdasToolPackages()
    upadas.update()


if __name__ == '__main__':
    main()