#!/usr/bin/env python3
"""Avisa a los buscadores (Bing, Yandex, Seznam, Naver… vía IndexNow) de las notas nuevas de TuHoy.

Bing alimenta también a DuckDuckGo, Yahoo y ChatGPT. Google no usa IndexNow: para Google están los
sitemaps enviados en Search Console.

La clave (INDEXNOW_KEY en .env) se sirve en https://tuhoy.com/<clave>.txt desde el Worker de
Cloudflare `tuhoy-indexnow`. Lo ya avisado se apunta en data/indexnow_state.json.

  python3 scripts/indexnow.py --dry-run   # muestra qué URL enviaría
  python3 scripts/indexnow.py             # envía las notas publicadas que falten (cron, tras cada edición)
  python3 scripts/indexnow.py --all       # reenvía todas las notas publicadas
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import daily_edition as daily  # noqa: E402

TZ = ZoneInfo("America/Chicago")
STATE = ROOT / "data" / "indexnow_state.json"
LOG = ROOT / "logs" / "indexnow.log"
ENDPOINT = "https://api.indexnow.org/indexnow"
HOST = "tuhoy.com"


def log(msg: str) -> None:
    line = f"{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')} [indexnow] {msg}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def submit(key: str, urls: list[str]) -> int:
    body = json.dumps({
        "host": HOST,
        "key": key,
        "keyLocation": f"https://{HOST}/{key}.txt",
        "urlList": urls,
    }).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        log(f"respuesta {e.code}: {e.read().decode(errors='replace')[:300]}")
        return e.code


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    env = daily.load_env()
    key = env.get("INDEXNOW_KEY")
    if not key:
        return 0
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"enviadas": []}
    sent = set() if args.all else set(state["enviadas"])

    ghost = daily.Ghost(env["GHOST_URL"], env["GHOST_ADMIN_API_KEY"])
    code, resp = ghost.get("/posts/?limit=all&filter=status:published&fields=url")
    if code >= 300:
        log(f"no se pudieron leer las notas: {code}")
        return 1
    urls = [p["url"] for p in resp.get("posts") or [] if p["url"] not in sent]
    if not urls:
        return 0
    if args.dry_run:
        print("\n".join(urls))
        return 0

    status = submit(key, urls[:10000])
    if status not in (200, 202):
        return 1
    state["enviadas"] = sorted(set(state["enviadas"]) | set(urls))[-5000:]
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"{len(urls)} URL avisadas ({status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
