#client.py
import socket
import os

class TCPClient:
    def __init__(self, server_host='192.168.137.96', server_port=8888):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
    
    def connect(self):
        """连接到服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            return True
        except Exception as e:
            return False
    
    def send_text(self, text):
        """发送文本数据"""
        if not self.socket:
            return False
        
        try:
            # 发送数据类型标识
            self.socket.send("TEXT".ljust(4).encode('utf-8'))
            
            # 发送数据长度
            text_data = text.encode('utf-8')
            data_length = len(text_data)
            self.socket.send(str(data_length).ljust(8).encode('utf-8'))
            
            # 发送实际数据
            self.socket.send(text_data)
            
            # 等待服务器确认
            response = self.socket.recv(1024).decode('utf-8')
            if response == "TEXT_RECEIVED":
                return True
            else:
                return False
                
        except Exception as e:
            return False
    
    def send_file(self, file_path):
        """发送文件/图片"""
        if not self.socket:
            return False
        
        if not os.path.exists(file_path):
            return False
        
        try:
            # 发送数据类型标识
            self.socket.send("FILE".ljust(4).encode('utf-8'))
            
            # 获取文件信息
            filename = os.path.basename(file_path)
            filesize = os.path.getsize(file_path)
            
            # 发送文件名和文件大小
            file_info = f"{filename}|{filesize}".ljust(256)
            self.socket.send(file_info.encode('utf-8'))
            
            # 读取并发送文件数据
            with open(file_path, 'rb') as f:
                sent_bytes = 0
                while sent_bytes < filesize:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.socket.send(chunk)
                    sent_bytes += len(chunk)
            
            # 等待服务器确认
            response = self.socket.recv(1024).decode('utf-8')
            if response == "FILE_RECEIVED":
                return True
            else:
                return False
                
        except Exception as e:
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            try:
                self.socket.send("EXIT".ljust(4).encode('utf-8'))
            except:
                pass
            self.socket.close()
            self.socket = None