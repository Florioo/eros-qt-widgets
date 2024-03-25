import threading
from queue import Queue

from eros_core import CLIResponse, CommandFrame, Eros, ResponseType, TransportStates
from pydantic import BaseModel
from qt_settings import QGenericSettingsWidget
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QContextMenuEvent, QFont, QGuiApplication
from qtpy.QtWidgets import (
    QDockWidget,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QScrollBar,
    QSpinBox,
    QWidget,
)
from termqt.terminal_widget import Terminal  # type: ignore

COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RESET = "\033[0m"


class QErosTerminalWidget(QDockWidget):
    eros_handle: Eros | None = None

    background_color = QColor(40, 40, 40)

    def __init__(self, parent, config_widget: "ErosTerminalConfigWidget", font: QFont) -> None:
        super().__init__("Eros Terminal", parent)

        self.receive_queue = Queue()

        self.config = config_widget.data

        self.terminal = Terminal(
            width=200,
            height=200,
            font_size=font.pointSize(),
            padding=10,
            line_height_factor=1.1,
        )

        self.scrollbar = QScrollBar(Qt.Orientation.Vertical, self.terminal)

        self.terminal.connect_scroll_bar(self.scrollbar)
        self.terminal.enable_auto_wrap(True)
        self.terminal.set_font(font)
        self.terminal.set_bg(self.background_color)
        self.terminal.stdin_callback = self.eros_transmit_handler  # type: ignore
        self.terminal.maximum_line_history = self.config.max_line_history

        self.disconnect_label = QLabel("Terminal Disconnected")
        self.disconnect_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.disconnect_label.setStyleSheet(
            "QLabel { font-size: 20px; background-color: " + self.background_color.name() + "; color: white; }"
        )

        layout = QHBoxLayout()  # Set the layout to the QWidget instance
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

    def set_eros_handle(self, eros: Eros):
        self.eros_handle = eros
        self.eros_handle.attach_channel_callback(self.config.aux_channel, self.receive_queue.put)
        self.eros_respone = CLIResponse(self.eros_handle, self.config.main_channel, self.eros_receive_handler)  # type: ignore

    def eros_transmit_handler(self, data):
        if self.eros_handle is not None:
            self.eros_handle.transmit_packet(self.config.main_channel, bytes(data))

    def async_termimal_writer(self):
        while True:
            # Group the data in the buffer
            buffer = self.receive_queue.get()

            while not self.receive_queue.empty():
                buffer = buffer + self.receive_queue.get()

            # Write to terminal
            self.terminal.stdout(buffer)

    def contextMenuEvent(self, event: QContextMenuEvent):
        """Overrides the default context menu event to add a paste option. on right click"""
        if event.reason() == QContextMenuEvent.Reason.Mouse:
            clipboard = QGuiApplication.clipboard()
            self.eros_transmit_handler(clipboard.text().encode())

        super().contextMenuEvent(event)

    def eros_receive_handler(self, packet: CommandFrame):
        if packet.resp_type == ResponseType.NACK:
            if len(packet.data):
                ret = f"{COLOR_RED}Error: {packet.data.decode()}{COLOR_RESET}\n"
            else:
                ret = f"{COLOR_RED}Error{COLOR_RESET}\n"
        else:
            if len(packet.data):
                ret = f"{packet.data.decode()}\n"
            else:
                ret = f"{COLOR_GREEN}OK{COLOR_RESET}\n"

        self.receive_queue.put(ret.encode())

    def status_update_callback(self, status: TransportStates):
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


class ErosTerminalConfigWidget(QGenericSettingsWidget):
    STORAGE_NAME = "eros_terminal"

    class Model(BaseModel):
        main_channel: int = 5
        aux_channel: int = 6
        max_line_history: int = 200

    def __init__(self) -> None:
        super().__init__()

        # Create the inputs
        self.main_channel_input = QSpinBox()
        self.main_channel_input.setMinimum(0)
        self.main_channel_input.setMaximum(15)

        self.aux_channel_input = QSpinBox()
        self.aux_channel_input.setMinimum(0)
        self.aux_channel_input.setMaximum(15)

        self.max_line_history_input = QSpinBox()
        self.max_line_history_input.setMinimum(10)
        self.max_line_history_input.setMaximum(1000)

        # Set the layout
        self._layout = QFormLayout()
        self._layout.addRow("Main Channel", self.main_channel_input)
        self._layout.addRow("Aux Channel", self.aux_channel_input)
        self._layout.addRow("Max Line History", self.max_line_history_input)
        self.setLayout(self._layout)

        # Save the settings when the inputs change
        self.main_channel_input.valueChanged.connect(self._on_value_changed)
        self.aux_channel_input.valueChanged.connect(self._on_value_changed)
        self.max_line_history_input.valueChanged.connect(self._on_value_changed)

    @property
    def data(self) -> Model:
        return ErosTerminalConfigWidget.Model(
            main_channel=self.main_channel_input.value(),
            aux_channel=self.aux_channel_input.value(),
            max_line_history=self.max_line_history_input.value(),
        )

    @data.setter
    def data(self, config: Model):
        self.main_channel_input.setValue(config.main_channel)
        self.aux_channel_input.setValue(config.aux_channel)
        self.max_line_history_input.setValue(config.max_line_history)
