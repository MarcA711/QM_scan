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
    scan_data = {}

    def __init__(self):
        super().__init__()

        # thread for scanning in background
        self.worker_thread = QThread()
        self.scan_worker = ScanWorker()
        self.scan_worker.moveToThread(self.worker_thread)
        self.worker_thread.finished.connect(self.scan_worker.deleteLater)
        self.scan_worker.finished_qm_scan.connect(self.update_qm_scan_data)
        self.scan_worker.finished_ref_scan.connect(self.update_ref_scan_data)
        self.start_scanning.connect(self.scan_worker.do_repeated_scan)
        self.worker_thread.start()

        # item model that references the data from each measurement
        self.model = QtGui.QStandardItemModel()
        self.model.itemChanged.connect(self.plot_data)

        self.layout = QtWidgets.QVBoxLayout(self)

        # horizontally splitted view: left: plot; righ: properties
        main_split = QtWidgets.QSplitter()
        self.layout.addWidget(main_split)

        # plot on the left side
        graph = pg.GraphicsLayoutWidget()
        main_split.addWidget(graph)
        self.signal_plot: pg.PlotItem = graph.addPlot()
        self.signal_plot.setLabels(title="", bottom="Time [x]", left="Counts")
        self.signal_plot.showGrid(x=True, y=True)

        # properties on the right:
        # splitted vertically: up: measurement series list; bottom: scan settings
        properties = QtWidgets.QWidget()
        main_split.addWidget(properties)
        properties_layout = QtWidgets.QVBoxLayout()
        properties.setLayout(properties_layout)

        ###
        # start measurement series list
        ###

        # QGroupBox as container for measurement series
        data_control_box = QtWidgets.QGroupBox("Data")
        properties_layout.addWidget(data_control_box)
        data_control_box_layout = QtWidgets.QVBoxLayout()
        data_control_box.setLayout(data_control_box_layout)

        # layout for save, load and deleta buttons in top row
        data_button_layout = QtWidgets.QHBoxLayout()
        data_control_box_layout.addLayout(data_button_layout)

        # save
        data_save_button = QtWidgets.QPushButton()
        data_button_layout.addWidget(data_save_button)
        data_save_button.setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.DocumentSave))
        data_save_button.clicked.connect(self.save_current_data)

        # load
        data_load_button = QtWidgets.QPushButton()
        data_button_layout.addWidget(data_load_button)
        data_load_button.setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.DocumentOpen))
        data_load_button.clicked.connect(self.load_data)

        # delete
        data_del_button = QtWidgets.QPushButton()
        data_button_layout.addWidget(data_del_button)
        data_del_button.setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.EditDelete))
        data_del_button.clicked.connect(self.delete_data)

        # list of data
        data_list = QtWidgets.QListView()
        data_control_box_layout.addWidget(data_list)
        data_list.setModel(self.model)

        ###
        # end measurement series list
        ###

        # QGroupBox as container for scan settings
        scan_control_box = QtWidgets.QGroupBox("Scan setting")
        properties_layout.addWidget(scan_control_box)
        scan_control_box_layout = QtWidgets.QVBoxLayout()
        scan_control_box.setLayout(scan_control_box_layout)

        self.parameter_widgets = {}
        for parameter_name in ["write_width", "signal_width", "offset"]:
            item, ref = self.parameter_settings(parameter_name)
            self.parameter_widgets[parameter_name] = ref
            scan_control_box_layout.addLayout(item)
        
        self.scan_control_start_button = QtWidgets.QPushButton("start")
        scan_control_box_layout.addWidget(self.scan_control_start_button)
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

    def parameter_settings(self, name):
        name = name.replace("_", " ")
        layout = QtWidgets.QHBoxLayout()

        text = QtWidgets.QLabel(name)
        layout.addWidget(text)

        val_min = QtWidgets.QDoubleSpinBox()
        val_max = QtWidgets.QDoubleSpinBox()
        val_step = QtWidgets.QSpinBox()
        val_step.setMinimum(1)

        layout.addWidget(val_min)
        layout.addWidget(val_max)
        layout.addWidget(val_step)

        return layout, (val_min, val_max, val_step)

    
    def start_scan(self):
        self.model.clear()
        self.scan_data = {}
        self.plot_data()

        parameters = {name: np.linspace(ref[0].value(), ref[1].value(), ref[2].value()) for name, ref in self.parameter_widgets.items()}
        
        self.start_scanning.emit(parameters)

    def update_qm_scan_data(self, result):
        name = f"{round(result["write_width"],2)} {round(result["signal_width"],2)} {round(result["offset"],2)}"
        self.scan_data[name] = result
        item = self.new_item(name)
        self.model.appendRow(item)

    def update_ref_scan_data(self, result):
        name = f"Reference: {round(result["signal_width"],2)}"
        self.scan_data[name] = result
        item = self.new_item(name)
        self.model.appendRow(item)

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