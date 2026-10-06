#!/usr/bin/env python3
"""Redacción de notas de TuHoy con un modelo de lenguaje: borrador, edición y verificación."""
from __future__ import annotations

import html
import json
import re
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("/home/raul/tuhoy")
PROMPTS = ROOT / "prompts"
REVIEW_QUEUE = ROOT / "data" / "review_queue.jsonl"

AI_LABEL = (
    "Nota redactada con asistencia de inteligencia artificial a partir de las fuentes citadas. "
    "¿Ves un error? Escríbenos y lo corregimos."
)

PROVIDERS = {
    "openai": {"base": "https://api.openai.com/v1", "model": "gpt-5.5", "key": "OPENAI_API_KEY"},
    "openrouter": {"base": "https://openrouter.ai/api/v1", "model": "openai/gpt-4.1", "key": "OPENROUTER_API_KEY"},
    "gemini": {
        "base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.5-pro",
        "key": "GEMINI_API_KEY",
    },
    "anthropic": {"base": "https://api.anthropic.com/v1", "model": "claude-sonnet-4-5", "key": "ANTHROPIC_API_KEY"},
}

BANNED = [
    r"en conclusi[oó]n", r"en resumen", r"para concluir",
    r"cabe (?:destacar|mencionar|se[nñ]alar|resaltar)",
    r"es importante (?:se[nñ]alar|destacar|mencionar|recordar)",
    r"en el (?:panorama|contexto) actual", r"en la actualidad",
    r"sin lugar a dudas?", r"sin duda alguna",
    r"juega un (?:papel|rol)", r"desempe[nñ]a un papel", r"papel (?:crucial|fundamental)",
    r"(?:es )?un testimonio de",
    r"en un mundo (?:cada vez m[aá]s|donde)",
    r"hoy en d[ií]a", r"en los [uú]ltimos tiempos",
    r"un hito", r"marca un antes y un despu[eé]s",
    r"navegar (?:el|la|los|las) (?:sistema|proceso|complejidad)",
    r"solo el tiempo dir[aá]", r"queda mucho por hacer", r"el futuro es incierto",
]
BANNED_RE = re.compile(r"\b(?:" + "|".join(BANNED) + r")\b", re.I)
SENT_SPLIT = re.compile(r"(?<=[\.\!\?…])\s+(?=[¿¡«\"“A-ZÁÉÍÓÚÑ0-9])")


class WriterError(RuntimeError):
    pass


def load_env() -> dict[str, str]:
    env = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def config(env: dict[str, str] | None = None) -> dict | None:
    """Devuelve la configuración del modelo o None si no hay clave."""
    env = env if env is not None else load_env()
    provider = (env.get("LLM_PROVIDER") or "").lower()
    if not provider:
        provider = next((p for p, c in PROVIDERS.items() if env.get(c["key"])), "")
    if provider not in PROVIDERS:
        return None
    spec = PROVIDERS[provider]
    key = env.get("LLM_API_KEY") or env.get(spec["key"])
    if not key:
        return None
    return {
        "provider": provider,
        "key": key,
        "model": env.get("LLM_MODEL") or spec["model"],
        "base": (env.get("LLM_BASE_URL") or spec["base"]).rstrip("/"),
        "factcheck": env.get("LLM_FACTCHECK", "1") != "0",
    }


def enabled() -> bool:
    return config() is not None


def _post(url: str, headers: dict, body: dict, timeout: int = 180) -> dict:
    data = json.dumps(body).encode()
    for attempt in range(3):
        req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:400]
            if e.code in (429, 500, 502, 503, 529) and attempt < 2:
                time.sleep(8 * (attempt + 1))
                continue
            raise WriterError(f"HTTP {e.code}: {detail}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 2:
                time.sleep(5)
                continue
            raise WriterError(str(e)) from e
    raise WriterError("sin respuesta")


def chat(cfg: dict, prompt: str, temperature: float, max_tokens: int = 4000, reasoning: str = "none") -> str:
    if cfg["provider"] == "anthropic":
        resp = _post(
            f"{cfg['base']}/messages",
            {"x-api-key": cfg["key"], "anthropic-version": "2023-06-01"},
            {
                "model": cfg["model"],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        return "".join(part.get("text", "") for part in resp.get("content") or [])
    body = {"model": cfg["model"], "messages": [{"role": "user", "content": prompt}]}
    if re.match(r"(?:openai/)?(?:gpt-5|o\d)", cfg["model"]):
        # Modelos de razonamiento: la temperatura solo se admite con el razonamiento apagado.
        body["max_completion_tokens"] = max_tokens if reasoning == "none" else max_tokens * 4
        body["reasoning_effort"] = reasoning
        if reasoning == "none":
            body["temperature"] = temperature
    else:
        body["max_tokens"] = max_tokens
        body["temperature"] = temperature
    resp = _post(f"{cfg['base']}/chat/completions", {"Authorization": f"Bearer {cfg['key']}"}, body)
    return resp["choices"][0]["message"]["content"] or ""


def parse_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise WriterError(f"respuesta sin JSON: {text[:200]}")
    return json.loads(text[start : end + 1])


# ---------- prompts ----------

def read_prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


def example_text(name: str) -> str:
    raw = (PROMPTS / "examples" / name).read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->", "", raw, flags=re.S).strip()


def pick_examples(source_text: str, inmigracion: bool) -> list[str]:
    """Dos ejemplos según el tipo de nota: impacto humano casi siempre, más noticia dura o explicativo."""
    explainer = re.search(r"\b(regla|requisit|tr[aá]mite|plazo|c[oó]mo (?:solicitar|pedir)|qu[eé] cambia|ley)\b", source_text, re.I)
    if inmigracion or explainer:
        return [example_text("02-impacto-humano.md"), example_text("03-explicativo.md")]
    return [example_text("01-noticia-dura.md"), example_text("02-impacto-humano.md")]


def fill(template: str, **values: str) -> str:
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template


def format_sources(sources: list[dict]) -> str:
    blocks = []
    for i, src in enumerate(sources, 1):
        blocks.append(
            f"## Fuente {i}: {src.get('name') or 'sin nombre'}\n"
            f"URL: {src.get('url') or ''}\n"
            f"Titular original: {src.get('title') or ''}\n\n"
            f"{src.get('text') or ''}"
        )
    return "\n\n".join(blocks)


# ---------- métricas ----------

def plain_text(article: dict) -> str:
    body = re.sub(r"^#+\s*", "", article.get("body") or "", flags=re.M)
    body = re.sub(r"^\s*-\s+", "", body, flags=re.M).replace("**", "")
    return "\n\n".join(x for x in (article.get("headline"), article.get("deck"), body) if x)


def sentences(text: str) -> list[str]:
    out = []
    for para in re.split(r"\n\s*\n", text):
        out.extend(s.strip() for s in SENT_SPLIT.split(para.strip()) if s.strip())
    return out


def metrics(text: str) -> dict:
    words = re.findall(r"\b[\wáéíóúüñÁÉÍÓÚÜÑ'-]+\b", text)
    sents = sentences(text)
    lengths = [len(re.findall(r"\b\w+\b", s)) for s in sents] or [0]
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    openings = [" ".join(s.split()[:2]).lower() for s in sents]
    repeated = sum(1 for o in set(openings) if openings.count(o) > 2)
    return {
        "words": len(words),
        "banned": len(BANNED_RE.findall(text)),
        "banned_found": sorted({m.group(0).lower() for m in BANNED_RE.finditer(text)}),
        "sentences": len(sents),
        "avg_sentence": round(sum(lengths) / len(lengths), 1),
        "sentence_stdev": round(statistics.pstdev(lengths), 1) if len(lengths) > 1 else 0.0,
        "paragraphs": len(paras),
        "repeated_openings": repeated,
    }


# ---------- HTML ----------

def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def md_to_html(body: str) -> str:
    out, bullets = [], []

    def flush() -> None:
        if bullets:
            out.append("<ul>" + "".join(f"<li>{inline(b)}</li>" for b in bullets) + "</ul>")
            bullets.clear()

    for block in re.split(r"\n\s*\n", body.strip()):
        lines = [l.rstrip() for l in block.strip().splitlines() if l.strip()]
        for line in lines:
            if re.match(r"^\s*[-*•]\s+", line):
                bullets.append(re.sub(r"^\s*[-*•]\s+", "", line))
                continue
            flush()
            heading = re.match(r"^#{1,4}\s+(.*)", line)
            if heading:
                out.append(f"<h2>{inline(heading.group(1).strip())}</h2>")
            else:
                out.append(f"<p>{inline(line.strip())}</p>")
        flush()
    return "\n".join(out)


def sources_html(sources: list[dict]) -> str:
    items = "".join(
        f'<li>{html.escape(s.get("name") or "Fuente")}: '
        f'<a href="{html.escape(s.get("url") or "")}">{html.escape(s.get("title") or "artículo original")}</a></li>'
        for s in sources
    )
    return f"<h2>Fuentes</h2>\n<ul>{items}</ul>\n<p><em>{html.escape(AI_LABEL)}</em></p>"


# ---------- pasadas ----------

def draft_pass(cfg: dict, sources: list[dict], inmigracion: bool) -> dict:
    src_text = format_sources(sources)
    prompt = fill(
        read_prompt("draft.md"),
        voice=read_prompt("voice.md"),
        examples="\n\n---\n\n".join(pick_examples(src_text, inmigracion)),
        sources=src_text,
        source_words=str(len(src_text.split())),
    )
    return parse_json(chat(cfg, prompt, temperature=0.8))


def edit_pass(cfg: dict, sources: list[dict], draft: dict, extra: str = "") -> dict:
    prompt = fill(
        read_prompt("edit.md"),
        voice=read_prompt("voice.md"),
        sources=format_sources(sources),
        draft=json.dumps({k: draft.get(k) for k in ("headline", "deck", "tier", "thin_sources", "body")}, ensure_ascii=False, indent=1),
    )
    if extra:
        prompt += "\n\n# Correcciones obligatorias\n\n" + extra
    return parse_json(chat(cfg, prompt, temperature=0.4))


def factcheck_pass(cfg: dict, sources: list[dict], article: dict) -> list[dict]:
    prompt = fill(
        read_prompt("factcheck.md"),
        sources=format_sources(sources),
        article=json.dumps({k: article.get(k) for k in ("headline", "deck", "body")}, ensure_ascii=False, indent=1),
    )
    result = parse_json(chat(cfg, prompt, temperature=0.0, max_tokens=2000, reasoning="medium"))
    return [c for c in result.get("unsupported") or [] if c.get("claim")]


def drop_claims(article: dict, claims: list[dict]) -> dict:
    """Último recurso: quita las frases que el verificador no pudo sustentar."""
    body = article.get("body") or ""
    for claim in claims:
        text = claim["claim"].strip().strip('"“”')
        if len(text) < 12:
            continue
        for sent in sentences(body):
            if text in sent or (len(text) > 40 and text[:40] in sent):
                body = body.replace(sent, "").replace("\n\n\n", "\n\n")
    article["body"] = re.sub(r"\n{3,}", "\n\n", body).strip()
    return article


def validate(article: dict) -> None:
    for key in ("headline", "deck", "body"):
        if not (article.get(key) or "").strip():
            raise WriterError(f"falta {key}")
    if len(article["body"].split()) < 150:
        raise WriterError("cuerpo demasiado corto")


def write_article(sources: list[dict], inmigracion: bool = False, cfg: dict | None = None, log=print) -> dict:
    """Devuelve headline, deck, html, body, tier, thin_sources, changes, unsupported, flagged, metrics."""
    cfg = cfg or config()
    if not cfg:
        raise WriterError("sin clave de modelo configurada")

    draft = draft_pass(cfg, sources, inmigracion)
    validate(draft)
    final = edit_pass(cfg, sources, draft)
    validate(final)

    m = metrics(plain_text(final))
    if m["banned"]:
        final = edit_pass(cfg, sources, final, "Elimina estas frases prohibidas: " + ", ".join(m["banned_found"]))
        validate(final)

    unsupported: list[dict] = []
    if cfg["factcheck"]:
        unsupported = factcheck_pass(cfg, sources, final)
        if unsupported:
            listed = "\n".join(f"- \"{c['claim']}\": {c.get('why', '')}" for c in unsupported)
            final = edit_pass(
                cfg,
                sources,
                final,
                "El verificador marcó estas afirmaciones como NO sustentadas por las fuentes. "
                "Bórralas o atenúalas; no inventes nada para reemplazarlas:\n" + listed,
            )
            validate(final)
            unsupported = factcheck_pass(cfg, sources, final)
            if unsupported:
                final = drop_claims(final, unsupported)

    headline = re.sub(r"\s+", " ", final["headline"]).strip()
    if len(headline) > 90:
        headline = headline[:89].rsplit(" ", 1)[0] + "…"
    flagged = bool(unsupported) or bool(final.get("thin_sources"))
    article = {
        "headline": headline,
        "deck": re.sub(r"\s+", " ", final["deck"]).strip(),
        "body": final["body"].strip(),
        "tier": final.get("tier") or "",
        "thin_sources": bool(final.get("thin_sources")),
        "changes": final.get("changes") or [],
        "unsupported": unsupported,
        "flagged": flagged,
        "draft": draft,
    }
    article["html"] = md_to_html(article["body"]) + "\n" + sources_html(sources)
    article["metrics"] = metrics(plain_text(article))
    log(
        f"writer {cfg['provider']}:{cfg['model']} tier={article['tier']} words={article['metrics']['words']} "
        f"banned={article['metrics']['banned']} unsupported={len(unsupported)} thin={article['thin_sources']}"
    )
    return article


def queue_for_review(article: dict, url: str, reason: str) -> None:
    REVIEW_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "url": url,
        "headline": article.get("headline"),
        "reason": reason,
        "unsupported": article.get("unsupported"),
        "changes": article.get("changes"),
    }
    with REVIEW_QUEUE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
