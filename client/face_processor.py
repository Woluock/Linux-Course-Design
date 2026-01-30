# face_processor.py
import cv2
import face_recognition
import numpy as np

class FaceProcessor:
    def __init__(self, data_manager):
        self.data_manager = data_manager
    
    def extract_face_features(self, image_path):
        """从图片中提取人脸特征"""
        try:
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            
            if len(face_locations) == 0:
                return None, "未检测到人脸"
            elif len(face_locations) > 1:
                return None, "检测到多个人脸"
            else:
                face_encodings = face_recognition.face_encodings(image, face_locations)
                if len(face_encodings) > 0:
                    return face_encodings[0], "成功提取特征"
                else:
                    return None, "无法提取人脸特征"
                    
        except Exception as e:
            return None, f"处理图片时出错: {e}"
    
    def extract_face_features_from_frame(self, frame):
        """从视频帧中提取人脸特征"""
        try:
            # 缩小帧以加速处理
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            
            if len(face_encodings) > 0:
                return face_encodings[0], "成功提取特征"
            else:
                return None, "无法提取人脸特征"
                
        except Exception as e:
            return None, f"处理帧时出错: {e}"
    
    def recognize_faces(self, frame):
        """识别人脸并返回结果"""
        try:
            # 缩小帧以加速处理
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # 检测人脸
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            
            if not face_encodings:
                return None, "未检测到人脸"
            
            recognition_results = []
            for face_encoding in face_encodings:
                # 如果没有已知人脸，标记为未知
                if not self.data_manager.known_face_encodings:
                    recognition_results.append(("Unknown", "识别失败：未注册"))
                    continue
                    
                # 检查是否匹配已知人脸
                matches = face_recognition.compare_faces(
                    self.data_manager.known_face_encodings, 
                    face_encoding
                )
                name = "Unknown"
                status = "识别失败：未注册"
                
                # 使用已知人脸中距离最小的
                face_distances = face_recognition.face_distance(
                    self.data_manager.known_face_encodings, 
                    face_encoding
                )
                best_match_index = np.argmin(face_distances)
                
                # 设置匹配阈值
                if matches[best_match_index] and face_distances[best_match_index] < 0.6:
                    name = self.data_manager.known_face_names[best_match_index]
                    if self.data_manager.record_attendance(name, frame):
                        status = "考勤成功"
                    else:
                        status = "考勤重复"
                else:
                    status = "识别失败：匹配度不足"
                
                recognition_results.append((name, status))
            
            return recognition_results, None
            
        except Exception as e:
            return None, f"识别过程中出错: {e}"
    
    def process_registration_samples(self, sample_images, name):
        """处理注册样本"""
        features_collected = []
        valid_samples = 0
        
        for img_path in sample_images:
            encoding, message = self.extract_face_features(img_path)
            if encoding is not None:
                features_collected.append(encoding)
                valid_samples += 1
        
        if valid_samples >= 3:
            # 计算平均特征向量
            avg_encoding = np.mean(features_collected, axis=0)
            return avg_encoding, valid_samples, True
        else:
            return None, valid_samples, False