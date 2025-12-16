from snAPI.Main import *

class MhCtl:
    def __init__(self):
        # Init Multiharp
        self.sn = snAPI()
        self.sn.getDevice()

        self.sn.initDevice(MeasMode.Histogram)
        self.sn.loadIniConfig("./MH.ini")

    def __del__(self):
        self.sn.closeDevice()

    def get_data(self):
        self.sn.histogram.measure(acqTime=1000, waitFinished=True, savePTU=True)
        data, bins = self.sn.histogram.getData()

        data = data[1]
        bins = bins
        return data, bins
