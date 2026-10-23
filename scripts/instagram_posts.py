#!/usr/bin/env python3
"""Publica en @tuhoynoticias las mismas notas que se programan para X.

Lee la cola de x_posts.py (data/x_queue.json, solo lectura). Instagram no arma vista previa
con enlace: sube la foto de la nota y pone el texto + la URL en el pie. Lo publicado se
apunta en data/ig_queue.json.

Sin sobresaltos: solo posts cuya hora pasó hace menos de 2 horas, como mucho uno por pasada
(el cron corre cada 15 min) y nada si IG_MODE no es api.

Estado transaccional: guarda intención/contenedor antes de publicar, reconcilia
contra medios reales y no reenvía resultados inciertos. Bloqueos no confirmados
pausan las llamadas 24 h; ninguna pausa demuestra que Meta haya levantado un bloqueo.

Variables en .env: IG_MODE (api | off), FB_PAGE_ID, FB_PAGE_TOKEN (el de la página TuHoy,
con la cuenta de Instagram profesional ligada). IG_USER_ID es opcional: si falta se lee de
la página (instagram_business_account).

  python3 scripts/instagram_posts.py --dry-run    # muestra lo que publicaría ahora
  python3 scripts/instagram_posts.py              # publica lo que toca (cron cada 15 min)
"""
import argparse
import json
import fcntl
import os
import tempfile
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import daily_edition as daily  # noqa: E402
import writer  # noqa: E402

TZ = ZoneInfo("America/Chicago")
X_QUEUE = ROOT / "data" / "x_queue.json"
IG_QUEUE = ROOT / "data" / "ig_queue.json"
LOG = ROOT / "logs" / "instagram.log"
GRAPH = "https://graph.facebook.com/v23.0"
MAX_DELAY = timedelta(hours=2)
PER_RUN = 1
CAPTION_MAX = 2200


def log(msg: str) -> None:
    line = f"{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')} [ig] {msg}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load(path: Path, default: dict) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def due_posts(x_queue: dict, done: set[str], now: datetime) -> list[dict]:
    out = []
    for t in x_queue.get("pendientes", []):
        hora = datetime.fromisoformat(t["hora"])
        if t["id"] in done or hora > now or now - hora > MAX_DELAY:
            continue
        out.append(t)
    return sorted(out, key=lambda t: t["hora"])


class GraphError(RuntimeError):
    """Only safe numeric metadata is logged; response bodies may contain secrets."""
    def __init__(self, http_status, code=None, subcode=None):
        self.http_status, self.code, self.subcode = http_status, code, subcode
        super().__init__(f"Meta HTTP {http_status}, code={code}, subcode={subcode}")

    @property
    def rate_limited(self):
        return self.http_status == 429 or self.code in {4, 17, 32, 613} or self.subcode in {2207051, 2207042}


def graph(method: str, path: str, token: str, fields: dict | None = None) -> dict:
    # Never put the token in URLs, exception messages or state files.
    url = f"{GRAPH}/{path.lstrip('/')}"
    headers = {"Authorization": "Bearer " + token}
    if method == "GET":
        if fields:
            url += "?" + urllib.parse.urlencode(fields)
        req = urllib.request.Request(url, headers=headers, method="GET")
    else:
        req = urllib.request.Request(url, data=urllib.parse.urlencode(fields or {}).encode(),
                                     headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            error = json.loads(e.read()).get("error", {})
        except (ValueError, AttributeError):
            error = {}
        finally:
            e.close()
        raise GraphError(e.code, error.get("code"), error.get("error_subcode")) from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise RuntimeError("Meta transport/response failure; outcome may be uncertain") from None


def save_state(state):
    IG_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=IG_QUEUE.parent, prefix=".ig-state-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, IG_QUEUE)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def recent_media(env, ig, since):
    """Bounded reads, follow only cursors (never token-bearing paging URLs)."""
    rows, after = [], None
    for _ in range(5):
        fields = {"fields": "id,caption,timestamp,permalink", "limit": 100}
        if after:
            fields["after"] = after
        data = graph("GET", f"{ig}/media", env["FB_PAGE_TOKEN"], fields)
        page = data.get("data")
        if not isinstance(page, list):
            raise RuntimeError("invalid media response")
        rows.extend(page)
        if not page or any(datetime.fromisoformat(m["timestamp"]) < since for m in page):
            return rows
        paging = data.get("paging", {})
        after = paging.get("cursors", {}).get("after") if paging.get("next") else None
        if not after:
            return rows
    raise RuntimeError("media reconciliation incomplete; no publication attempted")


def find_existing(item, media):
    url = (item.get("url") or "").strip()
    if not url:
        raise RuntimeError("missing article URL; cannot deduplicate")
    scheduled = datetime.fromisoformat(item["hora"])
    matches = []
    for m in media:
        # Exact URL token, not a substring that could match another article.
        if url in m.get("caption", "").split() and datetime.fromisoformat(m["timestamp"]) >= scheduled - timedelta(minutes=5):
            matches.append(m)
    return sorted(matches, key=lambda m: m["timestamp"])


def confirm(state, item, media_id, now, matches=None):
    if not any(h["id"] == item["id"] for h in state["historial"]):
        row = {"id": item["id"], "fecha": now.date().isoformat(), "ig_id": media_id}
        if matches:
            row["fecha"] = datetime.fromisoformat(matches[0]["timestamp"]).astimezone(TZ).date().isoformat()
            row["reconciled"] = True
            row["duplicate_count"] = max(0, len(matches) - 1)
        state["historial"].append(row)
    state.pop("pending", None)
    save_state(state)


def cooldown(state, now, hours=24):
    state["cooldown_until"] = (now + timedelta(hours=hours)).isoformat()
    save_state(state)



def ig_user_id(env: dict) -> str:
    if env.get("IG_USER_ID"):
        return env["IG_USER_ID"]
    data = graph(
        "GET",
        env["FB_PAGE_ID"],
        env["FB_PAGE_TOKEN"],
        {"fields": "instagram_business_account"},
    )
    ig = (data.get("instagram_business_account") or {}).get("id")
    if not ig:
        raise RuntimeError("la página TuHoy no tiene Instagram profesional ligado")
    return ig


def feature_image(env: dict, post_id: str) -> str | None:
    ghost = daily.Ghost(env["GHOST_URL"], env["GHOST_ADMIN_API_KEY"])
    status, data = ghost.get(f"/posts/{post_id}/?fields=id,feature_image")
    if status != 200:
        raise RuntimeError(f"Ghost {status}: {data}")
    posts = data.get("posts") or []
    url = (posts[0].get("feature_image") if posts else None) or ""
    return url or None


def caption(t: dict) -> str:
    text = (t.get("texto") or t.get("titulo") or "").strip()
    url = (t.get("url") or "").strip()
    pie = f"{text}\n\n{url}".strip() if url else text
    if len(pie) <= CAPTION_MAX:
        return pie
    keep = CAPTION_MAX - len(url) - 2
    if keep < 40:
        return url[:CAPTION_MAX]
    return f"{text[: keep - 1].rstrip()}…\n\n{url}"


def publish(env, ig, image_url, pie, state):
    pending = state["pending"]
    # Persist intent before every side effect. Never blindly repeat an uncertain POST.
    pending["stage"] = "creating"
    save_state(state)
    created = graph("POST", f"{ig}/media", env["FB_PAGE_TOKEN"],
                    {"image_url": image_url, "caption": pie})
    if not created.get("id"):
        raise RuntimeError("container response missing id")
    pending.update(creation_id=created["id"], stage="container")
    save_state(state)
    for _ in range(12):
        result = graph("GET", pending["creation_id"], env["FB_PAGE_TOKEN"],
                       {"fields": "status_code"})
        code = result.get("status_code", "").upper()
        if code == "FINISHED":
            break
        if code in {"ERROR", "EXPIRED", "PUBLISHED"}:
            raise RuntimeError("container requires reconciliation: " + code)
        time.sleep(2)
    else:
        raise RuntimeError("container not ready; retained for reconciliation")
    pending["stage"] = "publishing"
    save_state(state)
    result = graph("POST", f"{ig}/media_publish", env["FB_PAGE_TOKEN"],
                   {"creation_id": pending["creation_id"]})
    if not result.get("id"):
        raise RuntimeError("publish response missing id; reconcile before retry")
    return result["id"]


def run(env, state, x_queue, now, dry_run=False):
    done = {h["id"] for h in state["historial"] if h.get("ig_id")}
    due = due_posts(x_queue, done, now)
    if dry_run:
        print(f"eligible={len(due)} pending={bool(state.get('pending'))} cooldown={state.get('cooldown_until', 'none')}")
        return 0
    if state.get("cooldown_until") and datetime.fromisoformat(state["cooldown_until"]) > now:
        return 0
    if not due and not state.get("pending"):
        return 0
    ig = ig_user_id(env)
    pending = state.get("pending")
    candidates = due + ([pending["item"]] if pending else [])
    since = min(datetime.fromisoformat(t["hora"]) for t in candidates) - timedelta(minutes=5)
    media = recent_media(env, ig, since)
    if pending:
        item = pending["item"]
        matches = find_existing(item, media)
        if matches:
            confirm(state, item, matches[0]["id"], now, matches)
            log("uncertain publication reconciled; no resend")
        else:
            log("publication unresolved; automatic writes paused for manual reconciliation")
            cooldown(state, now)
            return 1
    # Reconcile all eligible items before choosing one; do not let repeats block the queue.
    remaining = []
    for item in due:
        matches = find_existing(item, media)
        if matches:
            confirm(state, item, matches[0]["id"], now, matches)
        elif not any(h["id"] == item["id"] for h in state["historial"]):
            remaining.append(item)
    if not remaining:
        return 0
    quota = graph("GET", f"{ig}/content_publishing_limit", env["FB_PAGE_TOKEN"],
                  {"fields": "quota_usage,config"})
    q = quota["data"][0]
    if q["quota_usage"] >= q["config"]["quota_total"]:
        cooldown(state, now)
        log("publishing quota exhausted; paused")
        return 0
    item = remaining[0]
    img = feature_image(env, item["id"])
    if not img:
        log("eligible article has no image; skipped")
        return 0
    state["pending"] = {"item": item, "started_at": now.isoformat(), "stage": "prepared"}
    save_state(state)
    try:
        media_id = publish(env, ig, img, caption(item), state)
    except (RuntimeError, OSError) as error:
        # Meta has returned 403/2207051 despite actually publishing. Treat every
        # failure after intent as uncertain, even an explicit API error.
        log(str(error) if isinstance(error, RuntimeError) else "local persistence error")
        save_state(state)
        try:
            matches = find_existing(item, recent_media(env, ig, since))
        except (RuntimeError, OSError, ValueError, KeyError):
            matches = []
        if matches:
            confirm(state, item, matches[0]["id"], now, matches)
            log("Meta returned an error but publication was confirmed; no resend")
            return 0
        if isinstance(error, GraphError) and error.rate_limited:
            cooldown(state, now)
        log("publication outcome uncertain; retained, no automatic resend")
        return 1
    confirm(state, item, media_id, now)
    log("publication confirmed and saved")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    env = writer.load_env()
    if (env.get("IG_MODE") or "off").lower() != "api" and not args.dry_run:
        return 0
    if not env.get("FB_PAGE_ID") or not env.get("FB_PAGE_TOKEN"):
        log("missing Facebook page configuration")
        return 1
    IG_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    # Lock the same untracked state inode: all new workers share this lock.
    with (IG_QUEUE.parent / "instagram.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        try:
            state = load(IG_QUEUE, {"historial": []})
            return run(env, state, load(X_QUEUE, {}), datetime.now(TZ), args.dry_run)
        except (RuntimeError, OSError, ValueError, KeyError, TypeError) as error:
            log(str(error) if isinstance(error, GraphError) else "Instagram worker failed safely; inspect state/configuration")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
