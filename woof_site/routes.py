# woof_site/routes.py
from flask import Blueprint, render_template, url_for, Response
from pathlib import Path
from datetime import datetime, timezone

from .helpers import (
    fetch_recent_from_substack,
    load_reading,
    SUBSTACK_BASE,
)
from .data.projects import PROJECTS

bp = Blueprint("main", __name__)

BASE_DIR = Path(__file__).resolve().parent

# warm the Substack cache once per process (Flask 3 safe)
_warmed = False
@bp.before_app_request
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
        return datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()

@bp.route("/")
def index():
    reading = load_reading()
    return render_template(
        "index.html",
        projects=PROJECTS,                                  # manual key projects
        posts=fetch_recent_from_substack(limit=5),          # Substack recent
        reading=reading,
        title="woofdog",
        substack_base=SUBSTACK_BASE,
    )

@bp.route("/sitemap.xml")
def sitemap():
    pages = [
        {
            "loc": url_for("main.index", _external=True),
            "lastmod": _iso_date(BASE_DIR / "templates" / "index.html"),
        },
    ]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in pages:
        xml.append("<url>")
        xml.append(f"  <loc>{p['loc']}</loc>")
        xml.append(f"  <lastmod>{p['lastmod']}</lastmod>")
        xml.append("</url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")

@bp.route("/robots.txt")
def robots():
    # Disallow crawlers for now
    return Response("User-agent: *\nDisallow: /\n", mimetype="text/plain")