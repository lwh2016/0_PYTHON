import win32com.client as comclient
import win32event
from shutil import copyfile


class CANoeHandle(object):
    AppStarted = False
    AppQuited = False

    def __init__(self):
        self.CANoe = None
        self.WriteWindow = None

    def AppStart(self):
        try:
            self.CANoe = comclient.Dispatch('CANoe.Application')
            self.AppStarted = True
            self.WriteWindow = self.CANoe.UI.Write
        except Exception:
            self.CANoe = None
            return

    def AppQuit(parameter_list):
        pass

    def CfgLoad(self):

    '''
    def CreatRBS(self, ProjName='RBS.cfg'):
        TempCfgFile = r'F:\0_PYTHON\9-WorkSpace\6_AutoRBS\Template.cfg'
        ProjName = 'F:\\0_PYTHON\\9-WorkSpace\\6_AutoRBS\\' + ProjName
        copyfile(TempCfgFile, ProjName)
        self.CANoe.Open(ProjName)
        self.CANoe.Configuration.Simulation_Setup.CANNetWorks()
    '''


def main():
    CANoe = CANoeHandle()
    CANoe.AppStart()
    CANoe.CreatRBS()


if __name__ == '__main__':
    main()
