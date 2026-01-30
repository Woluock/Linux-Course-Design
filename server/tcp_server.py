import socket
import threading
import os
import time
from datetime import datetime
import json

class TCPServerModule:
    def __init__(self, host='192.168.137.96', port=8888, data_dir="received_data"):
        """
        初始化TCP服务器模块
        
        Args:
            host: 服务器IP地址
            port: 服务器端口
            data_dir: 数据存储目录
        """
        self.host = host
        self.port = port
        self.data_dir = data_dir
        self.socket = None
        self.running = False
        self.server_thread = None
        self.clients = []
        
        # 回调函数
        self.on_text_received = None
        self.on_file_received = None
        self.on_client_connected = None
        self.on_client_disconnected = None
        
        # 创建数据存储目录
        self._ensure_data_directories()
    
    def _ensure_data_directories(self):
        """确保数据存储目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        text_dir = os.path.join(self.data_dir, "texts")
        image_dir = os.path.join(self.data_dir, "images")
        other_dir = os.path.join(self.data_dir, "other_files")
        
        for directory in [text_dir, image_dir, other_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
    
    def start_server(self):
        """
        启动TCP服务器
        
        Returns:
            bool: 启动成功返回True，失败返回False
        """
        if self.running:
            print("服务器已经在运行中")
            return True
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.socket.settimeout(1)  # 设置超时以便可以检查运行状态
            self.running = True
            
            # 启动服务器线程
            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            print(f"TCP服务器已启动在 {self.host}:{self.port}")
            return True
            
        except Exception as e:
            print(f"启动服务器失败: {e}")
            self.running = False
            return False
    
    def _server_loop(self):
        """服务器主循环"""
        while self.running:
            try:
                client_socket, client_address = self.socket.accept()
                
                # 触发客户端连接回调
                if self.on_client_connected:
                    self.on_client_connected(client_address)
                
                # 为每个客户端创建处理线程
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
                
                # 保存客户端信息
                self.clients.append({
                    'socket': client_socket,
                    'address': client_address,
                    'thread': client_thread
                })
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"接受连接时出错: {e}")
    
    def _handle_client(self, client_socket, client_address):
        """处理客户端连接"""
        try:
            while self.running:
                # 接收数据类型标识
                data_type = client_socket.recv(4)
                if not data_type:
                    break
                
                data_type = data_type.decode('utf-8').strip()
                
                if data_type == 'TEXT':
                    self._receive_text(client_socket, client_address)
                    
                elif data_type == 'FILE':
                    self._receive_file(client_socket, client_address)

                elif data_type == 'EXIT':
                    print(f"客户端 {client_address} 断开连接")
                    break
                    
        except Exception as e:
            print(f"处理客户端 {client_address} 时出错: {e}")
        finally:
            # 清理客户端信息
            self._remove_client(client_socket)
            client_socket.close()
            
            # 触发客户端断开回调
            if self.on_client_disconnected:
                self.on_client_disconnected(client_address)
    
    def _remove_client(self, client_socket):
        """移除客户端"""
        self.clients = [client for client in self.clients if client['socket'] != client_socket]
    
    def _receive_text(self, client_socket, client_address):
        """接收文本数据"""
        try:
            # 接收数据长度
            length_data = client_socket.recv(8)
            if not length_data:
                return
            
            data_length = int(length_data.decode('utf-8').strip())
            
            # 接收实际数据
            received_data = b''
            while len(received_data) < data_length:
                chunk = client_socket.recv(min(4096, data_length - len(received_data)))
                if not chunk:
                    break
                received_data += chunk
            
            text_data = received_data.decode('utf-8')
            
            # 触发文本接收回调
            if self.on_text_received:
                self.on_text_received(text_data, client_address)
            
            # 保存文本
            self.save_text(text_data, client_address)
            
            # 发送确认
            client_socket.send("TEXT_RECEIVED".encode('utf-8'))
            
        except Exception as e:
            print(f"接收文本数据时出错: {e}")
    
    def _receive_file(self, client_socket, client_address):
        """接收文件"""
        try:
            # 1. 接收文件信息头（256字节）
            # 客户端会先发送文件名和文件大小信息
            file_info = client_socket.recv(256).decode('utf-8').strip()
            
            # 2. 解析文件信息
            # 格式为 "文件名|文件大小"，例如 "photo.jpg|1024000"
            filename, filesize_str = file_info.split('|')
            filesize = int(filesize_str)  # 将字符串转换为整数
            
            print(f"开始接收文件: {filename}, 大小: {filesize} 字节")
            
            # 3. 接收文件的实际数据
            received_data = b''  # 创建空字节串来存储文件数据
            while len(received_data) < filesize:
                # 每次最多接收4096字节，确保不会超过文件总大小
                chunk_size = min(4096, filesize - len(received_data))
                chunk = client_socket.recv(chunk_size)
                
                if not chunk:  # 如果没有收到数据，说明连接可能中断
                    break
                received_data += chunk  # 将收到的数据块添加到总数据中
            
            # 4. 触发文件接收回调函数
            if self.on_file_received:
                self.on_file_received(filename, received_data, client_address)
            
            # 5. 保存文件到本地磁盘
            self.save_file(filename, received_data, client_address)
            
            # 6. 向客户端发送确认消息
            client_socket.send("FILE_RECEIVED".encode('utf-8'))
            
        except Exception as e:
            print(f"接收文件时出错: {e}")
            
    def save_text(self, text_data, client_address=None):
        """
        保存文本数据
        
        Args:
            text_data: 文本内容
            client_address: 客户端地址信息
            
        Returns:
            str: 保存的文件路径
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            client_info = f"_{client_address[0]}_{client_address[1]}" if client_address else ""
            filename = f"text_{timestamp}{client_info}.txt"
            filepath = os.path.join(self.data_dir, "texts", filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                if client_address:
                    f.write(f"客户端: {client_address[0]}:{client_address[1]}\n")
                f.write(f"数据长度: {len(text_data)}\n")
                f.write("-" * 50 + "\n")
                f.write(text_data + "\n")
            
            print(f"文本数据已保存: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"保存文本数据时出错: {e}")
            return None
    
    def save_file(self, filename, file_data, client_address=None):
        """
        保存文件/照片
        
        Args:
            filename: 原文件名
            file_data: 文件二进制数据
            client_address: 客户端地址信息
            
        Returns:
            str: 保存的文件路径
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            client_info = f"_{client_address[0]}_{client_address[1]}" if client_address else ""
            
            # 根据文件扩展名确定存储目录
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
                save_dir = "images"
            else:
                save_dir = "other_files"
            
            # 生成新文件名
            new_filename = f"{timestamp}{client_info}_{filename}"
            filepath = os.path.join(self.data_dir, save_dir, new_filename)
            
            with open(filepath, 'wb') as f:
                f.write(file_data)
            
            print(f"文件已保存: {filepath} ({len(file_data)} 字节)")
            return filepath
            
        except Exception as e:
            print(f"保存文件时出错: {e}")
            return None
    
    def stop_server(self):
        """停止服务器"""
        self.running = False
        
        # 关闭所有客户端连接
        for client in self.clients:
            try:
                client['socket'].close()
            except:
                pass
        
        # 关闭服务器socket
        if self.socket:
            self.socket.close()
            self.socket = None
        
        self.clients.clear()
        print("TCP服务器已停止")
    
    def is_running(self):
        """检查服务器是否在运行"""
        return self.running
    
    def get_connected_clients(self):
        """获取当前连接的客户端数量"""
        return len(self.clients)
    
    def set_callbacks(self, text_callback=None, file_callback=None, 
                     connect_callback=None, disconnect_callback=None):
        """
        设置回调函数
        
        Args:
            text_callback: 文本接收回调函数 function(text, client_address)
            file_callback: 文件接收回调函数 function(filename, file_data, client_address)
            connect_callback: 客户端连接回调函数 function(client_address)
            disconnect_callback: 客户端断开回调函数 function(client_address)
        """
        self.on_text_received = text_callback
        self.on_file_received = file_callback
        self.on_client_connected = connect_callback
        self.on_client_disconnected = disconnect_callback