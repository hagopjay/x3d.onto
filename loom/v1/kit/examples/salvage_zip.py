"""Recover the complete entries of a truncated zip (no central directory) from its local headers.

  python3 -I kit/examples/salvage_zip.py ARCHIVE.zip OUT_DIR

Each entry is inflated and kept only if its CRC-32 and size match the local header. Entries written with a
data descriptor (sizes after the data), the cut-off last entry and any CRC failure are reported, not kept.
Paths that would escape OUT_DIR are refused. Writes OUT_DIR/SALVAGE-REPORT.json.
"""
from __future__ import annotations

import json
import struct
import sys
import zlib
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
data = src.read_bytes()
out.mkdir(parents=True, exist_ok=True)
pos, kept, lost = 0, [], []
while True:
    i = data.find(b"PK\x03\x04", pos)
    if i < 0:
        break
    (_, _, flags, method, _, _, crc, csize, usize, nlen, xlen) = struct.unpack("<IHHHHHIIIHH", data[i:i + 30])
    name = data[i + 30:i + 30 + nlen].decode("utf-8", "replace")
    start = i + 30 + nlen + xlen
    pos = start
    if name.endswith("/"):
        continue
    if flags & 0x08:
        lost.append({"name": name, "why": "sizes in a data descriptor; not recoverable without the directory"})
        continue
    blob = data[start:start + csize]
    if len(blob) < csize:
        lost.append({"name": name, "why": f"truncated: {len(blob)} of {csize} compressed bytes present"})
        break
    try:
        raw = zlib.decompress(blob, -15) if method == 8 else blob if method == 0 else None
    except zlib.error as e:
        raw = None
        lost.append({"name": name, "why": f"inflate failed: {e}"})
    if raw is None:
        if not lost or lost[-1]["name"] != name:
            lost.append({"name": name, "why": f"unsupported method {method}"})
        continue
    if zlib.crc32(raw) != crc or len(raw) != usize:
        lost.append({"name": name, "why": "CRC or size mismatch"})
        continue
    dest = (out / name).resolve()
    if not str(dest).startswith(str(out.resolve()) + "/"):
        lost.append({"name": name, "why": "path escapes output directory"})
        continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    kept.append({"name": name, "bytes": usize, "crc32": f"{crc:08x}"})
    pos = start + csize
report = {"archive": src.name, "archive_bytes": len(data), "central_directory": data.rfind(b"PK\x05\x06") >= 0,
          "kept": kept, "lost": lost}
(out / "SALVAGE-REPORT.json").write_text(json.dumps(report, indent=2) + "\n")
print(f"kept {len(kept)} entries, lost {len(lost)}: " + "; ".join(f"{x['name']} ({x['why']})" for x in lost))
