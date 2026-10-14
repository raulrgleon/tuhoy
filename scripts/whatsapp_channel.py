#!/usr/bin/env python3
"""Prepara 1–2 notas al día para el canal de WhatsApp TuHoy.

Meta no tiene API oficial para publicar en canales (solo se pega a mano en la app).
Las pasarelas no oficiales conectan el WhatsApp del teléfono y pueden bloquear el
número de avisos. Este script envía a Raul un correo con foto, texto y enlace
listos para pegar en https://www.whatsapp.com/channel/0029Vb9BtwBA89MgSh7P3a45

  python3 scripts/whatsapp_channel.py --dry-run   # muestra las notas, no envía
  python3 scripts/whatsapp_channel.py             # un correo al día si WA_MODE=email
"""
from __future__ import annotations

import argparse
import html
import json
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import tiktok_posts as tt  # noqa: E402
import writer  # noqa: E402

TZ = ZoneInfo("America/Chicago")
X_QUEUE = ROOT / "data" / "x_queue.json"
WA_QUEUE = ROOT / "data" / "wa_queue.json"
LOG = ROOT / "logs" / "whatsapp-channel.log"
CANAL = "https://www.whatsapp.com/channel/0029Vb9BtwBA89MgSh7P3a45"
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def log(msg: str) -> None:
    line = f"{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')} [wa] {msg}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fecha_larga(d: datetime) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def pie(t: dict) -> str:
    text = (t.get("texto") or t.get("titulo") or "").strip()
    url = (t.get("url") or "").strip()
    return f"{text}\n\n{url}".strip() if url else text


def pick_today(x_queue: dict, done: set[str], now: datetime, n: int) -> list[dict]:
    today = now.date()
    out = []
    for t in x_queue.get("pendientes", []):
        hora = datetime.fromisoformat(t["hora"])
        if hora.date() != today or t["id"] in done:
            continue
        out.append(t)
    return sorted(out, key=lambda t: t["hora"])[:n]


def ya_enviado_hoy(historial: list[dict], now: datetime) -> bool:
    dia = now.date().isoformat()
    return any(h.get("fecha") == dia for h in historial)


def send_email(env: dict, to: str, notas: list[dict], fotos: dict[str, str], now: datetime) -> None:
    fecha = fecha_larga(now)
    bloques_txt = []
    bloques_html = []
    for i, t in enumerate(notas, 1):
        cuerpo = pie(t)
        foto = fotos.get(t["id"]) or ""
        bloques_txt.append(f"#{i} {t['titulo']}\nFoto: {foto or '(sin foto)'}\n\n{cuerpo}\n")
        img = (
            f'<p><img src="{html.escape(foto)}" alt="" width="560" '
            'style="max-width:100%;border-radius:8px"></p>'
            if foto
            else ""
        )
        bloques_html.append(
            '<div style="border:1px solid #e5e5e5;border-radius:10px;padding:14px;margin:0 0 18px">'
            f'<div style="color:#888;font-size:12px">#{i} · pega esto en el canal</div>'
            f"<h3 style=\"margin:8px 0\">{html.escape(t['titulo'])}</h3>"
            f"{img}"
            f'<pre style="white-space:pre-wrap;font-family:Arial,sans-serif;font-size:16px;'
            f'line-height:1.45">{html.escape(cuerpo)}</pre></div>'
        )
    msg = EmailMessage()
    msg["From"] = env.get("MAIL_FROM", "TuHoy <info@tuhoy.com>")
    msg["To"] = to
    msg["Subject"] = f"Canal WhatsApp · {len(notas)} notas para pegar ({fecha})"
    msg.set_content(
        f"Abre el canal TuHoy, toca el lápiz, adjunta la foto y pega el texto.\n"
        f"Canal: {CANAL}\n\n" + "\n---\n".join(bloques_txt)
    )
    msg.add_alternative(
        '<div style="font-family:Arial,sans-serif;max-width:560px">'
        f"<h2>Canal de WhatsApp · {html.escape(fecha)}</h2>"
        "<p>Meta no deja publicar en el canal por API. Abre "
        f'<a href="{html.escape(CANAL)}">el canal TuHoy</a>, toca el lápiz, '
        "adjunta la foto y pega el texto de cada recuadro.</p>"
        + "".join(bloques_html)
        + "</div>",
        subtype="html",
    )
    user = env.get("BREVO_SMTP_LOGIN") or env.get("MAIL_OPTIONS_AUTH_USER")
    password = env.get("BREVO_SMTP_KEY") or env.get("MAIL_OPTIONS_AUTH_PASS")
    with smtplib.SMTP(
        env.get("MAIL_OPTIONS_HOST", "smtp-relay.brevo.com"),
        int(env.get("MAIL_OPTIONS_PORT", "587")),
    ) as s:
        s.starttls()
        s.login(user.strip("'\""), password.strip("'\""))
        s.send_message(msg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    env = writer.load_env()
    mode = (env.get("WA_MODE") or "off").lower()
    if mode != "email" and not args.dry_run:
        return 0

    n = max(1, int(env.get("WA_POSTS") or "2"))
    now = datetime.now(TZ)
    wa_q = load(WA_QUEUE, {"historial": []})
    if ya_enviado_hoy(wa_q["historial"], now) and not args.dry_run:
        return 0

    notas = pick_today(load(X_QUEUE, {}), {h["id"] for h in wa_q["historial"]}, now, n)
    if args.dry_run:
        if not notas:
            print("nada que enviar hoy")
            return 0
        for t in notas:
            print(f"[{datetime.fromisoformat(t['hora']).strftime('%H:%M')}] {pie(t)}\n")
        return 0

    if not notas:
        log("no hay notas de hoy para el canal")
        return 0

    fotos = {}
    for t in notas:
        try:
            fotos[t["id"]] = tt.feature_image(env, t["id"]) or ""
        except RuntimeError as e:
            log(f"sin foto {t['titulo']}: {e}")
            fotos[t["id"]] = ""

    to = env.get("WA_EMAIL_TO") or env.get("X_EMAIL_TO") or "raulrgleon@gmail.com"
    try:
        send_email(env, to, notas, fotos, now)
    except Exception as e:
        log(f"error al enviar el correo: {e}")
        return 1

    for t in notas:
        wa_q["historial"].append({"id": t["id"], "fecha": now.date().isoformat()})
        log(f"listo para pegar: {t['titulo']}")
    wa_q["historial"] = wa_q["historial"][-200:]
    save_json(WA_QUEUE, wa_q)
    log(f"correo enviado a {to} con {len(notas)} notas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
