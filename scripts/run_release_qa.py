#!/usr/bin/env python3
"""Run release QA for the cross-agent Hello Interview card skill.

This is stricter than the visual smoke test. It validates the renderer against
multiple Hello Interview chapter styles, short/medium/long content, Chinese and
English output, plus cross-agent plugin packaging invariants.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import run_hello_interview_visual_smoke as smoke


ROOT = Path(__file__).resolve().parents[1]
SMOKE_CASE_DIR = ROOT / "examples" / "hello_interview_smoke_cases"
RELEASE_CASE_DIR = ROOT / "examples" / "hello_interview_release_cases"
DEFAULT_OUT_DIR = Path("/tmp/hello-interview-release-qa")

REQUIRED_LAYOUTS = {"architecture", "comparison", "concept-map", "decision", "modular-composite", "pipeline"}
REQUIRED_CATEGORIES = {
    "advanced-topic",
    "api-design",
    "core-concept",
    "framework",
    "key-technology",
    "pattern",
    "problem-breakdown",
}
REQUIRED_SIZES = {"short", "medium", "long"}
REQUIRED_LANGUAGES = {"Chinese", "English"}
REQUIRED_SOURCE_COMPLETENESS = {"complete", "thin"}
VALID_SOURCE_COMPLETENESS = {"complete", "partial", "thin"}
VALID_COMPLETION_MODES = {"none", "model_background", "researched"}

SMOKE_METADATA: dict[str, dict[str, str]] = {
    "api-design-concept-map.zh.json": {
        "chapter_category": "api-design",
        "content_size": "medium",
        "source_kind": "Hello Interview API design",
    },
    "caching-architecture.zh.json": {
        "chapter_category": "core-concept",
        "content_size": "medium",
        "source_kind": "Hello Interview core concept",
    },
    "cap-comparison.zh.json": {
        "chapter_category": "core-concept",
        "content_size": "medium",
        "source_kind": "Hello Interview core concept",
    },
    "consistent-hashing-map.zh.json": {
        "chapter_category": "core-concept",
        "content_size": "medium",
        "source_kind": "Hello Interview core concept",
    },
    "google-docs-realtime.zh.json": {
        "chapter_category": "problem-breakdown",
        "content_size": "long",
        "source_kind": "Hello Interview problem breakdown",
    },
    "kafka-pipeline.zh.json": {
        "chapter_category": "key-technology",
        "content_size": "medium",
        "source_kind": "Hello Interview key technology",
    },
    "rate-limiter-decision.zh.json": {
        "chapter_category": "problem-breakdown",
        "content_size": "short",
        "source_kind": "Hello Interview problem breakdown",
    },
    "redis-deep-dive-long.zh.json": {
        "chapter_category": "key-technology",
        "content_size": "long",
        "source_kind": "Hello Interview key technology",
    },
    "sharding-pipeline.zh.json": {
        "chapter_category": "core-concept",
        "content_size": "medium",
        "source_kind": "Hello Interview core concept",
    },
    "ticketmaster-architecture.zh.json": {
        "chapter_category": "problem-breakdown",
        "content_size": "long",
        "source_kind": "Hello Interview problem breakdown",
    },
    "ticketmaster-modular-composite.zh.json": {
        "chapter_category": "problem-breakdown",
        "content_size": "long",
        "source_kind": "Hello Interview problem breakdown",
    },
}

REQUIRED_JSON_FILES = [
    ".agents/plugins/marketplace.json",
    ".cursor-plugin/marketplace.json",
    ".claude-plugin/marketplace.json",
    "plugins/sde-interview-script-skill/.codex-plugin/plugin.json",
    "plugins/sde-interview-script-skill/.cursor-plugin/plugin.json",
    "plugins/sde-interview-script-skill/.claude-plugin/plugin.json",
    "plugins/sde-interview-script-skill/.mcp.json",
    "plugins/sde-interview-script-skill/mcp.json",
]

REQUIRED_PATHS = [
    "card/SKILL.md",
    "senior-sde-interview-script/SKILL.md",
    "plugins/sde-interview-script-skill/commands/card.md",
    "plugins/sde-interview-script-skill/skills/card/SKILL.md",
    "plugins/sde-interview-script-skill/skills/senior-sde-interview-script/SKILL.md",
    "scripts/render_interview_card.py",
    "scripts/run_hello_interview_visual_smoke.py",
    "scripts/share_excalidraw.mjs",
]

RENDERER_COPIES = [
    "card/scripts/render_interview_card.py",
    "senior-sde-interview-script/scripts/render_interview_card.py",
    "plugins/sde-interview-script-skill/skills/card/scripts/render_interview_card.py",
    "plugins/sde-interview-script-skill/skills/senior-sde-interview-script/scripts/render_interview_card.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run release QA for the SDE interview card skill.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR, help="Rendered output directory.")
    parser.add_argument(
        "--renderer",
        type=Path,
        default=ROOT / "scripts" / "render_interview_card.py",
        help="Renderer script to test.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def metadata_for(case_path: Path, fixture: dict[str, Any]) -> dict[str, str]:
    metadata = fixture.get("qa")
    if isinstance(metadata, dict):
        return {str(key): str(value) for key, value in metadata.items()}
    if case_path.name in SMOKE_METADATA:
        return SMOKE_METADATA[case_path.name]
    raise AssertionError(f"{case_path.name}: missing release QA metadata")


def validate_case_metadata(case_path: Path, fixture: dict[str, Any], metadata: dict[str, str]) -> None:
    for key in ("chapter_category", "content_size", "source_kind"):
        if not metadata.get(key):
            raise AssertionError(f"{case_path.name}: metadata missing {key}")
    if metadata["content_size"] not in REQUIRED_SIZES:
        raise AssertionError(f"{case_path.name}: invalid content_size {metadata['content_size']!r}")
    if metadata["chapter_category"] not in REQUIRED_CATEGORIES:
        raise AssertionError(f"{case_path.name}: invalid chapter_category {metadata['chapter_category']!r}")

    layout = str(fixture.get("layout") or "")
    expected_layout = metadata.get("expected_layout")
    if expected_layout and expected_layout != layout:
        raise AssertionError(f"{case_path.name}: expected layout {expected_layout}, got {layout}")

    if not fixture.get("summary") or not fixture.get("task") or not fixture.get("constraints"):
        raise AssertionError(f"{case_path.name}: summary, task, and constraints are required")
    if len(fixture.get("blocks") or []) < 4:
        raise AssertionError(f"{case_path.name}: release fixtures need at least four board blocks")

    block_count = len(fixture.get("blocks") or [])
    size = metadata["content_size"]
    if size == "short" and block_count > 5:
        raise AssertionError(f"{case_path.name}: short case has too many blocks: {block_count}")
    if size == "long" and block_count < 6:
        raise AssertionError(f"{case_path.name}: long case is too small: {block_count} blocks")

    source_notes = fixture.get("source_notes")
    completeness = metadata.get("source_completeness", "complete")
    completion_mode = metadata.get("completion_mode", "none")
    if completeness not in VALID_SOURCE_COMPLETENESS:
        raise AssertionError(f"{case_path.name}: invalid source_completeness {completeness!r}")
    if completion_mode not in VALID_COMPLETION_MODES:
        raise AssertionError(f"{case_path.name}: invalid completion_mode {completion_mode!r}")

    if completeness == "complete":
        return
    if not isinstance(source_notes, dict):
        raise AssertionError(f"{case_path.name}: partial/thin cases must include source_notes")
    if str(source_notes.get("completeness") or "") != completeness:
        raise AssertionError(f"{case_path.name}: source_notes completeness does not match QA metadata")
    if str(source_notes.get("completion_mode") or "") != completion_mode:
        raise AssertionError(f"{case_path.name}: source_notes completion_mode does not match QA metadata")
    added_points = source_notes.get("added_points")
    if not isinstance(added_points, list) or len(added_points) < 2:
        raise AssertionError(f"{case_path.name}: partial/thin cases need at least two added_points")


def absolute_points(element: dict[str, Any]) -> list[list[float]]:
    x = float(element.get("x", 0))
    y = float(element.get("y", 0))
    points = element.get("points") or [[0, 0], [element.get("width", 0), element.get("height", 0)]]
    return [[x + float(point[0]), y + float(point[1])] for point in points]


def rect_to_axis_segment_distance(
    rect: tuple[float, float, float, float],
    p1: list[float],
    p2: list[float],
) -> float:
    left, top, right, bottom = rect
    x1, y1 = p1
    x2, y2 = p2
    if abs(y1 - y2) < 0.001:
        seg_left, seg_right = sorted((x1, x2))
        dx = 0.0 if max(left, seg_left) <= min(right, seg_right) else min(abs(left - seg_right), abs(right - seg_left))
        dy = 0.0 if top <= y1 <= bottom else min(abs(top - y1), abs(bottom - y1))
        return math.hypot(dx, dy)
    if abs(x1 - x2) < 0.001:
        seg_top, seg_bottom = sorted((y1, y2))
        dx = 0.0 if left <= x1 <= right else min(abs(left - x1), abs(right - x1))
        dy = 0.0 if max(top, seg_top) <= min(bottom, seg_bottom) else min(abs(top - seg_bottom), abs(bottom - seg_top))
        return math.hypot(dx, dy)
    center_x = (left + right) / 2
    center_y = (top + bottom) / 2
    return min(math.hypot(center_x - x1, center_y - y1), math.hypot(center_x - x2, center_y - y2))


def validate_release_scene(case_path: Path, excalidraw_path: Path, preview_path: Path) -> None:
    scene = load_json(excalidraw_path)
    _, canvas_height = smoke.svg_size(preview_path)
    max_bottom = 0.0
    connectors: dict[tuple[str, str], dict[str, Any]] = {}
    labels: list[dict[str, Any]] = []

    for element in scene.get("elements", []):
        bounds = smoke.element_bounds(element)
        if bounds:
            max_bottom = max(max_bottom, bounds[3])
        custom = element.get("customData") or {}
        if custom.get("role") == "connector":
            connectors[(str(custom.get("from") or ""), str(custom.get("to") or ""))] = element
        if custom.get("role") == "connector_label":
            labels.append(element)

    if canvas_height - max_bottom < 58:
        raise AssertionError(
            f"{case_path.name}: bottom padding too small: canvas={canvas_height}, max_bottom={max_bottom:.1f}",
        )

    for label in labels:
        custom = label.get("customData") or {}
        key = (str(custom.get("from") or ""), str(custom.get("to") or ""))
        connector = connectors.get(key)
        if not connector:
            continue
        bounds = smoke.element_bounds(label)
        if not bounds:
            continue
        points = absolute_points(connector)
        distance = min(
            rect_to_axis_segment_distance(bounds, points[index], points[index + 1])
            for index in range(len(points) - 1)
        )
        if distance > 72:
            raise AssertionError(
                f"{case_path.name}: connector label {key[0]}->{key[1]} is too far from its line: {distance:.1f}px",
            )


def validate_packaging() -> None:
    for path_text in REQUIRED_PATHS:
        path = ROOT / path_text
        if not path.exists():
            raise AssertionError(f"Missing required release path: {path_text}")
    for path_text in REQUIRED_JSON_FILES:
        path = ROOT / path_text
        load_json(path)

    canonical = (ROOT / "scripts/render_interview_card.py").read_bytes()
    for copy_text in RENDERER_COPIES:
        copy_path = ROOT / copy_text
        if copy_path.read_bytes() != canonical:
            raise AssertionError(f"Renderer copy is out of sync: {copy_text}")


def compile_python() -> None:
    paths = [
        ROOT / "scripts/render_interview_card.py",
        ROOT / "scripts/run_hello_interview_visual_smoke.py",
        ROOT / "scripts/run_release_qa.py",
        *(ROOT / copy for copy in RENDERER_COPIES),
    ]
    env = dict(os.environ)
    env.setdefault("PYTHONPYCACHEPREFIX", "/tmp/sde-skill-pycache")
    subprocess.run([sys.executable, "-m", "py_compile", *(str(path) for path in paths)], check=True, env=env)


def run_release_cases(out_dir: Path, renderer: Path) -> None:
    case_paths = sorted(SMOKE_CASE_DIR.glob("*.json")) + sorted(RELEASE_CASE_DIR.glob("*.json"))
    if not case_paths:
        raise AssertionError("No release QA fixtures found")

    layouts: set[str] = set()
    categories: set[str] = set()
    sizes: set[str] = set()
    languages: set[str] = set()
    source_completeness: set[str] = set()
    print(f"Release QA rendering {len(case_paths)} fixtures into {out_dir}")

    for case_path in case_paths:
        fixture = load_json(case_path)
        metadata = metadata_for(case_path, fixture)
        validate_case_metadata(case_path, fixture, metadata)

        layout, counts, preview = smoke.run_case(case_path, out_dir, renderer)
        slug = case_path.stem.replace(".", "-")
        case_out = out_dir / slug
        validate_release_scene(case_path, case_out / f"{slug}.excalidraw", Path(preview))

        layouts.add(layout)
        categories.add(metadata["chapter_category"])
        sizes.add(metadata["content_size"])
        languages.add(str(fixture.get("language") or ""))
        source_completeness.add(metadata.get("source_completeness", "complete"))
        compact_counts = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
        print(
            f"PASS {case_path.name} "
            f"[{metadata['chapter_category']}/{metadata['content_size']}/{layout}] "
            f"{compact_counts}",
        )

    missing_layouts = REQUIRED_LAYOUTS - layouts
    missing_categories = REQUIRED_CATEGORIES - categories
    missing_sizes = REQUIRED_SIZES - sizes
    missing_languages = REQUIRED_LANGUAGES - languages
    missing_source_completeness = REQUIRED_SOURCE_COMPLETENESS - source_completeness
    if missing_layouts:
        raise AssertionError(f"Missing release layout coverage: {sorted(missing_layouts)}")
    if missing_categories:
        raise AssertionError(f"Missing Hello Interview category coverage: {sorted(missing_categories)}")
    if missing_sizes:
        raise AssertionError(f"Missing content size coverage: {sorted(missing_sizes)}")
    if missing_languages:
        raise AssertionError(f"Missing language coverage: {sorted(missing_languages)}")
    if missing_source_completeness:
        raise AssertionError(f"Missing source-completeness coverage: {sorted(missing_source_completeness)}")

    print("Release matrix:")
    print(f"  layouts: {', '.join(sorted(layouts))}")
    print(f"  categories: {', '.join(sorted(categories))}")
    print(f"  sizes: {', '.join(sorted(sizes))}")
    print(f"  languages: {', '.join(sorted(languages))}")
    print(f"  source completeness: {', '.join(sorted(source_completeness))}")


def main() -> None:
    args = parse_args()
    validate_packaging()
    compile_python()
    run_release_cases(args.out, args.renderer)
    print("RELEASE_QA_PASS")


if __name__ == "__main__":
    main()
