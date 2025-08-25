import tkinter as tk
from tkinter import ttk, messagebox
import pyautogui
import json
import threading
import time
from datetime import datetime, timedelta
import keyboard
import requests
import sys
import os

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # PyInstaller创建临时文件夹,将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class AutoClickerGUI:
    """
    自动点击器的图形界面类
    实现了坐标记录、定时执行、多线程点击等功能
    """
    
    def __init__(self, root):
        """
        初始化自动点击器
        Args:
            root: tkinter主窗口实例
        """
        # GUI相关
        self.root = root                  # 主窗口实例
        
        # 核心状态变量
        self.coordinates = []             # 存储所有记录的坐标点 [(x1,y1), (x2,y2),...]
        self.is_running = False           # 是否正在执行点击
        self.recording = False            # 是否处于录制状态
        self.scheduled_time = "20:00"     # 计划执行时间 "HH:MM"格式
        self.click_interval = 0.1         # 点击间隔时间(秒)
        self.last_record_time = 0         # 上次记录坐标的时间戳
        self.record_cooldown = 0.5        # 记录坐标的冷却时间(秒)
        self.update_timer = None          # 时间更新定时器

        # GUI组件
        self.status_label = None          # 状态显示标签
        self.coordinate_listbox = None    # 坐标列表显示框
        self.start_button = None          # 开始按钮
        self.stop_button = None           # 停止按钮
        self.clear_button = None          # 清空按钮
        self.interval_var = None          # 点击间隔输入变量

        # 文件路径
        self.coordinates_file = 'coordinates.json'    # 坐标保存文件
        self.settings_file = 'settings.json'         # 设置保存文件

        # 线程相关
        self.schedule_thread = None       # 定时任务线程
        self.update_time_thread = None    # 时间更新线程

        keyboard.on_press_key('esc', lambda _: self.emergency_stop())
        
        self.setup_gui()
        self.load_coordinates()
        self.load_settings()
        self.start_time_update()  # 启动时间更新
        
        # 启动定时任务和时间更新
        self.schedule_thread = threading.Thread(target=self.run_schedule, daemon=True)
        self.schedule_thread.start()
        self.update_time_thread = threading.Thread(target=self.update_network_time, daemon=True)
        self.update_time_thread.start()

    def get_network_time(self):
        """获取网络时间"""
        try:
            # 使用多个服务器交叉验证时间
            servers = [
                'https://www.baidu.com',
                'https://www.taobao.com',
                'https://www.jd.com'
            ]
            
            for server in servers:
                try:
                    start_time = time.time()
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    response = requests.get(server, headers=headers, timeout=2)
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        server_time = datetime.strptime(
                            response.headers['date'], 
                            '%a, %d %b %Y %H:%M:%S GMT'
                        )
                        
                        # 计算网络延迟并补偿
                        network_delay = (end_time - start_time) / 2
                        beijing_time = server_time + timedelta(hours=8, seconds=network_delay)
                        print(f"从 {server} 获取时间成功，网络延迟: {network_delay*1000:.2f}ms")
                        return beijing_time
                        
                except Exception as e:
                    print(f"从 {server} 获取时间失败: {str(e)}")
                    continue
                
            raise Exception("所有服务器都失败")
            
        except Exception as e:
            print(f"网络时间获取失败，使用本地时间: {str(e)}")
            return datetime.now()

    def update_network_time(self):
        """定期更新网络时间（毫秒级）"""
        while True:
            try:
                current_time = self.get_network_time()
                self.update_status_with_time(current_time)
                
                # 根据时间段调整更新频率
                current_hour = current_time.hour
                current_minute = current_time.minute
                current_second = current_time.second
                
                if (current_hour == 19 and current_minute == 59 and 
                    current_second >= 55):
                    time.sleep(0.01)  # 最后5秒，每10毫秒更新一次
                elif (current_hour == 19 and current_minute == 59 and 
                      current_second >= 50):
                    time.sleep(0.05)  # 最后10秒，每50毫秒更新一次
                elif (current_hour == 19 and current_minute == 59):
                    time.sleep(0.1)   # 最后1分钟，每100毫秒更新一次
                elif (current_hour == 19 and current_minute >= 58):
                    time.sleep(0.5)   # 最后2分钟，每500毫秒更新一次
                else:
                    time.sleep(10)     # 其他时间每10秒更新一次
                    
            except Exception as e:
                print(f"时间更新失败: {str(e)}")
                time.sleep(0.1)  # 出错后等待100毫秒再试
    def update_status_with_time(self, current_time):
        """这个方法现在只用于初始化显示"""
        pass  # 不再需要这个方法的实现

    def run_schedule(self):
        """运行定时任务（使用网络时间）"""
        while True:
            try:
                # 获取网络时间
                current_time = self.get_network_time()
                current_ms = int(time.time() * 1000) % 1000
                
                # 获取配置的时间
                scheduled_hour = int(self.scheduled_time.split(':')[0])
                scheduled_minute = int(self.scheduled_time.split(':')[1])
                
                # 打印详细的时间信息
                print(f"当前时间: {current_time.strftime('%H:%M:%S')}.{current_ms:03d}")
                print(f"目标时间: {scheduled_hour:02d}:{scheduled_minute:02d}:00.000")
                print(f"运行状态: {'运行中' if self.is_running else '等待中'}")
                
                # 更精确的时间判断
                is_target_time = (
                    current_time.hour == scheduled_hour and 
                    current_time.minute == scheduled_minute and 
                    current_time.second == 0 and 
                    current_ms >0 and  # 触发
                    not self.is_running
                )
                
                if is_target_time:
                    print(f"\n=== 触发执行时间 ===")
                    print(f"时间: {current_time.strftime('%H:%M:%S')}.{current_ms:03d}")
                    print(f"坐标数量: {len(self.coordinates)}")
                    self.root.after(0, self.start_clicking)
                    time.sleep(1)  # 等待1秒避免重复执行
                    continue
                
                # 动态调整检查频率
                if current_time.hour == scheduled_hour:
                    if current_time.minute == scheduled_minute:
                        time.sleep(0.001)  # 目标分钟：每1毫秒检查一次
                        print("高频检查中...")
                    elif current_time.minute == scheduled_minute - 1:
                        if current_time.second >= 55:
                            time.sleep(0.01)   # 最后5秒：每10毫秒检查一次
                            print("准备阶段...")
                        else:
                            time.sleep(0.1)    # 最后1分钟：每100毫秒检查一次
                    else:
                        time.sleep(1)          # 同一小时内：每秒检查一次
                else:
                    time.sleep(5)              # 其他时间：每5秒检查一次
                    
            except Exception as e:
                print(f"定时任务出错: {str(e)}")
                time.sleep(1)  # 出错后等待1秒再试

    def setup_gui(self):
        """设置图形界面，创建并布局所有GUI组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 坐标列表
        list_frame = ttk.LabelFrame(main_frame, text="记录的坐标", padding="5")
        list_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.coordinate_listbox = tk.Listbox(list_frame, height=10, width=40)
        self.coordinate_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.coordinate_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.coordinate_listbox.configure(yscrollcommand=scrollbar.set)
        
        # 控制按钮
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        ttk.Button(control_frame, text="开始录制坐标", command=self.toggle_recording).grid(row=0, column=0, padx=5)
        ttk.Button(control_frame, text="停止录制", command=self.stop_recording).grid(row=0, column=1, padx=5)
        ttk.Button(control_frame, text="清除所选坐标", command=self.delete_selected).grid(row=0, column=2, padx=5)
        ttk.Button(control_frame, text="清除所有坐标", command=self.clear_coordinates).grid(row=0, column=3, padx=5)
        
        # 运行控制
        run_frame = ttk.Frame(main_frame)
        run_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.start_button = ttk.Button(run_frame, text="开始执行", command=self.start_clicking)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(run_frame, text="停止执行", command=self.stop_clicking, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # 状态显示
        self.status_label = ttk.Label(main_frame, text="就绪")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=5)
        
        # 添加点击频率设置框架
        click_frame = ttk.LabelFrame(main_frame, text="点击频率设置", padding="5")
        click_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(click_frame, text="点击间隔(毫秒):").grid(row=0, column=0, padx=5)
        
        # 点击间隔输入
        self.interval_var = tk.StringVar(value=str(int(self.click_interval * 1000)))
        interval_spinbox = ttk.Spinbox(
            click_frame, 
            from_=1,  # 最小1毫秒
            to=1000,  # 最大1秒
            width=5,
            textvariable=self.interval_var
        )
        interval_spinbox.grid(row=0, column=1, padx=2)
        
        # 保存按钮
        ttk.Button(click_frame, text="保存频率设置", 
                   command=self.save_click_settings).grid(row=0, column=2, padx=5)
        
        # 时间设置框架（移到点击设置下面）
        time_frame = ttk.LabelFrame(main_frame, text="执行时间设置", padding="5")
        time_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(time_frame, text="执行时间:").grid(row=0, column=0, padx=5)
        
        # 小时选择
        self.hour_var = tk.StringVar(value=self.scheduled_time.split(':')[0])
        hour_spinbox = ttk.Spinbox(time_frame, from_=0, to=23, width=5, 
                                  textvariable=self.hour_var, format="%02.0f")
        hour_spinbox.grid(row=0, column=1, padx=2)
        
        ttk.Label(time_frame, text=":").grid(row=0, column=2)
        
        # 分钟选择
        self.minute_var = tk.StringVar(value=self.scheduled_time.split(':')[1])
        minute_spinbox = ttk.Spinbox(time_frame, from_=0, to=59, width=5,
                                    textvariable=self.minute_var, format="%02.0f")
        minute_spinbox.grid(row=0, column=3, padx=2)
        
        # 保存按钮
        ttk.Button(time_frame, text="保存时间设置", 
                   command=self.save_time_settings).grid(row=0, column=4, padx=5)

    def toggle_recording(self):
        """切换录制状态（开启/关闭录制模式）"""
        self.recording = True
        self.status_label.config(text="正在录制坐标... (按F8停止录制)")
        threading.Thread(target=self.record_coordinates, daemon=True).start()
    
    def stop_recording(self):
        """停止录制"""
        self.recording = False
        self.status_label.config(text="录制已停止")
    
    def record_coordinates(self):
        """
        记录坐标
        在录制模式下通过F9触发，记录当前鼠标坐标
        包含冷却时间控制，防止重复记录
        """
        while self.recording:
            if keyboard.is_pressed('F8'):  # 使用F8键停止录制
                self.stop_recording()
                break
            elif keyboard.is_pressed('F7'):  # 使用F9键记录坐标
                x, y = pyautogui.position()
                    # 检查该坐标是否已存在
                if (x, y) not in self.coordinates:
                    self.coordinates.append((x, y))
                    self.root.after(0, self.update_listbox)
                time.sleep(0.3)  # 防止重复记录
            time.sleep(0.1)
    
    def update_listbox(self):
        """更新坐标列表显示"""
        self.coordinate_listbox.delete(0, tk.END)
        for i, (x, y) in enumerate(self.coordinates):
            self.coordinate_listbox.insert(tk.END, f"坐标 {i+1}: ({x}, {y})")
    
    def delete_selected(self):
        """清除所选坐标"""
        selection = self.coordinate_listbox.curselection()
        if selection:
            index = selection[0]
            del self.coordinates[index]
            self.update_listbox()
    
    def clear_coordinates(self):
        """清空所有已记录的坐标，并更新显示和文件"""
        self.coordinates = []
        self.update_listbox()
    
    def save_coordinates(self):
        """将坐标保存到文件"""
        try:
            with open(self.coordinates_file, 'w') as f:
                json.dump(self.coordinates, f)
        except Exception as e:
            print(f"保存坐标失败: {str(e)}")
    
    def load_coordinates(self):
        """从文件加载保存的坐标"""
        try:
            if os.path.exists(self.coordinates_file):
                with open(self.coordinates_file, 'r') as f:
                    self.coordinates = json.load(f)
                self.update_listbox()
        except Exception as e:
            print(f"加载坐标失败: {str(e)}")
    
    def start_clicking(self):
        """开始执行点击任务，创建点击线程"""
        if not self.coordinates:
            messagebox.showwarning("警告", "没有记录的坐标！")
            return
                
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="正在执行点击...")
        
        threading.Thread(target=self.clicking_thread, daemon=True).start()
    
    def stop_clicking(self):
        """停止点击任务"""
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="已停止执行")
    
    def clicking_thread(self):
        """
        点击执行线程
        根据CPU核心数分组执行点击
        每组坐标由独立线程处理
        """
        import multiprocessing
        total_cores = multiprocessing.cpu_count()
        available_cores = max(1, total_cores//2 - 1)  # 预留2个核心，至少保留1个核心
        print(f"总CPU核心数: {total_cores}, 用于点击的核心数: {available_cores}")
        
        while self.is_running:
            try:
                # 计算每组大小：向上取整确保所有坐标都被分配
                total_coords = len(self.coordinates)
                coords_per_group = -(-total_coords // available_cores)  # 向上取整除法
                
                # 将坐标分组
                groups = []
                current_group = []
                for i, (x, y) in enumerate(self.coordinates):
                    current_group.append((i, x, y))
                    if len(current_group) == coords_per_group:
                        groups.append(current_group)
                        current_group = []
                if current_group:  # 处理剩余的坐标
                    groups.append(current_group)
                
                # 创建每组的点击函数
                def click_group(group):
                    for index, x, y in group:
                        pyautogui.doubleClick(x, y)
                        time.sleep(0.01)  # 组内点击间隔极短
                        pyautogui.doubleClick(x, y)  # 再次双击确保成功
                        print(f"双击坐标 {index+1}: ({x}, {y})")
                
                # 为每组创建线程
                threads = []
                for i, group in enumerate(groups):
                    t = threading.Thread(
                        target=lambda g=group: click_group(g),
                        daemon=True,
                        name=f"Group-{i+1}"
                    )
                    threads.append(t)
                
                # 同时启动所有组
                print(f"\n开始执行 {len(groups)} 组点击，每组约 {coords_per_group} 个坐标")
                for t in threads:
                    t.start()
                
                # 等待所有组完成
                for t in threads:
                    t.join(timeout=1.0)
                
                print(f"完成一轮点击\n")
                
                # 等待设定的间隔后进行下一轮
                time.sleep(self.click_interval)
                
            except Exception as e:
                print(f"点击执行出错: {str(e)}")
                time.sleep(0.1)
        
        print("点击线程结束")
    
    def emergency_stop(self):
        """紧急停止所有操作（ESC键触发）"""
        if self.is_running:
            self.is_running = False
            self.root.after(0, self.update_after_stop)

    def update_after_stop(self):
        """更新UI状态"""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        current_time = self.get_network_time()
        next_run = datetime.strptime(f"{current_time.date()} 20:00:00", "%Y-%m-%d %H:%M:%S")
        if current_time.time() >= datetime.strptime("20:00:00", "%H:%M:%S").time():
            next_run = next_run + timedelta(days=1)
        
        self.status_label.config(
            text=f"已停止执行 (按Esc键可随时停止)\n下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def on_closing(self):
        """窗口关闭时的清理操作"""
        self.stop_time_update()  # 停止时间更新
        self.save_coordinates()
        self.root.destroy()

    def save_time_settings(self):
        """保存时间设置"""
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                self.scheduled_time = f"{hour:02d}:{minute:02d}"
                self.save_settings()
                messagebox.showinfo("成功", f"执行时间已设置为 {self.scheduled_time}")
            else:
                messagebox.showerror("错误", "请输入有效的时间")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")

    def save_settings(self):
        """保存程序设置到文件"""
        try:
            settings = {
                'scheduled_time': self.scheduled_time,
                'click_interval': self.click_interval
            }
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            print(f"保存设置失败: {str(e)}")

    def load_settings(self):
        """从文件加载程序设置"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.scheduled_time = settings.get('scheduled_time', "20:00")
                    self.click_interval = settings.get('click_interval', 0.1)
        except Exception as e:
            print(f"加载设置失败: {str(e)}")
            self.scheduled_time = "20:00"
            self.click_interval = 0.1

    def save_click_settings(self):
        """保存点击频率设置"""
        try:
            interval_ms = int(self.interval_var.get())
            if 1 <= interval_ms <= 1000:
                self.click_interval = interval_ms / 1000  # 转换为秒
                self.save_settings()
                messagebox.showinfo("成功", f"点击间隔已设置为 {interval_ms} 毫秒")
            else:
                messagebox.showerror("错误", "请输入1-1000之间的数值")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")

    def start_time_update(self):
        """启动时间更新，定期更新显示的时间"""
        def update_display():
            try:
                # 获取网络时间
                current_time = self.get_network_time()
                current_ms = int(time.time() * 1000) % 1000
                
                # 计算下次执行时间
                next_run = datetime.strptime(
                    f"{current_time.date()} {self.scheduled_time}:00", 
                    "%Y-%m-%d %H:%M:%S"
                )
                if current_time.time() >= datetime.strptime(f"{self.scheduled_time}:00", "%H:%M:%S").time():
                    next_run = next_run + timedelta(days=1)
                
                # 更新显示
                status_text = f"当前网络时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}.{current_ms:03d}\n"
                status_text += f"下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}.000"
                
                self.status_label.config(text=status_text)
                
            except Exception as e:
                print(f"时间更新出错: {str(e)}")
            
            finally:
                # 确保下一次更新被调度
                if self.update_timer is not None:
                    self.update_timer = self.root.after(1000, update_display)  # 每秒更新一次
        
        # 开始第一次更新
        self.update_timer = self.root.after(0, update_display)

    def stop_time_update(self):
        """停止时间更新"""
        if self.update_timer is not None:
            self.root.after_cancel(self.update_timer)
            self.update_timer = None

def main():
    root = tk.Tk()
    root.title("定时点击器2025")
    app = AutoClickerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()