import struct
import sys

exe = sys.argv[1]
with open(exe, "r+b") as f:
    f.seek(0x3C)
    pe_offset = struct.unpack("<I", f.read(4))[0]
    f.seek(pe_offset + 8)
    f.write(b"\x00\x00\x00\x00")
    f.seek(pe_offset + 88)
    f.write(b"\x00\x00\x00\x00")
