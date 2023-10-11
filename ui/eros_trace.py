# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'eros_trace.ui'
##
## Created by: Qt User Interface Compiler version 6.5.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(784, 801)
        font = QFont()
        font.setPointSize(11)
        Form.setFont(font)
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.frame = QFrame(Form)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.udp_btn = QPushButton(self.frame)
        self.udp_btn.setObjectName(u"udp_btn")
        self.udp_btn.setMaximumSize(QSize(100, 16777215))

        self.horizontalLayout.addWidget(self.udp_btn)

        self.logger_btn = QPushButton(self.frame)
        self.logger_btn.setObjectName(u"logger_btn")
        self.logger_btn.setMaximumSize(QSize(100, 16777215))

        self.horizontalLayout.addWidget(self.logger_btn)

        self.plotter_btn = QPushButton(self.frame)
        self.plotter_btn.setObjectName(u"plotter_btn")
        self.plotter_btn.setMaximumSize(QSize(150, 16777215))

        self.horizontalLayout.addWidget(self.plotter_btn)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.verticalLayout.addWidget(self.frame)

        self.label = QLabel(Form)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setFamilies([u"Courier New"])
        font1.setPointSize(9)
        self.label.setFont(font1)

        self.verticalLayout.addWidget(self.label)

        self.data_viewer = QTreeWidget(Form)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.data_viewer.setHeaderItem(__qtreewidgetitem)
        self.data_viewer.setObjectName(u"data_viewer")
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.data_viewer.sizePolicy().hasHeightForWidth())
        self.data_viewer.setSizePolicy(sizePolicy)

        self.verticalLayout.addWidget(self.data_viewer)

        self.frame_2 = QFrame(Form)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_2)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.clear_btn = QPushButton(self.frame_2)
        self.clear_btn.setObjectName(u"clear_btn")
        self.clear_btn.setMaximumSize(QSize(100, 16777215))

        self.horizontalLayout_2.addWidget(self.clear_btn)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)


        self.verticalLayout.addWidget(self.frame_2)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.udp_btn.setText(QCoreApplication.translate("Form", u"Start udp", None))
        self.logger_btn.setText(QCoreApplication.translate("Form", u"Start logger", None))
        self.plotter_btn.setText(QCoreApplication.translate("Form", u"Graph selected", None))
        self.label.setText(QCoreApplication.translate("Form", u"TextLabel", None))
        self.clear_btn.setText(QCoreApplication.translate("Form", u"Clear list", None))
    # retranslateUi

