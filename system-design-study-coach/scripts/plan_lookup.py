#!/usr/bin/env python3
"""Look up one day from the generated 12-week curriculum manifests."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urljoin


def find_curriculum_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "curriculum"
        if (candidate / "week-01.json").exists():
            return candidate
    raise SystemExit("Could not find the bundled 12-week curriculum.")


def load_plan(curriculum_root: Path) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    paths = sorted(curriculum_root.glob("week-*.json"))
    if len(paths) != 12:
        raise SystemExit(f"Expected 12 week manifests, found {len(paths)}.")
    for expected_week, path in enumerate(paths, start=1):
        payload = json.loads(path.read_text(encoding="utf-8"))
        week = int(payload["week"])
        if week != expected_week:
            raise SystemExit(f"Expected Week {expected_week}, found Week {week}.")
        days = payload.get("days", [])
        if len(days) != 7:
            raise SystemExit(f"Week {week} must contain exactly seven days.")
        for expected_day, item in enumerate(days, start=1):
            if int(item["day"]) != expected_day:
                raise SystemExit(
                    f"Week {week}: expected Day {expected_day}, found {item['day']}."
                )
            plan.append(dict(item))
    return plan


def select_day(plan: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    if args.date:
        matches = [item for item in plan if item["date"] == args.date]
    elif args.week is not None or args.day is not None:
        if args.week is None or args.day is None:
            raise SystemExit("--week and --day must be provided together.")
        matches = [
            item
            for item in plan
            if int(item["week"]) == args.week and int(item["day"]) == args.day
        ]
    else:
        today = date.today().isoformat()
        matches = [item for item in plan if item["date"] == today]
        if not matches:
            raise SystemExit(
                f"No plan entry for today ({today}). Pass --week N --day M "
                "or --date YYYY-MM-DD."
            )
    if len(matches) != 1:
        raise SystemExit(f"Expected one matching day, found {len(matches)}.")
    return matches[0]


def with_public_url(item: dict[str, Any], base_url: str) -> dict[str, Any]:
    result = dict(item)
    if base_url:
        result["public_url"] = f"{base_url.rstrip('/')}/{item['page']}"
    page_url = str(result.get("public_url") or "")
    result["internal_resources"] = [
        {
            **resource,
            "url": (
                urljoin(page_url, str(resource["href"]))
                if page_url
                else str(resource["href"])
            ),
        }
        for resource in item.get("internal_resources", [])
    ]
    return result


def render_text(item: dict[str, Any]) -> str:
    lines = [
        f"Week {item['week']} Day {item['day']} · {item['date']}",
        item["title"],
        "",
        "精确时间段：",
    ]
    for block in item["time_blocks"]:
        lines.append(
            f"- {block['time']} · {block['title']}: {block['instruction']}"
        )
    lines.extend(["", "今日源包："])
    for source in item["sources"]:
        lines.append(
            f"- {source['page_title']} · {source['heading']}: {source['url']}"
        )
    if item.get("internal_resources"):
        lines.extend(["", "站内核对："])
        for resource in item["internal_resources"]:
            lines.append(f"- {resource['label']}: {resource['url']}")
    lines.extend(["", f"产出物：{item['artifact']}", "", "验收标准："])
    lines.extend(f"- {criterion}" for criterion in item["acceptance"])
    lines.extend(["", f"修复路径：{item['repair']}", "", "算法三题："])
    for problem in item["algorithms"]["problems"]:
        lines.append(f"- {problem['title']}: {problem['url']}")
    lines.append("")
    lines.append(f"页面：{item.get('public_url') or 'docs/' + item['page']}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Look up the verified 12-week system design plan."
    )
    parser.add_argument("--date", help="Plan date, YYYY-MM-DD.")
    parser.add_argument("--week", type=int, choices=range(1, 13))
    parser.add_argument("--day", type=int, choices=range(1, 8))
    parser.add_argument("--base-url", default="")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    item = with_public_url(
        select_day(load_plan(find_curriculum_root()), args),
        args.base_url,
    )
    if args.format == "json":
        print(json.dumps(item, ensure_ascii=False, indent=2))
    else:
        print(render_text(item))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
