#!/usr/bin/env python3
"""Publica en @tuhoynoticias las mismas notas que se programan para X.

Lee la cola de x_posts.py (data/x_queue.json, solo lectura). TikTok no arma vista previa
con enlace: sube la foto de la nota (modo foto) y pone el texto + la URL en la descripción.
Lo publicado se apunta en data/tt_queue.json. Los tokens van en data/tt_auth.json (gitignore).

Sin sobresaltos: solo posts cuya hora pasó hace menos de 2 horas, como mucho uno por pasada
(el cron corre cada 15 min) y nada si TT_MODE no es api.

Variables en .env: TT_MODE (api | off), TT_CLIENT_KEY, TT_CLIENT_SECRET.
Autorizar una vez: python3 scripts/tiktok_oauth.py

  python3 scripts/tiktok_posts.py --dry-run    # muestra lo que publicaría ahora
  python3 scripts/tiktok_posts.py              # publica lo que toca (cron cada 15 min)
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import daily_edition as daily  # noqa: E402
import writer  # noqa: E402

TZ = ZoneInfo("America/Chicago")
X_QUEUE = ROOT / "data" / "x_queue.json"
TT_QUEUE = ROOT / "data" / "tt_queue.json"
AUTH = ROOT / "data" / "tt_auth.json"
LOG = ROOT / "logs" / "tiktok.log"
API = "https://open.tiktokapis.com"
MAX_DELAY = timedelta(hours=2)
PER_RUN = 1
TITLE_MAX = 90
DESC_MAX = 4000


def log(msg: str) -> None:
    line = f"{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')} [tt] {msg}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_json(path: Path, data: dict, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, mode)


def utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def clip_utf16(s: str, limit: int) -> str:
    if utf16_len(s) <= limit:
        return s
    out = []
    n = 0
    for ch in s:
        n += 2 if ord(ch) > 0xFFFF else 1
        if n > limit:
            break
        out.append(ch)
    return "".join(out).rstrip()


def due_posts(x_queue: dict, done: set[str], now: datetime) -> list[dict]:
    out = []
    for t in x_queue.get("pendientes", []):
        hora = datetime.fromisoformat(t["hora"])
        if t["id"] in done or hora > now or now - hora > MAX_DELAY:
            continue
        out.append(t)
    return sorted(out, key=lambda t: t["hora"])


def title_of(t: dict) -> str:
    return clip_utf16((t.get("titulo") or "").strip(), TITLE_MAX)


def description_of(t: dict) -> str:
    text = (t.get("texto") or t.get("titulo") or "").strip()
    url = (t.get("url") or "").strip()
    pie = f"{text}\n\n{url}".strip() if url else text
    if utf16_len(pie) <= DESC_MAX:
        return pie
    keep = DESC_MAX - utf16_len(url) - 2
    if keep < 40:
        return clip_utf16(url, DESC_MAX)
    return f"{clip_utf16(text, keep - 1).rstrip()}…\n\n{url}"


def privacy_of(options: list[str]) -> str:
    for want in ("PUBLIC_TO_EVERYONE", "FOLLOWER_OF_CREATOR", "SELF_ONLY"):
        if want in options:
            return want
    return options[0] if options else "SELF_ONLY"


def form_post(url: str, fields: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(fields).encode(),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"TikTok OAuth {e.code}: {e.read().decode(errors='replace')[:400]}") from e


def api(path: str, token: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(body if body is not None else {}).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"TikTok {e.code}: {e.read().decode(errors='replace')[:400]}") from e
    err = data.get("error") or {}
    if err.get("code") not in (None, "", "ok"):
        raise RuntimeError(f"{err.get('code')}: {err.get('message')}")
    return data.get("data") or {}


def refresh_auth(env: dict, auth: dict) -> dict:
    exp = datetime.fromisoformat(auth["expires_at"])
    if exp - datetime.now(timezone.utc) > timedelta(minutes=30):
        return auth
    data = form_post(
        f"{API}/v2/oauth/token/",
        {
            "client_key": env["TT_CLIENT_KEY"],
            "client_secret": env["TT_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": auth["refresh_token"],
        },
    )
    if not data.get("access_token"):
        raise RuntimeError(f"no se pudo renovar el token: {data}")
    auth = {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token") or auth["refresh_token"],
        "open_id": data.get("open_id") or auth.get("open_id"),
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=int(data.get("expires_in") or 86400))).isoformat(),
        "scope": data.get("scope") or auth.get("scope"),
    }
    save_json(AUTH, auth, stat.S_IRUSR | stat.S_IWUSR)
    return auth


def feature_image(env: dict, post_id: str) -> str | None:
    ghost = daily.Ghost(env["GHOST_URL"], env["GHOST_ADMIN_API_KEY"])
    status, data = ghost.get(f"/posts/{post_id}/?fields=id,feature_image")
    if status != 200:
        raise RuntimeError(f"Ghost {status}: {data}")
    posts = data.get("posts") or []
    url = (posts[0].get("feature_image") if posts else None) or ""
    if url.startswith("//"):
        url = "https:" + url
    return url or None


def init_photo(token: str, image: str, t: dict, privacy: str, disable_comment: bool) -> str:
    data = api(
        "/v2/post/publish/content/init/",
        token,
        {
            "post_mode": "DIRECT_POST",
            "media_type": "PHOTO",
            "post_info": {
                "title": title_of(t),
                "description": description_of(t),
                "privacy_level": privacy,
                "disable_comment": disable_comment,
                "auto_add_music": True,
                "brand_content_toggle": False,
                "brand_organic_toggle": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "photo_images": [image],
                "photo_cover_index": 0,
            },
        },
    )
    pub = data.get("publish_id")
    if not pub:
        raise RuntimeError(f"sin publish_id: {data}")
    return pub


def publish(token: str, image: str, t: dict) -> str:
    info = api("/v2/post/publish/creator_info/query/", token, {})
    user = info.get("creator_username") or ""
    if user and user.lower() != "tuhoynoticias":
        raise RuntimeError(f"autorizada @{user}, no @tuhoynoticias")
    privacy = privacy_of(list(info.get("privacy_level_options") or []))
    disable_comment = bool(info.get("comment_disabled"))
    try:
        pub = init_photo(token, image, t, privacy, disable_comment)
    except RuntimeError as e:
        msg = str(e)
        if "unaudited_client_can_only_post_to_private_accounts" in msg and privacy != "SELF_ONLY":
            log("la app de TikTok aún no está auditada: el post sale privado hasta que TikTok apruebe la app")
            pub = init_photo(token, image, t, "SELF_ONLY", disable_comment)
        else:
            raise
    for _ in range(12):
        st = api("/v2/post/publish/status/fetch/", token, {"publish_id": pub})
        code = (st.get("status") or "").upper()
        if code in {"PUBLISH_COMPLETE", "PUBLISHED", "SUCCESS"}:
            return pub
        if code in {"FAILED", "PUBLISH_FAILED"}:
            raise RuntimeError(f"publicación {pub}: {st}")
        time.sleep(2)
    return pub


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    env = writer.load_env()
    if (env.get("TT_MODE") or "off").lower() != "api" and not args.dry_run:
        return 0

    tt_q = load(TT_QUEUE, {"historial": []})
    done = {h["id"] for h in tt_q["historial"]}
    now = datetime.now(TZ)
    due = due_posts(load(X_QUEUE, {}), done, now)[:PER_RUN]
    if args.dry_run:
        for t in due:
            print(f"[{datetime.fromisoformat(t['hora']).strftime('%H:%M')}] {description_of(t)}\n")
        if not due:
            print("nada que publicar ahora")
        return 0

    if not env.get("TT_CLIENT_KEY") or not env.get("TT_CLIENT_SECRET"):
        log("faltan TT_CLIENT_KEY o TT_CLIENT_SECRET en .env")
        return 1

    auth = load(AUTH, {})
    if not auth.get("refresh_token"):
        log("falta autorizar @tuhoynoticias: python3 scripts/tiktok_oauth.py")
        return 0
    try:
        auth = refresh_auth(env, auth)
    except RuntimeError as e:
        log(str(e))
        return 1

    for t in due:
        try:
            img = feature_image(env, t["id"])
            if not img:
                log(f"sin foto, se omite: {t['titulo']}")
                continue
            post_id = publish(auth["access_token"], img, t)
        except RuntimeError as e:
            log(f"error al publicar {t['titulo']}: {e}")
            return 1
        tt_q["historial"].append({"id": t["id"], "fecha": now.date().isoformat(), "tt_id": post_id})
        log(f"publicado {post_id}: {t['titulo']}")
    tt_q["historial"] = tt_q["historial"][-500:]
    save_json(TT_QUEUE, tt_q, 0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
