from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QDockWidget,QSpinBox, QListWidget, QLabel,QWidget, QTextEdit, QCheckBox
from PySide6.QtGui import  QColor, QTextCursor
from PySide6.QtCore import Signal, QSettings

from stransi import Ansi, SetAttribute, SetColor
from stransi.attribute import Attribute

from eros_core import Eros, TransportStates

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QDockWidget, QListWidget, QLabel,QPushButton,QWidget,QTextEdit,QSpinBox,QFormLayout, QFileDialog,QLineEdit,QStyle,QCheckBox
from PySide6.QtGui import QFont, QColor,QAction
from PySide6.QtCore import Signal, QObject, Slot, QSettings,QTimer

import logging
from logging.handlers import RotatingFileHandler
from queue import Queue
from ochre import Color

from functools import cached_property
from typing import Dict
import os
import time
from functools import cache

COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RESET = "\033[0m"

class QDockableErosLoggingWidget(QDockWidget):
    eros_handle:Eros = None
    
    data_signal = Signal(bytes)
    unidentified_data_signal = Signal(bytes)
    
    background_color = QColor(40, 40, 40)
    current_termial_color = None
    log_file_handler = None
    def __init__(self,parent=None, font=None, settings: QSettings= None):
        super().__init__("Eros Logger", parent, objectName="eros_logger")

        self.parameters = ConfigWidget(settings)

        self.output_lines = []

        # Configure the text edit
        self.text_edit = QTextEdit()
        
        if font is not None:
            self.text_edit.setFont(font)
        
        self.textbox_data_queue = Queue()
        
        self.text_edit.setAutoFillBackground(False)
        self.text_edit.setStyleSheet(u"QTextEdit {background-color: " + self.background_color.name() + ";\ncolor: white }")
        self.text_edit.setReadOnly(True)
        self.text_edit.document().setMaximumBlockCount(self.parameters.max_line_history)
        
        self.disconnect_label = QLabel("Logger Disconnected")
        self.disconnect_label.setAlignment(Qt.AlignCenter)
        self.disconnect_label.setStyleSheet("QLabel { font-size: 20px; background-color: " + self.background_color.name() + "; color: white; }")
                    
        if self.parameters.enable_file_logging:
            #create a rotating log file handler
            filename = f"eros_log_{time.strftime('%Y%m%d-%H%M%S')}.log"
            self.log_file_handler = open(os.path.join(self.parameters.log_path,filename), 'w')
        
        # Set central widget
        self.setWidget(self.text_edit)
        # self.data_signal.connect(self.append_text_to_output)
        # self.unidentified_data_signal.connect(self.append_unidentified_text_to_output)
        
        timer = QTimer(self)
        timer.timeout.connect(self.text_edit_append_task)
        timer.start(100)

    def text_edit_append_task(self):
        if self.textbox_data_queue.empty():
            return
        buffer = []
        while not self.textbox_data_queue.empty():
            buffer.append(self.textbox_data_queue.get())

        # while not self.textbox_data_queue.empty():
        buffer = "<br>".join(buffer)
        if len(buffer) > 0:
            self.text_edit.append(buffer)
    
    @cache
    def get_color(self,value:Color ):
        return self.color_map(value.web_color.name)
        
    def color_map(self, color):
        if color == "green":
            return "lightgreen"
        elif color == "maroon":
            return "red"
        elif color == "olive":
            return "yellow"
        return color
    
    def append_text_to_output(self, text):
        """Append text to the output text box
        """
        
        instructions = Ansi(text.decode("utf-8")).instructions()
        packet = ""
        for instruction in instructions:
            if isinstance(instruction, str):

            
                if self.current_termial_color is None:
                    packet += f"<span>{instruction}</span>"
                else:
                    packet += f"<span style='color: {self.current_termial_color}'>{instruction}</span>"
            
                if self.log_file_handler is not None:
                    self.log_file_handler.write(instruction.replace("<br>",""))

            else:
                if isinstance(instruction, SetAttribute):
                    if instruction.attribute == Attribute.NORMAL:
                        self.current_termial_color = None
                elif isinstance(instruction, SetColor):
                    self.current_termial_color = self.get_color(instruction.color)
            

        if self.log_file_handler is not None:
            self.log_file_handler.flush()
            
        # NOTE: append add a new line every time, this is not desired , because a line can contain multiple packets
        # Currently they will be split into multiple lines
        self.textbox_data_queue.put(packet)
    def append_unidentified_text_to_output(self, data:bytes):
        # Here we want to sanitize the data, so its nice and printable
        # This can contain any bytes, more effor is needed
        
        #Remove zero bytes
        data = data.replace(b'\x00',b'')
        
        # Don't print empty packets
        if len(data) == 0:
            return
        
        # Decode the data, ignore errors
        data = data.decode('utf-8', errors='ignore')
        
        # Add line breaks
        data = data.replace("\n", "<br>")
                
        # Add the data to the output
        self.append_text_to_output(data.encode())
        

    def set_eros_handle(self, eros:Eros):
        self.eros_handle = eros

        for channel in self.parameters.log_channels:
            self.eros_handle.attach_channel_callback(channel, self.append_text_to_output)

        if self.parameters.log_unidentified:
            self.eros_handle.attach_fail_callback(self.append_unidentified_text_to_output)            

    def status_update_callback(self, status:TransportStates):
        if status == TransportStates.CONNECTED:
            if not self.isEnabled():        
                self.setEnabled(True)
                self.append_text_to_output(f"{COLOR_GREEN}Connected{COLOR_RESET}\n".encode())

        elif self.isEnabled():
            self.setEnabled(False)
            # Print a message to the terminal
            self.append_text_to_output(f"{COLOR_RED}Disconnected{COLOR_RESET}\n".encode())
            
    def isEnabled(self):
        return self.text_edit.isEnabled()
    
    def setEnabled(self, enabled):
        self.text_edit.setEnabled(enabled)

        if enabled:
             self.setWidget(self.text_edit)
        else:

            self.setWidget(self.disconnect_label)

# Override the QSpinBox wheel event to ignore it
class QSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()

class ConfigWidget(QWidget):
    STORAGE_NAME = "eros_logger"
    
    DEFAULT_LOG_UNIDENTIFIED = True
    DEFAULT_MAX_LINE_HISTORY = 200
    DEFAULT_LOG_CHANNELS = [1]
    
    DEFAULT_LOG_PATH = os.path.expanduser("~/Desktop/")
    DEFAULT_ENABLE_FILE_LOGGING = False
    
    def __init__(self,  settings: QSettings) -> None:
        super().__init__()
        
        self.settings = settings
        
        #add checkbox to enable/disable logging
        self.log_unidentified_checkbox = QCheckBox("Log unidentified packets")
        
        #  Add a listview to select which channel to log
        self.log_channel_list = QListWidget()
        for i in range(0, 16):
            self.log_channel_list.addItem(str(i))
        self.log_channel_list.setSelectionMode(QListWidget.MultiSelection)
        
        self.max_line_history_input = QSpinBox()
        self.max_line_history_input.setMinimum(10)
        self.max_line_history_input.setMaximum(1000)
        self.max_line_history_input.setValue(200)
            
        # Enable logging to file
        self.enable_file_logging_input = QCheckBox("Enable file logging")
        
        
        self.log_path_input = QLineEdit()
        select_folder_action = QAction(self)
        select_folder_action.triggered.connect(self.query_folder)
        select_folder_action.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.log_path_input.addAction(select_folder_action, QLineEdit.TrailingPosition)

  
        # Set the layout
        self.layout = QFormLayout()
        self.layout.addWidget(self.log_unidentified_checkbox)
        self.layout.addRow("Max Lines to show", self.max_line_history_input)
        self.layout.addRow("Log Channels", self.log_channel_list)
        
        self.layout.addWidget(self.enable_file_logging_input)
        self.layout.addRow("Log Path", self.log_path_input)
        
        self.setLayout(self.layout)

        # Connect the signals so that the settings are saved
        self.log_unidentified_checkbox.stateChanged.connect(self.save)
        self.log_channel_list.itemSelectionChanged.connect(self.save)
        self.max_line_history_input.valueChanged.connect(self.save)
        self.log_path_input.textChanged.connect(self.save)
        self.enable_file_logging_input.stateChanged.connect(self.save)
        
        # Load the settings
        self.load()
    @property
    def max_line_history(self):
        return self.max_line_history_input.value()
    
    @property
    def log_channels(self):
        return [int(item.text()) for item in self.log_channel_list.selectedItems()]
    
    @property
    def log_unidentified(self): 
        return self.log_unidentified_checkbox.isChecked()
    
    @property
    def log_path(self) -> str:
        return self.log_path_input.text()
    @property
    def enable_file_logging(self) -> bool:
        return self.enable_file_logging_input.isChecked()
    
    def query_folder(self):
        path =  QFileDialog.getExistingDirectory(self, "Select Directory", self.log_path)
        
        if path is  None or path == "":
            return
        
        self.log_path_input.setText(path)
        self.save()
            
    
    def to_dict(self):
        return {
            "enable": self.log_unidentified,
            "max_line_history": self.max_line_history,
            "channels": self.log_channels,
            "log_path": self.log_path,
            "enable_file_logging": self.enable_file_logging
        }
        
    def from_dict(self, config):
        self.log_unidentified_checkbox.setChecked(config.get("enable", self.DEFAULT_LOG_UNIDENTIFIED))
        self.max_line_history_input.setValue(config.get("max_line_history", self.DEFAULT_MAX_LINE_HISTORY))
        self.log_channel_list.clearSelection()
        for channel in config.get("channels", self.DEFAULT_LOG_CHANNELS):
            self.log_channel_list.item(channel).setSelected(True)
            
        self.log_path_input.setText(config.get("log_path", self.DEFAULT_LOG_PATH))
        self.enable_file_logging_input.setChecked(config.get("enable_file_logging", self.DEFAULT_ENABLE_FILE_LOGGING))
        
    def save(self):
        self.settings.setValue(self.STORAGE_NAME, self.to_dict())
    
    def load(self):
        config = self.settings.value(self.STORAGE_NAME, {})
        self.from_dict(config)
        