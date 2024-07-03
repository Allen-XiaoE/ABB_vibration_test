import os, sys
import xsensdeviceapi as xda
import time
from threading import Lock


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


def receiver(fname, pill2kill):
    print("Creating XsControl object...")
    control = xda.XsControl_construct()
    assert control != 0

    xdaVersion = xda.XsVersion()
    xda.xdaVersion(xdaVersion)
    print("Using XDA version %s" % xdaVersion.toXsString())

    try:
        print("Scanning for devices...")
        portInfoArray = xda.XsScanner_scanPorts()

        # Find an MTi device
        mtPort = xda.XsPortInfo()
        for i in range(portInfoArray.size()):
            if (
                portInfoArray[i].deviceId().isMti()
                or portInfoArray[i].deviceId().isMtig()
            ):
                mtPort = portInfoArray[i]
                break

        if mtPort.empty():
            raise RuntimeError("No MTi device found. Aborting.")

        did = mtPort.deviceId()
        print("Found a device with:")
        print(" Device ID: %s" % did.toXsString())
        print(" Port name: %s" % mtPort.portName())

        print("Opening port...")
        if not control.openPort(mtPort.portName(), mtPort.baudrate()):
            raise RuntimeError("Could not open port. Aborting.")

        # Get the device object
        device = control.device(did)
        assert device != 0

        print(
            "Device: %s, with ID: %s opened."
            % (device.productCode(), device.deviceId().toXsString())
        )

        # Create and attach callback handler to device
        callback = XdaCallback()
        device.addCallbackHandler(callback)

        # Put the device into configuration mode before configuring the device
        print("Putting device into configuration mode...")
        if not device.gotoConfig():
            raise RuntimeError(
                "Could not put device into configuration mode. Aborting."
            )

        print("Configuring the device...")
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

        print("Creating a log file...")
        logFileName = os.path.join("DATA", fname + ".mtb")
        if device.createLogFile(logFileName) != xda.XRV_OK:
            raise RuntimeError("Failed to create a log file. Aborting.")
        else:
            print("Created a log file: %s" % fname)

        print("Putting device into measurement mode...")
        if not device.gotoMeasurement():
            raise RuntimeError("Could not put device into measurement mode. Aborting.")

        print("Starting recording...")
        if not device.startRecording():
            raise RuntimeError("Failed to start recording. Aborting.")

        print("Main loop. Recording data for 10 seconds.")

        while pill2kill.empty():
            time.sleep(0.1)

        print("\nStopping recording...")
        if not device.stopRecording():
            raise RuntimeError("Failed to stop recording. Aborting.")

        print("Closing log file...")
        if not device.closeLogFile():
            raise RuntimeError("Failed to close log file. Aborting.")

        print("Removing callback handler...")
        device.removeCallbackHandler(callback)

        print("Closing port...")
        control.closePort(mtPort.portName())

        print("Closing XsControl object...")
        control.close()

    except RuntimeError as error:
        print(error)
        sys.exit(1)
    except:
        print("An unknown fatal error has occured. Aborting.")
        sys.exit(1)
    else:
        print("Successful exit.")
