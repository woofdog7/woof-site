from flask import Flask, render_template, abort
from markdown import markdown
from pathlib import Path

app = Flask(__name__)

BASE = Path(__file__).resolve().parent
POSTS = BASE / "posts"

def load_posts():
    posts = []
    for p in POSTS.glob("*.md"):
        title = p.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
        posts.append({"slug": p.stem, "title": title})
    posts.sort(key=lambda x: x["slug"], reverse=True)
    return posts

@app.route("/")
def index():
    return render_template("index.html", posts=load_posts(), title="woofdog")

@app.route("/blog")
def blog():
    return render_template("blog.html", posts=load_posts())

@app.route("/blog/<slug>")
def post(slug):
    path = POSTS / f"{slug}.md"
    if not path.exists():
        abort(404)
    raw = path.read_text(encoding="utf-8")
    html = markdown(raw, extensions=["fenced_code", "codehilite", "tables"])
    title = raw.splitlines()[0].lstrip("# ").strip()
    return render_template("post.html", title=title, body=html)