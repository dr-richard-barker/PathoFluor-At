"""Minimal ENVI reader for the 2016 Andor Zyla line-scan cubes.

Only what these files use: BIL interleave, data type 12 (uint16), little-endian,
header offset 0. Anything else raises rather than being read wrongly.
"""
import re
from pathlib import Path

import numpy as np

_DTYPES = {1: "u1", 2: "i2", 3: "i4", 4: "f4", 5: "f8", 12: "u2"}


def parse_header(path):
    """Parse an ENVI .hdr into a dict. Brace blocks become lists of strings;
    'wavelength' and 'fwhm' become float arrays."""
    text = Path(path).read_text(errors="replace")
    out = {}
    for m in re.finditer(r"^\s*([^=\n{}]+?)\s*=\s*(\{[^}]*\}|[^\n]*)", text, re.M):
        key = m.group(1).strip().lower()
        val = m.group(2).strip()
        if val.startswith("{"):
            items = [v.strip() for v in val[1:-1].replace("\n", " ").split(",")]
            val = [v for v in items if v]
        out[key] = val
    for key in ("wavelength", "fwhm"):
        if key in out and isinstance(out[key], list):
            out[key] = np.array([float(v) for v in out[key]])
    for key in ("samples", "lines", "bands", "data type", "byte order", "header offset"):
        if key in out:
            out[key] = int(str(out[key]).split()[0])
    return out


def raw_path(hdr_path):
    hdr_path = Path(hdr_path)
    for ext in (".raw", ".img", ""):
        p = hdr_path.with_suffix(ext)
        if p.exists() and p != hdr_path:
            return p
    raise FileNotFoundError(f"no raw file next to {hdr_path}")


def _shape_dtype(h):
    if str(h.get("interleave", "")).lower() != "bil":
        raise ValueError(f"unsupported interleave {h.get('interleave')}")
    if h.get("header offset", 0) != 0:
        raise ValueError("non-zero header offset")
    dt = np.dtype(_DTYPES[h["data type"]]).newbyteorder("<" if h.get("byte order", 0) == 0 else ">")
    return (h["lines"], h["bands"], h["samples"]), dt


def open_cube(hdr_path):
    """Memory-map a cube as (lines, bands, samples)."""
    h = parse_header(hdr_path)
    shape, dt = _shape_dtype(h)
    raw = raw_path(hdr_path)
    expected = int(np.prod(shape)) * dt.itemsize
    if raw.stat().st_size < expected:
        raise ValueError(f"{raw.name}: {raw.stat().st_size} bytes < expected {expected}")
    return h, np.memmap(raw, dtype=dt, mode="r", shape=shape)


def read_cube(hdr_path, sha256=None):
    """Read a whole cube into memory in one sequential pass (fast on USB drives).
    If a hashlib object is given it is updated with the file's bytes as read."""
    h = parse_header(hdr_path)
    shape, dt = _shape_dtype(h)
    raw = raw_path(hdr_path)
    n = int(np.prod(shape)) * dt.itemsize
    buf = bytearray(raw.stat().st_size)
    view = memoryview(buf)
    with open(raw, "rb", buffering=0) as f:
        pos = 0
        while pos < len(buf):
            k = f.readinto(view[pos:pos + (64 << 20)])
            if not k:
                break
            if sha256 is not None:
                sha256.update(view[pos:pos + k])
            pos += k
    if pos < n:
        raise ValueError(f"{raw.name}: short read {pos} < {n}")
    cube = np.frombuffer(buf, dtype=dt, count=int(np.prod(shape))).reshape(shape)
    return h, cube
