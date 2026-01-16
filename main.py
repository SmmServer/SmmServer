import sys
import os
import subprocess
import threading
import queue
import time
import configparser
import argparse
import pretendo
import proxy
import warnings
import ctypes
import tkinter
from tkinter import messagebox

try:
    import customtkinter as ctk
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

IS_FROZEN = getattr(sys, 'frozen', False)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

if IS_FROZEN:
    APP_DIR = os.path.dirname(sys.executable)
    BASE_DIR = resource_path(".")
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = APP_DIR

CLIENTS_DIR = os.path.join(BASE_DIR, "NintendoClients")
CONFIGS_DIR = os.path.join(APP_DIR, "Configs")
SETTINGS_INI_PATH = os.path.join(CONFIGS_DIR, "settings.ini")
LOG_FILE_PATH = os.path.join(APP_DIR, "debug_log.txt")

# Define individual log paths
LOG_SMM_PATH = os.path.join(APP_DIR, "NEX SMM.log")
LOG_FRIENDS_PATH = os.path.join(APP_DIR, "NEX Friends.log")
LOG_PRETENDO_PATH = os.path.join(APP_DIR, "Pretendo.log")
LOG_PROXY_PATH = os.path.join(APP_DIR, "Proxy.log")

if not IS_FROZEN:
    sys.path.append(CLIENTS_DIR)

try:
    from NintendoClients import smmdb
except ImportError:
    smmdb = None

warnings.filterwarnings("ignore")

BIND_IP = pretendo.BIND_IP
FONT_FAMILY = "Segoe UI" if os.name == "nt" else "Roboto"

M3_BG = "#141218"
M3_SURFACE = "#1D1B20"
M3_PRIMARY = "#D0BCFF"
M3_ON_PRIMARY = "#381E72"
M3_SURFACE_VARIANT = "#49454F"
M3_CONSOLE_BG = "#1D1B20"
M3_DROPDOWN_FG = "#2B2930"
M3_WARNING = "#FFD54F"

DEFAULT_INI_CONTENT = f"""[OAuth20]
access_token=1234567890abcdef1234567890abcdef
refresh_token=fedcba0987654321fedcba0987654321fedcba12
expires_in=3600
service_token=U0VSVklDRVNFUlZJQ0VTRVJWSUNFU0VSVklDRVNFUlZJQ0VTRVJWSUNFU0VSVklDRVNFUlZJQ0VTRVJWSUNFU0VSVklDRVNFUlZJQ0VTRVJWSUNFU0U=

[00003200]
host={BIND_IP}
port=60000
pid=1337
password=password
token=RlJJRU5EU0ZSSUVORFNGUklFTkRTRlJJRU5EU0ZSSUVORFNGUklFTkRTRlJJRU5EU0ZSSUVORFNGUklFTkRTRlJJRU5EU0ZSSUVORFNGUklFTkRTRlI=

[1018DB00]
host={BIND_IP}
port=59900
pid=1337
password=password
token=U01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU00=
"""

def read_setting(section, key, fallback):
    config = configparser.ConfigParser()
    config.read(SETTINGS_INI_PATH)
    try: return config.get(section, key, fallback=fallback)
    except: return fallback

def write_setting(section, key, value):
    config = configparser.ConfigParser()
    config.read(SETTINGS_INI_PATH)
    if not config.has_section(section): config.add_section(section)
    config.set(section, key, str(value))
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    with open(SETTINGS_INI_PATH, 'w') as configfile: config.write(configfile)

def setup_configs():
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    os.makedirs(os.path.join(CLIENTS_DIR, "www"), exist_ok=True)
    ini_path = os.path.join(CONFIGS_DIR, "Pretendo++.ini")
    
    if not os.path.exists(ini_path):
        with open(ini_path, "w") as f: f.write(DEFAULT_INI_CONTENT)
    else:
        try:
            config = configparser.ConfigParser()
            config.read(ini_path)
            updated = False
            
            if config.has_section('00003200'):
                if config.get('00003200', 'host', fallback='') != BIND_IP:
                    config.set('00003200', 'host', BIND_IP)
                    updated = True
            
            if config.has_section('1018DB00'):
                if config.get('1018DB00', 'host', fallback='') != BIND_IP:
                    config.set('1018DB00', 'host', BIND_IP)
                    updated = True
            
            if updated:
                with open(ini_path, 'w') as f: config.write(f)
        except Exception: pass

    config = configparser.ConfigParser()
    config.read(SETTINGS_INI_PATH)
    if not config.has_section('General'):
        config.add_section('General')
        config.set('General', 'CourseSource', 'SMMDB')
        with open(SETTINGS_INI_PATH, 'w') as f: config.write(f)

def get_base_cmd():
    return [sys.executable] if IS_FROZEN else [sys.executable, os.path.abspath(sys.argv[0])]

class HybridLogger:
    def __init__(self, log_queue=None, print_to_stdout=True):
        self.terminal = sys.stdout
        self.log_queue = log_queue
        self.print_to_stdout = print_to_stdout
        self.lock = threading.Lock()
        
        try:
            self.file_handle = open(LOG_FILE_PATH, "a", encoding="utf-8", buffering=1)
        except:
            self.file_handle = None

    def _write_specific_log(self, filepath, message):
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except: pass

    def write(self, message):
        if '\x00' in message: return
        if not message.strip(): return
        
        with self.lock:
            # 1. Write to stdout
            if self.print_to_stdout and self.terminal:
                try:
                    self.terminal.write(message + "\n")
                    self.terminal.flush()
                except: pass

            # 2. Write to master debug log
            if self.file_handle:
                try:
                    self.file_handle.write(message + "\n")
                    self.file_handle.flush()
                except: pass

            # 3. Process tags and write to specific logs
            clean = message.strip()
            tag = "Debug"
            
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

            if "[CacheStatus]" in clean:
                tag = "CacheStatus"
                clean = clean.replace("[CacheStatus]", "").strip()
            elif clean.startswith("[Pretendo]"): 
                tag = "Pretendo"
                clean = clean.replace("[Pretendo]", "").strip()
                self._write_specific_log(LOG_PRETENDO_PATH, f"[{timestamp}] {clean}")
            elif clean.startswith("[Proxy]"): 
                tag = "Proxy"
                clean = clean.replace("[Proxy]", "").strip()
                self._write_specific_log(LOG_PROXY_PATH, f"[{timestamp}] {clean}")
            elif "CacheManager" in clean:
                clean = clean.replace("[CacheManager]", "").strip()
            elif "SMM" in clean: 
                tag = "SMM"
                self._write_specific_log(LOG_SMM_PATH, f"[{timestamp}] {clean}")
            elif "Friend" in clean: 
                tag = "Friends"
                self._write_specific_log(LOG_FRIENDS_PATH, f"[{timestamp}] {clean}")
            
            if self.log_queue:
                self.log_queue.put((tag, clean))

    def flush(self):
        with self.lock:
            if self.terminal: self.terminal.flush()
            if self.file_handle: self.file_handle.flush()

class ServerManager:
    def __init__(self, log_queue=None):
        self.log_queue = log_queue
        self.running = False
        self.subprocesses = []
        self.threads = []
        self.cache_thread = None
        setup_configs()

    def log(self, tag, msg):
        if self.log_queue: self.log_queue.put((tag, msg))
        else: print(f"[{tag}] {msg}")

    def start_cache_manager(self, progress_queue=None):
        # Silent return if already active (fixes double start issue)
        if self.cache_thread and self.cache_thread.is_alive():
            return

        def worker():
            try:
                if smmdb:
                    self.log("Debug", "Starting Cache Manager...")
                    smmdb.start_cache_worker(progress_queue, self.log_queue)
                else:
                    self.log("Debug", "SMMDB module not available.")
            except Exception as e:
                self.log("Debug", f"Cache error: {e}")
        
        self.cache_thread = threading.Thread(target=worker, daemon=True)
        self.cache_thread.start()

    def start_pretendo(self):
        t = threading.Thread(target=lambda: pretendo.start_server(), daemon=True)
        t.start()
        self.threads.append(t)

    def start_proxy(self):
        t = threading.Thread(target=lambda: proxy.start_proxy(), daemon=True)
        t.start()
        self.threads.append(t)

    def start_external(self, name, script, script_args=None):
        script_path = os.path.join(CLIENTS_DIR, script)
        cmd = get_base_cmd() + ["--run-script", script] if IS_FROZEN else [sys.executable, script_path]
        
        if script_args:
            cmd.extend(script_args)
        
        def reader(proc):
            if proc.stdout:
                for line in proc.stdout:
                    if line: self.log(name, line.strip())
        
        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                text=True, bufsize=1, cwd=CLIENTS_DIR, creationflags=flags, 
                env=env, encoding='utf-8', errors='ignore'
            )
            self.subprocesses.append(proc)
            threading.Thread(target=reader, args=(proc,), daemon=True).start()
            self.log("Debug", f"{name} service started.")
        except Exception as e:
            self.log("Debug", f"Failed to start {name}: {e}")

    def start_services(self, services=['start']):
        self.running = True
        all_services = 'start' in services
        
        if all_services or 'pretendo' in services: self.start_pretendo()
        if all_services or 'proxy' in services: self.start_proxy()
        if all_services or 'smm' in services: self.start_external("SMM", "example_smm_server.py")
        if all_services or 'friends' in services: self.start_external("Friends", "example_friend_server.py")
        if all_services or 'smmdb' in services: self.start_cache_manager()

    def stop_services(self):
        self.running = False
        pretendo.stop_server()
        proxy.stop_proxy()
        for p in self.subprocesses:
            try: p.terminate()
            except: pass
        self.subprocesses = []

def run_cli(services):
    print(f"Starting SmmServer CLI Mode: {services}")
    manager = ServerManager()
    manager.start_services(services)
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        manager.stop_services()

class CemuManager:
    def __init__(self, base_dir):
        self.cemu_dir = os.path.join(base_dir, "Cemu")
        if not os.path.exists(self.cemu_dir): os.makedirs(self.cemu_dir)
    def scan_versions(self):
        versions = []
        if not os.path.exists(self.cemu_dir): return versions
        for item in os.listdir(self.cemu_dir):
            full_path = os.path.join(self.cemu_dir, item)
            if item.endswith(".AppImage") and os.path.isfile(full_path): versions.append((item, full_path, "appimage"))
            elif os.path.isdir(full_path):
                exe_path = os.path.join(full_path, "Cemu.exe")
                if os.path.exists(exe_path): versions.append((f"{item} (v)", exe_path, "exe"))
            elif item == "Cemu.exe": versions.append(("Cemu (Root)", full_path, "exe"))
        return versions
    def launch(self, version_info, log_callback):
        name, path, vtype = version_info
        log_callback("Debug", f"Launching {name}...")
        try:
            if sys.platform == 'win32': subprocess.Popen([path], cwd=os.path.dirname(path), creationflags=subprocess.CREATE_NO_WINDOW)
            else: subprocess.Popen([path], cwd=os.path.dirname(path))
        except Exception as e: log_callback("Debug", f"Failed to launch Cemu: {e}")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SmmServer")
        self.geometry("1000x750")
        self.minsize(1000, 750)
        self.configure(fg_color=M3_BG)
        ctk.set_appearance_mode("Dark")
        
        try: self.iconbitmap(resource_path("mushroom.ico"))
        except: pass

        self.log_queue = queue.Queue()
        sys.stdout = HybridLogger(self.log_queue, print_to_stdout=False)
        sys.stderr = sys.stdout

        self.progress_queue = queue.Queue()
        self.manager = ServerManager(self.log_queue)
        self.cemu_mgr = CemuManager(APP_DIR)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.setup_sidebar()
        self.setup_main_content()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self.update_logs)
        self.after(100, self.update_progress)
        self.after(1500, lambda: self.manager.start_cache_manager(self.progress_queue))

    def setup_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=M3_SURFACE)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SmmServer", font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"), text_color="#E6E1E5")
        self.logo_label.pack(pady=(30, 20), padx=20, anchor="w")
        
        self.btn_server = ctk.CTkButton(self.sidebar_frame, text="Start Server", command=self.toggle_server, fg_color=M3_PRIMARY, text_color=M3_ON_PRIMARY, hover_color="#E8DEF8", corner_radius=24, height=48, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.btn_server.pack(padx=20, pady=10, fill="x")
        
        self.progress_label = ctk.CTkLabel(self.sidebar_frame, text="Cache Status: Idle", text_color="#CAC4D0", font=(FONT_FAMILY, 12))
        self.progress_label.pack(padx=20, pady=(10, 2), anchor="w")
        
        self.progress_bar = ctk.CTkProgressBar(self.sidebar_frame, progress_color=M3_PRIMARY)
        self.progress_bar.set(0)
        self.progress_bar.pack(padx=20, pady=(0, 10), fill="x")
        
        ctk.CTkLabel(self.sidebar_frame, text="Emulator Config", text_color="#CAC4D0", font=(FONT_FAMILY, 12)).pack(padx=20, pady=(15,5), anchor="w")
        
        self.cemu_vers = self.cemu_mgr.scan_versions()
        self.cemu_values = [v[0] for v in self.cemu_vers] if self.cemu_vers else ["No Cemu found"]
        self.combo_cemu = ctk.CTkComboBox(self.sidebar_frame, values=self.cemu_values, fg_color=M3_DROPDOWN_FG, border_width=0, button_color=M3_SURFACE_VARIANT, dropdown_fg_color=M3_SURFACE, dropdown_text_color="#E6E1E5", text_color="#E6E1E5", corner_radius=15, height=32, font=ctk.CTkFont(family=FONT_FAMILY, size=13))
        self.combo_cemu.pack(padx=20, pady=(0, 10), fill="x")
        if self.cemu_values: self.combo_cemu.set(self.cemu_values[0])
        
        self.btn_cemu = ctk.CTkButton(self.sidebar_frame, text="Launch Cemu", command=self.launch_cemu, fg_color="transparent", border_width=1, border_color=M3_SURFACE_VARIANT, text_color=M3_PRIMARY, hover_color=M3_SURFACE_VARIANT, corner_radius=20, height=40, font=ctk.CTkFont(family=FONT_FAMILY, size=13))
        self.btn_cemu.pack(padx=20, pady=0, fill="x")
        
        ctk.CTkFrame(self.sidebar_frame, height=1, fg_color=M3_SURFACE_VARIANT).pack(fill="x", padx=20, pady=(20, 10))
        
        self.tabs_container = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.tabs_container.pack(fill="x", padx=10, pady=0)
        self.tabs = ["SMM", "Friends", "Pretendo", "Proxy", "Debug"]
        self.current_tab = "SMM"
        self.log_buffers = {k: [] for k in self.tabs}
        self.tab_buttons = {}
        for tab in self.tabs:
            btn = ctk.CTkButton(self.tabs_container, text=f"  {tab}", command=lambda t=tab: self.switch_tab(t), fg_color=M3_SURFACE_VARIANT if tab == "SMM" else "transparent", text_color="#E6E1E5", hover_color=M3_SURFACE_VARIANT, anchor="w", corner_radius=24, height=48, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
            btn.pack(fill="x", pady=2)
            self.tab_buttons[tab] = btn

        self.spacer = ctk.CTkLabel(self.sidebar_frame, text="")
        self.spacer.pack(expand=True, fill="both")
        
        self.btn_debug = ctk.CTkButton(self.sidebar_frame, text="🐞 Debug Services", command=self.run_debug_tests, fg_color="transparent", text_color="#CAC4D0", hover_color=M3_SURFACE_VARIANT, anchor="w", height=40, font=ctk.CTkFont(family=FONT_FAMILY, size=13))
        self.btn_debug.pack(fill="x", padx=10, pady=(0, 5), side="bottom")
        
        self.btn_settings = ctk.CTkButton(self.sidebar_frame, text="⚙️ Settings", command=self.open_settings_window, fg_color="transparent", text_color="#CAC4D0", hover_color=M3_SURFACE_VARIANT, anchor="w", height=40, font=ctk.CTkFont(family=FONT_FAMILY, size=13))
        self.btn_settings.pack(fill="x", padx=10, pady=(0, 10), side="bottom")

    def setup_main_content(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=24, fg_color=M3_BG)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.lbl_title = ctk.CTkLabel(self.header_frame, text="Console Output: SMM", font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"), text_color="#E6E1E5")
        self.lbl_title.pack(side="left")
        
        self.status_container = ctk.CTkFrame(self.header_frame, fg_color="#3c2e2e", corner_radius=12)
        self.status_container.pack(side="right")
        self.status_dot = ctk.CTkLabel(self.status_container, text="●", font=("Arial", 16), text_color="#FFB4AB")
        self.status_dot.pack(side="left", padx=(10, 5), pady=5)
        self.status_lbl = ctk.CTkLabel(self.status_container, text="Stopped", font=(FONT_FAMILY, 12, "bold"), text_color="#FFB4AB")
        self.status_lbl.pack(side="left", padx=(0, 10), pady=5)
        
        self.console_card = ctk.CTkFrame(self.main_frame, fg_color=M3_CONSOLE_BG, corner_radius=16)
        self.console_card.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.console_card.grid_rowconfigure(0, weight=1)
        self.console_card.grid_columnconfigure(0, weight=1)
        
        self.console = ctk.CTkTextbox(self.console_card, font=("Consolas", 13), fg_color="transparent", text_color="#C4C7C5", wrap="none", activate_scrollbars=True)
        self.console.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 5))
        self.console.configure(state="disabled")
        
        self.cache_status_lbl = ctk.CTkLabel(self.console_card, text="> Status: Waiting for service...", anchor="w", font=("Consolas", 12), text_color="#9E9E9E")
        self.cache_status_lbl.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))

    def toggle_server(self):
        if not self.manager.running:
            self.manager.start_services(['start'])
            self.update_ui_running()
        else:
            self.manager.stop_services()
            self.update_ui_stopped()

    def update_ui_running(self):
        self.btn_server.configure(text="Stop Server", fg_color="#93000A", text_color="#FFDAD6", hover_color="#BA1A1A")
        self.status_container.configure(fg_color="#2e3c2e")
        self.status_dot.configure(text_color="#b6f2b6")
        self.status_lbl.configure(text="Running", text_color="#b6f2b6")

    def update_ui_stopped(self):
        self.btn_server.configure(text="Start Server", fg_color=M3_PRIMARY, text_color=M3_ON_PRIMARY, hover_color="#E8DEF8")
        self.status_container.configure(fg_color="#3c2e2e")
        self.status_dot.configure(text_color="#FFB4AB")
        self.status_lbl.configure(text="Stopped", text_color="#FFB4AB")

    def launch_cemu(self):
        if self.cemu_vers:
            idx = self.cemu_values.index(self.combo_cemu.get())
            self.cemu_mgr.launch(self.cemu_vers[idx], self.manager.log)

    def switch_tab(self, tab):
        self.current_tab = tab
        self.lbl_title.configure(text=f"Console Output: {tab}")
        for t, btn in self.tab_buttons.items():
            if t == tab: btn.configure(fg_color=M3_SURFACE_VARIANT)
            else: btn.configure(fg_color="transparent")
        self.console.configure(state="normal")
        self.console.delete("0.0", "end")
        self.console.insert("0.0", "".join(self.log_buffers.get(tab, [])))
        self.console.see("end")
        self.console.configure(state="disabled")

    def update_logs(self):
        while not self.log_queue.empty():
            try:
                tag, msg = self.log_queue.get_nowait()
                
                if tag == "CacheStatus":
                    self.cache_status_lbl.configure(text=f"> {msg}")
                    continue

                line = f"[{time.strftime('%H:%M:%S')}] {msg}\n"
                if tag in self.log_buffers:
                    self.log_buffers[tag].append(line)
                    if len(self.log_buffers[tag]) > 1000: self.log_buffers[tag].pop(0)
                
                if tag == self.current_tab:
                    self.console.configure(state="normal")
                    self.console.insert("end", line)
                    self.console.see("end")
                    self.console.configure(state="disabled")
            except: break
        self.after(100, self.update_logs)

    def update_progress(self):
        while not self.progress_queue.empty():
            try:
                # Direct event unpacking (Telekinesis)
                event_type, data = self.progress_queue.get_nowait()
                
                if event_type == "BOOT_START":
                    self.btn_server.configure(state="disabled")
                    self.progress_bar.configure(progress_color=M3_PRIMARY)
                    self.progress_label.configure(text="Bootstrapping Cache...")
                    self.progress_bar.set(0)
                
                elif event_type == "BOOT_END":
                    self.btn_server.configure(state="normal")
                    self.progress_bar.set(1.0)
                    # Idle State: Gray bar (#49454F)
                    self.progress_bar.configure(progress_color="#49454F")
                    self.progress_label.configure(text="Cache Status: Idle")
                
                elif event_type == "PROGRESS":
                    msg, val, total = data
                    # Ensure purple if moving
                    self.progress_bar.configure(progress_color=M3_PRIMARY)
                    self.progress_label.configure(text=f"{msg} ({val}/{total})")
                    if total > 0:
                        self.progress_bar.set(val/total)
                        
            except: break
        self.after(100, self.update_progress)

    def on_setting_change(self):
        write_setting('General', 'CourseSource', self.source_var.get())
        self.manager.log("Debug", f"Settings updated: Source={self.source_var.get()}")

    def open_settings_window(self):
        window = ctk.CTkToplevel(self)
        window.title("Settings")
        window.geometry("500x500") 
        window.resizable(False, False)
        window.configure(fg_color=M3_BG)
        window.transient(self)
        window.wait_visibility()
        window.grab_set()

        ctk.CTkLabel(window, text="Settings", font=(FONT_FAMILY, 20, "bold"), text_color="#E6E1E5").pack(pady=20)

        source_frame = ctk.CTkFrame(window, fg_color=M3_SURFACE, corner_radius=12)
        source_frame.pack(padx=20, pady=10, fill="x")
        ctk.CTkLabel(source_frame, text="Course Source", font=(FONT_FAMILY, 14, "bold"), text_color="#E6E1E5").pack(pady=(15, 5))
        self.source_var = ctk.StringVar(value=read_setting('General', 'CourseSource', 'SMMDB'))
        ctk.CTkRadioButton(source_frame, text="Nintendo Course World", variable=self.source_var, value="CourseWorld", command=self.on_setting_change).pack(anchor="w", padx=20, pady=5)
        ctk.CTkRadioButton(source_frame, text="SMMDB", variable=self.source_var, value="SMMDB", command=self.on_setting_change).pack(anchor="w", padx=20, pady=(5, 15))

        apikey_frame = ctk.CTkFrame(window, fg_color=M3_SURFACE, corner_radius=12)
        apikey_frame.pack(padx=20, pady=10, fill="x")
        ctk.CTkLabel(apikey_frame, text="SMMDB API Key", font=(FONT_FAMILY, 14, "bold"), text_color="#E6E1E5").pack(pady=(15, 5))
        self.apikey_var = ctk.StringVar(value=read_setting('General', 'SmmdbApiKey', ''))
        entry = ctk.CTkEntry(apikey_frame, textvariable=self.apikey_var, show="*")
        entry.pack(fill="x", padx=20, pady=5)

        def save_apikey():
            write_setting('General', 'SmmdbApiKey', self.apikey_var.get())
            messagebox.showinfo("Success", "API Key Saved")

        ctk.CTkButton(apikey_frame, text="Save Key", command=save_apikey, height=32, corner_radius=16).pack(pady=10, padx=20)

        ctk.CTkButton(window, text="Close", command=window.destroy, fg_color="transparent", border_width=1, border_color=M3_SURFACE_VARIANT).pack(pady=10)

    def run_debug_tests(self):
        if not self.manager.running:
            messagebox.showwarning("Server Offline", "The server must be running to perform debug tests.")
            return
        self.btn_debug.configure(state="disabled")
        self.switch_tab("Debug")
        self.manager.log("Debug", "[Debug] Starting full service test...")
        def run_tests():
            self.manager.log("Debug", "[Debug] Attempting NEX friend service login...")
            # Pass the configured IP to the login script
            self.manager.start_external("Debug", "example_friend_login.py", script_args=["-host", BIND_IP])
            time.sleep(5)
            self.manager.log("Debug", "[Debug] Attempting NEX SMM service login...")
            # Pass the configured IP to the login script
            self.manager.start_external("Debug", "example_smm_login.py", script_args=["-host", BIND_IP])
            time.sleep(5)
            self.manager.log("Debug", "[Debug] Finished! Please send all the .log files if issues persist.")
            self.after(100, lambda: self.btn_debug.configure(state="normal"))
        threading.Thread(target=run_tests, daemon=True).start()

    def on_close(self):
        self.manager.stop_services()
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SmmServer")
    parser.add_argument("--cli", nargs='+', help="Run specific services headless (e.g., --cli start, or --cli pretendo proxy)")
    parser.add_argument("--run-script", help="Internal use to run external scripts")
    
    # Use parse_known_args so that extra arguments passed to --run-script 
    # (like -host 127.0.5.1) don't cause an error in the main parser.
    args, unknown = parser.parse_known_args()

    if args.run_script:
        script_path = os.path.join(CLIENTS_DIR, args.run_script)
        if os.path.exists(script_path):
            sys.path.insert(0, CLIENTS_DIR)
            os.chdir(CLIENTS_DIR)
            
            # Patch sys.argv so the script thinks it received the arguments directly
            sys.argv = [script_path] + unknown
            
            with open(script_path, 'r', encoding='utf-8') as f:
                code = compile(f.read(), script_path, 'exec')
                exec(code, {'__name__': '__main__', '__file__': script_path})
        sys.exit(0)

    if args.cli:
        run_cli(args.cli)
    else:
        if GUI_AVAILABLE:
            app = App()
            app.mainloop()
        else:
            print("CustomTkinter not found. Install it to use the GUI, or use --cli start")