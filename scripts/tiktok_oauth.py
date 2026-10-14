#!/usr/bin/env python3
"""Autoriza @tuhoynoticias para que tiktok_posts.py publique.

1. Crea una app en https://developers.tiktok.com/ (Content Posting API, Direct Post,
   ámbito video.publish). Redirect URI: https://tuhoy.com/
2. Verifica la propiedad de https://tuhoy.com/ (URL properties) para que TikTok pueda
   leer las fotos de Ghost.
3. Pon TT_CLIENT_KEY y TT_CLIENT_SECRET en .env.
4. python3 scripts/tiktok_oauth.py
   Abre la URL, entra con @tuhoynoticias, copia la dirección a la que te manda
   (tuhoy.com/?code=...) y pégala:

   python3 scripts/tiktok_oauth.py --callback-url 'https://tuhoy.com/?code=...&state=...'

El token queda en data/tt_auth.json (gitignore, 600). No lo subas a git.
"""
from __future__ import annotations

import argparse
import secrets
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tiktok_posts as tt  # noqa: E402
import writer  # noqa: E402

SCOPES = "user.info.basic,video.publish"
REDIRECT = "https://tuhoy.com/"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--callback-url", default="")
    ap.add_argument("--code", default="")
    args = ap.parse_args()
    env = writer.load_env()
    key, secret = env.get("TT_CLIENT_KEY") or "", env.get("TT_CLIENT_SECRET") or ""
    if not key or not secret:
        print("Pon TT_CLIENT_KEY y TT_CLIENT_SECRET en .env")
        return 1
    redirect = env.get("TT_REDIRECT_URI") or REDIRECT
    if not args.callback_url and not args.code:
        state = secrets.token_urlsafe(16)
        q = urllib.parse.urlencode(
            {
                "client_key": key,
                "scope": SCOPES,
                "response_type": "code",
                "redirect_uri": redirect,
                "state": state,
            }
        )
        print("Abre esta URL con la cuenta @tuhoynoticias:\n")
        print(f"https://www.tiktok.com/v2/auth/authorize/?{q}\n")
        print("Cuando TikTok te devuelva a tuhoy.com, copia la URL completa y corre:")
        print("python3 scripts/tiktok_oauth.py --callback-url 'PEGA_AQUI'")
        return 0
    code = args.code
    if args.callback_url:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(args.callback_url).query)
        code = (q.get("code") or [""])[0]
        err = (q.get("error") or [""])[0]
        if err:
            print("TikTok rechazó el acceso:", err, (q.get("error_description") or [""])[0])
            return 1
    if not code:
        print("No hay code en la URL")
        return 1
    data = tt.form_post(
        f"{tt.API}/v2/oauth/token/",
        {
            "client_key": key,
            "client_secret": secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect,
        },
    )
    if not data.get("access_token"):
        print("TikTok no dio token:", {k: v for k, v in data.items() if k != "access_token"})
        return 1
    from datetime import datetime, timedelta, timezone

    tt.save_json(
        tt.AUTH,
        {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "open_id": data.get("open_id"),
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(seconds=int(data.get("expires_in") or 86400))
            ).isoformat(),
            "scope": data.get("scope"),
        },
        0o600,
    )
    print("Listo. Token guardado para", data.get("open_id") or "@tuhoynoticias")
    print("Enciende TT_MODE=api en .env cuando la app esté lista.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
