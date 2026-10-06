#!/usr/bin/env python3
"""Sube routes.yaml a Ghost guardando antes una copia de las rutas activas.

Si Ghost responde 403/501 con la clave de integración, sube routes.yaml a mano en
Ghost → Settings → Labs → Routes (requiere sesión de administrador).
"""
import importlib.util
import pathlib
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location("daily", ROOT / "scripts" / "daily_edition.py")
daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daily)
ENV = daily.load_env()
BASE = ENV["GHOST_URL"].rstrip("/") + "/ghost/api/admin"


def call(method: str, path: str, data: bytes | None = None, ctype: str | None = None):
    headers = {
        "Authorization": f"Ghost {daily.ghost_jwt(ENV['GHOST_ADMIN_API_KEY'])}",
        "User-Agent": daily.BROWSER,
        "Origin": "https://tuhoy.com",
    }
    if ctype:
        headers["Content-Type"] = ctype
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:800]


def main() -> int:
    status, current = call("GET", "/settings/routes/yaml/")
    if status != 200:
        print("download", status, current)
        return 1
    backup = ROOT / "data" / f"routes-backup-{int(time.time())}.yaml"
    backup.write_text(current, encoding="utf-8")
    print("backup", backup)

    boundary = "----tuhoy" + str(int(time.time()))
    content = (ROOT / "routes.yaml").read_bytes()
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"routes\"; filename=\"routes.yaml\"\r\n"
        f"Content-Type: application/x-yaml\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    status, result = call("POST", "/settings/routes/yaml/", body, f"multipart/form-data; boundary={boundary}")
    print("upload", status, result[:300])
    return 0 if status < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
