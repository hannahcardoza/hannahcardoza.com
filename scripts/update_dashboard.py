#!/usr/bin/env python3
"""Refresh the "now_playing.log" dashboard page (/web-log/now-playing/).

Pulls data from Letterboxd (RSS), Goodreads (public bookshelf widgets),
Spotify (Web API, needs SPOTIFY_* secrets), Strava (API, needs STRAVA_*
secrets), and Pinterest (RSS), renders static HTML, and writes it between marker comments in
docs/web-log/now-playing/index.html. Each source has its own markers.
If a source fails, its previous content is kept.

The "updated" date only changes when the data itself changed, so the
daily job doesn't create a commit when nothing is new.

Usage: python3 scripts/update_dashboard.py [path/to/page.html]
"""

import datetime as dt
import html
import base64
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

LETTERBOXD_USER = "iloveh0tdads"
PINTEREST_USER = "hannahmontanaxoxo"
GOODREADS_USER_ID = "181465183"
# Month each book was completed, saved so it persists. Filled from the date the
# book was rated (public updates widget), or else the month it first appeared
# on the Read shelf. Edit the file to correct a month.
FINISHED_FILE = Path(__file__).resolve().parent / "goodreads_finished.json"

UA = "hannahcardoza.com dashboard (+https://hannahcardoza.com)"
IMAGE_HOSTS = {"a.ltrbxd.com", "i.pinimg.com", "i.gr-assets.com",
               "i.scdn.co", "mosaic.scdn.co", "image-cdn-ak.spotifycdn.com", "image-cdn-fa.spotifycdn.com"}
KPIS = {}  # headline numbers collected by the renderers: key -> (value, label)
DEFAULT_PAGE = Path(__file__).resolve().parent.parent / "docs" / "web-log" / "now-playing" / "index.html"


def fetch(url, headers=None, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
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
    films, this_year, year = [], 0, str(dt.date.today().year)
    for it in root.findall("./channel/item"):
        title = it.findtext("letterboxd:filmTitle", namespaces=ns)
        if not title:
            continue  # lists and other non-diary items
        if (it.findtext("letterboxd:watchedDate", namespaces=ns) or "").startswith(year):
            this_year += 1
        if len(films) == 4:
            continue
        films.append({
            "title": title,
            "year": it.findtext("letterboxd:filmYear", namespaces=ns) or "",
            "rating": stars(it.findtext("letterboxd:memberRating", namespaces=ns)),
            "poster": first_img(it.findtext("description")),
        })
    if not films:
        raise ValueError("no films in feed")
    # The feed holds the 50 most recent entries, so 50 means "at least 50".
    KPIS["films"] = (f"{this_year}+" if this_year >= 50 else str(this_year), f"films logged in {year}")
    cards = []
    for f in films:
        img = (f'<img src="{esc(f["poster"])}" alt="Poster for {esc(f["title"])}" loading="lazy" width="150" height="225"/>'
               if f["poster"] else '<div class="dash-noposter"></div>')
        year = f' <span class="dash-year">{esc(f["year"])}</span>' if f["year"] else ""
        rating = f'<span class="dash-stars">{esc(f["rating"])}</span>' if f["rating"] else ""
        cards.append(f'<li>{img}<span class="dash-cap">{esc(f["title"])}{year}</span>{rating}</li>')
    return '<ul class="dash-films">' + "".join(cards) + "</ul>"



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


def rated_dates():
    """{title: date} for books rated recently, from the public updates widget.

    The widget shows recent activity as a date header followed by an update,
    e.g. "October 10" then "rated a book: The Only One Left". It has no year,
    so a date later than today is taken to be from last year.
    """
    page = fetch(f"https://www.goodreads.com/widgets/user_update_widget?num_updates=50&user={GOODREADS_USER_ID}").decode("utf-8", "replace")
    today = dt.date.today()
    dates, current = {}, None
    for blk in re.split(r'<div class="update[^"]*"', page)[1:]:
        parts = [p.strip().lstrip(">").strip() for p in html.unescape(re.sub(r"<[^>]+>", "|", blk)).split("|")]
        parts = [p for p in parts if p]
        if len(parts) == 1:
            try:
                d = dt.datetime.strptime(f"{parts[0]} {today.year}", "%B %d %Y").date()
            except ValueError:
                continue
            current = d.replace(year=today.year - 1) if d > today else d
        elif current and "rated a book" in parts and "by" in parts:
            title = clean_title(parts[parts.index("by") - 1])
            dates.setdefault(title, current)
    return dates


def finished_months(read_books):
    """Completed month per book, saved in FINISHED_FILE so it outlives the widget.

    Uses the date the book was rated when the updates widget has it.
    Otherwise falls back to the month the book first appeared on the Read shelf.
    """
    data = json.loads(FINISHED_FILE.read_text(encoding="utf-8")) if FINISHED_FILE.exists() else {}
    try:
        rated = rated_dates()
    except Exception as e:
        print(f"warning: updates widget failed ({e})", file=sys.stderr)
        rated = {}
    before = dict(data)
    for b in read_books:
        title = b["title"]
        if title in rated and not data.get(title):
            data[title] = rated[title].strftime("%B %Y")
        elif title not in data:
            data[title] = dt.date.today().strftime("%B %Y")
    if data != before:
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
    year = str(dt.date.today().year)
    KPIS["books"] = (str(sum(1 for b in read if (months.get(b["title"]) or "").endswith(year))), f"books read in {year}")

    def completed_key(b):  # newest completion first, undated books last
        try:
            return dt.datetime.strptime(months.get(b["title"]) or "", "%B %Y")
        except ValueError:
            return dt.datetime.min
    read = sorted(read, key=completed_key, reverse=True)

    def card(b, done):
        img = (f'<img src="{esc(b["cover"])}" alt="Cover of {esc(b["title"])}" loading="lazy" width="150" height="225"/>'
               if b["cover"] else '<div class="dash-noposter"></div>')
        by = f'<span class="dash-by">{esc(b["author"])}</span>' if b["author"] else ""
        rating = f'<span class="dash-stars">{"★" * b["stars"]}</span>' if done and b["stars"] else ""
        tag = ""
        if done:
            when = months.get(b["title"])
            try:
                when = dt.datetime.strptime(when or "", "%B %Y").strftime("%b %Y")
            except ValueError:
                pass
            tag = f'<span class="dash-done">✓ {esc(when)}</span>' if when else '<span class="dash-done">✓</span>'
        return f'<li>{img}<span class="dash-cap">{esc(b["title"])}</span>{by}{rating}{tag}</li>'

    out = ""
    if current:
        out += ('<p class="dash-sub dash-sub-now">Currently reading</p><ul class="dash-films">'
                + "".join(card(b, False) for b in current[:4]) + "</ul>")
    if read:
        out += ('<p class="dash-sub dash-sub-done">Completed</p><ul class="dash-films">'
                + "".join(card(b, True) for b in read[:4]) + "</ul>")
    return out


def env(name):
    """Read a setting from the environment, or from a local .env file (gitignored)."""
    if os.environ.get(name):
        return os.environ[name]
    path = Path(__file__).resolve().parent.parent / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip() == name:
                return v.strip()
    return None


def spotify_get(path, token):
    return json.loads(fetch(f"https://api.spotify.com/v1/{path}", headers={"Authorization": f"Bearer {token}"}))


def spotify_token():
    cid, secret, refresh = env("SPOTIFY_CLIENT_ID"), env("SPOTIFY_CLIENT_SECRET"), env("SPOTIFY_REFRESH_TOKEN")
    if not (cid and secret and refresh):
        raise ValueError("Spotify credentials not set")
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": refresh}).encode()
    resp = fetch("https://accounts.spotify.com/api/token", data=body,
                 headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"})
    return json.loads(resp)["access_token"]


def smallest_image(images, min_px=64):
    """Pick the smallest image at least min_px wide (Spotify lists several sizes)."""
    imgs = sorted((i for i in images or [] if i.get("url")), key=lambda i: i.get("width") or 9999)
    for i in imgs:
        if (i.get("width") or 9999) >= min_px:
            return safe_image(i["url"])
    return safe_image(imgs[-1]["url"]) if imgs else None


def track_row(track):
    art = smallest_image(track.get("album", {}).get("images"))
    artists = ", ".join(a["name"] for a in track.get("artists", []))
    img = f'<img src="{esc(art)}" alt="" loading="lazy" width="44" height="44"/>' if art else '<span class="dash-noart"></span>'
    return (f'<li>{img}<span class="dash-track">{esc(track.get("name"))}'
            f'<span class="dash-artist">{esc(artists)}</span></span></li>')


def render_spotify():
    token = spotify_token()
    me = spotify_get("me", token)

    recent, seen = [], set()
    for item in spotify_get("me/player/recently-played?limit=30", token).get("items", []):
        tr = item.get("track") or {}
        if tr.get("id") and tr["id"] not in seen:
            seen.add(tr["id"])
            recent.append(tr)
        if len(recent) == 5:
            break
    top = spotify_get("me/top/tracks?time_range=short_term&limit=5", token).get("items", [])
    artists = spotify_get("me/top/artists?time_range=short_term&limit=1", token).get("items", [])
    if artists:
        KPIS["artist"] = (artists[0].get("name", ""), "top artist this month")
    playlists = [pl for pl in spotify_get("me/playlists?limit=50", token).get("items", [])
                 if pl and pl.get("public") and (pl.get("owner") or {}).get("id") == me.get("id")][:6]
    if not (recent or top or playlists):
        raise ValueError("no Spotify data")

    out = '<div class="dash-cols">'
    if recent:
        out += '<div><p class="dash-sub dash-sub-spot">Recently played</p><ul class="dash-tracks">' + "".join(track_row(t) for t in recent) + "</ul></div>"
    if top:
        out += '<div><p class="dash-sub dash-sub-spot">On repeat this month</p><ul class="dash-tracks">' + "".join(track_row(t) for t in top) + "</ul></div>"
    out += "</div>"
    if playlists:
        cards = []
        for pl in playlists:
            cover = smallest_image(pl.get("images"), min_px=200)
            link = (pl.get("external_urls") or {}).get("spotify", "")
            if not link.startswith("https://open.spotify.com/"):
                link = ""
            img = f'<img src="{esc(cover)}" alt="" loading="lazy"/>' if cover else '<span class="dash-noart"></span>'
            inner = f'{img}<span class="dash-cap">{esc(pl.get("name"))}</span>'
            cards.append(f'<li><a href="{esc(link)}" target="_blank" rel="noopener">{inner}</a></li>' if link else f"<li>{inner}</li>")
        out += '<p class="dash-sub dash-sub-spot">Recent playlists</p><ul class="dash-lists">' + "".join(cards) + "</ul>"
    return out


RUN_TYPES = {"Run", "TrailRun", "VirtualRun"}


def render_strava():
    """Year-to-date fitness totals. Totals only: no maps, routes, or times of day."""
    cid, secret, refresh = env("STRAVA_CLIENT_ID"), env("STRAVA_CLIENT_SECRET"), env("STRAVA_REFRESH_TOKEN")
    if not (cid and secret and refresh):
        raise ValueError("Strava credentials not set")
    body = urllib.parse.urlencode({"client_id": cid, "client_secret": secret,
                                   "grant_type": "refresh_token", "refresh_token": refresh}).encode()
    tok = json.loads(fetch("https://www.strava.com/oauth/token", data=body))
    if tok.get("refresh_token") and tok["refresh_token"] != refresh:
        print("warning: Strava issued a new refresh token. Rerun scripts/strava_auth.py "
              "if the Fitness section stops updating.", file=sys.stderr)
    year = dt.date.today().year
    after = int(dt.datetime(year, 1, 1).timestamp())
    acts, page = [], 1
    while True:
        batch = json.loads(fetch(f"https://www.strava.com/api/v3/athlete/activities?after={after}&per_page=200&page={page}",
                                 headers={"Authorization": f"Bearer {tok['access_token']}"}))
        acts += batch
        if len(batch) < 200:
            break
        page += 1
    runs = [a for a in acts if a.get("sport_type") in RUN_TYPES]
    hikes = [a for a in acts if a.get("sport_type") == "Hike"]
    km = sum(a.get("distance", 0) for a in runs) / 1000
    longest = max((a.get("distance", 0) for a in runs), default=0) / 1000
    KPIS["km"] = (f"{km:.1f}", f"km run in {year}")
    tiles = [(str(len(runs)), "runs"), (f"{longest:.1f}", "km longest run"),
             (str(len(hikes)), "hikes"), (str(len(acts)), "activities")]
    out = ('<ul class="dash-stats">'
           + "".join(f'<li><span class="dash-num">{esc(v)}</span><span class="dash-label">{esc(k)}</span></li>' for v, k in tiles)
           + "</ul>")
    out += monthly_chart(acts, year)
    if acts:
        out += latest_activity(max(acts, key=lambda a: a.get("start_date", "")))
    return out


def monthly_chart(acts, year):
    """Column chart of distance per month (all activities), as inline SVG.

    Single series, so no legend: the subtitle names it. Each column has a
    native tooltip, and a visually hidden table carries the same numbers.
    """
    months = dt.date.today().month if year == dt.date.today().year else 12
    km = [0.0] * months
    for a in acts:
        m = int(a["start_date_local"][5:7])
        if m <= months:
            km[m - 1] += a.get("distance", 0) / 1000
    top = max(km) if any(km) else 1
    step = next(s for s in (5, 10, 20, 25, 50, 100, 200, 500) if top / s <= 4)
    ymax = step * -(-top // step)
    W, H, L, B, T = 420, 150, 30, 20, 14  # size and left/bottom/top padding
    slot = (W - L) / months
    bw = min(24, slot * 0.6)
    y = lambda v: T + (H - T - B) * (1 - v / ymax)
    parts = [f'<svg class="dash-chart" viewBox="0 0 {W} {H}" role="img" aria-label="Distance per month in {year}">']
    tick = 0
    while tick <= ymax:  # recessive hairline grid with clean tick labels
        parts.append(f'<line class="grid" x1="{L}" x2="{W}" y1="{y(tick):.1f}" y2="{y(tick):.1f}"/>'
                     f'<text class="tick" x="{L - 6}" y="{y(tick) + 4:.1f}" text-anchor="end">{tick:g}</text>')
        tick += step
    peak = km.index(top) if any(km) else -1
    for i, v in enumerate(km):
        cx = L + slot * i + slot / 2
        name = dt.date(year, i + 1, 1).strftime("%b")
        if v > 0:
            x0, x1, y0, yb = cx - bw / 2, cx + bw / 2, y(v), y(0)
            r = min(4, (yb - y0), bw / 2)
            d = (f"M{x0:.1f},{yb:.1f}V{y0 + r:.1f}Q{x0:.1f},{y0:.1f} {x0 + r:.1f},{y0:.1f}"
                 f"H{x1 - r:.1f}Q{x1:.1f},{y0:.1f} {x1:.1f},{y0 + r:.1f}V{yb:.1f}Z")
            parts.append(f'<g class="bar" tabindex="0"><title>{name} {year}: {v:.1f} km</title>'
                         f'<rect class="hit" x="{L + slot * i:.1f}" y="{T}" width="{slot:.1f}" height="{H - T - B}"/>'
                         f'<path d="{d}"/></g>')
            if i == peak:
                parts.append(f'<text class="peak" x="{cx:.1f}" y="{y0 - 4:.1f}" text-anchor="middle">{v:.0f}</text>')
        parts.append(f'<text class="tick" x="{cx:.1f}" y="{H - 5}" text-anchor="middle">{name[0]}</text>')
    parts.append(f'<line class="axis" x1="{L}" x2="{W}" y1="{y(0):.1f}" y2="{y(0):.1f}"/></svg>')
    rows = "".join(f"<tr><td>{dt.date(year, i + 1, 1):%B}</td><td>{v:.1f}</td></tr>" for i, v in enumerate(km))
    table = f'<table class="sr-only"><caption>Distance per month in {year}</caption><tr><th>Month</th><th>km</th></tr>{rows}</table>'
    return (f'<p class="dash-sub dash-sub-run">Distance per month, km (all activities)</p>'
            f'<div class="dash-chart-wrap">{"".join(parts)}{table}</div>')


def render_kpis(previous):
    """Headline tiles. A tile whose source failed keeps its previous value."""
    old = {key: tile for tile, key in re.findall(r'(<li data-kpi="(\w+)">.*?</li>)', previous, re.S)}
    tiles = []
    for key in ("films", "books", "km", "artist"):
        if key in KPIS:
            value, label = KPIS[key]
            cls = " dash-kpi-text" if key == "artist" else ""
            tiles.append(f'<li data-kpi="{key}"><span class="dash-kpi{cls}">{esc(value)}</span>'
                         f'<span class="dash-label">{esc(label)}</span></li>')
        elif key in old:
            tiles.append(old[key])
    if not tiles:
        raise ValueError("no headline numbers")
    return '<ul class="dash-kpis">' + "".join(tiles) + "</ul>"


def duration(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def latest_activity(a):
    """Most recent activity: type, date, and stats. No title, map, location, or time of day."""
    kind = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", a.get("sport_type") or a.get("type") or "Activity")
    day = dt.date.fromisoformat(a["start_date_local"][:10])
    km = a.get("distance", 0) / 1000
    stats = []
    if km:
        stats.append(("Distance", f"{km:.2f} km"))
    if a.get("moving_time"):
        stats.append(("Time", duration(a["moving_time"])))
    if km and a.get("moving_time") and a.get("sport_type") in RUN_TYPES:
        stats.append(("Pace", f"{duration(a['moving_time'] / km)} /km"))
    if a.get("total_elevation_gain"):
        stats.append(("Elevation", f"{a['total_elevation_gain']:.0f} m"))
    return (f'<p class="dash-sub dash-sub-run">Latest activity · {esc(kind)} · {day:%b} {day.day}, {day.year}</p>'
            '<ul class="dash-latest">'
            + "".join(f'<li><span class="dash-label">{esc(k)}</span><span class="dash-val">{esc(v)}</span></li>' for k, v in stats)
            + "</ul>")


def render_pinterest():
    root = ET.fromstring(fetch(f"https://www.pinterest.com/{PINTEREST_USER}/feed.rss"))
    pins = []
    for it in root.findall("./channel/item"):
        img = first_img(it.findtext("description"))
        if img:
            pins.append((img, (it.findtext("title") or "").strip() or "Pinterest pin"))
        if len(pins) == 15:
            break
    if not pins:
        raise ValueError("no pins in feed")
    return ('<ul class="dash-pins">'
            + "".join(f'<li><img src="{esc(src)}" alt="{esc(alt)}" loading="lazy"/></li>' for src, alt in pins)
            + "</ul>")


SOURCES = [("letterboxd", render_letterboxd), ("goodreads", render_goodreads), ("spotify", render_spotify), ("strava", render_strava), ("pinterest", render_pinterest)]


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

    prev = re.search(r"<!-- dash:kpis:start -->(.*?)<!-- dash:kpis:end -->", page, re.S)
    try:
        page = replace_block(page, "kpis", render_kpis(prev.group(1) if prev else ""))
    except Exception as e:
        print(f"warning: kpis failed, keeping previous content ({e})", file=sys.stderr)

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
