#!/usr/bin/env python3
"""Refresh the pinned "now_playing.log" dashboard on the Web Log page.

Pulls public data from Letterboxd (RSS), Chess.com (public API), and
Pinterest (RSS), renders static HTML, and writes it between marker
comments in docs/web-log/index.html. Each source has its own markers;
if a source fails, its previous content is kept.

The "updated" date only changes when the data itself changed, so the
daily job doesn't create a commit when nothing is new.

Usage: python3 scripts/update_dashboard.py [path/to/web-log/index.html]
"""

import datetime as dt
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

LETTERBOXD_USER = "iloveh0tdads"
CHESS_USER = "iloveh0tdads"
PINTEREST_USER = "hannahmontanaxoxo"

UA = "hannahcardoza.com dashboard (+https://hannahcardoza.com)"
IMAGE_HOSTS = {"a.ltrbxd.com", "i.pinimg.com"}
DEFAULT_PAGE = Path(__file__).resolve().parent.parent / "docs" / "web-log" / "index.html"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def esc(s):
    return html.escape(s or "", quote=True)


def safe_image(url):
    """Only allow https images from known hosts (feed content is untrusted)."""
    if not url:
        return None
    parts = urlsplit(html.unescape(url))
    if parts.scheme == "https" and parts.hostname in IMAGE_HOSTS:
        return parts.geturl()
    return None


def first_img(desc):
    m = re.search(r'<img[^>]+src="([^"]+)"', desc or "")
    return safe_image(m.group(1)) if m else None


def stars(rating):
    try:
        r = float(rating)
    except (TypeError, ValueError):
        return ""
    return "★" * int(r) + ("½" if r - int(r) >= 0.5 else "")


def render_letterboxd():
    ns = {"letterboxd": "https://letterboxd.com"}
    root = ET.fromstring(fetch(f"https://letterboxd.com/{LETTERBOXD_USER}/rss/"))
    films = []
    for it in root.findall("./channel/item"):
        title = it.findtext("letterboxd:filmTitle", namespaces=ns)
        if not title:
            continue  # lists and other non-diary items
        films.append({
            "title": title,
            "year": it.findtext("letterboxd:filmYear", namespaces=ns) or "",
            "rating": stars(it.findtext("letterboxd:memberRating", namespaces=ns)),
            "poster": first_img(it.findtext("description")),
        })
        if len(films) == 4:
            break
    if not films:
        raise ValueError("no films in feed")
    cards = []
    for f in films:
        img = (f'<img src="{esc(f["poster"])}" alt="Poster for {esc(f["title"])}" loading="lazy" width="150" height="225"/>'
               if f["poster"] else '<div class="dash-noposter"></div>')
        year = f' <span class="dash-year">{esc(f["year"])}</span>' if f["year"] else ""
        rating = f'<span class="dash-stars">{esc(f["rating"])}</span>' if f["rating"] else ""
        cards.append(f'<li>{img}<span class="dash-cap">{esc(f["title"])}{year}</span>{rating}</li>')
    return ('<h3 class="dash-h">&gt; Watching</h3>'
            '<ul class="dash-films">' + "".join(cards) + "</ul>")


def render_chess():
    s = json.loads(fetch(f"https://api.chess.com/pub/player/{CHESS_USER}/stats"))
    tiles = []
    for key, label in (("chess_rapid", "Rapid"), ("chess_blitz", "Blitz"), ("chess_bullet", "Bullet")):
        rating = s.get(key, {}).get("last", {}).get("rating")
        if rating:
            tiles.append((label, rating))
    puzzles = s.get("tactics", {}).get("highest", {}).get("rating")
    if puzzles:
        tiles.append(("Puzzles (best)", puzzles))
    if not tiles:
        raise ValueError("no chess ratings")
    return ('<h3 class="dash-h">&gt; Playing chess</h3><ul class="dash-stats">'
            + "".join(f'<li><span class="dash-num">{int(v)}</span><span class="dash-label">{esc(k)}</span></li>' for k, v in tiles)
            + "</ul>")


def render_pinterest():
    root = ET.fromstring(fetch(f"https://www.pinterest.com/{PINTEREST_USER}/feed.rss"))
    pins = []
    for it in root.findall("./channel/item"):
        img = first_img(it.findtext("description"))
        if img:
            pins.append((img, (it.findtext("title") or "").strip() or "Pinterest pin"))
        if len(pins) == 6:
            break
    if not pins:
        raise ValueError("no pins in feed")
    return ('<h3 class="dash-h">&gt; Pinning</h3><ul class="dash-pins">'
            + "".join(f'<li><img src="{esc(src)}" alt="{esc(alt)}" loading="lazy"/></li>' for src, alt in pins)
            + "</ul>")


SOURCES = [("letterboxd", render_letterboxd), ("chess", render_chess), ("pinterest", render_pinterest)]


def replace_block(page, name, content):
    pat = re.compile(rf"(<!-- dash:{name}:start -->).*?(<!-- dash:{name}:end -->)", re.S)
    if not pat.search(page):
        raise SystemExit(f"marker dash:{name} not found in page")
    return pat.sub(lambda m: m.group(1) + content + m.group(2), page, count=1)


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PAGE
    original = path.read_text(encoding="utf-8")
    page = original
    failed = []
    for name, render in SOURCES:
        try:
            page = replace_block(page, name, render())
        except SystemExit:
            raise
        except Exception as e:  # keep the previous content for this source
            failed.append(name)
            print(f"warning: {name} failed, keeping previous content ({e})", file=sys.stderr)

    if page != original:
        today = dt.date.today()
        stamp = f"{today:%b} {today.day}, {today.year}"
        page = replace_block(page, "updated", stamp)
        path.write_text(page, encoding="utf-8")
        print(f"updated dashboard ({stamp})")
    else:
        print("no changes")
    if len(failed) == len(SOURCES):
        sys.exit(1)


if __name__ == "__main__":
    main()
