#!/usr/bin/env python3
"""Sync Week 1 presentation only to public GitHub Pages.

Weeks 2-14 live in LoopCoach private data/presentations/ and are served
behind entitlement gates — not published here.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
DESKTOP = Path("/Users/danielwan/Desktop")
BASE = "https://danielwanwx.github.io/crack-system-interview-skill"
PUBLIC_WEEKS = (1,)


def patch_html(html: str, week: int) -> str:
    html = html.replace("file:///Users/danielwan/Desktop/week-manifest/", f"{BASE}/")
    html = re.sub(
        rf'href="file://[^"]*week{week}[^"]*scorecard\.html"',
        f'href="{BASE}/week{week}/scorecard.html"',
        html,
    )
    return html


def patch_action_guide(path: Path, week: int) -> bool:
    text = path.read_text(encoding="utf-8")
    link = f'<a href="week{week}/week{week}-presentation.html">讲义</a>'
    if link in text:
        return False
    needle = f'<a href="week{week}/scorecard.html">评分表</a>'
    if needle not in text:
        return False
    path.write_text(text.replace(needle, f"{link}{needle}"), encoding="utf-8")
    return True


def main() -> None:
    copied = []
    for week in PUBLIC_WEEKS:
        src = DESKTOP / ("bitly-week1.html" if week == 1 else f"week{week}-presentation.html")
        if not src.exists():
            raise FileNotFoundError(src)
        dest_dir = DOCS / f"week{week}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"week{week}-presentation.html"
        html = patch_html(src.read_text(encoding="utf-8"), week)
        dest.write_text(html, encoding="utf-8")
        copied.append(dest.relative_to(DOCS))

        guide = DOCS / f"week{week}-action-guide.html"
        if guide.exists():
            patch_action_guide(guide, week)

    print(f"Synced {len(copied)} public presentation(s) to docs/weekN/")
    for rel in copied:
        print(f"  {BASE}/{rel.as_posix()}")


if __name__ == "__main__":
    main()
