#!/usr/bin/env python3
"""Boletín diario «Lo que importa hoy»: las notas principales de las últimas 24 horas por correo.

Crea en Ghost un post de solo correo (no aparece en la web) y lo envía a los suscriptores de la
newsletter con Mailgun. Corre a las 07:00 America/Chicago, después de la edición de las 06:00.

Reglas para no dar sobresaltos:
- Un boletín por día como máximo (registro en data/digest_state.json).
- No envía si hay menos de DIGEST_MIN notas con foto en las últimas 24 horas.
- Solo actúa si DIGEST_MODE=on en .env.

  python3 scripts/daily_digest.py --dry-run          # muestra las notas y el HTML, sin crear nada
  python3 scripts/daily_digest.py --test correo@x    # envía una prueba solo a ese suscriptor
  python3 scripts/daily_digest.py                    # envía el boletín del día (cron)
"""
import argparse
import html
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import daily_edition as daily  # noqa: E402

TZ = ZoneInfo("America/Chicago")
STATE = ROOT / "data" / "digest_state.json"
LOG = ROOT / "logs" / "digest.log"
TAG = "#boletin"
TEST_LABEL = "prueba-boletin"
SKIP_TAGS = {"#resumen-automatico", TAG}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
FACEBOOK = "https://www.facebook.com/tuhoynoticias"
INSTAGRAM = "https://www.instagram.com/tuhoynoticias/"
WHATSAPP_CANAL = "https://www.whatsapp.com/channel/0029Vb9BtwBA89MgSh7P3a45"


def log(msg: str) -> None:
    line = f"{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')} [boletin] {msg}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def fecha_larga(d: datetime) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def section(p: dict) -> str:
    for t in p.get("tags") or []:
        if not t["name"].startswith("#"):
            return t["slug"]
    return ""


def pick_posts(posts: list[dict], now: datetime, n: int, per_section: int = 3) -> list[dict]:
    """Últimas 24 h, con foto y sin etiquetas internas. Las secciones se turnan (Inmigración
    primero, máximo `per_section` de cada una) para que el boletín no sea de un solo tema."""
    since = now - timedelta(hours=24)
    groups: dict[str, list[dict]] = {}
    for p in posts:
        published = datetime.fromisoformat(p["published_at"].replace("Z", "+00:00"))
        tags = {t["name"] for t in p.get("tags") or []}
        if published < since or not p.get("feature_image") or tags & SKIP_TAGS:
            continue
        groups.setdefault(section(p), []).append(p)
    for items in groups.values():
        items.sort(key=lambda p: (not p.get("featured"), -datetime.fromisoformat(
            p["published_at"].replace("Z", "+00:00")).timestamp()))
        del items[per_section:]
    order = sorted(groups, key=lambda s: (s != "inmigracion", -len(groups[s])))
    out = []
    while len(out) < n and any(groups[s] for s in order):
        for s in order:
            if groups[s] and len(out) < n:
                out.append(groups[s].pop(0))
    return out


def build_html(posts: list[dict], today: datetime) -> str:
    parts = [f"<p>Buenos días. Estas son las noticias que importan hoy, {fecha_larga(today)}.</p>"]
    for i, p in enumerate(posts):
        url = html.escape(p["url"])
        title = html.escape(p["title"])
        excerpt = html.escape(p.get("custom_excerpt") or p.get("excerpt") or "")
        if i == 0:
            parts.append(f'<img src="{html.escape(p["feature_image"])}" alt="{title}">')
        parts.append(f'<h2><a href="{url}">{title}</a></h2>')
        if excerpt:
            parts.append(f"<p>{excerpt}</p>")
        parts.append(f'<p><a href="{url}">Leer la nota completa →</a></p>')
        if i < len(posts) - 1:
            parts.append("<hr>")
    parts.append(
        "<hr><p>¿Te reenviaron este correo? Suscríbete gratis en "
        '<a href="https://tuhoy.com/#/portal/signup">tuhoy.com</a>. Síguenos en '
        f'<a href="{FACEBOOK}">Facebook</a>, <a href="{INSTAGRAM}">Instagram</a>, '
        f'<a href="https://x.com/TuHoy_">X</a> y el <a href="{WHATSAPP_CANAL}">canal de WhatsApp</a>. '
        "¿Sabes algo que debamos contar? Escríbenos por "
        '<a href="https://wa.me/14028240388">WhatsApp al (402) 824-0388</a>.</p>'
    )
    return "\n".join(parts)


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"enviados": []}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test", metavar="CORREO", help="Envía una prueba solo a este suscriptor.")
    args = ap.parse_args()

    env = daily.load_env()
    if (env.get("DIGEST_MODE") or "off").lower() != "on" and not (args.dry_run or args.test):
        return 0
    n = int(env.get("DIGEST_POSTS") or 6)
    min_posts = int(env.get("DIGEST_MIN") or 3)
    newsletter = env.get("DIGEST_NEWSLETTER") or "default-newsletter"

    now = datetime.now(timezone.utc)
    today = now.astimezone(TZ)
    state = load_state()
    if not (args.dry_run or args.test) and any(e["fecha"] == today.date().isoformat() for e in state["enviados"]):
        return 0

    ghost = daily.Ghost(env["GHOST_URL"], env["GHOST_ADMIN_API_KEY"])
    code, resp = ghost.get("/posts/?limit=50&filter=status:published&include=tags&order=published_at%20desc")
    if code >= 300:
        log(f"no se pudieron leer las notas: {code} {resp}")
        return 1
    posts = pick_posts(resp.get("posts") or [], now, n)
    if len(posts) < min_posts:
        log(f"no se envía: solo {len(posts)} notas con foto en 24 h (mínimo {min_posts})")
        return 0

    title = f"Lo que importa hoy: {fecha_larga(today)}"
    body = build_html(posts, today)
    if args.dry_run:
        print(title)
        for p in posts:
            print(" -", p["title"])
        print("\n" + body)
        return 0

    draft = {
        "posts": [{
            "title": title,
            "status": "draft",
            "email_only": True,
            "html": body,
            "custom_excerpt": posts[0]["title"][:300],
            "tags": [{"name": TAG}],
        }]
    }
    code, resp = ghost.post_json("/posts/?source=html", draft)
    if code >= 300:
        log(f"no se pudo crear el borrador: {code} {resp}")
        return 1
    post = resp["posts"][0]

    segment = "all"
    if args.test:
        # Las integraciones no pueden usar las vistas previas de correo de Ghost: la prueba es un envío
        # real filtrado por una etiqueta que solo lleva el miembro de prueba.
        code, resp = ghost.get(f"/members/?filter=email:'{args.test}'")
        members = [m for m in resp.get("members") or [] if m["email"].lower() == args.test.lower()]
        if code >= 300 or not members:
            log(f"prueba: {args.test} no es suscriptor de la newsletter")
            ghost._req("DELETE", f"/posts/{post['id']}/")
            return 1
        m = members[0]
        labels = [{"name": lb["name"]} for lb in m.get("labels") or []]
        if TEST_LABEL not in {lb["name"] for lb in labels}:
            ghost.put_json(f"/members/{m['id']}/", {"members": [{"labels": labels + [{"name": TEST_LABEL}]}]})
        segment = f"label:{TEST_LABEL}"

    code, resp = ghost.put_json(
        f"/posts/{post['id']}/?newsletter={newsletter}&email_segment={segment}",
        {"posts": [{"status": "published", "updated_at": post["updated_at"]}]},
    )
    if code >= 300:
        log(f"no se pudo enviar: {code} {resp}")
        return 1
    if args.test:
        log(f"prueba enviada a {args.test} ({post['id']})")
        return 0
    state["enviados"].append({"fecha": today.date().isoformat(), "post_id": post["id"],
                              "notas": [p["slug"] for p in posts]})
    state["enviados"] = state["enviados"][-120:]
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"enviado «{title}» con {len(posts)} notas ({post['id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
