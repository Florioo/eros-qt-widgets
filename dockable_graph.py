import json
import time
import os

from PySide2.QtWidgets import  QDockWidget,QTreeWidgetItem,QWidget,QStyle
from PySide2.QtCore import Signal, Qt, QSettings,QTimer
from PySide2.QtWidgets import  QDockWidget,QLineEdit, QLabel,QWidget,QSpinBox,QFormLayout,QAction,QFileDialog
from PySide2.QtGui import QFont,QIcon

from eros_core import Eros,TransportStates
from .ui.eros_trace import Ui_Form
from .data_output import CSVOutput, UDPOutput
import pyqtgraph as pg
from typing import Dict,List

import pandas as pd
import collections
import logging

class QGraphWidget(QDockWidget):
    PLOT_COLORS = ["r", "g", "b", "c", "m", "y", "k"]
    time_index = None
    
    def __init__(self,
                 id:int,
                 columns: List[str],
                 index = "time",
                 max_points = 1000,
                 max_update_rate = 1):
        
        super().__init__(f"Graph {id}", objectName=f"graph_dock_{id}") 
        self.id = id
        self.max_update_rate = max_update_rate
        self.last_update = time.time()
        
        self.log = logging.getLogger(f"graph {id}")
        
        self.plots = {}
        self.data = {}
        
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setBackground('w')
        self.graphWidget.addLegend()
        
        self.setWidget(self.graphWidget)
        self.frame = pd.DataFrame(columns=columns)
        self.max_points = max_points
        
        #Create a circular buffer for the time index        
        if index is not None:
            self.time_index = collections.deque(maxlen=self.max_points)
            self.index = index
            
        # Create plots for each column
        for i,column in enumerate(columns):
            plot_color = self.PLOT_COLORS[i%len(self.PLOT_COLORS)]
            self.data[column] = collections.deque(maxlen=self.max_points)
            self.plots[column] = self.graphWidget.plot(pen=plot_color,
                                                       name=column)
            
        # Add legend
    def update(self, data:Dict):
        if self.graphWidget is None:
            return

        # Add data to frame
        for key,value in data.items():
            if key in self.data:
                self.data[key].append(float(value))
                
        # Update the index
        if self.time_index is not None:
            self.time_index.append(data[self.index])
            
        if self.time_index is not None:
            index = list(self.time_index)
        else:
            index = list(range(len(self.data[column])))
        
        if time.time() - self.last_update < 1/self.max_update_rate:
            return
        
        self.last_update = time.time()
        
        # Update plots
        for column in self.data.keys():
            self.plots[column].setData(index, list(self.data[column]))
    
    # If closed destroy the widget
    def closeEvent(self, event):
        self.deleteLater()
        self.graphWidget = None
        self.plots = None
        self.data = None
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
            return QGraphWidget(id = config["id"],
                                columns=config["columns"],
                                index=config["index"],
                                max_points=config["max_points"],
                                max_update_rate=config["max_update_rate"])
        except:
            log = logging.getLogger("QGraphWidget")
            log.error("Failed to load graph config")
            return None  