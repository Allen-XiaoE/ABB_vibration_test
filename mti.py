import xsensdeviceapi as xda
from threading import Lock
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
import os,time

class XdaCallback(xda.XsCallback):
    def __init__(self):
        xda.XsCallback.__init__(self)
        self.m_progress = 0
        self.m_lock = Lock()

    def progress(self):
        return self.m_progress

    def onProgressUpdated(self, dev, current, total, identifier):
        self.m_lock.acquire()
        self.m_progress = current
        self.m_lock.release()

class Receiver(QThread):
    update_status = pyqtSignal(str)
    start_controller = pyqtSignal()
    parser = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self,series='IRB1100-00001'):
        super(Receiver,self).__init__()
        self.cycle = True
        self.series = series

    def run(self):

        self.control = xda.XsControl_construct()
        self.mtPort = xda.XsPortInfo()
        try:
            portInfoArray = xda.XsScanner_scanPorts()

            for i in range(portInfoArray.size()):
                if (
                    portInfoArray[i].deviceId().isMti()
                    or portInfoArray[i].deviceId().isMtig()
                ):
                    self.mtPort = portInfoArray[i]
                    break        
            while self.mtPort.empty():
                self.error.emit("没有发现sensor,请检查连接!")
                while self.cycle:
                    self.msleep(100)
                self.reset_cycle()
                portInfoArray = xda.XsScanner_scanPorts()

                for i in range(portInfoArray.size()):
                    if (
                        portInfoArray[i].deviceId().isMti()
                        or portInfoArray[i].deviceId().isMtig()
                    ):
                        self.mtPort = portInfoArray[i]
                        break
            did = self.mtPort.deviceId()
            if not self.control.openPort(self.mtPort.portName(), self.mtPort.baudrate()):
                raise RuntimeError("Could not open port. Aborting.")
            self.device = self.control.device(did)
            if self.device == 0:
                raise RuntimeError('Cannot create device! Aborting.')
            self.callback = XdaCallback()
            self.device.addCallbackHandler(self.callback)
            if not self.device.gotoConfig():
                raise RuntimeError(
                    "Could not put device into configuration mode. Aborting."
                )

            configArray = xda.XsOutputConfigurationArray()
            configArray.push_back(xda.XsOutputConfiguration(xda.XDI_PacketCounter, 0))
            configArray.push_back(xda.XsOutputConfiguration(xda.XDI_SampleTimeFine, 0))
            configArray.push_back(xda.XsOutputConfiguration(xda.XDI_Acceleration, 400))
            configArray.push_back(xda.XsOutputConfiguration(xda.XDI_FreeAcceleration, 400))
            configArray.push_back(xda.XsOutputConfiguration(xda.XDI_MagneticField, 400))
            configArray.push_back(xda.XsOutputConfiguration(xda.XDI_Quaternion, 400))


            if not self.device.setOutputConfiguration(configArray):
                raise RuntimeError("Could not configure the device. Aborting.")
            
            self.update_status.emit("Sensor热机中,该过程需要1分钟时间!")
            self.sleep(60)

            logFileName = os.path.join("DATA", self.series + ".mtb")
            if self.device.createLogFile(logFileName) != xda.XRV_OK:
                raise RuntimeError("Failed to create a log file. Aborting.")

            if not self.device.gotoMeasurement():
                raise RuntimeError("Could not put device into measurement mode. Aborting.")
            self.update_status.emit("创建数据记录文件: %s.mtb" % self.series)

            if not self.device.startRecording():
                raise RuntimeError("Failed to start recording. Aborting.")
            else:
                self.update_status.emit('开始数据记录!')
            self.start_controller.emit()

            while self.cycle:
                self.msleep(100)
            self.reset_cycle()

            if not self.device.closeLogFile():
                raise RuntimeError("Failed to close log file. Aborting.")
            else:
                self.update_status.emit('记录完成!')
            # print("Removing callback handler...")
            self.device.removeCallbackHandler(self.callback)

            # print("Closing port...")
            self.control.closePort(self.mtPort.portName())

            # print("Closing XsControl object...")
            self.control.close()

        except RuntimeError as error:
            self.update_status.emit(repr(error))

        except Exception as e:
            self.update_status.emit("An unknown fatal error has occured. Aborting.")
            self.update_status.emit(repr(e))

        else:
            self.update_status.emit("Sensor成功退出")
        
        self.parser.emit()

    def reset_cycle(self):
        self.cycle =True
    
    @pyqtSlot()
    def stop_cycle(self):
        self.cycle = False
    
    def stop_sensor(self):
        self.device.removeCallbackHandler(self.callback)

        # print("Closing port...")
        self.control.closePort(self.mtPort.portName())

        # print("Closing XsControl object...")
        self.control.close()

def parser(filename):
    print("Creating XsControl object...")
    control = xda.XsControl_construct()
    assert control != 0

    xdaVersion = xda.XsVersion()
    xda.xdaVersion(xdaVersion)
    print("Using XDA version %s" % xdaVersion.toXsString())

    try:
        print("Opening log file...")
        logfileName = os.path.join("DATA", f"{filename}.mtb")
        if not control.openLogFile(logfileName):
            raise RuntimeError("Failed to open log file. Aborting.")
        print("Opened log file: %s" % logfileName)

        deviceIdArray = control.mainDeviceIds()
        for i in range(deviceIdArray.size()):
            if deviceIdArray[i].isMti() or deviceIdArray[i].isMtig():
                mtDevice = deviceIdArray[i]
                break

        if not mtDevice:
            raise RuntimeError("No MTi device found. Aborting.")

        # Get the device object
        device = control.device(mtDevice)
        assert device != 0

        print(
            "Device: %s, with ID: %s found in file"
            % (device.productCode(), device.deviceId().toXsString())
        )

        callback = XdaCallback()
        device.addCallbackHandler(callback)

        device.setOptions(xda.XSO_RetainBufferedData, xda.XSO_None)

        print("Loading the file...")
        device.loadLogFile()
        while callback.progress() != 100:
            time.sleep(0)
        print("File is fully loaded")

        # Get total number of samples
        packetCount = device.getDataPacketCount()

        # Export the data
        print("Exporting the data...")
        s = "PacketCounter,SampleTimeFine,FreeAcc_E,FreeAcc_N,FreeAcc_U\n"
        index = 0
        while index < packetCount:
            # Retrieve a packet
            packet = device.getDataPacketByIndex(index)
            counter = packet.packetCounter()
            sampleTime = packet.sampleTimeFine()
            acc = packet.freeAcceleration()
            if len(acc) != 0:
                s += (
                    "%s" % counter
                    + ",%s" % sampleTime
                    + ",%.5f" % acc[0]
                    + ",%.5f" % acc[1]
                    + ",%.5f" % acc[2]
                )
                s += "\n"
            index += 1

        exportFileName = f"DATA//{filename}.txt"
        with open(exportFileName, "w") as outfile:
            outfile.write(s)
        print("File is exported to: %s" % exportFileName)

        print("Removing callback handler...")
        device.removeCallbackHandler(callback)

        print("Closing XsControl object...")
        control.close()

    except RuntimeError as error:
        print(error)
    except:
        print("An unknown fatal error has occured. Aborting.")
    else:
        print("Successful exit.")