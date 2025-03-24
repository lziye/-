import sys
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QVBoxLayout,
    QPushButton, QWidget, QTableWidget, QTableWidgetItem,
    QSpinBox, QLabel, QHBoxLayout, QHeaderView, QCheckBox, QSplitter, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
import folium
from io import BytesIO
import math

# 地球半径（用于距离计算）
EARTH_RADIUS = 6371

class EarthquakeApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.yiban = None
        self.jizhun = None
        self.jiben = None
        self.sifen = None
        self.filtered_sifen = None
        self.use_satellite = False  # 默认使用2D地图
        self.moved_markers = {}  # 用于存储移动后的标记位置

        self.setWindowTitle("台站距离筛选模块")
        self.setGeometry(200, 100, 1200, 700)

        self.initUI()

    def initUI(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout()

        # 地图窗口
        self.map_view = QWebEngineView()
        left_layout.addWidget(self.map_view)

        # 复选框设置
        check_layout = QHBoxLayout()
        self.show_yiban = QCheckBox("显示一般站")
        self.show_jizhun = QCheckBox("显示基准站")
        self.show_jiben = QCheckBox("显示基本站")
        self.show_sifen = QCheckBox("显示预建设台站")

        self.show_yiban.setChecked(True)
        self.show_jizhun.setChecked(True)
        self.show_jiben.setChecked(True)
        self.show_sifen.setChecked(True)

        self.show_yiban.stateChanged.connect(self.update_map)
        self.show_jizhun.stateChanged.connect(self.update_map)
        self.show_jiben.stateChanged.connect(self.update_map)
        self.show_sifen.stateChanged.connect(self.update_map)

        check_layout.addWidget(self.show_yiban)
        check_layout.addWidget(self.show_jizhun)
        check_layout.addWidget(self.show_jiben)
        check_layout.addWidget(self.show_sifen)
        left_layout.addLayout(check_layout)

        # 切换地图类型按钮
        self.toggle_map_btn = QPushButton("切换为实景地图")
        self.toggle_map_btn.clicked.connect(self.toggle_map)
        left_layout.addWidget(self.toggle_map_btn)

        # 下载新位置坐标按钮
        self.download_btn = QPushButton("下载新位置坐标")
        self.download_btn.clicked.connect(self.download_new_coords)
        left_layout.addWidget(self.download_btn)

        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)

        # 右侧功能区
        right_widget = QWidget()
        right_layout = QVBoxLayout()

        # 文件加载区域
        file_layout = QHBoxLayout()
        self.yiban_btn = QPushButton("选择一般站文件")
        self.jizhun_btn = QPushButton("选择基准站文件")
        self.jiben_btn = QPushButton("选择基本站文件")
        self.sifen_btn = QPushButton("选择预建设台站文件")

        file_layout.addWidget(self.yiban_btn)
        file_layout.addWidget(self.jizhun_btn)
        file_layout.addWidget(self.jiben_btn)
        file_layout.addWidget(self.sifen_btn)

        self.yiban_btn.clicked.connect(self.load_yiban)
        self.jizhun_btn.clicked.connect(self.load_jizhun)
        self.jiben_btn.clicked.connect(self.load_jiben)
        self.sifen_btn.clicked.connect(self.load_sifen)

        right_layout.addLayout(file_layout)

        # 筛选功能
        filter_layout = QHBoxLayout()
        self.distance_label = QLabel("最大筛选距离(km)：")
        self.distance_input = QSpinBox()
        self.distance_input.setRange(0, 1000)
        self.distance_input.setValue(5)

        self.filter_btn = QPushButton("筛选")
        self.filter_btn.clicked.connect(self.filter_data)

        filter_layout.addWidget(self.distance_label)
        filter_layout.addWidget(self.distance_input)
        filter_layout.addWidget(self.filter_btn)
        right_layout.addLayout(filter_layout)

        # 结果表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["预建设台站", "已建设台站", "相近距离 (km)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.table)

        # 保存按钮
        self.save_btn = QPushButton("保存结果")
        self.save_btn.clicked.connect(self.save_results)
        right_layout.addWidget(self.save_btn)



        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1500, 500])

        self.setCentralWidget(splitter)

        # 初始化地图
        self.update_map()

    # ========== 切换地图类型 ==========
    def toggle_map(self):
        self.use_satellite = not self.use_satellite
        if self.use_satellite:
            self.toggle_map_btn.setText("切换为2D地图")
        else:
            self.toggle_map_btn.setText("切换为实景地图")
        self.update_map()

    # ========== 更新地图 ==========
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


        # 显示一般站
        if self.yiban is not None and self.show_yiban.isChecked():
            for _, row in self.yiban.iterrows():
                folium.Marker(
                    location=[row['纬度'], row['经度']],
                    popup=row['站点名称'],
                    icon=folium.Icon(color="blue", icon="info-sign")
                ).add_to(m)

        # 显示基准站
        if self.jizhun is not None and self.show_jizhun.isChecked():
            for _, row in self.jizhun.iterrows():
                folium.Marker(
                    location=[row['纬度'], row['经度']],
                    popup=row['站点名称'],
                    icon=folium.Icon(color="red", icon="flag")
                ).add_to(m)

        # 显示基本站
        if self.jiben is not None and self.show_jiben.isChecked():
            for _, row in self.jiben.iterrows():
                folium.Marker(
                    location=[row['纬度'], row['经度']],
                    popup=row['站点名称'],
                    icon=folium.Icon(color="green", icon="home")
                ).add_to(m)

        # 显示预建设台站（仅显示筛选后的）
        if self.show_sifen.isChecked() and self.filtered_sifen is not None:
            for _, row in self.filtered_sifen.iterrows():
                marker = folium.Marker(
                    location=[row['纬度'], row['经度']],
                    popup=row['站点名称'],
                    icon=folium.Icon(color="purple", icon="cloud"),
                    draggable=True
                )
                marker.add_to(m)
                # 绑定拖动事件
                marker.add_child(folium.ClickForMarker(popup=f"台站: {row['站点名称']}"))
                marker.add_child(folium.LatLngPopup())
                self.moved_markers[row['站点名称']] = marker

        # 保存地图为 HTML，并替换完整性校验字段
        data = BytesIO()
        m.save(data, close_file=False)
        html = data.getvalue().decode()
        self.map_view.setHtml(html)

    # ========== 筛选功能 ==========
    def filter_data(self):
        if self.sifen is None or self.yiban is None:
            return

        max_distance = self.distance_input.value()
        results = []
        filtered_rows = []

        for _, row in self.sifen.iterrows():
            lat, lon = row['纬度'], row['经度']
            closest_station, min_distance = self.find_closest_station(lat, lon, self.yiban)
            if min_distance <= max_distance:
                results.append([row['站点名称'], closest_station, round(min_distance, 2)])
                filtered_rows.append(row)

        self.filtered_sifen = pd.DataFrame(filtered_rows)
        self.update_table(results)
        self.update_map()

    # ========== 文件加载模块 ==========
    def load_yiban(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择一般站文件", "", "Excel Files (*.xlsx)")
        if file_path:
            try:
                self.yiban = pd.read_excel(file_path)
                QMessageBox.information(self, "加载成功", "一般站文件加载成功！")  # 显示成功提示框
                self.update_map()
            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"一般站文件加载失败: {e}")

    def load_jizhun(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择基准站文件", "", "Excel Files (*.xlsx)")
        if file_path:
            try:
                self.jizhun = pd.read_excel(file_path)
                QMessageBox.information(self, "加载成功", "一般站文件加载成功！")  # 显示成功提示框
                self.update_map()
            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"一般站文件加载失败: {e}")

    def load_jiben(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择基本站文件", "", "Excel Files (*.xlsx)")
        if file_path:
            try:
                self.jiben = pd.read_excel(file_path)
                QMessageBox.information(self, "加载成功", "一般站文件加载成功！")  # 显示成功提示框
                self.update_map()
            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"一般站文件加载失败: {e}")

    def load_sifen(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择预建设台站文件", "", "Excel Files (*.xlsx)")
        if file_path:
            try:
                self.sifen = pd.read_excel(file_path)
                QMessageBox.information(self, "加载成功", "一般站文件加载成功！")  # 显示成功提示框
                self.update_map()
            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"一般站文件加载失败: {e}")

    def find_closest_station(self, lat, lon, stations):
        min_distance = float('inf')
        closest_station = ""
        for _, row in stations.iterrows():
            distance = self.haversine_distance(lat, lon, row['纬度'], row['经度'])
            if distance < min_distance:
                min_distance = distance
                closest_station = row['站点名称']
        return closest_station, min_distance

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.asin(math.sqrt(a))
        return EARTH_RADIUS * c

    def update_table(self, results):
        self.table.setRowCount(len(results))
        for i, row in enumerate(results):
            for j, value in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(value)))

    def save_results(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "保存结果", "", "Excel Files (*.xlsx)")
        if file_path:
            data = []
            for row in range(self.table.rowCount()):
                data.append([self.table.item(row, col).text() for col in range(self.table.columnCount())])
            pd.DataFrame(data, columns=["预建设台站", "已建设台站", "相近距离 (km)"]).to_excel(file_path, index=False)

    def download_new_coords(self):
        if not self.moved_markers:
            self.statusBar().showMessage("没有移动的台站", 3000)
            return

        data = []
        for name, marker in self.moved_markers.items():
            lat, lon = marker.location
            data.append([name, lat, lon])

        file_path, _ = QFileDialog.getSaveFileName(self, "保存新位置坐标", "", "Excel Files (*.xlsx)")
        if file_path:
            pd.DataFrame(data, columns=["台站名称", "纬度", "经度"]).to_excel(file_path, index=False)
            self.statusBar().showMessage("新位置坐标保存成功", 3000)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EarthquakeApp()
    window.show()
    sys.exit(app.exec())