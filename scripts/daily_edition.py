#!/usr/bin/env python3
"""Edición diaria de TuHoy: fuentes reales -> artículos originales en español -> Ghost.

Corre solo tres veces al día (cron 06:00, 12:00 y 18:00 America/Chicago, ~5 notas cada vez). Con clave de modelo (ver writer.py) redacta
notas originales en dos pasadas; sin clave, cae al resumen extractivo. No inventa noticias: si no hay texto
útil en la fuente, descarta la pieza. Deduplica por URL y por título.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import os
import random
import re
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import writer  # noqa: E402

ROOT = Path("/home/raul/tuhoy")
ENV_PATH = ROOT / ".env"
STATE_PATH = ROOT / "data" / "edition_state.json"
LOG_DIR = ROOT / "logs"
UA = "TuHoyBot/1.0 (+https://tuhoy.com; noticias diarias)"
BROWSER = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
CTX = ssl.create_default_context()

# Fuentes: RSS o sitemaps de Google News (las URL con "sitemap"). collect() las intercala.
# Google News cifra sus enlaces y no deja llegar al artículo: solo fuentes con URL directa.
# EFE y AP bloquean la lectura automática (403) y Voz de América no publica desde marzo de 2025.
SITEMAP_CNN = "https://cnnespanol.cnn.com/sitemap/news.xml"
SITEMAP_UNIVISION = "https://www.univision.com/feed-sitemap/google-news/noticias"
SITEMAP_TELEMUNDO = "https://www.telemundo.com/sitemap/telemundo/sitemap-news"
FEEDS_GENERAL = [
    "https://feeds.bbci.co.uk/mundo/rss.xml",
    "https://www.france24.com/es/rss",
    SITEMAP_CNN,
    SITEMAP_UNIVISION,
    SITEMAP_TELEMUNDO,
]
FEEDS_INMIGRACION = [
    "https://www.laopinion.com/categoria/inmigracion/feed/",
    "https://www.eldiariony.com/categoria/inmigracion/feed/",
    SITEMAP_UNIVISION,
    SITEMAP_TELEMUNDO,
    SITEMAP_CNN,
]
# Una ranura por edición para las secciones /venezuela/ y /cuba/.
FEEDS_PAISES = {
    "https://elpitazo.net/feed/": "Venezuela",
    "https://talcualdigital.com/feed/": "Venezuela",
    "https://www.elnacional.com/feed/": "Venezuela",
    "https://www.14ymedio.com/rss/": "Cuba",
    "https://www.cibercuba.com/rss.xml": "Cuba",
}
# Vídeos, directos, espectáculos y deportes no dan nota escrita útil.
SKIP_URL = re.compile(
    r"/(video|videos|shorts|live-news|famosos|horoscopos|shows|trending|deportes|entretenimiento|gallery)/",
    re.I,
)
MAX_AGE_HOURS = 48
COUNTRY_TAGS = [
    ("Venezuela", re.compile(r"\b(venezuela|venezolan[oa]s?|maduro|caracas|chavismo|chavista)\b", re.I)),
    ("Cuba", re.compile(r"\b(cuba|cuban[oa]s?|la habana|díaz-canel|diaz-canel)\b", re.I)),
]
DRY_RUN = False

# Páginas que suelen dar texto completo (la edición las reescribe; no se copian).
PAGINAS_INMIGRACION = [
    "https://www.courthousenews.com/judge-issues-final-ruling-against-ice-immigration-court-arrest-policy-in-manhattan/",
    "https://www.lanacion.com.ar/estados-unidos/florida/es-oficial-se-confirma-la-cifra-de-inmigrantes-que-podrian-ser-excluidos-de-medicaid-en-florida-nid04102026/",
    "https://www.nbcnews.com/news/us-news/judge-keeps-immigrant-delivery-driver-shot-ice-custody-alleged-assault-rcna600898",
    "https://www.nbcnews.com/politics/2026-election/shooting-death-houston-father-igniting-latino-politics-texas-rcna598588",
    "https://www.sltrib.com/news/2026/10/04/moroni-ice-enforcement-5-people/",
]

SKIP_TITLE = re.compile(
    r"(barajas cartas|spa, el antiguo|ana mendieta|christa pike|"
    r"vuelo de dubái|vuelo de dubai|copiloto del vuelo)",
    re.I,
)
INMIG_RE = re.compile(
    r"\b(inmigraci[oó]n|inmigrantes?|migrantes?|migraci[oó]n|\bice\b|dhs\b|"
    r"asilo|deportaci[oó]n|deportados?|\blatinos?\b|\blatinas?\b|hispan[oa]s?|"
    r"frontera|green card|medicaid|\bcbp\b|indocumentad)",
    re.I,
)
TAG_RULES = [
    ("salud", re.compile(r"\b(salud|médic|medic|hospital|vacun|glp|epidemia|virus)\b", re.I)),
    ("tecnologia", re.compile(r"\b(tecnolog|inteligencia artificial|\bia\b|algoritmo|openai|chip|ciber)\b", re.I)),
    ("economia", re.compile(r"\b(econom|mercado|inflaci|arancel|banco|bono|empleo|piketty|comercio)\b", re.I)),
    ("politica", re.compile(r"\b(eleccion|elección|congreso|senado|corte|juez|partido|lula|trump|bolsonaro|votante)\b", re.I)),
    ("mundo", re.compile(r".", re.I)),
]

IMG_FALLBACK = {
    "inmigracion": ["United States Mexico border fence Nogales", "CBP border patrol vehicle"],
    "politica": ["United States Capitol west facade", "voting booth United States"],
    "mundo": ["United Nations headquarters New York", "world leaders summit"],
    "economia": ["New York Stock Exchange facade", "container port cargo"],
    "tecnologia": ["data center server racks", "silicon wafer semiconductor"],
    "salud": ["hospital emergency entrance United States", "pharmacy shelves medicine"],
}

# Personas, lugares e instituciones -> búsqueda concreta en Commons.
IMG_HINTS = [
    (re.compile(r"\bpiketty\b", re.I), "Thomas Piketty"),
    (re.compile(r"\blula\b", re.I), "Foto oficial de Luiz Inácio Lula da Silva"),
    (re.compile(r"fl[aá]vio bolsonaro", re.I), "Senador Flávio Bolsonaro"),
    (re.compile(r"\bbolsonaro\b", re.I), "Jair Bolsonaro"),
    (re.compile(r"\bcornell\b", re.I), "Cornell University McGraw Tower"),
    (re.compile(r"\baustin\b", re.I), "Downtown Austin Texas skyline"),
    (re.compile(r"\bhouston\b", re.I), "Downtown Houston Texas skyline"),
    (re.compile(r"\bmoroni\b|\bsanpete\b", re.I), "Moroni Utah main street"),
    (re.compile(r"\bflorida\b.*medicaid|medicaid.*\bflorida\b", re.I), "Florida State Capitol Tallahassee"),
    (re.compile(r"manhattan|federal plaza|javits", re.I), "Jacob Javits Federal Building"),
    (re.compile(r"\bcanad[aá]\b", re.I), "Peace Arch United States Canada border"),
    (re.compile(r"\bvenezuela\b", re.I), "Palacio Federal Legislativo Caracas"),
    (re.compile(r"corte suprema|supreme court", re.I), "Supreme Court of the United States"),
    (re.compile(r"casa blanca|white house", re.I), "White House north facade"),
    (re.compile(r"\bice\b|inmigraci", re.I), "United States Mexico border fence"),
]


def log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}"
    print(line, flush=True)
    with (LOG_DIR / "daily.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def load_env() -> dict[str, str]:
    env = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"seen_urls": [], "seen_titles": [], "runs": []}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def ghost_jwt(key: str) -> str:
    kid, secret = key.split(":")
    now = int(time.time())
    h = b64url(json.dumps({"alg": "HS256", "typ": "JWT", "kid": kid}, separators=(",", ":")).encode())
    p = b64url(json.dumps({"iat": now, "exp": now + 300, "aud": "/admin/"}, separators=(",", ":")).encode())
    s = f"{h}.{p}"
    sig = hmac.new(bytes.fromhex(secret), s.encode(), hashlib.sha256).digest()
    return s + "." + b64url(sig)


class Ghost:
    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/ghost/api/admin"
        self.key = key

    def _req(self, method: str, path: str, data: bytes | None = None, content_type: str | None = "application/json"):
        headers = {
            "Authorization": f"Ghost {ghost_jwt(self.key)}",
            "Accept": "application/json",
            "User-Agent": BROWSER,
            "Origin": "https://tuhoy.com",
        }
        if data is not None and content_type:
            headers["Content-Type"] = content_type
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60, context=CTX) as resp:
                raw = resp.read().decode("utf-8", "replace")
                return resp.status, json.loads(raw or "{}")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"raw": raw[:800]}
            return e.code, parsed

    def get(self, path: str):
        return self._req("GET", path)

    def post_json(self, path: str, body: dict):
        return self._req("POST", path, json.dumps(body).encode(), "application/json")

    def put_json(self, path: str, body: dict):
        return self._req("PUT", path, json.dumps(body).encode(), "application/json")

    def upload_image(self, blob: bytes, filename: str, mime: str) -> str | None:
        boundary = "----TuhoyImg" + hashlib.md5(str(time.time()).encode()).hexdigest()
        head = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode()
        tail = f"\r\n--{boundary}--\r\n".encode()
        code, resp = self._req(
            "POST",
            "/images/upload/",
            head + blob + tail,
            f"multipart/form-data; boundary={boundary}",
        )
        if code >= 300:
            log(f"image upload fail {code} {resp}")
            return None
        images = resp.get("images") or []
        return images[0].get("url") if images else None


def http_get(url: str, timeout: int = 20, referer: str | None = None) -> bytes:
    headers = {"User-Agent": BROWSER, "Accept": "*/*"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
        return resp.read()


def meta_content(raw: str, *names: str) -> str:
    for name in names:
        for pat in (
            rf'<meta[^>]+(?:property|name)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{re.escape(name)}["\']',
        ):
            m = re.search(pat, raw, re.I)
            if m:
                return html.unescape(m.group(1)).strip()
    return ""


def source_name(url: str, raw: str = "", fallback: str = "") -> str:
    site = meta_content(raw, "og:site_name") if raw else ""
    if site:
        return site
    host = urllib.parse.urlparse(url).netloc.replace("www.", "")
    known = {
        "nbcnews.com": "NBC News",
        "sltrib.com": "The Salt Lake Tribune",
        "lanacion.com.ar": "LA NACIÓN",
        "courthousenews.com": "Courthouse News Service",
        "bbc.com": "BBC News Mundo",
        "bbc.co.uk": "BBC News Mundo",
        "elpais.com": "EL PAÍS",
        "france24.com": "France 24",
        "apnews.com": "Associated Press",
    }
    for key, label in known.items():
        if host.endswith(key):
            return label
    return fallback or host


def source_photo(article_url: str, raw: str | None = None) -> tuple[bytes, str, str, str] | None:
    """Foto de la nota original, con crédito al diario."""
    if raw is None:
        try:
            raw = http_get(article_url, timeout=20).decode("utf-8", "replace")
        except Exception as e:
            log(f"source page fail {article_url}: {e}")
            return None
    img = meta_content(raw, "og:image:secure_url", "og:image", "twitter:image", "twitter:image:src")
    if not img:
        m = re.search(r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)', raw, re.I)
        img = html.unescape(m.group(1)) if m else ""
    if not img:
        return None
    img = urllib.parse.urljoin(article_url, img)
    if img.startswith("//"):
        img = "https:" + img
    credit = source_name(article_url, raw)
    try:
        blob = http_get(img, timeout=30, referer=article_url)
    except Exception as e:
        log(f"source photo fail {img}: {e}")
        return None
    if len(blob) < 8000:
        return None
    if blob[:3] == b"\xff\xd8":
        mime, ext = "image/jpeg", "jpg"
    elif blob[:8] == b"\x89PNG\r\n\x1a\n":
        mime, ext = "image/png", "png"
    elif blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        mime, ext = "image/webp", "webp"
    else:
        # Ghost acepta jpeg/png; si viene html/error, abortar.
        if blob[:1] in (b"<", b"{") or blob[:15].lower().startswith(b"<!doctype"):
            return None
        mime, ext = "image/jpeg", "jpg"
    cap = f"Foto: {credit}."
    host = urllib.parse.urlparse(article_url).netloc.replace("www.", "").split(".")[0]
    return blob, f"{host}-fuente.{ext}", mime, cap


def strip_html(raw: str) -> str:
    raw = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw)
    raw = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", raw)
    raw = re.sub(r"(?is)<noscript[^>]*>.*?</noscript>", " ", raw)
    parts = re.findall(r"(?is)<p[^>]*>(.*?)</p>", raw)
    text = " ".join(parts) if parts else re.sub(r"(?is)<[^>]+>", " ", raw)
    text = html.unescape(re.sub(r"(?is)<[^>]+>", " ", text))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_rss(url: str) -> list[dict]:
    items = []
    try:
        raw = http_get(url)
    except Exception as e:
        log(f"rss fail {url} {e}")
        return items
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        log(f"rss xml fail {url} {e}")
        return items
    ns = {"atom": "http://www.w3.org/2005/Atom", "dc": "http://purl.org/dc/elements/1.1/"}
    nodes = root.findall(".//item")
    if not nodes:
        nodes = root.findall(".//atom:entry", ns)
    for node in nodes:
        title = (node.findtext("title") or node.findtext("atom:title", default="", namespaces=ns) or "").strip()
        link = (node.findtext("link") or "").strip()
        if not link:
            el = node.find("atom:link", ns)
            if el is not None:
                link = el.get("href") or ""
        desc = node.findtext("description") or node.findtext("atom:summary", default="", namespaces=ns) or ""
        desc = strip_html(desc)
        pub = node.findtext("pubDate") or node.findtext("atom:updated", default="", namespaces=ns) or ""
        source = ""
        if " - " in title:
            title, source = title.rsplit(" - ", 1)
        items.append({"title": title.strip(), "url": link.strip(), "desc": desc, "pub": pub, "source": source.strip()})
    return items


def parse_news_sitemap(url: str) -> list[dict]:
    """Sitemap de Google News: <loc>, <news:title> y <news:publication_date> por noticia."""
    try:
        raw = http_get(url).decode("utf-8", "replace")
    except Exception as e:
        log(f"sitemap fail {url} {e}")
        return []
    source = urllib.parse.urlparse(url).netloc.replace("www.", "")
    items = []
    for block in re.findall(r"<url>(.*?)</url>", raw, re.S):
        def field(tag: str) -> str:
            m = re.search(rf"<{tag}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag}>", block, re.S)
            return html.unescape(m.group(1).strip()) if m else ""

        title, link = field("news:title"), field("loc")
        if title and link:
            items.append({"title": title, "url": link, "desc": "", "pub": field("news:publication_date"), "source": source})
    return items


def item_age_hours(item: dict) -> float | None:
    pub = (item.get("pub") or "").strip()
    if not pub:
        return None
    try:
        when = parsedate_to_datetime(pub)
    except (TypeError, ValueError):
        try:
            when = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        except ValueError:
            return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - when).total_seconds() / 3600


def source_items(url: str) -> list[dict]:
    """Noticias recientes de una fuente, sin vídeos/directos ni piezas de más de MAX_AGE_HOURS."""
    items = parse_news_sitemap(url) if "sitemap" in url else parse_rss(url)
    out = []
    for item in items:
        if SKIP_URL.search(item["url"]):
            continue
        age = item_age_hours(item)
        if age is not None and age > MAX_AGE_HOURS:
            continue
        out.append(item)
    return out


def gdelt_url(title: str) -> str:
    words = " ".join(re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÜüÑñ0-9]{3,}", title)[:8])
    if not words:
        return ""
    qs = urllib.parse.urlencode(
        {
            "query": words,
            "mode": "ArtList",
            "maxrecords": 8,
            "timespan": "7d",
            "format": "json",
            "sort": "DateDesc",
        }
    )
    try:
        time.sleep(1.2)
        data = json.loads(http_get("https://api.gdeltproject.org/api/v2/doc/doc?" + qs, timeout=20))
    except Exception:
        return ""
    for art in data.get("articles") or []:
        u = art.get("url") or ""
        if u.startswith("http") and "news.google.com" not in u:
            return u
    return ""


def resolve_article_url(url: str, title: str = "") -> str:
    if "news.google.com" not in url:
        return url
    found = gdelt_url(title)
    if found:
        return found
    try:
        raw = http_get(url, timeout=15).decode("utf-8", "replace")
    except Exception:
        return url
    for pat in (
        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)',
        r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)',
        r'"canonicalUrl":"([^"]+)"',
    ):
        m = re.search(pat, raw, re.I)
        if m:
            dest = html.unescape(m.group(1))
            if dest.startswith("http") and "news.google.com" not in dest:
                return dest
    return url


def page_title(raw: str) -> str:
    for pat in (
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']',
        r"<title>([^<]+)</title>",
    ):
        m = re.search(pat, raw, re.I)
        if m:
            t = html.unescape(m.group(1)).split(" | ")[0].split(" - ")[0].strip()
            if 20 < len(t) < 160:
                return t
    return ""


NAV_JUNK_RE = re.compile(
    r"(ir al contenido|noticias video secciones|hay festival|aceptar cookie|"
    r"subscribe to|sign in|newsletter|copyright ©|bbc news,\s*mundo|"
    r"cuenta américa|síguenos|compartir esta|related stories)",
    re.I,
)


def looks_like_nav(sent: str) -> bool:
    if NAV_JUNK_RE.search(sent):
        return True
    words = sent.split()
    if len(words) >= 8:
        titled = sum(1 for w in words if w[:1].isupper())
        if titled / len(words) >= 0.72:
            return True
    return False


AUTO_TAG = "#resumen-automatico"
IA_TAG = "#ia-asistida"
REVIEW_TAG = "#revisar"
SENTENCE_RE = re.compile(r"(?<=[\.\!\?»\"”])\s+(?=[¿¡«\"“A-ZÁÉÍÓÚÑ])")


def smart_cut(text: str, limit: int) -> str:
    """Recorta sin dejar frases truncadas que parezcan completas."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    for sep in ("; ", ", ", " — ", ": "):
        idx = cut.rfind(sep)
        if idx >= limit * 0.75:
            return cut[:idx].rstrip() + "…"
    return cut.rsplit(" ", 1)[0].rstrip(",;:") + "…"


ABBREV_END_RE = re.compile(r"(?:\b[A-ZÁÉÍÓÚÑ]|\bEE\.UU|\bUU|\bSr|\bSra|\bDr|\bDra|\bSt|\bJr|\bvs|\bNo)\.$")


def first_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    parts = SENTENCE_RE.split(text)
    sentence = parts[0]
    for part in parts[1:]:
        if not ABBREV_END_RE.search(sentence):
            break
        sentence = f"{sentence} {part}"
    return sentence


def seo_slug(title: str, limit: int = 70) -> str:
    import unicodedata

    base = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    if len(base) <= limit:
        return base
    return base[:limit].rsplit("-", 1)[0]


def seo_meta_title(title: str) -> str | None:
    if len(title) <= 65:
        return None
    short = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()
    return short if len(short) <= 65 else None


def clean_source_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    drop = {
        "at_medium",
        "at_campaign",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        "ocid",
    }
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=False) if k.lower() not in drop]
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(query), ""))


BYLINE_RE = re.compile(
    r"^(?:Crédito:[^|]{2,60}\|\s*\S+\s+)?Por\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3}\s+(?=[A-ZÁÉÍÓÚÑ¿¡«“\"])"
)


def extract_article(url: str, limit: int = 1800) -> str:
    try:
        raw = http_get(url, timeout=18).decode("utf-8", "replace")
    except Exception as e:
        log(f"extract fail {url} {e}")
        return ""
    raw = re.sub(r"<figcaption.*?</figcaption>", " ", raw, flags=re.S | re.I)
    text = strip_html(raw)
    # drop leftover menus / cookies
    cut = []
    for sent in re.split(r"(?<=[\.\!\?])\s+", text):
        sent = BYLINE_RE.sub("", sent)
        if len(sent) < 50:
            continue
        if looks_like_nav(sent):
            continue
        if re.search(r"(cookie|suscríb|newsletter|aceptar|copyright ©)", sent, re.I):
            continue
        cut.append(sent.strip())
        if sum(len(x) for x in cut) > limit:
            break
    return " ".join(cut)


def trim_to_headline(text: str, *titles: str) -> str:
    """Quita el menú que algunas páginas (Univision, Telemundo) dejan antes del titular."""
    for title in titles:
        head = re.sub(r"\s+", " ", title or "").strip()[:40]
        if len(head) < 20:
            continue
        pos = text.find(head)
        if 0 < pos < 1500:
            return text[pos:]
    return text


def norm_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"[^\w\sáéíóúüñ]", " ", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip()


def tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-záéíóúüñ]{4,}", text.lower())}


def similar(a: str, b: str) -> bool:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return False
    if len(ta & tb) / len(ta | tb) >= 0.55:
        return True
    # Misma noticia con otro verbo: "convoca" / "decidió convocar".
    sa, sb = {w[:6] for w in ta}, {w[:6] for w in tb}
    shared = len(sa & sb)
    return shared >= 4 and shared / min(len(sa), len(sb)) >= 0.5


def classify(title: str, text: str, force_inmig: bool) -> list[str]:
    # Las páginas de medios contienen menús y recomendaciones no relacionados.
    # Clasificar con el titular y solo el inicio evita etiquetas falsas.
    blob = f"{title} {text[:500]}"
    tags = []
    if force_inmig or INMIG_RE.search(blob):
        tags.extend(["Inmigración", "Latinos"])
    for slug, rx in TAG_RULES:
        if rx.search(blob):
            names = {
                "salud": "Salud",
                "tecnologia": "Tecnología",
                "economia": "Economía",
                "politica": "Política",
                "mundo": "Mundo",
            }
            tags.append(names[slug])
            break
    if "Inmigración" in tags and "Mundo" in tags and "Política" not in tags:
        tags = [t for t in tags if t != "Mundo"] + ["Política"]
    return tags


def primary_slug(tags: list[str]) -> str:
    order = ["Inmigración", "Política", "Mundo", "Economía", "Tecnología", "Salud"]
    for name in order:
        if name in tags:
            return {
                "Inmigración": "inmigracion",
                "Política": "politica",
                "Mundo": "mundo",
                "Economía": "economia",
                "Tecnología": "tecnologia",
                "Salud": "salud",
            }[name]
    return "mundo"


def headline_es(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip(" .")
    title = title.replace("EEUU", "EE.UU.").replace("EE. UU.", "EE.UU.")
    if title and title[0].islower():
        title = title[0].upper() + title[1:]
    if len(title) <= 140:
        return title
    return title[:137].rsplit(" ", 1)[0] + "…"


def excerpt_es(text: str, title: str) -> str:
    sents = [
        s.strip()
        for s in re.split(r"(?<=[\.\!\?])\s+", text)
        if len(s.strip()) > 40 and not looks_like_nav(s)
    ]
    if sents:
        return smart_cut(sents[0], 300)
    return title


def write_html(title: str, text: str, source: str, url: str) -> str:
    article_url = clean_source_url(url)
    sents = [
        s.strip()
        for s in re.split(r"(?<=[\.\!\?])\s+", text)
        if 40 <= len(s.strip()) <= 280 and not looks_like_nav(s) and not s.strip()[:1].islower()
    ]
    seen = []
    for s in sents:
        if any(similar(s, prev) for prev in seen):
            continue
        seen.append(s)
        if len(seen) >= 5:
            break
    if len(seen) < 2:
        raise ValueError("poco texto útil")

    lead = seen[0]
    mid = " ".join(seen[1:3])
    extra = seen[3] if len(seen) > 3 else ""
    src = source or urllib.parse.urlparse(url).netloc.replace("www.", "")
    contexto = f'<p>Fuente: {html.escape(src)} — <a href="{html.escape(article_url)}">artículo original</a></p>'
    parts = [f"<p>{html.escape(lead)}</p>", f"<p>{html.escape(mid)}</p>"]
    if extra:
        parts.append(f"<p>{html.escape(extra)}</p>")
    parts.append(contexto)
    return "\n".join(parts)


def story_image_queries(title: str, text: str = "", slug_tag: str = "mundo") -> list[str]:
    blob = f"{title} {text}"
    queries: list[str] = []
    for rx, query in IMG_HINTS:
        if rx.search(blob) and query not in queries:
            queries.append(query)
    # Nombres propios de 2+ palabras en el titular (lugares, personas).
    for chunk in re.findall(r"\b([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚáéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚáéíóúñ]+){1,3})\b", title):
        if chunk.lower() not in {"estados unidos", "ee uu", "nueva york"} and chunk not in queries:
            queries.append(chunk)
    queries.extend(IMG_FALLBACK.get(slug_tag, IMG_FALLBACK["mundo"]))
    return queries[:8]


def commons_candidates(query: str) -> list[dict]:
    qs = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": 10,
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata|size",
            "iiurlwidth": 1600,
        }
    )
    try:
        data = json.loads(http_get("https://commons.wikimedia.org/w/api.php?" + qs))
    except Exception as e:
        log(f"commons fail {query}: {e}")
        return []
    out = []
    qtok = tokens(query)
    for page in ((data.get("query") or {}).get("pages") or {}).values():
        title = page.get("title") or ""
        if re.search(r"\.(pdf|svg|oga|webm|tiff)|logo|pyramid|election map|illustration", title, re.I):
            continue
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        mime = info.get("mime") or ""
        if mime not in ("image/jpeg", "image/png"):
            continue
        width = int(info.get("thumbwidth") or info.get("width") or 0)
        if width and width < 700:
            continue
        meta = info.get("extmetadata") or {}
        license_short = (meta.get("LicenseShortName") or {}).get("value", "")
        if license_short and not re.search(r"(pd|cc|public domain|cc0|cc-by|attribution)", license_short, re.I):
            continue
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        ftok = tokens(title)
        score = len(qtok & ftok) * 3 + min(width or 0, 2000) / 400
        out.append(
            {
                "title": title,
                "url": url,
                "mime": mime,
                "license": license_short,
                "artist": strip_html((meta.get("Artist") or {}).get("value") or "Wikimedia Commons"),
                "score": score,
            }
        )
    return out


def commons_image(*queries: str) -> tuple[bytes, str, str, str] | None:
    ranked: list[dict] = []
    seen_urls: set[str] = set()
    for query in queries:
        if not query:
            continue
        for cand in commons_candidates(query):
            if cand["url"] in seen_urls:
                continue
            seen_urls.add(cand["url"])
            ranked.append(cand)
    ranked.sort(key=lambda c: c["score"], reverse=True)
    for cand in ranked[:8]:
        try:
            blob = http_get(cand["url"], timeout=25)
        except Exception:
            continue
        if len(blob) < 12000:
            continue
        cap = f"Foto: {cand['artist']}. {cand['license'] or 'Wikimedia Commons'}."
        ext = "jpg" if "jpeg" in cand["mime"] else "png"
        safe = re.sub(r"[^a-z0-9]+", "-", cand["title"].lower())[:40].strip("-")
        return blob, f"{safe or 'tuhoy'}.{ext}", cand["mime"], cap
    return None


def existing_titles(ghost: Ghost) -> list[str]:
    titles = []
    code, resp = ghost.get("/posts/?limit=100&fields=title,canonical_url,slug")
    if code >= 300:
        log(f"list posts fail {code}")
        return titles
    for p in resp.get("posts") or []:
        titles.append(p.get("title") or "")
    return titles


def ensure_tags(ghost: Ghost) -> None:
    wanted = [
        ("Inmigración", "inmigracion", "Inmigración, latinos y la vida entre dos países."),
        ("Latinos", "latinos", "Comunidad latina en Estados Unidos y en la diáspora."),
    ]
    for name, slug, desc in wanted:
        code, resp = ghost.get(f"/tags/slug/{slug}/")
        if code == 200:
            continue
        code, resp = ghost.post_json(
            "/tags/",
            {"tags": [{"name": name, "slug": slug, "description": desc}]},
        )
        log(f"create tag {slug} -> {code}")


def update_navigation(ghost: Ghost) -> None:
    nav = [
        {"label": "Inicio", "url": "/"},
        {"label": "Mundo", "url": "/tag/mundo/"},
        {"label": "Inmigración", "url": "/tag/inmigracion/"},
        {"label": "Política", "url": "/tag/politica/"},
        {"label": "Economía", "url": "/tag/economia/"},
        {"label": "Tecnología", "url": "/tag/tecnologia/"},
        {"label": "Salud", "url": "/tag/salud/"},
        {"label": "Quiénes somos", "url": "/about/"},
    ]
    code, resp = ghost.put_json("/settings/", {"settings": [{"key": "navigation", "value": json.dumps(nav)}]})
    log(f"nav update {code} {resp.get('errors') or 'ok'}")


def collect(force_inmig: bool, limit: int, feeds: list[str] | None = None) -> list[dict]:
    urls = list(feeds or (FEEDS_INMIGRACION if force_inmig else FEEDS_GENERAL))
    # Orden de fuentes al azar en cada edición e intercalado (1.ª de cada una, luego 2.ª...),
    # para que ninguna acapare la portada.
    random.shuffle(urls)
    lists = []
    for feed in urls:
        items = source_items(feed)
        for item in items:
            item["country"] = FEEDS_PAISES.get(feed, "")
        lists.append(items)
    bag = [lst[i] for i in range(max((len(lst) for lst in lists), default=0)) for lst in lists if i < len(lst)]
    out = []
    seen = set()
    for item in bag:
        title = item["title"]
        if not title or SKIP_TITLE.search(title):
            continue
        key = norm_title(title)
        if key in seen:
            continue
        seen.add(key)
        if force_inmig and not INMIG_RE.search(title):
            continue
        out.append(item)
        if len(out) >= limit:
            break
    return out


def publish_item(ghost: Ghost, item: dict, force_inmig: bool, featured: bool, known: list[str], state: dict) -> bool:
    title = headline_es(item["title"])
    if any(similar(title, k) for k in known):
        log(f"skip similar: {title}")
        return False
    if norm_title(title) in state["seen_titles"] or item["url"] in state["seen_urls"]:
        log(f"skip seen: {title}")
        return False

    article_url = resolve_article_url(item["url"], title)
    body_text = trim_to_headline(extract_article(article_url), item["title"], title)
    text = (item.get("desc") or "") + " " + body_text
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < 280:
        log(f"skip short: {title}")
        return False
    if len(re.findall(r"\bdata-[a-z-]+=", body_text)) >= 3:
        log(f"skip texto con código de la página: {title}")
        return False
    if item.get("require_body") and len(body_text) < 600:
        log(f"skip sin artículo legible: {title}")
        return False
    if DRY_RUN:
        tags = classify(title, text, force_inmig)
        tags += [name for name, rx in COUNTRY_TAGS if rx.search(f"{title} {text[:300]}") or item.get("country") == name]
        log(f"[prueba] publicaría ({', '.join(tags)}){' ★' if featured else ''}: {title} <- {article_url}")
        known.append(title)
        return True
    source_title = title
    written = None
    if writer.enabled():
        full = (item.get("desc") or "") + " " + trim_to_headline(extract_article(article_url, limit=9000), item["title"], title)
        sources = [
            {
                "name": item.get("source") or urllib.parse.urlparse(article_url).netloc.replace("www.", ""),
                "url": clean_source_url(article_url),
                "title": source_title,
                "text": re.sub(r"\s+", " ", full).strip(),
            }
        ]
        try:
            written = writer.write_article(sources, inmigracion=force_inmig, log=log)
        except Exception as e:
            log(f"writer fail, extractivo {title}: {e}")
    if written:
        title = written["headline"]
        body = written["html"]
        excerpt = written["deck"]
    else:
        try:
            body = write_html(title, text, item.get("source") or "", article_url)
        except ValueError as e:
            log(f"skip write {title}: {e}")
            return False
        excerpt = excerpt_es(text, title)

    tags = classify(source_title, text, force_inmig)
    slug_tag = primary_slug(tags)
    # País solo por titular y entradilla: el cuerpo de las páginas trae menús y recomendados.
    tags += [
        name
        for name, rx in COUNTRY_TAGS
        if (item.get("country") == name or rx.search(f"{source_title} {title} {excerpt}")) and name not in tags
    ]
    img_url = None
    caption = ""
    picked = source_photo(article_url)
    if not picked:
        queries = story_image_queries(title, text, slug_tag)
        picked = commons_image(*queries)
    if picked:
        blob, filename, mime, caption = picked
        img_url = ghost.upload_image(blob, filename, mime)
        if img_url and caption:
            body += f"\n<p><em>{html.escape(caption)}</em></p>"

    if written:
        # Redacción original: indexable. Las frases sin sustento ya se eliminaron; #revisar solo
        # la pone en la cola de revisión humana.
        internal = [{"name": IA_TAG}]
        if written["flagged"]:
            internal.append({"name": REVIEW_TAG})
            writer.queue_for_review(
                written,
                clean_source_url(article_url),
                "fuentes escasas" if written["thin_sources"] else "afirmaciones sin sustento",
            )
    else:
        # Texto extractivo de la fuente: no indexable hasta que la redacción lo reescriba.
        internal = [{"name": AUTO_TAG}]

    payload = {
        "posts": [
            {
                "title": title,
                "slug": seo_slug(title),
                "meta_title": seo_meta_title(title),
                "custom_excerpt": excerpt,
                "meta_description": smart_cut(excerpt, 155),
                "html": body,
                "status": "published",
                "featured": featured,
                "tags": [{"name": t} for t in tags] + internal,
                "feature_image": img_url,
                "feature_image_caption": caption,
                "feature_image_alt": title,
                "visibility": "public",
            }
        ]
    }
    code, resp = ghost.post_json("/posts/?source=html", payload)
    if code >= 300:
        log(f"publish fail {code} {resp}")
        return False
    post = (resp.get("posts") or [{}])[0]
    log(f"published {post.get('slug')} :: {title}")
    state["seen_urls"].append(item["url"])
    state["seen_urls"].append(article_url)
    state["seen_titles"].append(norm_title(source_title))
    known.append(source_title)
    if title != source_title:
        known.append(title)
    return True


def run(max_general: int = 2, max_inmig: int = 2, max_paises: int = 1) -> int:
    env = load_env()
    ghost = Ghost(env["GHOST_URL"], env["GHOST_ADMIN_API_KEY"])
    state = load_state()
    if not DRY_RUN:
        ensure_tags(ghost)
        update_navigation(ghost)
    known = existing_titles(ghost)
    published = 0

    extras = []
    for page in PAGINAS_INMIGRACION:
        extras.append({"title": "", "url": page, "desc": "", "pub": "", "source": urllib.parse.urlparse(page).netloc})
    for extra in extras:
        try:
            raw = http_get(extra["url"], timeout=18).decode("utf-8", "replace")
        except Exception:
            continue
        extra["title"] = headline_es(page_title(raw) or extra["url"])
        extra["desc"] = extract_article(extra["url"])[:500]
        if len(extra["desc"]) < 280:
            continue
        if publish_item(ghost, extra, True, featured=False, known=known, state=state):
            published += 1
            if published >= max_inmig:
                break

    inmig = collect(True, 16)
    first = published == 0
    for item in inmig:
        if published >= max_inmig:
            break
        if publish_item(ghost, item, True, featured=first, known=known, state=state):
            published += 1
            first = False

    general_ok = 0
    for item in collect(False, 18):
        if general_ok >= max_general:
            break
        if INMIG_RE.search(item["title"]):
            continue
        if publish_item(ghost, item, False, featured=False, known=known, state=state):
            general_ok += 1
            published += 1

    paises_ok = 0
    for item in collect(False, 15, feeds=list(FEEDS_PAISES)):
        if paises_ok >= max_paises:
            break
        item["require_body"] = True
        if publish_item(ghost, item, bool(INMIG_RE.search(item["title"])), featured=False, known=known, state=state):
            paises_ok += 1
            published += 1

    if DRY_RUN:
        log(f"[prueba] fin: {published} notas (no se publicó nada)")
        return 0
    state["runs"].append(
        {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "published": published,
            "inmigracion": min(published, max_inmig),
        }
    )
    state["seen_urls"] = state["seen_urls"][-400:]
    state["seen_titles"] = state["seen_titles"][-400:]
    state["runs"] = state["runs"][-60:]
    save_state(state)
    log(f"done published={published}")
    return 0 if published else 1


def main() -> int:
    global DRY_RUN
    import argparse

    ap = argparse.ArgumentParser(description="Una edición de TuHoy (el cron la lanza a las 6, 12 y 18 h de Chicago).")
    ap.add_argument("--inmig", type=int, default=2, help="notas de inmigración (la primera va destacada)")
    ap.add_argument("--general", type=int, default=2, help="notas generales")
    ap.add_argument("--paises", type=int, default=1, help="notas de Venezuela/Cuba")
    ap.add_argument("--dry-run", action="store_true", help="muestra qué publicaría, sin redactar ni publicar")
    args = ap.parse_args()
    DRY_RUN = args.dry_run

    lock = Path("/tmp/tuhoy-daily.lock")
    if lock.exists() and time.time() - lock.stat().st_mtime < 3600:
        log("lock held, exit")
        return 0
    lock.write_text(str(os.getpid()), encoding="utf-8")
    try:
        return run(max_general=args.general, max_inmig=args.inmig, max_paises=args.paises)
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    sys.exit(main())
