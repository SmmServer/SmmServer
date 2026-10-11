import platform
import re
import shutil
import socket
import subprocess

REQUIRED_TCP_PORTS = [80, 443, 8383]
REQUIRED_UDP_PORTS = [59900, 59921, 60000, 60021]
NEX_PORTS = [59900, 59921, 60000, 60021]


def _bind_error(port, sock_type, host="127.0.0.1"):
    s = socket.socket(socket.AF_INET, sock_type)
    try:
        if sock_type == socket.SOCK_STREAM:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        return None
    except OSError as e:
        return e
    finally:
        try:
            s.close()
        except Exception:
            pass


def is_tcp_port_free(port, host="127.0.0.1"):
    return _bind_error(port, socket.SOCK_STREAM, host) is None


def is_udp_port_free(port, host="127.0.0.1"):
    return _bind_error(port, socket.SOCK_DGRAM, host) is None


def get_excluded_port_ranges():
    if platform.system() != "Windows":
        return []
    if shutil.which("netsh") is None:
        return []
    ranges = []
    for proto in ("tcp", "udp"):
        try:
            out = subprocess.run(
                ["netsh", "int", "ipv4", "show", "excludedportrange", f"protocol={proto}"],
                capture_output=True, text=True, timeout=10,
            ).stdout or ""
            for m in re.finditer(r"(\d+)\s*-\s*(\d+)", out):
                try:
                    start, end = int(m.group(1)), int(m.group(2))
                    ranges.append((proto, start, end))
                except ValueError:
                    continue
        except Exception:
            continue
    return ranges


def ports_in_excluded_ranges(ports, ranges=None):
    if ranges is None:
        ranges = get_excluded_port_ranges()
    hits = []
    for port in ports:
        for proto, start, end in ranges:
            if start <= port <= end:
                hits.append((port, proto, start, end))
                break
    return hits


def diagnose():
    warnings = []
    for port in REQUIRED_TCP_PORTS:
        err = _bind_error(port, socket.SOCK_STREAM)
        if err is not None:
            if getattr(err, "errno", None) in (13, 1):
                warnings.append(
                    f"TCP port {port} needs elevated privileges to bind ({err}). "
                    f"On Linux/macOS run with sudo for local testing; on Windows run as Administrator."
                )
                continue
            if port == 80:
                warnings.append(
                    "TCP port 80 is in use. The HTTPS proxy only needs 443, "
                    "but if HTTP fails check Skype/VMware/IIS or run as Administrator. "
                    "See issue #5."
                )
            elif port == 443:
                warnings.append(
                    "TCP port 443 is in use or blocked. Cemu HTTPS cannot reach "
                    "SmmServer -> ErrEula 106-0502. Close VPN/antivirus web filters "
                    "or another web server. Whitelist SmmServer/Cemu (issues #5, #10)."
                )
            elif port == 8383:
                warnings.append(
                    "TCP port 8383 is in use. The Pretendo HTTP server cannot start; "
                    "course downloads will fail."
                )
    for port in REQUIRED_UDP_PORTS:
        if not is_udp_port_free(port):
            warnings.append(
                f"UDP port {port} is in use. NEX auth/secure cannot bind -> "
                "106-0502/106-0103. Close other game servers or reboot."
            )
    try:
        hits = ports_in_excluded_ranges(NEX_PORTS + [443, 8383])
        for port, proto, start, end in hits:
            warnings.append(
                f"Port {port} is inside a Hyper-V/WSL2 excluded {proto.upper()} range "
                f"{start}-{end}. Run as Administrator: "
                "`netsh int ipv4 set dynamic tcp start=51001 num=5000` (and ipv6/udp), "
                "then reboot. See issue #21."
            )
    except Exception:
        pass
    return warnings


if __name__ == "__main__":
    for w in diagnose():
        print("WARN: " + w)
    if not diagnose():
        print("All required ports look free.")
