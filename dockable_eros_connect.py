from typing import Dict

from eros_core import Eros, ErosSerial, ErosTCP, ErosUDP, ErosZMQ, TransportStates
from pydantic import BaseModel
from qtpy.QtCore import QRegularExpression, QSettings, Qt, QTimer, Signal
from qtpy.QtGui import QRegularExpressionValidator
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)
from qt_settings import QGenericSettingsWidget
from si_prefix import si_format

from .data_output import ErosZMQBroker
from .ui.eros_connect import Ui_Form

UART_VID_MAP = {4292: "ESP32", 1027: "ESP-PROG"}


class QDockableErosConnectWidget(QDockWidget):
    STORAGE_LOCATION = "eros_connection"

    eros: Eros | None = None
    last_state = None
    zmq_broker = None

    eros_handle_signal = Signal(Eros)
    eros_connection_change_signal = Signal(TransportStates)

    def __init__(self, parent, config_widget: "ErosConnectConfigWidget", settings: QSettings):
        super().__init__("Eros Connect", parent, objectName="eros_connect_widget")  # type: ignore

        self.main_widget = QWidget()

        self.storage = settings
        self.config = config_widget.data

        self.ui = Ui_Form()
        self.ui.setupUi(self.main_widget)

        # Set central widget
        self.setWidget(self.main_widget)

        self.uart_handler = UART_Handler(
            self.ui.uart_baud_selector,
            self.ui.uart_device_selector,
            self.ui.uart_device_scan,
            self.storage,
        )
        self.tcp_handler = TCP_Handler(self.ui.tcp_host, self.ui.tcp_port, self.storage)
        self.udp_handler = UDP_Handler(self.ui.udp_host, self.ui.udp_port, self.storage)
        self.zmq_handler = ZMQ_Handler(self.ui.zmq_host, self.ui.zmq_port, self.storage)

        # Connect button
        self.ui.connect_disconnect_btn.clicked.connect(self.toggle_connect_button)

        # Set alignment of laabel
        self.ui.traffic_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.ui.traffic_label.setStyleSheet("background-color: rgb(230, 230, 230);")
        self.ui.traffic_label.setText("")

        # Create a QTimer to update the UI
        self.ui_update_timer = QTimer()
        self.ui_update_timer.timeout.connect(self.update_ui)
        self.ui_update_timer.setSingleShot(False)
        self.ui_update_timer.start(100)

        if self.config.zmq_enable:
            self.zmq_broker = ErosZMQBroker("127.0.0.1", 2000)

        self.load_config()

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

        self.ui.traffic_label.setText(
            f"in:    {si_format(outgoing_data, precision=2)}B\n"
            f"out:   {si_format(incoming_data, precision=2)}B\n"
            f"error: {si_format(unrecognized_data, precision=2)}B"
        )

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
                self.eros = self.uart_handler.connect(auto_reconnect=self.config.auto_reconnect)

            elif self.ui.tabWidget.currentIndex() == 1:
                self.eros = self.tcp_handler.connect(auto_reconnect=self.config.auto_reconnect)

            elif self.ui.tabWidget.currentIndex() == 2:
                self.eros = self.udp_handler.connect()

            elif self.ui.tabWidget.currentIndex() == 3:
                self.eros = self.zmq_handler.connect()

            self.eros_handle_signal.emit(self.eros)

        else:
            assert self.eros is not None

            self.eros.close()
            self.eros = None

        if self.zmq_broker is not None:
            assert self.eros is not None
            self.zmq_broker.attach_eros(self.eros)

        self.update_connection_status()

    def update_connection_status(self):
        if self.is_connected():
            self.ui.tabWidget.setEnabled(False)
            self.ui.connect_disconnect_btn.setText("Disconnect")

        else:
            self.ui.tabWidget.setEnabled(True)
            self.ui.connect_disconnect_btn.setText("Connect")

    def save_config(self):
        config = {
            "selected_tab": self.ui.tabWidget.currentIndex(),
        }

        self.storage.setValue(self.STORAGE_LOCATION, config)

        self.uart_handler.save_config()
        self.tcp_handler.save_config()
        self.udp_handler.save_config()
        self.zmq_handler.save_config()

    def load_config(self):
        config = self.storage.value(self.STORAGE_LOCATION, {})

        assert isinstance(config, Dict)

        if config == {}:
            return

        # Only set the values if they are valid
        self.ui.tabWidget.setCurrentIndex(config.get("selected_tab", 0))


class UART_Handler:
    STORAGE_LOCATION = "eros_uart_connection"

    loaded_port = None

    def __init__(self, baud_combobox, device_combobox, scan_button, storage: QSettings):
        self.device_combobox: QComboBox = device_combobox
        self.baud_combobox: QComboBox = baud_combobox
        self.scan_button: QPushButton = scan_button
        self.uart_device_list = []
        self.storage = storage

        # Only allow numbers in the baud combobox
        reg_ex = QRegularExpression("[0-9]+")
        input_validator = QRegularExpressionValidator(reg_ex, self.baud_combobox)
        self.baud_combobox.setValidator(input_validator)

        self.scan_button.clicked.connect(self.scan_uart_devices)

        self.load_config()

    def scan_uart_devices(self):
        if self.loaded_port is not None:
            current_selected_port = self.loaded_port
            self.loaded_port = None
        else:
            # Get current selection
            current_selected_port = self.uart_get_current_port()

        self.device_combobox.clear()

        serial_ports = ErosSerial.get_serial_ports()  # type: ignore

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

    def connect(self, auto_reconnect=True):
        target_port = self.uart_get_current_port()

        if target_port is None:
            return

        baud_rate = int(self.baud_combobox.currentText())

        # Connect to the device
        eros_transport_handle = ErosSerial(target_port, baud_rate, auto_reconnect=auto_reconnect)
        eros_handle = Eros(eros_transport_handle)

        self.save_config()

        return eros_handle

    def save_config(self):
        if self.device_combobox.currentIndex() == -1:
            return

        config = {
            "uart_baud": self.baud_combobox.currentText(),
            "uart_device": self.uart_device_list[self.device_combobox.currentIndex()].port,
        }

        self.storage.setValue(self.STORAGE_LOCATION, config)

    def load_config(self):
        config = self.storage.value(self.STORAGE_LOCATION, {})

        assert isinstance(config, dict)

        if config == {}:
            return

        # Only set the values if they are valid
        self.baud_combobox.setCurrentText(config.get("uart_baud", "2000000"))
        self.loaded_port = config.get("uart_device")

        # Update the list of devices
        self.scan_uart_devices()


class TCP_Handler:
    STORAGE_LOCATION = "eros_tcp_connection"

    def __init__(self, ip_lineedit, port_lineedit, storage: QSettings):
        self.ip_lineedit: QLineEdit = ip_lineedit
        self.port_lineedit: QLineEdit = port_lineedit
        self.storage = storage
        self.load_config()

    def connect(self, auto_reconnect=True):
        port = int(self.port_lineedit.text())
        ip = self.ip_lineedit.text()

        # Connect to the device
        eros_transport_handle = ErosTCP(ip, port, auto_reconnect=auto_reconnect)
        eros_handle = Eros(eros_transport_handle)

        self.save_config()

        return eros_handle

    def save_config(self):
        config = {
            "ip": self.ip_lineedit.text(),
            "port": self.port_lineedit.text(),
        }
        self.storage.setValue(self.STORAGE_LOCATION, config)

    def load_config(self):
        config = self.storage.value(self.STORAGE_LOCATION, {})

        assert isinstance(config, dict)

        if config == {}:
            return

        # Only set the values if they are valid
        self.ip_lineedit.setText(config.get("ip", ""))
        self.port_lineedit.setText(config.get("port", "6666"))


class UDP_Handler:
    STORAGE_LOCATION = "eros_udp_connection"

    def __init__(self, ip_lineedit, port_lineedit, storage: QSettings):
        self.ip_lineedit: QLineEdit = ip_lineedit
        self.port_lineedit: QLineEdit = port_lineedit
        self.storage = storage
        self.load_config()

    def connect(self, auto_reconnect=True):
        port = int(self.port_lineedit.text())
        ip = self.ip_lineedit.text()

        # Connect to the device
        eros_transport_handle = ErosUDP(ip, port)
        eros_handle = Eros(eros_transport_handle)

        self.save_config()

        return eros_handle

    def save_config(self):
        config = {
            "ip": self.ip_lineedit.text(),
            "port": self.port_lineedit.text(),
        }
        self.storage.setValue(self.STORAGE_LOCATION, config)

    def load_config(self):
        config = self.storage.value(self.STORAGE_LOCATION, {})

        assert isinstance(config, dict)

        if config == {}:
            return

        # Only set the values if they are valid
        self.ip_lineedit.setText(config.get("ip", ""))
        self.port_lineedit.setText(config.get("port", "5555"))


class ZMQ_Handler:
    STORAGE_LOCATION = "eros_zmq_connection"

    def __init__(self, ip_lineedit, port_lineedit, storage: QSettings):
        self.ip_lineedit: QLineEdit = ip_lineedit
        # Disable the ip line edit
        self.ip_lineedit.setEnabled(False)

        self.port_lineedit: QLineEdit = port_lineedit
        self.storage = storage
        self.load_config()

    def connect(self, auto_reconnect=True):
        port = int(self.port_lineedit.text())
        # ip = self.ip_lineedit.text()

        # Connect to the device
        eros_transport_handle = ErosZMQ(port)
        eros_handle = Eros(eros_transport_handle)

        self.save_config()

        return eros_handle

    def save_config(self):
        config = {
            "ip": self.ip_lineedit.text(),
            "port": self.port_lineedit.text(),
        }
        self.storage.setValue(self.STORAGE_LOCATION, config)

    def load_config(self):
        config = self.storage.value(self.STORAGE_LOCATION, {})

        assert isinstance(config, dict)

        if config == {}:
            return

        # Only set the values if they are valid
        self.ip_lineedit.setText(config.get("ip", "127.0.0.1"))
        self.port_lineedit.setText(config.get("port", "2000"))


class ErosConnectConfigWidget(QGenericSettingsWidget):
    class Model(BaseModel):
        zmq_enable: bool = False
        auto_reconnect: bool = True

    def __init__(self) -> None:
        super().__init__()

        # Create the inputs
        self.zmq_enable_input = QCheckBox("Enable ZMQ")
        self.auto_reconnect_input = QCheckBox("Auto Reconnect")

        # Set the layout
        self._layout = QFormLayout()
        self._layout.addRow(self.zmq_enable_input)
        self._layout.addRow(self.auto_reconnect_input)
        self.setLayout(self._layout)

        # Save the settings when the inputs change
        self.zmq_enable_input.stateChanged.connect(self._on_value_changed)
        self.auto_reconnect_input.stateChanged.connect(self._on_value_changed)

    @property
    def data(self) -> Model:
        return ErosConnectConfigWidget.Model(
            zmq_enable=self.zmq_enable_input.isChecked(),
            auto_reconnect=self.auto_reconnect_input.isChecked(),
        )

    @data.setter
    def data(self, config: Model):
        self.zmq_enable_input.setChecked(config.zmq_enable)
        self.auto_reconnect_input.setChecked(config.auto_reconnect)
