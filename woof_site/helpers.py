# woof_site/helpers.py
import time
import json
import feedparser
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from flask import Response

# ----- config / constants -----
SUBSTACK_BASE = "https://woofdog7.substack.com/"  # swap substack later
CACHE_TTL: float = 24 * 60 * 60.0                      # refresh 24h
HTTP_TIMEOUT = 8
HTTP_HEADERS = {"User-Agent": "woof-site/1.0 (+https://example.com)"}

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "reading.json"

_cache = {"ts": 0.0, "posts": []}

# ----- security headers -----
def secure_headers(resp: Response):
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' https: data:; "
        "style-src 'self' 'unsafe-inline'; script-src 'self';"
    )
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return resp

def add_noindex_header(resp: Response):
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp

# ----- content loaders -----
def load_reading():
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"current_project": None, "collections": []}

def _first_img_src(html: str) -> str | None:
    try:
        soup = BeautifulSoup(html or "", "html.parser")
        img = soup.find("img")
        return img["src"] if img and img.has_attr("src") else None
    except Exception:
        return None

def _og_image_from_page(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT, headers=HTTP_HEADERS)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for key in ("og:image", "og:image:url"):
            tag = soup.find("meta", attrs={"property": key})
            if tag and tag.get("content"):
                return tag["content"]
    except Exception:
        pass
    return None

def fetch_recent_from_substack(limit=5):
    # serve cached copy if fresh
    if _cache["posts"] and (time.time() - _cache["ts"] < CACHE_TTL):
        return _cache["posts"][:limit]

    feed_url = f"{SUBSTACK_BASE}/feed"
    feed = feedparser.parse(feed_url)
    posts = []
    for entry in feed.entries[:limit]:
        html = ""
        if getattr(entry, "content", None):
            html = entry.content[0].value
        elif getattr(entry, "summary", None):
            html = entry.summary

        img = _first_img_src(html) or _og_image_from_page(entry.link) or "/static/projects/placeholder.jpeg"
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        desc = (text[:180] + "…") if len(text) > 180 else text

        posts.append({
            "title": entry.title,
            "url": entry.link,
            "desc": desc,
            "image": img,
            "published": getattr(entry, "published", "")
        })

    _cache["posts"] = posts
    _cache["ts"] = time.time()
    return posts[:limit]