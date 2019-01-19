# import serial
# ser = serial.Serial('com1')
# print(ser.portstr, end='\n')
import re

searchStyle = re.compile(
    r'root(\s+)(\d+)(\s+)(\d).(\d)(\s+)(\d).(\d)(\s)(\d+)(\s+)(\d+).*(R|Sl)\s+(\d+):(\d+)\s+(\d+):(\d+)\s+(\w+)'
)

fr = open('9-WorkSpace/2_RamUsage/123.txt', 'r')
lines = fr.readlines()
L = []
for line in lines:
    line = line.strip('')
    searchResult = searchStyle.search(line)
    try:
        name = searchResult.group(18)
        usage = searchResult.group(12)
        index = searchResult.group(2)
        if 'CtAp' in name:
            tup = (index, name, usage)
            # print(index, name, usage)
            L.append(tup)
    except:
        pass
s = 0
for elem in L:
    s = s + int(elem[2])
print(s)