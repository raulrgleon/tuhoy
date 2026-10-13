#!/usr/bin/env python3
"""Pone en cada nota la foto de la fuente y el crédito del diario."""
import argparse
import html
import importlib.util
import re

spec = importlib.util.spec_from_file_location("daily", "/home/raul/tuhoy/scripts/daily_edition.py")
daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daily)


def replace_photo_credit(body: str, caption: str) -> str:
    """Mantiene el crédito de la foto al final de la nota."""
    credit = caption.strip().rstrip(".") + "."
    paragraph = f"<p><em>{html.escape(credit)}</em></p>"
    pattern = re.compile(r"<p><em>\s*Foto:.*?</em></p>\s*", re.IGNORECASE | re.DOTALL)
    if pattern.search(body):
        return pattern.sub("", body).rstrip() + paragraph
    return body.rstrip() + paragraph


def sync_existing_credits(ghost) -> int:
    code, resp = ghost.get("/posts/?limit=all&formats=html")
    if code >= 300:
        daily.log(f"credit sync read fail {code} {resp}")
        return 0
    updated = 0
    for post in resp.get("posts") or []:
        caption = (post.get("feature_image_caption") or "").strip()
        body = post.get("html") or ""
        if not caption.lower().startswith("foto:") or not body:
            continue
        revised = replace_photo_credit(body, caption)
        if revised == body:
            continue
        payload = {"posts": [{"html": revised, "updated_at": post["updated_at"]}]}
        status, result = ghost.put_json(f"/posts/{post['id']}/?source=html", payload)
        if status < 300:
            updated += 1
        else:
            daily.log(f"credit sync fail {post.get('slug')} {status} {result}")
    daily.log(f"photo credits synchronized {updated}")
    return updated


def source_url(post: dict) -> str:
    src = post.get("canonical_url") or ""
    if src.startswith("http"):
        return src
    for link in re.findall(r'href="(https?://[^"]+)"', post.get("html") or ""):
        if "tuhoy.com" not in link and not link.lower().endswith(".pdf"):
            return link
    return ""


def fill_missing(ghost, dry_run: bool) -> int:
    """Pone portada a las notas publicadas que no tienen: foto de la fuente o, si no, de Commons."""
    flt = "feature_image:null%2Bstatus:published"
    code, resp = ghost.get(f"/posts/?limit=all&filter={flt}&formats=html&include=tags")
    if code >= 300:
        daily.log(f"sin foto: lectura fallida {code} {resp}")
        return 0
    n = 0
    for post in resp.get("posts") or []:
        src = source_url(post)
        slug_tag = daily.primary_slug([t["name"] for t in post.get("tags") or [] if not t["name"].startswith("#")])
        text = daily.strip_html(post.get("html") or "")
        url = cap = None
        for pick in (
            lambda: daily.source_photo(src) if src else None,
            lambda: daily.commons_image(*daily.story_image_queries(post["title"], text, slug_tag)),
        ):
            picked = pick()
            if not picked:
                continue
            blob, name, mime, cap = picked
            if dry_run:
                url = f"(prueba) {name}"
                break
            url = ghost.upload_image(blob, name, mime)
            if url:
                break
        if not url:
            daily.log(f"sin foto: no se encontró imagen para {post['slug']}")
            continue
        if dry_run:
            print(f"{post['slug']}: {url} · {cap}")
            n += 1
            continue
        payload = {
            "posts": [
                {
                    "feature_image": url,
                    "feature_image_alt": post["title"],
                    "feature_image_caption": cap,
                    "html": replace_photo_credit(post.get("html") or "", cap) if cap else post.get("html"),
                    "updated_at": post["updated_at"],
                }
            ]
        }
        c, r = ghost.put_json(f"/posts/{post['id']}/?source=html", payload)
        daily.log(f"sin foto: {post['slug']} -> {c} {cap} {url}")
        n += c < 300
    return n


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--credits-only",
        action="store_true",
        help="Sincroniza el crédito final sin volver a descargar imágenes.",
    )
    parser.add_argument("--sin-foto", action="store_true", help="Solo pone portada a las notas publicadas sin foto.")
    parser.add_argument("--dry-run", action="store_true", help="Con --sin-foto: muestra qué foto pondría.")
    args = parser.parse_args()
    env = daily.load_env()
    ghost = daily.Ghost(env["GHOST_URL"], env["GHOST_ADMIN_API_KEY"])
    if args.credits_only:
        sync_existing_credits(ghost)
        return 0
    if args.sin_foto:
        n = fill_missing(ghost, args.dry_run)
        daily.log(f"sin foto: {n} notas con portada nueva")
        return 0

    code, resp = ghost.get("/posts/?limit=50&formats=html")
    n = 0
    for post in resp.get("posts") or []:
        src = post.get("canonical_url") or ""
        if not src.startswith("http"):
            continue
        picked = daily.source_photo(src)
        if not picked:
            daily.log(f"no source photo {post.get('slug')}")
            continue
        blob, name, mime, cap = picked
        url = ghost.upload_image(blob, name, mime)
        if not url:
            daily.log(f"upload fail {post.get('slug')}")
            continue
        revised = replace_photo_credit(post.get("html") or "", cap)
        payload = {
            "posts": [
                {
                    "feature_image": url,
                    "feature_image_alt": f"{post.get('title')} — {cap}",
                    "feature_image_caption": cap,
                    "html": revised,
                    "updated_at": post["updated_at"],
                }
            ]
        }
        c, r = ghost.put_json(f"/posts/{post['id']}/?source=html", payload)
        daily.log(f"source photo {post.get('slug')} -> {c} {cap} {url}")
        n += 1
    daily.log(f"source photos updated {n}")
    return 0 if n else 1


if __name__ == "__main__":
    raise SystemExit(main())
