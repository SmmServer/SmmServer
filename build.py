from dotenv import load_dotenv

load_dotenv()

import subprocess
import sys

sys.exit(subprocess.call(["uv", "run", "PyInstaller", "SmmServer.spec"]))
