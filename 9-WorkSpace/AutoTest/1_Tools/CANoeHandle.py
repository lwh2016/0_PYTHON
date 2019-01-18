import win32com.client as comclient
import win32event
from logger import logger


class CANoeHandle(object):
    AppStarted = False
    AppQuited = False

    def __init__(self):
        self.CANoeApp = None
        self.logger = logger('terminal')

    def AppStart(self):
        try:
            self.CANoeApp = comclient.Dispatch('Word.Application')
            print(self.CANoeApp.__dict__)
            self.logger.logInfo(str(self.CANoeApp) + ' is starting')
            AppStarted = True
            self.logger.logInfo(str(self.CANoeApp) + ' started')
        except Exception:
            self.logger.logError("CANoe is not start normally!")
            self.CANoeApp = None
            return

    # def cfgLoad

    def AppQuit(parameter_list):
        pass


def main():
    CANoe = CANoeHandle()
    CANoe.AppStart()


if __name__ == '__main__':
    main()
