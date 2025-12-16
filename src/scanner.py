from PySide6.QtCore import QObject, Signal
import time

from awg_ctl import AwgCtl
from mh_ctl import MhCtl


class ScanWorker(QObject):
    QObject
    finished_qm_scan = Signal(dict)
    finished_ref_scan = Signal(dict)

    def __init__(self):
        super().__init__()
        self._stop = False

        self.awg_ctl = AwgCtl()
        self.mh_ctl = MhCtl()

    def __del__(self):
        del(self.mh_ctl)
        del(self.awg_ctl)

    def do_reference_measurement(self, signal_width):
        self.awg_ctl.set_awg_ref(signal_width)
        time.sleep(2)
        data, bins = self.mh_ctl.get_data()

        result = {
            "signal_width": signal_width,
            "bins": bins,
            "data": data,
        }

        self.finished_ref_scan.emit(result)

    def do_single_scan(self, write_width, signal_width, offset):
        self.awg_ctl.set_awg_scan(write_width, signal_width, offset)
        time.sleep(2)
        data, bins = self.mh_ctl.get_data()

        result = {
            "write_width": write_width,
            "signal_width": signal_width,
            "offset": offset,
            "bins": bins,
            "data": data,
        }

        self.finished_scan.emit(result)

    def do_repeated_scan(self, params):
        self.do_reference_measurement(100)
        # self._stop = False
        # for signal_width in params["signal_width"]:
        #     # perform reference measurement in EIT mode for any new signal width
        #     self.do_reference_measurement(signal_width)

        #     for write_width in params["write_width"]:
        #         for offset in params["offset"]:
        #             if self._stop:
        #                 return
        #             self.do_single_scan(write_width, signal_width, offset)
