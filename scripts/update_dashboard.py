#!/usr/bin/env python3
"""Refresh the "now_playing.log" dashboard page (/web-log/now-playing/).

Pulls public data from Letterboxd (RSS), Goodreads (public bookshelf
widgets), and Pinterest (RSS), renders static HTML, and writes it between marker comments in
docs/web-log/now-playing/index.html. Each source has its own markers.
If a source fails, its previous content is kept.

The "updated" date only changes when the data itself changed, so the
daily job doesn't create a commit when nothing is new.

Usage: python3 scripts/update_dashboard.py [path/to/page.html]
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
PINTEREST_USER = "hannahmontanaxoxo"
GOODREADS_USER_ID = "181465183"
# Month each book was completed. Goodreads doesn't share read dates publicly,
# so the first time a book shows up on the Read shelf, this script records the
# current month here. A null value means "completed, date unknown".
FINISHED_FILE = Path(__file__).resolve().parent / "goodreads_finished.json"

UA = "hannahcardoza.com dashboard (+https://hannahcardoza.com)"
IMAGE_HOSTS = {"a.ltrbxd.com", "i.pinimg.com", "i.gr-assets.com"}
DEFAULT_PAGE = Path(__file__).resolve().parent.parent / "docs" / "web-log" / "now-playing" / "index.html"


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
    return ('<h3 class="dash-h">&gt; Watching <span class="dash-src">via Letterboxd</span></h3>'
            '<ul class="dash-films">' + "".join(cards) + "</ul>")



def goodreads_shelf(shelf, widget_id):
    """Books on a shelf, newest first, via Goodreads' public bookshelf widget.

    The widget is meant for embedding on other sites, so it works without
    signing in. It returns JavaScript containing the widget HTML.
    """
    url = (f"https://www.goodreads.com/review/custom_widget/{GOODREADS_USER_ID}.{shelf}"
           f"?shelf={shelf}&num_books=20&order=d&sort={'date_read' if shelf == 'read' else 'date_added'}"
           f"&show_author=1&show_cover=1&show_rating=1&show_title=1&cover_size=small"
           f"&widget_id={widget_id}&widget_bg_transparent=1&widget_border_width=0")
    js = fetch(url).decode("utf-8", "replace")
    code = js.replace("\\n", "\n").replace('\\"', '"').replace("\\/", "/")
    books = []
    for blk in re.split(r'class="gr_custom_each_container_\d+"', code)[1:]:
        title = re.search(r'gr_custom_title_\d+">\s*<a[^>]*>([^<]+)', blk)
        if not title:
            continue
        author = re.search(r'gr_custom_author_\d+">\s*by\s*<a[^>]*>([^<]+)', blk)
        cover = re.search(r'<img alt="[^"]*" border="0" src="([^"]+)"', blk)
        books.append({
            "title": clean_title(html.unescape(title.group(1))),
            "author": re.sub(r"\s+", " ", html.unescape(author.group(1))).strip() if author else "",
            "stars": len(re.findall(r"gr_flat_red_star_active", blk)),
            "cover": safe_image(re.sub(r"\._S[XY]\d+_", "._SX318_", cover.group(1))) if cover else None,
        })
    return books


def clean_title(title):
    return re.sub(r"\s*\([^)]*#[^)]*\)$", "", title).strip()  # drop "(Series, #6)"


def finished_months(read_books):
    """Load the completed-month record, adding this month for newly read books."""
    data = json.loads(FINISHED_FILE.read_text(encoding="utf-8")) if FINISHED_FILE.exists() else {}
    changed = False
    this_month = dt.date.today().strftime("%B %Y")
    for b in read_books:
        if b["title"] not in data:
            data[b["title"]] = this_month
            changed = True
    if changed:
        FINISHED_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def render_goodreads():
    """One Reading row: currently reading, then the most recently read books."""
    # The widget lists books oldest first, so reverse for newest first.
    current = goodreads_shelf("currently-reading", 2)[::-1]
    read = goodreads_shelf("read", 3)[::-1]
    if not current and not read:
        raise ValueError("no books on either shelf")
    months = finished_months(read)

    def card(b, done):
        img = (f'<img src="{esc(b["cover"])}" alt="Cover of {esc(b["title"])}" loading="lazy" width="150" height="225"/>'
               if b["cover"] else '<div class="dash-noposter"></div>')
        by = f'<span class="dash-by">{esc(b["author"])}</span>' if b["author"] else ""
        rating = f'<span class="dash-stars">{"★" * b["stars"]}</span>' if done and b["stars"] else ""
        tag = ""
        if done:
            when = months.get(b["title"])
            tag = f'<span class="dash-done">✓ Completed{" · " + esc(when) if when else ""}</span>'
        return f'<li>{img}<span class="dash-cap">{esc(b["title"])}</span>{by}{rating}{tag}</li>'

    out = '<h3 class="dash-h">&gt; Reading <span class="dash-src">via Goodreads</span></h3>'
    if current:
        out += ('<p class="dash-sub dash-sub-now">Currently reading</p><ul class="dash-films">'
                + "".join(card(b, False) for b in current[:4]) + "</ul>")
    if read:
        out += ('<p class="dash-sub dash-sub-done">Completed</p><ul class="dash-films">'
                + "".join(card(b, True) for b in read[:4]) + "</ul>")
    return out


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
    return ('<h3 class="dash-h">&gt; Pinning <span class="dash-src">via Pinterest</span></h3><ul class="dash-pins">'
            + "".join(f'<li><img src="{esc(src)}" alt="{esc(alt)}" loading="lazy"/></li>' for src, alt in pins)
            + "</ul>")


SOURCES = [("letterboxd", render_letterboxd), ("goodreads", render_goodreads), ("pinterest", render_pinterest)]


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
