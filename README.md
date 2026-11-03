# hannahcardoza.com

Personal website for Hannah Cardoza. It's a plain static site (HTML and CSS, no build step), hosted on GitHub Pages at [hannahcardoza.com](https://hannahcardoza.com).

## Structure

```
docs/                    Site root, served by GitHub Pages
├── index.html           Home
├── about/index.html     About
├── experience/index.html
├── blog/index.html      Web log
├── 404.html
├── assets/
│   ├── styles.css       Compiled Tailwind CSS from the original design (don't hand-edit)
│   ├── site.css         Custom styles: ticker banner and contact popup
│   ├── site.js          Footer visitor counter
│   └── og.png           Link preview image
├── favicon.svg / favicon.ico / apple-touch-icon.png
├── robots.txt, sitemap.xml
└── CNAME                Custom domain for GitHub Pages
```

## Run locally

```sh
cd docs
python3 -m http.server 8000
```

Then open http://localhost:8000. Pages use root-relative paths (`/assets/...`), so open them through the server, not as files.

## Editing

- Each page is a standalone HTML file. The header, ticker, nav, footer, and contact popup are repeated in every page, so update all five files when changing them.
- `styles.css` is precompiled Tailwind, so only utility classes already used on the site are available. Put new styles in `site.css`.
- Add new pages to `sitemap.xml`.

## Analytics

Page views are tracked with [GoatCounter](https://hannahcardoza.goatcounter.com) (no cookies). The footer visitor number comes from GoatCounter's public counter, which needs "Allow adding visitor counts on your website" turned on in GoatCounter settings. Visits from localhost aren't counted.

## Deploy

Pushing to `master` publishes the site. GitHub Pages serves the `docs/` folder (Settings → Pages → Deploy from branch → `master` / `docs`).
