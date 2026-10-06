#!/usr/bin/env python3
"""Compara la redacción antigua (extractiva) con la nueva (modelo, dos pasadas) en 5 historias guardadas.

Uso:
  python3 scripts/eval_writer.py --build     # guarda 5 historias reales en data/eval_stories/
  python3 scripts/eval_writer.py             # compara y escribe data/eval_report.md
  python3 scripts/eval_writer.py --old-only  # solo métricas de la versión antigua
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_edition as daily  # noqa: E402
import writer  # noqa: E402

STORIES = daily.ROOT / "data" / "eval_stories"
REPORT = daily.ROOT / "data" / "eval_report.md"
COL = 62


def build(n: int = 5) -> None:
    STORIES.mkdir(parents=True, exist_ok=True)
    picked = []
    for force_inmig in (True, False):
        for item in daily.collect(force_inmig, 12):
            if len(picked) >= (3 if force_inmig else n):
                break
            url = daily.resolve_article_url(item["url"], item["title"])
            full = daily.extract_article(url, limit=9000)
            if len(full) < 1500:
                continue
            picked.append(
                {
                    "title": daily.headline_es(item["title"]),
                    "source": item.get("source") or "",
                    "url": daily.clean_source_url(url),
                    "desc": item.get("desc") or "",
                    "text": full,
                    "inmigracion": force_inmig,
                }
            )
    for i, story in enumerate(picked[:n], 1):
        (STORIES / f"{i:02d}.json").write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"guardada {i:02d}: {story['title'][:80]} ({len(story['text'].split())} palabras de fuente)")


def old_version(story: dict) -> dict:
    text = re.sub(r"\s+", " ", (story["desc"] + " " + story["text"][:1800])).strip()
    body_html = daily.write_html(story["title"], text, story["source"], story["url"])
    paras = [re.sub(r"<[^>]+>", "", p) for p in re.findall(r"<p>(.*?)</p>", body_html, re.S)]
    body = "\n\n".join(p for p in paras if not p.startswith("Fuente:"))
    return {"headline": story["title"], "deck": daily.excerpt_es(text, story["title"]), "body": body}


def new_version(story: dict) -> dict:
    name = story["source"] or re.sub(r"^www\.", "", re.sub(r"^https?://([^/]+).*", r"\1", story["url"]))
    sources = [{"name": name, "url": story["url"], "title": story["title"], "text": story["desc"] + " " + story["text"]}]
    return writer.write_article(sources, inmigracion=story["inmigracion"])


def side_by_side(left: str, right: str) -> str:
    def wrap(text: str) -> list[str]:
        lines = []
        for para in text.split("\n"):
            lines.extend(textwrap.wrap(para, COL) or [""])
        return lines

    a, b = wrap(left), wrap(right)
    rows = max(len(a), len(b))
    a += [""] * (rows - len(a))
    b += [""] * (rows - len(b))
    return "\n".join(f"{x:<{COL}} │ {y}" for x, y in zip(a, b))


def metric_line(label: str, m: dict) -> str:
    return (
        f"{label:<8} palabras={m['words']:<5} prohibidas={m['banned']:<3} frase_media={m['avg_sentence']:<5} "
        f"variación={m['sentence_stdev']:<5} párrafos={m['paragraphs']:<3} aperturas_repetidas={m['repeated_openings']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--old-only", action="store_true")
    args = parser.parse_args()

    if args.build:
        build()
        return 0

    files = sorted(STORIES.glob("*.json"))
    if not files:
        print("No hay historias guardadas. Ejecuta primero: python3 scripts/eval_writer.py --build")
        return 1
    run_new = not args.old_only and writer.enabled()
    if not args.old_only and not run_new:
        print("Sin clave de modelo en .env: solo se mide la versión antigua (añade LLM_PROVIDER y su clave, ver .env.example).\n")

    report = ["# Evaluación de redacción: antigua vs nueva\n"]
    totals = {"old": [], "new": []}
    for path in files:
        story = json.loads(path.read_text(encoding="utf-8"))
        old = old_version(story)
        m_old = writer.metrics(writer.plain_text(old))
        totals["old"].append(m_old)
        print("=" * (COL * 2 + 3))
        print(f"{path.stem} · {story['title'][:100]}")
        print(metric_line("ANTIGUA", m_old))
        report.append(f"## {path.stem} · {story['title']}\n\n- Antigua: {metric_line('', m_old).strip()}")

        new_text = "(sin clave de modelo)"
        if run_new:
            try:
                new = new_version(story)
                totals["new"].append(new["metrics"])
                print(metric_line("NUEVA", new["metrics"]))
                new_text = writer.plain_text(new)
                report.append(f"- Nueva: {metric_line('', new['metrics']).strip()}")
                report.append(f"- Cambios del editor: {'; '.join(new['changes'][:6])}")
                if new["unsupported"]:
                    report.append(f"- Sin sustento tras verificar: {new['unsupported']}")
                report.append(f"\n### Nueva\n\n**{new['headline']}**\n\n*{new['deck']}*\n\n{new['body']}\n")
            except Exception as e:
                new_text = f"(error: {e})"
                print(f"NUEVA    error: {e}")
        report.append(f"\n### Antigua\n\n**{old['headline']}**\n\n{old['body']}\n")
        print()
        print(side_by_side("ANTIGUA\n\n" + writer.plain_text(old), "NUEVA\n\n" + new_text))
        print()

    def avg(rows: list[dict], key: str) -> float:
        return round(sum(r[key] for r in rows) / len(rows), 1) if rows else 0.0

    print("=" * (COL * 2 + 3))
    for label, rows in (("ANTIGUA", totals["old"]), ("NUEVA", totals["new"])):
        if rows:
            print(
                f"{label:<8} media: palabras={avg(rows, 'words')} prohibidas={avg(rows, 'banned')} "
                f"frase_media={avg(rows, 'avg_sentence')} variación={avg(rows, 'sentence_stdev')}"
            )
    REPORT.write_text("\n".join(report), encoding="utf-8")
    print(f"\nInforme completo: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
