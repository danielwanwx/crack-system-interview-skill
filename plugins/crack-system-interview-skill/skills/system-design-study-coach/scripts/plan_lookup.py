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
        if (parent / "docs" / "system-design-project-route.html").exists() and (parent / "curriculum").is_dir():
            return parent
        if (parent / "skills").is_dir() and (parent / "curriculum").is_dir():
            return parent
    raise SystemExit("Could not find a bundled curriculum from script path.")


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

    algo_match = re.search(r'<div class="algo-pack">(.+?)</div>\s*</section>', text, re.S)
    algo_html = algo_match.group(1) if algo_match else ""
    algo_links = extract_links(algo_html)
    required, optional = [], []
    for link in algo_links:
        target = optional if link["label"].startswith(("选做：", "快刷：")) else required
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
        "source_format": "html-fallback",
    }


def parse_manifest_day(week_doc: dict, item: dict) -> dict:
    week = int(week_doc["week"])
    day = int(item["day"])
    sources = [
        {
            "title": source["title"],
            "label": source.get("provider", ""),
            "url": source["url"],
            "acceptance": source.get("acceptance", ""),
        }
        for source in item.get("sources", [])
    ]
    algorithms = item.get("algorithms", {})

    def normalize_links(items: list[dict]) -> list[dict[str, str]]:
        return [
            {"label": link.get("label") or link.get("title", ""), "url": link["url"]}
            for link in items
        ]

    rubric = {block["time"]: block["task"] for block in item.get("time_blocks", [])}
    rubric.update(
        {
            "产出物": item.get("deliverable", ""),
            "必须掌握": item.get("mastery", ""),
            "修复规则": item.get("repair", ""),
        }
    )
    return {
        "week": week,
        "day": day,
        "date": item["date"],
        "eyebrow": f"第 {week} 周 · 第 {day} 天 · {item['date']} · {item.get('focus', '')}",
        "title": item["title"],
        "deck": item.get("focus", ""),
        "sources": sources,
        "rubric": rubric,
        "algorithms": {
            "required": normalize_links(list(algorithms.get("required", []))),
            "optional": normalize_links(list(algorithms.get("optional", []))),
        },
        "path": item["page"],
        "case_id": item.get("case_id", ""),
        "source_format": "curriculum-manifest",
    }


def load_plan(repo_root: Path) -> list[dict]:
    docs_root = repo_root / "docs"
    pages_by_key: dict[tuple[int, int], dict] = {}
    curriculum_root = repo_root / "curriculum"
    for path in sorted(curriculum_root.glob("week-*.json")):
        week_doc = json.loads(path.read_text(encoding="utf-8"))
        for item in week_doc.get("days", []):
            parsed = parse_manifest_day(week_doc, item)
            key = (parsed["week"], parsed["day"])
            if key in pages_by_key:
                raise ValueError(f"Duplicate curriculum day: Week {key[0]} Day {key[1]}")
            pages_by_key[key] = parsed
    for path in sorted(docs_root.glob("week*/day-*.html")):
        parsed = parse_day(path, docs_root)
        pages_by_key.setdefault((parsed["week"], parsed["day"]), parsed)
    return [pages_by_key[key] for key in sorted(pages_by_key)]


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
