from typing import Dict


from PySide2.QtCore import Qt, QRegExp
from PySide2.QtWidgets import QDockWidget, QPushButton,QWidget,QWidget,QComboBox,QCheckBox,QFormLayout,QSpinBox
from PySide2.QtCore import Signal, QTimer,QSettings
from PySide2.QtGui import QRegExpValidator

from eros_core import Eros, ErosSerial,TransportStates
from si_prefix import si_format

from .ui.eros_connect import Ui_Form
from .data_output import ErosZMQBroker
          
UART_VID_MAP = {4292:  "ESP32",
                1027:  "ESP-PROG"}    

class QDockableErosConnectWidget(QDockWidget):
    STORAGE_LOCATION = "eros_connection"
    
    eros = None 
    last_state = None
    zmq_broker = None

    
    eros_handle_signal = Signal(Eros)
    eros_connection_change_signal = Signal(TransportStates)
    
    def __init__(self,parent=None, persistent_settings: QSettings = None):
        super().__init__("Eros Connect",
                         parent,
                         objectName="eros_connection")
        
        self.main_widget = QWidget()
        self.storage = persistent_settings
        
        self.parameters = ConfigWidget(persistent_settings)
        
        self.ui = Ui_Form()
        self.ui.setupUi(self.main_widget)

        # Set central widget
        self.setWidget(self.main_widget)
        
        self.uart_handler = UART_Handler(self.ui.uart_baud_selector, self.ui.uart_device_selector, self.ui.uart_device_scan, self.storage)

        # Connect button
        self.ui.connect_disconnect_btn.clicked.connect(self.toggle_connect_button)

        # Set alignment of laabel
        self.ui.traffic_label.setAlignment(Qt.AlignTop)
        self.ui.traffic_label.setStyleSheet("background-color: rgb(230, 230, 230);")
        self.ui.traffic_label.setText("")
        
        # Create a QTimer to update the UI
        self.ui_update_timer = QTimer()
        self.ui_update_timer.timeout.connect(self.update_ui)
        self.ui_update_timer.setSingleShot(False)
        self.ui_update_timer.start(100)
        
        if self.parameters.zmq_enable:
            self.zmq_broker = ErosZMQBroker("127.0.0.1", 2000)
        
    def update_ui(self):
        if self.eros is None:
            if self.last_state is None:
                return
            
            self.eros_connection_change_signal.emit(None)
            
            self.ui.status_general.setText("Not Active")
            self.ui.status_general.setStyleSheet("background-color: lightgrey")
            self.last_state = None
            return
        
        outgoing_data = 0
        incoming_data = 0
        unrecognized_data = 0
        
        for id, group in self.eros.analytics.items():
            if id == -1:
                unrecognized_data += group[0].get_total()
                continue
            outgoing_data += group[0].get_total()
            incoming_data += group[1].get_total()
            

        self.ui.traffic_label.setText(f"in:    {si_format(outgoing_data, precision=2)}B\n"\
                                      f"out:   {si_format(incoming_data, precision=2)}B\n" \
                                      f"error: {si_format(unrecognized_data, precision=2)}B")      
             
        status = self.eros.get_state()
        
        if status == self.last_state:
            return

        self.eros_connection_change_signal.emit(status)
        self.last_state = status
        
            
        if status == TransportStates.CONNECTED:
            self.ui.status_general.setText("Connected")
            self.ui.status_general.setStyleSheet("background-color: lightgreen")
            
        elif status == TransportStates.CONNECTING:
            self.ui.status_general.setText("Connecting")
            self.ui.status_general.setStyleSheet("background-color: lightyellow")
            
        elif status == TransportStates.DEAD:            
            self.ui.status_general.setText("Dead")
            self.ui.status_general.setStyleSheet("background-color: red")
        
        
    def is_connected(self):
        return self.eros is not None
    
    def toggle_connect_button(self):
        # Lock the tab widget
        if not self.is_connected():
            
            if self.ui.tabWidget.currentIndex() == 0:
                self.eros = self.uart_handler.connect(auto_reconnect=self.parameters.auto_reconnect)
            
            self.eros_handle_signal.emit(self.eros)

        else:
            self.eros.close()
            self.eros = None
            
        if self.zmq_broker is not None:
            self.zmq_broker.attach_eros(self.eros)
        
        self.update_connection_status()
        
    def update_connection_status(self): 
        if self.is_connected():
            self.ui.tabWidget.setEnabled(False)
            self.ui.connect_disconnect_btn.setText("Disconnect")
            
        else:
            self.ui.tabWidget.setEnabled(True)
            self.ui.connect_disconnect_btn.setText("Connect")
            


class UART_Handler():
    STORAGE_LOCATION = "eros_uart_connection"
    def __init__(self, baud_combobox, device_combobox, scan_button,storage:QSettings):
        self.device_combobox:QComboBox = device_combobox
        self.baud_combobox:QComboBox = baud_combobox
        self.scan_button :QPushButton= scan_button
        self.uart_device_list = None
        self.storage = storage
        
        # Only allow numbers in the baud combobox
        reg_ex = QRegExp("[0-9]+")
        input_validator = QRegExpValidator(reg_ex, self.baud_combobox)
        self.baud_combobox.setValidator(input_validator)

        self.scan_button.clicked.connect(self.scan_uart_devices)

        self.load_config()
        
    def scan_uart_devices(self):
        # Get current selection
        current_selected_port =  self.uart_get_current_port()
        
        if current_selected_port is not None:
            current_selected_port = current_selected_port
            
        self.device_combobox.clear()
        
        serial_ports = ErosSerial.get_serial_ports()
        for port in serial_ports:
            if port.vid in UART_VID_MAP:
                self.device_combobox.addItem(f"{port.port} ({UART_VID_MAP[port.vid]})")
            else:
                self.device_combobox.addItem(f"{port.port} (Unknown)")
        self.uart_device_list = serial_ports
        
        # Restore selection
        for i, port in enumerate(self.uart_device_list):
            if port.port == current_selected_port:
                self.device_combobox.setCurrentIndex(i)
                
    def uart_get_current_port(self):
        handle = self.uart_get_current_device()
        if handle is None:
            return None
        return handle.port
    
    def uart_get_current_device(self):
        index = self.device_combobox.currentIndex()
        if not self.uart_device_list:
            return None
        
        if len(self.uart_device_list) < index:
            return None
        
        return self.uart_device_list[index]
    
    def connect(self,auto_reconnect=True):
        target_port = self.uart_get_current_port()
        
        if target_port is None:
            return
        
        baud_rate = int(self.baud_combobox.currentText())

        # Connect to the device
        eros_transport_handle = ErosSerial(target_port,baud_rate, auto_reconnect=auto_reconnect)
        eros_handle = Eros(eros_transport_handle)
        
        self.save_config()
        
        return eros_handle
    
    def save_config(self):
        config  ={
            "uart_baud": self.baud_combobox.currentText(),
            "uart_device": self.device_combobox.currentText(),
        }

        self.storage.setValue(self.STORAGE_LOCATION, config)
        
    def load_config(self):
        config = self.storage.value(self.STORAGE_LOCATION, {})
        
        if config == {}:
            return
        
        # Only set the values if they are valid
        self.baud_combobox.setCurrentText(config.get("uart_baud","2000000"))
        self.device_combobox.setCurrentText(config.get("uart_device",""))
        # Update the list of devices
        self.scan_uart_devices()
        
# Override the QSpinBox wheel event to ignore it
class QSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()
 
             
class ConfigWidget(QWidget):
    
    STORAGE_NAME = "eros_connect"
    
    DEFAULT_ZMQ_ENABLE = False
    DEFAULT_AUTO_RECONNECT = True
    
    def __init__(self,settings: QSettings) -> None:
        super().__init__()
        
        self.settings = settings
        
        # Create the inputs
        self.zmq_enable_input = QCheckBox("Enable ZMQ")
        self.auto_reconnect_input = QCheckBox("Auto Reconnect")
        
        # Set the layout
        self.layout = QFormLayout()
        self.layout.addRow( self.zmq_enable_input)
        self.layout.addRow( self.auto_reconnect_input)
        self.setLayout(self.layout)

        # Save the settings when the inputs change
        self.zmq_enable_input.stateChanged.connect(self.save)
        self.auto_reconnect_input.stateChanged.connect(self.save)
        
        # Load the settings at startup
        self.load()
    
    @property
    def zmq_enable(self):
        return self.zmq_enable_input.isChecked()
    
    @property
    def auto_reconnect(self):
        return self.auto_reconnect_input.isChecked()
    
                
    def to_dict(self):
        return {
            "zmq_enable": self.zmq_enable,
            "auto_reconnect": self.auto_reconnect,
        }
        
    def from_dict(self, config: Dict):
        self.zmq_enable_input.setChecked(config.get("zmq_enable", self.DEFAULT_ZMQ_ENABLE))
        self.auto_reconnect_input.setChecked(config.get("auto_reconnect", self.DEFAULT_AUTO_RECONNECT))
        
    def save(self):
        self.settings.setValue(self.STORAGE_NAME, self.to_dict())
    
    def load(self):
        config = self.settings.value(self.STORAGE_NAME, {})
        self.from_dict(config)
        
        