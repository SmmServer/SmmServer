import sys
import os
import time
import socket
import configparser
import re
import io
import zipfile
import email
import requests
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

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

if not IS_FROZEN:
    sys.path.append(CLIENTS_DIR)

try:
    from NintendoClients import smmdb
except ImportError:
    smmdb = None

def get_bind_ip():
    if sys.platform == 'darwin':
        return '127.0.0.1'
    return '127.0.5.1'

BIND_IP = get_bind_ip()

def read_setting(section, key, fallback):
    config = configparser.ConfigParser()
    config.read(SETTINGS_INI_PATH)
    try: return config.get(section, key, fallback=fallback)
    except: return fallback

class ReusableHTTPServer(HTTPServer):
    address_family = socket.AF_INET
    allow_reuse_address = True
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()

class PretendoHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[Pretendo] {self.command} {self.path} - {args[1]}", flush=True)

    def do_HEAD(self): self.handle_request(method="HEAD")
    def do_GET(self): self.handle_request(method="GET")
    def do_POST(self): self.handle_request(method="POST")

    def handle_request(self, method):
        try:
            config_path = os.path.join(CONFIGS_DIR, "Pretendo++.ini")
            config = configparser.ConfigParser()
            config.read(config_path)
            parsed = urlparse(self.path)
            www_save_dir = os.path.join(CLIENTS_DIR, "www")
            os.makedirs(www_save_dir, exist_ok=True)

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
                                data: bytes = part.get_payload(decode=True)
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
                    course_source = read_setting('General', 'coursesource', 'CourseWorld')
                    
                    if course_source == 'SMMDB':
                        folders_order = ["smmdb", "courseworld"]
                    else:
                        folders_order = ["courseworld", "smmdb"]

                    bases_to_check = [
                        os.path.join(www_save_dir, folders_order[0]), 
                        os.path.join(www_save_dir, folders_order[1])
                    ]
                    if os.path.exists(CLIENTS_DIR):
                        bases_to_check.append(os.path.join(CLIENTS_DIR, "www", folders_order[0]))
                        bases_to_check.append(os.path.join(CLIENTS_DIR, "www", folders_order[1]))

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

server_instance = None

def start_server():
    global server_instance
    try:
        server_instance = ReusableHTTPServer((BIND_IP, 8383), PretendoHandler)
        print(f"[Pretendo] Server running on {BIND_IP}:8383", flush=True)
        server_instance.serve_forever()
    except Exception as e:
        print(f"[Pretendo] Crash: {e}", flush=True)

def stop_server():
    global server_instance
    if server_instance:
        try:
            server_instance.shutdown()
            server_instance.server_close()
        except: pass
        server_instance = None

if __name__ == "__main__":
    start_server()