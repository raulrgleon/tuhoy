#!/usr/bin/env python3
"""Repara texto residual, descripciones, títulos SEO e indexación de las notas de TuHoy."""
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import pathlib
import re
import urllib.parse

spec = importlib.util.spec_from_file_location("daily", "/home/raul/tuhoy/scripts/daily_edition.py")
daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daily)

# Menú de BBC Mundo que el extractor antiguo coló dentro de los párrafos.
MENU_RE = re.compile(
    r"BBC News, Mundo Ir al contenido Noticias Video Secciones Noticias América Latina Internacional EE\.UU\.\s*|"
    r"Economía Ciencia Salud Cultura Tecnología Hay Festival Centroamérica Cuenta\s*(?:América Latina Internacional EE\.UU\.)?\s*"
)
BOILERPLATE_RE = re.compile(
    r"(?:<h2[^>]*>\s*Contexto\s*</h2>\s*)?<p>El caso importa porque toca a familias.*?</p>\s*", re.S
)
DEMO_RE = re.compile(r"<p><strong>Edición de demostración</strong>.*?</p>\s*", re.S)
AUTO_SOURCES = ("bbc.com", "france24.com")

DEKS_PATH = pathlib.Path("/home/raul/tuhoy/data/original_deks.json")
ORIGINAL_DEKS: dict[str, str] = json.loads(DEKS_PATH.read_text()) if DEKS_PATH.exists() else {}

# Titulares de más de 65 caracteres: versión de hasta 60 para la etiqueta <title>.
META_TITLES = {
    "Venezuela: la tensión interna": "Venezuela: pugna interna entre apertura y continuidad",
    "Por qué arrestaron al fiscal general en Bolivia": "Bolivia: por qué arrestaron al fiscal general Roger Mariaca",
    "Colapsa en Hawái": "Colapsa en Hawái el arco marino Hōlei, de 550 años",
    "Su esposa fue arrastrada por un tsunami": "Bucea desde hace años para sentirse cerca de su esposa",
    "En fotos: las multitudinarias protestas en España": "En fotos: protestas masivas en España por la vivienda",
    "Cinco detenidos a la salida del pavo": "ICE en Moroni, Utah: cinco detenidos a la salida del pavo",
    "Houston: la muerte de Lorenzo Salgado": "Houston: la muerte de Lorenzo Salgado moviliza el voto latino",
    "Florida avisa: 177.000 inmigrantes": "Florida: 177.000 inmigrantes legales pueden perder Medicaid",
    "Un juez de Manhattan tumba": "Juez de Manhattan tumba los arrestos de ICE en tribunales",
    "El presidente de Cornell": "Cornell \"debe hacer más\" tras la denuncia de violación",
    "Thomas Piketty": "Piketty: el nerviosismo de Washington y la pérdida de control",
    "Por qué Canadá contempla": "Por qué Canadá contempla una (improbable) invasión de EE.UU.",
    "Cómo se compara Flávio Bolsonaro": "Flávio vs. Jair Bolsonaro: qué cambia en el duelo con Lula",
    "Elecciones en Brasil: Flávio Bolsonaro": "Brasil: Flávio Bolsonaro y Lula van a segunda vuelta",
    "El Senado aprueba por 77 a 22": "El Senado aprueba un marco para el deporte universitario",
    "Ocho marineros del Abraham Lincoln": "Ocho marineros del USS Abraham Lincoln intentaron suicidarse",
    "Un juez obliga a devolver la acreditación": "Juez ordena devolver la acreditación a CNN, MS NOW y Politico",
    "Cinco detenidos junto a una base": "Inglaterra: cinco detenidos junto a una base de EE.UU.",
    "Netanyahu: un piloto apuñaló": "Netanyahu: un piloto apuñaló a otro e intentó estrellar el avión",
    "Tennessee suspende las ejecuciones": "Tennessee suspende ejecuciones tras fallar la inyección a Pike",
    "La Corte Suprema frena el recorte": "La Corte Suprema frena el recorte al voto por correo",
}


def plain(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def clean_body(body: str, title: str) -> str:
    body = DEMO_RE.sub("", BOILERPLATE_RE.sub("", body))

    def fix_paragraph(match: re.Match) -> str:
        inner = MENU_RE.sub("", match.group(1)).strip()
        text = plain(inner)
        if not text:
            return ""
        is_meta = text.startswith(("Fuente:", "Foto:"))
        if not is_meta and (
            len(text) < 40
            or text[:1].islower()
            or daily.looks_like_nav(text)
            or daily.similar(text, title)
        ):
            return ""
        return f"<p>{inner}</p>"

    body = re.sub(r"<p>(.*?)</p>\s*", fix_paragraph, body, flags=re.S)

    def fix_link(match: re.Match) -> str:
        href = daily.clean_source_url(html.unescape(match.group(1)))
        label = match.group(2)
        if label.strip().startswith("http"):
            label = "artículo original"
        return f'<a href="{html.escape(href)}">{label}</a>'

    return re.sub(r'<a href="([^"]+)">(.*?)</a>', fix_link, body, flags=re.S)


def lead_text(body: str) -> str:
    for para in re.findall(r"<p>(.*?)</p>", body, flags=re.S):
        text = plain(para)
        if len(text) > 40 and not text.startswith(("Fuente:", "Foto:")):
            return text
    return ""


def is_truncated(excerpt: str, lead: str) -> bool:
    stem = excerpt.rstrip(".… ").strip()
    return bool(stem) and lead.startswith(stem) and len(lead) > len(stem) + 2


def plan_post(post: dict) -> dict:
    title = post["title"]
    body = clean_body(post.get("html") or "", title)
    lead = lead_text(body)
    excerpt = ORIGINAL_DEKS.get(title) or (post.get("custom_excerpt") or "").strip()
    if (
        not excerpt
        or excerpt.startswith("Edición de demostración")
        or is_truncated(excerpt, lead)
        or daily.looks_like_nav(excerpt)
    ):
        excerpt = daily.smart_cut(daily.first_sentence(lead), 300) or excerpt
    if 70 <= len(excerpt) <= 160:
        meta_desc = excerpt
    elif title in ORIGINAL_DEKS:
        meta_desc = daily.smart_cut(excerpt, 155)
    else:
        meta_desc = daily.smart_cut(daily.first_sentence(lead) or excerpt, 155)

    meta_title = None
    for prefix, short in META_TITLES.items():
        if title.startswith(prefix):
            meta_title = short
            break
    if meta_title is None:
        meta_title = daily.seo_meta_title(title)

    tags = [{"name": t["name"]} for t in post.get("tags") or [] if t["slug"] != "edicion-de-demostracion"]
    hosts = {urllib.parse.urlsplit(h).netloc.replace("www.", "") for h in re.findall(r'href="([^"]+)"', body)}
    if any(src in host for host in hosts for src in AUTO_SOURCES) and not any(t["name"] == daily.AUTO_TAG for t in tags):
        tags.append({"name": daily.AUTO_TAG})

    return {
        "html": body,
        "custom_excerpt": excerpt,
        "meta_title": meta_title,
        "meta_description": meta_desc,
        "og_title": None,
        "og_description": None,
        "twitter_title": None,
        "twitter_description": None,
        "canonical_url": None,
        "tags": tags,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    env = daily.load_env()
    ghost = daily.Ghost(env["GHOST_URL"], env["GHOST_ADMIN_API_KEY"])
    code, resp = ghost.get("/posts/?limit=all&formats=html&include=tags")
    if code >= 300:
        daily.log(f"seo posts fail {code}")
        return 1

    changed = 0
    for post in resp.get("posts") or []:
        plan = plan_post(post)
        diff = {
            k: v
            for k, v in plan.items()
            if (post.get(k) or None) != (v or None) and k != "tags"
        }
        old_tags = sorted(t["name"] for t in post.get("tags") or [])
        if old_tags != sorted(t["name"] for t in plan["tags"]):
            diff["tags"] = plan["tags"]
        if not diff:
            continue
        changed += 1
        if args.dry_run:
            print("==", post["slug"][:70], sorted(diff))
            for key in ("meta_title", "meta_description", "custom_excerpt"):
                if key in diff:
                    print(f"   {key}: {diff[key]}")
            continue
        payload = {"posts": [{**diff, "updated_at": post["updated_at"]}]}
        status, result = ghost.put_json(f"/posts/{post['id']}/?source=html", payload)
        if status >= 300:
            daily.log(f"seo post fail {post['slug']} {status} {result}")

    if not args.dry_run:
        code, tags = ghost.get("/tags/?limit=all&include=count.posts")
        for tag in tags.get("tags") or []:
            if tag["slug"] == "edicion-de-demostracion" and not tag["count"]["posts"]:
                status, _ = ghost._req("DELETE", f"/tags/{tag['id']}/")
                daily.log(f"seo delete empty tag {tag['slug']} {status}")
    daily.log(f"seo posts {'to change' if args.dry_run else 'updated'} {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
