import sys
import math
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QWidget, QTableWidget, QTableWidgetItem,
    QSpinBox, QHeaderView, QFileDialog, QSplitter, QMessageBox
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt
from io import BytesIO
import folium
from folium import Map, Marker, Icon
from folium.plugins import MarkerCluster
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon, Point
import numpy as np

EARTH_RADIUS = 6371  # 地球半径（km）

class StationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("台站生成模块")
        self.setGeometry(100, 100, 1200, 800)
        self.moved_markers = {}  # 初始化 moved_markers
        self.use_satellite = False  # 默认使用2D地图
        self.polygon_points = None
        self.fault_lines = []  # 存储断裂带数据
        self.initUI()

    def initUI(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ========== 左侧界面 ========== #
        left_widget = QWidget()
        left_layout = QVBoxLayout()

        # 地图
        self.map_view = QWebEngineView()
        left_layout.addWidget(self.map_view)

        # 切换地图类型按钮
        self.toggle_map_btn = QPushButton("切换为实景地图")
        self.toggle_map_btn.clicked.connect(self.toggle_map)
        left_layout.addWidget(self.toggle_map_btn)

        # 下载新位置坐标按钮
        self.download_btn = QPushButton("下载新位置坐标")
        self.download_btn.clicked.connect(self.download_new_coords)
        left_layout.addWidget(self.download_btn)

        # 导入断裂带按钮
        self.import_fault_btn = QPushButton("导入断裂带文件")
        self.import_fault_btn.clicked.connect(self.load_fault_data)
        left_layout.addWidget(self.import_fault_btn)

        left_widget.setLayout(left_layout)

        # ========== 右侧界面 ========== #
        right_widget = QWidget()
        right_layout = QVBoxLayout()

        # 示例坐标（示例为中国中部四边形）
        default_coords = [
            (31.77, 118.24),
            (31.77, 120.34),
            (33.20, 118.24),
            (33.20, 120.34)
        ]

        # 坐标输入框
        self.coord_inputs = []
        for i in range(4):
            coord_layout = QHBoxLayout()
            label = QLabel(f"位置 {i + 1} 纬度:")
            lat_input = QLineEdit()
            lon_label = QLabel(" 经度:")
            lon_input = QLineEdit()

            # 设置默认值（示例经纬度）
            lat_input.setText(f"{default_coords[i][0]}")
            lon_input.setText(f"{default_coords[i][1]}")

            coord_layout.addWidget(label)
            coord_layout.addWidget(lat_input)
            coord_layout.addWidget(lon_label)
            coord_layout.addWidget(lon_input)

            self.coord_inputs.append((lat_input, lon_input))

            right_layout.addLayout(coord_layout)

        # 生成间隔（km）
        self.distance_label = QLabel("生成台站间隔（km）：")
        self.distance_input = QSpinBox()
        self.distance_input.setRange(1, 100)
        self.distance_input.setValue(5)
        right_layout.addWidget(self.distance_label)
        right_layout.addWidget(self.distance_input)

        # 生成按钮
        self.generate_btn = QPushButton("生成台站")
        self.generate_btn.clicked.connect(self.generate_stations)
        right_layout.addWidget(self.generate_btn)

        # 输出文本框
        self.output_table = QTableWidget()
        self.output_table.setColumnCount(2)
        self.output_table.setHorizontalHeaderLabels(["纬度", "经度"])
        self.output_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.output_table)

        # 保存按钮
        self.save_btn = QPushButton("保存结果")
        self.save_btn.clicked.connect(self.save_results)
        right_layout.addWidget(self.save_btn)

        right_widget.setLayout(right_layout)

        # 将左右两部分添加到分割器中
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        # 设置分割器的拉伸比例
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1500, 500])

        # 设置主窗口的布局
        layout = QVBoxLayout()
        layout.addWidget(splitter)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 初始化地图
        self.update_map()

    def load_fault_data(self):
        """导入断裂带数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择断裂带文件", "", "Text Files (*.txt)")
        if not file_path:
            return

        self.fault_lines = []
        current_coords = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    if line.startswith('>'):
                        if current_coords:
                            self.fault_lines.append({
                                'name': '幕府山焦山断裂带',
                                'coordinates': current_coords.copy()
                            })
                            current_coords = []
                    else:
                        parts = line.split()
                        if len(parts) == 2:
                            try:
                                lon = float(parts[0])
                                lat = float(parts[1])
                                current_coords.append((lat, lon))  # 转换为（纬度，经度）
                            except ValueError:
                                continue

                # 处理最后一个块
                if current_coords:
                    self.fault_lines.append({
                        'name': '幕府山焦山断裂带',
                        'coordinates': current_coords.copy()
                    })

            self.update_map()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"文件解析失败: {str(e)}")

    def update_map(self):
        """更新地图显示"""
        # 创建基础地图
        if self.use_satellite:
            m = folium.Map(
                location=[35, 105],
                zoom_start=5,
                tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
                attr="Google"
            )
        else:
            m = folium.Map(location=[35, 105], zoom_start=5, tiles="OpenStreetMap")

        # 绘制多边形
        if self.polygon_points:
            polygon = Polygon(self.polygon_points)
            folium.PolyLine(
                list(polygon.exterior.coords),
                color="blue",
                weight=2.5,
                opacity=1
            ).add_to(m)

        # 绘制断裂带
        for fault in self.fault_lines:
            # 绘制红色线段
            line = folium.PolyLine(
                locations=fault['coordinates'],
                color='red',
                weight=3,
                opacity=0.8,
                popup=folium.Popup(fault['name'], max_width=300)
            ).add_to(m)

            # 在线段中间添加文字标注（动态字体大小）
            if len(fault['coordinates']) >= 2:
                mid_index = len(fault['coordinates']) // 2
                mid_point = fault['coordinates'][mid_index]
                marker_id = f"label_{id(fault)}"
                folium.Marker(
                    location=mid_point,
                    icon=folium.DivIcon(
                        html=f'''
                        <div id="{marker_id}" style="
                            font-size: 14px;
                            color: red;
                            font-weight: bold;
                            text-align: center;
                            white-space: nowrap;
                        ">{fault["name"]}</div>
                        ''',
                        icon_size=(150, 36)
                    )
                ).add_to(m)

                # 添加 JavaScript 监听缩放事件，动态调整字体大小
                m.get_root().html.add_child(folium.Element(f"""
                    <script>
                        function adjustLabelSize() {{
                            var zoom = map.getZoom();
                            var fontSize = Math.max(10, zoom * 2) + 'px';
                            var label = document.getElementById('{marker_id}');
                            if (label) {{
                                label.style.fontSize = fontSize;
                            }}
                        }}
                        map.on('zoomend', adjustLabelSize);
                        adjustLabelSize();  // 初始化时调整一次
                    </script>
                """))

        # 添加鼠标位置显示
        from folium.plugins import MousePosition
        MousePosition(position="bottomleft", separator=" | ", empty_string="No coordinates").add_to(m)

        # 绘制台站
        if self.moved_markers:
            marker_cluster = MarkerCluster().add_to(m)
            for name, (lat, lon) in self.moved_markers.items():
                marker = Marker(
                    location=[lat, lon],
                    icon=Icon(color="red", icon="cloud"),
                    draggable=True
                ).add_to(marker_cluster)

                # 使用 JavaScript 在拖动结束后更新坐标
                js = f"""
                function onDragEnd(e) {{
                    var marker = e.target;
                    var newLat = marker.getLatLng().lat;
                    var newLng = marker.getLatLng().lng;
                    window.pybridge.send('{name}:' + newLat + ',' + newLng);
                }}
                marker.on('dragend', onDragEnd);
                """
                marker.add_child(folium.Element(f'<script>{js}</script>'))

        # 渲染地图
        data = BytesIO()
        m.save(data, close_file=False)
        html = data.getvalue().decode()
        self.map_view.setHtml(html)


    # ========== 切换地图类型 ==========
    def toggle_map(self):
        self.use_satellite = not self.use_satellite
        if self.use_satellite:
            self.toggle_map_btn.setText("切换为2D地图")
        else:
            self.toggle_map_btn.setText("切换为实景地图")
        self.update_map()

    def create_grid(self, polygon, interval):
        lat_min, lon_min, lat_max, lon_max = polygon.bounds
        lat_step = interval / 111  # 1度纬度约111公里
        lon_step = interval / (111 * math.cos(math.radians(lat_min)))

        lat_values = np.arange(lat_min, lat_max, lat_step)
        lon_values = np.arange(lon_min, lon_max, lon_step)

        stations = []
        for lat in lat_values:
            for lon in lon_values:
                point = Point(lat, lon)
                if polygon.contains(point):
                    stations.append((lat, lon))

        if not stations:
            raise ValueError("生成台站失败：间隔过大或四边形面积不足")

        return stations

    def display_stations(self, stations):
        self.output_table.setRowCount(len(stations))
        for i, (lat, lon) in enumerate(stations):
            self.output_table.setItem(i, 0, QTableWidgetItem(f"{lat:.6f}"))
            self.output_table.setItem(i, 1, QTableWidgetItem(f"{lon:.6f}"))

    def save_results(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "保存台站", "", "Excel Files (*.xlsx)")
        if file_path:
            data = []
            for row in range(self.output_table.rowCount()):
                lat = self.output_table.item(row, 0).text()
                lon = self.output_table.item(row, 1).text()
                data.append([lat, lon])

            df = pd.DataFrame(data, columns=["纬度", "经度"])
            df.to_csv(file_path, index=False)

    def generate_stations(self):
        try:
            # 读取输入的四个坐标
            points = []
            for lat_input, lon_input in self.coord_inputs:
                lat = float(lat_input.text().strip())
                lon = float(lon_input.text().strip())
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    raise ValueError(f"无效的坐标: 纬度={lat}, 经度={lon}")
                points.append((lat, lon))

            if len(points) != 4:
                raise ValueError("需要完整的四个顶点坐标")

            # === 使用 ConvexHull 修复输入顺序 ===
            points_array = np.array(points)
            hull = ConvexHull(points_array)

            # 将 ConvexHull 输出的索引转换为合法的点集（按照逆时针或顺时针顺序）
            ordered_points = [tuple(points_array[i]) for i in hull.vertices]

            # 将点转换为合法 Polygon
            polygon = Polygon(ordered_points)

            if not polygon.is_valid:
                raise ValueError("生成的四边形无效")

            interval = self.distance_input.value()
            stations = self.create_grid(polygon, interval)

            if not stations:
                raise ValueError("生成台站失败：间隔过大或四边形面积不足")

            # 存储生成的台站
            self.moved_markers = {f"Station_{i + 1}": (lat, lon) for i, (lat, lon) in enumerate(stations)}
            self.polygon_points = list(polygon.exterior.coords)[:-1]  # 去掉闭合的重复点

            # 显示台站和更新地图
            self.display_stations(stations)
            self.update_map()

        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def download_new_coords(self):
        if not self.moved_markers:
            QMessageBox.information(self, "提示", "没有移动的台站")
            return

        data = []
        for name, (lat, lon) in self.moved_markers.items():
            data.append([lat, lon])  # 只保存纬度和经度

        file_path, _ = QFileDialog.getSaveFileName(self, "保存新位置坐标", "", "Excel Files (*.xlsx)")
        if file_path:
            pd.DataFrame(data, columns=["纬度", "经度"]).to_excel(file_path, index=False)
            QMessageBox.information(self, "提示", "新位置坐标保存成功")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StationApp()
    window.show()
    sys.exit(app.exec())