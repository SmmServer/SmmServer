import sys
import zipfile
import shutil
import os

path = sys.argv[1]
temp_path = path + ".tmp"

with zipfile.ZipFile(path, "r") as zin:
    with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for item in sorted(zin.infolist(), key=lambda i: i.filename):
            item.date_time = (2026, 1, 1, 0, 0, 0)
            with zin.open(item.filename) as f_in:
                zout.writestr(item, f_in.read())

os.replace(temp_path, path)
print(f"Fixed timestamps for {path}")
