# -*- coding: utf-8 -*-
# @Time    : 2025/3/11 16:15
# @Author  : liziye
# @FileName: Sta_GUI.py
# @Software: PyCharm
# @E-mail  : 937887153@qq.com
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from Function1 import EarthquakeApp
from Function2 import StationDistanceWidget
from Function3 import StationApp

class CombinedApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能台站布设系统")
        self.setGeometry(200, 100, 1200, 800)

        self.initUI()

    def initUI(self):
        tab_widget = QTabWidget()

        # 统一三个模块的风格和布局
        self.earthquake_tab = EarthquakeApp()
        self.distance_tab = StationDistanceWidget()
        self.station_tab = StationApp()

        tab_widget.addTab(self.earthquake_tab, "台站距离筛选模块")
        tab_widget.addTab(self.distance_tab, "台站自检查模块")
        tab_widget.addTab(self.station_tab, "台站生成模块")

        # 统一外观
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #C4C4C4;
                background-color: #F5F5F5;
            }
            QTabBar::tab {
                background: #E0E0E0;
                padding: 10px;
                border: 1px solid #C4C4C4;
                border-bottom-color: #C4C4C4;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                border-bottom: 2px solid #0078D7;
            }
        """)

        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(tab_widget)
        container.setLayout(layout)

        self.setCentralWidget(container)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CombinedApp()
    window.show()
    sys.exit(app.exec())
