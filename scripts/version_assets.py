#!/usr/bin/env python3
"""Add or refresh ?v=<hash> on local CSS/JS links so browsers fetch changes immediately.

GitHub Pages lets browsers cache files for 10 minutes, so without a version
tag a visitor can see new HTML with an old stylesheet. Run this after editing
anything in docs/assets/:

    python3 scripts/version_assets.py

scripts/check_site.py fails if a tag is out of date.
"""

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "docs"
ASSET_RE = re.compile(r'((?:href|src)="(/assets/[^"?]+\.(?:css|js)))(?:\?v=[0-9a-f]+)?"')


def asset_hash(path):
    return hashlib.sha256((ROOT / path.lstrip("/")).read_bytes()).hexdigest()[:8]


def versioned(text):
    return ASSET_RE.sub(lambda m: f'{m.group(1)}?v={asset_hash(m.group(2))}"', text)


def main():
    changed = 0
    for page in sorted(ROOT.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        new = versioned(text)
        if new != text:
            page.write_text(new, encoding="utf-8")
            changed += 1
    print(f"updated asset versions in {changed} page(s)")


if __name__ == "__main__":
    sys.exit(main())
