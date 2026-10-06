#!/usr/bin/env python3
"""Empaqueta themes/tuhoy, lo sube a Ghost y lo activa.

  python3 scripts/upload_theme.py
"""
import importlib.util
import io
import json
import os
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME = ROOT / "themes" / "tuhoy"

spec = importlib.util.spec_from_file_location("daily", ROOT / "scripts" / "daily_edition.py")
daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daily)


def build_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, _, files in os.walk(THEME):
            for f in files:
                full = Path(dirpath) / f
                z.write(full, Path("tuhoy") / full.relative_to(THEME))
    return buf.getvalue()


def main() -> int:
    env = daily.load_env()
    ghost = daily.Ghost(env["GHOST_URL"], env["GHOST_ADMIN_API_KEY"])
    version = json.loads((THEME / "package.json").read_text())["version"]
    boundary = "----TuhoyTheme" + uuid.uuid4().hex
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"tuhoy.zip\"\r\n"
        "Content-Type: application/zip\r\n\r\n"
    ).encode() + build_zip() + f"\r\n--{boundary}--\r\n".encode()
    status, resp = ghost._req("POST", "/themes/upload/", body, f"multipart/form-data; boundary={boundary}")
    print("upload", version, status, "" if status < 300 else json.dumps(resp, ensure_ascii=False)[:800])
    if status >= 300:
        return 1
    status, resp = ghost._req("PUT", "/themes/tuhoy/activate/", b"{}")
    print("activate", status, "" if status < 300 else json.dumps(resp, ensure_ascii=False)[:800])
    return 0 if status < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
