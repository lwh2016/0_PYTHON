class logger(object):
    def __init__(self, logType='terminal'):
        self.logType = logType

    def logInfo(self, infoStr):
        if self.logType == 'terminal':
            print('logInfo: %s ' % infoStr)
        else:
            pass

    def logDebug(self, debugStr):
        if self.logType == 'terminal':
            print('logDebug: %s ' % debugStr)
        else:
            pass

    def logWarn(self, warningStr):
        if self.logType == 'terminal':
            print('logWarn: %s ' % warningStr)
        else:
            pass

    def logError(self, errorStr):
        if self.logType == 'terminal':
            print('logError: %s ' % errorStr)
        else:
            pass


if __name__ == "__main__":
    log = logger('terminal')
    log.logInfo('normally!')