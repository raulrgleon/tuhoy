#!/usr/bin/env python3
"""Publica en @tuhoynoticias las mismas notas que se programan para X.

Lee la cola de x_posts.py (data/x_queue.json, solo lectura). Instagram no arma vista previa
con enlace: sube la foto de la nota y pone el texto + la URL en el pie. Lo publicado se
apunta en data/ig_queue.json.

Sin sobresaltos: solo posts cuya hora pasó hace menos de 2 horas, como mucho uno por pasada
(el cron corre cada 15 min) y nada si IG_MODE no es api. No se activa hasta que Raul lo pida.

Variables en .env: IG_MODE (api | off), FB_PAGE_ID, FB_PAGE_TOKEN (el de la página TuHoy,
con la cuenta de Instagram profesional ligada). IG_USER_ID es opcional: si falta se lee de
la página (instagram_business_account).

  python3 scripts/instagram_posts.py --dry-run    # muestra lo que publicaría ahora
  python3 scripts/instagram_posts.py              # publica lo que toca (cron cada 15 min)
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import daily_edition as daily  # noqa: E402
import writer  # noqa: E402

TZ = ZoneInfo("America/Chicago")
X_QUEUE = ROOT / "data" / "x_queue.json"
IG_QUEUE = ROOT / "data" / "ig_queue.json"
LOG = ROOT / "logs" / "instagram.log"
GRAPH = "https://graph.facebook.com/v23.0"
MAX_DELAY = timedelta(hours=2)
PER_RUN = 1
CAPTION_MAX = 2200


def log(msg: str) -> None:
    line = f"{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')} [ig] {msg}"
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


def graph(method: str, path: str, token: str, fields: dict | None = None) -> dict:
    url = f"{GRAPH}/{path.lstrip('/')}"
    if method == "GET":
        q = dict(fields or {})
        q["access_token"] = token
        url += "?" + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, method="GET")
    else:
        body = dict(fields or {})
        body["access_token"] = token
        req = urllib.request.Request(
            url, data=urllib.parse.urlencode(body).encode(), method="POST"
        )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Instagram {e.code}: {e.read().decode(errors='replace')[:400]}") from e


def ig_user_id(env: dict) -> str:
    if env.get("IG_USER_ID"):
        return env["IG_USER_ID"]
    data = graph(
        "GET",
        env["FB_PAGE_ID"],
        env["FB_PAGE_TOKEN"],
        {"fields": "instagram_business_account"},
    )
    ig = (data.get("instagram_business_account") or {}).get("id")
    if not ig:
        raise RuntimeError("la página TuHoy no tiene Instagram profesional ligado")
    return ig


def feature_image(env: dict, post_id: str) -> str | None:
    ghost = daily.Ghost(env["GHOST_URL"], env["GHOST_ADMIN_API_KEY"])
    status, data = ghost.get(f"/posts/{post_id}/?fields=id,feature_image")
    if status != 200:
        raise RuntimeError(f"Ghost {status}: {data}")
    posts = data.get("posts") or []
    url = (posts[0].get("feature_image") if posts else None) or ""
    return url or None


def caption(t: dict) -> str:
    text = (t.get("texto") or t.get("titulo") or "").strip()
    url = (t.get("url") or "").strip()
    pie = f"{text}\n\n{url}".strip() if url else text
    if len(pie) <= CAPTION_MAX:
        return pie
    keep = CAPTION_MAX - len(url) - 2
    if keep < 40:
        return url[:CAPTION_MAX]
    return f"{text[: keep - 1].rstrip()}…\n\n{url}"


def publish(env: dict, ig: str, image_url: str, pie: str) -> str:
    created = graph(
        "POST",
        f"{ig}/media",
        env["FB_PAGE_TOKEN"],
        {"image_url": image_url, "caption": pie},
    )
    creation_id = created.get("id")
    if not creation_id:
        raise RuntimeError(f"contenedor sin id: {created}")
    for _ in range(12):
        st = graph("GET", creation_id, env["FB_PAGE_TOKEN"], {"fields": "status_code,status"})
        code = (st.get("status_code") or "").upper()
        if code == "FINISHED":
            break
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"contenedor {creation_id}: {st}")
        time.sleep(2)
    else:
        raise RuntimeError(f"contenedor {creation_id} no terminó: {st}")
    published = graph(
        "POST",
        f"{ig}/media_publish",
        env["FB_PAGE_TOKEN"],
        {"creation_id": creation_id},
    )
    post_id = published.get("id")
    if not post_id:
        raise RuntimeError(f"publicación sin id: {published}")
    return post_id


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    env = writer.load_env()
    if (env.get("IG_MODE") or "off").lower() != "api" and not args.dry_run:
        return 0
    if not env.get("FB_PAGE_ID") or not env.get("FB_PAGE_TOKEN"):
        log("faltan FB_PAGE_ID o FB_PAGE_TOKEN en .env")
        return 1

    ig_q = load(IG_QUEUE, {"historial": []})
    done = {h["id"] for h in ig_q["historial"]}
    now = datetime.now(TZ)
    due = due_posts(load(X_QUEUE, {}), done, now)[:PER_RUN]
    if args.dry_run:
        for t in due:
            print(f"[{datetime.fromisoformat(t['hora']).strftime('%H:%M')}] {caption(t)}\n")
        if not due:
            print("nada que publicar ahora")
        return 0

    try:
        ig = ig_user_id(env)
    except RuntimeError as e:
        log(str(e))
        return 0

    for t in due:
        try:
            img = feature_image(env, t["id"])
            if not img:
                log(f"sin foto, se omite: {t['titulo']}")
                continue
            post_id = publish(env, ig, img, caption(t))
        except RuntimeError as e:
            log(f"error al publicar {t['titulo']}: {e}")
            return 1
        ig_q["historial"].append({"id": t["id"], "fecha": now.date().isoformat(), "ig_id": post_id})
        log(f"publicado {post_id}: {t['titulo']}")
    ig_q["historial"] = ig_q["historial"][-500:]
    IG_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    IG_QUEUE.write_text(json.dumps(ig_q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
