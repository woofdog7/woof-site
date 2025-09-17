from flask import Flask, render_template, url_for, Response
import feedparser
from bs4 import BeautifulSoup
from pathlib import Path
import requests
import json
from datetime import datetime, timezone
import time



CACHE_TTL: float = 24 * 60 * 60.0
_cache = {"ts": 0.0, "posts": []}
HTTP_TIMEOUT = 8
HTTP_HEADERS = {"User-Agent": "woof-site/1.0 (+https://example.com)"}

app = Flask(__name__)

# TEMP: hardcoded secret for local dev only
app.secret_key = "dev-woofdog-secret-12345"

SUBSTACK_BASE = "https://ridethewave721.substack.com"

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "reading.json"

_warmed = False

@app.before_request
def _warm_cache_once():
    global _warmed
    if _warmed:
        return
    try:
        fetch_recent_from_substack(limit=5)
    except Exception:
        pass
    _warmed = True

def _iso_date(p: Path) -> str:
    try:
        t = p.stat().st_mtime
        # timezone-aware and inspector-friendly
        return datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()

@app.after_request
def secure_headers(resp):
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' https: data:; "
        "style-src 'self' 'unsafe-inline'; script-src 'self';"
    )
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return resp

@app.route("/sitemap.xml")
def sitemap():
    # real routes tba
    pages = [
        {
            "loc": url_for("index", _external=True),
            "lastmod": _iso_date(BASE_DIR / "templates" / "index.html"),
        },
    ]

    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="https://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in pages:
        xml.append("<url>")
        xml.append(f"  <loc>{p['loc']}</loc>")
        xml.append(f"  <lastmod>{p['lastmod']}</lastmod>")
        xml.append("</url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")

@app.route("/robots.txt")
def robots():
    return Response("User-agent: *\nDisallow: /\n", mimetype="text/plain")

@app.after_request
def add_noindex_header(resp):
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp

def load_reading():
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"current_project": None, "collections": []}

def _first_img_src(html: str) -> str | None:
    """Grab the first <img src=...> from the RSS HTML."""
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

# manual key projects
PROJECTS = [
    {
        "title": "Creating a True-Random Number Generator",
        "desc": "TRNG implementation and assurance write-up",
        "image": "projects/P2_dia.png",
        "url": "https://woofdog7.substack.com/p/web-app-integration-test-post"
    },
    {
        "title": "Statistical Evaluation for Cryptography",
        "desc": "What's the deal with random numbers",
        "image": "projects/stats.png",
        "url": "https://woofdog7.substack.com/p/web-app-integration-test-post"
    },
    {
        "title": "Coding a Security Operations Centre",
        "desc": "Log parsing to rule setting",
        "image": "projects/soc.png",
        "url": "https://woofdog7.substack.com/p/web-app-integration-test-post"
    },
    {
        "title": "Placeholder",
        "desc": "I need to do more things",
        "image": "projects/scope.png",
        "url": "https://woofdog7.substack.com"
    },
]

@app.route("/")
def index():
    reading = load_reading()
    return render_template(
        "index.html",
        projects=PROJECTS,
        posts=fetch_recent_from_substack(limit=5),
        reading=reading,
        title="woofdog",
        substack_base=SUBSTACK_BASE,
    )