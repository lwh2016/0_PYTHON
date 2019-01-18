import os
import sys
import configparser
from 1_Tools import 


class TestProject(object):
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(sys.path[0] +
                         "\\0_Configure\\AutoTestBasicConfig.ini")
        self.pythonPath = self.config.get('BasicPath', 'pythonPath')
        self.PiePath = self.config.get('BasicPath', 'PIE_Path')

    def PreWorkCheck(self):
        pass

    def RunTest(self):
        pass


def main():
    Test = TestProject()
    Test.RunTest()


if __name__ == '__main__':
    main()
