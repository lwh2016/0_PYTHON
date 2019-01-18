# -*- coding: utf-8 -*-
# @file SWCStartTime.py
# @author guokonghui
# @description
# @created Wed Dec 12 2018 15:48:27 GMT+0800 (中国标准时间)
# @last-modified Thu Dec 13 2018 11:13:16 GMT+0800 (中国标准时间)
#

from GetTargetFile import GetTargetFile
from datetime import datetime
import re
import xlsxwriter


def SWCPortStartTime(powerOnPoint, SwcPortTimeList):
    pline = re.split(r"[' ': .]", powerOnPoint)
    pPoint = int(str(
        pline[4])[0:3]) + int(pline[3]) * 1000 + int(pline[2]) * 1000 * 60
    gap = {}
    for t in SwcPortTimeList:
        tline = re.split(r"[' ': .]", t[1])
        tpoint = int(str(
            tline[4])[0:3]) + int(tline[3]) * 1000 + int(tline[2]) * 1000 * 60
        g = tpoint - pPoint
        gap[t[0]] = g / 1000
    # print(gap)
    return gap


def SWCTimePoint(gapList, portList):
    ll = {}
    lastSwcName = ''
    for swcid in portList:
        if (swcid in gapList):
            name = portList[swcid]
            time = gapList[swcid]
            if name not in ll:
                ll[name] = time
            else:
                if ll[name] > time:
                    ll[name] = time
    sorted_ll = []
    for k in ll:
        sorted_ll.append((k, ll[k]))

    def by_key(t):
        return t[1]

    sorted_ll = sorted(sorted_ll, key=by_key)
    return sorted_ll


def main():
    fileHandler = GetTargetFile('.txt')
    FileList = fileHandler.getTarFile()
    RaModelHandler = GetTargetFile('.py')
    PortList = RaModelHandler.getTarFile()

    excelTable = xlsxwriter.Workbook('SWC_Time.xlsx')
    workSheet = excelTable.add_worksheet('SWC_Time')
    gapSheet = excelTable.add_worksheet('Port_Time')
    nameSheet = excelTable.add_worksheet('swcName')
    for txtfile in FileList:
        with open(txtfile, 'r') as f:
            rows = f.readlines()
            if len(rows) == 1:
                powerOnTime = rows[0]
                # print(powerOnTime)
            else:
                portTimeLines = []
                for r in rows:
                    elem = (int(str(r[0:2]), 16), r[2:])
                    portTimeLines.append(elem)
                # print(portTimeLines)
    gapList = SWCPortStartTime(powerOnTime, portTimeLines)

    gapindex = 1
    gapSheet.write_row(0, 0, ('PortId', 'PortStartTimeGap'))
    for g in gapList:
        gapSheet.write_row(gapindex, 0, (g, gapList[g]))
        gapindex += 1

    for pyfile in PortList:
        if pyfile.split('\\')[-1] == 'RA_Model.py':
            RaModelFile = pyfile
            break
    with open(RaModelFile, 'r') as fr:
        port2idList = {}
        lines = fr.readlines()
        # print(lines[10])
        for line in lines:
            if line.startswith('port_to_id['):
                lineList = re.split(r"[' '=_\n']", str(line))
                # print(lineList)
                swcPortId = int(lineList[-2])
                swcname = str(lineList[3])[1:]
                port2idList[swcPortId] = swcname

        # print(port2idList)

    portIdIndex = 1
    nameSheet.write_row(0, 0, ('PortId', 'SwcIncludePort'))
    for g in port2idList:
        nameSheet.write_row(portIdIndex, 0, (g, port2idList[g]))
        portIdIndex += 1

    ll = SWCTimePoint(gapList, port2idList)
    # print(ll)

    workSheet.write_row(0, 0, ('swcName', 'swcStartTime'))
    index = 1
    for l in ll:
        workSheet.write_row(index, 0, l)
        index = index + 1
    excelTable.close()


if __name__ == '__main__':
    main()