"""Local editorial safeguards; no network calls or credentials."""
import fcntl
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

SENSITIVE = re.compile(r'\b(ice|inmigra\w*|deporta\w*|asilo|visa[s]?|uscis|elecci[oó]n\w*|electoral\w*|votant\w*|voto[s]?|acus\w*|arrest\w*|deten\w*|homicid\w*|suicid\w*|muer[et]\w*|fallec\w*|salud|m[eé]dic\w*|vacun\w*|embaraz\w*|fentanilo|droga[s]?|menor(?:es)?|abuso|guerra|ataque[s]?)\b', re.I)

def review_reasons(title, deck, immigration=False):
    return ['Tema sensible: requiere revisión editorial humana'] if immigration or SENSITIVE.search(title + ' ' + deck) else []

@contextmanager
def edition_lock(path):
    """Kernel releases the lock on exit/crash; never unlink a locked inode."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    acquired = False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError:
            pass
        yield acquired
    finally:
        if acquired:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

def licensed_source(image_url, manifest):
    """An editor must record explicit permission for the exact image URL."""
    try:
        record = json.loads(Path(manifest).read_text()).get(image_url, {})
        if record.get('authorized') is not True:
            return None
        if not all(isinstance(record.get(k), str) and record[k].strip() for k in ('license', 'evidence', 'credit')):
            return None
        if urlsplit(record['evidence']).scheme != 'https':
            return None
        return record
    except (OSError, ValueError, TypeError, AttributeError):
        return None

def commons_license(short_name, license_url):
    # No unknown licenses, NC/ND restrictions or generic "CC" matches.
    return bool(re.fullmatch(r'(?:CC0|Public domain|PD|CC BY(?:-SA)?(?: [1-4]\.0)?)', short_name.strip(), re.I) and urlsplit(license_url).scheme == 'https')

def record_image(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        data = (json.dumps(record, ensure_ascii=False) + '\n').encode()
        with os.fdopen(fd, 'ab', closefd=False) as stream:
            stream.write(data)
            stream.flush()
    finally:
        os.close(fd)
