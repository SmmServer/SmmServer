import io
import sys
import zipfile

path = sys.argv[1]
with zipfile.ZipFile(path, "r") as zin:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in sorted(zin.infolist(), key=lambda i: i.filename):
            item.date_time = (2024, 1, 1, 0, 0, 0)
            zout.writestr(item, zin.read(item.filename))
with open(path, "wb") as f:
    f.write(buf.getvalue())
