# camera_capture.py
import cv2
import threading
import time

class CameraCapture:
    def __init__(self, camera_index=9):
        self.camera_index = camera_index
        self.cap = None
        self.current_frame = None
        self.camera_active = False
        self.frame_lock = threading.Lock()
        
    def start_camera(self):
        """启动摄像头"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.camera_active = True
                
                # 启动帧捕获线程
                self.capture_thread = threading.Thread(target=self._capture_frames, daemon=True)
                self.capture_thread.start()
                return True
            else:
                return False
                
        except Exception as e:
            print(f"启动摄像头失败: {e}")
            return False
    
    def _capture_frames(self):
        """捕获帧的线程函数"""
        while self.camera_active and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                with self.frame_lock:
                    self.current_frame = frame.copy()
            time.sleep(0.03)  # 约30fps
    
    def get_frame(self):
        """获取当前帧"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None
    
    def capture_photo(self, filename):
        """拍摄照片并保存"""
        frame = self.get_frame()
        if frame is not None:
            cv2.imwrite(filename, frame)
            return True
        return False
    
    def stop_camera(self):
        """停止摄像头"""
        self.camera_active = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
    
    def is_camera_active(self):
        """检查摄像头是否活跃"""
        return self.camera_active and self.cap is not None and self.cap.isOpened()