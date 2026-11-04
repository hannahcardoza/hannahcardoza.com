# hannahcardoza.com

Personal website for Hannah Cardoza. It's a plain static site (HTML, CSS, and a little JavaScript, no build step), hosted on GitHub Pages at [hannahcardoza.com](https://hannahcardoza.com).

## Structure

```
docs/                       Site root, served by GitHub Pages
├── index.html              Home
├── about/index.html        About
├── experience/index.html   Experience, education, skills
├── web-log/index.html      Web Log
├── web-log/now-playing/    Auto-updated dashboard (Letterboxd, Pinterest)
├── 404.html                Not found page
├── assets/
│   ├── styles.css          Compiled Tailwind CSS from the original design (don't hand-edit)
│   ├── site.css            Custom styles: ticker, popups, tags, legend, dashboard
│   ├── site.js             Footer visitor counter and one-time welcome popup
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
- `styles.css` is precompiled Tailwind, so only utility classes already used on the site are available. Put new styles in `site.css`.
- Experience tag colours are defined in `site.css` (`.t-software`, `.t-hardware`, and so on). A new tag needs a class there and, if it starts a new colour group, an entry in the legend.
- After changing the home page, regenerate `assets/og.png` (a 1920×1080 screenshot, taken after the welcome popup has been dismissed) so link previews stay current.
- Add new pages to `sitemap.xml`.

## Web Log dashboard

The dashboard page at `/web-log/now-playing/` is refreshed daily by `scripts/update_dashboard.py` (`.github/workflows/update-dashboard.yml`). It pulls public data from Letterboxd (RSS) and Pinterest (RSS) and writes static HTML between `<!-- dash:NAME:start -->` / `<!-- dash:NAME:end -->` markers in `docs/web-log/now-playing/index.html`. If a source fails, its previous content is kept. The job only commits when the data changed.

- Run it locally: `python3 scripts/update_dashboard.py`
- Run it on GitHub: Actions tab, "Update dashboard", "Run workflow"
- Usernames are set at the top of the script
- GitHub pauses scheduled jobs after 60 days without repo activity. If the dashboard stops updating, re-enable the workflow in the Actions tab.

## Checks

`scripts/check_site.py` checks internal links and assets, HTML tag balance, duplicate ids, required head tags, and that `sitemap.xml` matches the pages. It runs automatically on every push to `master` and every pull request (`.github/workflows/check-site.yml`). External links aren't checked. To run it locally:

```sh
python3 scripts/check_site.py docs
```

## Analytics

Page views are tracked with [GoatCounter](https://hannahcardoza.goatcounter.com) (no cookies). The footer visitor number comes from GoatCounter's public counter, which needs "Allow adding visitor counts on your website" turned on in GoatCounter settings. Visits from localhost aren't counted.

## Deploy

Pushing to `master` publishes the site. GitHub Pages serves the `docs/` folder (Settings → Pages → Deploy from branch → `master` / `docs`). **Enforce HTTPS** is turned on in the same settings page.

## License

© Hannah Cardoza. All rights reserved. The site's content and design are not licensed for reuse.
