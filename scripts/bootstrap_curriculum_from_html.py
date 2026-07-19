#!/usr/bin/env python3
"""Create transitional curriculum manifests from published daily pages.

Week 1 is authored as the first native Interview Case curriculum. This utility
captures the remaining published weeks as structured data so the Coach no
longer needs to parse HTML at runtime while they are migrated into native cases.
"""

from __future__ import annotations

import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CURRICULUM = ROOT / "curriculum"
LOOKUP = ROOT / "system-design-study-coach" / "scripts" / "plan_lookup.py"


def load_lookup_module():
    spec = importlib.util.spec_from_file_location("plan_lookup", LOOKUP)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load plan_lookup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def to_manifest_day(item: dict) -> dict:
    time_blocks = []
    for key, value in item["rubric"].items():
        if re.match(r"^\d{2}:\d{2}", key):
            time_blocks.append({"time": key, "task": value})
    return {
        "day": item["day"],
        "date": item["date"],
        "title": item["title"],
        "focus": item["eyebrow"].split("·")[-1].strip(),
        "page": item["path"],
        "case_id": "",
        "time_blocks": time_blocks,
        "sources": [
            {
                "title": source["title"],
                "provider": source["label"],
                "url": source["url"],
                "acceptance": source["acceptance"],
            }
            for source in item["sources"]
        ],
        "deliverable": item["rubric"].get("产出物", ""),
        "mastery": item["rubric"].get("必须掌握", ""),
        "repair": item["rubric"].get("修复规则", ""),
        "algorithms": item["algorithms"],
        "source_status": "transitional-generated-from-html"
    }


def main() -> None:
    module = load_lookup_module()
    by_week: dict[int, list[dict]] = defaultdict(list)
    for page in sorted(DOCS.glob("week*/day-*.html")):
        item = module.parse_day(page, DOCS)
        if item["week"] != 1:
            by_week[item["week"]].append(to_manifest_day(item))

    CURRICULUM.mkdir(exist_ok=True)
    for week, days in sorted(by_week.items()):
        if len(days) != 7:
            raise ValueError(f"Week {week} should contain 7 days, found {len(days)}")
        payload = {
            "schema_version": "1.0",
            "week": week,
            "title": f"Week {week} transitional curriculum",
            "source_status": "transitional-generated-from-html",
            "days": sorted(days, key=lambda item: item["day"]),
        }
        path = CURRICULUM / f"week-{week:02}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
