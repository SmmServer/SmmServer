import sys
import os
import ssl
import socket
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

IS_FROZEN = getattr(sys, 'frozen', False)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

CERTS_DIR = resource_path("Certs")

def get_bind_ip():
    if sys.platform == 'darwin':
        return '127.0.0.1'
    return '127.0.5.1'

BIND_IP = get_bind_ip()

class ReusableHTTPServer(HTTPServer):
    address_family = socket.AF_INET
    allow_reuse_address = True
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()

class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[Proxy] {self.command} {self.path} - {args[1]}", flush=True)
    def do_GET(self): self.proxy()
    def do_POST(self): self.proxy()
    def proxy(self):
        try:
            target_url = f"http://{BIND_IP}:8383{self.path}"
            req_headers = {}
            for k, v in self.headers.items():
                if k.lower() not in ['host', 'connection', 'transfer-encoding', 'upgrade']:
                    req_headers[k] = v
            req_headers['Host'] = f'{BIND_IP}:8383'

            data = None
            if 'Content-Length' in self.headers:
                try: data = self.rfile.read(int(self.headers['Content-Length']))
                except: pass

            req = urllib.request.Request(target_url, data=data, headers=req_headers, method=self.command)
            with urllib.request.urlopen(req, timeout=15) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ['transfer-encoding', 'content-encoding', 'connection']:
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.read())
        except Exception: pass

servers = []

def start_server_instance(server_class, port, use_ssl=False, context=None):
    try:
        server = server_class(('', port), ProxyHandler)
        if use_ssl and context:
            server.socket = context.wrap_socket(server.socket, server_side=True)
        servers.append(server)
        proto = "HTTPS" if use_ssl else "HTTP"
        print(f"[Proxy] IPv4 {proto} listening on Port {port}", flush=True)
        server.serve_forever()
    except Exception as e:
        print(f"[Proxy] Failed to bind {port}: {e}", flush=True)

def start_proxy():
    cert_file = os.path.join(CERTS_DIR, "account.nintendo.net.crt")
    key_file = os.path.join(CERTS_DIR, "account.nintendo.net.pem")

    ctx = None
    try:
        if os.path.exists(cert_file) and os.path.exists(key_file):
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ctx.load_cert_chain(cert_file, key_file)
        else:
            print(f"[Proxy] Certificates not found in {CERTS_DIR}", flush=True)
    except Exception as e:
        print(f"[Proxy] SSL Error: {e}", flush=True)

    # Listen only on IPv4 Port 443 with SSL (No IPv6, No Port 80)
    t = threading.Thread(target=start_server_instance, args=(ReusableHTTPServer, 443, True, ctx), daemon=True)
    t.start()

def stop_proxy():
    for s in servers:
        try:
            s.shutdown()
            s.server_close()
        except: pass
    servers.clear()

if __name__ == "__main__":
    start_proxy()
    while True:
        pass