import os
import time
from functools import cache
from queue import Queue
from typing import List

from eros_core import Eros, TransportStates
from ochre import Color
from pydantic import BaseModel
from qt_settings import QGenericSettingsWidget
from qtpy.QtCore import Qt, QTimer, Signal
from qtpy.QtGui import QAction, QColor
from qtpy.QtWidgets import (
    QCheckBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QSpinBox,
    QStyle,
    QTextEdit,
)
from stransi import Ansi, SetAttribute, SetColor
from stransi.attribute import Attribute

COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RESET = "\033[0m"


class QDockableErosLoggingWidget(QDockWidget):
    eros_handle: Eros | None = None

    data_signal = Signal(bytes)
    unidentified_data_signal = Signal(bytes)

    background_color = QColor(40, 40, 40)
    current_termial_color = None
    log_file_handler = None

    def __init__(self, parent, config: "LoggerConfigWidget", font=None):
        super().__init__("Eros Logger", parent)

        self.output_lines = []
        self.config_widget = config
        self.config = config.data

        # Configure the text edit
        self.text_edit = QTextEdit()

        if font is not None:
            self.text_edit.setFont(font)

        self.textbox_data_queue = Queue()

        self.text_edit.setAutoFillBackground(False)
        self.text_edit.setStyleSheet(
            "QTextEdit {background-color: " + self.background_color.name() + ";\ncolor: white }"
        )
        self.text_edit.setReadOnly(True)
        self.text_edit.document().setMaximumBlockCount(self.config.max_line_history)

        self.disconnect_label = QLabel("Logger Disconnected")
        self.disconnect_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.disconnect_label.setStyleSheet(
            "QLabel { font-size: 20px; background-color: " + self.background_color.name() + "; color: white; }"
        )

        if self.config.enable_file_logging:
            # create a rotating log file handler
            filename = f"eros_log_{time.strftime('%Y%m%d-%H%M%S')}.log"
            self.log_file_handler = open(os.path.join(self.config.log_path, filename), "w")

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
    def get_color(self, value: Color):
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
        """Append text to the output text box"""

        instructions = Ansi(text.decode("utf-8")).instructions()
        packet = ""
        for instruction in instructions:
            if isinstance(instruction, str):
                if self.current_termial_color is None:
                    packet += f"<span>{instruction}</span>"
                else:
                    packet += f"<span style='color: {self.current_termial_color}'>{instruction}</span>"

                if self.log_file_handler is not None:
                    self.log_file_handler.write(instruction.replace("<br>", ""))

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

    def append_unidentified_text_to_output(self, data_raw: bytes):
        # Here we want to sanitize the data, so its nice and printable
        # This can contain any bytes, more effor is needed

        # Remove zero bytes
        data_raw = data_raw.replace(b"\x00", b"")

        # Don't print empty packets
        if len(data_raw) == 0:
            return

        # Decode the data, ignore errors
        data = data_raw.decode("utf-8", errors="ignore")

        # Add line breaks
        data = data.replace("\n", "<br>")

        # Add the data to the output
        self.append_text_to_output(data.encode())

    def set_eros_handle(self, eros: Eros):
        self.eros_handle = eros

        for channel in self.config.channels:
            self.eros_handle.attach_channel_callback(channel, self.append_text_to_output)

        if self.config.log_unidentified:
            self.eros_handle.attach_fail_callback(self.append_unidentified_text_to_output)

    def status_update_callback(self, status: TransportStates):
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


class LoggerConfigWidget(QGenericSettingsWidget):
    STORAGE_NAME = "eros_logger"

    class Model(BaseModel):
        log_unidentified: bool = False
        max_line_history: int = 200
        channels: List[int] = [1]
        log_path: str = os.path.expanduser("~/Desktop/")
        enable_file_logging: bool = False

    def __init__(self) -> None:
        super().__init__()

        # add checkbox to enable/disable logging
        self.log_unidentified_checkbox = QCheckBox("Log unidentified packets")

        #  Add a listview to select which channel to log
        self.log_channel_list = QListWidget()
        for i in range(0, 16):
            self.log_channel_list.addItem(str(i))
        self.log_channel_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        self.max_line_history_input = QSpinBox()
        self.max_line_history_input.setMinimum(10)
        self.max_line_history_input.setMaximum(1000)

        # Enable logging to file
        self.enable_file_logging_input = QCheckBox("Enable file logging")

        self.log_path_input = QLineEdit()
        select_folder_action = QAction(self)
        select_folder_action.triggered.connect(self.query_folder)
        select_folder_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.log_path_input.addAction(select_folder_action, QLineEdit.ActionPosition.TrailingPosition)

        # Set the layout
        self._layout = QFormLayout()
        self._layout.addWidget(self.log_unidentified_checkbox)
        self._layout.addRow("Max Lines to show", self.max_line_history_input)
        self._layout.addRow("Log Channels", self.log_channel_list)

        self._layout.addWidget(self.enable_file_logging_input)
        self._layout.addRow("Log Path", self.log_path_input)

        self.setLayout(self._layout)

        # Connect the signals so that the settings are saved
        self.log_unidentified_checkbox.stateChanged.connect(self._on_value_changed)
        self.log_channel_list.itemSelectionChanged.connect(self._on_value_changed)
        self.max_line_history_input.valueChanged.connect(self._on_value_changed)
        self.log_path_input.textChanged.connect(self._on_value_changed)
        self.enable_file_logging_input.stateChanged.connect(self._on_value_changed)

    def query_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory", self.log_path_input.text())

        if path is None or path == "":
            return

        self.log_path_input.setText(path)

    @property
    def data(self) -> Model:
        selected_channels = self.log_channel_list.selectedItems()
        return self.Model(
            log_unidentified=self.log_unidentified_checkbox.isChecked(),
            max_line_history=self.max_line_history_input.value(),
            channels=[int(channel.text()) for channel in selected_channels],
            log_path=self.log_path_input.text(),
            enable_file_logging=self.enable_file_logging_input.isChecked(),
        )

    @data.setter
    def data(self, value: Model):
        self.log_unidentified_checkbox.setChecked(value.log_unidentified)
        self.max_line_history_input.setValue(value.max_line_history)
        self.log_channel_list.clearSelection()
        for channel in value.channels:
            self.log_channel_list.item(channel).setSelected(True)

        self.log_path_input.setText(value.log_path)
        self.enable_file_logging_input.setChecked(value.enable_file_logging)
