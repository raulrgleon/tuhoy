#!/usr/bin/env python3
"""Reescribe con writer.py las notas ya publicadas, a partir de sus fuentes originales.

Conserva slug (URL), fecha, imagen y crédito. Guarda copia de seguridad antes de tocar nada.

  python3 scripts/rewrite_published.py --limit 1          # prueba con una nota
  python3 scripts/rewrite_published.py --slug mi-nota     # una nota concreta
  python3 scripts/rewrite_published.py                    # todas las pendientes
  python3 scripts/rewrite_published.py --restore data/backup-posts-XXXX.json
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_edition as daily  # noqa: E402
import writer  # noqa: E402

SKIP_HOSTS = ("tuhoy.com", "wikimedia.org", "wikipedia.org", "creativecommons.org")
MIN_SOURCE_CHARS = 1200


def source_links(post_html: str) -> list[str]:
    urls = []
    for href in re.findall(r'href="([^"]+)"', post_html or ""):
        href = html.unescape(href)
        if href.startswith("http") and not any(h in href for h in SKIP_HOSTS) and href not in urls:
            urls.append(href)
    return urls[:2]


def original_title(url: str) -> str:
    try:
        raw = daily.http_get(url, timeout=18).decode("utf-8", "replace")
    except Exception:
        return "artículo original"
    return daily.page_title(raw) or "artículo original"


def build_sources(post: dict) -> list[dict]:
    sources = []
    for url in source_links(post.get("html") or ""):
        text = daily.extract_article(url, limit=9000)
        if len(text) < MIN_SOURCE_CHARS:
            continue
        raw_name = re.sub(r"^https?://(?:www\.)?([^/]+).*", r"\1", url)
        sources.append({"name": raw_name, "url": daily.clean_source_url(url), "title": original_title(url), "text": text})
    return sources


def is_inmig(post: dict) -> bool:
    return any(t["slug"] in ("inmigracion", "latinos") for t in post.get("tags") or [])


def rewrite(ghost, post: dict) -> str:
    sources = build_sources(post)
    if not sources:
        return f"skip sin fuente legible: {post['slug']}"
    art = writer.write_article(sources, inmigracion=is_inmig(post), log=daily.log)

    body = art["html"]
    if post.get("feature_image_caption"):
        body += f"\n<p><em>{html.escape(re.sub(r'<[^>]+>', '', post['feature_image_caption']))}</em></p>"

    internal = {daily.AUTO_TAG, daily.IA_TAG, daily.REVIEW_TAG}
    tags = [{"name": t["name"]} for t in post.get("tags") or [] if t["name"] not in internal]
    tags.append({"name": daily.IA_TAG})
    if art["flagged"]:
        tags.append({"name": daily.REVIEW_TAG})
        writer.queue_for_review(art, sources[0]["url"], "fuentes escasas" if art["thin_sources"] else "afirmaciones sin sustento")

    payload = {
        "posts": [
            {
                "title": art["headline"],
                "html": body,
                "custom_excerpt": daily.smart_cut(art["deck"], 300),
                "meta_title": daily.seo_meta_title(art["headline"]),
                "meta_description": daily.smart_cut(art["deck"], 155),
                "feature_image_alt": art["headline"],
                "tags": tags,
                "updated_at": post["updated_at"],
            }
        ]
    }
    status, resp = ghost.put_json(f"/posts/{post['id']}/?source=html", payload)
    if status >= 300:
        return f"FAIL {post['slug']} {status} {str(resp)[:200]}"
    m = art["metrics"]
    flag = " [#revisar]" if art["flagged"] else ""
    return f"ok {post['slug'][:60]} :: {art['headline']} ({m['words']} palabras, {art['tier']}){flag}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--slug", default="")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--restore", default="")
    args = parser.parse_args()

    env = daily.load_env()
    ghost = daily.Ghost(env["GHOST_URL"], env["GHOST_ADMIN_API_KEY"])

    if args.restore:
        saved = json.loads(Path(args.restore).read_text(encoding="utf-8"))
        for old in saved:
            code, cur = ghost.get(f"/posts/{old['id']}/")
            fields = {k: old.get(k) for k in ("title", "html", "custom_excerpt", "meta_title", "meta_description", "feature_image_alt")}
            fields["tags"] = [{"name": t["name"]} for t in old.get("tags") or []]
            fields["updated_at"] = cur["posts"][0]["updated_at"]
            status, _ = ghost.put_json(f"/posts/{old['id']}/?source=html", {"posts": [fields]})
            print("restore", old["slug"], status)
        return 0

    if not writer.enabled():
        print("Sin clave de modelo en .env")
        return 1

    code, resp = ghost.get("/posts/?limit=all&formats=html&include=tags&filter=status:published")
    posts = [p for p in resp.get("posts") or [] if not any(t["name"] == daily.IA_TAG for t in p.get("tags") or [])]
    # Boletines multitema (una URL para varias notas): solo la nota que coincide con el tema principal.
    by_source: dict[str, list[dict]] = {}
    for p in posts:
        links = source_links(p.get("html") or "")
        if links:
            by_source.setdefault(links[0], []).append(p)
    multi = set()
    for url, group in by_source.items():
        if len(group) < 2:
            continue
        path_words = set(re.findall(r"[a-z0-9]{3,}", url.lower().split("/", 3)[-1])) - {"com", "www", "html"}

        def overlap(p: dict) -> int:
            return len(path_words & set(re.findall(r"[a-z0-9]{3,}", p["slug"])))

        best = max(group, key=overlap)
        multi.update(p["id"] for p in group if p is not best or overlap(p) == 0)
    for p in posts:
        if p["id"] in multi:
            print(f"skip fuente multitema: {p['slug']}")
    posts = [p for p in posts if p["id"] not in multi]

    if args.slug:
        posts = [p for p in posts if p["slug"] == args.slug]
    if args.limit:
        posts = posts[: args.limit]
    if not posts:
        print("Nada que reescribir")
        return 0

    backup = daily.ROOT / "data" / f"backup-posts-{int(time.time())}.json"
    backup.write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"copia de seguridad: {backup} ({len(posts)} notas)")

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(rewrite, ghost, p): p for p in posts}
        for fut in as_completed(futures):
            try:
                line = fut.result()
            except Exception as e:
                line = f"ERROR {futures[fut]['slug']}: {e}"
            results.append(line)
            print(line, flush=True)
    ok = sum(1 for r in results if r.startswith("ok"))
    print(f"\nreescritas {ok} de {len(posts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
