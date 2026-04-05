import os
import re
import sys
import json
import uuid
import queue
import threading
import subprocess
import configparser
import tkinter as tk  
import customtkinter as ctk
from tkinter import messagebox

# ================= 配置主题与全局常量 =================
ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue")  

# 可执行文件路径配置（源码运行填 python main.py，打包后填 ./chaoxing.exe）
#EXE_COMMAND = ["python", "main.py"]
EXE_COMMAND = ["./ChaoxingTool.exe"]

# 自适应系统编码，解决 Windows CMD 乱码问题
CMD_ENCODING = "gb18030" if sys.platform == "win32" else "utf-8"
# 过滤日志颜色的正则
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# 配置文件保存路径
HISTORY_FILE = "history_configs.json"
GLOBAL_CFG_FILE = "global_config.json"  # 核心1：新增全局配置文件

class ChaoXingGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("超星学习通多并发刷课工具 By-钢")
        self.geometry("1100x780")
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 核心状态管理字典
        self.processes = {} 
        self.acc_ui_elements = {} 
        self.log_textboxes = {}
        self.log_queues = {} 
        self.video_slots = {}  # 核心：存储微观视频并发卡槽
        

        # 核心1：加载历史数据和全局配置数据
        self.history_data = self.load_history() 
        self.global_data = self.load_global_config()
        # 启动视频进度本地模拟引擎，每秒更新一次
        self.after(1000, self.simulate_video_tick)
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        

        # ---------------- 1. 左侧导航栏 ----------------
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="chaoxing-Auto", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_account_tab = ctk.CTkButton(self.sidebar_frame, text="👤 账号运行页", command=lambda: self.select_frame("account"))
        self.btn_account_tab.grid(row=1, column=0, padx=20, pady=10)
        
        self.btn_history_tab = ctk.CTkButton(self.sidebar_frame, text="📜 历史配置库", command=lambda: self.select_frame("history"))
        self.btn_history_tab.grid(row=2, column=0, padx=20, pady=10)

        self.btn_config_tab = ctk.CTkButton(self.sidebar_frame, text="⚙️ 全局设置", command=lambda: self.select_frame("config"))
        self.btn_config_tab.grid(row=3, column=0, padx=20, pady=10)

        self.btn_log_tab = ctk.CTkButton(self.sidebar_frame, text="📝 运行日志", command=lambda: self.select_frame("log"))
        self.btn_log_tab.grid(row=4, column=0, padx=20, pady=10)

        # ---------------- 2. 各大内容页面初始化 ----------------
        self.init_account_frame()
        self.init_history_frame()
        self.init_config_frame()
        self.init_log_frame()

        self.add_account_card()
        self.select_frame("account")
        
    def on_closing(self):
        if self.processes:
            if not messagebox.askyesno("确认退出", "后台还有账号正在运行！\n确定要强行退出并结束所有任务吗？"):
                return
            for acc_id, p in self.processes.items():
                try:
                    p.terminate()
                except Exception:
                    pass
        self.destroy()
        os._exit(0)

    # ========================== 全局配置与持久化 ==========================
    def load_global_config(self):
        """加载全局 Token 配置"""
        if os.path.exists(GLOBAL_CFG_FILE):
            try:
                with open(GLOBAL_CFG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {"tiku_provider": "TikuYanxi", "tiku_token": ""}

    def save_global_config(self, event=None):
        """保存全局 Token 配置"""
        data = {
            "tiku_provider": self.tiku_combo.get(),
            "tiku_token": self.tiku_token_entry.get().strip()
        }
        try:
            with open(GLOBAL_CFG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def bind_context_menu(self, widget):
        menu = tk.Menu(self, tearoff=0, bg="#333333", fg="white", activebackground="#1f538d", activeforeground="white")
        menu.add_command(label="复制 (Copy)", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="粘贴 (Paste)", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_command(label="剪切 (Cut)", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_separator()
        menu.add_command(label="全选 (Select All)", command=lambda: widget.select_range(0, 'end') or widget.icursor('end'))

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu)

    def toggle_password_visibility(self, entry, btn):
        if entry.cget("show") == "*":
            entry.configure(show="")
            btn.configure(text="🙈") 
        else:
            entry.configure(show="*")
            btn.configure(text="👁")

    # ========================== 页面初始化逻辑 ==========================
    def init_account_frame(self):
        self.account_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.account_frame.grid_columnconfigure(0, weight=1)
        self.account_frame.grid_rowconfigure(1, weight=1)
        
        self.add_acc_frame = ctk.CTkFrame(self.account_frame)
        self.add_acc_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        self.btn_add_acc = ctk.CTkButton(self.add_acc_frame, text="➕ 添加新空白账号卡片", height=40, font=ctk.CTkFont(weight="bold"), command=self.add_account_card)
        self.btn_add_acc.pack(pady=15, padx=20, fill="x")

        self.acc_list_frame = ctk.CTkScrollableFrame(self.account_frame, label_text="账号配置列表 (独立控制运行状态)")
        self.acc_list_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")

    def init_history_frame(self):
        self.history_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.history_frame.grid_columnconfigure(0, weight=1)
        self.history_frame.grid_rowconfigure(1, weight=1)
        
        search_bar = ctk.CTkFrame(self.history_frame)
        search_bar.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        self.entry_search = ctk.CTkEntry(search_bar, placeholder_text="搜索账号 / 密码 / 备注", width=300)
        self.entry_search.pack(side="left", padx=15, pady=15)
        self.bind_context_menu(self.entry_search)
        
        btn_search = ctk.CTkButton(search_bar, text="🔍 搜索", width=80, command=self.render_history_list)
        btn_search.pack(side="left", padx=10)
        
        self.history_list_frame = ctk.CTkScrollableFrame(self.history_frame, label_text="本地保存的历史配置")
        self.history_list_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
    def init_config_frame(self):
        self.config_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.label_cfg = ctk.CTkLabel(self.config_frame, text="以下参数为所有账号通用的全局配置", font=ctk.CTkFont(size=16, weight="bold"))
        self.label_cfg.pack(pady=20, padx=20, anchor="w")
        
        self.tiku_frame = ctk.CTkFrame(self.config_frame)
        self.tiku_frame.pack(fill="x", padx=20, pady=10)
        
        # 核心1：使用全局配置文件初始化 UI 组件并绑定保存事件
        ctk.CTkLabel(self.tiku_frame, text="题库提供商:").grid(row=0, column=0, padx=10, pady=10)
        self.tiku_combo = ctk.CTkComboBox(self.tiku_frame, values=["TikuYanxi", "TikuLike", "TikuAdapter", "AI", "SiliconFlow"], command=self.save_global_config)
        self.tiku_combo.set(self.global_data.get("tiku_provider", "TikuYanxi"))
        self.tiku_combo.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(self.tiku_frame, text="全局题库Token/Key:").grid(row=0, column=2, padx=10, pady=10)
        self.tiku_token_entry = ctk.CTkEntry(self.tiku_frame, placeholder_text="填入Token或API Key(选填)", width=250)
        self.tiku_token_entry.insert(0, self.global_data.get("tiku_token", ""))
        self.tiku_token_entry.grid(row=0, column=3, padx=10, pady=10, sticky="w")
        
        self.bind_context_menu(self.tiku_token_entry) 
        self.tiku_token_entry.bind("<FocusOut>", self.save_global_config) # 失去焦点即保存
        
    def init_log_frame(self):
        self.log_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.log_frame.grid_rowconfigure(1, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)
        
        self.log_ctrl_frame = ctk.CTkFrame(self.log_frame, fg_color="transparent")
        self.log_ctrl_frame.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="ew")
        
        self.log_mode_var = ctk.StringVar(value="🌱 优雅模式")
        self.log_mode_seg = ctk.CTkSegmentedButton(
            self.log_ctrl_frame, 
            values=["🌱 优雅模式", "🔧 底层日志"], 
            variable=self.log_mode_var, 
            command=self.switch_log_mode
        )
        self.log_mode_seg.pack(side="left")
        
        # 👇 ================= 新增：自动滚动置底开关 ================= 👇
        # 找到 init_log_frame 方法中的这一段并替换：
        self.auto_scroll_var = ctk.StringVar(value="on")  # 改用 StringVar 更稳定
        self.auto_scroll_switch = ctk.CTkSwitch(
            self.log_ctrl_frame, 
            text="自动滚动置底", 
            variable=self.auto_scroll_var,
            onvalue="on",      # 明确开的值
            offvalue="off"     # 明确关的值
)
        self.auto_scroll_switch.pack(side="left", padx=20)
        # 👆 ======================================================== 👆
        
        self.log_tabs = ctk.CTkTabview(self.log_frame)
        self.log_tabs.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        
    def switch_log_mode(self, mode):
        for acc_id, log_dict in self.log_textboxes.items():
            txt_elegant = log_dict['txt_elegant']
            txt_raw = log_dict['txt_raw']
            if mode == "🌱 优雅模式":
                txt_raw.pack_forget()
                txt_elegant.pack(expand=True, fill="both")
            else:
                txt_elegant.pack_forget()
                txt_raw.pack(expand=True, fill="both")

    def select_frame(self, name):
        self.account_frame.grid_forget()
        self.history_frame.grid_forget()
        self.config_frame.grid_forget()
        self.log_frame.grid_forget()

        if name == "account":
            self.account_frame.grid(row=0, column=1, sticky="nsew")
        elif name == "history":
            self.render_history_list()
            self.history_frame.grid(row=0, column=1, sticky="nsew")
        elif name == "config":
            self.config_frame.grid(row=0, column=1, sticky="nsew")
        elif name == "log":
            self.log_frame.grid(row=0, column=1, sticky="nsew")

    # ========================== 历史配置数据处理 ==========================
    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return []
        return []

    def save_history(self):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history_data, f, ensure_ascii=False, indent=2)

    def save_card_to_history(self, acc_id):
        self.save_global_config() # 同时保存全局配置
        
        ui = self.acc_ui_elements.get(acc_id)
        if not ui: return
        
        phone = ui['phone'].get().strip()
        if not phone:
            messagebox.showwarning("警告", "必须填写手机号才能保存配置！")
            return

        data = {
            "phone": phone,
            "pwd": ui['pwd'].get().strip(),
            "remark": ui['remark'].get().strip(),
            "courses": ui['courses'].get().strip(),
            "tiku": ui['tiku'].get() == 1,
            "submit": ui['submit'].get() == 1,
            "cover_rate": ui['cover_rate'].get().strip() or "0.9",
            "speed": ui['speed'].get(),
            "jobs": ui['jobs'].get()
        }

        updated = False
        for item in self.history_data:
            if item.get("phone") == phone:
                item.update(data)
                updated = True
                break
        if not updated:
            self.history_data.append(data)
            
        self.save_history()
        messagebox.showinfo("成功", f"账号 [{phone}] 的配置已成功保存！")

    def delete_history_item(self, phone):
        if messagebox.askyesno("确认", f"确定要从历史配置中永久删除账号 [{phone}] 吗？"):
            self.history_data = [item for item in self.history_data if item.get("phone") != phone]
            self.save_history()
            self.render_history_list()

    def render_history_list(self):
        for widget in self.history_list_frame.winfo_children():
            widget.destroy()
            
        keyword = self.entry_search.get().strip().lower()
        
        for item in self.history_data:
            phone = item.get("phone", "")
            pwd = item.get("pwd", "")
            remark = item.get("remark", "")
            
            if keyword and not (keyword in phone.lower() or keyword in pwd.lower() or keyword in remark.lower()):
                continue
                
            self.create_history_card(item)

    def create_history_card(self, data):
        card = ctk.CTkFrame(self.history_list_frame, border_width=1, border_color="#555555")
        card.pack(fill="x", pady=8, padx=5)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)
        
        display_text = f"📱 账号: {data.get('phone')}"
        if data.get("remark"):
            display_text += f"   |   📝 备注: {data.get('remark')}"
            
        ctk.CTkLabel(header, text=display_text, font=ctk.CTkFont(weight="bold")).pack(side="left")

        btn_load = ctk.CTkButton(header, text="📥 一键加载", fg_color="#2b8a3e", hover_color="#237032", width=80,
                                 command=lambda d=data: self.load_preset_to_account(d))
        btn_load.pack(side="right", padx=10)
        
        btn_del = ctk.CTkButton(header, text="🗑️ 删除", fg_color="#8B0000", hover_color="#5C0000", width=60,
                                command=lambda p=data.get("phone"): self.delete_history_item(p))
        btn_del.pack(side="right", padx=10)

        details = ctk.CTkFrame(card, fg_color="transparent")
        info_text = (
            f"🔑 密码: {data.get('pwd')}    📚 指定课程: {data.get('courses') or '全部'}\n"
            f"⚙️ 启用题库: {'是' if data.get('tiku') else '否'}    📝 自动提交: {'是' if data.get('submit') else '否'}    "
            f"🎯 最低搜到率: {data.get('cover_rate')}\n"
            f"▶ 倍速: {data.get('speed')}x    ⚡ 并发数: {data.get('jobs')}"
        )
        ctk.CTkLabel(details, text=info_text, justify="left").pack(side="left", padx=10, pady=10)

        def toggle_details(d_frame=details, b_toggle=None):
            if d_frame.winfo_ismapped():
                d_frame.pack_forget()
                b_toggle.configure(text="🔽 展开详情")
            else:
                d_frame.pack(fill="x", padx=10)
                b_toggle.configure(text="🔼 收起")

        btn_toggle = ctk.CTkButton(header, text="🔽 展开详情", width=80, fg_color="#444444", 
                                   command=lambda: toggle_details(b_toggle=btn_toggle))
        btn_toggle.pack(side="right", padx=10)

    def load_preset_to_account(self, data):
        self.add_account_card(preset_data=data)
        self.select_frame("account")

    # ========================== 账号运行卡片管理 ==========================
    def add_account_card(self, preset_data=None):
        acc_id = str(uuid.uuid4())[:8]  
        
        card_frame = ctk.CTkFrame(self.acc_list_frame, border_width=1, border_color="#333333")
        card_frame.pack(fill="x", pady=10, padx=5)

        card_frame.columnconfigure((1, 3, 5), weight=1)

        ctk.CTkLabel(card_frame, text="📱 手机号:").grid(row=0, column=0, padx=5, pady=10, sticky="e")
        entry_phone = ctk.CTkEntry(card_frame, placeholder_text="学习通手机号")
        entry_phone.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.bind_context_menu(entry_phone)

        ctk.CTkLabel(card_frame, text="🔑 密码:").grid(row=0, column=2, padx=5, pady=10, sticky="e")
        pwd_inner_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
        pwd_inner_frame.grid(row=0, column=3, padx=5, pady=10, sticky="ew")
        pwd_inner_frame.columnconfigure(0, weight=1)

        entry_pwd = ctk.CTkEntry(pwd_inner_frame, show="*", placeholder_text="输入密码")
        entry_pwd.grid(row=0, column=0, sticky="ew")
        self.bind_context_menu(entry_pwd)

        btn_eye = ctk.CTkButton(pwd_inner_frame, text="👁", width=30, fg_color="#444444", hover_color="#555555",
                                command=lambda: self.toggle_password_visibility(entry_pwd, btn_eye))
        btn_eye.grid(row=0, column=1, padx=(5, 0))

        ctk.CTkLabel(card_frame, text="📝 备注:").grid(row=0, column=4, padx=5, pady=10, sticky="e")
        entry_remark = ctk.CTkEntry(card_frame, placeholder_text="例: 张三的大物课")
        entry_remark.grid(row=0, column=5, padx=5, pady=10, sticky="ew")
        self.bind_context_menu(entry_remark)

        ctk.CTkLabel(card_frame, text="📚 课程ID:").grid(row=1, column=0, padx=5, pady=10, sticky="e")
        entry_courses = ctk.CTkEntry(card_frame, placeholder_text="留空则自动挂机所有课程")
        entry_courses.grid(row=1, column=1, columnspan=4, padx=5, pady=10, sticky="ew")
        self.bind_context_menu(entry_courses)

        btn_refetch = ctk.CTkButton(card_frame, text="🔄 重新获取ID", width=100, fg_color="#2b8a3e", hover_color="#237032",
                                    command=lambda: self.fetch_courses_for_card(entry_phone.get(), entry_pwd.get(), entry_courses, btn_refetch))
        btn_refetch.grid(row=1, column=5, padx=5, pady=10, sticky="w")

        frame_tiku = ctk.CTkFrame(card_frame, fg_color="transparent")
        frame_tiku.grid(row=2, column=0, columnspan=6, sticky="ew", padx=5, pady=5)
        
        switch_tiku = ctk.CTkSwitch(frame_tiku, text="启用题库 (答题)")
        switch_tiku.pack(side="left", padx=(10, 20))

        switch_submit = ctk.CTkSwitch(frame_tiku, text="自动提交")
        switch_submit.pack(side="left", padx=20)
        
        ctk.CTkLabel(frame_tiku, text="最低搜到率:").pack(side="left", padx=(10, 5))
        entry_cover = ctk.CTkEntry(frame_tiku, width=60)
        entry_cover.pack(side="left")
        self.bind_context_menu(entry_cover)

        frame_speed = ctk.CTkFrame(card_frame, fg_color="transparent")
        frame_speed.grid(row=3, column=0, columnspan=6, sticky="ew", padx=5, pady=5)
        
        ctk.CTkLabel(frame_speed, text="▶ 播放倍速:").pack(side="left", padx=(10, 5))
        combo_speed = ctk.CTkComboBox(frame_speed, values=["1.0", "1.25", "1.5", "1.75", "2.0"], width=80)
        combo_speed.pack(side="left", padx=(0, 20))
        
        ctk.CTkLabel(frame_speed, text="⚡ 并发章节数:").pack(side="left", padx=(10, 5))
        combo_jobs = ctk.CTkComboBox(frame_speed, values=["1", "2", "3", "4", "5", "6"], width=80)
        combo_jobs.pack(side="left")

        ctrl_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
        ctrl_frame.grid(row=4, column=0, columnspan=6, pady=(5, 10), sticky="e")

        btn_del = ctk.CTkButton(ctrl_frame, text="删除卡片", fg_color="#8B0000", hover_color="#5C0000", width=80,
                                command=lambda: self.delete_account_card(acc_id))
        btn_del.pack(side="left", padx=10)
        
        btn_save = ctk.CTkButton(ctrl_frame, text="💾 保存配置", fg_color="#006400", hover_color="#004d00", width=80,
                                command=lambda: self.save_card_to_history(acc_id))
        btn_save.pack(side="left", padx=10)

        btn_stop = ctk.CTkButton(ctrl_frame, text="⏹ 停止任务", fg_color="red", width=80, state="disabled",
                                 command=lambda: self.stop_process(acc_id))
        btn_stop.pack(side="right", padx=10)

        btn_start = ctk.CTkButton(ctrl_frame, text="▶ 开始运行", width=100,
                                  command=lambda: self.start_process(acc_id))
        btn_start.pack(side="right", padx=10)

        if preset_data:
            entry_phone.insert(0, preset_data.get("phone", ""))
            entry_pwd.insert(0, preset_data.get("pwd", ""))
            entry_remark.insert(0, preset_data.get("remark", ""))
            entry_courses.insert(0, preset_data.get("courses", ""))
            entry_cover.insert(0, preset_data.get("cover_rate", "0.9"))
            combo_speed.set(preset_data.get("speed", "1.0"))
            combo_jobs.set(str(preset_data.get("jobs", "4")))
            if preset_data.get("tiku", True): switch_tiku.select()
            else: switch_tiku.deselect()
            if preset_data.get("submit", False): switch_submit.select()
            else: switch_submit.deselect()
        else:
            entry_cover.insert(0, "0.9")
            combo_speed.set("1.0")
            combo_jobs.set("4")
            switch_tiku.select()
            switch_submit.deselect()

        self.acc_ui_elements[acc_id] = {
            'frame': card_frame, 'phone': entry_phone, 'pwd': entry_pwd, 'remark': entry_remark,
            'courses': entry_courses, 'tiku': switch_tiku, 'submit': switch_submit,
            'cover_rate': entry_cover, 'speed': combo_speed, 'jobs': combo_jobs,
            'btn_refetch': btn_refetch, 'btn_start': btn_start, 'btn_stop': btn_stop, 'btn_del': btn_del
        }

    def delete_account_card(self, acc_id):
        if messagebox.askyesno("确认", "确定要关闭并删除当前的运行卡片吗？"):
            self.stop_process(acc_id)  
            ui = self.acc_ui_elements.pop(acc_id, None)
            if ui:
                ui['frame'].destroy()
            if acc_id in self.log_textboxes:
                tab_id = self.log_textboxes[acc_id]['tab_id']
                try: self.log_tabs.delete(tab_id)
                except: pass
                del self.log_textboxes[acc_id]
            if acc_id in self.log_queues:
                del self.log_queues[acc_id]

    def fetch_courses_for_card(self, phone, pwd, target_entry, btn_widget):
        phone = phone.strip()
        pwd = pwd.strip()
        if not phone or not pwd:
            messagebox.showwarning("警告", "请先在当前卡片输入手机号和密码！")
            return
            
        btn_widget.configure(state="disabled", text="登录查询中...")
        threading.Thread(target=self._fetch_courses_thread, args=(phone, pwd, target_entry, btn_widget), daemon=True).start()

    def _fetch_courses_thread(self, phone, pwd, target_entry, btn_widget):
        cfg_path = f"config_temp_fetch_{phone}.ini"
        config = configparser.ConfigParser()
        config["common"] = {
            "use_cookies": "false", "username": phone, "password": pwd,
            "course_list": "", "speed": "1.0", "jobs": "1", "notopen_action": "retry"
        }
        with open(cfg_path, "w", encoding="utf-8") as f:
            config.write(f)
            
        cmd = EXE_COMMAND + ["-c", cfg_path]
        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding=CMD_ENCODING, errors="replace", startupinfo=startupinfo
            )
            
            courses = []
            in_list = False
            error_msg = None
            
            for line in iter(process.stdout.readline, ''):
                clean_line = ANSI_ESCAPE.sub('', line).strip()
                
                if "登录失败" in clean_line or "密码错误" in clean_line or "LoginError" in clean_line:
                    error_msg = clean_line.split("-")[-1].strip() if "-" in clean_line else "账号或密码错误"
                    break
                    
                if "**********课程列表**********" in clean_line:
                    in_list = True
                    continue
                    
                if in_list:
                    if "****************************" in clean_line: break 
                    if clean_line.startswith("ID:"):
                        parts = clean_line.split("课程名:")
                        if len(parts) == 2:
                            courses.append((parts[0].replace("ID:", "").strip(), parts[1].strip()))
            
            process.terminate()
            try: os.remove(cfg_path)
            except: pass
                
            if error_msg: self.after(0, lambda: messagebox.showerror("登录失败", error_msg))
            elif not courses: self.after(0, lambda: messagebox.showwarning("提示", "未获取到课程列表，请检查账号状态。"))
            else: self.after(0, self.show_course_dialog, courses, target_entry)
                
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("执行错误", str(e)))
        finally:
            self.after(0, lambda: btn_widget.configure(state="normal", text="🔄 重新获取ID"))

    def show_course_dialog(self, courses, target_entry):
        dialog = ctk.CTkToplevel(self)
        dialog.title("请选择要学习的课程")
        dialog.geometry("400x500")
        dialog.grab_set() 
        dialog.focus_force()
        
        lbl = ctk.CTkLabel(dialog, text="勾选下方需要自动挂机的课程：", font=ctk.CTkFont(weight="bold"))
        lbl.pack(pady=10, padx=10, anchor="w")
        
        scroll = ctk.CTkScrollableFrame(dialog)
        scroll.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 优化点1：使用列表存放数据，将格式化后的 "课程名(ID)" 作为复选框的真实值
        self.course_items = []
        for c_id, c_name in courses:
            var = ctk.StringVar(value="0")
            formatted_val = f"{c_name}({c_id})"  # 组合出“课程名(ID)”格式
            self.course_items.append({'var': var, 'val': formatted_val})
            
            display_name = c_name if len(c_name) < 22 else c_name[:20] + "..."
            # 优化点2：onvalue 设为完整的格式化字符串，而非纯数字 ID
            cb = ctk.CTkCheckBox(scroll, text=display_name, variable=var, onvalue=formatted_val, offvalue="0")
            cb.pack(pady=8, padx=5, anchor="w")
            
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        
        def on_confirm():
            # 获取选中的值，此时选中的已经是类似 "古典诗词鉴赏(12345)" 的完整字符串
            selected = [item['var'].get() for item in self.course_items if item['var'].get() != "0"]
            target_entry.delete(0, 'end')
            if selected: target_entry.insert(0, ", ".join(selected))
            dialog.destroy()
            
        # 优化点3：全选和清空逻辑适配新数据结构
        ctk.CTkButton(btn_frame, text="全选", width=60, command=lambda: [item['var'].set(item['val']) for item in self.course_items]).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="清空", width=60, command=lambda: [item['var'].set("0") for item in self.course_items]).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="确定", command=on_confirm).pack(side="right", padx=10)

        # ========================== 账号运行逻辑 ==========================
    def generate_config_for_account(self, acc_id, parsed_course_ids_str="0"):
        ui = self.acc_ui_elements[acc_id]
        phone = ui['phone'].get().strip()
        pwd = ui['pwd'].get().strip()
        
        tiku_enable = ui['tiku'].get()
        tiku_submit = ui['submit'].get()
        cover_rate_val = ui['cover_rate'].get().strip() or "0.9"
        speed_val = ui['speed'].get()
        jobs_val = ui['jobs'].get()

        config = configparser.ConfigParser()
        config["common"] = {
            "use_cookies": "false", "username": phone, "password": pwd,
            "course_list": parsed_course_ids_str,  # 强制使用过滤后的纯数字
            "speed": speed_val, "jobs": jobs_val, "notopen_action": "retry"
        }
        
        if tiku_enable:
            tiku_token = self.tiku_token_entry.get().strip()
            config["tiku"] = {
                "provider": self.tiku_combo.get(), 
                "submit": "true" if tiku_submit else "false",
                "cover_rate": cover_rate_val, "delay": "1.0", "true_list": "正确,对,√,是", "false_list": "错误,错,×,否,不对,不正确",
                "tokens": tiku_token, "url": tiku_token, "endpoint": "", "key": tiku_token, "model": "", 
                "min_interval_seconds": "3", "http_proxy": "", "likeapi_search": "false", "likeapi_vision": "true",
                "likeapi_model": "glm-4.5-air", "likeapi_retry": "true", "likeapi_retry_times": "3",
                "siliconflow_key": tiku_token, "siliconflow_model": "deepseek-ai/DeepSeek-R1",
                "siliconflow_endpoint": "https://api.siliconflow.cn/v1/chat/completions"
            }
        
        config_filename = f"config_temp_{acc_id}.ini"
        with open(config_filename, "w", encoding="utf-8") as f:
            config.write(f)
        return config_filename



    def start_process(self, acc_id):
        ui = self.acc_ui_elements[acc_id]
        phone = ui['phone'].get().strip()
        pwd = ui['pwd'].get().strip()

        if not phone or not pwd:
            messagebox.showwarning("警告", "账号和密码不能为空！")
            return
            
        if acc_id in self.processes: return

        self.save_global_config() 
        self.save_card_to_history(acc_id)

        ui['btn_start'].configure(state="disabled", text="运行中...")
        ui['btn_stop'].configure(state="normal")
        ui['phone'].configure(state="disabled")
        ui['pwd'].configure(state="disabled")
        ui['remark'].configure(state="disabled")
        
        # ================= 核心：课程数据的解析与分离 =================
        raw_courses = ui['courses'].get().strip()
        course_ids_for_config = []
        course_display_names = []

        if raw_courses:
            # 按照逗号或换行分割多个课程
            course_items = re.split(r'[,，\n]+', raw_courses)
            for item in course_items:
                item = item.strip()
                if not item: continue
                
                # 提取出所有的数字作为配置用的 ID
                id_match = re.search(r'\d+', item)
                if id_match:
                    course_id = id_match.group(0)
                    course_ids_for_config.append(course_id)
                    
                    # 提取非数字部分作为课程名（去除括号等无用符号）
                    name_part = re.sub(r'[\d\(\)（）]', '', item).strip()
                    if name_part:
                        course_display_names.append(f"【{name_part}】({course_id})")
                    else:
                        course_display_names.append(f"ID:{course_id}")
        
        # 1. 组装给底层 config 用的纯数字字符串 (为空则走自动全扫 "0")
        parsed_course_ids_str = ",".join(course_ids_for_config) if course_ids_for_config else "0"
        cfg_path = self.generate_config_for_account(acc_id, parsed_course_ids_str)
        
        # 2. 组装给宏观 UI 展示用的优雅队列文本
        if course_display_names:
            display_text = ", ".join(course_display_names)
            initial_queue_text = f"⏳ 待处理课程队列: {display_text} (共 {len(course_display_names)} 门)"
        else:
            initial_queue_text = "⏳ 待处理课程队列: 自动扫描账号下所有未完成课程"
        # ==============================================================

        remark = ui['remark'].get().strip()
        tab_name = remark if remark else phone
        tab_id = f"{tab_name} [{acc_id[:4]}]" 
        
        if acc_id not in self.log_textboxes:
            self.log_tabs.add(tab_id)
            tab = self.log_tabs.tab(tab_id)
            
            # ================= 顶部：三级状态监控面板 =================
            status_panel_frame = ctk.CTkFrame(tab, fg_color="#242424", border_width=1, border_color="#444444")
            status_panel_frame.pack(side="top", fill="x", padx=5, pady=(10, 5))
            
            # 【第一层】宏观队列 (使用正则解析生成的 initial_queue_text)
            lbl_queue = ctk.CTkLabel(status_panel_frame, text=initial_queue_text, 
                                     font=("Microsoft YaHei", 12), text_color="#A0A0A0")
            lbl_queue.pack(side="top", anchor="w", padx=10, pady=(5, 0))
            
            # 【第二层】中观课程
            lbl_current_course = ctk.CTkLabel(status_panel_frame, text="▶ 当前暂无活跃课程...", 
                                              font=("Microsoft YaHei", 14, "bold"), text_color="#E6A23C")
            lbl_current_course.pack(side="top", anchor="w", padx=10, pady=(2, 5))

            # 👇 ==== 【第三层】微观并发卡槽 (核心修改区) ==== 👇
            # 将普通的 CTkFrame 替换为 CTkScrollableFrame，并强制设定 height=150
            video_slots_frame = ctk.CTkScrollableFrame(status_panel_frame, height=150, fg_color="transparent")
            # 严格控制 pack 属性：使用 fill="x" 即可，绝对不要加 expand=True，把剩余高度全部留给下方的日志框
            video_slots_frame.pack(side="top", fill="x", padx=10, pady=(0, 5))
            
            try:
                jobs_count = int(ui['jobs'].get())
            except ValueError:
                jobs_count = 4 
            
            self.video_slots[acc_id] = []
            
            # 在受限高度的滚动面板内生成动态卡槽
            for i in range(jobs_count):
                slot_frame = ctk.CTkFrame(video_slots_frame, fg_color="transparent")
                slot_frame.pack(side="top", fill="x", pady=2)
                
                lbl_video = ctk.CTkLabel(slot_frame, text=f"[空闲槽位 {i+1}] 等待分配视频任务...", font=("Microsoft YaHei", 12))
                lbl_video.pack(side="top", anchor="w")
                
                bar_video = ctk.CTkProgressBar(slot_frame, height=10)
                bar_video.set(0.0)
                bar_video.pack(side="top", fill="x")
                
                self.video_slots[acc_id].append({
                    'is_free': True, 'task_name': '', 'total': 0, 'current': 0,
                    'label_widget': lbl_video, 'bar_widget': bar_video, 'default_color': bar_video.cget("progress_color") 
                })
            # 👆 ========================================= 👆

            # ================= 底部：日志文本框 =================
            txt_elegant = ctk.CTkTextbox(tab, font=("Microsoft YaHei", 12), spacing1=3, spacing3=3)
            txt_raw = ctk.CTkTextbox(tab, font=("Consolas", 12), fg_color="#1e1e1e", text_color="#cccccc")

            
            if self.log_mode_var.get() == "🌱 优雅模式":
                txt_elegant.pack(expand=True, fill="both")
            else:
                txt_raw.pack(expand=True, fill="both")
                
            self.log_textboxes[acc_id] = {
                'txt_elegant': txt_elegant, 'txt_raw': txt_raw,
                'lbl_queue': lbl_queue, 'lbl_current_course': lbl_current_course,
                'current_course_name': '', 'queue_base_text': initial_queue_text, 'tab_id': tab_id
            }
        else:
            self.log_textboxes[acc_id]['txt_elegant'].insert("end", "\n\n--- 重新启动 ---\n\n")
            self.log_textboxes[acc_id]['txt_raw'].insert("end", "\n\n--- 重新启动 ---\n\n")
            # 重启时恢复由正则解析出来的全新队列文本
            self.log_textboxes[acc_id]['lbl_queue'].configure(text=initial_queue_text)
            self.log_textboxes[acc_id]['lbl_current_course'].configure(text="▶ 当前暂无活跃课程...")
            self.log_textboxes[acc_id]['current_course_name'] = ""
            self.log_textboxes[acc_id]['queue_base_text'] = initial_queue_text
            for i, slot in enumerate(self.video_slots.get(acc_id, [])):
                self.reset_video_slot(slot, i)

        self.select_frame("log")
        self.log_tabs.set(tab_id)

        self.log_queues[acc_id] = queue.Queue()
        self.after(50, self.flush_log_queue, acc_id)

        cmd = EXE_COMMAND + ["-c", cfg_path, "-v"]
        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding=CMD_ENCODING, errors="replace", startupinfo=startupinfo
            )
            self.processes[acc_id] = process
            
            t = threading.Thread(target=self.read_process_output, args=(process, acc_id), daemon=True)
            t.start()
            
        except Exception as e:
            self.log_textboxes[acc_id]['txt_elegant'].insert("end", f"❌ 启动失败: {e}\n")
            self.log_textboxes[acc_id]['txt_raw'].insert("end", f"启动失败: {e}\n")
            self.reset_ui_state(acc_id)

    # ================ 核心双擎日志与状态拦截 ================
    def read_process_output(self, process, acc_id):
        q = self.log_queues.get(acc_id)
        if not q: return
        buffer = []
        
        while True:
            char = process.stdout.read(1)
            if not char: break
            
            if char == '\n':
                q.put(('append', ANSI_ESCAPE.sub('', "".join(buffer) + '\n')))
                buffer = []
            elif char == '\r':
                q.put(('overwrite', ANSI_ESCAPE.sub('', "".join(buffer))))
                buffer = []
            else:
                buffer.append(char)

        process.wait()
        msg = f"\n[ 进程已结束，退出码：{process.returncode} ]\n"
        q.put(('append', msg))
        self.after(100, self.reset_ui_state, acc_id)

    def format_elegant_log(self, content):
        pattern = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\s+\|\s+([A-Z]+)\s*\|\s+[^\s]+\s+-\s+(.*)'
        match = re.search(pattern, content)
        if match:
            level = match.group(1).strip()
            msg = match.group(2).strip()
            if level in ["DEBUG", "TRACE"]:
                return None
            
            icon_map = {"INFO": "🌱", "WARNING": "⚠️", "ERROR": "❌", "SUCCESS": "✅"}
            return f"{icon_map.get(level, '🔹')} {msg}\n"
        
        if not content.strip() or "%|" in content or "it/s]" in content:
            return None
            
        return content

    def flush_log_queue(self, acc_id):
        if acc_id not in self.log_queues or acc_id not in self.log_textboxes:
            return
            
        q = self.log_queues[acc_id]
        ui_data = self.log_textboxes[acc_id]
        txt_elegant = ui_data['txt_elegant']
        txt_raw = ui_data['txt_raw']
        lbl_queue = ui_data['lbl_queue']
        lbl_current_course = ui_data['lbl_current_course']
        
        slots = self.video_slots.get(acc_id, [])
        processed = False
        
        # 定义需要拦截的所有正则表达式
        pattern_total_courses = r'当前课程任务数量:\s*(\d+)'
        pattern_course_start = r'开始学习课程:\s*(.*)'
        pattern_unfinished = r'unfinished task:\s*(\d+)'
        pattern_video_start = r'开始任务:\s*(.*?),\s*总时长:\s*(\d+)s,\s*已进行:\s*(\d+)s'
        pattern_video_finish = r'任务(?:瞬间)?完成:\s*(.*)'
        # 脏日志拦截，防止污染优雅视图
        pattern_rt = r'Got rt:\s*([\d\.]+)'
        pattern_tqdm = r'(\d+)/(\d+)'

        while not q.empty():
            processed = True
            try:
                msg_type, content = q.get_nowait()
                is_status_log = False

                # ==== 事件 A: 拦截总课程数量 ====
                match_total = re.search(pattern_total_courses, content)
                if match_total:
                    total_num = match_total.group(1)
                    base_text = ui_data.get('queue_base_text', '')
                    lbl_queue.configure(text=f"{base_text}  (共发现 {total_num} 门待刷课程)")
                    is_status_log = True

                # ==== 事件 B: 拦截具体课程开始 ====
                match_course = re.search(pattern_course_start, content)
                if match_course:
                    course_name = match_course.group(1).strip()
                    ui_data['current_course_name'] = course_name
                    lbl_current_course.configure(text=f"📚 当前课程: 【{course_name}】 | 任务点: 正在扫描章节...")
                    is_status_log = True

                # ==== 事件 C: 拦截未完成任务点 ====
                match_unfinished = re.search(pattern_unfinished, content)
                if match_unfinished:
                    tasks_left = match_unfinished.group(1)
                    course_name = ui_data.get('current_course_name', '未知课程')
                    if course_name:
                        lbl_current_course.configure(text=f"📚 当前课程: 【{course_name}】 | 🔥 剩余未完成任务点: {tasks_left} 个")
                    is_status_log = True

                # ==== 事件 D: 拦截视频任务开始分配卡槽 ====
                match_v_start = re.search(pattern_video_start, content)
                if match_v_start:
                    video_name = match_v_start.group(1).strip()
                    total_s = float(match_v_start.group(2))
                    current_s = float(match_v_start.group(3))
                    
                    for slot in slots:
                        if slot['is_free']:
                            slot['is_free'] = False
                            slot['task_name'] = video_name
                            slot['total'] = total_s
                            slot['current'] = current_s
                            
                            ratio = current_s / total_s if total_s > 0 else 0.0
                            slot['bar_widget'].configure(progress_color=slot['default_color'])
                            slot['bar_widget'].set(min(1.0, ratio))
                            slot['label_widget'].configure(text=f"▶ 正在播放: {video_name} ({int(current_s)}s / {int(total_s)}s)", text_color=("black", "white"))
                            break
                    is_status_log = True
                    
                # ==== 事件 E: 拦截视频任务完成释放卡槽 ====
                match_v_finish = re.search(pattern_video_finish, content)
                if match_v_finish:
                    video_name = match_v_finish.group(1).strip()
                    for i, slot in enumerate(slots):
                        if not slot['is_free'] and slot['task_name'] == video_name:
                            slot['bar_widget'].configure(progress_color="#2b8a3e") # 变绿
                            slot['bar_widget'].set(1.0)
                            slot['label_widget'].configure(text=f"✅ 播放完毕: {video_name}", text_color="#2b8a3e")
                            self.after(2000, lambda s=slot, idx=i: self.reset_video_slot(s, idx))
                            break
                    is_status_log = True
                
                # ==== 拦截心跳包和 \r ====
                elif msg_type == 'overwrite' or re.search(pattern_rt, content) or (msg_type == 'overwrite' and re.search(pattern_tqdm, content)):
                    is_status_log = True

                # ----------------- 写入文本框分发 -----------------
                if msg_type == 'append': 
                    txt_raw.insert("end", content)
                elif msg_type == 'overwrite':
                    txt_raw.delete("end-1l linestart", "end")
                    txt_raw.insert("end", content)
                
                if not is_status_log:
                    elegant_content = content
                    if msg_type == 'append':
                        elegant_content = self.format_elegant_log(content)
                    if elegant_content is not None:
                        if msg_type == 'append': 
                            txt_elegant.insert("end", elegant_content)
                        elif msg_type == 'overwrite':
                            txt_elegant.delete("end-1l linestart", "end")
                            txt_elegant.insert("end", elegant_content)
                            
            except queue.Empty:
                break
        # 👇 ================= 修改：加入开关状态判断 ================= 👇
        # 只有当有新日志处理过，且用户打开了“自动滚动置底”开关时，才强制拉到底部
        if processed and self.auto_scroll_var.get() == "on": 
            # 使用更底层的强力滚动方法，确保100%置底，且关闭时不干扰视图
            txt_raw._textbox.yview_moveto(1.0)
            txt_elegant._textbox.yview_moveto(1.0)
            
        if acc_id in self.processes: 
            self.after(50, self.flush_log_queue, acc_id)
        if processed: 
            txt_raw.see("end")
            txt_elegant.see("end")

    def stop_process(self, acc_id):
        if acc_id in self.processes:
            self.processes[acc_id].terminate() 
            msg = "\n[ 用户手动强制终止了该账号的任务 ]\n"
            if acc_id in self.log_queues:
                self.log_queues[acc_id].put(('append', msg))
            self.reset_ui_state(acc_id)
            
    def reset_ui_state(self, acc_id):
        if acc_id in self.processes:
            del self.processes[acc_id]
        if acc_id in self.acc_ui_elements:
            ui = self.acc_ui_elements[acc_id]
            ui['btn_start'].configure(state="normal", text="▶ 开始运行")
            ui['btn_stop'].configure(state="disabled")
            ui['phone'].configure(state="normal")
            ui['pwd'].configure(state="normal")
            ui['remark'].configure(state="normal")
    def reset_video_slot(self, slot, index):
        """延迟回调：将卡槽状态重置为空闲"""
        slot['is_free'] = True
        slot['task_name'] = ''
        slot['total'] = 0
        slot['current'] = 0
        slot['bar_widget'].configure(progress_color=slot['default_color'])
        slot['bar_widget'].set(0.0)
        slot['label_widget'].configure(text=f"[空闲槽位 {index+1}] 等待分配视频任务...", text_color=("black", "white"))

    def simulate_video_tick(self):
        """本地模拟心跳：每秒向前推动视频进度"""
        for acc_id, slots in self.video_slots.items():
            if acc_id not in self.processes:
                continue
                
            for slot in slots:
                if not slot['is_free'] and slot['total'] > 0:
                    try:
                        speed_val = float(self.acc_ui_elements[acc_id]['speed'].get())
                    except:
                        speed_val = 1.0
                        
                    # 步进：每秒 += 1 * 倍速
                    slot['current'] += (1 * speed_val)
                    
                    # 保护机制：最高只跑到 99%，等待后端发来「任务完成」信号
                    capped_current = min(slot['current'], slot['total'] * 0.99)
                    ratio = capped_current / slot['total']
                    
                    # 更新 UI
                    slot['bar_widget'].set(ratio)
                    slot['label_widget'].configure(text=f"▶ 正在播放: {slot['task_name']} ({int(capped_current)}s / {int(slot['total'])}s)")

        # 循环调度
        self.after(1000, self.simulate_video_tick)
if __name__ == "__main__":
    app = ChaoXingGUI()
    app.mainloop()
