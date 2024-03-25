import json
import os
import time
from typing import List

from eros_core import Eros, TransportStates
from pydantic import BaseModel
from qt_settings import QGenericSettingsWidget
from qtpy.QtCore import QSettings, Qt, QTimer, Signal
from qtpy.QtGui import QAction, QFont
from qtpy.QtWidgets import (
    QCheckBox,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from .data_output import CSVOutput, UDPOutput
from .dockable_graph import QGraphWidget
from .ui.eros_trace import Ui_Form


class QErosTraceWidget(QDockWidget):
    eros_handle: Eros | None = None

    data_signal = Signal(bytes)
    last_update = time.time()

    csv_output: CSVOutput

    def __init__(self, parent, config_widget: "QErosTraceConfigWidget", settings: QSettings) -> None:
        super().__init__("Eros Trace", parent, objectName="eros_trace_widget")  # type: ignore

        self.main_widget = QWidget()
        self.config = config_widget.data
        self.graphs: List[QGraphWidget] = []
        self.settings = settings

        self.csv_output = CSVOutput()
        self.udp_output = UDPOutput()
        self.start_time = time.time()

        self.ui = Ui_Form()
        self.ui.setupUi(self.main_widget)

        # Configure the table
        self.ui.data_viewer.setAlternatingRowColors(True)
        self.ui.data_viewer.setWordWrap(True)
        self.ui.data_viewer.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)

        # Set the headers
        self.ui.data_viewer.setHeaderLabels(["Key", "Value"])
        self.ui.logger_btn.clicked.connect(self.toggle_csv_logging)
        self.ui.udp_btn.clicked.connect(self.toggle_udp_output)
        self.ui.plotter_btn.clicked.connect(self.create_plotter)
        self.ui.clear_btn.clicked.connect(lambda: self.ui.data_viewer.clear())

        # Set central widget
        self.setWidget(self.main_widget)
        self.data_signal.connect(self.update_table)

        # start update timer
        self.update_timer = QTimer(singleShot=False, interval=100)  # type: ignore
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start()

        self.load_config()

        if self.config.udp_auto_start:
            self.toggle_udp_output()

    def update_table(self, text_raw: bytes):
        """Append text to the output text box"""
        text = text_raw.decode("utf-8")
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

        for key, value in obj.items():
            # find the item in the list
            items = self.ui.data_viewer.findItems(key, Qt.MatchFlag.MatchExactly)

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
        if not self.csv_output.is_open():
            self.csv_output.open(self.config.csv_path, skip_every_n_lines=0)
        else:
            self.csv_output.close()

    def toggle_udp_output(self):
        if not self.udp_output.is_open():
            self.udp_output.open(self.config.udp_ip, self.config.udp_port)
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

        dockable_widget = QGraphWidget(
            id=next_id,
            columns=[item.text(0) for item in selected_items],
            index="time",
            max_points=self.config.max_point_history,
            max_update_rate=self.config.max_update_rate,
        )

        self.parent().addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dockable_widget)  # type: ignore

        self.graphs.append(dockable_widget)

    def update_ui(self):
        status_string = ""
        if self.udp_output.is_open():
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

    def set_eros_handle(self, eros: Eros):
        self.eros_handle = eros
        self.eros_handle.attach_channel_callback(self.config.trace_channel, self.data_signal.emit)

    def status_update_callback(self, status: TransportStates):
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
        assert isinstance(widgets, list)

        for widget_config in widgets:
            dockable_widget = QGraphWidget.from_dict(widget_config)
            if dockable_widget is None:
                continue
            self.parent().addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dockable_widget)  # type: ignore
            self.graphs.append(dockable_widget)


class QErosTraceConfigWidget(QGenericSettingsWidget):
    class Model(BaseModel):
        udp_ip: str = "127.0.0.1"
        udp_port: int = 1234
        csv_path: str = os.path.expanduser("~/Desktop/")
        trace_channel: int = 10
        max_point_history: int = 5000
        max_update_rate: float = 15
        udp_auto_start: bool = False

    def __init__(self) -> None:
        super().__init__()

        self.trace_channel_input = QSpinBox()
        self.trace_channel_input.setMinimum(0)
        self.trace_channel_input.setMaximum(16)

        self.udp_ip_input = QLineEdit()

        self.udp_port_input = QSpinBox()
        self.udp_port_input.setMinimum(0)
        self.udp_port_input.setMaximum(65535)

        self.udp_auto_start_input = QCheckBox("Auto start")

        self.csv_path_input = QLineEdit()

        select_folder_action = QAction(self)
        select_folder_action.triggered.connect(self.query_folder)
        select_folder_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.csv_path_input.addAction(select_folder_action, QLineEdit.ActionPosition.TrailingPosition)

        self.max_point_history_input = QSpinBox()
        self.max_point_history_input.setMinimum(0)
        self.max_point_history_input.setMaximum(10000)

        self.max_update_rate_input = QDoubleSpinBox()
        self.max_update_rate_input.setMinimum(0.1)
        self.max_update_rate_input.setMaximum(20)

        font = QFont()
        font.setUnderline(True)

        # Set the layout
        self._layout = QFormLayout()
        self._layout.addRow("Trace Channel", self.trace_channel_input)
        # Add a label on the first column, which contains underlined text "UDP Settings"

        self._layout.addRow(QLabel("UDP Settings", font=font))  # type: ignore
        self._layout.addRow("UDP IP", self.udp_ip_input)
        self._layout.addRow("UDP Port", self.udp_port_input)
        self._layout.addWidget(self.udp_auto_start_input)

        self._layout.addRow(QLabel("CSV Settings", font=font))  # type: ignore
        self._layout.addRow("Path", self.csv_path_input)

        self._layout.addRow(QLabel("Plot settings", font=font))  # type: ignore
        self._layout.addRow("Max points", self.max_point_history_input)
        self._layout.addRow("Max update rate", self.max_update_rate_input)

        self.setLayout(self._layout)

        self.udp_ip_input.textChanged.connect(self._on_value_changed)
        self.udp_port_input.valueChanged.connect(self._on_value_changed)
        self.csv_path_input.textChanged.connect(self._on_value_changed)
        self.trace_channel_input.valueChanged.connect(self._on_value_changed)
        self.max_point_history_input.valueChanged.connect(self._on_value_changed)
        self.max_update_rate_input.valueChanged.connect(self._on_value_changed)
        self.udp_auto_start_input.stateChanged.connect(self._on_value_changed)

    def query_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory", self.csv_path_input.text())

        if path is None or path == "":
            return

        self.csv_path_input.setText(path)

    @property
    def data(self) -> Model:
        return QErosTraceConfigWidget.Model(
            udp_ip=self.udp_ip_input.text(),
            udp_port=self.udp_port_input.value(),
            csv_path=self.csv_path_input.text(),
            trace_channel=self.trace_channel_input.value(),
            max_point_history=self.max_point_history_input.value(),
            max_update_rate=self.max_update_rate_input.value(),
            udp_auto_start=self.udp_auto_start_input.isChecked(),
        )

    @data.setter
    def data(self, config: Model):
        self.udp_ip_input.setText(config.udp_ip)
        self.udp_port_input.setValue(config.udp_port)
        self.csv_path_input.setText(config.csv_path)
        self.trace_channel_input.setValue(config.trace_channel)
        self.max_point_history_input.setValue(config.max_point_history)
        self.max_update_rate_input.setValue(config.max_update_rate)
        self.udp_auto_start_input.setChecked(config.udp_auto_start)
