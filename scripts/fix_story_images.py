#!/usr/bin/env python3
"""Sustituye fotos genéricas por una imagen de Commons que corresponde a cada nota."""
from __future__ import annotations

import html
import importlib.util
import json
import re
import time
import urllib.parse

spec = importlib.util.spec_from_file_location("daily", "/home/raul/tuhoy/scripts/daily_edition.py")
daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daily)

# Archivo de Wikimedia Commons elegido a mano para cada slug.
ARCHIVOS = {
    "cinco-detenidos-a-la-salida-del-pavo-en-moroni-utah-los-ninos-faltan-a-clase": (
        "File:Moroni main street.jpg",
        "Calle principal de Moroni, Utah, donde ICE detuvo a cinco personas a la salida de la planta.",
    ),
    "austin-el-juez-deja-preso-al-repartidor-venezolano-tiroteado-por-ice": (
        "File:Downtown Austin Skyline On Town Lake.jpg",
        "Austin, Texas, donde un agente de ICE tiroteó al repartidor Wilber Garcés Pérez.",
    ),
    "houston-la-muerte-de-lorenzo-salgado-araujo-enciende-el-voto-latino-en-texas": (
        "File:Downtown Houston, TX Skyline - 2018.jpg",
        "Houston, Texas. La muerte de Lorenzo Salgado Araujo a manos de ICE moviliza el voto latino.",
    ),
    "florida-avisa-177-000-inmigrantes-con-papeles-pueden-perder-el-medicaid": (
        "File:Florida’s Historic Capitol and Florida State Capitol 2.JPG",
        "Capitolio de Florida en Tallahassee, donde el Estado identifica a 177.000 inmigrantes que pueden perder Medicaid.",
    ),
    "un-juez-de-manhattan-tumba-las-detenciones-de-ice-en-los-pasillos-de-inmigracion": (
        "File:Jacob Javits Federal Building 002.jpg",
        "Edificio federal Jacob Javits (26 Federal Plaza), sede de los juzgados de inmigración de Manhattan.",
    ),
    "el-presidente-de-cornell-dice-que-la-universidad-debe-hacer-mas-tras-la-denuncia-de-violacion-en-grupo-en-una-fraternidad": (
        "File:Cornell University - McGraw Tower.jpg",
        "Torre McGraw del campus de Cornell en Ithaca, Nueva York.",
    ),
    "thomas-piketty-el-nerviosismo-que-vemos-hoy-en-washington-tiene-que-ver-con-el-hecho-de-que-ee-uu-esta-perdiendo-el-control-sobre-el-mund": (
        "File:Thomas Piketty2.jpg",
        "El economista Thomas Piketty.",
    ),
    "por-que-canada-contempla-una-improbable-invasion-desde-ee-uu-y-que-papel-juega-el-caso-de-venezuela": (
        "File:Peace Arch, U.S.-Canada border.jpg",
        "El Peace Arch en la frontera entre Estados Unidos y Canadá.",
    ),
    "como-se-compara-flavio-bolsonaro-con-su-padre-jair-y-cuanto-cambia-el-duelo-con-lula-por-la-presidencia-de-brasil-4-anos-despues": (
        "File:Foto oficial do senador Flávio Bolsonaro (v. AgSen).jpg",
        "El senador Flávio Bolsonaro, candidato a la presidencia de Brasil.",
    ),
    "elecciones-en-brasil-flavio-bolsonaro-y-lula-da-silva-van-a-una-segunda-vuelta-en-la-que-el-presidente-enfrenta-una-dificil-remontada": (
        "File:Foto oficial de Luiz Inácio Lula da Silva (2023–2027).jpg",
        "El presidente Luiz Inácio Lula da Silva, que irá a balotaje el 25 de octubre.",
    ),
}


def commons_file(title: str) -> tuple[bytes, str, str, str] | None:
    qs = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata",
            "iiurlwidth": 1600,
        }
    )
    data = json.loads(daily.http_get("https://commons.wikimedia.org/w/api.php?" + qs))
    pages = (data.get("query") or {}).get("pages") or {}
    for page in pages.values():
        info = (page.get("imageinfo") or [None])[0]
        if not info:
            continue
        url = info.get("thumburl") or info.get("url")
        mime = info.get("mime") or "image/jpeg"
        meta = info.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value") or "Wikimedia Commons"
        artist = daily.strip_html((meta.get("Artist") or {}).get("value") or "Wikimedia Commons")
        blob = None
        for attempt in range(4):
            try:
                blob = daily.http_get(url, timeout=30)
                break
            except Exception as e:
                daily.log(f"retry {title}: {e}")
                time.sleep(3 + attempt * 2)
        if not blob:
            return None
        ext = "jpg" if "jpeg" in mime else "png"
        return blob, f"{re.sub('[^a-z0-9]+', '-', title.lower())[:48].strip('-')}.{ext}", mime, f"Foto: {artist}. {lic}."
    return None


def main() -> int:
    env = daily.load_env()
    ghost = daily.Ghost(env["GHOST_URL"], env["GHOST_ADMIN_API_KEY"])
    code, resp = ghost.get("/posts/?limit=40")
    posts = {p["slug"]: p for p in (resp.get("posts") or [])}
    n = 0
    for slug, (filename, alt) in ARCHIVOS.items():
        post = posts.get(slug)
        if not post:
            daily.log(f"missing {slug}")
            continue
        picked = commons_file(filename)
        if not picked:
            daily.log(f"no file {filename}")
            continue
        blob, name, mime, cap = picked
        url = ghost.upload_image(blob, name, mime)
        if not url:
            daily.log(f"upload fail {slug}")
            continue
        body = post.get("html") or ""
        body = re.sub(r"<p><em>Foto:.*?</em></p>\s*$", "", body, flags=re.S)
        body = body.rstrip() + f"\n<p><em>{html.escape(alt)} {html.escape(cap)}</em></p>"
        payload = {
            "posts": [
                {
                    "feature_image": url,
                    "feature_image_alt": alt,
                    "feature_image_caption": alt,
                    "updated_at": post["updated_at"],
                }
            ]
        }
        c, r = ghost.put_json(f"/posts/{post['id']}/", payload)
        daily.log(f"image {slug} -> {c} {url}")
        n += 1
    daily.log(f"fixed images {n}")
    return 0 if n else 1


if __name__ == "__main__":
    raise SystemExit(main())
