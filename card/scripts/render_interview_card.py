#!/usr/bin/env python3
"""Render a senior SDE interview script card as Excalidraw + preview image.

The agent supplies already-summarized content as JSON. This script is purposely
dependency-light so Codex, Cursor, and Claude Code can all run it after clone.
It always writes a preview SVG and a .excalidraw file. If Node.js and network
access are available, it also creates an excalidraw.com share link.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


HANDWRITING_FONT = (
    "Excalifont,Xiaolai,HanziPen SC,HanziPen TC,Kaiti SC,KaiTi,"
    "Bradley Hand,Comic Sans MS,cursive,sans-serif"
)

DIAGRAM_FONT = (
    "Comic Shanns,Excalifont,Xiaolai,HanziPen SC,HanziPen TC,Kaiti SC,"
    "Comic Sans MS,cursive,monospace"
)

PLUS_STYLE_ALIASES = {
    "plus",
    "excalidraw-plus",
    "excalidraw_plus",
    "whiteboard",
    "interview-whiteboard",
    "reference",
}

PLUS_BLUE = "#a5d8ff"
PLUS_STROKE = "#1e1e1e"
PLUS_PINK = "#fcc2d7"
PLUS_YELLOW = "#fffbe6"
PLUS_GREEN = "#f1fcf3"
PLUS_MINT = "#eef8ff"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render an interview answer card from structured JSON content.",
    )
    parser.add_argument(
        "--content",
        required=True,
        help="Path to JSON content file, or '-' to read JSON from stdin.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory. Defaults to /tmp/sde-interview-card-<timestamp>.",
    )
    parser.add_argument("--slug", default="interview-card", help="Output filename slug.")
    parser.add_argument(
        "--no-share",
        action="store_true",
        help="Skip uploading to excalidraw.com.",
    )
    return parser.parse_args()


def load_content(path: str) -> dict[str, Any]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    if data.get("blocks") or data.get("nodes"):
        data["blocks"] = data.get("blocks") or data.get("nodes") or []
        data["connectors"] = data.get("connectors") or []
        data["callouts"] = data.get("callouts") or []
        data.setdefault("title", "Script Card")
        data.setdefault("summary", "")
        data.setdefault("layout", "auto")
        return data
    required = ["title", "summary", "script", "short", "flows"]
    missing = [key for key in required if not data.get(key)]
    if missing:
        raise SystemExit(f"Missing required content fields: {', '.join(missing)}")
    if not isinstance(data["flows"], list):
        raise SystemExit("content.flows must be a list")
    flows = [str(item) for item in data["flows"][:4]]
    while len(flows) < 4:
        flows.append("")
    data["flows"] = flows
    return data


def token_width(token: str, size: int) -> float:
    width = 0.0
    for char in token:
        code = ord(char)
        if char.isspace():
            width += size * 0.32
        elif 0x3400 <= code <= 0x9FFF:
            width += size * 0.98
        elif char in "`.,;:/|!()[]{}":
            width += size * 0.35
        else:
            width += size * 0.56
    return width


def tokenize(text: str) -> list[str]:
    return re.findall(
        r"`[^`]+`|[A-Za-z0-9_./?=&{}:#()+-]+|[\u3400-\u9fff]|\s+|[^\sA-Za-z0-9_./?=&{}:#()+\-\u3400-\u9fff`]",
        text,
    )


def wrap_paragraph(paragraph: str, size: int, max_width: int) -> list[str]:
    lines: list[str] = []
    line = ""
    line_width = 0.0
    for token in tokenize(paragraph):
        token = " " if token.isspace() else token
        width = token_width(token, size)
        if line and line_width + width > max_width:
            lines.append(line.rstrip())
            line = token.lstrip()
            line_width = token_width(line, size)
        else:
            line += token
            line_width += width

        while line_width > max_width and len(line) > 1:
            acc = ""
            acc_width = 0.0
            rest_start = 0
            for idx, char in enumerate(line):
                char_width = token_width(char, size)
                if acc and acc_width + char_width > max_width:
                    rest_start = idx
                    break
                acc += char
                acc_width += char_width
            else:
                break
            lines.append(acc.rstrip())
            line = line[rest_start:].lstrip()
            line_width = token_width(line, size)
    if line.strip():
        lines.append(line.rstrip())
    fixed: list[str] = []
    orphan_punctuation = set("。，、；：！？,.!?;:")
    for item in lines:
        if fixed and item.strip() in orphan_punctuation:
            fixed[-1] = fixed[-1] + item.strip()
        else:
            fixed.append(item)
    return fixed


def wrap_text(text: str, size: int, max_width: int) -> list[str | None]:
    wrapped: list[str | None] = []
    paragraphs = text.split("\n")
    for idx, paragraph in enumerate(paragraphs):
        if paragraph:
            wrapped.extend(wrap_paragraph(paragraph, size, max_width))
        else:
            wrapped.append(None)
        if idx != len(paragraphs) - 1:
            wrapped.append(None)
    return wrapped


def text_block_svg(
    text: str,
    size: int,
    max_width: int,
    color: str,
    line_gap: int,
    paragraph_gap: int,
    font_family: str = HANDWRITING_FONT,
    align: str = "left",
) -> dict[str, Any]:
    lines = wrap_text(text, size, max_width)
    line_height = int(size * 1.26) + line_gap
    y = int(size * 1.1)
    text_nodes: list[str] = []
    max_line_width = 1.0
    centered = align == "center"
    svg_width = max_width + 8
    text_x = svg_width / 2 if centered else 0
    anchor = ' text-anchor="middle"' if centered else ""
    for line in lines:
        if line is None:
            y += paragraph_gap
            continue
        max_line_width = max(max_line_width, token_width(line, size))
        text_nodes.append(
            f'<text x="{text_x}" y="{y}" font-size="{size}" fill="{color}" '
            f'font-family="{font_family}"{anchor}>{html.escape(line)}</text>'
        )
        y += line_height
    width = svg_width if centered else min(max_width + 8, int(math.ceil(max_line_width)) + 10)
    height = max(1, y - int(size * 0.3))
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">' + "".join(text_nodes) + "</svg>"
    )
    data_url = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode(
        "ascii",
    )
    return {"dataURL": data_url, "width": width, "height": height, "svg": svg}


def rich_text_block_svg(
    title: str,
    body: str,
    max_width: int,
    color: str,
    title_size: int = 30,
    body_size: int = 26,
    align: str = "left",
    font_family: str = HANDWRITING_FONT,
) -> dict[str, Any]:
    title_lines = wrap_text(title, title_size, max_width) if title else []
    body_lines = wrap_text(body, body_size, max_width) if body else []
    y = int(title_size * 1.05)
    text_nodes: list[str] = []
    max_line_width = 1.0
    centered = align == "center"
    svg_width = max_width + 8
    text_x = svg_width / 2 if centered else 0
    anchor = ' text-anchor="middle"' if centered else ""
    for line in title_lines:
        if line is None:
            y += int(title_size * 0.65)
            continue
        max_line_width = max(max_line_width, token_width(line, title_size))
        text_nodes.append(
            f'<text x="{text_x}" y="{y}" font-size="{title_size}" font-weight="700" '
            f'fill="{color}" font-family="{font_family}"{anchor}>{html.escape(line)}</text>'
        )
        y += int(title_size * 1.45)
    if title_lines and body_lines:
        y += 8
    for line in body_lines:
        if line is None:
            y += int(body_size * 0.85)
            continue
        max_line_width = max(max_line_width, token_width(line, body_size))
        text_nodes.append(
            f'<text x="{text_x}" y="{y}" font-size="{body_size}" fill="{color}" '
            f'font-family="{font_family}"{anchor}>{html.escape(line)}</text>'
        )
        y += int(body_size * 1.58)
    width = svg_width if centered else min(max_width + 8, int(math.ceil(max_line_width)) + 10)
    height = max(1, y - int(body_size * 0.25))
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">' + "".join(text_nodes) + "</svg>"
    )
    data_url = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode(
        "ascii",
    )
    return {"dataURL": data_url, "width": width, "height": height, "svg": svg}


def element_id(rng: random.Random, prefix: str) -> str:
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    return f"{prefix}_" + "".join(rng.choice(chars) for _ in range(16))


def base_element(
    rng: random.Random,
    el_type: str,
    x: float,
    y: float,
    width: float,
    height: float,
    now: int,
) -> dict[str, Any]:
    return {
        "id": element_id(rng, el_type),
        "type": el_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": "#1f2937",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 2,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 3},
        "seed": rng.randint(1, 2**31 - 1),
        "version": 1,
        "versionNonce": rng.randint(1, 2**31 - 1),
        "isDeleted": False,
        "boundElements": None,
        "updated": now,
        "link": None,
        "locked": False,
    }


def rectangle(
    rng: random.Random,
    x: float,
    y: float,
    width: float,
    height: float,
    stroke: str,
    stroke_width: int,
    now: int,
    background: str = "transparent",
    stroke_style: str = "solid",
) -> dict[str, Any]:
    element = base_element(rng, "rectangle", x, y, width, height, now)
    element.update(
        {
            "strokeColor": stroke,
            "backgroundColor": background,
            "strokeWidth": stroke_width,
            "strokeStyle": stroke_style,
        },
    )
    return element


def diamond(
    rng: random.Random,
    x: float,
    y: float,
    width: float,
    height: float,
    stroke: str,
    stroke_width: int,
    now: int,
    background: str = "transparent",
) -> dict[str, Any]:
    element = base_element(rng, "diamond", x, y, width, height, now)
    element.update(
        {
            "strokeColor": stroke,
            "backgroundColor": background,
            "strokeWidth": stroke_width,
        },
    )
    return element


def ellipse(
    rng: random.Random,
    x: float,
    y: float,
    width: float,
    height: float,
    stroke: str,
    stroke_width: int,
    now: int,
    background: str = "transparent",
) -> dict[str, Any]:
    element = base_element(rng, "ellipse", x, y, width, height, now)
    element.update(
        {
            "strokeColor": stroke,
            "backgroundColor": background,
            "strokeWidth": stroke_width,
        },
    )
    return element


def image_element(
    rng: random.Random,
    key: str,
    block: dict[str, Any],
    x: float,
    y: float,
    now: int,
) -> tuple[dict[str, Any], str]:
    file_id = f"{key}_{element_id(rng, 'file')}"
    element = base_element(rng, "image", x, y, block["width"], block["height"], now)
    element.update(
        {
            "strokeColor": "transparent",
            "backgroundColor": "transparent",
            "roundness": None,
            "fileId": file_id,
            "scale": [1, 1],
            "status": "saved",
            "crop": None,
        },
    )
    return element, file_id


def arrow(
    rng: random.Random,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    now: int,
    stroke: str = "#2563eb",
    stroke_width: int = 3,
) -> dict[str, Any]:
    element = base_element(rng, "arrow", x1, y1, x2 - x1, y2 - y1, now)
    element.update(
        {
            "strokeColor": stroke,
            "backgroundColor": "transparent",
            "roundness": None,
            "points": [[0, 0], [x2 - x1, y2 - y1]],
            "lastCommittedPoint": None,
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": None,
            "endArrowhead": "arrow",
            "strokeWidth": stroke_width,
        },
    )
    return element


def routed_arrow(
    rng: random.Random,
    points: list[list[float]],
    now: int,
    stroke: str = "#2563eb",
    stroke_width: int = 3,
) -> dict[str, Any]:
    if len(points) < 2:
        raise ValueError("routed arrows require at least two points")
    x1, y1 = points[0]
    x2, y2 = points[-1]
    element = base_element(rng, "arrow", x1, y1, x2 - x1, y2 - y1, now)
    element.update(
        {
            "strokeColor": stroke,
            "backgroundColor": "transparent",
            "roundness": None,
            "points": [[px - x1, py - y1] for px, py in points],
            "lastCommittedPoint": None,
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": None,
            "endArrowhead": "arrow",
            "strokeWidth": stroke_width,
        },
    )
    return element


def add_image_block(
    elements: list[dict[str, Any]],
    files: dict[str, Any],
    rng: random.Random,
    key: str,
    block: dict[str, Any],
    x: float,
    y: float,
    now: int,
) -> None:
    element, file_id = image_element(rng, key, block, x, y, now)
    elements.append(element)
    files[file_id] = {
        "id": file_id,
        "mimeType": "image/svg+xml",
        "dataURL": block["dataURL"],
        "created": now,
    }


def svg_data_block(svg: str, width: int, height: int) -> dict[str, Any]:
    data_url = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return {"dataURL": data_url, "width": width, "height": height, "svg": svg}


def component_icon_svg(kind: str, label: str = "", size: int = 72) -> dict[str, Any]:
    kind = (kind or "service").lower()
    palette = {
        "api": ("#e64980", "API"),
        "gateway": ("#e64980", "API"),
        "lambda": ("#fd7e14", "λ"),
        "compute": ("#fd7e14", "λ"),
        "storage": ("#40c057", "S3"),
        "s3": ("#40c057", "S3"),
        "database": ("#4c6ef5", "DB"),
        "db": ("#4c6ef5", "DB"),
        "dynamodb": ("#4c6ef5", "DB"),
        "cache": ("#37b24d", "C"),
        "queue": ("#7950f2", "Q"),
        "cdn": ("#228be6", "CDN"),
        "client": ("#74c0fc", "U"),
        "user": ("#74c0fc", "U"),
        "service": ("#4dabf7", "S"),
    }
    bg, default_text = palette.get(kind, palette["service"])
    text = (label or default_text)[:4]
    radius = 9
    mark = ""
    if kind in {"database", "db", "dynamodb"}:
        mark = (
            '<ellipse cx="36" cy="24" rx="19" ry="8" fill="none" stroke="#fff" stroke-width="4"/>'
            '<path d="M17 24v22c0 5 8 9 19 9s19-4 19-9V24" fill="none" stroke="#fff" stroke-width="4"/>'
            '<path d="M17 36c0 5 8 9 19 9s19-4 19-9" fill="none" stroke="#fff" stroke-width="3"/>'
        )
        text = ""
    elif kind in {"storage", "s3"}:
        mark = (
            '<path d="M21 24h31l-3 33H24z" fill="none" stroke="#fff" stroke-width="4" stroke-linejoin="round"/>'
            '<path d="M25 24c2-5 20-5 23 0" fill="none" stroke="#fff" stroke-width="4"/>'
        )
        text = ""
    elif kind in {"queue"}:
        mark = (
            '<path d="M19 22h34M19 36h34M19 50h34" stroke="#fff" stroke-width="5" stroke-linecap="round"/>'
        )
        text = ""
    elif kind in {"cache"}:
        mark = '<path d="M39 12L22 39h16l-5 22 18-31H35z" fill="none" stroke="#fff" stroke-width="5" stroke-linejoin="round"/>'
        text = ""
    elif kind in {"client", "user"}:
        mark = (
            '<circle cx="36" cy="25" r="10" fill="none" stroke="#fff" stroke-width="4"/>'
            '<path d="M18 58c4-14 32-14 36 0" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round"/>'
        )
        text = ""
    if text:
        mark = (
            f'<text x="36" y="45" text-anchor="middle" font-family="{DIAGRAM_FONT}" '
            f'font-size="22" font-weight="700" fill="#fff">{html.escape(text)}</text>'
        )
    caption = html.escape(label) if label and label != text else ""
    caption_node = (
        f'<text x="36" y="88" text-anchor="middle" font-family="{DIAGRAM_FONT}" '
        f'font-size="12" fill="#1e1e1e">{caption}</text>'
        if caption
        else ""
    )
    height = size + (22 if caption else 0)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{height}" viewBox="0 0 72 {72 + (22 if caption else 0)}">'
        f'<rect x="6" y="6" width="60" height="60" rx="{radius}" fill="{bg}"/>'
        f'{mark}{caption_node}</svg>'
    )
    return svg_data_block(svg, size, height)


def dimension(value: Any, default: float, total: float) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if 0 < number <= 1:
        return number * total
    return number


def block_kind(block: dict[str, Any]) -> str:
    return str(block.get("kind") or block.get("type") or block.get("shape") or "concept").lower()


def block_shape(block: dict[str, Any], allow_diamond: bool = True) -> str:
    shape = str(block.get("shape") or "").lower()
    kind = block_kind(block)
    if allow_diamond and (shape in {"diamond", "decision"} or kind in {"decision", "question", "choice"}):
        return "diamond"
    if shape in {"ellipse", "circle", "oval"} or kind in {"client", "actor", "user"}:
        return "ellipse"
    return "rectangle"


def block_stroke(block: dict[str, Any]) -> str:
    kind = block_kind(block)
    if kind in {"warning", "risk", "caveat", "anti-pattern"}:
        return "#b91c1c"
    if kind in {"note", "talk", "talk_track", "example"}:
        return "#111827"
    return "#2563eb"


def normalize_style(content: dict[str, Any]) -> str:
    return str(content.get("style") or content.get("visual_style") or "").strip().lower()


def is_plus_style(content: dict[str, Any]) -> bool:
    style = normalize_style(content)
    if not style and (content.get("task") or content.get("constraints")):
        return True
    return style in PLUS_STYLE_ALIASES


def plus_block_fill(block: dict[str, Any], index: int = 0) -> str:
    if block.get("fill") is not None:
        return str(block.get("fill"))
    if block.get("background") is not None:
        return str(block.get("background"))
    kind = block_kind(block)
    if kind in {"note", "callout", "question", "followup", "follow-up", "interviewer"}:
        return PLUS_PINK
    if kind in {"caveat", "risk", "tradeoff", "trade-off", "warning"}:
        return PLUS_YELLOW
    if kind in {"answer", "principle", "takeaway", "conclusion"}:
        return PLUS_GREEN
    if kind in {"frame", "task", "constraints", "section"}:
        return "transparent"
    if kind in {"annotation", "hint"}:
        return PLUS_MINT
    return PLUS_BLUE


def plus_block_stroke(block: dict[str, Any]) -> str:
    return str(block.get("stroke") or PLUS_STROKE)


def plus_text_color(block: dict[str, Any]) -> str:
    return str(block.get("textColor") or block.get("text_color") or PLUS_STROKE)


def coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    if isinstance(value, dict):
        parts = []
        if value.get("title"):
            parts.append(str(value["title"]))
        body = value.get("body") or value.get("text") or value.get("items")
        if isinstance(body, list):
            parts.extend(str(item) for item in body)
        elif body:
            parts.append(str(body))
        return "\n".join(parts)
    return str(value)


def normalize_block(raw: Any, index: int) -> dict[str, Any]:
    if isinstance(raw, str):
        return {"id": f"b{index}", "title": raw, "body": "", "kind": "concept"}
    block = dict(raw)
    block.setdefault("id", f"b{index}")
    if "body" not in block:
        block["body"] = block.get("text") or block.get("description") or ""
    block.setdefault("title", block.get("label") or f"Block {index + 1}")
    return block


def auto_positions(
    blocks: list[dict[str, Any]],
    layout: str,
    top: float,
    canvas_width: float,
) -> dict[str, tuple[float, float, float, float]]:
    positions: dict[str, tuple[float, float, float, float]] = {}
    margin = 80
    content_width = canvas_width - 2 * margin
    layout = layout.lower()
    if layout in {"comparison", "tradeoff", "compare"}:
        left_x = margin
        right_x = margin + content_width / 2 + 40
        col_w = content_width / 2 - 40
        left_y = top
        right_y = top
        left_count = 0
        right_count = 0
        for index, block in enumerate(blocks):
            lane = str(block.get("lane") or block.get("side") or "").lower()
            choose_right = lane in {"right", "ap", "availability", "option-b"} or (
                not lane and index % 2 == 1
            )
            x = right_x if choose_right else left_x
            y = right_y if choose_right else left_y
            h = dimension(block.get("height"), 230, 900)
            positions[str(block["id"])] = (x, y, col_w, h)
            if choose_right:
                right_y += h + 42
                right_count += 1
            else:
                left_y += h + 42
                left_count += 1
        return positions

    if layout in {"decision", "decision-tree", "decision_tree"} and blocks:
        first = blocks[0]
        positions[str(first["id"])] = (margin + 520, top, 560, 260)
        branches = blocks[1:4]
        branch_w = 430 if len(branches) == 3 else 520
        gap = (content_width - len(branches) * branch_w) / max(1, len(branches) - 1)
        branch_y = top + 340
        for index, block in enumerate(branches):
            positions[str(block["id"])] = (margin + index * (branch_w + gap), branch_y, branch_w, 250)
        rest_y = branch_y + 330
        for index, block in enumerate(blocks[4:]):
            positions[str(block["id"])] = (margin + (index % 2) * 820, rest_y + (index // 2) * 290, 760, 230)
        return positions

    if layout in {"pipeline", "flow", "sequence"}:
        block_w = 440 if len(blocks) <= 3 else 360
        block_h = 225
        gap = 58
        max_cols = max(1, min(4, int((content_width + gap) // (block_w + gap))))
        start_x = margin + max(0, (content_width - min(len(blocks), max_cols) * block_w - (min(len(blocks), max_cols) - 1) * gap) / 2)
        for index, block in enumerate(blocks):
            row = index // max_cols
            col = index % max_cols
            row_count = min(max_cols, len(blocks) - row * max_cols)
            row_start_x = margin + max(0, (content_width - row_count * block_w - (row_count - 1) * gap) / 2)
            positions[str(block["id"])] = (
                row_start_x + col * (block_w + gap),
                top + row * 330,
                block_w,
                dimension(block.get("height"), block_h, 900),
            )
        return positions

    if layout in {"architecture", "system", "system-design"}:
        rows: dict[str, list[dict[str, Any]]] = {"top": [], "middle": [], "bottom": []}
        for index, block in enumerate(blocks):
            lane = str(block.get("lane") or block.get("tier") or "").lower()
            kind = block_kind(block)
            if lane in rows:
                rows[lane].append(block)
            elif kind in {"client", "actor", "user", "frontend", "edge"}:
                rows["top"].append(block)
            elif kind in {"db", "database", "cache", "queue", "store", "data"}:
                rows["bottom"].append(block)
            else:
                rows["middle"].append(block)
        if not rows["middle"] and rows["bottom"]:
            rows["middle"], rows["bottom"] = rows["bottom"], rows["middle"]
        y_by_row = {"top": top, "middle": top + 310, "bottom": top + 620}
        for row_name, row_blocks in rows.items():
            if not row_blocks:
                continue
            gap = 58
            block_w = min(430, (content_width - gap * (len(row_blocks) - 1)) / max(1, len(row_blocks)))
            block_w = max(320, block_w)
            total_w = len(row_blocks) * block_w + (len(row_blocks) - 1) * gap
            start_x = margin + max(0, (content_width - total_w) / 2)
            for index, block in enumerate(row_blocks):
                positions[str(block["id"])] = (
                    start_x + index * (block_w + gap),
                    y_by_row[row_name],
                    block_w,
                    dimension(block.get("height"), 225, 900),
                )
        return positions

    if layout in {"map", "concept", "concept-map", "concept_map"} and len(blocks) >= 3:
        positions[str(blocks[0]["id"])] = (margin + 580, top + 130, 440, 240)
        ring = blocks[1:]
        coords = [
            (margin, top, 430, 220),
            (margin + 1130, top, 430, 220),
            (margin, top + 360, 430, 220),
            (margin + 1130, top + 360, 430, 220),
            (margin + 560, top + 520, 480, 220),
        ]
        for block, pos in zip(ring, coords):
            positions[str(block["id"])] = pos
        return positions

    cols = min(4, max(1, len(blocks)))
    if len(blocks) > 4:
        cols = 3
    gap = 54
    block_w = (content_width - gap * (cols - 1)) / cols
    block_h = 245
    for index, block in enumerate(blocks):
        row = index // cols
        col = index % cols
        positions[str(block["id"])] = (
            margin + col * (block_w + gap),
            top + row * (block_h + 82),
            block_w,
            dimension(block.get("height"), block_h, 900),
        )
    return positions


def block_center(pos: tuple[float, float, float, float]) -> tuple[float, float]:
    x, y, w, h = pos
    return x + w / 2, y + h / 2


def localized_talk_label(language: str) -> str:
    normalized = language.lower()
    if "chinese" in normalized or "中文" in normalized or "zh" in normalized:
        return "面试可讲"
    if "spanish" in normalized or "español" in normalized:
        return "Como decirlo"
    return "Say this"


def connector_points(
    src: tuple[float, float, float, float],
    dst: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    sx, sy, sw, sh = src
    dx, dy, dw, dh = dst
    scx, scy = sx + sw / 2, sy + sh / 2
    dcx, dcy = dx + dw / 2, dy + dh / 2
    delta_x = dcx - scx
    delta_y = dcy - scy
    if abs(delta_x) >= abs(delta_y):
        start_x = sx + (sw if delta_x >= 0 else 0)
        end_x = dx + (0 if delta_x >= 0 else dw)
        return start_x, scy, end_x, dcy
    start_y = sy + (sh if delta_y >= 0 else 0)
    end_y = dy + (0 if delta_y >= 0 else dh)
    return scx, start_y, dcx, end_y


def orthogonal_points(
    src: tuple[float, float, float, float],
    dst: tuple[float, float, float, float],
) -> list[list[float]]:
    x1, y1, x2, y2 = connector_points(src, dst)
    if abs(x2 - x1) >= abs(y2 - y1):
        mid_x = x1 + (x2 - x1) / 2
        return [[x1, y1], [mid_x, y1], [mid_x, y2], [x2, y2]]
    mid_y = y1 + (y2 - y1) / 2
    return [[x1, y1], [x1, mid_y], [x2, mid_y], [x2, y2]]


def centered_right_angle_points(
    src: tuple[float, float, float, float],
    dst: tuple[float, float, float, float],
) -> list[list[float]]:
    sx, sy, sw, sh = src
    dx, dy, dw, _ = dst
    start_x = sx + sw / 2
    start_y = sy + sh
    end_x = dx + dw / 2
    end_y = dy
    mid_y = start_y + max(36, (end_y - start_y) / 2)
    if abs(start_x - end_x) < 4:
        return [[start_x, start_y], [end_x, end_y]]
    return [[start_x, start_y], [start_x, mid_y], [end_x, mid_y], [end_x, end_y]]


def add_top_frame(
    elements: list[dict[str, Any]],
    files: dict[str, Any],
    blocks_svg: dict[str, Any],
    rng: random.Random,
    key: str,
    title: str,
    body: str,
    x: float,
    y: float,
    w: float,
    h: float,
    now: int,
) -> None:
    elements.append(
        rectangle(
            rng,
            x,
            y,
            w,
            h,
            PLUS_STROKE,
            2,
            now,
            background="transparent",
            stroke_style="dashed",
        ),
    )
    title_width = min(330, max(230, int(w * 0.38)))
    body_width = max(220, int(w - title_width - 62))
    title_size = 36 if len(title) > 8 else 42
    title_block = text_block_svg(title, title_size, title_width, PLUS_STROKE, 8, 14, DIAGRAM_FONT)
    body_block = text_block_svg(body, 24, body_width, PLUS_STROKE, 7, 12, DIAGRAM_FONT)
    blocks_svg[f"{key}_title"] = title_block
    blocks_svg[f"{key}_body"] = body_block
    add_image_block(elements, files, rng, f"{key}_title", title_block, x + 44, y + max(24, (h - title_block["height"]) / 2), now)
    add_image_block(elements, files, rng, f"{key}_body", body_block, x + title_width + 48, y + max(22, (h - body_block["height"]) / 2), now)


def add_whiteboard_text(
    elements: list[dict[str, Any]],
    files: dict[str, Any],
    blocks_svg: dict[str, Any],
    rng: random.Random,
    key: str,
    text: str,
    x: float,
    y: float,
    max_width: int,
    size: int,
    now: int,
    color: str = PLUS_STROKE,
    align: str = "center",
) -> dict[str, Any]:
    block = text_block_svg(text, size, max_width, color, 8, 12, DIAGRAM_FONT, align=align)
    blocks_svg[key] = block
    add_image_block(elements, files, rng, key, block, x, y, now)
    return block


def add_whiteboard_block(
    elements: list[dict[str, Any]],
    files: dict[str, Any],
    blocks_svg: dict[str, Any],
    rng: random.Random,
    block: dict[str, Any],
    pos: tuple[float, float, float, float],
    index: int,
    now: int,
) -> None:
    x, y, w, h = pos
    shape = str(block.get("shape") or "").lower()
    kind = block_kind(block)
    if shape in {"circle", "ellipse", "oval"} or kind in {"client", "actor", "user"}:
        elements.append(ellipse(rng, x, y, w, h, plus_block_stroke(block), 2, now, background=plus_block_fill(block, index)))
    else:
        if shape == "square":
            size = min(w, h)
            x += (w - size) / 2
            y += (h - size) / 2
            w = h = size
        elements.append(
            rectangle(
                rng,
                x,
                y,
                w,
                h,
                plus_block_stroke(block),
                int(block.get("strokeWidth") or 2),
                now,
                background=plus_block_fill(block, index),
                stroke_style=str(block.get("strokeStyle") or block.get("stroke_style") or "solid"),
            ),
        )

    icon_name = str(block.get("icon") or "").strip()
    icon_space = 92 if icon_name and w > 260 else 0
    text_x = x + 24 + icon_space
    text_w = int(max(130, w - 48 - icon_space))
    text_block = rich_text_block_svg(
        str(block.get("title") or ""),
        str(block.get("body") or ""),
        text_w,
        plus_text_color(block),
        int(block.get("title_size") or 28),
        int(block.get("body_size") or 20),
        align=str(block.get("align") or "center").lower(),
        font_family=DIAGRAM_FONT,
    )
    key = f"wb_block_{block['id']}"
    blocks_svg[key] = text_block
    text_y = y + max(18, (h - text_block["height"]) / 2)
    if icon_space:
        text_x = x + icon_space + (w - icon_space - text_block["width"]) / 2
    else:
        text_x = x + (w - text_block["width"]) / 2
    add_image_block(elements, files, rng, key, text_block, text_x, text_y, now)

    if icon_name:
        icon = component_icon_svg(icon_name, str(block.get("icon_label") or block.get("iconLabel") or ""), int(block.get("icon_size") or 66))
        icon_key = f"wb_icon_{block['id']}"
        blocks_svg[icon_key] = icon
        add_image_block(elements, files, rng, icon_key, icon, x + 18, y + h - icon["height"] - 16, now)


def whiteboard_positions(
    blocks: list[dict[str, Any]],
    layout: str,
    top: float,
    canvas_width: float,
) -> dict[str, tuple[float, float, float, float]]:
    layout = layout.lower()
    positions: dict[str, tuple[float, float, float, float]] = {}
    margin = 70
    if layout in {"decision", "decision-tree", "decision_tree"} and blocks:
        center_w = 520
        center_h = 165
        positions[str(blocks[0]["id"])] = (canvas_width / 2 - center_w / 2, top, center_w, center_h)
        branches = blocks[1:3]
        branch_w = 460
        branch_h = 165
        if len(branches) == 1:
            positions[str(branches[0]["id"])] = (canvas_width / 2 - branch_w / 2, top + 255, branch_w, branch_h)
        elif len(branches) >= 2:
            positions[str(branches[0]["id"])] = (margin, top + 255, branch_w, branch_h)
            positions[str(branches[1]["id"])] = (canvas_width - margin - branch_w, top + 255, branch_w, branch_h)
        rest = blocks[3:]
        for index, block in enumerate(rest):
            w = 520 if len(rest) == 1 else 420
            x = (canvas_width - w) / 2 if len(rest) == 1 else margin + (index % 2) * (canvas_width - 2 * margin - w)
            y = top + 500 + (index // 2) * 210
            positions[str(block["id"])] = (x, y, w, dimension(block.get("height"), 150, 800))
        return positions

    if layout in {"comparison", "tradeoff", "compare"}:
        left = [block for index, block in enumerate(blocks) if str(block.get("lane") or block.get("side") or ("left" if index % 2 == 0 else "right")).lower() not in {"right", "ap", "availability", "option-b"}]
        right = [block for index, block in enumerate(blocks) if block not in left]
        left_x = margin
        right_x = canvas_width - margin - 560
        col_w = 560
        gap_y = 92
        for lane_blocks, x in ((left, left_x), (right, right_x)):
            y = top
            for block in lane_blocks:
                h = dimension(block.get("height"), 180, 800)
                positions[str(block["id"])] = (x, y, col_w, h)
                y += h + gap_y
        return positions

    if layout in {"pipeline", "flow", "sequence"}:
        block_w = 300 if len(blocks) > 3 else 350
        block_h = 155
        gap = 60
        total = len(blocks) * block_w + max(0, len(blocks) - 1) * gap
        start_x = max(margin, (canvas_width - total) / 2)
        for index, block in enumerate(blocks):
            positions[str(block["id"])] = (
                start_x + index * (block_w + gap),
                top,
                dimension(block.get("width") or block.get("w"), block_w, canvas_width),
                dimension(block.get("height") or block.get("h"), block_h, 800),
            )
        return positions

    if layout in {"architecture", "system", "system-design"}:
        rows: dict[str, list[dict[str, Any]]] = {"top": [], "middle": [], "bottom": []}
        for block in blocks:
            lane = str(block.get("lane") or block.get("tier") or "").lower()
            kind = block_kind(block)
            if lane in rows:
                rows[lane].append(block)
            elif kind in {"client", "actor", "user", "frontend"}:
                rows["top"].append(block)
            elif kind in {"database", "db", "cache", "queue", "storage", "store", "data"}:
                rows["bottom"].append(block)
            else:
                rows["middle"].append(block)
        row_y = {"top": top, "middle": top + 245, "bottom": top + 500}
        for row, row_blocks in rows.items():
            if not row_blocks:
                continue
            block_w = 260 if len(row_blocks) >= 4 else 310
            gap = 70
            total = len(row_blocks) * block_w + max(0, len(row_blocks) - 1) * gap
            x0 = max(margin, (canvas_width - total) / 2)
            for index, block in enumerate(row_blocks):
                shape = str(block.get("shape") or "").lower()
                kind = block_kind(block)
                h = 170
                w = block_w
                if shape in {"circle", "ellipse"} or kind in {"client", "actor", "user"}:
                    w = h = 180
                positions[str(block["id"])] = (
                    x0 + index * (block_w + gap),
                    row_y[row],
                    dimension(block.get("width") or block.get("w"), w, canvas_width),
                    dimension(block.get("height") or block.get("h"), h, 800),
                )
        return positions

    center_x = canvas_width / 2 - 260
    if blocks:
        positions[str(blocks[0]["id"])] = (center_x, top + 120, 520, 190)
    spokes = [
        (margin, top, 380, 150),
        (canvas_width - margin - 380, top, 380, 150),
        (margin, top + 310, 380, 150),
        (canvas_width - margin - 380, top + 310, 380, 150),
        (canvas_width / 2 - 230, top + 430, 460, 150),
    ]
    for block, pos in zip(blocks[1:], spokes):
        positions[str(block["id"])] = pos
    return positions


def build_whiteboard_scene(content: dict[str, Any], slug: str) -> tuple[dict[str, Any], dict[str, Any], int, int]:
    rng = random.Random(20260620)
    now = int(time.time() * 1000)
    canvas_width = int(dimension(content.get("width"), 1500, 1500))
    margin = 70
    content_width = canvas_width - margin * 2
    elements: list[dict[str, Any]] = []
    files: dict[str, Any] = {}
    blocks_svg: dict[str, Any] = {}

    title = str(content.get("title") or "Interview Whiteboard")
    title_block = add_whiteboard_text(
        elements,
        files,
        blocks_svg,
        rng,
        "wb_title",
        title,
        0,
        52,
        canvas_width,
        44,
        now,
        align="center",
    )
    y_cursor = 52 + title_block["height"] + 34
    summary = str(content.get("summary") or "")
    if summary:
        summary_block = text_block_svg(summary, 25, int(content_width), PLUS_STROKE, 8, 12, DIAGRAM_FONT, align="center")
        blocks_svg["wb_summary"] = summary_block
        add_image_block(elements, files, rng, "wb_summary", summary_block, (canvas_width - summary_block["width"]) / 2, y_cursor, now)
        y_cursor += summary_block["height"] + 52

    task_text = coerce_text(content.get("task") or content.get("problem"))
    constraints_text = coerce_text(content.get("constraints"))
    if task_text or constraints_text:
        frame_h = 230
        if task_text and constraints_text:
            task_w = 590
            gap = 44
            add_top_frame(elements, files, blocks_svg, rng, "wb_task", str(content.get("task_title") or "Task:"), task_text, margin, y_cursor, task_w, frame_h, now)
            add_top_frame(
                elements,
                files,
                blocks_svg,
                rng,
                "wb_constraints",
                str(content.get("constraints_title") or "Constraints:"),
                constraints_text,
                margin + task_w + gap,
                y_cursor,
                content_width - task_w - gap,
                frame_h,
                now,
            )
        else:
            add_top_frame(
                elements,
                files,
                blocks_svg,
                rng,
                "wb_task",
                str(content.get("task_title") or ("Constraints:" if constraints_text else "Task:")),
                task_text or constraints_text,
                margin,
                y_cursor,
                content_width,
                frame_h,
                now,
            )
        y_cursor += frame_h + 86

    raw_blocks = content.get("blocks") or content.get("nodes") or []
    blocks = [normalize_block(block, index) for index, block in enumerate(raw_blocks)]
    layout = str(content.get("layout") or "auto")
    if layout.lower() == "auto":
        if any(str(block.get("lane") or block.get("side") or "") for block in blocks):
            layout = "comparison"
        elif any(block_kind(block) in {"service", "api", "database", "db", "cache", "queue", "storage", "client", "actor", "user"} for block in blocks):
            layout = "architecture"
        elif len(blocks) <= 5:
            layout = "concept-map"
        else:
            layout = "pipeline"
    positions = whiteboard_positions(blocks, layout, y_cursor, canvas_width)

    for index, block in enumerate(blocks):
        block_id = str(block["id"])
        default = positions.get(block_id, (margin, y_cursor, 300, 160))
        pos = (
            dimension(block.get("x"), default[0], canvas_width),
            dimension(block.get("y"), default[1], 1600),
            dimension(block.get("width") or block.get("w"), default[2], content_width),
            dimension(block.get("height") or block.get("h"), default[3], 800),
        )
        positions[block_id] = pos
        add_whiteboard_block(elements, files, blocks_svg, rng, block, pos, index, now)

    connectors = list(content.get("connectors") or [])
    if not connectors and blocks:
        if layout.lower() in {"decision", "decision-tree", "decision_tree"}:
            for block in blocks[1:3]:
                connectors.append({"from": blocks[0]["id"], "to": block["id"], "routing": "centered"})
            if len(blocks) > 3:
                for block in blocks[1:3]:
                    connectors.append({"from": block["id"], "to": blocks[3]["id"], "routing": "centered"})
        elif layout.lower() in {"comparison", "tradeoff", "compare"}:
            lane_groups: dict[str, list[dict[str, Any]]] = {}
            for index, block in enumerate(blocks):
                lane = str(block.get("lane") or block.get("side") or ("left" if index % 2 == 0 else "right")).lower()
                lane_groups.setdefault(lane, []).append(block)
            for lane_blocks in lane_groups.values():
                for idx in range(len(lane_blocks) - 1):
                    connectors.append({"from": lane_blocks[idx]["id"], "to": lane_blocks[idx + 1]["id"]})
        else:
            for idx in range(len(blocks) - 1):
                connectors.append({"from": blocks[idx]["id"], "to": blocks[idx + 1]["id"]})

    for index, connector in enumerate(connectors):
        src = str(connector.get("from") or connector.get("source") or "")
        dst = str(connector.get("to") or connector.get("target") or "")
        if connector.get("points"):
            points = [[float(p[0]), float(p[1])] for p in connector["points"] if isinstance(p, list | tuple) and len(p) >= 2]
        elif src in positions and dst in positions:
            if str(connector.get("routing") or "").lower() in {"centered", "center", "decision"}:
                points = centered_right_angle_points(positions[src], positions[dst])
            else:
                points = orthogonal_points(positions[src], positions[dst])
        else:
            continue
        elements.append(routed_arrow(rng, points, now, stroke=str(connector.get("stroke") or PLUS_STROKE), stroke_width=int(connector.get("strokeWidth") or 2)))
        label = str(connector.get("label") or "")
        if label:
            label_block = text_block_svg(label, 17, 230, PLUS_STROKE, 6, 8, DIAGRAM_FONT, align="center")
            label_key = f"wb_connector_{index}"
            blocks_svg[label_key] = label_block
            mid = points[len(points) // 2]
            add_image_block(
                elements,
                files,
                rng,
                label_key,
                label_block,
                mid[0] - label_block["width"] / 2,
                mid[1] - label_block["height"] / 2,
                now,
            )

    max_y = max((y + h for x, y, w, h in positions.values()), default=y_cursor)
    callouts = list(content.get("callouts") or [])
    for index, callout in enumerate(callouts):
        default_w = 420 if index < 2 else 620
        default_h = 130
        default_x = (canvas_width - default_w) / 2 if len(callouts) == 1 else margin + (index % 2) * (content_width - default_w)
        x = dimension(callout.get("x"), default_x, canvas_width)
        y = dimension(callout.get("y"), max_y + 54 + (index // 2) * 170, 2200)
        w = dimension(callout.get("width") or callout.get("w"), default_w, content_width)
        h = dimension(callout.get("height") or callout.get("h"), default_h, 600)
        note = dict(callout)
        note.setdefault("id", f"callout{index}")
        note.setdefault("kind", "note")
        note.setdefault("fill", [PLUS_PINK, PLUS_YELLOW, PLUS_MINT][index % 3])
        note.setdefault("title_size", 24)
        note.setdefault("body_size", 20)
        add_whiteboard_block(elements, files, blocks_svg, rng, note, (x, y, w, h), index, now)
        max_y = max(max_y, y + h)

    canvas_height = int(max_y + 95)
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "sde-interview-script-skill",
        "elements": elements,
        "appState": {
            "viewBackgroundColor": "#ffffff",
            "gridSize": None,
            "theme": "light",
            "name": slug,
            "scrollX": 0,
            "scrollY": 0,
            "zoom": {"value": 1},
        },
        "files": files,
    }
    return scene, blocks_svg, canvas_width, canvas_height


def build_diagram_scene(
    content: dict[str, Any],
    slug: str,
) -> tuple[dict[str, Any], dict[str, Any], int, int]:
    rng = random.Random(20260616)
    now = int(time.time() * 1000)
    plus_style = is_plus_style(content)
    canvas_width = int(dimension(content.get("width"), 1760, 1760))
    margin = 80
    content_width = canvas_width - margin * 2
    elements: list[dict[str, Any]] = []
    files: dict[str, Any] = {}
    blocks_svg: dict[str, Any] = {
        "title": text_block_svg(
            str(content.get("title", "Script Card")),
            44 if plus_style else 42,
            1320,
            PLUS_STROKE if plus_style else "#111827",
            14,
            22,
            DIAGRAM_FONT if plus_style else HANDWRITING_FONT,
            align="center" if plus_style else "left",
        ),
    }
    title_x = (canvas_width - blocks_svg["title"]["width"]) / 2 if plus_style else margin
    add_image_block(elements, files, rng, "title", blocks_svg["title"], title_x, 70, now)
    y_cursor = 70 + blocks_svg["title"]["height"] + 42
    summary = str(content.get("summary") or "")
    if summary:
        blocks_svg["summary"] = text_block_svg(
            summary,
            28,
            int(content_width),
            "#374151" if not plus_style else PLUS_STROKE,
            12,
            18,
            DIAGRAM_FONT if plus_style else HANDWRITING_FONT,
            align="center" if plus_style else "left",
        )
        summary_x = (canvas_width - blocks_svg["summary"]["width"]) / 2 if plus_style else margin
        add_image_block(elements, files, rng, "summary", blocks_svg["summary"], summary_x, y_cursor, now)
        y_cursor += blocks_svg["summary"]["height"] + 64

    task_text = coerce_text(content.get("task") or content.get("problem"))
    constraints_text = coerce_text(content.get("constraints"))
    if plus_style and (task_text or constraints_text):
        frame_h = 150
        gap = 48
        if task_text and constraints_text:
            left_w = 680
            right_w = content_width - left_w - gap
            add_top_frame(
                elements,
                files,
                blocks_svg,
                rng,
                "task",
                str(content.get("task_title") or "Task:"),
                task_text,
                margin,
                y_cursor,
                left_w,
                frame_h,
                now,
            )
            add_top_frame(
                elements,
                files,
                blocks_svg,
                rng,
                "constraints",
                str(content.get("constraints_title") or "Constraints:"),
                constraints_text,
                margin + left_w + gap,
                y_cursor,
                right_w,
                frame_h,
                now,
            )
        else:
            add_top_frame(
                elements,
                files,
                blocks_svg,
                rng,
                "task",
                str(content.get("task_title") or ("Constraints:" if constraints_text else "Task:")),
                task_text or constraints_text,
                margin,
                y_cursor,
                content_width,
                frame_h,
                now,
            )
        y_cursor += frame_h + 86

    raw_blocks = content.get("blocks") or content.get("nodes") or []
    diagram_blocks = [normalize_block(block, index) for index, block in enumerate(raw_blocks)]
    layout = str(content.get("layout") or "auto")
    if plus_style and layout.lower() == "auto":
        kinds = {block_kind(block) for block in diagram_blocks}
        if kinds & {"service", "api", "database", "db", "cache", "queue", "storage", "cdn", "client"}:
            layout = "architecture"
        elif any(str(block.get("lane") or block.get("side") or "") for block in diagram_blocks):
            layout = "comparison"
        else:
            layout = "concept-map"
    auto = auto_positions(diagram_blocks, layout, y_cursor, canvas_width)
    positions: dict[str, tuple[float, float, float, float]] = {}
    for block in diagram_blocks:
        block_id = str(block["id"])
        default = auto.get(block_id, (margin, y_cursor, 420, 220))
        x = dimension(block.get("x"), default[0], canvas_width)
        y = dimension(block.get("y"), default[1], 1600)
        w = dimension(block.get("width") or block.get("w"), default[2], content_width)
        h = dimension(block.get("height") or block.get("h"), default[3], 900)
        positions[block_id] = (x, y, w, h)

    if positions:
        min_diagram_y = min(pos[1] for pos in positions.values())
        if min_diagram_y < y_cursor:
            shift_y = y_cursor - min_diagram_y
            positions = {
                block_id: (x, y + shift_y, w, h)
                for block_id, (x, y, w, h) in positions.items()
            }

    for block in diagram_blocks:
        block_id = str(block["id"])
        x, y, w, h = positions[block_id]
        stroke = plus_block_stroke(block) if plus_style else str(block.get("stroke") or block_stroke(block))
        fill = plus_block_fill(block) if plus_style else str(block.get("fill") or block.get("background") or "transparent")
        text_color = plus_text_color(block) if plus_style else (stroke if stroke != "#111827" else "#111827")
        shape = block_shape(block, allow_diamond=(not plus_style or bool(block.get("allowDiamond"))))
        default_align = "center" if plus_style else "left"
        default_valign = "center" if plus_style else "top"
        align = str(block.get("align") or content.get("align") or default_align).lower()
        valign = str(block.get("valign") or content.get("valign") or default_valign).lower()
        stroke_width = int(block.get("strokeWidth") or block.get("stroke_width") or (2 if plus_style else (3 if stroke == "#2563eb" else 2)))
        stroke_style = str(block.get("strokeStyle") or block.get("stroke_style") or "solid")
        icon_name = str(block.get("icon") or "").strip()
        reserve_icon_space = bool(plus_style and icon_name)
        text_area_x = x
        text_area_w = w
        if shape == "diamond":
            elements.append(diamond(rng, x, y, w, h, stroke, stroke_width, now, background=fill))
            text_w = int(max(160, w * 0.62))
            text_x = x + (w - text_w) / 2
            text_y = y + h * 0.22
        elif shape == "ellipse":
            elements.append(ellipse(rng, x, y, w, h, stroke, stroke_width, now, background=fill))
            text_area_x = x + (96 if reserve_icon_space else 0)
            text_area_w = w - (116 if reserve_icon_space else 0)
            text_w = int(max(160, text_area_w * 0.68))
            text_x = text_area_x + (text_area_w - text_w) / 2
            text_y = y + h * 0.24
        else:
            elements.append(
                rectangle(
                    rng,
                    x,
                    y,
                    w,
                    h,
                    stroke,
                    stroke_width,
                    now,
                    background=fill,
                    stroke_style=stroke_style,
                ),
            )
            text_area_x = x + (118 if reserve_icon_space else 24)
            text_area_w = w - (148 if reserve_icon_space else 48)
            text_w = int(max(180, text_area_w))
            text_x = text_area_x + ((text_area_w - text_w) / 2 if align == "center" else 0)
            text_y = y + 28
        key = f"block{block_id}"
        blocks_svg[key] = rich_text_block_svg(
            str(block.get("title") or ""),
            str(block.get("body") or ""),
            text_w,
            text_color,
            31 if plus_style else 30,
            23 if plus_style else 26,
            align=align,
            font_family=DIAGRAM_FONT if plus_style else HANDWRITING_FONT,
        )
        if align == "center":
            if reserve_icon_space:
                text_x = text_area_x + (text_area_w - blocks_svg[key]["width"]) / 2
            else:
                text_x = x + (w - blocks_svg[key]["width"]) / 2
        if valign == "center":
            text_y = y + max(18, (h - blocks_svg[key]["height"]) / 2)
        add_image_block(elements, files, rng, key, blocks_svg[key], text_x, text_y, now)

        if plus_style and icon_name:
            icon_label = str(block.get("icon_label") or block.get("iconLabel") or "")
            icon_size = int(dimension(block.get("icon_size"), 70, 120))
            icon_block = component_icon_svg(icon_name, icon_label, icon_size)
            icon_key = f"icon{block_id}"
            blocks_svg[icon_key] = icon_block
            icon_x = float(block.get("icon_x") or (x + 18))
            icon_y = float(block.get("icon_y") or (y + h - icon_block["height"] - 14))
            add_image_block(elements, files, rng, icon_key, icon_block, icon_x, icon_y, now)

    connectors = list(content.get("connectors") or [])
    if not connectors and diagram_blocks:
        if layout.lower() in {"decision", "decision-tree", "decision_tree"}:
            connectors = [
                {"from": str(diagram_blocks[0]["id"]), "to": str(block["id"])}
                for block in diagram_blocks[1:4]
            ]
        elif layout.lower() not in {"comparison", "tradeoff", "compare"}:
            connectors = [
                {"from": str(diagram_blocks[index]["id"]), "to": str(diagram_blocks[index + 1]["id"])}
                for index in range(len(diagram_blocks) - 1)
            ]
    for index, connector in enumerate(connectors):
        connector_stroke = str(connector.get("stroke") or connector.get("color") or (PLUS_STROKE if plus_style else "#2563eb"))
        connector_width = int(connector.get("strokeWidth") or connector.get("stroke_width") or (2 if plus_style else 3))
        if connector.get("points"):
            raw_points = connector.get("points") or []
            points = [
                [float(point[0]), float(point[1])]
                for point in raw_points
                if isinstance(point, list | tuple) and len(point) >= 2
            ]
            if len(points) < 2:
                continue
            elements.append(routed_arrow(rng, points, now, stroke=connector_stroke, stroke_width=connector_width))
            label = str(connector.get("label") or "")
            if label:
                key = f"connector{index}"
                blocks_svg[key] = text_block_svg(
                    label,
                    18 if not plus_style else 19,
                    220,
                    "#1e3a8a" if not plus_style else PLUS_STROKE,
                    8,
                    10,
                    DIAGRAM_FONT if plus_style else HANDWRITING_FONT,
                    align="center",
                )
                mid = points[len(points) // 2]
                add_image_block(
                    elements,
                    files,
                    rng,
                    key,
                    blocks_svg[key],
                    mid[0] - blocks_svg[key]["width"] / 2,
                    mid[1] - 38,
                    now,
                )
            continue
        src = str(connector.get("from") or connector.get("source") or "")
        dst = str(connector.get("to") or connector.get("target") or "")
        if src not in positions or dst not in positions:
            continue
        if plus_style or str(connector.get("routing") or "").lower() in {"orthogonal", "right-angle", "right_angle"}:
            points = orthogonal_points(positions[src], positions[dst])
            elements.append(routed_arrow(rng, points, now, stroke=connector_stroke, stroke_width=connector_width))
            label_x = sum(point[0] for point in points) / len(points)
            label_y = sum(point[1] for point in points) / len(points)
        else:
            x1, y1, x2, y2 = connector_points(positions[src], positions[dst])
            elements.append(arrow(rng, x1, y1, x2, y2, now, stroke=connector_stroke, stroke_width=connector_width))
            label_x = (x1 + x2) / 2
            label_y = (y1 + y2) / 2
        label = str(connector.get("label") or "")
        if label:
            key = f"connector{index}"
            blocks_svg[key] = text_block_svg(
                label,
                18 if not plus_style else 19,
                220,
                "#1e3a8a" if not plus_style else PLUS_STROKE,
                8,
                10,
                DIAGRAM_FONT if plus_style else HANDWRITING_FONT,
                align="center",
            )
            add_image_block(
                elements,
                files,
                rng,
                key,
                blocks_svg[key],
                label_x - blocks_svg[key]["width"] / 2,
                label_y - 38,
                now,
            )

    max_y = max((y + h for x, y, w, h in positions.values()), default=y_cursor)
    for index, callout in enumerate(content.get("callouts") or []):
        x = dimension(callout.get("x"), margin + (index % 2) * 820, canvas_width)
        y = dimension(callout.get("y"), max_y + 60 + (index // 2) * 190, 2000)
        w = dimension(callout.get("width") or callout.get("w"), 760, content_width)
        h = dimension(callout.get("height") or callout.get("h"), 160, 600)
        stroke = str(callout.get("stroke") or (PLUS_STROKE if plus_style else "#b91c1c"))
        fill = str(callout.get("fill") or callout.get("background") or ([PLUS_PINK, PLUS_YELLOW, PLUS_MINT][index % 3] if plus_style else "transparent"))
        elements.append(rectangle(rng, x, y, w, h, stroke, 1 if plus_style else 2, now, background=fill))
        key = f"callout{index}"
        blocks_svg[key] = rich_text_block_svg(
            str(callout.get("title") or "Caveat"),
            str(callout.get("body") or callout.get("text") or ""),
            int(w - 48),
            PLUS_STROKE if plus_style else stroke,
            24 if plus_style else 22,
            21 if plus_style else 20,
            align=str(callout.get("align") or ("center" if plus_style else "left")).lower(),
            font_family=DIAGRAM_FONT if plus_style else HANDWRITING_FONT,
        )
        text_x = x + (w - blocks_svg[key]["width"]) / 2 if plus_style else x + 24
        text_y = y + max(16, (h - blocks_svg[key]["height"]) / 2) if plus_style else y + 26
        add_image_block(elements, files, rng, key, blocks_svg[key], text_x, text_y, now)
        max_y = max(max_y, y + h)

    talk_track = content.get("talk_track") or content.get("short") or ""
    if isinstance(talk_track, list):
        talk_track = "\n".join(str(item) for item in talk_track)
    include_talk = bool(content.get("include_talk_track_in_board") or content.get("include_script_in_board"))
    if talk_track and (include_talk or not plus_style):
        y = max_y + 78
        h = 165
        elements.append(rectangle(rng, margin, y, content_width, h, "#111827", 2, now))
        blocks_svg["talk"] = rich_text_block_svg(
            localized_talk_label(str(content.get("language") or "")),
            str(talk_track),
            int(content_width - 64),
            "#111827",
            23,
            21,
            font_family=HANDWRITING_FONT,
        )
        add_image_block(elements, files, rng, "talk", blocks_svg["talk"], margin + 32, y + 26, now)
        max_y = y + h

    canvas_height = int(max_y + 90)
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "sde-interview-script-skill",
        "elements": elements,
        "appState": {
            "viewBackgroundColor": "#ffffff",
            "gridSize": None,
            "theme": "light",
            "name": slug,
            "scrollX": 0,
            "scrollY": 0,
            "zoom": {"value": 1},
        },
        "files": files,
    }
    return scene, blocks_svg, canvas_width, canvas_height


def build_legacy_scene(content: dict[str, Any], slug: str) -> tuple[dict[str, Any], dict[str, Any], int, int]:
    rng = random.Random(20260614)
    now = int(time.time() * 1000)
    blocks: dict[str, Any] = {
        "title": text_block_svg(content["title"], 42, 1100, "#111827", 14, 22),
        "summary": text_block_svg(content["summary"], 28, 1450, "#374151", 14, 22),
        "script": text_block_svg(content["script"], 27, 1450, "#111827", 14, 24),
        "short": text_block_svg(content["short"], 26, 1450, "#111827", 13, 20),
    }
    for index, flow in enumerate(content["flows"]):
        blocks[f"flow{index}"] = text_block_svg(flow, 24, 310, "#1e3a8a", 12, 16)

    margin = 80
    card_width = 1600
    padding = 46
    script_y = 70
    content_x = margin + padding
    y_cursor = script_y + 34
    elements: list[dict[str, Any]] = []
    files: dict[str, Any] = {}
    content_items: list[tuple[str, dict[str, Any], str]] = []
    for key in ["title", "summary", "script"]:
        element, file_id = image_element(rng, key, blocks[key], content_x, y_cursor, now)
        content_items.append((key, element, file_id))
        y_cursor += element["height"] + (24 if key == "title" else 22)
    script_card_height = y_cursor - script_y + 24
    elements.append(rectangle(rng, margin, script_y, card_width, script_card_height, "#111827", 2, now))
    for key, element, file_id in content_items:
        elements.append(element)
        files[file_id] = {
            "id": file_id,
            "mimeType": "image/svg+xml",
            "dataURL": blocks[key]["dataURL"],
            "created": now,
        }

    flow_y = script_y + script_card_height + 74
    flow_width = 360
    flow_height = 250
    gap = (card_width - 4 * flow_width) / 3
    flow_xs = [margin + index * (flow_width + gap) for index in range(4)]
    for index, flow_x in enumerate(flow_xs):
        elements.append(rectangle(rng, flow_x, flow_y, flow_width, flow_height, "#2563eb", 3, now))
        key = f"flow{index}"
        element, file_id = image_element(rng, key, blocks[key], flow_x + 24, flow_y + 30, now)
        elements.append(element)
        files[file_id] = {
            "id": file_id,
            "mimeType": "image/svg+xml",
            "dataURL": blocks[key]["dataURL"],
            "created": now,
        }
        if index < 3:
            elements.append(
                arrow(
                    rng,
                    flow_x + flow_width + 14,
                    flow_y + flow_height / 2,
                    flow_xs[index + 1] - 18,
                    flow_y + flow_height / 2,
                    now,
                ),
            )

    short_y = flow_y + flow_height + 74
    short_element, short_file_id = image_element(
        rng,
        "short",
        blocks["short"],
        margin + padding,
        short_y + 38,
        now,
    )
    short_height = short_element["height"] + 76
    elements.append(rectangle(rng, margin, short_y, card_width, short_height, "#111827", 2, now))
    elements.append(short_element)
    files[short_file_id] = {
        "id": short_file_id,
        "mimeType": "image/svg+xml",
        "dataURL": blocks["short"]["dataURL"],
        "created": now,
    }

    canvas_height = int(short_y + short_height + 80)
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "sde-interview-script-skill",
        "elements": elements,
        "appState": {
            "viewBackgroundColor": "#ffffff",
            "gridSize": None,
            "theme": "light",
            "name": slug,
            "scrollX": 0,
            "scrollY": 0,
            "zoom": {"value": 1},
        },
        "files": files,
    }
    return scene, blocks, 1760, canvas_height


def build_scene(content: dict[str, Any], slug: str) -> tuple[dict[str, Any], dict[str, Any], int, int]:
    if is_plus_style(content):
        return build_whiteboard_scene(content, slug)
    if content.get("blocks") or content.get("nodes"):
        return build_diagram_scene(content, slug)
    return build_legacy_scene(content, slug)


def svg_image_tag(block: dict[str, Any], x: float, y: float) -> str:
    inner_svg = block["svg"].split(">", 1)[1].rsplit("</svg>", 1)[0]
    return (
        f'<g transform="translate({x:.0f} {y:.0f})">'
        f"{inner_svg}</g>"
    )


def rough_rng(seed: str) -> random.Random:
    return random.Random(sum((index + 1) * ord(char) for index, char in enumerate(seed)))


def rough_segment_points(
    start: tuple[float, float],
    end: tuple[float, float],
    rng: random.Random,
    amplitude: float,
) -> list[tuple[float, float]]:
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    length = max(1.0, math.hypot(dx, dy))
    nx = -dy / length
    ny = dx / length
    steps = max(1, int(length // 48))
    points: list[tuple[float, float]] = []
    for step in range(steps + 1):
        t = step / steps
        x = x1 + dx * t
        y = y1 + dy * t
        if 0 < step < steps:
            wobble = rng.uniform(-amplitude, amplitude)
            x += nx * wobble + rng.uniform(-amplitude * 0.35, amplitude * 0.35)
            y += ny * wobble + rng.uniform(-amplitude * 0.35, amplitude * 0.35)
        points.append((x, y))
    return points


def rough_points(
    points: list[tuple[float, float]],
    seed: str,
    amplitude: float,
    closed: bool = False,
) -> list[tuple[float, float]]:
    rng = rough_rng(seed)
    path_points = list(points)
    if closed and path_points[0] != path_points[-1]:
        path_points.append(path_points[0])
    result: list[tuple[float, float]] = []
    for index in range(len(path_points) - 1):
        segment = rough_segment_points(path_points[index], path_points[index + 1], rng, amplitude)
        if result:
            segment = segment[1:]
        result.extend(segment)
    return result


def polyline_svg(
    points: list[tuple[float, float]],
    color: str,
    stroke_width: float,
    marker_id: str | None = None,
    opacity: float = 1.0,
    closed: bool = False,
    dash: str | None = None,
) -> str:
    if closed and points and points[0] != points[-1]:
        points = [*points, points[0]]
    point_text = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
    marker = f' marker-end="url(#{marker_id})"' if marker_id else ""
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<polyline points="{point_text}" fill="none" stroke="{color}" '
        f'stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'opacity="{opacity}"{dash_attr}{marker} />'
    )


def rough_polyline_svg(
    points: list[tuple[float, float]],
    color: str,
    stroke_width: float,
    seed: str,
    marker_id: str | None = None,
    closed: bool = False,
    dash: str | None = None,
) -> str:
    primary = rough_points(points, seed + "a", 2.2 if closed else 1.6, closed)
    secondary = rough_points(points, seed + "b", 1.7 if closed else 1.2, closed)
    return (
        polyline_svg(secondary, color, max(1.0, stroke_width * 0.8), None, 0.42, closed, dash)
        + polyline_svg(primary, color, stroke_width, marker_id, 0.95, closed, dash)
    )


def rounded_rect_points(x: float, y: float, w: float, h: float, r: float) -> list[tuple[float, float]]:
    r = min(r, w / 2, h / 2)
    return [
        (x + r, y),
        (x + w - r, y),
        (x + w - r / 2, y + r / 3),
        (x + w, y + r),
        (x + w, y + h - r),
        (x + w - r / 2, y + h - r / 3),
        (x + w - r, y + h),
        (x + r, y + h),
        (x + r / 2, y + h - r / 3),
        (x, y + h - r),
        (x, y + r),
        (x + r / 2, y + r / 3),
    ]


def jitter(value: float, rng: random.Random, amount: float = 1.7) -> float:
    return value + rng.uniform(-amount, amount)


def rounded_rect_path(x: float, y: float, w: float, h: float, r: float, seed: str) -> str:
    rng = rough_rng(seed)
    r = min(r, w / 2, h / 2)
    x0, y0, x1, y1 = x, y, x + w, y + h
    return " ".join(
        [
            f"M {jitter(x0 + r, rng):.1f} {jitter(y0, rng):.1f}",
            f"L {jitter(x1 - r, rng):.1f} {jitter(y0, rng):.1f}",
            f"Q {jitter(x1, rng):.1f} {jitter(y0, rng):.1f} {jitter(x1, rng):.1f} {jitter(y0 + r, rng):.1f}",
            f"L {jitter(x1, rng):.1f} {jitter(y1 - r, rng):.1f}",
            f"Q {jitter(x1, rng):.1f} {jitter(y1, rng):.1f} {jitter(x1 - r, rng):.1f} {jitter(y1, rng):.1f}",
            f"L {jitter(x0 + r, rng):.1f} {jitter(y1, rng):.1f}",
            f"Q {jitter(x0, rng):.1f} {jitter(y1, rng):.1f} {jitter(x0, rng):.1f} {jitter(y1 - r, rng):.1f}",
            f"L {jitter(x0, rng):.1f} {jitter(y0 + r, rng):.1f}",
            f"Q {jitter(x0, rng):.1f} {jitter(y0, rng):.1f} {jitter(x0 + r, rng):.1f} {jitter(y0, rng):.1f}",
        ],
    )


def rough_rounded_rect_svg(element: dict[str, Any]) -> str:
    x = float(element["x"])
    y = float(element["y"])
    w = float(element["width"])
    h = float(element["height"])
    stroke = element["strokeColor"]
    stroke_width = float(element.get("strokeWidth") or 2)
    fill = element.get("backgroundColor") or "transparent"
    rx = 28 if element.get("roundness") else 0
    dash = ' stroke-dasharray="8 10"' if element.get("strokeStyle") == "dashed" else ""
    fill_node = ""
    if fill not in {"transparent", "none", ""}:
        fill_node = (
            f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" '
            f'rx="{rx}" ry="{rx}" fill="{fill}" opacity="0.92" />'
        )
    if element.get("strokeStyle") == "dashed":
        return (
            fill_node
            + f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" '
            f'rx="{rx}" ry="{rx}" fill="none" stroke="{stroke}" '
            f'stroke-width="{stroke_width}" stroke-linecap="round"{dash} />'
        )
    path_a = rounded_rect_path(x, y, w, h, rx, element["id"] + "a")
    path_b = rounded_rect_path(x + 0.5, y - 0.3, w - 0.7, h + 0.4, rx, element["id"] + "b")
    return (
        fill_node
        + f'<path d="{path_b}" fill="none" stroke="{stroke}" stroke-width="{max(1.0, stroke_width * 0.8):.1f}" '
        'stroke-linecap="round" stroke-linejoin="round" opacity="0.42" />'
        + f'<path d="{path_a}" fill="none" stroke="{stroke}" stroke-width="{stroke_width:.1f}" '
        'stroke-linecap="round" stroke-linejoin="round" opacity="0.96" />'
    )


def rough_ellipse_svg(element: dict[str, Any]) -> str:
    x = float(element["x"])
    y = float(element["y"])
    w = float(element["width"])
    h = float(element["height"])
    cx = x + w / 2
    cy = y + h / 2
    rx = w / 2
    ry = h / 2
    stroke = element["strokeColor"]
    stroke_width = float(element.get("strokeWidth") or 2)
    fill = element.get("backgroundColor") or "transparent"
    fill_attr = fill if fill not in {"transparent", "none", ""} else "none"
    return (
        f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" fill="{fill_attr}" '
        f'stroke="{stroke}" stroke-width="{max(1.0, stroke_width * 0.75):.1f}" opacity="0.45" />'
        f'<ellipse cx="{cx + 1:.0f}" cy="{cy - 1:.0f}" rx="{max(1, rx - 1):.0f}" ry="{max(1, ry + 1):.0f}" fill="none" '
        f'stroke="{stroke}" stroke-width="{stroke_width:.1f}" />'
    )


def render_preview_svg(scene: dict[str, Any], blocks: dict[str, Any], width: int, height: int) -> str:
    nodes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
    ]
    for element in scene["elements"]:
        if element["type"] == "rectangle":
            nodes.append(rough_rounded_rect_svg(element))
        elif element["type"] == "ellipse":
            nodes.append(rough_ellipse_svg(element))
        elif element["type"] == "diamond":
            x = element["x"]
            y = element["y"]
            w = element["width"]
            h = element["height"]
            points = [
                (x + w / 2, y),
                (x + w, y + h / 2),
                (x + w / 2, y + h),
                (x, y + h / 2),
            ]
            point_text = " ".join(f"{px:.0f},{py:.0f}" for px, py in points)
            fill = element.get("backgroundColor") or "transparent"
            if fill not in {"transparent", "none", ""}:
                nodes.append(f'<polygon points="{point_text}" fill="{fill}" opacity="0.92" />')
            nodes.append(
                rough_polyline_svg(points, element["strokeColor"], element["strokeWidth"], element["id"], closed=True),
            )
        elif element["type"] == "arrow":
            x1 = element["x"]
            y1 = element["y"]
            points = element.get("points") or [[0, 0], [element["width"], element["height"]]]
            absolute_points = [(x1 + point[0], y1 + point[1]) for point in points]
            marker_id = f"arrow-{element['id']}"
            nodes.append(
                f'<defs><marker id="{marker_id}" markerWidth="10" markerHeight="10" '
                'refX="8" refY="3" orient="auto" markerUnits="strokeWidth">'
                f'<path d="M0,0 L0,6 L9,3 z" fill="{element["strokeColor"]}" />'
                "</marker></defs>"
            )
            nodes.append(
                rough_polyline_svg(
                    absolute_points,
                    element["strokeColor"],
                    element.get("strokeWidth") or 3,
                    element["id"],
                    marker_id=marker_id,
                ),
            )
        elif element["type"] == "image":
            key = element["fileId"].split("_file_")[0]
            if key in blocks:
                nodes.append(svg_image_tag(blocks[key], element["x"], element["y"]))
    nodes.append("</svg>")
    return "".join(nodes)


def maybe_share(excalidraw_path: Path, skip: bool) -> dict[str, Any] | None:
    if skip or not shutil.which("node"):
        return None
    script_path = Path(__file__).with_name("share_excalidraw.mjs")
    try:
        completed = subprocess.run(
            ["node", str(script_path), "--input", str(excalidraw_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return json.loads(completed.stdout)
    except Exception as error:  # pragma: no cover - runtime/network fallback
        return {"error": str(error)}


def main() -> None:
    args = parse_args()
    content = load_content(args.content)
    timestamp = int(time.time())
    out_dir = Path(args.out or f"/tmp/sde-interview-card-{timestamp}")
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", args.slug).strip("-") or "interview-card"

    scene, blocks, canvas_width, canvas_height = build_scene(content, slug)
    excalidraw_path = out_dir / f"{slug}.excalidraw"
    preview_path = out_dir / f"{slug}-preview.svg"
    result_path = out_dir / f"{slug}-result.json"
    excalidraw_path.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")
    preview_svg = render_preview_svg(scene, blocks, canvas_width, canvas_height)
    preview_path.write_text(preview_svg, encoding="utf-8")
    share = maybe_share(excalidraw_path, args.no_share)
    result = {
        "preview": str(preview_path),
        "excalidraw": str(excalidraw_path),
        "link": share.get("url") if isinstance(share, dict) else None,
        "share": share,
    }
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
