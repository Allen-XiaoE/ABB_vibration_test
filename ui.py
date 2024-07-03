import sys, time,os
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from window import Ui_MainWindow
from mti import parser, receiver, XdaCallback
import xsensdeviceapi as xda
from rws import RWS
from queue import Queue
from dataprocess import calculation


class Vibration_Test_UI(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(Vibration_Test_UI, self).__init__()
        self.setupUi(self)
        self.rws = RWS()
        self.q = Queue()
        self.viration_test_button.clicked.connect(self.run)
        self.get_serial_number_button.clicked.connect(self.get_serial)
        self.stop_button.clicked.connect(self.stop)
        self.gotosyncpose_button.clicked.connect(self.gohome)
        self.motor_on_button.clicked.connect(self.motor_on)

    def update_status(self, text):
        self.status_text.append(text)

    def clear_status(self):
        self.status_text.clear()

    def get_serial(self):
        if self.rws.baseurl == "https://192.168.125.1":
            serial = self.rws.GETserial()
        else:
            serial = "1100-000001"
        self.serial_number.setText(serial)

    def gohome(self):
        self.gohome_run = GohomeThread(self.rws, self.q)
        self.gohome_run.update_status.connect(self.update_status)
        self.gohome_run.start()

    def motor_on(self):
        self.rws.motor("motoron")
        self.update_status("motor on!")

    def stop(self):
        self.rws.stopexcuseRapid()
        self.update_status("Stop rapid!")
    
    def cal(self,series):
        self.update_status('开始数据解析')
        parser(series)
        self.update_status('数据解析完成')
        value = calculation(series)
        self.update_status(f'Result:{value}')

    def run(self):
        self.clear_status()
        serial = self.serial_number.text()

        self.receives = Recive_Data(serial=serial,q=self.q)
        self.receives.update_status.connect(self.update_status)
        self.receives.cal.connect(self.cal)
        self.receives.start()
        # self.q.put('startRecording')


        self.work = WorkerThread(self.rws, serial, self.q)
        self.work.update_status.connect(self.update_status)
        self.work.start()


class WorkerThread(QThread):

    update_status = pyqtSignal(str)

    def __init__(self, rws: RWS, serial: str, q: Queue):
        super().__init__()
        self.rws = rws
        self.serial = serial
        self.queue = q

    def run(self):

        while self.queue.empty():
            time.sleep(5)
        
        if self.queue.get() != 'start':
            self.update_status.emit('程序停止')
            return
        
        while self.rws.connect_verification() != "OK":
            self.update_status.emit("请检查控制柜连接！")

        self.update_status.emit(f"Serial No.: {self.serial}")

        while self.rws.GETopmode() != "AUTO":
            self.update_status.emit("请将Auto！")

        self.update_status.emit("电机上电")

        if self.rws.motor("motoron") != "OK":
            self.update_status.emit(
                "电机上电失败,检查控制柜连接状态以及控制柜模式是否为自动！"
            )

        _con = open(r"RAPID\IRB1100_Vibration_Test_v0.1.2_new_CFG_0528.modx", "r")
        content = _con.read()
        if self.rws.uploadfile("temp/vibration.modx", content=content) != "OK":
            self.update_status.emit("上传失败")

        if self.rws.loadmodule("temp/vibration.modx") != "OK":
            self.update_status.emit("载入失败")

        if self.rws.pptoRoutine("VibrationTest", "IRB1100_Vibration_Test") != "OK":
            self.update_status.emit("PP失败")
        if self.rws.excuseRapid() != "OK":
            self.update_status.emit("rapid执行失败")

        while self.rws.GETrapidstatus() != "stopped":
            self.update_status.emit("程序VibrationTest运行中...")
            time.sleep(5)

        if self.rws.unloadmodule("IRB1100_Vibration_Test") != "OK":
            self.update_status.emit("unload失败")

        if self.rws.deletefile("temp/vibration.modx") != "OK":
            self.update_status.emit("删除失败")
        self.queue.put("complete")

        self.update_status.emit("完成！")


class GohomeThread(QThread):
    update_status = pyqtSignal(str)

    def __init__(self, rws):
        super().__init__()
        self.rws = rws

    def run(self):
        while self.rws.connect_verification() != "OK":
            self.update_status.emit("请检查控制柜连接！")

        while self.rws.GETopmode() != "AUTO":
            self.update_status.emit("请将Auto！")

        self.update_status.emit("电机上电")

        if self.rws.motor("motoron") != "OK":
            self.update_status.emit(
                "电机上电失败,检查控制柜连接状态以及控制柜模式是否为自动！"
            )
        self.rws = RWS()

        _con = open(r"RAPID\IRB1100_Vibration_Test_v0.1.2_new_CFG_0528.modx", "r")
        content = _con.read()
        if self.rws.uploadfile("temp/vibration.modx", content=content) != "OK":
            self.update_status.emit("上传失败")

        if self.rws.loadmodule("temp/vibration.modx") != "OK":
            self.update_status.emit("载入失败")

        if self.rws.pptoRoutine("GotoSyncPos", "IRB1100_Vibration_Test") != "OK":
            self.update_status.emit("PP失败")

        if self.rws.excuseRapid() != "OK":
            self.update_status.emit("rapid执行失败")

        while self.rws.GETrapidstatus() != "stopped":
            self.update_status.emit("程序GotoSyncPos运行中...")
            time.sleep(5)

        if self.rws.unloadmodule("IRB1100_Vibration_Test") != "OK":
            self.update_status.emit("unload失败")

        if self.rws.deletefile("temp/vibration.modx") != "OK":
            self.update_status.emit("删除失败")

        self.update_status.emit("完成！")


class Recive_Data(QThread):
    update_status = pyqtSignal(str)
    cal = pyqtSignal(str)

    def __init__(self, q: Queue, serial: str) -> None:
        super().__init__()
        self.q = q
        self.series = serial

    def run(self):
        control = xda.XsControl_construct()
        mtPort = xda.XsPortInfo()
        try:
            portInfoArray = xda.XsScanner_scanPorts()

            for i in range(portInfoArray.size()):
                if (
                    portInfoArray[i].deviceId().isMti()
                    or portInfoArray[i].deviceId().isMtig()
                ):
                    mtPort = portInfoArray[i]
                    break
            while mtPort.empty():
                self.update_status.emit("没有发现sensor,请检查连接!")
                time.sleep(5)
            did = mtPort.deviceId()
            if not control.openPort(mtPort.portName(), mtPort.baudrate()):
                raise RuntimeError("Could not open port. Aborting.")
            device = control.device(did)
            if device == 0:
                raise RuntimeError('Cannot create device! Aborting.')
            callback = XdaCallback()
            device.addCallbackHandler(callback)
            if not device.gotoConfig():
                raise RuntimeError(
                    "Could not put device into configuration mode. Aborting."
                )

            configArray = xda.XsOutputConfigurationArray()
            configArray.push_back(xda.XsOutputConfiguration(xda.XDI_PacketCounter, 0))
            configArray.push_back(xda.XsOutputConfiguration(xda.XDI_SampleTimeFine, 0))

            if device.deviceId().isImu():
                configArray.push_back(xda.XsOutputConfiguration(xda.XDI_Acceleration, 400))
                configArray.push_back(xda.XsOutputConfiguration(xda.XDI_RateOfTurn, 400))
                configArray.push_back(xda.XsOutputConfiguration(xda.XDI_MagneticField, 400))
            elif device.deviceId().isVru() or device.deviceId().isAhrs():
                configArray.push_back(xda.XsOutputConfiguration(xda.XDI_Acceleration, 400))
                configArray.push_back(
                    xda.XsOutputConfiguration(xda.XDI_FreeAcceleration, 400)
                )
                configArray.push_back(xda.XsOutputConfiguration(xda.XDI_MagneticField, 400))
                configArray.push_back(xda.XsOutputConfiguration(xda.XDI_Quaternion, 400))
            elif device.deviceId().isGnss():
                configArray.push_back(xda.XsOutputConfiguration(xda.XDI_Quaternion, 400))
                configArray.push_back(xda.XsOutputConfiguration(xda.XDI_LatLon, 400))
                configArray.push_back(
                    xda.XsOutputConfiguration(xda.XDI_AltitudeEllipsoid, 400)
                )
                configArray.push_back(xda.XsOutputConfiguration(xda.XDI_VelocityXYZ, 400))
            else:
                raise RuntimeError("Unknown device while configuring. Aborting.")

            if not device.setOutputConfiguration(configArray):
                raise RuntimeError("Could not configure the device. Aborting.")
            
            logFileName = os.path.join("DATA", self.series + ".mtb")
            if device.createLogFile(logFileName) != xda.XRV_OK:
                raise RuntimeError("Failed to create a log file. Aborting.")
            else:
                self.update_status.emit("Created a log file: %s.mtb" % self.series)

            if not device.gotoMeasurement():
                raise RuntimeError("Could not put device into measurement mode. Aborting.")

            self.update_status.emit("Sensor需要进行热机中,大概需要2分钟!")
            time.sleep(120)
            self.q.put('Start')
            if self.q.get() == 'Start':
                if not device.startRecording():
                    raise RuntimeError("Failed to start recording. Aborting.")
                self.update_status.emit('开始数据记录!')
            else:
                if not device.closeLogFile():
                    raise RuntimeError("Failed to close log file. Aborting.")
                device.removeCallbackHandler(callback)
                control.closePort(mtPort.portName())
                control.close()
                return
            
            while self.q.empty():
                time.sleep(1)
            self.update_status.emit('记录完成!')
            if not device.closeLogFile():
                raise RuntimeError("Failed to close log file. Aborting.")

            print("Removing callback handler...")
            device.removeCallbackHandler(callback)

            print("Closing port...")
            control.closePort(mtPort.portName())

            print("Closing XsControl object...")
            control.close()

        except RuntimeError as error:
            self.update_status.emit(repr(error))

        except:
            self.update_status.emit("An unknown fatal error has occured. Aborting.")
        else:
            self.update_status.emit("Successful exit.")
        self.cal.emit(self.series)
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Vibration_Test_UI()
    window.show()
    sys.exit(app.exec_())
