#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from html import unescape
from pathlib import Path


def find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "docs" / "system-design-project-route.html").exists():
            return parent
    raise SystemExit("Could not find docs/system-design-project-route.html from script path.")


def clean_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = unescape(value)
    return re.sub(r"[ \t]+", " ", value).strip()


def first(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text, re.S)
    return clean_html(match.group(1)) if match else default


def extract_links(html: str) -> list[dict[str, str]]:
    return [
        {"label": clean_html(label), "url": unescape(url)}
        for url, label in re.findall(r'<a href="([^"]+)">(.+?)</a>', html, re.S)
    ]


def parse_day(path: Path, docs_root: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    relative_path = path.relative_to(docs_root).as_posix()
    week_match = re.search(r"week(\d+)/day-(\d+)(?:-[^/]+)?\.html$", relative_path)
    if not week_match:
        raise ValueError(f"Not a day page: {path}")
    week = int(week_match.group(1))
    day = int(week_match.group(2))
    eyebrow = first(r'<div class="eyebrow">(.+?)</div>', text)
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", eyebrow)

    source_titles = re.findall(
        r'<div class="source-title"><a href="([^"]+)">(.+?)</a><span>(.+?)</span></div>',
        text,
        re.S,
    )
    proofs = re.findall(r'<div class="proof">(.+?)</div>', text, re.S)
    sources = []
    for idx, (url, title, label) in enumerate(source_titles):
        sources.append(
            {
                "title": clean_html(title),
                "label": clean_html(label),
                "url": unescape(url),
                "acceptance": clean_html(proofs[idx]) if idx < len(proofs) else "",
            }
        )

    rubric = {
        clean_html(th): clean_html(td)
        for th, td in re.findall(r"<tr><th>(.+?)</th><td>(.+?)</td></tr>", text, re.S)
    }

    algo_match = re.search(r'<div class="algo-pack">(.+?)</div></section>', text, re.S)
    algo_html = algo_match.group(1) if algo_match else ""
    algo_links = extract_links(algo_html)
    required, optional = [], []
    for link in algo_links:
        target = optional if link["label"].startswith("选做：") else required
        target.append(link)

    return {
        "week": week,
        "day": day,
        "date": date_match.group(1) if date_match else "",
        "eyebrow": eyebrow,
        "title": first(r"<h1>(.+?)</h1>", text),
        "deck": first(r'<p class="deck">(.+?)</p>', text),
        "sources": sources,
        "rubric": rubric,
        "algorithms": {"required": required, "optional": optional},
        "path": relative_path,
    }


def load_plan(repo_root: Path) -> list[dict]:
    docs_root = repo_root / "docs"
    pages = []
    for path in sorted(docs_root.glob("week*/day-*.html")):
        pages.append(parse_day(path, docs_root))
    return pages


def select_day(plan: list[dict], args: argparse.Namespace) -> dict:
    if args.date:
        matches = [item for item in plan if item["date"] == args.date]
    elif args.week and args.day:
        matches = [item for item in plan if item["week"] == args.week and item["day"] == args.day]
    else:
        today = date.today().isoformat()
        matches = [item for item in plan if item["date"] == today]
        if not matches:
            raise SystemExit(
                f"No plan entry for today ({today}). Pass --week N --day M or --date YYYY-MM-DD."
            )
    if not matches:
        raise SystemExit("No matching day found.")
    return matches[0]


def with_public_url(item: dict, base_url: str) -> dict:
    if base_url:
        base = base_url.rstrip("/")
        item = dict(item)
        item["public_url"] = f"{base}/{item['path']}"
    return item


def render_text(item: dict) -> str:
    lines = [
        f"Week {item['week']} Day {item['day']} - {item['title']}",
        item["eyebrow"],
        "",
        item["deck"],
        "",
        "Learning sources:",
    ]
    for source in item["sources"]:
        lines.append(f"- {source['title']} ({source['label']}): {source['url']}")
        if source["acceptance"]:
            lines.append(f"  {source['acceptance']}")
    lines += ["", "Acceptance:"]
    for key, value in item["rubric"].items():
        lines.append(f"- {key}: {value}")
    lines += ["", "Required algorithms:"]
    for link in item["algorithms"]["required"]:
        lines.append(f"- {link['label']}: {link['url']}")
    if item["algorithms"]["optional"]:
        lines += ["", "Optional hot problems:"]
        for link in item["algorithms"]["optional"]:
            lines.append(f"- {link['label']}: {link['url']}")
    if "public_url" in item:
        lines += ["", f"Page: {item['public_url']}"]
    else:
        lines += ["", f"Path: docs/{item['path']}"]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Look up the 18-week system design plan by date or week/day.")
    parser.add_argument("--date", help="Plan date, YYYY-MM-DD.")
    parser.add_argument("--week", type=int, help="Week number.")
    parser.add_argument("--day", type=int, help="Day number within the week.")
    parser.add_argument("--base-url", default="", help="Optional GitHub Pages base URL.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    item = with_public_url(select_day(load_plan(find_repo_root()), args), args.base_url)
    if args.format == "json":
        print(json.dumps(item, ensure_ascii=False, indent=2))
    else:
        print(render_text(item))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
