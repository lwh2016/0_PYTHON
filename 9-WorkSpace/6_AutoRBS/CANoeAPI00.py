# -*- coding: utf-8 -*-
# @file CANoeAPI.py
# @author guokonghui
# @description
# @created Tue Nov 13 2018 15:03:58 GMT+0800 (中国标准时间)
# @last-modified Tue Nov 13 2018 15:24:00 GMT+0800 (中国标准时间)
#

import sys
try:
    sys.coinit_flags = 0  # specify free threading
except Exception as ex:
    print("ERROR: Failed to set free threading coinit.")
    print(ex)
import win32com.client as comclient
import win32event
import time
from os.path import (join, splitext)
try:
    from Modules.FileHandlers import Log
    use_log = True
except Exception:
    use_log = False
    print("WARNING: No log class available, print will be used for out!")

_CANOE_API_DEBUG_ = True


class CANoeApplicationEvents(object):
    def OnOpen(self, App):
        print("CANoe started.")


class CANoeConfigurationEvents(object):
    def __init__(self):
        self.cfgClosed = win32event.CreateEvent(None, 0, 0, None)

    def OnClose(self):
        print("Configuration %s is closed.")
        win32event.SetEvent(self.cfgClosed)


class CANoeTestConfigurationEvents(object):
    def __init__(self):
        self.CTRInfo = {"success": False, "generated": False, "reportPath": ""}
        self.testDone = win32event.CreateEvent(None, 0, 0, None)
        self.reportDone = win32event.CreateEvent(None, 0, 0, None)
        self.evenLst = [self.testDone, self.reportDone]
        self.finishReason = -1

    def OnStart(self):
        print("Running ...")

    def OnStop(self, reason):
        self.finishReason = reason
        if _CANOE_API_DEBUG_:
            if reason == 1:
                print("ERROR: The test module was stopped by the user.")
            elif reason == 2:
                print("The test module was stopped by measurement stop.")
        win32event.SetEvent(self.testDone)

    def OnReportGenerated(self, success, sourceFullName, generatedFullName):
        self.CTRInfo["success"] = success
        self.CTRInfo["generated"] = True
        self.CTRInfo["reportPath"] = generatedFullName
        if _CANOE_API_DEBUG_:
            print("Test report %s generated!" % generatedFullName)
        win32event.SetEvent(self.reportDone)


class MeasurementEvents(object):
    def __init__(self):
        self.measurementIsRunning = False
        self.measuermenStarted = win32event.CreateEvent(None, 0, 0, None)

    def OnStart(self):
        self.measurementIsRunning = True
        win32event.SetEvent(self.measuermenStarted)

    def OnStop(self):
        self.measurementIsRunning = False
        win32event.SetEvent(self.measuermenStarted)


class PrivateLog():
    def __init__(self):
        self.warning = self.info
        self.error = self.info
        self.critical = self.info
        self.warning = self.info

    def info(self, message="", coloroverride=None):
        print(message)


class CANoeAPI(object):
    def __init__(self):
        self.CANoe = None
        self.Config = None
        self.Measurement = None
        self.mWrite = None
        self.ReportPath = ""
        self.ReportGenerated = False
        self.MeasuremnetRuning = False
        if use_log:
            self.log = Log.Loging()
        else:
            self.log = PrivateLog()

    # end of __init__

    def WriteMessage(self, Message):
        if self.mWrite is not None:
            self.mWrite.Output(Message)

    def StartCANoe(self, TCName):
        try:
            # starting CANoe
            self.CANoe = comclient.Dispatch("CANoe.Application")
            FullName = self.CANoe.Version.FullName
            self.mWrite = self.CANoe.UI.Write
            self.log.info("Starting %s" % (FullName))
        except Exception:
            self.CANoe = None
            self.log.error("CANoe not found")
            return None

    def LoadCFG(self, cfg):
        # starting required cfg
        try:
            self.log.info("Loading CANoe configuration '%s'" % cfg)
            self.CANoe.Open(cfg, False, False)
            self.InitMeasurementControls()
            self.log.info("Done.")
        except Exception as e:
            self.log.error("Failed to open %s file." % cfg)
            self.log.error("%s" % str(e))
            sys.exit(1)

    def StartMeasurement(self, enable=True):
        if self.Measurement is not None:
            if self.MeasuremnetRuning == enable:
                self.log.info("Measurement is in correct state.")
            else:
                mEvent = comclient.DispatchWithEvents(self.Measurement,
                                                      MeasurementEvents)
                if enable:
                    self.Measurement.Start()
                else:
                    self.Measurement.Stop()
                rc = win32event.WaitForSingleObject(mEvent.measuermenStarted,
                                                    60000)
                self.MeasuremnetRuning = mEvent.measurementIsRunning
                if rc != win32event.WAIT_OBJECT_0:
                    self.log.error("Measurement %s time out." %
                                   ("START" if enable else "STOP"))
                else:
                    if enable:
                        self.log.info("Measurement is started, waiting 5 "
                                      "seconds to have active bus stable "
                                      "state...")
                        time.sleep(5)
        else:
            self.log.error("Measurement object not initialized. Check whether "
                           "the CNOoe is runnig.")

    def SaveCANoeCfg(self):
        self.CANoe.Configuration.Save()

    def DeactivateAllNodes(self):
        self.WriteMessage("DeactivateAllNodes")
        try:
            for i in range(
                    self.CANoe.Configuration.SimulationSetup.Buses.Count):
                BusItemArray = self.CANoe.Configuration.SimulationSetup.Buses
                BusItem = BusItemArray(i + 1)
                BusVB2Item = comclient.CastTo(BusItem, "IBusVB2")
                BusVB2Item.Active = False
        except Exception as e:
            self.log.error(str(e))
            sys.exit("Could not deactivate networks. Exiting!")

    def TurnOnCANNetwork(self, networkName):
        # CAN network can be always turned on
        self.CANoe.UI.Write.Output("TurnOnCANNetwork")
        try:
            BusItemArray = self.CANoe.Configuration.SimulationSetup.Buses
            BusItem = BusItemArray(networkName)
            BusVB2Item = comclient.CastTo(BusItem, "IBusVB2")
            BusVB2Item.Active = True
        except Exception as e:
            self.log.error(str(e))
            sys.exit("Could not activate 'CAN test network'. Exiting!")

    def TurnOffAllNodes(self):
        # turn all nodes off
        self.WriteMessage("TurnOffAllNodes(self)")
        for i in range(self.CANoe.Configuration.SimulationSetup.Nodes.Count):
            Node = self.CANoe.Configuration.SimulationSetup.Nodes.Item(i + 1)
            Node.Active = False

    def TurnOffAllBusNodes(self, busName):
        BusItemArray = self.CANoe.Configuration.SimulationSetup.Buses
        BusItem = BusItemArray(busName)
        BusVB2Item = comclient.CastTo(BusItem, "IBusVB2")
        self.WriteMessage("TurnOffAllBusNodes(self)")
        for i in range(BusVB2Item.Nodes.Count):
            Node = BusVB2Item.Nodes.Item(i + 1)
            self.log.info("Turn off node name: %s" % Node.Name)
            Node.Active = False

    def TurnOffPartnerNodes(self, busName, nodes):
        BusItemArray = self.CANoe.Configuration.SimulationSetup.Buses
        BusItem = BusItemArray(busName)
        BusVB2Item = comclient.CastTo(BusItem, "IBusVB2")
        self.WriteMessage("TurnOffPartnerNodes(self)")
        for nodeName in nodes:
            for i in range(BusVB2Item.Nodes.Count):
                Node = BusVB2Item.Nodes.Item(i + 1)
                if nodeName == Node.Name:
                    self.log.info("Turn off node name: %s" % Node.Name)
                    Node.Active = False

    def TurnOnPartnerNodes(self, busName, nodes):
        BusItemArray = self.CANoe.Configuration.SimulationSetup.Buses
        BusItem = BusItemArray(busName)
        BusVB2Item = comclient.CastTo(BusItem, "IBusVB2")
        self.CANoe.UI.Write.Output("TurnOnPartnerNodes(self)")
        for nodeName in nodes:
            for i in range(BusVB2Item.Nodes.Count):
                Node = BusVB2Item.Nodes.Item(i + 1)
                if nodeName == Node.Name:
                    self.log.info("Turn on node name: %s" % Node.Name)
                    Node.Active = True

    def TurnOffActiveNodes(self):
        # turn all nodes off
        self.WriteMessage("TurnOffAllNodes(self)")
        for i in range(self.CANoe.Configuration.SimulationSetup.Nodes.Count):
            Node = self.CANoe.Configuration.SimulationSetup.Nodes.Item(i + 1)
            if (Node.Active is True):
                Node.Active = False
                self.WriteMessage("TurnOffActiveNodes(self)")

    # activating single test node
    def ActivateSingleNode(self, TCname):
        nodeFound = 0
        ProblematicTests = ""
        self.WriteMessage("ActivateSingleNode")
        for j in range(self.CANoe.Configuration.SimulationSetup.Nodes.Count):
            Name =\
                self.CANoe.Configuration.SimulationSetup.Nodes.Item(j+1).Name
            # if Name == testCase.TCname:
            if Name == TCname:
                nodeFound = 1
                Node = self.CANoe.Configuration.SimulationSetup.Nodes.Item(j +
                                                                           1)
                Node.Active = True
                break
        if nodeFound == 0:
            ProblematicTests = ProblematicTests + TCname + ", "
        time.sleep(5)

    def ActivateSingleTest(
            self,
            TCname,
            WaitForFinish=True,
            TimeOut=(120 * 60),  # default time-out 2h
            testEnvName="APHFlashReboot",
            restart_measurement_if_time_out=True):
        """
        This method activates single TestModule from selected test environment.
        If test environment is no passed as argument default test envronment
        name is used. Default time-ot is 2h because several test modules in
        default test environment can run for a while.
        TCname = name of the test module.
        WaitForFinish = True if we want to wait for test to finish
        TimeOut - time-out in seconds
        testEnvName - name of the test environment which holds test case module
        """
        nodeFound = 0
        verdict = -1  # timeout
        self.ReportPath = ""
        ProblematicTests = ""
        tstCnt = 0
        self.log.info("Running test %s.%s" % (testEnvName, TCname))
        canoeCfg = self.CANoe.Configuration
        tstEnvCnt = canoeCfg.TestSetup.TestEnvironments.Count + 1
        for i in range(1, tstEnvCnt):
            tstEnv = canoeCfg.TestSetup.TestEnvironments.Item(i)
            tEnvName = tstEnv.Name.encode("ascii")
            if tEnvName == testEnvName:
                tstCnt = tstEnv.Items.Count
                break
        else:
            self.log.error(
                "CANoe test environment '%s' not found!" % testEnvName)

        for j in range(tstCnt):
            selTest = tstEnv.Items(j + 1)
            Name = selTest.Name.encode("ascii")
            if Name == TCname:
                nodeFound = 1
                SelectedTest = comclient.CastTo(selTest, "ITSTestModule")
                self.ReportGenerated = False
                self.ReportPath = SelectedTest.Report.FullName
                if WaitForFinish:
                    tEvents = comclient.DispatchWithEvents(
                        SelectedTest, CANoeTestConfigurationEvents)

                    SelectedTest.Start()
                    # waiting for test to finish in CANoe
                    rc = win32event.WaitForSingleObject(
                        tEvents.testDone, TimeOut * 1000)
                    if rc != win32event.WAIT_OBJECT_0:
                        self.log.error("TEST TIME OUT!!!")
                        if restart_measurement_if_time_out:
                            # recovery procedure. if not executed the state of
                            # the canot test is unknown it could still run
                            self.log.warning("Restarting measurement to "
                                             "stop test!")
                            self.StartMeasurement(False)
                            self.StartMeasurement(True)

                    if SelectedTest.Report.Enabled:
                        # wait for report generation 5 sec should be enough
                        rc = win32event.WaitForSingleObject(
                            tEvents.reportDone, 5000)
                        if rc != win32event.WAIT_OBJECT_0:
                            self.log.error("REPORT NOT GENERATED!!!")
                    else:
                        if _CANOE_API_DEBUG_:
                            self.log.info("Test report not enabled")

                    self.ReportGenerated = tEvents.CTRInfo["success"]
                    if self.ReportGenerated:
                        tcReport, unused_ext = splitext(
                            tEvents.CTRInfo["reportPath"])
                        self.ReportPath = ("%s.xml" % tcReport)
                    if _CANOE_API_DEBUG_:
                        self.log.info("Test report --> %s" % self.ReportPath)

                    if (tEvents.finishReason == 0):
                        verdict = SelectedTest.Verdict
                        if verdict == 1:
                            self.log.info("Test passed!")
                        elif verdict == 2:
                            self.log.info("Test failed!")
                        else:
                            self.log.info("End of test! "
                                          "Verdict not available!")
                    elif (tEvents.finishReason == 1):
                        self.log.error("The test module was stopped by "
                                       "the user.")
                    elif (tEvents.finishReason == 2):
                        self.log.error("The test module was stopped by "
                                       "measurement stop.")
                    elif (tEvents.finishReason == -1):
                        self.log.error("CANoe test time out error!")
                else:
                    SelectedTest.Start()
                break

        if nodeFound == 0:
            self.log.error("%s.%s test not found!" % (testEnvName, TCname))
            ProblematicTests = ProblematicTests + TCname + ", "
        return verdict

    def GetLastTestReportName(self):
        return self.ReportPath

    def ActivateTestConfigTest(self, WaitForFinish=True, TimeOut=120 * 60):
        """
        TCname = name of the test
        WaitForFinish = True if we want to wait for test to finish
        Number of seconds for waiting = TimeOut
        """
        # self.CANoe.UI.Write.Output("ActivateSingleTest " + TCname)
        TestConfiguration = self.CANoe.Configuration.TestConfigurations.Item(1)

        if WaitForFinish:
            tEvents = comclient.DispatchWithEvents(
                TestConfiguration, CANoeTestConfigurationEvents)

            self.log.info("TestConfiguration Test START/PLAY")
            # starting CANoe tests made in vTestStudio...
            TestConfiguration.Start()
            # waiting for test to finish in CANoe
            rc = win32event.WaitForSingleObject(tEvents.testDone,
                                                TimeOut * 1000)
            if rc != win32event.WAIT_OBJECT_0:
                self.log.error("TEST TIME OUT!!!")
            # wait for report generation 5 sec should be enough
            rc = win32event.WaitForSingleObject(tEvents.reportDone, 5000)
            if rc != win32event.WAIT_OBJECT_0:
                self.log.error("REPORT NOT GENERATED!!!")

            self.ReportGenerated = tEvents.CTRInfo["success"]
            if self.ReportGenerated:
                tcReport, unused_ext = splitext(tEvents.CTRInfo["reportPath"])
                self.ReportPath = ("%s.xml" % tcReport)
            if _CANOE_API_DEBUG_:
                self.log.info("Test report --> %s" % self.ReportPath)
        else:
            self.log.info("TestConfiguration Test START/PLAY")
            # starting CANoe tests made in vTestStudio...
            TestConfiguration.Start()

    def SaveConfiguration(self):
        self.Config = self.CANoe.Configuration
        if (self.Config.Saved is False):
            self.Config.Save()
            self.WriteMessage("SaveConfiguration")

    def InitMeasurementControls(self):
        self.Measurement = self.CANoe.Measurement

    def Quit(self):
        if self.CANoe is not None:
            lc_config = self.CANoe.Configuration
            self.log.info("Closing CANoe configuration %s" % lc_config.Name)
            self.StartMeasurement(False)
            time.sleep(1)
            lc_config.Modified = False
            self.CANoe.Quit()
        else:
            self.log.error("No CANoe application instance!")
        self.CANoe = None
        self.mWrite = None
        self.Config = None
        self.Measurement = None
        self.MeasuremnetRuning = False

    def _SwitchNetwork(self, net_name, active):
        result = True
        try:
            BusItemArray = self.CANoe.Configuration.SimulationSetup.Buses
            BusItem = BusItemArray(net_name)
            BusVB2Item = comclient.CastTo(BusItem, "IBusVB2")
            BusVB2Item.Active = active
        except Exception as e:
            result = False
            self.log.error(str(e))
            self.log.error("Could not activate %s network'." % net_name)
        return result

    # activating whole FR network
    def TurnOnFlexRayNetwork(self):
        self._SwitchNetwork('MLBevo_Fx_Cluster', True)

    # deactivating whole FR network
    def TurnOffFlexRayNetwork(self):
        self._SwitchNetwork('MLBevo_Fx_Cluster', False)

    # activating whole LIN network
    def TurnOnLINNetwork(self):
        try:
            BusItemArray = self.CANoe.Configuration.SimulationSetup.Buses
            BusItem = BusItemArray('LIN test network')
            BusVB2Item = comclient.CastTo(BusItem, "IBusVB2")
            BusVB2Item.Active = True
        except Exception as e:
            self.log.error(str(e))
            sys.exit("Could not activate 'LIN test network'. Exiting!")

    # deactivating whole LIN network
    def TurnOffLINNetwork(self):
        try:
            BusItemArray = self.CANoe.Configuration.SimulationSetup.Buses
            BusItem = BusItemArray('LIN test network')
            BusVB2Item = comclient.CastTo(BusItem, "IBusVB2")
            BusVB2Item.Active = False
        except Exception as e:
            self.log.error(str(e))
            sys.exit("Could not deactivate 'LIN test network'. Exiting!")

    def GetSysvarObj(self, varName, namespace=None):

        objNamespace = None

        for item in self.CANoe.System.Namespaces:
            if _CANOE_API_DEBUG_:
                self.log.info("Name of namespaces is: %s" % item.Name)
            if (item.Name == namespace):
                if _CANOE_API_DEBUG_:
                    self.log.info("Namespace name is: %s" % item.Name)
                objNamespace = item
                break
        if objNamespace is not None:
            try:
                for idxVar in range(1, objNamespace.Variables.Count + 1):
                    objSysvar = objNamespace.Variables.Item(idxVar)
                    if objSysvar.Name == varName:
                        if _CANOE_API_DEBUG_:
                            self.log.info(
                                "Variable name is: %s" % objSysvar.Name)
                        return objSysvar
            except Exception as ex:
                self.log.error("Error in CANoegetSysvarObj")

        return None

    # end def GetSysvarObj

    def GetValueOfSysvar(self, varName, namespace=None):

        objSysvar = self.GetSysvarObj(varName, namespace)

        if objSysvar is None:
            return False

        return objSysvar.Value

    # end def GetValueOfSysvar

    def SetValueOfSysvar(self, value, varName, namespace=None):

        retVal = False
        objSysvar = self.GetSysvarObj(varName, namespace)

        if objSysvar is None:
            return retVal

        try:
            objSysvar.Value = value
            retVal = True
        except Exception:
            self.log.info("sysvar: {}::{} could not write "
                          "value {}".format(namespace, varName, value))
        return retVal

    # end def SetValueOfSysvar


def main():
    from os.path import (abspath)
    # test sample for init SIT and start of test on VS1
    canAPI = CANoeAPI()
    print("Opening CANoe")
    canAPI.StartCANoe("Not used")
    cfgPath = join("..", "..", "CANoeCommon", "COM_E2E",
                   "COM_E2E_AllNodes_HILS.cfg")
    print("Opening CANoe configuration...")
    canAPI.LoadCFG(abspath(cfgPath))
    print("Done\n")
    print("Measurement starting ...")
    canAPI.StartMeasurement(True)
    print("Done\n")
    canAPI.ActivateSingleTest("PowerON", True, 50, "APHFlashReboot")
    print("Wrogn test call...")
    canAPI.ActivateSingleTest("KL30_ON", testEnvName="COM_E2E_TE")
    canAPI.ActivateSingleTest("Dummy")
    print("Done\n")
    canAPI.ActivateSingleTest("Coding", True, 60)
    print("Report path is '%s'" % canAPI.GetLastTestReportName())
    time.sleep(15)
    canAPI.ActivateSingleTest("PowerOFF", True, 50)
    time.sleep(10)
    canAPI.ActivateSingleTest("PowerON", True, 50)

    # canAPI.ActivateSingleTest("FaultMemory", True, 120)
    print("\nStopping measurement")
    canAPI.StartMeasurement(False)


if __name__ == "__main__":
    main()
