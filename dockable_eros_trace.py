import json
import time
import os

from PySide6.QtWidgets import  QDockWidget,QTreeWidgetItem,QWidget,QStyle
from PySide6.QtCore import Signal, Qt, QSettings,QTimer
from PySide6.QtWidgets import  QDockWidget,QLineEdit, QLabel,QWidget,QSpinBox,QFormLayout,QFileDialog,QTreeWidget,QDoubleSpinBox,QCheckBox
from PySide6.QtGui import QFont,QIcon,QAction

from eros_core import Eros,TransportStates
from .ui.eros_trace import Ui_Form
from .data_output import CSVOutput, UDPOutput
from .dockable_graph import QGraphWidget
from typing import List

class QErosTraceWidget(QDockWidget):
    eros_handle:Eros = None
    
    data_signal = Signal(bytes)
    last_update = time.time()
    
    csv_output = None
    
    def __init__(self,parent=None, settings: QSettings = None):
        super().__init__("Eros Trace", parent, objectName="eros_trace")
        
        self.main_widget = QWidget()
        self.settings = settings
        self.graphs:List[QGraphWidget] = []
        
        self.csv_output = CSVOutput()
        self.udp_output = UDPOutput()
        self.start_time = time.time()
        
        self.ui = Ui_Form()
        self.ui.setupUi(self.main_widget)

        #Configure the table
        self.ui.data_viewer.setAlternatingRowColors(True)
        self.ui.data_viewer.setWordWrap(True)
        self.ui.data_viewer.setSelectionMode(QTreeWidget.ExtendedSelection)

        # Set the headers
        self.ui.data_viewer.setHeaderLabels(["Key", "Value"])
        self.ui.logger_btn.clicked.connect(self.toggle_csv_logging)
        self.ui.udp_btn.clicked.connect(self.toggle_udp_output)
        self.ui.plotter_btn.clicked.connect(self.create_plotter)
        self.ui.clear_btn.clicked.connect(lambda: self.ui.data_viewer.clear())
        
        self.parameters = ConfigWidget( settings)
        
        # Set central widget
        self.setWidget(self.main_widget)
        self.data_signal.connect(self.update_table)
        
        #start update timer
        self.update_timer = QTimer(singleShot=False, interval=100)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start()
        
        self.load_config()
        
        if self.parameters.udp_auto_start:
            self.toggle_udp_output()
            
    def update_table(self, text:bytes):
        """Append text to the output text box
        """
        text = text.decode("utf-8")
        if text[0] == "{":
            obj = json.loads(text)
        else:
            # Load csv
            obj = {}
            for i, key in enumerate(text.split(",")):
                obj[f"item {i}"] = key
                
        if self.csv_output.is_open():
            self.csv_output.write(obj)
        
        if self.udp_output.is_open():
            self.udp_output.write(obj)
        
        for graph in self.graphs:
            # Add time index
            _obj = obj.copy() 
            _obj["time"] = time.time() - self.start_time
            if not graph.isOpen():
                self.graphs.remove(graph)
                break
            
            graph.update(_obj)
            
            
        # Limit update rate for the graphical portion
        if time.time() - self.last_update < 0.05:
            return
        
        self.last_update = time.time()
        
        
        for key,value in obj.items():
            # find the item in the list
            items = self.ui.data_viewer.findItems(key, Qt.MatchExactly)
            
            if len(items) == 0: 
                # Add item to the list
                item = QTreeWidgetItem(self.ui.data_viewer)
                item.setText(0, key)
                item.setText(1, str(value))
                self.ui.data_viewer.addTopLevelItem(item)
                # Resize the columns
                self.ui.data_viewer.resizeColumnToContents(0)
                
            else:
                # Update the item
                item = items[0]
                item.setText(1, str(value))
                
    def toggle_csv_logging(self):
        if not self.csv_output.is_open() :
            self.csv_output.open(self.parameters.csv_path, skip_every_n_lines=0)
        else:
            self.csv_output.close()

    def toggle_udp_output(self):
        if not self.udp_output.is_open() :
            self.udp_output.open(self.parameters.udp_ip, self.parameters.udp_port)
        else:
            self.udp_output.close()
        self.update_ui()
        
    def create_plotter(self):
        selected_items = self.ui.data_viewer.selectedItems()
        
        if len(selected_items) == 0:
            return
        
        next_id = 1
        if len(self.graphs) > 0:
            next_id = max([graph.id for graph in self.graphs]) + 1
            
        dockable_widget = QGraphWidget( id= next_id,
                                        columns=[item.text(0) for item in selected_items],
                                        index="time",
                                        max_points=self.parameters.max_point_history,
                                        max_update_rate=self.parameters.max_update_rate)
        
        self.parent().addDockWidget(Qt.RightDockWidgetArea, dockable_widget)
        
        self.graphs.append(dockable_widget)
        
    def update_ui(self):
        status_string = ""
        if  self.udp_output.is_open():
            self.ui.udp_btn.setText("Stop UDP")
            status_string += f"UDP Packets: {self.udp_output.get_logged_packets()}\n"
        else:
            self.ui.udp_btn.setText("Start UDP")
            
        if self.csv_output.is_open():
            self.ui.logger_btn.setText("Stop Logging")
            status_string += f"CSV Packets: {self.csv_output.get_logged_packets()}\n"
        else:
            self.ui.logger_btn.setText("Start Logging")
        
        self.ui.label.setText(status_string)
        

    def set_eros_handle(self, eros:Eros):
        self.eros_handle = eros
        self.eros_handle.attach_channel_callback(self.parameters.trace_channel, self.data_signal.emit)
            
    def status_update_callback(self, status:TransportStates):
        if status == TransportStates.CONNECTED:
            self.main_widget.setEnabled(True)
        else:
            self.main_widget.setEnabled(False)

    def save_config(self):
       # Save the state of all the dockable widgets
        widget_config = [param.to_dict() for param in self.graphs]
        self.settings.setValue("graph_widgets", widget_config)
        
    def load_config(self):
        widgets = self.settings.value("graph_widgets", [])
        for widget_config in widgets:
            dockable_widget = QGraphWidget.from_dict(widget_config)
            if dockable_widget is None:
                continue
            self.parent().addDockWidget(Qt.RightDockWidgetArea, dockable_widget)
            self.graphs.append(dockable_widget)
            
# Override the QSpinBox wheel event to ignore it
class QSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()


class ConfigWidget(QWidget):
    STORAGE_NAME = "eros_trace"
    
    DEFAULT_TRACE_CHANNEL = 10
    DEFAULT_UDP_IP = "127.0.0.1"
    DEFAULT_UDP_PORT = 1234
    DEFAULT_UDP_AUTO_START = False
    
    DEFAULT_PATH = os.path.expanduser("~/Desktop/")
    
    DEFAULT_MAX_POINT_HISTORY = 5000
    DEFAULT_MAX_UPDATE_RATE = 15
    
    def __init__(self, settings: QSettings) -> None:
        super().__init__()
        
        self.settings = settings
        
        self.trace_channel_input = QSpinBox()
        self.trace_channel_input.setMinimum(0)
        self.trace_channel_input.setMaximum(16)
        self.trace_channel_input.setValue(10)
        
        self.udp_ip_input = QLineEdit()
        self.udp_ip_input.setText(self.DEFAULT_UDP_IP)
        
        self.udp_port_input = QSpinBox()
        self.udp_port_input.setMinimum(0)
        self.udp_port_input.setMaximum(65535)
        self.udp_port_input.setValue(self.DEFAULT_UDP_PORT)
        
        self.udp_auto_start_input = QCheckBox("Auto start")
         
        self.csv_path_input = QLineEdit()
        self.csv_path_input.setText(self.DEFAULT_PATH)
        
        select_folder_action = QAction(self)
        select_folder_action.triggered.connect(self.query_folder)
        select_folder_action.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.csv_path_input.addAction(select_folder_action, QLineEdit.TrailingPosition)

        self.max_point_history_input = QSpinBox()
        self.max_point_history_input.setMinimum(0)
        self.max_point_history_input.setMaximum(10000)
        self.max_point_history_input.setValue(1000)

        self.max_update_rate_input = QDoubleSpinBox()
        self.max_update_rate_input.setMinimum(0.1)
        self.max_update_rate_input.setMaximum(20)
        self.max_update_rate_input.setValue(1)

        font = QFont()
        font.setUnderline(True)
        
        # Set the layout
        self.layout = QFormLayout()
        self.layout.addRow("Trace Channel", self.trace_channel_input)
        # Add a label on the first column, which contains underlined text "UDP Settings"

        self.layout.addRow(QLabel("UDP Settings", font=font))
        self.layout.addRow("UDP IP", self.udp_ip_input)
        self.layout.addRow("UDP Port", self.udp_port_input)
        self.layout.addWidget( self.udp_auto_start_input)
        
        self.layout.addRow(QLabel("CSV Settings", font=font))
        self.layout.addRow("Path", self.csv_path_input)
        
        self.layout.addRow(QLabel("Plot settings", font=font))
        self.layout.addRow("Max points", self.max_point_history_input)
        self.layout.addRow("Max update rate", self.max_update_rate_input)
        
        self.setLayout(self.layout)
        

        self.udp_ip_input.textChanged.connect(self.save)
        self.udp_port_input.valueChanged.connect(self.save)
        self.csv_path_input.textChanged.connect(self.save)
        self.trace_channel_input.valueChanged.connect(self.save)
        self.max_point_history_input.valueChanged.connect(self.save)
        self.max_update_rate_input.valueChanged.connect(self.save)
        self.udp_auto_start_input.stateChanged.connect(self.save)

        
        # Load the settings
        self.load()
    
    @property
    def udp_auto_start(self):
        return self.udp_auto_start_input.isChecked()
    
    @property
    def max_point_history(self):
        return self.max_point_history_input.value()
    @property
    def max_update_rate(self):
        return self.max_update_rate_input.value()
    
    @property
    def trace_channel(self):
        return self.trace_channel_input.value()
    @property
    def udp_ip(self):
        return self.udp_ip_input.text()
    
    @property
    def udp_port(self):
        return self.udp_port_input.value()
    
    @property
    def csv_path(self):
        return self.csv_path_input.text()
    
    def query_folder(self):
        path =  QFileDialog.getExistingDirectory(self, "Select Directory", self.csv_path)
        
        if path is  None or path == "":
            return
        
        self.csv_path_input.setText(path)
        self.save()
            
    def to_dict(self):
        return {
            "udp_ip": self.udp_ip,
            "udp_port": self.udp_port,
            "csv_path": self.csv_path,
            "trace_channel": self.trace_channel,
            "max_point_history": self.max_point_history,
            "max_update_rate": self.max_update_rate,
            "udp_auto_start": self.udp_auto_start
        }
        
    def from_dict(self, config):
        self.udp_ip_input.setText(config.get("udp_ip", self.DEFAULT_UDP_IP))
        self.udp_port_input.setValue(config.get("udp_port", self.DEFAULT_UDP_PORT))
        self.csv_path_input.setText(config.get("csv_path", self.DEFAULT_PATH))
        self.trace_channel_input.setValue(config.get("trace_channel", self.DEFAULT_TRACE_CHANNEL))
        self.max_point_history_input.setValue(config.get("max_point_history", self.DEFAULT_MAX_POINT_HISTORY))
        self.max_update_rate_input.setValue(config.get("max_update_rate", self.DEFAULT_MAX_UPDATE_RATE))
        self.udp_auto_start_input.setChecked(config.get("udp_auto_start", self.DEFAULT_UDP_AUTO_START))
        
    def save(self):
        self.settings.setValue(self.STORAGE_NAME, self.to_dict())
    
    def load(self):
        config = self.settings.value(self.STORAGE_NAME, {})
        self.from_dict(config)
        