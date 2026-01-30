# GUI.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
import os
from datetime import datetime
from PIL import Image, ImageTk
import cv2

from data_manager import DataManager
from face_processor import FaceProcessor
from camera_capture import CameraCapture
from tcp_client import TCPClient

class FaceAttendanceSystem:
    def __init__(self, root):
        self.root = root
        self.data_manager = DataManager()
        self.face_processor = FaceProcessor(self.data_manager)
        self.camera_capture = CameraCapture(camera_index=9)
        self.client = TCPClient('192.168.137.96', 8888)

        self.current_mode = "attendance"  # "attendance" or "registration"
        self.registration_name = ""
        self.sample_count = 0
        self.sample_images = []
        self.recognition_active = True
        self.last_recognition_time = 0
        self.recognition_interval = 3
        
        self.setup_gui()
        self.start_camera()
        self.show_tcp()
    
    def setup_gui(self):
        """设置GUI界面"""
        self.root.title("智能考勤系统")
        self.root.geometry("700x950")
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 标题和模式切换
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, pady=(0, 10), sticky=(tk.W, tk.E))
        header_frame.columnconfigure(0, weight=1)
        
        title_label = ttk.Label(header_frame, text="智能考勤系统", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        #网络连接状态
        tcp_frane = ttk.Frame(header_frame)
        tcp_frane.grid(row=0, column=2, sticky=tk.E)

        self.tcp_label = ttk.Label(header_frame, text="正在连接服务器", 
                                     font=('Arial', 10), foreground='blue')
        self.tcp_label.grid(row=0, column=0, sticky=tk.E)

        # 模式切换按钮
        mode_frame = ttk.Frame(header_frame)
        mode_frame.grid(row=0, column=1, sticky=tk.E)
        
        self.attendance_btn = ttk.Button(mode_frame, text="考勤模式", 
                                        command=self.switch_to_attendance)
        self.attendance_btn.grid(row=0, column=0, padx=5)
        self.attendance_btn.state(['disabled'])
        
        self.registration_btn = ttk.Button(mode_frame, text="注册模式", 
                                          command=self.switch_to_registration)
        self.registration_btn.grid(row=0, column=1, padx=5)
        
        # 摄像头显示区域
        video_frame = ttk.LabelFrame(main_frame, text="摄像头预览", padding="5")
        video_frame.grid(row=1, column=0, pady=(0, 10), sticky=(tk.W, tk.E, tk.N, tk.S))
        video_frame.columnconfigure(0, weight=1)
        video_frame.rowconfigure(0, weight=1)
        
        self.video_label = ttk.Label(video_frame, background='black')
        self.video_label.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 控制按钮区域 - 重新设计布局
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, pady=(0, 10), sticky=(tk.W, tk.E))
        control_frame.columnconfigure(0, weight=1)
        
        # 考勤模式控件
        self.attendance_controls = ttk.Frame(control_frame)
        
        attendance_status_frame = ttk.Frame(self.attendance_controls)
        attendance_status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), columnspan=2)
        attendance_status_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(attendance_status_frame, text="系统就绪", 
                                     font=('Arial', 20), foreground='blue')
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        # 注册模式控件
        self.registration_controls = ttk.Frame(control_frame)
        
        reg_status_frame = ttk.Frame(self.registration_controls)
        reg_status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), columnspan=4)
        reg_status_frame.columnconfigure(0, weight=1)
        
        self.reg_status_label = ttk.Label(reg_status_frame, text="准备注册", 
                                         font=('Arial', 12))
        self.reg_status_label.grid(row=0, column=0, sticky=tk.W)
        
        # 注册按钮区域
        reg_buttons_frame = ttk.Frame(self.registration_controls)
        reg_buttons_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), columnspan=4, pady=5)
        
        self.start_reg_btn = ttk.Button(reg_buttons_frame, text="开始注册", 
                                       command=self.start_registration, width=12)
        self.start_reg_btn.grid(row=0, column=0, padx=(130,15))
        
        self.capture_btn = ttk.Button(reg_buttons_frame, text="拍照采集", 
                                     command=self.capture_photo, width=12)
        self.capture_btn.grid(row=0, column=1, padx=15)
        self.capture_btn.state(['disabled'])
        
        self.cancel_btn = ttk.Button(reg_buttons_frame, text="取消注册", 
                                    command=self.cancel_registration, width=12)
        self.cancel_btn.grid(row=0, column=2, padx=15)
        self.cancel_btn.state(['disabled'])
        
        # 进度条
        self.progress = ttk.Progressbar(self.registration_controls, orient='horizontal', 
                                       length=650, mode='determinate')
        self.progress.grid(row=2, column=0, columnspan=4, pady=5, sticky=(tk.W, tk.E))
        
        # 通用控制按钮区域 - 放在控制框架的单独一行
        common_frame = ttk.LabelFrame(control_frame, text="系统工具", padding="5")
        common_frame.grid(row=1, column=0, pady=(10, 0), sticky=(tk.W, tk.E))
        common_frame.columnconfigure(0, weight=1)
        
        common_buttons_frame = ttk.Frame(common_frame)
        common_buttons_frame.grid(row=0, column=0, pady=5)
        
        self.list_btn = ttk.Button(common_buttons_frame, text="查看已注册列表", 
                                  command=self.show_registered_list, width=15)
        self.list_btn.grid(row=0, column=0, padx=10)
        
        self.clear_btn = ttk.Button(common_buttons_frame, text="清空所有数据", 
                                   command=self.clear_all_data, width=15)
        self.clear_btn.grid(row=0, column=1, padx=10)
        
        self.quit_btn = ttk.Button(common_buttons_frame, text="退出系统", 
                                  command=self.quit_system, width=15)
        self.quit_btn.grid(row=0, column=2, padx=10)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="系统日志", padding="5")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, height=12, width=80, font=('Arial', 9))
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 初始显示考勤模式
        self.show_attendance_controls()

        self.log_message("系统初始化完成")
        self.log_message(f"已加载 {self.data_manager.get_registered_count()} 个注册人脸")
    
    def show_tcp(self):
        """更新tcpt通信连接状态"""
        if self.client.connect():
            self.tcp_label.config(text=f"成功连接服务器", foreground='green')
        else:
            self.tcp_label.config(text=f"服务器连接失败", foreground='red')
        self.tcp_label.after(1000, self.show_tcp)

    def show_attendance_controls(self):
        """显示考勤模式控件"""
        self.registration_controls.grid_remove()
        self.attendance_controls.grid(row=0, column=0, sticky=(tk.W, tk.E))
        # 通用控制按钮已经在独立区域，不需要移动
    
    def show_registration_controls(self):
        """显示注册模式控件"""
        self.attendance_controls.grid_remove()
        self.registration_controls.grid(row=0, column=0, sticky=(tk.W, tk.E))
        # 通用控制按钮已经在独立区域，不需要移动
    
    def switch_to_attendance(self):
        """切换到考勤模式"""
        self.current_mode = "attendance"
        self.recognition_active = True
        self.show_attendance_controls()
        self.attendance_btn.state(['disabled'])
        self.registration_btn.state(['!disabled'])
        self.log_message("切换到考勤模式")
    
    def switch_to_registration(self):
        """切换到注册模式"""
        self.current_mode = "registration"
        self.recognition_active = False
        self.show_registration_controls()
        self.attendance_btn.state(['!disabled'])
        self.registration_btn.state(['disabled'])
        self.log_message("切换到注册模式")
    
    def start_camera(self):
        """启动摄像头"""
        if self.camera_capture.start_camera():
            self.log_message("摄像头启动成功")
            self.update_camera()
        else:
            # 尝试其他摄像头索引
            for i in range(1, 5):
                self.camera_capture = CameraCapture(camera_index=i)
                if self.camera_capture.start_camera():
                    self.log_message(f"摄像头启动成功 (索引 {i})")
                    self.update_camera()
                    return
            
            self.log_message("错误：无法启动摄像头")
            messagebox.showerror("错误", "无法启动摄像头，请检查摄像头连接")
    
    def update_camera(self):
        """更新摄像头画面"""
        if self.camera_capture.is_camera_active():
            frame = self.camera_capture.get_frame()
            if frame is not None:
                # 考勤模式下进行人脸识别
                if self.current_mode == "attendance":
                    current_time = time.time()
                    if (self.recognition_active and 
                        current_time - self.last_recognition_time >= self.recognition_interval):
                        self.last_recognition_time = current_time
                        self.perform_recognition(frame.copy())
                
                # 注册模式下显示状态信息
                elif self.current_mode == "registration" and self.registration_name:
                    display_frame = frame.copy()
                    cv2.putText(display_frame, f"Registration: {self.registration_name}", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(display_frame, f"Samples: {self.sample_count}/5", 
                               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    frame = display_frame
                
                # 转换并显示图像
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_resized = cv2.resize(frame_rgb, (640, 480))
                
                img = Image.fromarray(frame_resized)
                imgtk = ImageTk.PhotoImage(image=img)
                
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
            
            self.root.after(30, self.update_camera)
    
    def perform_recognition(self, frame):
        """执行人脸识别"""
        def recognition_thread():
            try:
                results, error = self.face_processor.recognize_faces(frame)
                
                if error:
                    self.root.after(0, lambda: self.status_label.config(text=error, foreground='red'))
                    return
                
                if results:
                    for name, status in results:
                        self.root.after(0, lambda n=name, s=status: self.show_recognition_result(n, s))
                else:
                    self.root.after(0, lambda: self.status_label.config(text="未识别到人脸", foreground='orange'))
                        
            except Exception as e:
                self.root.after(0, lambda: self.status_label.config(text=f"识别错误: {e}", foreground='red'))
        
        threading.Thread(target=recognition_thread, daemon=True).start()
    
    def show_recognition_result(self, name, status):
        """显示识别结果"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if status == "考勤成功":
            result_text = f"[{timestamp}] ✓ 考勤成功 - {name}\n"
            self.status_label.config(text=f"考勤成功: {name}", foreground='green')
            self.log_message(f"考勤成功: {name}")
        elif status == "考勤重复":
            result_text = f"[{timestamp}] ⚠ 考勤重复 - {name}\n"
            self.status_label.config(text=f"考勤重复: {name}", foreground='orange')
            self.log_message(f"考勤重复: {name}")
        else:
            result_text = f"[{timestamp}] ✗ {status}\n"
            self.status_label.config(text=status, foreground='red')
        
        # 在日志中显示结果
        self.log_text.insert(tk.END, result_text)
        self.log_text.see(tk.END)
    
    def start_registration(self):
        """开始注册流程"""
        name = simpledialog.askstring("输入姓名", "请输入要注册的姓名:")
        if name and name.strip():
            name = name.strip()
            if self.data_manager.is_name_registered(name):
                messagebox.showwarning("警告", f"姓名 '{name}' 已被注册")
            else:
                self.registration_name = name
                self.sample_count = 0
                self.sample_images = []
                
                self.start_reg_btn.state(['disabled'])
                self.capture_btn.state(['!disabled'])
                self.cancel_btn.state(['!disabled'])
                self.progress['value'] = 0
                
                self.reg_status_label.config(text=f"正在注册: {name}", foreground='blue')
                self.log_message(f"开始注册: {name}")
        else:
            messagebox.showwarning("警告", "姓名不能为空")
    
    def capture_photo(self):
        """拍照采集样本"""
        if not self.registration_name:
            messagebox.showwarning("警告", "请先开始注册流程")
            return
            
        if self.sample_count >= 5:
            messagebox.showinfo("提示", "已采集5张照片，正在处理...")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"temp_sample_{self.registration_name}_{timestamp}.jpg"
        
        if self.camera_capture.capture_photo(filename):
            self.sample_images.append(filename)
            self.sample_count += 1
            self.progress['value'] = self.sample_count * 20
            
            self.log_message(f"已拍摄样本 {self.sample_count}/5")
            self.reg_status_label.config(text=f"已采集 {self.sample_count}/5 张照片", foreground='green')
            
            if self.sample_count >= 5:
                self.log_message("开始处理样本...")
                self.reg_status_label.config(text="正在处理样本...", foreground='orange')
                self.process_registration_samples()
    
    def process_registration_samples(self):
        """处理注册样本"""
        def process_thread():
            encoding, valid_samples, success = self.face_processor.process_registration_samples(
                self.sample_images, self.registration_name
            )
            
            self.root.after(0, lambda: self.finish_registration(encoding, valid_samples, success))
        
        threading.Thread(target=process_thread, daemon=True).start()
    
    def finish_registration(self, encoding, valid_samples, success):
        """完成注册"""
        # 清理临时文件
        for img_path in self.sample_images:
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except:
                    pass
        
        if success and encoding is not None:
            if self.data_manager.add_face_data(self.registration_name, encoding):
                self.log_message(f"✓ 注册成功: {self.registration_name} (基于 {valid_samples} 个有效样本)")
                self.reg_status_label.config(text=f"注册成功: {self.registration_name}", foreground='green')
                messagebox.showinfo("成功", f"注册成功: {self.registration_name}\n基于 {valid_samples} 个有效样本")
            else:
                self.log_message("注册失败：保存数据时出错")
                self.reg_status_label.config(text="注册失败", foreground='red')
                messagebox.showerror("错误", "注册失败：保存数据时出错")
        else:
            self.log_message(f"注册失败：有效样本不足 ({valid_samples}/5)")
            self.reg_status_label.config(text=f"有效样本不足 ({valid_samples}/5)", foreground='red')
            messagebox.showerror("错误", f"有效样本不足 ({valid_samples}/5)，需要至少3个有效样本")
        
        self.cancel_registration()
    
    def cancel_registration(self):
        """取消注册"""
        # 清理临时文件
        for img_path in self.sample_images:
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except:
                    pass
        
        self.registration_name = ""
        self.sample_count = 0
        self.sample_images = []
        
        self.start_reg_btn.state(['!disabled'])
        self.capture_btn.state(['disabled'])
        self.cancel_btn.state(['disabled'])
        self.progress['value'] = 0
        self.reg_status_label.config(text="准备注册", foreground='black')
        
        if self.current_mode == "registration":
            self.log_message("注册流程已取消")
    
    def show_registered_list(self):
        """显示已注册列表"""
        names = self.data_manager.known_face_names
        if not names:
            messagebox.showinfo("已注册列表", "暂无注册人脸")
        else:
            list_text = f"已注册人脸列表 (共{len(names)}人):\n\n"
            for i, name in enumerate(names, 1):
                list_text += f"{i}. {name}\n"
            messagebox.showinfo("已注册列表", list_text)
            self.log_message("查看已注册列表")
    
    def clear_all_data(self):
        """清空所有数据"""
        if messagebox.askyesno("确认清空", "确定要清空所有人脸数据吗？此操作不可恢复！"):
            if self.data_manager.clear_all_data():
                self.log_message("已清空所有人脸数据")
                messagebox.showinfo("成功", "已清空所有人脸数据")
            else:
                messagebox.showerror("错误", "清空数据失败")
    
    def quit_system(self):
        """退出系统"""
        if messagebox.askokcancel("退出", "确定要退出系统吗？"):
            self.camera_capture.stop_camera()
            self.root.destroy()
    
    def log_message(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)

def main():
    root = tk.Tk()
    app = FaceAttendanceSystem(root)

    # 设置窗口在屏幕中央显示
    window_width = 700
    window_height = 950
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    root.mainloop()

if __name__ == "__main__":
    main()