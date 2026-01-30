# data_manager.py
import os
import pickle
import cv2
from datetime import datetime
from tcp_client import TCPClient


class DataManager:
    def __init__(self):
        self.face_data_file = "face_data.pkl"
        self.attendance_file = "attendance_log.csv"
        self.photos_dir = "attendance_photos"
        self.known_face_encodings = []
        self.known_face_names = []
        self.recognized_names = set()
        self.client = TCPClient('192.168.137.96', 8888)
        
        self.load_known_faces()
        self.create_attendance_file()
    
    def load_known_faces(self):
        """加载已知人脸数据"""
        try:
            if os.path.exists(self.face_data_file):
                with open(self.face_data_file, 'rb') as f:
                    data = pickle.load(f)
                    self.known_face_encodings = data['encodings']
                    self.known_face_names = data['names']
                return True
            else:
                return False
        except Exception as e:
            print(f"加载人脸数据失败: {e}")
            return False
    
    def save_known_faces(self):
        """保存人脸数据"""
        try:
            data = {
                'encodings': self.known_face_encodings,
                'names': self.known_face_names
            }
            with open(self.face_data_file, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            print(f"保存人脸数据失败: {e}")
            return False
    
    def create_attendance_file(self):
        """创建考勤记录文件"""
        if not os.path.exists(self.attendance_file):
            with open(self.attendance_file, 'w', encoding='utf-8') as f:
                f.write("日期,时间,姓名,状态\n")

        if not os.path.exists(self.photos_dir):
            os.makedirs(self.photos_dir)
    
    def record_attendance(self, name, frame=None):
        """记录考勤"""
        if name in self.recognized_names:
            return False  # 已经记录过，避免重复
        
        current_time = datetime.now()
        date_str = current_time.strftime("%Y-%m-%d")
        time_str = current_time.strftime("%H:%M:%S")
        
        with open(self.attendance_file, 'a', encoding='utf-8') as f:
            f.write(f"{date_str},{time_str},{name},考勤成功\n")
                
        # 保存考勤照片
        if frame is not None:
            photo_filename = f"{name}_{date_str}_{time_str.replace(':', '')}.jpg"
            photo_path = os.path.join(self.photos_dir, photo_filename)
            cv2.imwrite(photo_path, frame)

        if self.client.connect():
            self.client.send_text(f"{date_str},{time_str},{name}")
            self.client.send_file(photo_path)

        self.recognized_names.add(name)
        return True
    
    def is_name_registered(self, name):
        """检查姓名是否已注册"""
        return name in self.known_face_names
    
    def add_face_data(self, name, encoding):
        """添加人脸数据"""
        self.known_face_encodings.append(encoding)
        self.known_face_names.append(name)
        return self.save_known_faces()
    
    def clear_all_data(self):
        """清空所有人脸数据"""
        self.known_face_encodings = []
        self.known_face_names = []
        if os.path.exists(self.face_data_file):
            os.remove(self.face_data_file)
        return True
    
    def get_registered_count(self):
        """获取已注册人数"""
        return len(self.known_face_names)
    
    def get_attendance_count(self):
        """获取已考勤人数"""
        return len(self.recognized_names)