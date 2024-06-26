import collections
import logging
import time
from typing import Dict, List

import pandas as pd
import pyqtgraph as pg
from qtpy.QtWidgets import QDockWidget


class QGraphWidget(QDockWidget):
    PLOT_COLORS = ["r", "g", "b", "c", "m", "y", "k"]
    time_index = None
    data: Dict[str, collections.deque]
    plots: Dict[str, pg.PlotDataItem]
    indexes: Dict[str, collections.deque]

    def __init__(
        self,
        id: int,
        columns: List[str],
        index="time",
        max_points=1000,
        max_update_rate: float = 1,
    ):
        super().__init__(f"Graph {id}", objectName=f"graph_dock_{id}")  # type: ignore
        self.id = id
        self.max_update_rate = max_update_rate
        self.last_update = time.time()

        self.log = logging.getLogger(f"graph {id}")

        self.plots = {}
        self.data = {}
        self.indexes = {}

        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setBackground("w")
        self.graphWidget.addLegend()

        self.setWidget(self.graphWidget)
        self.frame = pd.DataFrame(columns=columns)
        self.max_points = max_points

        # Create a circular buffer for the time index
        self.index = index

        # Create plots for each column
        for i, column in enumerate(columns):
            plot_color = self.PLOT_COLORS[i % len(self.PLOT_COLORS)]
            self.indexes[column] = collections.deque(maxlen=self.max_points)
            self.data[column] = collections.deque(maxlen=self.max_points)
            self.plots[column] = self.graphWidget.plot(pen=plot_color, name=column)

        # Add legend

    def update(self, data: Dict):
        if self.graphWidget is None:
            return

        # Add data to frame
        for key, value in data.items():
            if key in self.data:
                self.data[key].append(float(value))
                self.indexes[key].appendleft(float(data[self.index]))

        if time.time() - self.last_update < 1 / self.max_update_rate:
            return

        self.last_update = time.time()

        # Update plots
        for column in self.data.keys():
            if len(self.data[column]) == 0:
                continue

            self.plots[column].setData(list(self.indexes[column]), list(self.data[column]))

    # If closed destroy the widget
    def closeEvent(self, event):
        self.deleteLater()
        self.graphWidget = None
        self.plots = None  # type: ignore
        self.data = None  # type: ignore
        self.time_index = None
        event.accept()

    # Check if the widget is open
    def isOpen(self) -> bool:
        return self.graphWidget is not None

    def to_dict(self) -> dict:
        # Return config as a dict
        config = {}
        config["id"] = self.id
        config["columns"] = list(self.data.keys())
        config["index"] = self.index
        config["max_points"] = self.max_points
        config["max_update_rate"] = self.max_update_rate
        return config

    @classmethod
    def from_dict(cls, config: dict):
        try:
            # Load config from dict
            return QGraphWidget(
                id=config["id"],
                columns=config["columns"],
                index=config["index"],
                max_points=config["max_points"],
                max_update_rate=config["max_update_rate"],
            )
        except Exception:
            log = logging.getLogger("QGraphWidget")
            log.exception("Failed to load graph config")
            return None
