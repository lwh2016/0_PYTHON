import os
import copy as cp
from shutil import copyfile as cpf


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

    #print("The %s file not in this path %s" % (name, path))
    return None


def searchFileByFormat(path, form, deepMod=True):
    searchRes = set()
    if os.path.isdir(path):
        if deepMod:
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.split(".")[-1] == form:
                        result = os.path.join(str(root), str(file))
                        searchRes.add(result)
        else:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isfile(item_path):
                    if item_path.split(".")[-1] == form:
                        searchRes.add(item_path)
    return searchRes


def getCxxHeaders(path, cxxFile):
    if not os.path.isfile(cxxFile):
        try:
            cxxFile = searchFileByName(path, cxxFile)
        except:
            print("The %s not exist" % cxxFile)
    headersList = []
    headersSet = set()
    with open(cxxFile, 'r') as f:
        arrayLines = f.readlines()
    for line in arrayLines:
        if line.startswith("#include \""):
            header = line.split("\"")[-2]
            headersList.append(header)
    for f in headersList:
        res = searchFileByName(path, f)
        if res:
            headersSet.add(res)
    return headersSet


def analysisAllHeaders(path, file2ana, deepMod=True):
    if not os.path.isfile(file2ana):
        file2ana = searchFileByName(path, file2ana)
    anaResult = set()
    analysisedSet = set()
    if not deepMod:
        anaResult = getCxxHeaders(path, file2ana)
    else:
        curLevelHeadersSet = getCxxHeaders(path, file2ana)
        length = len(curLevelHeadersSet)
        while length > 0:
            print(length)
            lastLevelHeadersSet = cp.deepcopy(curLevelHeadersSet)
            anaResult = anaResult | lastLevelHeadersSet
            curLevelHeadersSet.clear()
            for file in lastLevelHeadersSet:
                file_src = getCxxSource(path, file)
                src_headerSet = set()
                if file_src:
                    src_headerSet = getCxxHeaders(path, file_src)
                    analysisedSet.add(file_src)
                headerSet = getCxxHeaders(path, file)
                analysisedSet.add(file)
                curLevelHeadersSet = curLevelHeadersSet | headerSet | src_headerSet
            intersection = cp.deepcopy(curLevelHeadersSet & analysisedSet)
            curLevelHeadersSet = cp.deepcopy(curLevelHeadersSet - intersection)
            length = len(curLevelHeadersSet)
    return anaResult


def getCxxSource(path, headerFile):
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
        temName = str(namelist[0]) + "."

    names = [temName + str("c"), temName + str("cc"), temName + str("cpp")]
    pathName = []
    for n in names:
        pn = os.path.join(path, n)
        pathName.append(pn)

    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isfile(item_path):
            if item_path in pathName:
                return item_path

    print("This header file %s not have source file" % header)
    return


def write2file(tarPath, filename, contentList):
    file = os.path.join(tarPath, filename)
    contentList = sorted(contentList)
    with open(file, 'w') as f:
        for l in contentList:
            f.write(l + "\n")


def copyFolders(srcPath, orgFileList, tarPath):
    for f in orgFileList:
        if not os.path.isfile(f):
            f = searchFileByName(srcPath, f)
        tarPathTail = f.split(srcPath)[-1]
        tarPathFile = tarPath + tarPathTail
        tp, tf = os.path.split(tarPathFile)
        if not os.path.isdir(tp):
            os.makedirs(tp)
        cpf(f, tarPathFile)


def modifyFile(file):
    if not os.path.isfile(file):
        print("%s is not exist!")
        return
    p, file_new = os.path.split(file)
    file_new = "m_" + file_new
    file_new = os.path.join(p, file_new)
    f_new = open(file_new, 'w')
    with open(file, 'r') as f:
        arrayLines = f.readlines()
        for line in arrayLines:
            if "namespace apollo" in line:
                line = "//" + line
            elif "apollo." in line:
                line = line.replace("apollo.", "")
            elif "apollo::" in line:
                line = line.replace("apollo::", "")
            f_new.write(line)
        f.close()
        f_new.close()
    os.remove(file)
    os.rename(file_new, file)


if __name__ == "__main__":
    cxxFile = "/examples/talker.cc"
    path = "/home/igs/Code/cyber"

    # 获取并修改pb文件,先执行protoc.sh脚本才有意义
    pbSet = searchFileByFormat(path, "proto")
    for pbf in pbSet:
        modifyFile(pbf)
    # print(pbSet)
    # print(len(pbSet))

    # 获取头文件
    r_headers = analysisAllHeaders(path, cxxFile)

    # 获取对应的源文件
    number_src = 0
    r_srcs = []
    for h in r_headers:
        sf = getCxxSource(path, h)
        if sf is not None:
            r_srcs.append(sf)
            number_src = number_src + 1

    # 把头文件和源文件路径写入日志文件
    write2file(path, "headers.txt", r_headers)
    print(len(r_headers))

    write2file(path, "srcs.txt", r_srcs)
    print(len(r_srcs))

    # 定义复制的目的路径并将提取的文件复制到目的路径下
    tarPath = "/home/igs/modify_cyber"
    copyFolders(path, r_headers, tarPath)
    copyFolders(path, r_srcs, tarPath)

    # 生成修改文件的存放路径
    m_r_headers = []
    m_r_srcs = []
    for h in r_headers:
        h = tarPath + h.split(path)[-1]
        m_r_headers.append(h)
    #print(m_r_headers)

    for s in r_srcs:
        s = tarPath + s.split(path)[-1]
        m_r_srcs.append(s)
    #print(m_r_srcs)

    # 将修改后的文件列表写入到log中
    write2file(tarPath, "m_headers.txt", m_r_headers)
    print(len(m_r_headers))

    write2file(tarPath, "m_srcs.txt", m_r_srcs)
    print(len(m_r_srcs))

    # 修改文件并保存
    for ele_h in m_r_headers:
        modifyFile(ele_h)
    for ele_s in m_r_srcs:
        modifyFile(ele_s)
