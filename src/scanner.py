# import redpitaya_scpi as scpi
from numpy import linspace

from PySide6.QtCore import QObject, Signal
import time

from awg_ctl import set_awg

import pyvisa as visa
from snAPI.Main import *

class ScanWorker(QObject):
    QObject
    finished_scan = Signal(dict)

    def __init__(self):
        super().__init__()
        self._stop = False

        # Set up VISA instrument object
        rm = visa.ResourceManager('@py')
        self.awg = rm.open_resource('TCPIP0::141.20.45.148::inst0::INSTR')
        self.awg.timeout = 10000 #float('+inf') #(in ms)
        print('Connected to ', self.awg.query('*idn?'))

        # Init Multiharp
        self.sn = snAPI()
        self.sn.getDevice()

        self.sn.initDevice(MeasMode.Histogram)
        self.sn.loadIniConfig("./MH.ini")

    def __del__(self):
        self.awg.close()
        self.sn.closeDevice()

    def mh_get_data(self):
        self.sn.histogram.measure(acqTime=1000, waitFinished=True, savePTU=True)
        data, bins = self.sn.histogram.getData()

        data = data[1]#[:6000]
        bins = bins#[:6000]
        return data, bins

    def do_single_scan(self, write_width, signal_width, offset):
        set_awg(self.awg, write_width, signal_width, offset)
        data, bins = self.mh_get_data()

        result = {
            "write_width": write_width,
            "signal_width": signal_width,
            "offset": offset,
            "data": data,
            "bins": bins
        }

        self.finished_scan.emit(result)

    def do_repeated_scan(self, params):
        self._stop = False
        for write_width in params["write_width"]:
            for signal_width in params["signal_width"]:
                for offset in params["offset"]:
                    if self._stop:
                        return
                    self.do_single_scan(write_width, signal_width, offset)
