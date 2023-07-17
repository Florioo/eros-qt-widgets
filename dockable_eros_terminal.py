import termqt
import threading
from typing import Dict
from queue import Queue

from PySide2.QtGui import QColor
from PySide2.QtWidgets import QDockWidget, QWidget, QScrollBar, QHBoxLayout, QLabel, QWidget, QSpinBox, QFormLayout
from PySide2.QtGui import  QColor, QGuiApplication
from PySide2.QtCore import  QSettings, Qt

from eros_core import Eros, ResponseType, CLIResponse, CommandFrame, TransportStates

COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RESET = "\033[0m"


class QErosTerminalWidget(QDockWidget):
    eros_handle:Eros = None
    
    background_color = QColor(40, 40, 40)
    
    def __init__(self, parent=None, font=None, settings: QSettings = None):
        super().__init__("Eros Terminal", parent, objectName="eros_terminal")
        
        self.receive_queue = Queue()

        self.parameters = ConfigWidget( settings)
        
        self.terminal = termqt.Terminal(width=200, 
                                        height=200,
                                        font_size=font.pointSize(),
                                        padding=10,
                                        line_height_factor=1.1)

        self.scrollbar = QScrollBar(Qt.Vertical, self.terminal)
 
 
        self.terminal.connect_scroll_bar(self.scrollbar)
        self.terminal.enable_auto_wrap(True)
        self.terminal.set_font(font)
        self.terminal.set_bg(self.background_color)
        self.terminal.stdin_callback = self.eros_transmit_handler
        self.terminal.maximum_line_history = self.parameters.max_line_history
        
        self.disconnect_label = QLabel("Terminal Disconnected")
        self.disconnect_label.setAlignment(Qt.AlignCenter)
        self.disconnect_label.setStyleSheet("QLabel { font-size: 20px; background-color: " + self.background_color.name() + "; color: white; }")
        
        layout = QHBoxLayout() # Set the layout to the QWidget instance
        layout.addWidget(self.terminal)
        layout.addWidget(self.scrollbar)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.main_widget = QWidget()
        self.main_widget.setLayout(layout)

        
        # Set central widget
        self.setWidget(self.main_widget)
        
        # Start the terminal writer thread
        self.writer_thread = threading.Thread(target=self.async_termimal_writer, daemon=True)
        self.writer_thread.start()
        
    def wheelEvent(self, event):
        """Passes all the wheel events to the scrollbar,
        so that the user can scroll using the mouse wheel anywhere on the terminal widget.
        """
        self.scrollbar.wheelEvent(event)
        
    def set_eros_handle(self, eros:Eros):
        self.eros_handle = eros
        self.eros_handle.attach_channel_callback(self.parameters.aux_channel, self.receive_queue.put)
        self.eros_respone = CLIResponse(self.eros_handle, self.parameters.main_channel, self.eros_receive_handler)
    
    def eros_transmit_handler(self,data):
        if self.eros_handle is not None:
            self.eros_handle.transmit_packet(self.parameters.main_channel, bytes(data))
    
    def async_termimal_writer(self):
        while True:
            # Group the data in the buffer
            buffer = self.receive_queue.get()
                    
            while not self.receive_queue.empty():
                buffer = buffer + self.receive_queue.get()
            
            # Write to terminal
            self.terminal.stdout(buffer)
            
    def contextMenuEvent(self, event): 
        """Overrides the default context menu event to add a paste option. on right click
        """
        if event.reason() == event.Mouse:
            clipboard = QGuiApplication.clipboard()
            self.eros_transmit_handler(clipboard.text().encode())
   
        super().contextMenuEvent(event)
        
    def eros_receive_handler(self, packet:CommandFrame):
        if packet.resp_type == ResponseType.NACK:
            if len(packet.data):
                ret = ( f"{COLOR_RED}Error: {packet.data.decode()}{COLOR_RESET}\n")
            else:
                ret = ( f"{COLOR_RED}Error{COLOR_RESET}\n")
        else:
            if len(packet.data):
                ret = ( f"{packet.data.decode()}\n")
            else:
                ret = ( f"{COLOR_GREEN}OK{COLOR_RESET}\n")
        
        self.receive_queue.put(ret.encode())
        
    def status_update_callback(self, status:TransportStates):
        if status == TransportStates.CONNECTED:
            if not self.isEnabled():        
                self.setEnabled(True)
                self.receive_queue.put(f"{COLOR_GREEN}Connected{COLOR_RESET}\n".encode())

        elif self.isEnabled():
            self.setEnabled(False)
            # Print a message to the terminal
            self.receive_queue.put(f"{COLOR_RED}Disconnected{COLOR_RESET}\n".encode())
            
    def isEnabled(self):
        return self.main_widget.isEnabled()
    
    def setEnabled(self, enabled):
        self.main_widget.setEnabled(enabled)

        if enabled:
             self.setWidget(self.main_widget)
        else:

            self.setWidget(self.disconnect_label)
            
            
# Override the QSpinBox wheel event to ignore it
class QSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()

class ConfigWidget(QWidget):
    
    STORAGE_NAME = "eros_terminal"
    
    DEFAULT_MAIN_CHANNEL = 5
    DEFAULT_AUX_CHANNEL = 6
    DEFAULT_MAX_LINE_HISTORY = 200
    
    def __init__(self, settings: QSettings) -> None:
        super().__init__()
        
        self.settings = settings
        
        # Create the inputs
        self.main_channel_input = QSpinBox()
        self.main_channel_input.setMinimum(0)
        self.main_channel_input.setMaximum(15)
        self.main_channel_input.setValue(5)
        
        self.aux_channel_input = QSpinBox()
        self.aux_channel_input.setMinimum(0)
        self.aux_channel_input.setMaximum(15)
        self.aux_channel_input.setValue(6)
        
        self.max_line_history_input = QSpinBox()
        self.max_line_history_input.setMinimum(10)
        self.max_line_history_input.setMaximum(1000)
        self.max_line_history_input.setValue(200)
        
        # Set the layout
        self.layout = QFormLayout()
        self.layout.addRow("Main Channel", self.main_channel_input)
        self.layout.addRow("Aux Channel", self.aux_channel_input)
        self.layout.addRow("Max Line History", self.max_line_history_input)
        self.setLayout(self.layout)

        # Save the settings when the inputs change
        self.main_channel_input.valueChanged.connect(self.save)
        self.aux_channel_input.valueChanged.connect(self.save)
        self.max_line_history_input.valueChanged.connect(self.save)
        
        # Load the settings at startup
        self.load()
    
    @property
    def main_channel(self):
        return self.main_channel_input.value()
    
    @property
    def aux_channel(self):
        return self.aux_channel_input.value()

    @property
    def max_line_history(self):
        return self.max_line_history_input.value()
                
    def to_dict(self):
        return {
            "main_channel": self.main_channel,
            "aux_channel": self.aux_channel,
            "max_line_history": self.max_line_history
        }
        
    def from_dict(self, config: Dict):
        self.main_channel_input.setValue(config.get("main_channel",self.DEFAULT_MAIN_CHANNEL))
        self.aux_channel_input.setValue(config.get("aux_channel", self.DEFAULT_AUX_CHANNEL))
        self.max_line_history_input.setValue(config.get("max_line_history", self.DEFAULT_MAX_LINE_HISTORY))

    def save(self):
        self.settings.setValue(self.STORAGE_NAME, self.to_dict())
    
    def load(self):
        config = self.settings.value(self.STORAGE_NAME, {})
        self.from_dict(config)
        
        