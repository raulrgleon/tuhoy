#!/usr/bin/env python3
"""Publica en la página de Facebook de TuHoy las mismas notas que se programan para X.

No escribe textos propios: lee la cola de x_posts.py (data/x_queue.json, solo lectura) y, cuando a
un post le llega su hora, lo publica en la página con el enlace a la nota (Facebook arma la vista
previa con la foto y el titular). Lo publicado se apunta en data/fb_queue.json.

Para no dar sobresaltos: solo publica posts cuya hora pasó hace menos de 2 horas y como mucho
uno por pasada (el cron corre cada 15 min).

Variables en .env: FB_MODE (api | off), FB_PAGE_ID, FB_PAGE_TOKEN (token de página sin caducidad).

  python3 scripts/facebook_posts.py --dry-run    # muestra lo que publicaría ahora
  python3 scripts/facebook_posts.py              # publica lo que toca (cron cada 15 min)
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import writer  # noqa: E402

TZ = ZoneInfo("America/Chicago")
X_QUEUE = ROOT / "data" / "x_queue.json"
FB_QUEUE = ROOT / "data" / "fb_queue.json"
LOG = ROOT / "logs" / "facebook.log"
GRAPH = "https://graph.facebook.com/v23.0"
MAX_DELAY = timedelta(hours=2)
PER_RUN = 1


def log(msg: str) -> None:
    line = f"{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')} [fb] {msg}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load(path: Path, default: dict) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def due_posts(x_queue: dict, done: set[str], now: datetime) -> list[dict]:
    out = []
    for t in x_queue.get("pendientes", []):
        hora = datetime.fromisoformat(t["hora"])
        if t["id"] in done or hora > now or now - hora > MAX_DELAY:
            continue
        out.append(t)
    return sorted(out, key=lambda t: t["hora"])


def publish(env: dict, t: dict) -> str:
    data = urllib.parse.urlencode(
        {"message": t["texto"], "link": t["url"], "access_token": env["FB_PAGE_TOKEN"]}
    ).encode()
    req = urllib.request.Request(f"{GRAPH}/{env['FB_PAGE_ID']}/feed", data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())["id"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Facebook {e.code}: {e.read().decode(errors='replace')[:300]}") from e


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    env = writer.load_env()
    if (env.get("FB_MODE") or "off").lower() != "api" and not args.dry_run:
        return 0
    if not env.get("FB_PAGE_ID") or not env.get("FB_PAGE_TOKEN"):
        log("faltan FB_PAGE_ID o FB_PAGE_TOKEN en .env")
        return 1

    fb = load(FB_QUEUE, {"historial": []})
    done = {h["id"] for h in fb["historial"]}
    now = datetime.now(TZ)
    due = due_posts(load(X_QUEUE, {}), done, now)[:PER_RUN]
    if args.dry_run:
        for t in due:
            print(f"[{datetime.fromisoformat(t['hora']).strftime('%H:%M')}] {t['texto']}\n    {t['url']}\n")
        if not due:
            print("nada que publicar ahora")
        return 0

    for t in due:
        try:
            post_id = publish(env, t)
        except RuntimeError as e:
            log(f"error al publicar {t['titulo']}: {e}")
            return 1
        fb["historial"].append({"id": t["id"], "fecha": now.date().isoformat(), "fb_id": post_id})
        log(f"publicado {post_id}: {t['titulo']}")
    fb["historial"] = fb["historial"][-500:]
    FB_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    FB_QUEUE.write_text(json.dumps(fb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
