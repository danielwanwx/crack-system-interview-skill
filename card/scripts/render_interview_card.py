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
    "HanziPen SC,HanziPen TC,Kaiti SC,KaiTi,Bradley Hand,"
    "Comic Sans MS,cursive,sans-serif"
)


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
    return lines


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
) -> dict[str, Any]:
    lines = wrap_text(text, size, max_width)
    line_height = int(size * 1.26) + line_gap
    y = int(size * 1.1)
    text_nodes: list[str] = []
    max_line_width = 1.0
    for line in lines:
        if line is None:
            y += paragraph_gap
            continue
        max_line_width = max(max_line_width, token_width(line, size))
        text_nodes.append(
            f'<text x="0" y="{y}" font-size="{size}" fill="{color}" '
            f'font-family="{HANDWRITING_FONT}">{html.escape(line)}</text>'
        )
        y += line_height
    width = min(max_width + 8, int(math.ceil(max_line_width)) + 10)
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
    title_size: int = 24,
    body_size: int = 21,
) -> dict[str, Any]:
    title_lines = wrap_text(title, title_size, max_width) if title else []
    body_lines = wrap_text(body, body_size, max_width) if body else []
    y = int(title_size * 1.05)
    text_nodes: list[str] = []
    max_line_width = 1.0
    for line in title_lines:
        if line is None:
            y += int(title_size * 0.65)
            continue
        max_line_width = max(max_line_width, token_width(line, title_size))
        text_nodes.append(
            f'<text x="0" y="{y}" font-size="{title_size}" font-weight="700" '
            f'fill="{color}" font-family="{HANDWRITING_FONT}">{html.escape(line)}</text>'
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
            f'<text x="0" y="{y}" font-size="{body_size}" fill="{color}" '
            f'font-family="{HANDWRITING_FONT}">{html.escape(line)}</text>'
        )
        y += int(body_size * 1.58)
    width = min(max_width + 8, int(math.ceil(max_line_width)) + 10)
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
) -> dict[str, Any]:
    element = base_element(rng, "rectangle", x, y, width, height, now)
    element.update(
        {
            "strokeColor": stroke,
            "backgroundColor": "transparent",
            "strokeWidth": stroke_width,
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
) -> dict[str, Any]:
    element = base_element(rng, "diamond", x, y, width, height, now)
    element.update(
        {
            "strokeColor": stroke,
            "backgroundColor": "transparent",
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
) -> dict[str, Any]:
    element = base_element(rng, "ellipse", x, y, width, height, now)
    element.update(
        {
            "strokeColor": stroke,
            "backgroundColor": "transparent",
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
) -> dict[str, Any]:
    element = base_element(rng, "arrow", x1, y1, x2 - x1, y2 - y1, now)
    element.update(
        {
            "strokeColor": "#2563eb",
            "backgroundColor": "transparent",
            "roundness": None,
            "points": [[0, 0], [x2 - x1, y2 - y1]],
            "lastCommittedPoint": None,
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": None,
            "endArrowhead": "arrow",
            "strokeWidth": 3,
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


def block_shape(block: dict[str, Any]) -> str:
    shape = str(block.get("shape") or "").lower()
    kind = block_kind(block)
    if shape in {"diamond", "decision"} or kind in {"decision", "question", "choice"}:
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


def build_diagram_scene(
    content: dict[str, Any],
    slug: str,
) -> tuple[dict[str, Any], dict[str, Any], int, int]:
    rng = random.Random(20260616)
    now = int(time.time() * 1000)
    canvas_width = int(dimension(content.get("width"), 1760, 1760))
    margin = 80
    content_width = canvas_width - margin * 2
    elements: list[dict[str, Any]] = []
    files: dict[str, Any] = {}
    blocks_svg: dict[str, Any] = {
        "title": text_block_svg(str(content.get("title", "Script Card")), 42, 1320, "#111827", 14, 22),
    }
    add_image_block(elements, files, rng, "title", blocks_svg["title"], margin, 70, now)
    y_cursor = 70 + blocks_svg["title"]["height"] + 42
    summary = str(content.get("summary") or "")
    if summary:
        blocks_svg["summary"] = text_block_svg(summary, 28, int(content_width), "#374151", 12, 18)
        add_image_block(elements, files, rng, "summary", blocks_svg["summary"], margin, y_cursor, now)
        y_cursor += blocks_svg["summary"]["height"] + 64

    raw_blocks = content.get("blocks") or content.get("nodes") or []
    diagram_blocks = [normalize_block(block, index) for index, block in enumerate(raw_blocks)]
    layout = str(content.get("layout") or "auto")
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
        stroke = str(block.get("stroke") or block_stroke(block))
        shape = block_shape(block)
        if shape == "diamond":
            elements.append(diamond(rng, x, y, w, h, stroke, 3, now))
            text_w = int(max(160, w * 0.62))
            text_x = x + (w - text_w) / 2
            text_y = y + h * 0.22
        elif shape == "ellipse":
            elements.append(ellipse(rng, x, y, w, h, stroke, 3 if stroke == "#2563eb" else 2, now))
            text_w = int(max(160, w * 0.68))
            text_x = x + (w - text_w) / 2
            text_y = y + h * 0.24
        else:
            elements.append(rectangle(rng, x, y, w, h, stroke, 3 if stroke == "#2563eb" else 2, now))
            text_w = int(max(180, w - 48))
            text_x = x + 24
            text_y = y + 28
        key = f"block{block_id}"
        blocks_svg[key] = rich_text_block_svg(
            str(block.get("title") or ""),
            str(block.get("body") or ""),
            text_w,
            stroke if stroke != "#111827" else "#111827",
        )
        add_image_block(elements, files, rng, key, blocks_svg[key], text_x, text_y, now)

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
        src = str(connector.get("from") or connector.get("source") or "")
        dst = str(connector.get("to") or connector.get("target") or "")
        if src not in positions or dst not in positions:
            continue
        x1, y1, x2, y2 = connector_points(positions[src], positions[dst])
        elements.append(arrow(rng, x1, y1, x2, y2, now))
        label = str(connector.get("label") or "")
        if label:
            key = f"connector{index}"
            blocks_svg[key] = text_block_svg(label, 18, 190, "#1e3a8a", 8, 10)
            add_image_block(
                elements,
                files,
                rng,
                key,
                blocks_svg[key],
                (x1 + x2) / 2 - blocks_svg[key]["width"] / 2,
                (y1 + y2) / 2 - 38,
                now,
            )

    max_y = max((y + h for x, y, w, h in positions.values()), default=y_cursor)
    for index, callout in enumerate(content.get("callouts") or []):
        x = dimension(callout.get("x"), margin + (index % 2) * 820, canvas_width)
        y = dimension(callout.get("y"), max_y + 60 + (index // 2) * 190, 2000)
        w = dimension(callout.get("width") or callout.get("w"), 760, content_width)
        h = dimension(callout.get("height") or callout.get("h"), 160, 600)
        stroke = str(callout.get("stroke") or "#b91c1c")
        elements.append(rectangle(rng, x, y, w, h, stroke, 2, now))
        key = f"callout{index}"
        blocks_svg[key] = rich_text_block_svg(
            str(callout.get("title") or "Caveat"),
            str(callout.get("body") or callout.get("text") or ""),
            int(w - 48),
            stroke,
            22,
            20,
        )
        add_image_block(elements, files, rng, key, blocks_svg[key], x + 24, y + 26, now)
        max_y = max(max_y, y + h)

    talk_track = content.get("talk_track") or content.get("short") or ""
    if isinstance(talk_track, list):
        talk_track = "\n".join(str(item) for item in talk_track)
    if talk_track:
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
    if content.get("blocks") or content.get("nodes"):
        return build_diagram_scene(content, slug)
    return build_legacy_scene(content, slug)


def svg_image_tag(block: dict[str, Any], x: float, y: float) -> str:
    inner_svg = block["svg"].split(">", 1)[1].rsplit("</svg>", 1)[0]
    return (
        f'<g transform="translate({x:.0f} {y:.0f})">'
        f"{inner_svg}</g>"
    )


def render_preview_svg(scene: dict[str, Any], blocks: dict[str, Any], width: int, height: int) -> str:
    nodes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
    ]
    for element in scene["elements"]:
        if element["type"] == "rectangle":
            nodes.append(
                f'<rect x="{element["x"]:.0f}" y="{element["y"]:.0f}" '
                f'width="{element["width"]:.0f}" height="{element["height"]:.0f}" '
                f'rx="28" ry="28" fill="none" stroke="{element["strokeColor"]}" '
                f'stroke-width="{element["strokeWidth"]}" />'
            )
        elif element["type"] == "ellipse":
            nodes.append(
                f'<ellipse cx="{element["x"] + element["width"] / 2:.0f}" '
                f'cy="{element["y"] + element["height"] / 2:.0f}" '
                f'rx="{element["width"] / 2:.0f}" ry="{element["height"] / 2:.0f}" '
                f'fill="none" stroke="{element["strokeColor"]}" '
                f'stroke-width="{element["strokeWidth"]}" />'
            )
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
            nodes.append(
                f'<polygon points="{point_text}" fill="none" stroke="{element["strokeColor"]}" '
                f'stroke-width="{element["strokeWidth"]}" />'
            )
        elif element["type"] == "arrow":
            x1 = element["x"]
            y1 = element["y"]
            x2 = x1 + element["width"]
            y2 = y1 + element["height"]
            marker_id = f"arrow-{element['id']}"
            nodes.append(
                f'<defs><marker id="{marker_id}" markerWidth="10" markerHeight="10" '
                'refX="8" refY="3" orient="auto" markerUnits="strokeWidth">'
                f'<path d="M0,0 L0,6 L9,3 z" fill="{element["strokeColor"]}" />'
                "</marker></defs>"
            )
            nodes.append(
                f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
                f'stroke="{element["strokeColor"]}" stroke-width="4" '
                f'marker-end="url(#{marker_id})" />'
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
