#!/usr/bin/env python3
"""Refresh the "now_playing.log" dashboard page (/web-log/now-playing/).

Pulls public data from Letterboxd (RSS), Goodreads (public profile page),
and Pinterest (RSS), renders static HTML, and writes it between marker comments in
docs/web-log/now-playing/index.html. Each source has its own markers.
If a source fails, its previous content is kept.

The "updated" date only changes when the data itself changed, so the
daily job doesn't create a commit when nothing is new.

Usage: python3 scripts/update_dashboard.py [path/to/page.html]
"""

import datetime as dt
import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

LETTERBOXD_USER = "iloveh0tdads"
PINTEREST_USER = "hannahmontanaxoxo"
GOODREADS_PROFILE = "https://www.goodreads.com/user/show/181465183-hannah-cardoza"

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
    return ('<h3 class="dash-h">&gt; Watching</h3>'
            '<ul class="dash-films">' + "".join(cards) + "</ul>")



def render_goodreads():
    """Books in the "Currently Reading" box on the public profile page.

    Goodreads has no public feed for this profile, so this reads the profile
    HTML. If Goodreads changes the page, this raises and the previous content
    is kept until the parser is updated.
    """
    page = fetch(GOODREADS_PROFILE).decode("utf-8", "replace")
    start = page.find("is Currently Reading</a>")
    if start < 0:
        raise ValueError("currently reading section not found")
    end = page.find("updatedTimestamp", start)
    seg = page[start:end if end > 0 else start + 8000]
    titles = [html.unescape(re.sub(r"<[^>]+>", "", m)).strip()
              for m in re.findall(r'<a class="bookTitle"[^>]*>(.*?)</a>', seg, re.S)]
    authors = [re.sub(r"\s+", " ", html.unescape(a)).strip()
               for a in re.findall(r'<a class="authorName"[^>]*>(?:<span[^>]*>)?([^<]+)', seg)]
    covers = [safe_image(re.sub(r"\._SX\d+_", "._SX318_", c))
              for c in re.findall(r'<img[^>]+src="(https://i\.gr-assets\.com/[^"]+)"', seg)]
    if not titles:
        raise ValueError("no books in currently reading section")
    cards = []
    for i, title in enumerate(titles[:4]):
        title = re.sub(r"\s*\([^)]*#[^)]*\)$", "", title)  # drop "(Series, #6)"
        author = authors[i] if i < len(authors) else ""
        cover = covers[i] if i < len(covers) else None
        img = (f'<img src="{esc(cover)}" alt="Cover of {esc(title)}" loading="lazy" width="150" height="225"/>'
               if cover else '<div class="dash-noposter"></div>')
        by = f'<span class="dash-by">{esc(author)}</span>' if author else ""
        cards.append(f'<li>{img}<span class="dash-cap">{esc(title)}</span>{by}</li>')
    out = '<h3 class="dash-h">&gt; Reading</h3><ul class="dash-films">' + "".join(cards) + "</ul>"
    try:
        out += render_year_in_books()
    except Exception as e:  # the currently-reading part still renders
        print(f"warning: year in books failed ({e})", file=sys.stderr)
    return out


def render_year_in_books():
    """Books read this year, from the public "Year in Books" page."""
    year = dt.date.today().year
    user_id = re.search(r"/user/show/(\d+)", GOODREADS_PROFILE).group(1)
    page = fetch(f"https://www.goodreads.com/user/year_in_books/{year}/{user_id}").decode("utf-8", "replace")
    books, seen = [], set()
    for tag in re.findall(r"<img[^>]+>", page):
        src = re.search(r'src="(https://i\.gr-assets\.com/[^"]+/books/[^"]+)"', tag)
        alt = re.search(r'alt="([^"]+ by [^"]+)"', tag)
        if not (src and alt):
            continue
        label = html.unescape(alt.group(1))
        if label in seen:
            continue
        seen.add(label)
        title, _, author = label.rpartition(" by ")
        books.append((re.sub(r"\s*\([^)]*#[^)]*\)$", "", title).strip(), author.strip(), safe_image(src.group(1))))
    if not books:
        return ""
    cards = []
    for title, author, cover in books[:8]:
        img = (f'<img src="{esc(cover)}" alt="Cover of {esc(title)}" loading="lazy" width="150" height="225"/>'
               if cover else '<div class="dash-noposter"></div>')
        cards.append(f'<li>{img}<span class="dash-cap">{esc(title)}</span><span class="dash-by">{esc(author)}</span></li>')
    n = len(books)
    return (f'<p class="dash-sub">Read in {year}: {n} book{"s" if n != 1 else ""}</p>'
            '<ul class="dash-films">' + "".join(cards) + "</ul>")


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
