import cantools
from GetTargetFile import GetTargetFile


def getMsg():
    dbcHandler = GetTargetFile('.dbc')
    dbcFileList = dbcHandler.getTarFile()
    msgAttrList = []
    for dbcfile in dbcFileList:
        dbc = cantools.database.load_file(dbcfile)
        for msg in dbc.messages:
            msgAttrList.append(msg.name)
    return msgAttrList


if __name__ == "__main__":
    print(getMsg())