#!/usr/bin/env python3
"""Escribe un post para X por cada nota nueva (una vez publicada la edición) y lo entrega.

El cron lo lanza justo después de cada edición (6, 12 y 18 h de Chicago). Toma las notas publicadas
que aún no tienen post (sin #revisar ni #resumen-automatico; máximo X_POSTS por tanda) y reparte los
posts cada X_SPACING minutos hasta la edición siguiente. Los posts pendientes de tandas anteriores se conservan.

Modos (X_MODE en .env):
  email (por defecto)  manda los posts por correo con un botón que abre X con el texto listo.
  api                  los publica en @tuhoy_ con la API de X (requiere créditos
                       y X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET).

  python3 scripts/x_posts.py              # escribe los posts de las notas nuevas (y los manda o los encola)
  python3 scripts/x_posts.py --dry-run    # solo los muestra
  python3 scripts/x_posts.py --post-due   # modo api: publica los que ya tocan (cron cada 15 min)
"""
import argparse
import base64
import hashlib
import hmac
import html
import importlib.util
import json
import secrets
import smtplib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import writer  # noqa: E402

spec = importlib.util.spec_from_file_location("daily", ROOT / "scripts" / "daily_edition.py")
daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daily)

TZ = ZoneInfo("America/Chicago")
QUEUE = ROOT / "data" / "x_queue.json"
EDITION_HOURS = [6, 12, 18]
LAST_POST_HOUR = 23  # no se programan posts más tarde
SKIP_TAGS = {daily.AUTO_TAG, daily.REVIEW_TAG}
URL_LEN = 23  # X cuenta cualquier enlace como 23 caracteres
MAX_LEN = 280


def log(msg: str) -> None:
    daily.log(f"[x] {msg}")


def recent_posts(ghost, hours: int = 30) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    flt = urllib.parse.quote(f"status:published+published_at:>'{since}'", safe="")
    status, data = ghost.get(
        f"/posts/?limit=60&filter={flt}&include=tags&order=published_at%20desc"
        "&fields=id,title,custom_excerpt,excerpt,url,feature_image,published_at"
    )
    if status != 200:
        raise RuntimeError(f"Ghost {status}: {data}")
    posts = []
    for p in data.get("posts", []):
        tags = {t["name"] for t in p.get("tags") or []}
        if tags & SKIP_TAGS:
            continue
        p["seccion"] = next((t["name"] for t in p.get("tags") or [] if not t["name"].startswith("#")), "")
        posts.append(p)
    return posts


def already_tweeted() -> set[str]:
    if not QUEUE.exists():
        return set()
    return {t["id"] for t in json.loads(QUEUE.read_text(encoding="utf-8")).get("historial", [])}


def compose(posts: list[dict], n: int) -> list[dict]:
    cfg = writer.config()
    if not cfg:
        raise RuntimeError("sin clave de modelo en .env")
    notas = "\n\n".join(
        f"id: {p['id']}\nsección: {p['seccion']}\ntitular: {p['title']}\nresumen: {(p.get('custom_excerpt') or p.get('excerpt') or '')[:400]}"
        for p in posts
    )
    prompt = writer.fill(writer.read_prompt("tweets.md"), n=str(n), notas=notas)
    data = writer.parse_json(writer.chat(cfg, prompt, temperature=0.7, max_tokens=3000))
    by_id = {p["id"]: p for p in posts}
    out = []
    for t in data.get("tweets", []):
        post = by_id.get(t.get("id"))
        text = " ".join((t.get("texto") or "").split())
        if not post or not text or any(o["id"] == post["id"] for o in out):
            continue
        if writer.BANNED_RE.search(text):
            log(f"descartado por frase prohibida: {text}")
            continue
        if len(text) + 1 + URL_LEN > MAX_LEN:
            text = daily.smart_cut(text, MAX_LEN - URL_LEN - 2)
        out.append({"id": post["id"], "titulo": post["title"], "url": post["url"], "texto": text})
        if len(out) == n:
            break
    return out


def schedule(tweets: list[dict], env: dict, pending: list[dict], now: datetime | None = None) -> None:
    """Reparte los posts desde ahora hasta la próxima edición, detrás de los que ya están en cola."""
    now = now or datetime.now(TZ)
    spacing = int(env.get("X_SPACING") or 60)
    start = now + timedelta(minutes=10)
    start = start.replace(second=0, microsecond=0) + timedelta(minutes=(-start.minute) % 15)
    queued = [datetime.fromisoformat(t["hora"]) for t in pending]
    if queued and max(queued) + timedelta(minutes=spacing) > start:
        start = max(queued) + timedelta(minutes=spacing)
    next_ed = next(
        (now.replace(hour=h, minute=0, second=0, microsecond=0) for h in EDITION_HOURS if h > now.hour),
        now.replace(hour=LAST_POST_HOUR, minute=0, second=0, microsecond=0),
    )
    window = (next_ed - start).total_seconds() / 60
    if tweets and window > 0:
        spacing = max(20, min(spacing, int(window // len(tweets))))
    end_of_day = now.replace(hour=LAST_POST_HOUR, minute=0, second=0, microsecond=0)
    for i, t in enumerate(tweets):
        t["hora"] = min(start + timedelta(minutes=spacing * i), end_of_day).isoformat()


def full_text(t: dict, with_link: bool = True) -> str:
    return f"{t['texto']}\n{t['url']}" if with_link else t["texto"]


# ---------- correo ----------

def send_email(env: dict, tweets: list[dict]) -> None:
    to = env.get("X_EMAIL_TO", "raulrgleon@gmail.com")
    fecha = datetime.now(TZ).strftime("%d/%m/%Y")
    items_html, items_txt = [], []
    for i, t in enumerate(tweets, 1):
        intent = "https://x.com/intent/post?" + urllib.parse.urlencode({"text": full_text(t)})
        hora = datetime.fromisoformat(t["hora"]).strftime("%H:%M")
        items_html.append(
            f'<div style="border:1px solid #e5e5e5;border-radius:10px;padding:14px;margin:0 0 14px">'
            f'<div style="color:#888;font-size:12px">#{i} · sugerido {hora}</div>'
            f'<p style="font-size:16px;line-height:1.45;margin:8px 0">{html.escape(t["texto"])}<br>'
            f'<a href="{html.escape(t["url"])}">{html.escape(t["url"])}</a></p>'
            f'<a href="{html.escape(intent)}" style="display:inline-block;background:#000;color:#fff;'
            f'padding:8px 16px;border-radius:20px;text-decoration:none;font-weight:bold">Publicar en X</a></div>'
        )
        items_txt.append(f"#{i} ({hora})\n{full_text(t)}\nPublicar: {intent}\n")
    msg = EmailMessage()
    msg["From"] = env.get("MAIL_FROM", "TuHoy <info@tuhoy.com>")
    msg["To"] = to
    msg["Subject"] = f"Los {len(tweets)} posts de X de hoy ({fecha})"
    msg.set_content("\n".join(items_txt))
    msg.add_alternative(
        '<div style="font-family:Arial,sans-serif;max-width:560px">'
        f"<h2>Posts para @tuhoy_ · {fecha}</h2>"
        "<p>Toca <b>Publicar en X</b> con la sesión de @tuhoy_ abierta, o prográmalos en X a la hora sugerida.</p>"
        + "".join(items_html) + "</div>",
        subtype="html",
    )
    user = env.get("BREVO_SMTP_LOGIN") or env.get("MAIL_OPTIONS_AUTH_USER")
    password = env.get("BREVO_SMTP_KEY") or env.get("MAIL_OPTIONS_AUTH_PASS")
    with smtplib.SMTP(env.get("MAIL_OPTIONS_HOST", "smtp-relay.brevo.com"), int(env.get("MAIL_OPTIONS_PORT", "587"))) as s:
        s.starttls()
        s.login(user.strip("'\""), password.strip("'\""))
        s.send_message(msg)
    log(f"correo enviado a {to} con {len(tweets)} posts")


# ---------- API de X (OAuth 1.0a) ----------

def oauth_header(env: dict, method: str, url: str) -> str:
    params = {
        "oauth_consumer_key": env["X_API_KEY"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": env["X_ACCESS_TOKEN"],
        "oauth_version": "1.0",
    }
    q = lambda s: urllib.parse.quote(s, safe="~")  # noqa: E731
    base = "&".join([method, q(url), q("&".join(f"{q(k)}={q(v)}" for k, v in sorted(params.items())))])
    key = f"{q(env['X_API_SECRET'])}&{q(env['X_ACCESS_SECRET'])}"
    params["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join(f'{q(k)}="{q(v)}"' for k, v in sorted(params.items()))


def post_tweet(env: dict, text: str) -> str:
    url = "https://api.x.com/2/tweets"
    req = urllib.request.Request(
        url,
        data=json.dumps({"text": text}).encode(),
        method="POST",
        headers={"Authorization": oauth_header(env, "POST", url), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())["data"]["id"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"X {e.code}: {e.read().decode(errors='replace')[:300]}") from e


def links_for(env: dict, index: int) -> bool:
    """X_LINKS: all | none | número de posts con enlace (los más importantes primero)."""
    mode = (env.get("X_LINKS") or "all").lower()
    if mode == "all":
        return True
    if mode == "none":
        return False
    return index < int(mode)


def assign_links(env: dict, tweets: list[dict], queue: dict) -> None:
    """Con X_LINKS numérico, el cupo es por día (cada enlace cuesta $0.20): se reparte entre tandas."""
    mode = (env.get("X_LINKS") or "all").lower()
    if mode in ("all", "none"):
        for t in tweets:
            t["link"] = mode == "all"
        return
    today = datetime.now(TZ).date().isoformat()
    used = sum(1 for t in queue.get("historial", []) if t.get("link") and t.get("fecha") == today)
    left = max(0, int(mode) - used)
    for i, t in enumerate(tweets):
        t["link"] = i < left


def post_due(env: dict) -> None:
    if not QUEUE.exists():
        return
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    now = datetime.now(TZ)
    for i, t in enumerate(queue.get("pendientes", [])):
        if t.get("tweet_id") or t.get("vencido") or datetime.fromisoformat(t["hora"]) > now:
            continue
        if now - datetime.fromisoformat(t["hora"]) > timedelta(hours=2):
            t["vencido"] = True
            log(f"vencido, no se publica: {t['titulo']}")
            continue
        try:
            t["tweet_id"] = post_tweet(env, full_text(t, t["link"] if "link" in t else links_for(env, i)))
            log(f"publicado {t['tweet_id']}: {t['titulo']}")
        except RuntimeError as e:
            log(f"error al publicar {t['titulo']}: {e}")
            break
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------- principal ----------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--post-due", action="store_true")
    ap.add_argument("-n", type=int, help="número de posts (por defecto X_POSTS o 7)")
    args = ap.parse_args()

    env = writer.load_env()
    args.n = args.n or int(env.get("X_POSTS") or 8)
    mode = (env.get("X_MODE") or "email").lower()
    if args.post_due:
        if mode == "api":
            post_due(env)
        return 0

    ghost = daily.Ghost(env["GHOST_URL"], env["GHOST_ADMIN_API_KEY"])
    seen = already_tweeted()
    posts = [p for p in recent_posts(ghost) if p["id"] not in seen]
    if not posts:
        log("sin notas nuevas")
        return 0
    if len(posts) > args.n:
        log(f"{len(posts)} notas nuevas; se escriben las {args.n} más importantes")
    tweets = compose(posts, min(args.n, len(posts)))
    if not tweets:
        log("el modelo no devolvió posts válidos")
        return 1

    queue = json.loads(QUEUE.read_text(encoding="utf-8")) if QUEUE.exists() else {}
    now = datetime.now(TZ)
    # Se conservan los pendientes aún por publicar; los publicados o vencidos de hace más de un día se limpian.
    pending = [
        t
        for t in queue.get("pendientes", [])
        if not t.get("tweet_id") and not t.get("vencido")
        or now - datetime.fromisoformat(t["hora"]) < timedelta(days=1)
    ]
    waiting = [t for t in pending if not t.get("tweet_id") and not t.get("vencido")]
    schedule(tweets, env, waiting, now)
    assign_links(env, tweets, queue)

    if args.dry_run:
        for t in tweets:
            link = "con enlace" if t["link"] else "sin enlace"
            print(f"[{datetime.fromisoformat(t['hora']).strftime('%H:%M')}] ({len(t['texto'])}, {link}) {t['texto']}\n    {t['url']}\n")
        return 0

    historial = (
        queue.get("historial", []) + [{"id": t["id"], "fecha": t["hora"][:10], "link": t["link"]} for t in tweets]
    )[-500:]
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(
        json.dumps({"pendientes": pending + tweets, "historial": historial}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if mode == "api":
        log(f"{len(tweets)} posts encolados para X")
        post_due(env)
    else:
        send_email(env, tweets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
