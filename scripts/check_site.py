#!/usr/bin/env python3
"""Basic checks for the static site in docs/.

Checks internal links and assets, HTML tag balance, duplicate ids,
required head tags, and that sitemap.xml matches the pages on disk.
External links are not checked (too flaky for CI).

Usage: python3 scripts/check_site.py [site_root]
Exits with status 1 if any problem is found.
"""

import hashlib
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

SITE_URL = "https://hannahcardoza.com"
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
}
# Elements inside inline SVG are allowed to self-close.
SVG_CHILDREN = {"polygon", "path", "rect", "circle", "line", "polyline", "ellipse", "stop"}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.refs = []
        self.ids = {}
        self.lang = None
        self.title = None
        self.meta = {}
        self.canonical = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        self._open(tag, dict(attrs), self_closing=False)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, dict(attrs), self_closing=True)

    def _open(self, tag, a, self_closing):
        line = self.getpos()[0]
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "title":
            self._in_title = True
            self.title = ""
        if tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key] = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        for attr in ("href", "src"):
            if a.get(attr):
                self.refs.append((line, a[attr]))
        if a.get("id"):
            if a["id"] in self.ids:
                self.errors.append(f"line {line}: duplicate id '{a['id']}' (first on line {self.ids[a['id']]})")
            else:
                self.ids[a["id"]] = line
        if tag not in VOID and not (self_closing and tag in SVG_CHILDREN):
            if self_closing:
                self.errors.append(f"line {line}: <{tag}/> is not a void element")
            else:
                self.stack.append((tag, line))

    def handle_endtag(self, tag):
        line = self.getpos()[0]
        if tag == "title":
            self._in_title = False
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"line {line}: stray </{tag}>")
            return
        open_tag, open_line = self.stack[-1]
        if open_tag == tag:
            self.stack.pop()
        elif any(t == tag for t, _ in self.stack):
            while self.stack and self.stack[-1][0] != tag:
                t, l = self.stack.pop()
                self.errors.append(f"line {l}: <{t}> not closed before </{tag}> on line {line}")
            self.stack.pop()
        else:
            self.errors.append(f"line {line}: </{tag}> does not match open <{open_tag}> from line {open_line}")

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def close(self):
        super().close()
        for t, l in self.stack:
            self.errors.append(f"line {l}: <{t}> never closed")


def resolve(root: Path, page: Path, ref: str):
    """Return the file a local reference points to, or None if it is external."""
    parts = urlsplit(ref)
    if parts.scheme or ref.startswith("//") or ref.startswith("#"):
        if ref.startswith(SITE_URL):
            parts = urlsplit(ref[len(SITE_URL):] or "/")
        else:
            return None
    path = parts.path
    if not path:
        return None
    target = (root / path.lstrip("/")) if path.startswith("/") else (page.parent / path)
    if path.endswith("/") or target.is_dir():
        target = target / "index.html"
    return target


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "docs").resolve()
    pages = sorted(root.rglob("*.html"))
    problems = []

    for page in pages:
        rel = page.relative_to(root)
        p = PageParser()
        p.feed(page.read_text(encoding="utf-8"))
        p.close()
        issues = list(p.errors)

        if not p.lang:
            issues.append("missing <html lang>")
        if not (p.title or "").strip():
            issues.append("missing <title>")
        if "viewport" not in p.meta:
            issues.append("missing viewport meta")
        if rel.name != "404.html":
            if not p.meta.get("description"):
                issues.append("missing meta description")
            if not p.canonical:
                issues.append("missing canonical link")

        for line, ref in p.refs:
            if ref.startswith(("mailto:", "tel:")):
                continue
            m = re.match(r"(/assets/[^?]+\.(?:css|js))(?:\?v=([0-9a-f]+))?$", ref)
            if m:
                want = hashlib.sha256((root / m.group(1).lstrip("/")).read_bytes()).hexdigest()[:8] \
                    if (root / m.group(1).lstrip("/")).is_file() else None
                if want and m.group(2) != want:
                    issues.append(f"line {line}: {m.group(1)} version tag is out of date (run scripts/version_assets.py)")
            target = resolve(root, page, ref)
            if target is not None and not target.is_file():
                issues.append(f"line {line}: broken link {ref}")

        problems += [f"{rel}: {i}" for i in issues]

    sitemap = root / "sitemap.xml"
    if sitemap.is_file():
        listed = set()
        for loc in re.findall(r"<loc>(.*?)</loc>", sitemap.read_text(encoding="utf-8")):
            target = resolve(root, root / "index.html", loc)
            if target is None or not target.is_file():
                problems.append(f"sitemap.xml: {loc} has no matching page")
            else:
                listed.add(target.resolve())
        for page in pages:
            if page.name != "404.html" and page.resolve() not in listed:
                problems.append(f"sitemap.xml: {page.relative_to(root)} is not listed")
    else:
        problems.append("sitemap.xml is missing")

    if problems:
        print(f"Found {len(problems)} problem(s):")
        for msg in problems:
            print(f"  - {msg}")
        return 1
    print(f"OK: checked {len(pages)} pages, internal links, and sitemap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
