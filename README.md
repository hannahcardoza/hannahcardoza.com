# hannahcardoza.com

Personal website for Hannah Cardoza. It's a plain static site (HTML, CSS, and a little JavaScript, no build step), hosted on GitHub Pages at [hannahcardoza.com](https://hannahcardoza.com).

## Structure

```
docs/                       Site root, served by GitHub Pages
├── index.html              Home
├── about/index.html        About
├── experience/index.html   Experience, education, skills
├── web-log/index.html      Web Log
├── web-log/now-playing/    Auto-updated dashboard (Letterboxd, Goodreads, Spotify, Strava, Pinterest)
├── 404.html                Not found page
├── assets/
│   ├── styles.css          Compiled Tailwind CSS from the original design (don't hand-edit)
│   ├── site.css            Custom styles: ticker, popups, tags, legend, dashboard
│   ├── site.js             Visitor counter, welcome popup, sticky mini nav, HC-FM radio
│   └── og.png              Link preview image (screenshot of the home page)
├── favicon.svg, favicon.ico, apple-touch-icon.png
├── robots.txt, sitemap.xml
├── CNAME                   Custom domain for GitHub Pages
└── .nojekyll               Serve files as-is (skip Jekyll processing)
```

## Run locally

```sh
cd docs
python3 -m http.server 8000
```

Then open http://localhost:8000. Pages use root-relative paths (`/assets/...`), so open them through the server, not as files.

To see the welcome popup again, clear the site's data in your browser (it's remembered in `localStorage` under `hc-welcomed`).

## Editing

- Each page is a standalone HTML file. The header, ticker, nav, footer, and contact popup are repeated in every page, so update all five files when changing them.
- After editing anything in `docs/assets/`, run `python3 scripts/version_assets.py`. It updates the `?v=` tags on stylesheet and script links so visitors get the new files right away instead of a cached copy (GitHub Pages caches for 10 minutes). The site check fails if a tag is stale.
- `styles.css` is precompiled Tailwind, so only utility classes already used on the site are available. Put new styles in `site.css`.
- Experience tag colours are defined in `site.css` (`.t-software`, `.t-hardware`, and so on). A new tag needs a class there and, if it starts a new colour group, an entry in the legend.
- After changing the home page, regenerate `assets/og.png` (a 1920×1080 screenshot, taken after the welcome popup has been dismissed) so link previews stay current.
- Add new pages to `sitemap.xml`.

## Web Log dashboard

The dashboard page at `/web-log/now-playing/` is refreshed daily by `scripts/update_dashboard.py` (`.github/workflows/update-dashboard.yml`). It pulls data from Letterboxd (RSS), Goodreads (public bookshelf widgets), Spotify (Web API), Strava (API), and Pinterest (RSS) and writes static HTML between `<!-- dash:NAME:start -->` / `<!-- dash:NAME:end -->` markers in `docs/web-log/now-playing/index.html`. If a source fails, its previous content is kept. The job only commits when the data changed.

- Layout: headline tiles (`dash:kpis`) above a grid of panels, one per source. Each panel's title bar is static HTML in the page; the script fills each panel body.
- Run it locally: `python3 scripts/update_dashboard.py`
- Run it on GitHub: Actions tab, "Update dashboard", "Run workflow"
- Usernames are set at the top of the script
- Spotify needs three GitHub secrets (`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`). `python3 scripts/spotify_auth.py` sets them up and also writes a gitignored `.env` for local runs.
- Strava works the same way: `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_REFRESH_TOKEN`, set up by `python3 scripts/strava_auth.py`. Only totals and the latest activity's stats are shown, never maps, locations, titles, or times of day.
- Goodreads doesn't share read dates, so `scripts/goodreads_finished.json` records the month each book first appears on the Read shelf. Edit it to correct a month (`null` means date unknown).
- GitHub pauses scheduled jobs after 60 days without repo activity. If the dashboard stops updating, re-enable the workflow in the Actions tab.

## Checks

`scripts/check_site.py` checks internal links and assets, HTML tag balance, duplicate ids, required head tags, and that `sitemap.xml` matches the pages. It runs automatically on every push to `master` and every pull request (`.github/workflows/check-site.yml`). External links aren't checked. To run it locally:

```sh
python3 scripts/check_site.py docs
```

## Radio

The RADIO button (bottom left) opens HC-FM, a small player that streams [SomaFM](https://somafm.com) stations (listener-supported, commercial-free). It never autoplays, remembers station/volume/open state in `localStorage` (`hc-radio`), shows the current track from SomaFM's public song feed, and falls back across three stream mirrors. Stations are listed at the top of the radio section in `site.js`.

## Analytics

Page views are tracked with [GoatCounter](https://hannahcardoza.goatcounter.com) (no cookies). The footer visitor number comes from GoatCounter's public counter, which needs "Allow adding visitor counts on your website" turned on in GoatCounter settings. Visits from localhost aren't counted.

## Deploy

Pushing to `master` publishes the site. GitHub Pages serves the `docs/` folder (Settings → Pages → Deploy from branch → `master` / `docs`). **Enforce HTTPS** is turned on in the same settings page.

## License

© Hannah Cardoza. All rights reserved. The site's content and design are not licensed for reuse.
