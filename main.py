import sys
import os
import subprocess
import threading
import queue
import time
import asyncio
import configparser
import argparse
import logging
import shutil
import flet as ft
from typing import Dict, List

# Path Handling
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

# Flet Storage Handling (Official Way)
FLET_STORAGE = os.getenv("FLET_APP_STORAGE_DATA")
if FLET_STORAGE:
    STORAGE_DIR = FLET_STORAGE
    # Initialize storage if missing
    for folder in ["Cemu", "Configs", os.path.join("NintendoClients", "www")]:
        src = os.path.join(BASE_DIR, folder)
        dst = os.path.join(STORAGE_DIR, folder)
        if not os.path.exists(dst) and os.path.exists(src):
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy(src, dst)
            except Exception as e:
                print(f"Error initializing storage for {folder}: {e}")
else:
    STORAGE_DIR = APP_DIR

os.environ["SMM_STORAGE_DIR"] = STORAGE_DIR

CLIENTS_DIR = os.path.join(BASE_DIR, "NintendoClients")
sys.path.append(BASE_DIR)

import pretendo
import proxy
try:
    from NintendoClients import example_smm_server, example_friend_server, smmdb
except ImportError:
    example_smm_server = None
    example_friend_server = None
    smmdb = None

class CemuManager:
    def __init__(self, base_dir):
        self.cemu_dir = os.path.join(STORAGE_DIR, "Cemu")
        if not os.path.exists(self.cemu_dir): os.makedirs(self.cemu_dir)
        
    def scan_versions(self):
        versions = []
        if not os.path.exists(self.cemu_dir): return versions
        for item in os.listdir(self.cemu_dir):
            full_path = os.path.join(self.cemu_dir, item)
            if item.endswith(".AppImage") and os.path.isfile(full_path):
                versions.append((item, full_path, "appimage"))
            elif os.path.isdir(full_path):
                exe_path = os.path.join(full_path, "Cemu.exe")
                if os.path.exists(exe_path):
                    versions.append((f"{item} (v)", exe_path, "exe"))
            elif item == "Cemu.exe":
                versions.append(("Cemu (Root)", full_path, "exe"))
        return versions

    def launch(self, version_info, log_callback):
        name, path, vtype = version_info
        log_callback("Debug", f"Launching {name}...")
        try:
            if sys.platform == 'win32':
                subprocess.Popen([path], cwd=os.path.dirname(path), creationflags=0x08000000) # CREATE_NO_WINDOW
            else:
                subprocess.Popen([path], cwd=os.path.dirname(path))
        except Exception as e:
            log_callback("Debug", f"Failed to launch Cemu: {e}")

# Constants (Material 3)
M3_BG = "#141218"
M3_SURFACE = "#1D1B20"
M3_PRIMARY = "#D0BCFF"
M3_ON_PRIMARY = "#381E72"
M3_SECONDARY_CONTAINER = "#49454F"
M3_ON_SECONDARY_CONTAINER = "#E8DEF8"
M3_SURFACE_VARIANT = "#49454F"
M3_CONSOLE_BG = "#1D1B20"
M3_WARNING = "#FFD54F"
M3_ERROR = "#F2B8B5"
M3_SUCCESS = "#B6F2B6"

CONFIGS_DIR = os.path.join(STORAGE_DIR, "Configs")
SETTINGS_INI_PATH = os.path.join(CONFIGS_DIR, "settings.ini")
BIND_IP = pretendo.BIND_IP

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

class FletLogHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            tname = record.threadName
            content = msg.lower()
            tag = "Debug"
            
            # 1. Route by Thread Name
            if tname == 'SMM_Service': tag = "SMM"
            elif tname == 'Friends_Service': tag = "Friends"
            elif tname == 'Pretendo_Service': tag = "Pretendo"
            elif tname == 'Proxy_Service': tag = "Proxy"
            
            # 2. Route by Content Tag
            if "[smm]" in content or "[nex-smm]" in content: tag = "SMM"
            elif "[friend]" in content or "[nex-friends]" in content: tag = "Friends"
            elif "[pretendo]" in content: tag = "Pretendo"
            elif "[proxy]" in content: tag = "Proxy"
            elif "[cachestatus]" in content: tag = "CacheStatus"
            
            # 3. Route by Logger Name fallback
            elif "smm" in record.name.lower(): tag = "SMM"
            elif "friend" in record.name.lower(): tag = "Friends"
            elif "pretendo" in record.name.lower(): tag = "Pretendo"
            elif "proxy" in record.name.lower(): tag = "Proxy"

            self.log_queue.put((tag, msg))
        except Exception:
            self.handleError(record)

class ServerManager:
    def __init__(self):
        self.running = False
        self.threads = {}
        self.stop_events = {}
        os.makedirs(CONFIGS_DIR, exist_ok=True)
        os.makedirs(os.path.join(CLIENTS_DIR, "www"), exist_ok=True)

    def start_services(self):
        self.running = True
        self.stop_events = {k: threading.Event() for k in ['smm', 'friends']}
        
        self.threads['pretendo'] = threading.Thread(target=pretendo.start_server, name='Pretendo_Service', daemon=True)
        self.threads['pretendo'].start()
        
        self.threads['proxy'] = threading.Thread(target=proxy.start_proxy, name='Proxy_Service', daemon=True)
        self.threads['proxy'].start()
        
        if example_smm_server:
            self.threads['smm'] = threading.Thread(
                target=lambda: example_smm_server.start_server(BIND_IP, self.stop_events['smm']), 
                name='SMM_Service', daemon=True
            )
            self.threads['smm'].start()
            
        if example_friend_server:
            self.threads['friends'] = threading.Thread(
                target=lambda: example_friend_server.start_server(BIND_IP, self.stop_events['friends']), 
                name='Friends_Service', daemon=True
            )
            self.threads['friends'].start()

    def stop_services(self):
        self.running = False
        pretendo.stop_server()
        proxy.stop_proxy()
        if example_smm_server: example_smm_server.stop_server()
        if example_friend_server: example_friend_server.stop_server()
        for e in self.stop_events.values(): e.set()
        self.threads.clear()

    def start_external(self, name, script, log_queue, script_args=None):
        script_path = os.path.join(CLIENTS_DIR, script)
        cmd = [sys.executable, script_path]
        if script_args: cmd.extend(script_args)
        
        def reader(proc):
            for line in proc.stdout:
                if line: log_queue.put((name, line.strip()))
        
        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                text=True, bufsize=1, cwd=CLIENTS_DIR, creationflags=flags,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )
            threading.Thread(target=reader, args=(proc,), daemon=True).start()
            return proc
        except Exception as e:
            log_queue.put(("Debug", f"Failed to start {name}: {e}"))
            return None

async def main(page: ft.Page):
    page.title = "SmmServer"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = M3_BG
    page.padding = 0
    page.window_width = 1000
    page.window_height = 750

    log_queue = queue.Queue()
    progress_queue = queue.Queue()

    # Logging Cleanup
    for h in logging.getLogger().handlers[:]: logging.getLogger().removeHandler(h)
    
    handler = FletLogHandler(log_queue)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    manager = ServerManager()

    # Cemu Logic
    cemu_mgr = CemuManager(APP_DIR)
    cemu_vers = cemu_mgr.scan_versions()
    cemu_options = [ft.dropdown.Option(v[0]) for v in cemu_vers] if cemu_vers else [ft.dropdown.Option("No Cemu found")]
    
    def on_launch_cemu(e):
        if cemu_vers:
            selection = combo_cemu.value
            for name, path, vtype in cemu_vers:
                if name == selection:
                    cemu_mgr.launch((name, path, vtype), logging.info)
                    break

    combo_cemu = ft.Dropdown(
        options=cemu_options,
        value=cemu_options[0].key if cemu_options else None,
        height=40,
        text_size=13,
        bgcolor=M3_SURFACE,
        border_color=M3_SURFACE_VARIANT,
        border_radius=15,
        content_padding=ft.Padding.symmetric(horizontal=12, vertical=0),
        expand=True
    )

    # UI State
    current_tab = "SMM"
    log_buffers = {k: [] for k in ["SMM", "Friends", "Pretendo", "Proxy", "Debug"]}

    # UI Components - Common
    status_dot = ft.Text("●", color=M3_ERROR, size=14)
    status_msg = ft.Text("Stopped", color=M3_ERROR, size=12, weight="bold")
    status_indicator = ft.Container(
        content=ft.Row([status_dot, status_msg], spacing=4, alignment=ft.MainAxisAlignment.CENTER),
        width=100, height=32, bgcolor="#3c2e2e", border_radius=16,
    )

    cache_status_text = ft.Text("> Status: Ready", size=12, color="#9E9E9E", italic=True)
    progress_bar = ft.ProgressBar(value=0, color=M3_PRIMARY, bgcolor="#49454F", height=3)
    progress_label = ft.Text("Cache Status: Idle", size=12, color="#CAC4D0")

    console_text = ft.Text(value="", font_family="Consolas", size=13, color="#C4C7C5", selectable=True)
    console_container = ft.Column([console_text], scroll=ft.ScrollMode.ALWAYS, expand=True, spacing=0)

    # UI Components - Base
    btn_server = ft.FilledButton(
        "Start Server",
        style=ft.ButtonStyle(
            bgcolor=M3_PRIMARY, color=M3_ON_PRIMARY, shape=ft.RoundedRectangleBorder(radius=20),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12)
        ),
        expand=True
    )

    async def update_ui_status():
        if manager.running:
            btn_server.text = "Stop Server"
            btn_server.style = ft.ButtonStyle(bgcolor="#93000A", color="#FFDAD6", shape=ft.RoundedRectangleBorder(radius=20))
            status_indicator.bgcolor = "#2e3c2e"
            status_dot.color = M3_SUCCESS
            status_msg.value = "Running"
            status_msg.color = M3_SUCCESS
        else:
            btn_server.text = "Start Server"
            btn_server.style = ft.ButtonStyle(bgcolor=M3_PRIMARY, color=M3_ON_PRIMARY, shape=ft.RoundedRectangleBorder(radius=20))
            status_indicator.bgcolor = "#3c2e2e"
            status_dot.color = M3_ERROR
            status_msg.value = "Stopped"
            status_msg.color = M3_ERROR
        page.update()

    async def on_server_click(e):
        if not manager.running: manager.start_services()
        else: manager.stop_services()
        await update_ui_status()

    # Settings Logic
    async def open_settings(e):
        source_var = ft.Ref[ft.RadioGroup]()
        apikey_var = ft.Ref[ft.TextField]()

        async def save_settings(e):
            write_setting('General', 'CourseSource', source_var.current.value)
            write_setting('General', 'SmmdbApiKey', apikey_var.current.value)
            dialog.open = False
            page.update()
            logging.info(f"Settings saved: Source={source_var.current.value}")

        async def cancel_settings(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Settings"),
            content=ft.Column([
                ft.Text("Course Source", weight="bold"),
                ft.RadioGroup(
                    ref=source_var,
                    content=ft.Column([
                        ft.Radio(value="CourseWorld", label="Nintendo Course World"),
                        ft.Radio(value="SMMDB", label="SMMDB"),
                    ]),
                    value=read_setting('General', 'CourseSource', 'SMMDB')
                ),
                ft.Divider(),
                ft.Text("SMMDB API Key", weight="bold"),
                ft.TextField(
                    ref=apikey_var,
                    value=read_setting('General', 'SmmdbApiKey', ''),
                    password=True, can_reveal_password=True,
                    bgcolor=M3_SURFACE_VARIANT, border_radius=10
                ),
                ft.Divider(),
                ft.Text("Application Data", weight="bold"),
                ft.Text("Files are saved in:", size=11, color="#CAC4D0"),
                ft.Container(
                    content=ft.Text(STORAGE_DIR, size=11, color=M3_PRIMARY, selectable=True),
                    bgcolor="#2D2933", padding=8, border_radius=5
                ),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Save", on_click=save_settings),
                ft.TextButton("Cancel", on_click=cancel_settings),
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
    
    # Debug Logic

    debug_progress_bar = ft.ProgressBar(value=0, color=M3_PRIMARY, visible=False)

    async def run_debug_tests(e):
        if not manager.running:
            page.snack_bar = ft.SnackBar(ft.Text("Start the server first!"))
            page.snack_bar.open = True
            page.update()
            return
        
        await switch_tab("Debug")
        debug_progress_bar.visible = True
        debug_progress_bar.value = 0.1
        page.update()
        
        logging.getLogger().info("[Debug] Starting Friend Service test...")
        manager.start_external("Friends", "example_friend_login.py", log_queue, ["-host", BIND_IP])
        await asyncio.sleep(4)
        
        debug_progress_bar.value = 0.5
        page.update()
        logging.getLogger().info("[Debug] Starting SMM Service test...")
        manager.start_external("SMM", "example_smm_login.py", log_queue, ["-host", BIND_IP])
        await asyncio.sleep(4)
        
        debug_progress_bar.value = 1.0
        page.update()
        logging.getLogger().info("[Debug] Diagnostic Finished.")
        await asyncio.sleep(2)
        debug_progress_bar.visible = False
        page.update()
    
    btn_server.on_click = on_server_click

    async def switch_tab(tab):
        nonlocal current_tab
        current_tab = tab
        for t, btns in tab_buttons.items():
            for btn in btns:
                btn.bgcolor = M3_SECONDARY_CONTAINER if t == tab else ft.Colors.TRANSPARENT
                btn.content.color = M3_ON_SECONDARY_CONTAINER if t == tab else "#E6E1E5"
        console_text.value = "".join(log_buffers[tab])
        header_title.value = f"Console Output: {tab}"
        page.update()

    tab_buttons = {k: [] for k in ["SMM", "Friends", "Pretendo", "Proxy", "Debug"]}

    def create_sidebar_content():
        # Re-create tabs column for each instance
        local_tabs = ft.Column(spacing=1)
        for t in ["SMM", "Friends", "Pretendo", "Proxy", "Debug"]:
            btn = ft.Container(
                content=ft.Text(f" {t}", size=12, weight="bold", color="#E6E1E5"),
                on_click=lambda e, tab=t: page.run_task(switch_tab, tab),
                bgcolor=M3_SECONDARY_CONTAINER if t == current_tab else ft.Colors.TRANSPARENT,
                border_radius=18, height=36, alignment=ft.Alignment(-1, 0), padding=ft.Padding.symmetric(horizontal=12)
            )
            tab_buttons[t].append(btn) 
            local_tabs.controls.append(btn)

        return ft.Column([
            ft.Text("SmmServer", size=22, weight="bold", color="#E6E1E5"),
            ft.Container(height=4),
            ft.Row([btn_server]),
            ft.Container(height=4),
            progress_label,
            progress_bar,
            ft.Container(height=10),
            ft.Text("Emulator Config", size=11, color="#CAC4D0"),
            ft.Row([combo_cemu]),
            ft.Container(height=2),
            ft.OutlinedButton(
                "Launch Cemu", on_click=on_launch_cemu,
                style=ft.ButtonStyle(
                    color=M3_PRIMARY, side=ft.BorderSide(1, M3_SURFACE_VARIANT),
                    shape=ft.RoundedRectangleBorder(radius=15),
                ),
                height=36
            ),
            ft.Divider(height=1, color=M3_SURFACE_VARIANT),
            ft.Text("Logs", size=11, weight="bold", color="#CAC4D0"),
            local_tabs,
            ft.Container(expand=True),
            ft.TextButton(
                content=ft.Row([ft.Icon(ft.Icons.BUG_REPORT, color="#CAC4D0", size=16), ft.Text("Debug Services", color="#CAC4D0", size=12)], spacing=10),
                on_click=run_debug_tests,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.symmetric(horizontal=8))
            ),
            ft.TextButton(
                content=ft.Row([ft.Icon(ft.Icons.SETTINGS, color="#CAC4D0", size=16), ft.Text("Settings", color="#CAC4D0", size=12)], spacing=10),
                on_click=open_settings,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.symmetric(horizontal=8))
            ),
        ], expand=True)

    sidebar = ft.Container(
        content=create_sidebar_content(),
        width=210, bgcolor=M3_SURFACE, padding=ft.Padding.only(left=10, right=10, top=20, bottom=15),
    )

    def close_mobile_menu(e):
        mobile_nav_overlay.visible = False
        page.update()

    mobile_nav_overlay = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Menu", size=24, weight="bold", color="#E6E1E5"),
                ft.IconButton(ft.Icons.CLOSE, on_click=close_mobile_menu, icon_color="#E6E1E5", icon_size=30)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(color=M3_SURFACE_VARIANT),
            ft.Column([create_sidebar_content()], scroll=ft.ScrollMode.AUTO, expand=True)
        ]),
        bgcolor=M3_SURFACE,
        padding=20,
        visible=False,
        top=0, left=0, right=0, bottom=0,
        expand=True
    )
    page.overlay.append(mobile_nav_overlay)

    def toggle_mobile_menu(e):
        mobile_nav_overlay.visible = True
        page.update()

    hamburger_btn = ft.IconButton(
        icon=ft.Icons.MENU, icon_color="#E6E1E5", 
        on_click=toggle_mobile_menu,
        visible=False,
        icon_size=28
    )

    header_title = ft.Text("Console Output: SMM", size=20, weight="bold", color="#E6E1E5")


    main_content = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Row([hamburger_btn, header_title], spacing=10),
                status_indicator
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=8),
            debug_progress_bar,
            ft.Container(
                content=ft.Column([
                    console_container,
                    ft.Divider(height=1, color=M3_SURFACE_VARIANT),
                    ft.Container(content=cache_status_text, padding=ft.Padding.symmetric(vertical=4))
                ]),
                bgcolor=M3_CONSOLE_BG, border_radius=16, padding=16, expand=True,
                border=ft.Border.all(1, M3_SURFACE_VARIANT)
            )
        ], expand=True),
        bgcolor=M3_BG, padding=20, expand=True
    )

    def on_resize(e):
        # Use window_width as fallback, default to 1000 (Desktop) if both are 0
        w = page.width if page.width > 0 else (page.window_width if page.window_width > 0 else 1000)
        is_mobile = w < 800
        sidebar.visible = not is_mobile
        hamburger_btn.visible = is_mobile
        # Hide status indicator on mobile if width is small
        status_indicator.visible = not is_mobile
        page.update()

    page.on_resized = on_resize
    page.on_resize = on_resize # Compatibility fallback

    page.add(ft.Row([sidebar, main_content], expand=True, spacing=0))
    
    # Trigger initial check
    on_resize(None)

    async def update_loop():
        while True:
            try:
                updated = False
                while not log_queue.empty():
                    tag, msg = log_queue.get_nowait()
                    if tag == "CacheStatus":
                        cache_status_text.value = f"> {msg}"
                        tag = "Debug"
                    
                    line = msg + "\n"
                    if tag in log_buffers:
                        log_buffers[tag].append(line)
                        if len(log_buffers[tag]) > 1000: log_buffers[tag].pop(0)
                        if tag == current_tab:
                            console_text.value += line
                            updated = True
                
                while not progress_queue.empty():
                    evt, data = progress_queue.get_nowait()
                    if evt == "PROGRESS":
                        msg, val, total = data
                        progress_label.value = f"{msg} ({val}/{total})"
                        progress_bar.value = val/total if total > 0 else 0
                        updated = True
                    elif evt == "BOOT_START" or evt == "BOOT_END":
                        progress_label.value = "Cache Status: Idle" if evt == "BOOT_END" else "Bootstrapping..."
                        progress_bar.value = 1.0 if evt == "BOOT_END" else None
                        updated = True

                if updated: page.update()
            except Exception as e:
                print(f"Update Loop Error: {e}")
            await asyncio.sleep(0.05)

    asyncio.create_task(update_loop())
    if smmdb:
        threading.Thread(target=lambda: smmdb.start_cache_worker(progress_queue, log_queue), daemon=True, name='Cache_Worker').start()

if __name__ == "__main__":
    ft.run(main)
