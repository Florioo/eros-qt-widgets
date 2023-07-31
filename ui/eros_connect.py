# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'eros_connect.ui'
##
## Created by: Qt User Interface Compiler version 6.5.1
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTabWidget, QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(250, 400)
        Form.setMaximumSize(QSize(350, 400))
        font = QFont()
        font.setPointSize(10)
        Form.setFont(font)
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tabWidget = QTabWidget(Form)
        self.tabWidget.setObjectName(u"tabWidget")
        self.uart_tab = QWidget()
        self.uart_tab.setObjectName(u"uart_tab")
        self.formLayout = QFormLayout(self.uart_tab)
        self.formLayout.setObjectName(u"formLayout")
        self.uart_device_scan = QPushButton(self.uart_tab)
        self.uart_device_scan.setObjectName(u"uart_device_scan")

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.uart_device_scan)

        self.uart_device_selector = QComboBox(self.uart_tab)
        self.uart_device_selector.setObjectName(u"uart_device_selector")
        self.uart_device_selector.setEditable(True)

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.uart_device_selector)

        self.label = QLabel(self.uart_tab)
        self.label.setObjectName(u"label")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label)

        self.uart_baud_selector = QComboBox(self.uart_tab)
        self.uart_baud_selector.addItem("")
        self.uart_baud_selector.addItem("")
        self.uart_baud_selector.addItem("")
        self.uart_baud_selector.addItem("")
        self.uart_baud_selector.setObjectName(u"uart_baud_selector")
        self.uart_baud_selector.setEditable(True)

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.uart_baud_selector)

        self.label_4 = QLabel(self.uart_tab)
        self.label_4.setObjectName(u"label_4")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label_4)

        self.tabWidget.addTab(self.uart_tab, "")
        self.tcp_tab = QWidget()
        self.tcp_tab.setObjectName(u"tcp_tab")
        self.formLayout_2 = QFormLayout(self.tcp_tab)
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.label_2 = QLabel(self.tcp_tab)
        self.label_2.setObjectName(u"label_2")

        self.formLayout_2.setWidget(0, QFormLayout.LabelRole, self.label_2)

        self.tcp_host = QLineEdit(self.tcp_tab)
        self.tcp_host.setObjectName(u"tcp_host")

        self.formLayout_2.setWidget(0, QFormLayout.FieldRole, self.tcp_host)

        self.label_3 = QLabel(self.tcp_tab)
        self.label_3.setObjectName(u"label_3")

        self.formLayout_2.setWidget(1, QFormLayout.LabelRole, self.label_3)

        self.tcp_port = QLineEdit(self.tcp_tab)
        self.tcp_port.setObjectName(u"tcp_port")

        self.formLayout_2.setWidget(1, QFormLayout.FieldRole, self.tcp_port)

        self.tabWidget.addTab(self.tcp_tab, "")

        self.verticalLayout.addWidget(self.tabWidget)

        self.connect_disconnect_btn = QPushButton(Form)
        self.connect_disconnect_btn.setObjectName(u"connect_disconnect_btn")

        self.verticalLayout.addWidget(self.connect_disconnect_btn)

        self.groupBox = QGroupBox(Form)
        self.groupBox.setObjectName(u"groupBox")
        self.formLayout_4 = QFormLayout(self.groupBox)
        self.formLayout_4.setObjectName(u"formLayout_4")
        self.status_general = QLineEdit(self.groupBox)
        self.status_general.setObjectName(u"status_general")

        self.formLayout_4.setWidget(0, QFormLayout.FieldRole, self.status_general)

        self.label_5 = QLabel(self.groupBox)
        self.label_5.setObjectName(u"label_5")

        self.formLayout_4.setWidget(2, QFormLayout.LabelRole, self.label_5)

        self.label_6 = QLabel(self.groupBox)
        self.label_6.setObjectName(u"label_6")

        self.formLayout_4.setWidget(0, QFormLayout.LabelRole, self.label_6)

        self.traffic_label = QLabel(self.groupBox)
        self.traffic_label.setObjectName(u"traffic_label")
        self.traffic_label.setMinimumSize(QSize(0, 50))
        font1 = QFont()
        font1.setFamilies([u"Courier"])
        font1.setPointSize(10)
        self.traffic_label.setFont(font1)

        self.formLayout_4.setWidget(2, QFormLayout.FieldRole, self.traffic_label)


        self.verticalLayout.addWidget(self.groupBox)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(Form)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.uart_device_scan.setText(QCoreApplication.translate("Form", u"scan", None))
        self.label.setText(QCoreApplication.translate("Form", u"Device", None))
        self.uart_baud_selector.setItemText(0, QCoreApplication.translate("Form", u"115200", None))
        self.uart_baud_selector.setItemText(1, QCoreApplication.translate("Form", u"500000", None))
        self.uart_baud_selector.setItemText(2, QCoreApplication.translate("Form", u"1000000", None))
        self.uart_baud_selector.setItemText(3, QCoreApplication.translate("Form", u"2000000", None))

        self.uart_baud_selector.setCurrentText(QCoreApplication.translate("Form", u"115200", None))
        self.label_4.setText(QCoreApplication.translate("Form", u"Baud", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.uart_tab), QCoreApplication.translate("Form", u"UART", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"Host", None))
        self.label_3.setText(QCoreApplication.translate("Form", u"Port", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tcp_tab), QCoreApplication.translate("Form", u"TCP", None))
        self.connect_disconnect_btn.setText(QCoreApplication.translate("Form", u"Connect", None))
        self.groupBox.setTitle(QCoreApplication.translate("Form", u"Status", None))
        self.label_5.setText(QCoreApplication.translate("Form", u"Traffic", None))
        self.label_6.setText(QCoreApplication.translate("Form", u"Status", None))
        self.traffic_label.setText(QCoreApplication.translate("Form", u"Traffic", None))
    # retranslateUi

