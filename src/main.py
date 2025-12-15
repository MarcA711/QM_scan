import sys
from PySide6 import QtCore, QtWidgets, QtGui, QtGraphs, QtGraphsWidgets, QtCharts
from PySide6.QtCore import QThread, Signal
import pyqtgraph as pg

import pickle
from pathlib import Path
import numpy as np

from scanner import ScanWorker

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

class MyWidget(QtWidgets.QWidget):
    start_scanning = Signal(dict)
    def __init__(self):
        super().__init__()

        self.scan_data = {}

        self.worker_thread = QThread()
        self.scan_worker = ScanWorker()
        self.scan_worker.moveToThread(self.worker_thread)
        self.worker_thread.finished.connect(self.scan_worker.deleteLater)
        self.scan_worker.finished_scan.connect(self.update_scan_data)
        self.start_scanning.connect(self.scan_worker.do_repeated_scan)
        self.worker_thread.start()

        self.model = QtGui.QStandardItemModel()
        self.model.itemChanged.connect(self.plot_data)

        self.layout = QtWidgets.QVBoxLayout(self)

        self.main_split = QtWidgets.QSplitter()
        self.layout.addWidget(self.main_split)

        self.graph: pg.GraphicsLayoutWidget = pg.GraphicsLayoutWidget()
        self.main_split.addWidget(self.graph)

        self.signal_plot: pg.PlotItem = self.graph.addPlot()
        self.signal_plot.setLabels(title="", bottom="Time [x]", left="Counts")
        self.signal_plot.showGrid(x=True, y=True)

        self.properties = QtWidgets.QWidget()
        self.main_split.addWidget(self.properties)
        self.properties_layout = QtWidgets.QVBoxLayout()
        self.properties.setLayout(self.properties_layout)

        self.data_control_box = QtWidgets.QGroupBox("Data")
        self.properties_layout.addWidget(self.data_control_box)
        self.data_control_box_layout = QtWidgets.QVBoxLayout()
        self.data_control_box.setLayout(self.data_control_box_layout)
        self.data_button_layout = QtWidgets.QHBoxLayout()
        self.data_control_box_layout.addLayout(self.data_button_layout)
        self.data_save_button = QtWidgets.QPushButton()
        self.data_button_layout.addWidget(self.data_save_button)
        self.data_save_button.setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.DocumentSave))
        self.data_save_button.clicked.connect(self.save_current_data)
        self.data_load_button = QtWidgets.QPushButton()
        self.data_button_layout.addWidget(self.data_load_button)
        self.data_load_button.setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.DocumentOpen))
        self.data_load_button.clicked.connect(self.load_data)
        self.data_del_button = QtWidgets.QPushButton()
        self.data_button_layout.addWidget(self.data_del_button)
        self.data_del_button.setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.EditDelete))
        self.data_del_button.clicked.connect(self.delete_data)
        self.data_list = QtWidgets.QListView()
        self.data_control_box_layout.addWidget(self.data_list)
        self.data_list.setModel(self.model)

        self.scan_control_box = QtWidgets.QGroupBox("Scan setting")
        self.properties_layout.addWidget(self.scan_control_box)
        self.scan_control_box_layout = QtWidgets.QVBoxLayout()
        self.scan_control_box.setLayout(self.scan_control_box_layout)

        self.scan_control_write_width_layout = QtWidgets.QHBoxLayout()
        self.scan_control_box_layout.addLayout(self.scan_control_write_width_layout)
        self.scan_control_write_width_layout.addWidget(QtWidgets.QLabel("Write width"))
        self.scan_control_write_width_min = QtWidgets.QDoubleSpinBox()
        self.scan_control_write_width_layout.addWidget(self.scan_control_write_width_min)
        self.scan_control_write_width_max = QtWidgets.QDoubleSpinBox()
        self.scan_control_write_width_layout.addWidget(self.scan_control_write_width_max)
        self.scan_control_write_width_step = QtWidgets.QSpinBox()
        self.scan_control_write_width_layout.addWidget(self.scan_control_write_width_step)

        self.scan_control_signal_width_layout = QtWidgets.QHBoxLayout()
        self.scan_control_box_layout.addLayout(self.scan_control_signal_width_layout)
        self.scan_control_signal_width_layout.addWidget(QtWidgets.QLabel("Signal width"))
        self.scan_control_signal_width_min = QtWidgets.QDoubleSpinBox()
        self.scan_control_signal_width_layout.addWidget(self.scan_control_signal_width_min)
        self.scan_control_signal_width_max = QtWidgets.QDoubleSpinBox()
        self.scan_control_signal_width_layout.addWidget(self.scan_control_signal_width_max)
        self.scan_control_signal_width_step = QtWidgets.QSpinBox()
        self.scan_control_signal_width_layout.addWidget(self.scan_control_signal_width_step)

        self.scan_control_offset_layout = QtWidgets.QHBoxLayout()
        self.scan_control_box_layout.addLayout(self.scan_control_offset_layout)
        self.scan_control_offset_layout.addWidget(QtWidgets.QLabel("Offset"))
        self.scan_control_offset_min = QtWidgets.QDoubleSpinBox()
        self.scan_control_offset_layout.addWidget(self.scan_control_offset_min)
        self.scan_control_offset_max = QtWidgets.QDoubleSpinBox()
        self.scan_control_offset_layout.addWidget(self.scan_control_offset_max)
        self.scan_control_offset_step = QtWidgets.QSpinBox()
        self.scan_control_offset_layout.addWidget(self.scan_control_offset_step)
        self.scan_control_start_button = QtWidgets.QPushButton("start")
        self.scan_control_box_layout.addWidget(self.scan_control_start_button)
        self.scan_control_start_button.clicked.connect(self.start_scan)

    def closeEvent(self, event):
        self.stop_scanning()
        self.worker_thread.quit()
        self.worker_thread.wait()
        del(self.scan_worker)
        event.accept()

    def new_item(self, text):
        item = QtGui.QStandardItem(text)
        item.setCheckState(QtCore.Qt.CheckState.Unchecked)
        item.setCheckable(True)
        item.setEditable(False)
        item.setSelectable(True)

        idx = self.model.rowCount()
        color = pg.intColor(idx)
        pixmap = QtGui.QPixmap(100, 100)
        pixmap.fill(QtGui.QColor(255,255,255,255))
        painter = QtGui.QPainter(pixmap)
        painter.setBrush(color)
        painter.drawRect(0,45,100,10)
        painter.end()
        item.setIcon(pixmap)

        return item
    
    def start_scan(self):
        self.model.clear()
        self.scan_data = {}
        parameters = {
            "write_width": np.linspace(self.scan_control_write_width_min.value(),
                                        self.scan_control_write_width_max.value(),
                                        self.scan_control_write_width_step.value()),
            "signal_width": np.linspace(self.scan_control_signal_width_min.value(),
                                        self.scan_control_signal_width_max.value(),
                                        self.scan_control_signal_width_step.value()),
            "offset": np.linspace(self.scan_control_offset_min.value(),
                                        self.scan_control_offset_max.value(),
                                        self.scan_control_offset_step.value())
        }
        
        self.start_scanning.emit(parameters)


    def update_scan_data(self, result):
        name = f"{round(result["write_width"],2)} {round(result["signal_width"],2)} {round(result["offset"],2)}"
        self.scan_data[name] = result
        item = self.new_item(name)
        self.model.appendRow(item)
        # self.plot_data()

    def stop_scanning(self):
        self.scan_worker._stop = True

    def save_current_data(self):
        pass

    def load_data(self):
        pass

    def delete_data(self):
        pass

    def plot_data(self):
        self.signal_plot.clear()

        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            color = pg.intColor(row)
   
            if item.checkState() == QtCore.Qt.CheckState.Checked:
                pen = pg.mkPen(color, width=2)
                dataset_name = item.text()
                result = self.scan_data[dataset_name]

                self.signal_plot.plot(result["bins"][:6000], result["data"][:6000], pen=pen)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = MyWidget()
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())