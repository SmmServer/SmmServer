import subprocess
import sys
import os
import argparse
from dotenv import load_dotenv

load_dotenv()

def run_command(cmd):
    print(f"Running: {' '.join(cmd)}")
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        print(f"Error: Command '{cmd[0]}' not found.")
        return 1

def build_windows():
    print("Building for Windows...")
    # Flet build windows generates an executable in build/windows
    res = run_command(["flet", "build", "windows", "--yes"])
    if res == 0:
        exe_path = os.path.join("build", "windows", "SmmServer.exe")
        if os.path.exists(exe_path):
            print("Applying PE header fixes...")
            run_command([sys.executable, "fix_pe_headers.py", exe_path])
    return res

def build_linux():
    print("Building for Linux...")
    return run_command(["flet", "build", "linux", "--yes"])

def build_android():
    print("Building for Android (APK)...")
    res = run_command(["flet", "build", "apk", "--yes"])
    if res == 0:
        apk_path = os.path.join("build", "apk", "app-release.apk")
        if os.path.exists(apk_path):
            print("Fixing ZIP timestamps for deterministic build...")
            run_command([sys.executable, "fix_zip_timestamps.py", apk_path])
    return res

def main():
    parser = argparse.ArgumentParser(description="SmmServer Build Script")
    parser.add_argument("platform", choices=["windows", "linux", "android", "all"], help="Target platform")
    args = parser.parse_args()

    if args.platform == "windows" or args.platform == "all":
        build_windows()
    if args.platform == "linux" or args.platform == "all":
        build_linux()
    if args.platform == "android" or args.platform == "all":
        build_android()

if __name__ == "__main__":
    main()
