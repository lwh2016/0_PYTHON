import os
import sys


class GetTargetFile(object):
    def __init__(self,
                 targetFileFormat,
                 targetFilePath=os.path.split(os.path.realpath(__file__))[0]):
        self.targetFileFormat = targetFileFormat
        self.targetFileName = []
        self.targetFilePath = targetFilePath
        # print(self.targetFilePath)

    def getTarFile(self):
        # targetFilePath = os.path.split(os.path.realpath(sys.argv[0]))
        # targetFilePath = list(targetFilePath)[0]
        # print(targetFilePath)
        try:
            for roots, dirs, files in os.walk(self.targetFilePath):
                for file in files:
                    if os.path.splitext(file)[1] == str(self.targetFileFormat):
                        self.targetFileName.append(os.path.join(roots, file))
        except ValueError as e:
            print("No %s file in the specified path Or Specified path is wrong"
                  % self.targetFileFormat)
        finally:
            pass
        filesNum = len(self.targetFileName)
        if filesNum > 0:
            print('\n****** Get %d %s File : \n' % (filesNum,
                                                    self.targetFileFormat))
            for f in self.targetFileName:
                print('\t', f, end='\n')
        else:
            print("\n******Don't Get Any %s File" % (self.targetFileFormat))
        # print(self.targetFileName)
        return self.targetFileName


def main():
    gf = GetTargetFile('.dbc')
    gf.getTarFile()


if __name__ == '__main__':
    main()
