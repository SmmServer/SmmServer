import customtkinter as ctk
import sys
import os
import subprocess
import threading
import queue
import time
import ssl
import stat
import urllib.request
import urllib.error
import configparser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from tkinter import messagebox
import ctypes
import traceback
import io
import socket
import warnings
import email
import requests
import re
import zipfile
from email.policy import HTTP

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
CERTS_DIR = resource_path("Certs")
CONFIGS_DIR = os.path.join(APP_DIR, "Configs")
SETTINGS_INI_PATH = os.path.join(CONFIGS_DIR, "settings.ini")
LOG_FILE_PATH = os.path.join(APP_DIR, "debug_log.txt")

if not IS_FROZEN:
    sys.path.append(CLIENTS_DIR)

try:
    from NintendoClients import smmdb
except ImportError:
    smmdb = None

warnings.filterwarnings("ignore")

class HybridLogger:
    def __init__(self, log_to_file=False):
        self.terminal = sys.stdout
        self.log_to_file = log_to_file
        self.lock = threading.Lock()

        if self.log_to_file:
            try:
                self.file_handle = open(LOG_FILE_PATH, "a", encoding="utf-8", buffering=1)
            except:
                self.log_to_file = False

    def write(self, message):
        if '\x00' in message: return
        with self.lock:
            try:
                if self.terminal:
                    self.terminal.write(message)
                    self.terminal.flush()
            except: pass

            if self.log_to_file:
                try:
                    self.file_handle.write(message)
                    self.file_handle.flush()
                except: pass

    def flush(self):
        with self.lock:
            try:
                if self.terminal: self.terminal.flush()
                if self.log_to_file: self.file_handle.flush()
            except: pass

if not IS_FROZEN:
    sys.stdout = HybridLogger(log_to_file=True)
else:
    sys.stdout = HybridLogger(log_to_file=False)

sys.stderr = sys.stdout

FONT_FAMILY = "Segoe UI" if os.name == "nt" else "Roboto"

NINTENDO_DOMAINS = [
    "account.nintendo.net", "discovery.olv.nintendo.net", "wup-ama.app.nintendo.net",
    "tagaya.wup.shop.nintendo.net", "npts.app.nintendo.net"
]

DEFAULT_INI = """[OAuth20]
access_token=1234567890abcdef1234567890abcdef
refresh_token=fedcba0987654321fedcba0987654321fedcba12
expires_in=3600
service_token=U0VSVklDRVNFUlZJQ0VTRVJWSUNFU0VSVklDRVNFUlZJQ0VTRVJWSUNFU0VSVklDRVNFUlZJQ0VTRVJWSUNFU0VSVklDRVNFUlZJQ0VTRVJWSUNFU0U=

[00003200]
host=127.0.0.1
port=60000
pid=1337
password=password
token=RlJJRU5EU0ZSSUVORFNGUklFTkRTRlJJRU5EU0ZSSUVORFNGUklFTkRTRlJJRU5EU0ZSSUVORFNGUklFTkRTRlJJRU5EU0ZSSUVORFNGUklFTkRTRlI=

[1018DB00]
host=127.0.0.1
port=59900
pid=1337
password=password
token=U01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU01NU00=
"""

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

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

if not os.path.exists(SETTINGS_INI_PATH):
    write_setting('General', 'CourseSource', 'SMMDB')

def get_base_cmd():
    if IS_FROZEN:
        return [sys.executable]
    else:
        return [sys.executable, os.path.abspath(sys.argv[0])]

class ReusableHTTPServer(HTTPServer):
    address_family = socket.AF_INET
    allow_reuse_address = True
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()

class IPv4HTTPServer(ReusableHTTPServer): pass

class IPv6HTTPServer(HTTPServer):
    address_family = socket.AF_INET6
    allow_reuse_address = True
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()

class ElevatedWorker:
    def __init__(self):
        self.proxies = []
        self.running_proxy = False

    def log(self, msg):
        print(msg, flush=True)

    def kill_port(self, port):
        try:
            current_pid = os.getpid()
            if sys.platform == 'win32':
                cmd = f"netstat -aon | findstr :{port}"
                try:
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, startupinfo=si).decode()
                    for line in output.splitlines():
                        if "LISTENING" not in line.upper(): continue
                        parts = line.strip().split()
                        if len(parts) > 4:
                            try:
                                pid = int(parts[-1])
                                if pid > 4 and pid != current_pid:
                                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=si)
                            except ValueError: continue
                except: pass
            else:
                subprocess.run(["fuser", "-k", "-9", f"{port}/tcp"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass

    def cleanup_ports(self):
        for p in [80, 443, 8383, 59900, 60000, 59921, 60021]: self.kill_port(p)

    def patch_hosts(self):
        self.log("[Worker] Patching Hosts (IPv4 + IPv6)...")
        hosts_path = r"C:\Windows\System32\drivers\etc\hosts" if sys.platform == 'win32' else "/etc/hosts"
        try:
            if sys.platform == 'win32':
                try: os.chmod(hosts_path, stat.S_IWRITE)
                except: pass
            if not os.path.exists(hosts_path):
                self.log(f"[Worker] Hosts not found.")
                return
            with open(hosts_path, "r", encoding='utf-8') as f: content = f.read()
            new_content = content
            if not new_content.endswith("\n"): new_content += "\n"
            added = False
            for domain in NINTENDO_DOMAINS:
                if f"127.0.0.1 {domain}" not in content:
                    new_content += f"127.0.0.1 {domain}\n"
                    added = True
            if added:
                with open(hosts_path, "w", encoding='utf-8') as f: f.write(new_content)
                self.log("[Worker] Hosts updated. Flushing DNS...")
                subprocess.run("ipconfig /flushdns", shell=True, stdout=subprocess.DEVNULL)
            else:
                self.log("[Worker] Hosts already patched.")
        except Exception as e:
            self.log(f"[Worker] Error patching hosts: {e}")

    def revert_hosts(self):
        self.log("[Worker] Reverting Hosts file...")
        hosts_path = r"C:\Windows\System32\drivers\etc\hosts" if sys.platform == 'win32' else "/etc/hosts"
        try:
            if sys.platform == 'win32':
                try: os.chmod(hosts_path, stat.S_IWRITE)
                except: pass
            with open(hosts_path, "r", encoding='utf-8') as f: lines = f.readlines()
            new_lines = [line for line in lines if not any(domain in line for domain in NINTENDO_DOMAINS)]
            with open(hosts_path, "w", encoding='utf-8') as f: f.writelines(new_lines)
            self.log(f"[Worker] Hosts reverted.")
            subprocess.run("ipconfig /flushdns", shell=True, stdout=subprocess.DEVNULL)
        except Exception: pass

    def start_proxy(self):
        if self.running_proxy:
            self.stop_proxy()
            time.sleep(0.5)
        self.running_proxy = True

        class ProxyHandler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                print(f"[Proxy] {self.command} {self.path} - {args[1]}", flush=True)
            def do_GET(self): self.proxy()
            def do_POST(self): self.proxy()
            def proxy(s):
                try:
                    target_url = f"http://127.0.0.1:8383{s.path}"
                    req_headers = {}
                    for k, v in s.headers.items():
                        if k.lower() not in ['host', 'connection', 'transfer-encoding', 'upgrade']:
                            req_headers[k] = v
                    req_headers['Host'] = '127.0.0.1:8383'

                    data = None
                    if 'Content-Length' in s.headers:
                        try: data = s.rfile.read(int(s.headers['Content-Length']))
                        except: pass

                    req = urllib.request.Request(target_url, data=data, headers=req_headers, method=s.command)
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        s.send_response(resp.status)
                        for k, v in resp.headers.items():
                            if k.lower() not in ['transfer-encoding', 'content-encoding', 'connection']:
                                s.send_header(k, v)
                        s.end_headers()
                        s.wfile.write(resp.read())
                except Exception: pass

        def spawn_server(server_class, port, use_ssl=False, context=None):
            try:
                server = server_class(('', port), ProxyHandler)
                if use_ssl and context:
                    server.socket = context.wrap_socket(server.socket, server_side=True)
                self.proxies.append(server)
                addr_type = "IPv6" if server_class == IPv6HTTPServer else "IPv4"
                proto = "HTTPS" if use_ssl else "HTTP"
                self.log(f"[Proxy] {addr_type} {proto} listening on Port {port}")
                server.serve_forever()
            except Exception as e:
                self.log(f"[Proxy] Failed to bind {port}: {e}")

        cert_file = os.path.join(CERTS_DIR, "account.nintendo.net.crt")
        key_file = os.path.join(CERTS_DIR, "account.nintendo.net.pem")

        ctx = None
        try:
            if os.path.exists(cert_file) and os.path.exists(key_file):
                ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ctx.load_cert_chain(cert_file, key_file)
            else:
                self.log(f"[Proxy] Certificates not found in {CERTS_DIR}")
        except Exception as e:
            self.log(f"[Proxy] SSL Error: {e}")

        threading.Thread(target=spawn_server, args=(IPv4HTTPServer, 80, False), daemon=True).start()
        threading.Thread(target=spawn_server, args=(IPv4HTTPServer, 443, True, ctx), daemon=True).start()

        if socket.has_ipv6:
            threading.Thread(target=spawn_server, args=(IPv6HTTPServer, 80, False), daemon=True).start()
            threading.Thread(target=spawn_server, args=(IPv6HTTPServer, 443, True, ctx), daemon=True).start()

    def stop_proxy(self):
        for s in self.proxies:
            try:
                s.shutdown()
                s.server_close()
            except: pass
        self.proxies = []
        self.running_proxy = False
        self.log("[Proxy] Stopped.")

    def loop(self):
        while True:
            try:
                cmd = sys.stdin.readline(1024).strip()
                if not cmd: break
                if cmd == "CMD:NUKE": self.cleanup_ports()
                elif cmd == "CMD:START_PROXY": self.start_proxy()
                elif cmd == "CMD:STOP_PROXY": self.stop_proxy()
                elif cmd == "CMD:HOSTS": self.patch_hosts()
                elif cmd == "CMD:UNHOSTS": self.revert_hosts()
                elif cmd == "CMD:EXIT":
                    self.stop_proxy()
                    sys.exit(0)
            except: break

class ServerManager:
    def __init__(self, log_queue, app_instance):
        self.log_queue = log_queue
        self.app = app_instance
        self.running = False
        self.subprocesses = []
        self.elevated_worker = None

        self.dirs = { "clients": CLIENTS_DIR }
        os.makedirs(self.dirs['clients'], exist_ok=True)
        os.makedirs(CONFIGS_DIR, exist_ok=True)

        ini_path = os.path.join(CONFIGS_DIR, "Pretendo++.ini")
        if not os.path.exists(ini_path):
            with open(ini_path, "w") as f: f.write(DEFAULT_INI)

    def log(self, tab, msg):
        if msg is None: return
        clean_msg = msg.replace('\x00', '').strip()
        if "Successfully saved" in clean_msg or "Downloading" in clean_msg:
            print(f"[{tab}] {clean_msg}")
            return
        if clean_msg:
            self.log_queue.put((tab, clean_msg))

    def start_cache_worker(self):
        def worker_thread():
            try:
                if smmdb:
                    self.log("Debug", "Starting Cache Manager...")
                    smmdb.start_cache_worker(self.app.progress_queue, self.log_queue)
                else:
                    self.log("Debug", "SMMDB module not available (ImportError).")
            except Exception as e:
                self.log("Debug", f"Cache worker failed: {e}")
        threading.Thread(target=worker_thread, daemon=True).start()

    def start_elevated_worker(self):
        if self.elevated_worker and self.elevated_worker.poll() is None: return

        cmd = get_base_cmd() + ["--start"]
        if sys.platform != 'win32': cmd = ['pkexec', 'env', 'PYTHONUNBUFFERED=1'] + cmd

        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            si = subprocess.STARTUPINFO() if sys.platform == 'win32' else None
            if si: si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"

            self.elevated_worker = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, creationflags=flags, startupinfo=si, env=env,
                cwd=APP_DIR, encoding='utf-8', errors='ignore'
            )

            def worker_reader():
                if not self.elevated_worker or not self.elevated_worker.stdout: return
                try:
                    for line in self.elevated_worker.stdout:
                        if line:
                            txt = line.strip().replace('\x00', '')
                            if not txt: continue
                            if txt.startswith("[Proxy]"): self.log("Proxy", txt.replace("[Proxy] ", ""))
                            elif txt.startswith("[Debug]"): self.log("Debug", txt.replace("[Debug] ", ""))
                            elif txt.startswith("[Worker]"): self.log("Debug", txt.replace("[Worker] ", "[Worker] "))
                            else: self.log("Debug", f"[Worker] {txt}")
                except Exception: pass

            t = threading.Thread(target=worker_reader, daemon=True)
            t.start()
            self.log("Debug", "Elevated Worker connected.")
        except Exception as e:
            self.log("Debug", f"Elevated Worker failed to start: {e}")

    def send_worker_cmd(self, cmd):
        if self.elevated_worker and self.elevated_worker.poll() is None:
            try:
                self.elevated_worker.stdin.write(f"{cmd}\n")
                self.elevated_worker.stdin.flush()
            except: pass

    def shutdown_worker(self):
        if self.elevated_worker:
            self.send_worker_cmd("CMD:EXIT")
            try: self.elevated_worker.kill()
            except: pass

    def start(self):
        if self.running: return
        self.running = True
        self.log("Debug", "Starting services...")
        self.start_elevated_worker()
        time.sleep(0.5)
        self.send_worker_cmd("CMD:STOP_PROXY")
        self.send_worker_cmd("CMD:NUKE")
        time.sleep(0.8)
        self.send_worker_cmd("CMD:START_PROXY")
        time.sleep(1)
        self.spawn_process("Pretendo", "--pretendo")
        self.spawn_external_script("SMM", "example_smm_server.py")
        self.spawn_external_script("Friends", "example_friend_server.py")

    def stop(self):
        self.running = False
        self.log("Debug", "Stopping services...")
        self.send_worker_cmd("CMD:STOP_PROXY")
        for p in self.subprocesses:
            try: p.terminate()
            except: pass
        self.subprocesses = []
        self.send_worker_cmd("CMD:NUKE")

    def spawn_process(self, name, flag):
        cmd = get_base_cmd() + [flag]
        self.spawn_command(name, cmd, BASE_DIR)

    def spawn_external_script(self, name, script_name):
        script_path = os.path.join(self.dirs['clients'], script_name)
        if IS_FROZEN:
            cmd = get_base_cmd() + ["--run-script", script_name]
            cwd = self.dirs['clients']
        else:
            cmd = [sys.executable, script_path]
            cwd = self.dirs['clients']

        self.spawn_command(name, cmd, cwd)

    def spawn_command(self, name, command, cwd):
        def reader(proc, tab_name):
            try:
                for line in proc.stdout:
                    if line:
                        clean_line = line.strip().replace('\x00', '')
                        if clean_line:
                            self.log(tab_name, clean_line)
            except: pass
            finally:
                if proc.stdout: proc.stdout.close()

        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"

            proc = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                text=True, bufsize=1, cwd=cwd, env=env, creationflags=flags,
                encoding='utf-8', errors='ignore'
            )
            self.subprocesses.append(proc)
            threading.Thread(target=reader, args=(proc, name), daemon=True).start()
            self.log(name, f"Service '{name}' started.")
        except Exception as e:
            self.log(name, f"Error starting '{name}': {e}")

    def update_hosts(self):
        self.start_elevated_worker()
        self.send_worker_cmd("CMD:HOSTS")

    def reset_hosts(self):
        self.start_elevated_worker()
        self.send_worker_cmd("CMD:UNHOSTS")

    @staticmethod
    def run_pretendo_worker():
        www_save_dir = os.path.join(CLIENTS_DIR, "www")
        os.makedirs(www_save_dir, exist_ok=True)

        class PretendoHandler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                print(f"{self.command} {self.path} - {args[1]}", flush=True)
            def do_HEAD(self): self.handle_request(method="HEAD")
            def do_GET(self): self.handle_request(method="GET")
            def do_POST(self): self.handle_request(method="POST")
            def handle_request(self, method):
                try:
                    config_path = os.path.join(CONFIGS_DIR, "Pretendo++.ini")
                    config = configparser.ConfigParser()
                    config.read(config_path)
                    parsed = urlparse(self.path)

                    if parsed.path == "/smm/upload":
                        try:
                            content_type = self.headers.get('Content-Type')
                            length = int(self.headers.get('Content-Length', 0))
                            body = b""

                            if 'chunked' in self.headers.get('Transfer-Encoding', '').lower():
                                while True:
                                    line = self.rfile.readline()
                                    if not line: break
                                    try: chunk_len = int(line.strip(), 16)
                                    except ValueError: break
                                    if chunk_len == 0:
                                        self.rfile.read(2)
                                        break
                                    chunk = self.rfile.read(chunk_len)
                                    body += chunk
                                    self.rfile.read(2)
                            else:
                                body = self.rfile.read(length)

                            dump_dir = os.path.join(CLIENTS_DIR, "dumps")
                            if not os.path.exists(dump_dir): os.makedirs(dump_dir)
                            with open(os.path.join(dump_dir, f"upload_{int(time.time())}.bin"), "wb") as f: f.write(body)

                            ash0_starts = [m.start() for m in re.finditer(b'ASH0', body)]
                            final_payload = None

                            if len(ash0_starts) >= 4:
                                chunks = []
                                for i in range(len(ash0_starts)):
                                    start = ash0_starts[i]
                                    end = ash0_starts[i+1] if i + 1 < len(ash0_starts) else len(body)
                                    chunks.append(body[start:end])

                                try:
                                    c_thumb0 = smmdb.ash0_decompress(chunks[0])
                                    c_data = smmdb.ash0_decompress(chunks[1])
                                    c_sub = smmdb.ash0_decompress(chunks[2])
                                    c_thumb1 = smmdb.ash0_decompress(chunks[3])

                                    if c_data:
                                        zip_buffer = io.BytesIO()
                                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                                            zf.writestr("course000/thumbnail0.tnl", c_thumb0 if c_thumb0 else b"")
                                            zf.writestr("course000/course_data.cdt", c_data)
                                            zf.writestr("course000/course_data_sub.cdt", c_sub if c_sub else b"")
                                            zf.writestr("course000/thumbnail1.tnl", c_thumb1 if c_thumb1 else b"")
                                        final_payload = zip_buffer.getvalue()
                                        print(f"[Pretendo] Prepared SMMDB upload package.", flush=True)
                                except: pass

                            if not final_payload and len(ash0_starts) > 0:
                                final_payload = smmdb.ash0_decompress(body[ash0_starts[0]:])

                            if final_payload:
                                api_key = read_setting('General', 'SmmdbApiKey', '')
                                headers = {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                                    'Content-Type': 'application/octet-stream',
                                    'filename': 'course000',
                                    'Origin': 'https://smmdb.net',
                                    'Referer': 'https://smmdb.net/upload'
                                }
                                if api_key: headers['Authorization'] = f'APIKEY {api_key}'

                                requests.post("https://smmdb.net/api/uploadcourse", headers=headers, data=final_payload, timeout=60)
                                print(f"[Pretendo] Course sent to SMMDB.", flush=True)
                                self.respond(200, "text/plain", b"OK", method)
                                return

                            self.respond(200, "text/plain", b"OK", method)
                        except Exception as e:
                            print(f"[Pretendo] Upload error: {e}", flush=True)
                            self.respond(500, "text/plain", b"Server Error", method)
                        return

                    if parsed.path == "/ping":
                        self.respond(200, "text/plain", b"pong", method)
                        return

                    if method == "POST" and parsed.path == "/v1/api/oauth20/access_token/generate":
                        sec = config['OAuth20'] if 'OAuth20' in config else {}
                        xml = f'<OAuth20><access_token><token>{sec.get("access_token")}</token><refresh_token>{sec.get("refresh_token")}</refresh_token><expires_in>{sec.get("expires_in")}</expires_in></access_token></OAuth20>'
                        self.respond(200, "text/xml", xml.encode('utf-8'), method)
                        return

                    if parsed.path == "/v1/api/provider/nex_token/@me":
                        qs = parse_qs(parsed.query)
                        gid = qs.get('game_server_id', [''])[0]
                        if gid in config:
                            s = config[gid]
                            xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><nex_token><host>{s.get("host")}</host><nex_password>{s.get("password")}</nex_password><pid>{s.get("pid")}</pid><port>{s.get("port")}</port><token>{s.get("token")}</token></nex_token>'
                            self.respond(200, "application/xml;charset=UTF-8", xml.encode('utf-8'), method)
                        else:
                            self.respond(400, "text/plain", f"unknown game_server_id {gid}".encode(), method)
                        return

                    if parsed.path == "/v1/api/provider/service_token/@me":
                        service_token = config['OAuth20'].get('service_token', '') if 'OAuth20' in config else ''
                        xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><service_token><token>{service_token}</token></service_token>'
                        self.respond(200, "application/xml;charset=UTF-8", xml.encode('utf-8'), method)
                        return

                    if method == "POST" and parsed.path == "/post":
                        try:
                            content_type = self.headers.get('Content-Type', '')
                            length = int(self.headers.get('Content-Length', 0))
                            body = self.rfile.read(length)

                            if 'multipart/form-data' in content_type:
                                msg = email.message_from_bytes(
                                    b'MIME-Version: 1.0\r\n' +
                                    f'Content-Type: {content_type}\r\n'.encode() +
                                    b'\r\n' + body
                                )

                                for part in msg.walk():
                                    if part.get_content_disposition() == 'form-data' and part.get_param('name') == 'file':
                                        data: bytes = part.get_payload(decode=True) # type: ignore
                                        filename = f"file{int(time.time())}.bin"
                                        save_path = os.path.join(www_save_dir, filename)
                                        with open(save_path, "wb") as f:
                                            f.write(data)
                                        print(f"[Pretendo] Saved dump to {save_path}")
                                        self.respond(200, "text/plain", b"OK", method)
                                        return
                            self.respond(400, "text/plain", b"Bad Request", method)
                        except:
                            self.respond(500, "text/plain", b"Server Error", method)
                        return

                    if parsed.path.startswith("/smm/course/") or "datastore" in parsed.path or not parsed.path.startswith("/v1/api"):
                        raw_name = os.path.basename(parsed.path)
                        search_filename = raw_name

                        if parsed.path.startswith("/smm/course/"):
                            match = re.search(r'(\d+)', raw_name)
                            if match:
                                try:
                                    course_id = int(match.group(1))
                                    search_filename = "{:011d}-00001".format(course_id)
                                except: pass
                        
                        found_path = None
                        
                        datastore_dir = os.path.join(www_save_dir, "datastore")
                        ds_try_path = os.path.join(datastore_dir, search_filename)
                        if os.path.exists(ds_try_path):
                            found_path = ds_try_path

                        if not found_path:
                            bases_to_check = [
                                os.path.join(www_save_dir, "smmdb"), 
                                os.path.join(www_save_dir, "courseworld")
                            ]
                            if os.path.exists(CLIENTS_DIR):
                                bases_to_check.append(os.path.join(CLIENTS_DIR, "www", "smmdb"))
                                bases_to_check.append(os.path.join(CLIENTS_DIR, "www", "courseworld"))

                            for base in bases_to_check:
                                if not os.path.exists(base): continue
                                for i in range(4):
                                    try_path = os.path.join(base, str(i), search_filename)
                                    if os.path.exists(try_path):
                                        found_path = try_path
                                        break
                                if found_path: break
                        
                        if found_path:
                            try:
                                with open(found_path, "rb") as f: data = f.read()
                                self.respond(200, "application/octet-stream", data, method)
                            except: self.respond(500, "text/plain", b"File Error", method)
                        else:
                            if "datastore" in parsed.path:
                                print(f"[Pretendo] Datastore file not found: {parsed.path}", flush=True)
                                self.respond(404, "text/plain", b"Not Found", method)
                            else:
                                self.respond(404, "text/plain", b"Not Found", method)
                        return

                    self.respond(404, "text/plain", b"Not Found", method)
                except Exception as e: print(f"Error Request: {e}", flush=True)

            def respond(self, code, ctype, body, method):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                if method != "HEAD": self.wfile.write(body)

        try:
            server = ReusableHTTPServer(('127.0.0.1', 8383), PretendoHandler)
            print("[Pretendo] Worker running on :8383", flush=True)
            server.serve_forever()
        except Exception as e: print(f"[Pretendo] Crash: {e}", flush=True)

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

class HostsManager:
    def check_status(self):
        hosts_path = r"C:\Windows\System32\drivers\etc\hosts" if sys.platform == 'win32' else "/etc/hosts"
        try:
            with open(hosts_path, "r", encoding='utf-8') as f: content = f.read()
            for d in NINTENDO_DOMAINS:
                if d not in content: return False
            return True
        except: return False

M3_BG = "#141218"
M3_SURFACE = "#1D1B20"
M3_PRIMARY = "#D0BCFF"
M3_ON_PRIMARY = "#381E72"
M3_SURFACE_VARIANT = "#49454F"
M3_CONSOLE_BG = "#1D1B20"
M3_DROPDOWN_FG = "#2B2930"
M3_WARNING = "#FFD54F"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SmmServer")
        self.geometry("1000x750")
        self.minsize(1000, 750)
        self.configure(fg_color=M3_BG)
        ctk.set_appearance_mode("Dark")

        try:
            self.iconbitmap(resource_path("mushroom.ico"))
        except: pass

        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()

        self.manager = ServerManager(self.log_queue, self)
        self.hosts_mgr = HostsManager()
        self.cemu_mgr = CemuManager(APP_DIR)

        t = threading.Thread(target=self.manager.start_elevated_worker, daemon=True)
        t.start()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.setup_sidebar()
        self.setup_main_content()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self.check_queue)
        self.after(500, self.check_hosts)
        self.after(100, self.update_progress_bar)
        self.after(1500, self.manager.start_cache_worker)

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
        self.console.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.console.configure(state="disabled")

    def check_queue(self):
        messages_by_tab = {}
        try:
            while not self.log_queue.empty():
                try:
                    tab, msg = self.log_queue.get_nowait()
                    if tab not in messages_by_tab: messages_by_tab[tab] = []
                    timestamp = time.strftime("[%H:%M:%S]")
                    line = f"{timestamp} {msg}\n"
                    messages_by_tab[tab].append(line)
                except queue.Empty: break
            for tab, lines in messages_by_tab.items():
                full_text = "".join(lines)
                self.log_buffers.setdefault(tab, []).extend(lines)
                if len(self.log_buffers[tab]) > 1000:
                    self.log_buffers[tab] = self.log_buffers[tab][-1000:]
                if tab == self.current_tab:
                    self.console.configure(state="normal")
                    if float(self.console.index("end")) > 1000:
                        self.console.delete("1.0", "50.0")
                    self.console.insert("end", full_text)
                    self.console.see("end")
                    self.console.configure(state="disabled")
        except Exception: pass
        self.after(100, self.check_queue)

    def update_progress_bar(self):
        try:
            while not self.progress_queue.empty():
                message, value, total = self.progress_queue.get_nowait()
                if total > 0:
                    self.progress_label.configure(text=f"{message} ({value}/{total})")
                    self.progress_bar.set(value / total)
                else:
                    self.progress_label.configure(text=f"{message}")
                    self.progress_bar.set(0)

                is_bootstrapping = (message == "Bootstrapping Cache" and value < total)

                if is_bootstrapping:
                    self.status_container.configure(fg_color="#3c342e")
                    self.status_dot.configure(text_color=M3_WARNING)
                    self.status_lbl.configure(text="Caching", text_color=M3_WARNING)
                    self.btn_server.configure(state="disabled", text="Caching...")
                else:
                    if self.manager.running:
                        self.update_ui_running()
                    else:
                        self.update_ui_stopped()
        except queue.Empty: pass
        self.after(250, self.update_progress_bar)

    def update_ui_running(self):
        self.btn_server.configure(state="normal", text="Stop Server", fg_color="#93000A", text_color="#FFDAD6", hover_color="#BA1A1A")
        self.status_container.configure(fg_color="#2e3c2e")
        self.status_dot.configure(text_color="#b6f2b6")
        self.status_lbl.configure(text="Running", text_color="#b6f2b6")

    def update_ui_stopped(self):
        self.btn_server.configure(state="normal", text="Start Server", fg_color=M3_PRIMARY, text_color=M3_ON_PRIMARY, hover_color="#E8DEF8")
        self.status_container.configure(fg_color="#3c2e2e")
        self.status_dot.configure(text_color="#FFB4AB")
        self.status_lbl.configure(text="Stopped", text_color="#FFB4AB")

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

    def toggle_server(self):
        self.btn_server.configure(state="disabled")
        def toggle_thread():
            try:
                if not self.manager.running:
                    self.manager.start()
                    self.after(0, self.update_ui_running)
                else:
                    self.manager.stop()
                    self.after(0, self.update_ui_stopped)
            except Exception:
                self.after(0, self.update_ui_stopped)
        threading.Thread(target=toggle_thread, daemon=True).start()

    def launch_cemu(self):
        if not self.cemu_vers: return
        idx = self.cemu_values.index(self.combo_cemu.get())
        self.cemu_mgr.launch(self.cemu_vers[idx], self.manager.log)

    def check_hosts(self):
        if not self.hosts_mgr.check_status():
            if messagebox.askyesno("DNS Config", "Nintendo domains are not redirected.\nFix hosts file? (Admin required)"):
                self.manager.update_hosts()

    def on_setting_change(self):
        write_setting('General', 'CourseSource', self.source_var.get())
        self.manager.log("Debug", f"Settings updated: Source={self.source_var.get()}")

    def open_settings_window(self):
        window = ctk.CTkToplevel(self)
        window.title("Settings")
        window.geometry("400x600")
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

        hosts_frame = ctk.CTkFrame(window, fg_color=M3_SURFACE, corner_radius=12)
        hosts_frame.pack(padx=20, pady=10, fill="x")
        ctk.CTkLabel(hosts_frame, text="Hosts File", font=(FONT_FAMILY, 14, "bold"), text_color="#E6E1E5").pack(pady=(15, 5))
        def revert_action():
            self.manager.reset_hosts()
            messagebox.showinfo("Success", "Request sent.\nThe hosts file will be cleaned.")
        ctk.CTkButton(hosts_frame, text="Restore Hosts", command=revert_action, fg_color="#93000A", hover_color="#BA1A1A", text_color="#FFDAD6", height=40, corner_radius=20).pack(pady=15, padx=20, fill="x")

        ctk.CTkButton(window, text="Close", command=window.destroy, fg_color="transparent", border_width=1, border_color=M3_SURFACE_VARIANT).pack(pady=20)

    def run_debug_tests(self):
        if not self.manager.running:
            messagebox.showwarning("Server Offline", "The server must be running to perform debug tests.")
            return
        self.btn_debug.configure(state="disabled")
        self.switch_tab("Debug")
        self.manager.log("Debug", "[Debug] Starting full service test...")
        def run_tests():
            self.manager.log("Debug", "[Debug] Attempting NEX friend service login...")
            self.manager.spawn_external_script("Debug", "example_friend_login.py")
            time.sleep(5)
            self.manager.log("Debug", "[Debug] Attempting NEX SMM service login...")
            self.manager.spawn_external_script("Debug", "example_smm_login.py")
            time.sleep(5)
            self.manager.log("Debug", "[Debug] Attempting HTTPS connection via proxy...")
            self.manager.spawn_command("Debug", get_base_cmd() + ["--debug-ssl"], BASE_DIR)
            time.sleep(5)
            self.manager.log("Debug", "[Debug] Finished! Please send all the .log files if issues persist.")
            self.after(100, lambda: self.btn_debug.configure(state="normal"))
        threading.Thread(target=run_tests, daemon=True).start()

    def on_close(self):
        try:
            self.manager.shutdown_worker()
            if self.manager.running: self.manager.stop()
        except: pass
        self.destroy()
        os._exit(0)

def run_script_from_clients(script_name):
    script_path = os.path.join(CLIENTS_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"Error: Script not found at {script_path}")
        return

    try:
        import runpy
        sys.path.insert(0, CLIENTS_DIR)

        original_argv = sys.argv
        sys.argv = [script_path]

        original_cwd = os.getcwd()
        os.chdir(CLIENTS_DIR)

        runpy.run_path(script_path, run_name="__main__")

        os.chdir(original_cwd)
        sys.argv = original_argv
    except Exception as e:
        print(f"Error running script {script_name}: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--start":
            d = ElevatedWorker()
            d.loop()
            sys.exit()
        elif sys.argv[1] == "--pretendo":
            ServerManager.run_pretendo_worker()
            sys.exit()
        elif sys.argv[1] == "--run-script" and len(sys.argv) > 2:
            run_script_from_clients(sys.argv[2])
            sys.exit()
        elif sys.argv[1] == "--debug-ssl":
            sys.exit()

    if sys.platform == 'win32':
        if not is_admin():
            try:
                if IS_FROZEN:
                    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, "", None, 1)
                else:
                    script = os.path.abspath(sys.argv[0])
                    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}"', None, 1)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to get admin rights: {e}")
            sys.exit()

    try:
        app = App()
        app.mainloop()
    except Exception as e:
        print(f"FATAL CRASH: {e}")
        print(traceback.format_exc())