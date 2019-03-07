import os
import copy as cp


def searchFileByName(path, name, deepMod=True):
    if os.path.isfile(name):
        return name
    else:
        relPath, relName = os.path.split(name)
        if deepMod:
            for root, dirs, files in os.walk(path):
                if relName in files:
                    result = os.path.join(str(root), str(relName))
                    if name in result:
                        return result
        else:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isfile(item_path):
                    if name in item:
                        return item_path

    print("The %s file not in this path %s" % (name, path))
    return


def getCxxHeaders(path, cxxFile):
    exclusions = []
    if not os.path.isfile(cxxFile):
        try:
            cxxFile = searchFileByName(path, cxxFile)
        except:
            exclusions.append(cxxFile)
            print("The %s not exist" % cxxFile)
    headersList = []
    headersSet = set()
    with open(cxxFile, 'r') as f:
        arrayLines = f.readlines()
    for line in arrayLines:
        if line.startswith("#include \""):
            header = line.split("\"")[-2]
            if header not in exclusions:
                headersList.append(header)
    for f in headersList:
        headersSet.add(searchFileByName(path, f))
    return headersSet


def analysisAllHeaders(path, file2ana, deepMod=True):
    if not os.path.isfile(file2ana):
        file2ana = searchFileByName(path, file2ana)
    anaResult = set()
    if not deepMod:
        anaResult = getCxxHeaders(path, file2ana)
    else:
        curLevelHeadersSet = getCxxHeaders(path, file2ana)
        N_set = {None}
        curLevelHeadersSet = curLevelHeadersSet - N_set
        length = len(curLevelHeadersSet)
        while length > 0:
            lastLevelHeadersSet = cp.deepcopy(curLevelHeadersSet)
            anaResult = anaResult | lastLevelHeadersSet
            curLevelHeadersSet.clear()
            for file in lastLevelHeadersSet:
                headerSet = getCxxHeaders(path, file)
                curLevelHeadersSet = curLevelHeadersSet | headerSet
                N_set = {None}
                curLevelHeadersSet = curLevelHeadersSet - N_set
            length = len(curLevelHeadersSet)
    return anaResult


def getCxxSource(path ,headerFile):
    if not os.path.isfile(headerFile):
        headerFile = searchFileByName(path, headerFile)
    path, name = os.path.split(headerFile)
    header = cp.deepcopy(name)
    namelist = name.split(".")
    namelist.pop()
    temName = ""
    if len(namelist) > 1:
        for ele in namelist:
            temName = temName + str(ele) + "."
    else:
        temName = str(namelist[0])

    names = [temName + str(".c"), temName + str(".cc"), temName + str(".cpp")]
    pathName = []
    for n in names:
        pn = os.path.join(path,n)
        pathName.append(pn)

    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isfile(item_path):
            if item_path in pathName:
                return item_path
                
    print("This header file %s not have source file" % header)
    return


if __name__ == "__main__":
    cxxFile = "/examples/talker.cc"
    path = "/home/igs/Code/cyber"

    r_headers = analysisAllHeaders(path, cxxFile)
    print(len(r_headers))

    number_src = 0
    for h in r_headers:
        sf = getCxxSource(path, h)
        if sf is not None:
            number_src = number_src + 1
        print(sf)
    print(number_src)



