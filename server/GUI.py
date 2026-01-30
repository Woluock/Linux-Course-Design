import sys
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QLabel, QWidget, QSplitter, 
                             QListWidget, QTabWidget, QMessageBox, QFileDialog,
                             QScrollArea, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QPixmap, QImage

from data_manager import DataManager
import tcp_server

class ServerThread(QThread):
    """服务器线程，用于在后台运行TCP服务器"""
    text_received = pyqtSignal(str, tuple)
    file_received = pyqtSignal(str, bytes, tuple)
    client_connected = pyqtSignal(tuple)
    client_disconnected = pyqtSignal(tuple)
    
    def __init__(self, host='192.168.137.96', port=8888):
        super().__init__()
        self.server = tcp_server.TCPServerModule(host, port)
        self.setup_callbacks()
        
    def setup_callbacks(self):
        """设置回调函数"""
        self.server.set_callbacks(
            text_callback=self.on_text_received,
            file_callback=self.on_file_received,
            connect_callback=self.on_client_connected,
            disconnect_callback=self.on_client_disconnected
        )
    
    def on_text_received(self, text, client_address):
        self.text_received.emit(text, client_address)
    
    def on_file_received(self, filename, file_data, client_address):
        self.file_received.emit(filename, file_data, client_address)
    
    def on_client_connected(self, client_address):
        self.client_connected.emit(client_address)
    
    def on_client_disconnected(self, client_address):
        self.client_disconnected.emit(client_address)
    
    def run(self):
        if not self.server.start_server():
            pass
    
    def stop(self):
        self.server.stop_server()

class ServerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.server_thread = None
        self.data_manager = DataManager()
        self.history_entries = []
        self.connected_ips = set()
        
        self.init_ui()
        self.load_history_data()
    
    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle('智能考勤系统服务器监控界面')
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Horizontal)
        
        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])
        main_layout.addWidget(splitter)
        
        self.statusBar().showMessage('服务器未启动')
    
    def create_left_panel(self):
        """创建左侧控制面板"""
        left_widget = QWidget()
        layout = QVBoxLayout(left_widget)
        
        # 服务器控制按钮
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton('启动服务器')
        self.start_btn.clicked.connect(self.start_server)
        self.stop_btn = QPushButton('停止服务器')
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        layout.addLayout(control_layout)

        # 考勤时间设置区域
        attendance_time_layout = QVBoxLayout()
        attendance_time_layout.addWidget(QLabel('考勤截止时间设置:'))
        
        # 时间设置水平布局
        time_setting_layout = QHBoxLayout()
        time_setting_layout.addWidget(QLabel('截止时间:'))
        
        # 小时下拉框
        self.hour_combo = QComboBox()
        for i in range(24):
            self.hour_combo.addItem(f"{i:02d}")
        self.hour_combo.setCurrentText("09")  # 默认9点
        
        # 分钟下拉框
        self.minute_combo = QComboBox()
        for i in range(0, 60, 5):  # 每5分钟一个选项
            self.minute_combo.addItem(f"{i:02d}")
        self.minute_combo.setCurrentText("00")  # 默认00分
        
        time_setting_layout.addWidget(self.hour_combo)
        time_setting_layout.addWidget(QLabel('时'))
        time_setting_layout.addWidget(self.minute_combo)
        time_setting_layout.addWidget(QLabel('分'))
        
        # 设置按钮
        self.set_time_btn = QPushButton('设置')
        self.set_time_btn.clicked.connect(self.set_attendance_time)
        time_setting_layout.addWidget(self.set_time_btn)
        
        attendance_time_layout.addLayout(time_setting_layout)
        
        # 显示当前设置的截止时间
        self.current_time_label = QLabel('当前截止时间: 09:00')
        attendance_time_layout.addWidget(self.current_time_label)
        
        layout.addLayout(attendance_time_layout)
        
        # 功能按钮
        self.export_btn = QPushButton('导出数据到CSV')
        self.export_btn.clicked.connect(self.export_to_csv)
        layout.addWidget(self.export_btn)
        
        self.refresh_btn = QPushButton('刷新历史数据')
        self.refresh_btn.clicked.connect(self.load_history_data)
        layout.addWidget(self.refresh_btn)
        
        # 连接客户端信息
        clients_layout = QVBoxLayout()
        clients_layout.addWidget(QLabel('连接客户端:'))
        self.clients_list = QListWidget()
        clients_layout.addWidget(self.clients_list)
        layout.addLayout(clients_layout)
        
        # 数据列表
        data_list_layout = QVBoxLayout()
        data_list_layout.addWidget(QLabel('考勤流水:'))
        
        self.data_tabs = QTabWidget()
        self.current_data_list = QListWidget()
        self.current_data_list.currentRowChanged.connect(self.on_current_data_selected)
        self.data_tabs.addTab(self.current_data_list, "当前数据")
        
        self.history_data_list = QListWidget()
        self.history_data_list.currentRowChanged.connect(self.on_history_data_selected)
        self.data_tabs.addTab(self.history_data_list, "历史数据")
        
        data_list_layout.addWidget(self.data_tabs)
        layout.addLayout(data_list_layout)
        
        return left_widget
    
    def create_right_panel(self):
        """创建右侧数据显示面板"""
        right_widget = QWidget()
        layout = QVBoxLayout(right_widget)
        
        # 数据详情显示
        detail_layout = QVBoxLayout()
        detail_layout.addWidget(QLabel('考勤详情:'))
        self.data_detail = QTextEdit()
        self.data_detail.setReadOnly(True)
        detail_layout.addWidget(self.data_detail)
        layout.addLayout(detail_layout)
        
        # 图片显示区域
        image_layout = QVBoxLayout()
        image_layout.addWidget(QLabel('图片预览:'))
        self.image_scroll = QScrollArea()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setText("暂无图片")
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: white;")
        self.image_scroll.setWidget(self.image_label)
        self.image_scroll.setWidgetResizable(True)
        image_layout.addWidget(self.image_scroll)
        layout.addLayout(image_layout)
        
        return right_widget
    
    def start_server(self):
        """启动服务器"""
        try:
            self.server_thread = ServerThread()
            self.server_thread.text_received.connect(self.on_text_data_received)
            self.server_thread.file_received.connect(self.on_file_data_received)
            self.server_thread.client_connected.connect(self.on_client_connected)
            self.server_thread.client_disconnected.connect(self.on_client_disconnected)
            self.server_thread.start()
            
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.statusBar().showMessage('服务器已启动')
            
            self.data_manager.clear_current_data()
            self.current_data_list.clear()
            
            QMessageBox.information(self, '成功', '服务器启动成功！')
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'启动服务器失败: {str(e)}')
    
    def stop_server(self):
        """停止服务器"""
        if self.server_thread:
            self.server_thread.stop()
            self.server_thread.wait()
            self.server_thread = None
            
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.statusBar().showMessage('服务器已停止')
            
            QMessageBox.information(self, '成功', '服务器已停止！')
    
    def on_text_data_received(self, text, client_address):
        """处理接收到的文本数据"""
        try:
            data_entry = self.data_manager.parse_text_data(text, client_address)
            if data_entry:
                display_text = self.data_manager.get_current_data_display(data_entry)
                self.current_data_list.addItem(display_text)
                self.current_data_list.setCurrentRow(self.current_data_list.count() - 1)
                self.show_data_detail(data_entry)
                self.statusBar().showMessage(f'收到来自 {client_address} 的文本数据')
                
        except Exception as e:
            self.statusBar().showMessage(f'处理文本数据时出错: {str(e)}')
    
    def on_file_data_received(self, filename, file_data, client_address):
        """处理接收到的文件数据"""
        try:
            timestamp = self.data_manager.add_image_data(filename, file_data, client_address)
            if timestamp:
                self.display_image(file_data)
                self.statusBar().showMessage(f'收到来自 {client_address} 的图片: {filename}')
            else:
                self.statusBar().showMessage(f'收到来自 {client_address} 的文件: {filename}')
                
        except Exception as e:
            self.statusBar().showMessage(f'处理文件数据时出错: {str(e)}')
    
    def on_client_connected(self, client_address):
        """处理客户端连接"""
        client_info = f"{client_address[0]}"
        # 检查这个IP是否已经显示
        if client_info not in self.connected_ips:
            self.connected_ips.add(client_info)
            self.clients_list.addItem(client_info)
            self.statusBar().showMessage(f'客户端连接: {client_info}')
    
    def on_client_disconnected(self, client_address):
        """处理客户端断开"""
        client_info = f"{client_address[0]}:{client_address[1]}"
        for i in range(self.clients_list.count()):
            if self.clients_list.item(i).text() == client_info:
                self.clients_list.takeItem(i)
                break
        self.statusBar().showMessage(f'客户端断开: {client_info}')
    
    def on_current_data_selected(self, row):
        """当前数据项被选中"""
        current_data = self.data_manager.current_data
        if 0 <= row < len(current_data):
            data_entry = current_data[row]
            self.show_data_detail(data_entry)
            image_data = self.data_manager.get_image_for_timestamp(data_entry['timestamp'])
            if image_data:
                self.display_image(image_data)
            else:
                self.image_label.setText("该记录无对应图片")
                self.image_label.setPixmap(QPixmap())
    
    def on_history_data_selected(self, row):
        """历史数据项被选中"""
        if 0 <= row < len(self.history_entries):
            entry = self.history_entries[row]
            try:
                data_entry = self.data_manager.load_history_entry_detail(entry['file_path'])
                if data_entry:
                    self.show_data_detail(data_entry)
                    image_data = self.data_manager.load_history_image(entry['file_path'])
                    if image_data:
                        self.display_image(image_data)
                    else:
                        self.image_label.setText("该记录无对应图片")
                        self.image_label.setPixmap(QPixmap())
            except Exception as e:
                self.data_detail.setText(f"读取历史数据文件失败: {str(e)}")
                self.image_label.setText("加载历史图片失败")
    
    def show_data_detail(self, data_entry):
        """显示数据详情"""
        detail_text = self.data_manager.get_data_detail_text(data_entry)
        self.data_detail.setText(detail_text)
    
    def display_image(self, image_data):
        """显示图片"""
        try:
            image = QImage()
            image.loadFromData(image_data)
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                scaled_pixmap = pixmap.scaled(
                    self.image_label.width(), 
                    self.image_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setText("图片加载失败")
        except Exception as e:
            self.image_label.setText(f"显示图片时出错: {str(e)}")
    
    def load_history_data(self):
        """加载历史数据"""
        try:
            self.history_entries = self.data_manager.load_history_data()
            self.history_data_list.clear()
            
            for entry in self.history_entries:
                item = self.history_data_list.addItem(entry['display_text'])
                self.history_data_list.item(self.history_data_list.count() - 1).setData(Qt.UserRole, entry['file_path'])
            
            self.statusBar().showMessage(f'已加载 {len(self.history_entries)} 条历史记录')
            
        except Exception as e:
            QMessageBox.warning(self, '警告', f'加载历史数据失败: {str(e)}')
    
    def set_attendance_time(self):
        """设置考勤截止时间"""
        hour = int(self.hour_combo.currentText())
        minute = int(self.minute_combo.currentText())
        
        # 更新数据管理器的截止时间
        self.data_manager.set_deadline_time(hour, minute)
        
        # 更新显示
        self.current_time_label.setText(f'当前截止时间: {hour:02d}:{minute:02d}')
        
        QMessageBox.information(self, '成功', f'考勤截止时间已设置为 {hour:02d}:{minute:02d}')

    def export_to_csv(self):
        """导出数据到CSV文件"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                '导出CSV文件', 
                f'考勤数据_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                'CSV文件 (*.csv)'
            )
            
            if file_path:
                success = self.data_manager.export_to_csv(self.history_entries, file_path)
                if success:
                    QMessageBox.information(self, '成功', f'数据已导出到: {file_path}')
                
        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出CSV文件失败: {str(e)}')
    
    def closeEvent(self, event):
        """关闭应用程序事件"""
        if self.server_thread and self.server_thread.isRunning():
            reply = QMessageBox.question(
                self, '确认退出',
                '服务器正在运行，确定要退出吗？',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.stop_server()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = ServerGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()