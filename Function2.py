import sys
import pandas as pd
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QVBoxLayout, QPushButton, QWidget, QTableWidget, QTableWidgetItem, QSpinBox, QLabel, QHBoxLayout, QHeaderView, QSplitter, QCheckBox, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
import folium
from io import BytesIO
from math import radians, sin, cos, sqrt, asin
import itertools

EARTH_RADIUS = 6371

class DistanceCalculator:
    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        return EARTH_RADIUS * c

class StationDistanceWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.stations = None
        self.filtered_results = []
        self.moved_markers = {}  # 初始化 moved_markers
        self.use_satellite = False  # 默认使用2D地图
        self.initUI()

    def initUI(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout()

        self.map_view = QWebEngineView()
        left_layout.addWidget(self.map_view)

        check_layout = QHBoxLayout()
        self.show_stations = QCheckBox("显示筛选结果")
        self.show_stations.setChecked(True)
        self.show_stations.stateChanged.connect(self.update_map)
        check_layout.addWidget(self.show_stations)

        left_layout.addLayout(check_layout)

        # 切换地图类型按钮
        self.toggle_map_btn = QPushButton("切换为实景地图")
        self.toggle_map_btn.clicked.connect(self.toggle_map)
        left_layout.addWidget(self.toggle_map_btn)

        self.download_btn = QPushButton("下载新位置坐标")
        self.download_btn.clicked.connect(self.download_new_coords)
        left_layout.addWidget(self.download_btn)

        left_widget.setLayout(left_layout)

        right_widget = QWidget()
        right_layout = QVBoxLayout()

        file_layout = QHBoxLayout()
        self.load_btn = QPushButton("选择台站文件")
        file_layout.addWidget(self.load_btn)
        self.load_btn.clicked.connect(self.load_stations)
        right_layout.addLayout(file_layout)

        filter_layout = QHBoxLayout()
        self.distance_input = QSpinBox()
        self.distance_input.setRange(0, 1000)
        self.distance_input.setValue(5)
        self.filter_btn = QPushButton("筛选")
        self.filter_btn.clicked.connect(self.filter_data)

        filter_layout.addWidget(QLabel("最大筛选距离(km):"))
        filter_layout.addWidget(self.distance_input)
        filter_layout.addWidget(self.filter_btn)

        right_layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["预建设台站A", "预建设台站B", "最小距离(km)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.table)

        # 保存按钮
        self.save_btn = QPushButton("保存结果")
        self.save_btn.clicked.connect(self.save_results)
        right_layout.addWidget(self.save_btn)

        right_widget.setLayout(right_layout)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1500, 500])

        layout = QVBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)

        self.update_map()

    def load_stations(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择台站文件", "", "Excel Files (*.xlsx)")
        if file_path:
            try:
                self.stations = pd.read_excel(file_path)
                if not {'站点名称', '纬度', '经度'}.issubset(self.stations.columns):
                    raise ValueError("文件缺少必要的列")
                self.update_map()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载文件失败: {e}")

    def filter_data(self):
        if self.stations is None:
            QMessageBox.warning(self, "警告", "请先加载台站文件！")
            return

        max_distance = self.distance_input.value()
        self.filtered_results = []

        pairs = itertools.combinations(self.stations.index, 2)
        for i, j in pairs:
            row1 = self.stations.loc[i]
            row2 = self.stations.loc[j]
            if row1['站点名称'] != row2['站点名称']:  # 站点名称不相等时才筛选
                distance = DistanceCalculator.haversine_distance(row1['纬度'], row1['经度'], row2['纬度'], row2['经度'])
                if distance <= max_distance:
                    self.filtered_results.append([row1['站点名称'], row2['站点名称'], round(distance, 2)])

        self.display_results(self.filtered_results)
        self.update_map()  # **筛选成功后刷新地图**

    def display_results(self, results):
        self.table.setRowCount(len(results))
        for i, row in enumerate(results):
            for j, value in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(value)))

    # ========== 切换地图类型 ==========
    def toggle_map(self):
        self.use_satellite = not self.use_satellite
        if self.use_satellite:
            self.toggle_map_btn.setText("切换为2D地图")
        else:
            self.toggle_map_btn.setText("切换为实景地图")
        self.update_map()


    def update_map(self):
        if self.use_satellite:
            m = folium.Map(
                location=[35, 105],
                zoom_start=5,
                tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
                attr="Google"
            )
        else:
            m = folium.Map(location=[35, 105], zoom_start=5, tiles="OpenStreetMap")

        # 添加鼠标位置显示
        from folium.plugins import MousePosition
        MousePosition(position="bottomleft", separator=" | ", empty_string="No coordinates").add_to(m)

        if self.filtered_results and self.show_stations.isChecked():
            for station_a, station_b, _ in self.filtered_results:
                row_a = self.stations.loc[self.stations['站点名称'] == station_a].iloc[0]
                row_b = self.stations.loc[self.stations['站点名称'] == station_b].iloc[0]

                marker_a = folium.Marker(
                    location=[row_a['纬度'], row_a['经度']],
                    popup=row_a['站点名称'],
                    draggable=True
                )
                marker_a.add_to(m)
                self.moved_markers[row_a['站点名称']] = marker_a

                marker_b = folium.Marker(
                    location=[row_b['纬度'], row_b['经度']],
                    popup=row_b['站点名称'],
                    draggable=True
                )
                marker_b.add_to(m)
                self.moved_markers[row_b['站点名称']] = marker_b

        data = BytesIO()
        m.save(data, close_file=False)
        html = data.getvalue().decode()
        self.map_view.setHtml(html)

    def save_results(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "保存结果", "", "Excel Files (*.xlsx)")
        if file_path:
            data = []
            for row in range(self.table.rowCount()):
                data.append([self.table.item(row, col).text() for col in range(self.table.columnCount())])
            pd.DataFrame(data, columns=["预建设台站A", "预建设台站B", "相近距离 (km)"]).to_excel(file_path, index=False)

    def download_new_coords(self):
        if not self.moved_markers:
            QMessageBox.information(self, "提示", "没有移动的台站")
            return

        data = []
        for name, marker in self.moved_markers.items():
            lat, lon = marker.location
            data.append([name, lat, lon])

        file_path, _ = QFileDialog.getSaveFileName(self, "保存新位置坐标", "", "Excel Files (*.xlsx)")
        if file_path:
            pd.DataFrame(data, columns=["台站名称", "纬度", "经度"]).to_excel(file_path, index=False)
            QMessageBox.information(self, "提示", "新位置坐标保存成功")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("台站自检查模块")
        self.setGeometry(200, 100, 1200, 700)
        self.setCentralWidget(StationDistanceWidget())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())