import os
import csv
import glob
from datetime import datetime

class DataManager:
    """数据管理类，负责数据的解析、存储和加载"""
    
    def __init__(self, data_dir="received_data"):
        self.data_dir = data_dir
        self.current_data = []  # 当前会话数据（未保存）
        self.current_images = {}  # 当前会话图片 {timestamp: image_data}

        self.deadline_hour = 9 # 考勤截止时间（默认9:00）
        self.deadline_minute = 0
        
    
    def parse_text_data(self, text, client_address):
        """解析文本数据 (格式: "日期,时间,姓名")"""
        try:
            parts = text.split(',')
            if len(parts) >= 3:
                date = parts[0].strip()
                time = parts[1].strip()
                name = parts[2].strip()
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 判断是否迟到
                is_late = self.is_late(time)
                
                data_entry = {
                    'timestamp': timestamp,
                    'date': date,
                    'time': time,
                    'name': name,
                    'client_address': client_address,
                    'raw_text': text,
                    'is_late': is_late
                }
                
                # 添加到当前数据
                self.current_data.append(data_entry)
                return data_entry
            return None
        except Exception as e:
            raise Exception(f"解析文本数据失败: {str(e)}")

    def is_late(self, check_time_str):
        """
        判断是否迟到
        
        Args:
            check_time_str: 打卡时间字符串，格式如 "08:30" 或 "08:30:15"
        
        Returns:
            bool: 是否迟到
        """
        try:
            # 解析打卡时间（处理可能包含秒的情况）
            time_parts = check_time_str.split(':')
            check_hour = int(time_parts[0])
            check_minute = int(time_parts[1])
            
            # 比较时间
            if check_hour > self.deadline_hour:
                return "迟到"
            elif check_hour == self.deadline_hour:
                if check_minute > self.deadline_minute:
                    return "迟到"
            return "正常"
            
        except Exception as e:
            return "错误"

    def set_deadline_time(self, hour, minute):
        """设置考勤截止时间"""
        self.deadline_hour = hour
        self.deadline_minute = minute
        print(f"考勤截止时间设置为: {hour:02d}:{minute:02d}")

    def add_image_data(self, filename, file_data, client_address):
        """添加图片数据到当前会话"""
        try:
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.current_images[timestamp] = file_data
                return timestamp
            return None
        except Exception as e:
            raise Exception(f"添加图片数据失败: {str(e)}")
    
    def get_current_data_display(self, data_entry):
        """获取当前数据的显示文本"""
        return f"{data_entry['timestamp']} - {data_entry['name']} ({data_entry['client_address'][0]})"
    
    def get_data_detail_text(self, data_entry):
        """获取数据详情文本"""
        detail_text = f"""
客户端: {data_entry.get('client_address', ('未知', '未知'))[0]}:{data_entry.get('client_address', ('未知', '未知'))[1]}
日期: {data_entry.get('date', '未知')}
打卡时间: {data_entry.get('time', '未知')}
姓名: {data_entry.get('name', '未知')}
考勤状态: {data_entry.get('is_late', '未知')}
        """
        return detail_text.strip()
    
    def get_image_for_timestamp(self, timestamp):
        """根据时间戳获取图片数据"""
        return self.current_images.get(timestamp)
    
    def clear_current_data(self):
        """清空当前数据"""
        self.current_data.clear()
        self.current_images.clear()
    
    def load_history_data(self):
        """从文件系统加载历史数据"""
        try:
            history_entries = []
            texts_dir = os.path.join(self.data_dir, "texts")
            
            if not os.path.exists(texts_dir):
                return history_entries
            
            # 获取所有文本文件并按时间排序
            text_files = glob.glob(os.path.join(texts_dir, "*.txt"))
            text_files.sort(key=os.path.getmtime, reverse=True)
            
            for file_path in text_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 解析文件内容
                    lines = content.split('\n')
                    display_info = ""
                    timestamp = ""
                    client_info = ""
                    
                    for line in lines:
                        if line.startswith('时间:'):
                            timestamp = line.replace('时间:', '').strip()
                        elif line.startswith('客户端:'):
                            client_info = line.replace('客户端:', '').strip()
                        elif line.strip() and not line.startswith('数据长度:') and not line.startswith('-' * 50):
                            raw_data = line.strip()
                            parts = raw_data.split(',')
                            if len(parts) >= 3:
                                name = parts[2].strip()
                                display_info = f"{timestamp} - {name} ({client_info})"
                                break
                    
                    if not display_info:
                        display_info = f"{os.path.basename(file_path)}"
                    
                    history_entries.append({
                        'display_text': display_info,
                        'file_path': file_path
                    })
                    
                except Exception as e:
                    print(f"读取历史文件 {file_path} 失败: {e}")
            
            return history_entries
            
        except Exception as e:
            raise Exception(f"加载历史数据失败: {str(e)}")
    
    def load_history_entry_detail(self, file_path):
        """加载历史数据条目的详细信息"""
        try:
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            data_entry = {}
            
            for line in lines:
                if line.startswith('时间:'):
                    data_entry['timestamp'] = line.replace('时间:', '').strip()
                elif line.startswith('客户端:'):
                    client_str = line.replace('客户端:', '').strip()
                    if ':' in client_str:
                        ip, port = client_str.split(':')
                        data_entry['client_address'] = (ip, int(port))
                elif line.startswith('数据长度:'):
                    continue
                elif line.startswith('-' * 50):
                    continue
                elif line.strip() and 'raw_text' not in data_entry:
                    data_entry['raw_text'] = line.strip()
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        data_entry['date'] = parts[0].strip()
                        data_entry['time'] = parts[1].strip()
                        data_entry['name'] = parts[2].strip()
            
            return data_entry
            
        except Exception as e:
            raise Exception(f"加载历史条目详情失败: {str(e)}")
    
    def load_history_image(self, text_file_path):
        """加载历史图片"""
        try:
            base_data_dir = os.path.dirname(os.path.dirname(text_file_path))
            images_dir = os.path.join(base_data_dir, "images")
            
            if not os.path.exists(images_dir):
                return None
            
            text_filename = os.path.basename(text_file_path)
            
            if text_filename.startswith("text_") and text_filename.endswith(".txt"):
                core_name = text_filename[5:-4]
                
                found_images = []
                
                # 精确匹配
                exact_pattern = os.path.join(images_dir, f"{core_name}*")
                exact_matches = glob.glob(exact_pattern)
                found_images.extend([f for f in exact_matches if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))])
                
                # 时间戳匹配
                if not found_images:
                    timestamp_part = core_name[:15]
                    timestamp_pattern = os.path.join(images_dir, f"{timestamp_part}*")
                    timestamp_matches = glob.glob(timestamp_pattern)
                    found_images.extend([f for f in timestamp_matches if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))])
                
                if found_images:
                    found_images.sort(key=os.path.getmtime, reverse=True)
                    with open(found_images[0], 'rb') as f:
                        return f.read()
            
            return None
            
        except Exception as e:
            raise Exception(f"加载历史图片失败: {str(e)}")
    
    def export_to_csv(self, history_entries, output_path):
        """导出数据到CSV文件"""
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['日期', '时间', '姓名']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                # 导出当前数据
                for data in self.current_data:
                    writer.writerow({
                        '日期': data['date'],
                        '时间': data['time'],
                        '姓名': data['name']
                    })
                
                # 导出历史数据
                for entry in history_entries:
                    file_path = entry['file_path']
                    if os.path.exists(file_path):
                        try:
                            data_entry = self.load_history_entry_detail(file_path)
                            if data_entry:
                                writer.writerow({
                                    '日期': data_entry.get('date', ''),
                                    '打卡时间': data_entry.get('time', ''),
                                    '姓名': data_entry.get('name', '')
                                })
                        except Exception as e:
                            print(f"导出历史数据失败 {file_path}: {e}")
            
            return True
            
        except Exception as e:
            raise Exception(f"导出CSV文件失败: {str(e)}")