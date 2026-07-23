#!/usr/bin/env python3
"""Build the verified 12-week curriculum, printable pages, and coach manifests.

Generation is deliberately fail-closed: every run performs the live source
verification before it writes a page.  The reviewed source manifest is the
only place where an external page title or fragment may enter the generated
site.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence

from curriculum_model import (
    ROOT,
    CurriculumError,
    CurriculumModel,
    day_date,
    load_model,
    scheduled_algorithms,
    validate_model,
)


SITE_TITLE = "12 周系统设计完整学习路线"
PUBLIC_BASE = "https://danielwanwx.github.io/crack-system-interview-skill"


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def compact_unique(items: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def source_ref(
    model: CurriculumModel,
    source_id: str,
    heading: str,
    *,
    class_name: str = "source-link",
) -> str:
    page_title = model.resolver.page_title(source_id)
    href = model.resolver.href(source_id, heading)
    label = f"{page_title} · {heading}"
    return (
        f'<a class="{esc(class_name)}" href="{esc(href)}" target="_blank" '
        f'rel="noreferrer">{esc(label)}</a>'
    )


def source_records(
    model: CurriculumModel,
    refs: Iterable[tuple[str, str]],
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for source_id, heading in compact_unique(refs):
        result.append(
            {
                "source_id": source_id,
                "page_title": model.resolver.page_title(source_id),
                "heading": heading,
                "url": model.resolver.href(source_id, heading),
            }
        )
    return result


def project_read_refs(project: dict[str, Any]) -> list[tuple[str, str]]:
    return [(str(project["source"]), str(heading)) for heading in project["read"]["headings"]]


def project_deep_refs(project: dict[str, Any]) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    for heading in project["deep"]["headings"]:
        source_id = (
            str(project["deep"].get("senior_source"))
            if (
                heading == "Senior"
                and project["deep"].get("senior_source")
                and not project["deep"].get("senior_headings")
            )
            else str(project["source"])
        )
        refs.append((source_id, str(heading)))
    refs.extend(
        (
            str(project["deep"]["senior_source"]),
            str(heading),
        )
        for heading in project["deep"].get("senior_headings", [])
    )
    refs.extend(
        (str(ref["source"]), str(ref["heading"]))
        for group in ("concepts", "ddia", "ai_extensions")
        for ref in project.get(group, [])
    )
    return compact_unique(refs)


def project_senior_refs(project: dict[str, Any]) -> list[tuple[str, str]]:
    senior_headings = project["deep"].get("senior_headings", [])
    if senior_headings:
        return [
            (str(project["deep"]["senior_source"]), str(heading))
            for heading in senior_headings
        ]
    return [
        (
            str(project["deep"].get("senior_source") or project["source"]),
            "Senior",
        )
    ]


def qa_refs(project: dict[str, Any]) -> list[tuple[str, str]]:
    return compact_unique(
        (str(ref["source"]), str(ref["heading"]))
        for qa in project.get("staff_qa", [])
        for ref in qa.get("sources", [])
    )


def week_all_refs(case_week: dict[str, Any]) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    for project in case_week["projects"]:
        refs.extend(project_read_refs(project))
        refs.extend(project_deep_refs(project))
        refs.extend(qa_refs(project))
    return compact_unique(refs)


def nav(prefix: str, week: int | None = None) -> str:
    items = [
        (f"{prefix}index.html", "首页"),
        (f"{prefix}system-design-project-route.html", "12 周路线"),
        (f"{prefix}coverage-matrix.html", "30 题矩阵"),
    ]
    if week is not None:
        items.extend(
            [
                (f"{prefix}week{week}-action-guide.html", f"第 {week} 周"),
                (f"{prefix}week{week}/lecture.html", "中文讲义"),
                (f"{prefix}week{week}/staff-qa.html", "Staff Q&A"),
                (f"{prefix}week{week}/live-mock.html", "Live Mock"),
                (f"{prefix}week{week}/scorecard.html", "复盘"),
            ]
        )
    links = "".join(f'<a href="{esc(href)}">{esc(label)}</a>' for href, label in items)
    return (
        '<header class="site-header"><a class="brand" href="'
        f'{esc(prefix)}index.html"><span>CS</span> Crack System</a>'
        f'<nav aria-label="主导航">{links}</nav></header>'
    )


def page(
    *,
    title: str,
    eyebrow: str,
    content: str,
    prefix: str = "",
    week: int | None = None,
    description: str = "",
    show_hero: bool = True,
) -> str:
    full_title = SITE_TITLE if title == SITE_TITLE else f"{title} · {SITE_TITLE}"
    hero = (
        '<section class="hero compact">'
        f'<p class="eyebrow">{esc(eyebrow)}</p>'
        f"<h1>{esc(title)}</h1>"
        + (f'<p class="lede">{esc(description)}</p>' if description else "")
        + "</section>"
        if show_hero
        else ""
    )
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{esc(description or title)}">
  <title>{esc(full_title)}</title>
  <link rel="stylesheet" href="{esc(prefix)}assets/curriculum.css">
</head>
<body>
  {nav(prefix, week)}
  <main>
    {hero}
    {content}
  </main>
  <footer>由可验证源清单生成 · 外链标题与锚点在构建前逐一在线核验 · {SITE_TITLE}</footer>
  <script src="{esc(prefix)}assets/curriculum.js"></script>
</body>
</html>
"""
    return "\n".join(line.rstrip() for line in document.splitlines()) + "\n"


def bullets(values: Sequence[str], class_name: str = "") -> str:
    css = f' class="{esc(class_name)}"' if class_name else ""
    return f"<ul{css}>" + "".join(f"<li>{esc(value)}</li>" for value in values) + "</ul>"


def source_list(
    model: CurriculumModel,
    refs: Iterable[tuple[str, str]],
    *,
    ordered: bool = False,
) -> str:
    tag = "ol" if ordered else "ul"
    rows = "".join(
        f"<li>{source_ref(model, source_id, heading)}</li>"
        for source_id, heading in compact_unique(refs)
    )
    return f'<{tag} class="source-list">{rows}</{tag}>'


def daily_time_blocks(kind: str, focus: str) -> list[tuple[str, str, str]]:
    algorithm = [
        ("07:30–08:00", "算法 1", "独立作答；写出复杂度和一个反例。"),
        ("08:00–08:30", "算法 2", "延续同一 NeetCode tag block，不跨 tag 拼题。"),
        ("12:20–12:50", "算法 3", "计时完成；只记录错因与下一次修复动作。"),
    ]
    if kind == "project-read":
        design = [
            ("19:30–20:00", "问题框定", "先写 FR/NFR、容量假设和不做什么；暂不画扩展组件。"),
            (
                "20:00–21:20",
                "连续完整通读",
                f"从 Understanding/Understand the Problem 按原文顺序读到 High-Level Design：{focus}。",
            ),
            ("21:20–21:50", "关页重建", "不看答案重画 API、数据模型、读写路径和权威状态。"),
            ("21:50–22:10", "验收与修复", "逐条核对验收标准；不通过就执行当天 repair，不用补读掩盖。"),
        ]
    elif kind == "project-deep":
        design = [
            ("19:30–20:20", "Deep Dives", f"围绕 {focus} 逐个回答机制、规模阈值和失败语义。"),
            ("20:20–20:50", "精确补课", "只读今天列出的 Core / Technology / Pattern / DDIA 小节。"),
            ("20:50–21:30", "Senior/Staff 追问", "先口述回答，再对照详细答案；为每个追问写证据。"),
            ("21:30–22:10", "故障注入与修复", "把超时、重复、乱序、热点或部分失败注入白板后重答。"),
        ]
    elif kind == "mock":
        design = [
            ("19:30–20:15", "无资料 Mock", f"由 GPT Live 从 {focus} 随机抽题，候选人独立推进。"),
            ("20:15–20:45", "追问压力段", "面试官只追边界、热点、一致性和恢复，不给方案提示。"),
            ("20:45–21:25", "证据复盘", "按 scorecard 找出最低维度，定位到具体遗漏句或图。"),
            ("21:25–22:10", "定向复测", "只重做最低维度；能在相同追问下清楚修正才算完成。"),
        ]
    elif kind == "repair":
        design = [
            ("19:30–20:00", "弱项排序", "只选一个可观察的最低分维度，写出失败证据。"),
            ("20:00–20:50", "源头修复", f"回到 {focus} 的精确小节，补齐缺失机制与边界。"),
            ("20:50–21:30", "重画/重述", "删除错误分支，重建端到端时序与失败处理。"),
            ("21:30–22:10", "盲测", "由 GPT Live 换一种问法复测；未过则记录下周首个 repair。"),
        ]
    else:
        design = [
            ("19:30–20:10", "跨题对照", f"围绕 {focus} 比较同一机制在不同产品语义下的变化。"),
            ("20:10–20:50", "机制整合", "把 API、数据、缓存、索引、网络与一致性连成端到端路径。"),
            ("20:50–21:30", "故障演练", "选择一次最危险的部分失败，明确检测、隔离、恢复和补偿。"),
            ("21:30–22:10", "口述验收", "完成 15 分钟设计陈述，并用 scorecard 记录唯一最低项。"),
        ]
    return algorithm + design


def time_table(blocks: Sequence[tuple[str, str, str]]) -> str:
    rows = "".join(
        f"<tr><td>{esc(period)}</td><th>{esc(title)}</th><td>{esc(detail)}</td></tr>"
        for period, title, detail in blocks
    )
    return (
        '<div class="table-wrap"><table class="schedule">'
        "<thead><tr><th>时间</th><th>阶段</th><th>执行方式</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def algorithm_panel(
    model: CurriculumModel,
    block_id: str,
    day_number: int,
) -> tuple[str, dict[str, Any]]:
    tag, mode, problems = scheduled_algorithms(model, block_id, day_number)
    mode_labels = {
        "new": "新题：完整建模",
        "review": "复习：关答案复写",
        "mixed": "混合：新题 + 错题复测",
        "timed": "计时：面试节奏",
    }
    cards = "".join(
        '<article class="algo-card">'
        f'<span class="number">{index}</span>'
        f'<a href="{esc(problem["url"])}" target="_blank" rel="noreferrer">{esc(problem["title"])}</a>'
        f'<code>{esc(problem["slug"])}</code>'
        "</article>"
        for index, problem in enumerate(problems, start=1)
    )
    payload = {
        "tag": tag,
        "mode": mode,
        "problems": [
            {
                "title": str(problem["title"]),
                "slug": str(problem["slug"]),
                "url": str(problem["url"]),
            }
            for problem in problems
        ],
    }
    return (
        '<section class="panel"><div class="section-heading">'
        f"<div><p class=\"kicker\">NeetCode 连续 Tag Block</p><h2>{esc(tag)}</h2></div>"
        f'<span class="badge">{esc(mode_labels.get(mode, mode))}</span></div>'
        f'<div class="algo-grid">{cards}</div>'
        '<p class="micro">算法与系统设计各自连续推进；不为了主题感制造牵强关联。每天恰好 3 道。</p>'
        "</section>",
        payload,
    )


def day_assignment(
    model: CurriculumModel,
    route_week: dict[str, Any],
    case_week: dict[str, Any],
    day_number: int,
) -> dict[str, Any]:
    route_day = route_week["days"][day_number - 1]
    kind = str(route_day["kind"])
    override = route_day.get("assignment")
    project = (
        model.projects[str(route_day["project"])]
        if route_day.get("project")
        else None
    )
    if kind == "project-read" and project:
        title = f"{project['title']} · 完整通读"
        focus = str(project["title"])
        refs = project_read_refs(project)
        artifact = str(project["read"]["deliverable"])
        acceptance = list(project["read"]["acceptance"])
        repair = str(project["read"]["repair"])
    elif kind == "project-deep" and project:
        title = f"{project['title']} · Deep Dive 与 Senior 修复"
        focus = str(project["title"])
        refs = project_deep_refs(project)
        artifact = str(project["deep"]["deliverable"])
        acceptance = list(project["deep"]["acceptance"])
        repair = str(project["deep"]["repair"])
    else:
        title = str(route_day.get("title") or kind)
        focus = "、".join(str(item["title"]) for item in case_week["projects"])
        refs = compact_unique(
            ref
            for item in case_week["projects"]
            for ref in (
                project_deep_refs(item)
                if kind in {"mock", "repair"}
                else [
                    *(
                        (str(node["source"]), str(node["heading"]))
                        for node in item.get("concepts", [])
                    ),
                    *(
                        (str(node["source"]), str(node["heading"]))
                        for node in item.get("ddia", [])
                    ),
                    *(
                        (str(node["source"]), str(node["heading"]))
                        for node in item.get("ai_extensions", [])
                    ),
                ]
            )
        )
        if kind == "mock":
            artifact = "一份无资料白板、逐字追问记录、scorecard 与最低分维度的修复前后对照。"
            acceptance = [
                "前 5 分钟主动澄清 FR/NFR 与规模，不照背参考架构。",
                "每个新增组件都能对应已证明的瓶颈、正确性边界或故障恢复。",
                "追问后能修正原方案并说明变化，不用术语堆叠逃避具体时序。",
            ]
            repair = "从最低分维度抽取一个失败片段，回到对应精确小节，重画后让 GPT Live 改写问法复测。"
        elif kind == "repair":
            artifact = "本周最低维度的错误证据、修复白板、90 秒重答与一次盲测记录。"
            acceptance = [
                "弱项由具体证据确定，而不是用“整体不熟”描述。",
                "修复后能在不看讲义的情况下给出机制、边界和 failure path。",
                "盲测问题与原问题不同，仍能迁移同一判断。",
            ]
            repair = "盲测未通过时不扩展阅读范围，只保留同一弱项为下一周第一个修复任务。"
        else:
            artifact = "一张跨项目机制对照图，包含不同产品语义下的选型、失效和修复触发器。"
            acceptance = [
                "至少比较两个项目，不把相同组件误当成相同语义。",
                "每条数据路径都有权威状态、派生状态与一致性窗口。",
                "包含一次部分失败的检测、隔离、恢复和可观测证据。",
            ]
            repair = "若对照只剩组件清单，改用同一个失败场景逐题走时序，写出差异来自哪条需求。"

    internal_resources: list[dict[str, str]] = []
    time_blocks = daily_time_blocks(kind, focus)
    if override:
        focus = str(override["focus"])
        refs = [
            (str(ref["source"]), str(ref["heading"]))
            for ref in override["source_refs"]
        ]
        artifact = str(override["artifact"])
        acceptance = [str(item) for item in override["acceptance"]]
        repair = str(override["repair"])
        internal_resources = [
            {"href": str(item["href"]), "label": str(item["label"])}
            for item in override.get("internal_resources", [])
        ]
        time_blocks = [
            *daily_time_blocks(kind, focus)[:3],
            *[
                (
                    str(block["time"]),
                    str(block["title"]),
                    str(block["instruction"]),
                )
                for block in override["design_blocks"]
            ],
        ]
    return {
        "kind": kind,
        "project": project,
        "title": title,
        "focus": focus,
        "refs": refs,
        "artifact": artifact,
        "acceptance": acceptance,
        "repair": repair,
        "internal_resources": internal_resources,
        "time_blocks": time_blocks,
    }


def manifest_day_payload(
    model: CurriculumModel,
    route_week: dict[str, Any],
    case_week: dict[str, Any],
    day_number: int,
    *,
    assignment: dict[str, Any] | None = None,
    algorithms: dict[str, Any] | None = None,
) -> dict[str, Any]:
    week_number = int(route_week["week"])
    resolved_assignment = assignment or day_assignment(
        model, route_week, case_week, day_number
    )
    if algorithms is None:
        tag, mode, problems = scheduled_algorithms(
            model, str(route_week["algorithm_block"]), day_number
        )
        algorithms = {
            "tag": tag,
            "mode": mode,
            "problems": [
                {
                    "title": str(problem["title"]),
                    "slug": str(problem["slug"]),
                    "url": str(problem["url"]),
                }
                for problem in problems
            ],
        }
    date_value = day_date(model, week_number, day_number)
    return {
        "week": week_number,
        "day": day_number,
        "date": date_value.isoformat(),
        "kind": resolved_assignment["kind"],
        "title": resolved_assignment["title"],
        "page": f"week{week_number}/day-{day_number}.html",
        "public_url": f"{PUBLIC_BASE}/week{week_number}/day-{day_number}.html",
        "time_blocks": [
            {"time": period, "title": title, "instruction": instruction}
            for period, title, instruction in resolved_assignment["time_blocks"]
        ],
        "sources": source_records(model, resolved_assignment["refs"]),
        "internal_resources": resolved_assignment["internal_resources"],
        "artifact": resolved_assignment["artifact"],
        "acceptance": resolved_assignment["acceptance"],
        "repair": resolved_assignment["repair"],
        "algorithms": algorithms,
    }


def render_day(
    model: CurriculumModel,
    route_week: dict[str, Any],
    case_week: dict[str, Any],
    day_number: int,
) -> tuple[str, dict[str, Any]]:
    week_number = int(route_week["week"])
    assignment = day_assignment(model, route_week, case_week, day_number)
    algorithm_html, algorithm_data = algorithm_panel(
        model, str(route_week["algorithm_block"]), day_number
    )
    project = assignment["project"]
    refs = assignment["refs"]
    date_value = day_date(model, week_number, day_number)
    sources_heading = (
        "按原文顺序连续通读"
        if assignment["kind"] == "project-read"
        else "今日精确源包"
    )
    source_html = source_list(
        model, refs, ordered=assignment["kind"] == "project-read"
    )
    internal_resources_html = (
        "<h3>站内核对</h3><ul class=\"source-list\">"
        + "".join(
            f'<li><a href="{esc(item["href"])}">{esc(item["label"])}</a></li>'
            for item in assignment["internal_resources"]
        )
        + "</ul>"
        if assignment["internal_resources"]
        else ""
    )
    source_gap_html = (
        '<div class="source-gap"><strong>原项目页缺口</strong>'
        f'<p>{esc(project["deep"]["source_gap"])}</p></div>'
        if project
        and assignment["kind"] == "project-deep"
        and project.get("deep", {}).get("source_gap")
        else ""
    )
    if project and assignment["kind"] == "project-deep":
        qa_preview = "".join(
            '<article class="question-card">'
            f'<p class="kicker">真实追问 {index}</p><h3>{esc(item["question"])}</h3>'
            f'<p><strong>触发：</strong>{esc(item["trigger"])}</p>'
            f'<p><strong>先修：</strong>{esc(item["repair"])}</p></article>'
            for index, item in enumerate(project["staff_qa"][:3], start=1)
        )
    else:
        qa_preview = ""
    content = (
        '<section class="metrics">'
        f'<div><span>Week</span><strong>{week_number:02d}</strong></div>'
        f'<div><span>Day</span><strong>{day_number}</strong></div>'
        f'<div><span>日期</span><strong>{date_value:%m/%d}</strong></div>'
        '<div><span>算法</span><strong>3</strong></div></section>'
        '<section class="panel"><div class="section-heading"><div><p class="kicker">精确时间段</p>'
        f'<h2>{esc(assignment["focus"])}</h2></div><span class="badge">{esc(assignment["kind"])}</span></div>'
        f'{time_table(assignment["time_blocks"])}</section>'
        '<section class="two-col"><article class="panel">'
        f'<p class="kicker">Source packet</p><h2>{esc(sources_heading)}</h2>'
        f'{source_html}{internal_resources_html}{source_gap_html}</article>'
        '<article class="panel"><p class="kicker">今日唯一产出物</p>'
        f'<h2>交付</h2><p>{esc(assignment["artifact"])}</p>'
        f'<h3>验收标准</h3>{bullets(assignment["acceptance"])}'
        f'<div class="repair"><strong>不通过怎么修</strong><p>{esc(assignment["repair"])}</p></div>'
        "</article></section>"
        + (
            f'<section class="panel"><p class="kicker">Senior / Staff pressure test</p>'
            f'<h2>先答，再看完整 Q&A</h2><div class="card-grid">{qa_preview}</div>'
            f'<a class="button" href="staff-qa.html#{esc(project["slug"])}">进入完整追问与答案</a></section>'
            if qa_preview and project
            else ""
        )
        + algorithm_html
        + '<section class="next-prev">'
        + (
            f'<a href="day-{day_number - 1}.html">← Day {day_number - 1}</a>'
            if day_number > 1
            else f'<a href="../week{week_number}-action-guide.html">← 本周总览</a>'
        )
        + (
            f'<a href="day-{day_number + 1}.html">Day {day_number + 1} →</a>'
            if day_number < 7
            else '<a href="scorecard.html">本周复盘 →</a>'
        )
        + "</section>"
    )
    html_text = page(
        title=assignment["title"],
        eyebrow=f"Week {week_number:02d} · Day {day_number} · {date_value.isoformat()}",
        description="当天任务只有明确产出、验收标准与修复路径；读完不等于完成。",
        content=content,
        prefix="../",
        week=week_number,
    )
    manifest_day = manifest_day_payload(
        model,
        route_week,
        case_week,
        day_number,
        assignment=assignment,
        algorithms=algorithm_data,
    )
    return html_text, manifest_day


def render_audio_preview(
    model: CurriculumModel,
    case_week: dict[str, Any],
) -> str:
    preview = case_week["audio_preview"]
    audio = model.audio
    source_id = str(audio["source"])
    configured_heading = str(audio.get("heading") or "")
    if not configured_heading:
        entry = model.resolver.entry(source_id)
        configured_heading = str(entry.get("sections", [{}])[0].get("text") or "")
    if not configured_heading:
        headings = model.resolver.headings(source_id)
        if not headings:
            raise CurriculumError(f"{source_id}: optional audio entry has no verified heading")
        configured_heading = headings[0].text
    optional_link = source_ref(
        model, source_id, configured_heading, class_name="button secondary"
    )
    return (
        '<section class="panel audio"><div class="section-heading"><div>'
        '<p class="kicker">2 分钟中文讲译预听</p>'
        f'<h2>{esc(preview["title"])}</h2></div><span class="badge">不自动生成</span></div>'
        f'<p class="script" id="audio-script">{esc(preview["script"])}</p>'
        '<div class="audio-actions">'
        '<button class="button" type="button" data-copy="#audio-script">复制讲译脚本</button>'
        f"{optional_link}</div>"
        '<dl class="config">'
        f'<div><dt>默认 Voice</dt><dd>{esc(audio["voice"])}</dd></div>'
        f'<div><dt>默认 Model</dt><dd>{esc(audio["model"])}</dd></div>'
        '<div><dt>Credits</dt><dd>页面不调用 API，不批量生成；仅在用户主动选择时进入可选入口。</dd></div>'
        "</dl></section>"
    )


def render_week_guide(
    model: CurriculumModel,
    route_week: dict[str, Any],
    case_week: dict[str, Any],
) -> str:
    week_number = int(route_week["week"])
    project_map = {str(item["slug"]): item for item in case_week["projects"]}
    rows: list[str] = []
    for day_number, route_day in enumerate(route_week["days"], start=1):
        assignment = day_assignment(model, route_week, case_week, day_number)
        rows.append(
            "<tr>"
            f"<td>Day {day_number}<small>{day_date(model, week_number, day_number).isoformat()}</small></td>"
            f'<th><a href="week{week_number}/day-{day_number}.html">{esc(assignment["title"])}</a></th>'
            f"<td>07:30–08:30<br>12:20–12:50<br>19:30–22:10</td>"
            f"<td>{esc(assignment['artifact'])}</td>"
            "</tr>"
        )
    loops = "".join(
        '<article class="project-card">'
        f'<p class="kicker">完整项目闭环</p><h3>{esc(project["title"])}</h3>'
        f'<p><strong>Read：</strong>{esc(project["read"]["deliverable"])}</p>'
        f'<p><strong>Deep：</strong>{esc(project["deep"]["deliverable"])}</p>'
        f'{source_list(model, [project_read_refs(project)[0], project_read_refs(project)[-1], *project_deep_refs(project)[:2]])}'
        "</article>"
        for project in project_map.values()
    )
    content = (
        '<section class="metrics">'
        f'<div><span>项目</span><strong>{len(project_map)}</strong></div>'
        '<div><span>学习日</span><strong>7</strong></div>'
        '<div><span>算法</span><strong>21</strong></div>'
        f'<div><span>源锚点</span><strong>{len(week_all_refs(case_week))}</strong></div></section>'
        '<section class="panel"><div class="section-heading"><div><p class="kicker">Project calendar</p>'
        '<h2>本周日历与精确时间</h2></div>'
        '<div class="page-actions">'
        f'<a class="button" href="week{week_number}/lecture.html">中文讲义</a>'
        f'<a class="button secondary" href="week{week_number}/staff-qa.html">Staff Q&A</a>'
        f'<a class="button secondary" href="week{week_number}/live-mock.html">Mock</a>'
        f'<a class="button secondary" href="week{week_number}/scorecard.html">复盘</a>'
        "</div></div>"
        '<div class="table-wrap"><table class="calendar"><thead><tr>'
        "<th>日期</th><th>任务</th><th>固定时段</th><th>产出</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div></section>"
        f'<section><div class="section-heading"><div><p class="kicker">不是主项目/迁移项目</p>'
        f'<h2>{esc(route_week["theme"])}</h2></div></div><div class="card-grid">{loops}</div></section>'
        + render_audio_preview(model, case_week)
    )
    return page(
        title=f"第 {week_number} 周 · {route_week['theme']}",
        eyebrow=f"Week {week_number:02d} Action Guide",
        description="每个项目都有完整通读日与 Deep Dive/Senior 修复日；复杂度只改变项目数量，不删除学习环节。",
        content=content,
        week=week_number,
    )


def render_lecture(
    model: CurriculumModel,
    route_week: dict[str, Any],
    case_week: dict[str, Any],
) -> str:
    week_number = int(route_week["week"])
    projects_html: list[str] = []
    for project in case_week["projects"]:
        project_packet = compact_unique(
            [
                (str(project["source"]), "High-Level Design"),
                *project_deep_refs(project),
            ]
        )
        sections = "".join(
            '<article class="lecture-section">'
            f'<span class="section-index">{index:02d}</span><div>'
            f'<h3>{esc(item["title"])}</h3><p>{esc(item["body"])}</p>'
            f'<div class="takeaway"><strong>能迁移的判断：</strong>{esc(item["takeaway"])}</div>'
            "</div></article>"
            for index, item in enumerate(project["lecture"], start=1)
        )
        projects_html.append(
            f'<section class="panel lecture-project" id="{esc(project["slug"])}">'
            f'<p class="kicker">{esc(project["title"])}</p>'
            f'<h2>{esc(project["title"])}：从需求语义到故障修复</h2>{sections}'
            '<aside class="source-gap"><strong>项目配套精读</strong>'
            '<p>以下是本项目整组讲义的精确源包，不把同一组链接重复伪装成逐段引文。</p>'
            f'{source_list(model, project_packet)}</aside></section>'
        )
    return page(
        title=f"第 {week_number} 周中文深度讲义",
        eyebrow=f"Week {week_number:02d} · Lecture",
        description="不是摘要：每节都解释为什么、何时失效、如何在白板和追问里证明。",
        content="".join(projects_html),
        prefix="../",
        week=week_number,
    )


def render_staff_qa(
    model: CurriculumModel,
    route_week: dict[str, Any],
    case_week: dict[str, Any],
) -> str:
    week_number = int(route_week["week"])
    groups: list[str] = []
    for project in case_week["projects"]:
        cards = "".join(
            '<article class="qa-card">'
            f'<div class="qa-number">Q{index}</div><div><h3>{esc(qa["question"])}</h3>'
            f'<p class="trigger"><strong>为什么面试官会追：</strong>{esc(qa["trigger"])}</p>'
            f'<div class="answer"><strong>详细回答</strong><p>{esc(qa["answer"])}</p></div>'
            f'<p><strong>继续追问：</strong>{esc(qa["follow_up"])}</p>'
            f'<p><strong>常见漏项：</strong>{esc(qa["common_miss"])}</p>'
            f'<div class="repair"><strong>现场修复</strong><p>{esc(qa["repair"])}</p></div>'
            f'<div class="citations"><span>证据</span>{source_list(model, [(str(ref["source"]), str(ref["heading"])) for ref in qa["sources"]])}</div>'
            "</div></article>"
            for index, qa in enumerate(project["staff_qa"], start=1)
        )
        groups.append(
            f'<section class="panel" id="{esc(project["slug"])}"><p class="kicker">Senior / Staff Drill</p>'
            f'<h2>{esc(project["title"])}</h2><div class="qa-list">{cards}</div></section>'
        )
    return page(
        title=f"第 {week_number} 周 Staff 追问与详细答案",
        eyebrow=f"Week {week_number:02d} · Staff Q&A",
        description="先遮住答案口述；答案必须覆盖判断、机制、失败语义和可验证修复。",
        content="".join(groups),
        prefix="../",
        week=week_number,
    )


def render_mock(
    model: CurriculumModel,
    route_week: dict[str, Any],
    case_week: dict[str, Any],
) -> str:
    week_number = int(route_week["week"])
    rotation = "".join(
        '<article class="project-card">'
        f'<p class="kicker">抽题池</p><h3>{esc(project["title"])}</h3>'
        f'<p>{esc(project["read"]["deliverable"])}</p>'
        f'<h4>Pressure prompts</h4>{bullets([qa["question"] for qa in project["staff_qa"][:3]])}'
        f'{source_list(model, project_deep_refs(project)[:3])}</article>'
        for project in case_week["projects"]
    )
    script = """你是严格的 Senior/Staff 系统设计面试官。随机选本页一个项目，只给题目，不泄露参考架构。前 5 分钟检查需求与规模；之后根据候选人的选择追问热点、正确性边界、部分失败、恢复和可观测性。不要接受 “加缓存、上 Kafka、exactly once” 这类无时序答案。每次只问一个问题，等待回答；最后按本页 scorecard 给出证据、最低维度和一道改写后的复测题。"""
    content = (
        '<section class="panel"><div class="section-heading"><div><p class="kicker">GPT Live Mock</p>'
        '<h2>直接可用的面试官指令</h2></div><button class="button" type="button" data-copy="#mock-script">复制指令</button></div>'
        f'<p class="script" id="mock-script">{esc(script)}</p></section>'
        '<section class="panel"><p class="kicker">45 分钟主循环 + 25 分钟修复</p><h2>时间盒</h2>'
        + time_table(
            [
                ("00:00–05:00", "澄清", "FR/NFR、规模、成功与失败语义。"),
                ("05:00–15:00", "基线", "API、实体、数据模型、可工作的单区 HLD。"),
                ("15:00–30:00", "深挖", "由候选人的选择触发两次机制追问。"),
                ("30:00–40:00", "故障", "注入一次部分失败、热点或乱序。"),
                ("40:00–45:00", "收束", "风险、指标、演进触发器；禁止继续加盒子。"),
                ("45:00–55:00", "评分", "只记录可观察证据与最低维度。"),
                ("55:00–70:00", "修复复测", "回到精确源锚点，重答最低维度。"),
            ]
        )
        + '</section><section><div class="section-heading"><div><p class="kicker">Dynamic rotation</p>'
        '<h2>项目与真实追问池</h2></div></div>'
        f'<div class="card-grid">{rotation}</div></section>'
    )
    return page(
        title=f"第 {week_number} 周 Live Mock",
        eyebrow=f"Week {week_number:02d} · Mock",
        description="Mock 的终点不是一份总评，而是一次有证据的 repair 与改写题复测。",
        content=content,
        prefix="../",
        week=week_number,
    )


def render_scorecard(
    route_week: dict[str, Any],
    case_week: dict[str, Any],
) -> str:
    week_number = int(route_week["week"])
    rubric = [
        ("问题框定", "FR/NFR 可量化；范围与失败语义明确。"),
        ("API 与数据", "契约、幂等键、索引、权威状态能互相推导。"),
        ("高层设计", "先有可工作基线；组件由需求或瓶颈证明。"),
        ("Deep Dive", "能讲机制、阈值、替代方案与故障时序。"),
        ("Senior 判断", "主动管理歧义、取舍、演进和跨团队边界。"),
        ("可靠性", "检测、隔离、重试/补偿、恢复与可观测性闭环。"),
        ("表达", "白板可读，先结论再证据，追问后能修正。"),
    ]
    rows = "".join(
        f"<tr><th>{esc(name)}</th><td>{esc(signal)}</td>"
        '<td class="score-box">□ 0　□ 1　□ 2　□ 3</td><td class="notes"></td></tr>'
        for name, signal in rubric
    )
    projects = bullets([str(project["title"]) for project in case_week["projects"]])
    content = (
        '<section class="panel print-only-friendly"><p class="kicker">Evidence, not vibes</p>'
        '<h2>0–3 分量表</h2><p>0=缺失；1=提示后能补；2=独立完成；3=能解释替代方案、失效与演进触发器。'
        '只记可引用的回答或白板证据。</p>'
        '<div class="table-wrap"><table class="scorecard"><thead><tr><th>维度</th><th>可观察信号</th>'
        f"<th>分数</th><th>证据</th></tr></thead><tbody>{rows}</tbody></table></div></section>"
        '<section class="two-col"><article class="panel"><p class="kicker">本周覆盖</p>'
        f"<h2>项目</h2>{projects}"
        '<h3>三条复盘句</h3><ol><li>我在哪一个追问开始失去因果链？</li>'
        '<li>哪一个组件没有需求或瓶颈证据？</li><li>改写题后，我能否迁移同一判断？</li></ol></article>'
        '<article class="panel"><p class="kicker">Repair contract</p><h2>最低维度修复单</h2>'
        '<p>最低维度：________________</p><p>失败证据：________________</p>'
        '<p>精确源锚点：______________</p><p>删除/改写：_______________</p>'
        '<p>复测题：__________________</p><p>复测证据：________________</p>'
        '<div class="repair"><strong>完成定义</strong><p>不是“看懂了”，而是在新问法下独立得到正确判断。</p></div>'
        "</article></section>"
    )
    return page(
        title=f"第 {week_number} 周评分与修复",
        eyebrow=f"Week {week_number:02d} · Scorecard",
        description="把最弱的一项变成下一次可复测的具体动作。",
        content=content,
        prefix="../",
        week=week_number,
    )


def render_route(model: CurriculumModel) -> str:
    cards: list[str] = []
    for route_week in model.route["weeks"]:
        week_number = int(route_week["week"])
        case_week = model.weeks[week_number]
        projects = " · ".join(str(project["title"]) for project in case_week["projects"])
        read_days = sum(day["kind"] == "project-read" for day in route_week["days"])
        deep_days = sum(day["kind"] == "project-deep" for day in route_week["days"])
        cards.append(
            '<article class="route-card">'
            f'<span class="week-number">{week_number:02d}</span><div>'
            f'<p class="kicker">{esc(route_week["theme"])}</p><h2>{esc(projects)}</h2>'
            f'<p>{read_days} 个完整通读日 · {deep_days} 个 Deep/Senior 日 · 21 道算法</p>'
            f'<a class="button" href="week{week_number}-action-guide.html">打开第 {week_number} 周</a>'
            "</div></article>"
        )
    content = (
        '<section class="metrics"><div><span>周</span><strong>12</strong></div>'
        '<div><span>Hello Interview 项目</span><strong>30</strong></div>'
        '<div><span>算法</span><strong>252</strong></div>'
        '<div><span>项目完整学习日</span><strong>60</strong></div></section>'
        '<section class="panel"><p class="kicker">Route principles</p><h2>内容复杂度决定排期，不决定是否学完整</h2>'
        '<div class="principles"><p><strong>Read Day</strong> 从 Understanding the Problem 连续读到 High-Level Design。</p>'
        '<p><strong>Deep Day</strong> 完成 Potential Deep Dives、Senior 预期、真实追问和修复。</p>'
        '<p><strong>Algorithms</strong> 每天 3 道，按 NeetCode tag block 连续推进。</p>'
        '<p><strong>Applied AI</strong> 只在 ChatGPT 周使用 OpenAI/Anthropic 官方延伸。</p></div></section>'
        f'<section class="route-list">{"".join(cards)}</section>'
    )
    return page(
        title="12 周项目路线",
        eyebrow="Complete Coverage Route",
        description="30 个当前 System Design Question Breakdowns 全覆盖；没有主项目/迁移项目的降级层级。",
        content=content,
    )


def render_coverage(model: CurriculumModel) -> str:
    rows: list[str] = []
    index = 0
    for route_week in model.route["weeks"]:
        week_number = int(route_week["week"])
        for slug in route_week["projects"]:
            index += 1
            project = model.projects[str(slug)]
            first_read = project_read_refs(project)[0]
            last_read = project_read_refs(project)[-1]
            first_deep = project_deep_refs(project)[0]
            senior = project_senior_refs(project)[-1]
            rows.append(
                f"<tr><td>{index:02d}</td><th>{esc(project['title'])}</th><td>W{week_number:02d}</td>"
                f"<td>{source_ref(model, *first_read)}<br>{source_ref(model, *last_read)}</td>"
                f"<td>{source_ref(model, *first_deep)}<br>{source_ref(model, *senior)}</td>"
                f'<td><a href="week{week_number}/lecture.html#{esc(project["slug"])}">讲义</a> · '
                f'<a href="week{week_number}/staff-qa.html#{esc(project["slug"])}">Q&amp;A</a></td></tr>'
            )
    content = (
        '<section class="panel"><div class="section-heading"><div><p class="kicker">Coverage gate</p>'
        '<h2>30 / 30 完整闭环</h2></div><span class="badge">Read 30 · Deep 30</span></div>'
        '<div class="table-wrap"><table class="coverage"><thead><tr><th>#</th><th>原站题目</th><th>周</th>'
        f"<th>完整通读边界</th><th>Deep / Senior 边界</th><th>学习资产</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div></section>"
    )
    return page(
        title="Hello Interview 30 题覆盖矩阵",
        eyebrow="Verified Coverage Matrix",
        description="矩阵直接证明每一题都有一个完整通读日和一个 Deep/Senior 修复日。",
        content=content,
    )


def render_index(model: CurriculumModel) -> str:
    week_cards = "".join(
        '<a class="week-tile" href="'
        f'week{week["week"]}-action-guide.html"><span>W{int(week["week"]):02d}</span>'
        f'<strong>{esc(week["theme"])}</strong><small>'
        + " · ".join(
            esc(model.projects[str(slug)]["title"]) for slug in week["projects"]
        )
        + "</small></a>"
        for week in model.route["weeks"]
    )
    content = (
        '<section class="hero-grid"><div><p class="eyebrow">2026-07-27 开始 · 12 周</p>'
        '<h1>把 30 道系统设计题，学成 30 个完整判断链。</h1>'
        '<p class="lede">每题都先从问题理解连续读到 High-Level Design，再用 Deep Dives、Senior '
        '追问、故障注入和 repair 把“看懂”变成可独立作答。</p>'
        '<div class="page-actions"><a class="button" href="system-design-project-route.html">进入 12 周路线</a>'
        '<a class="button secondary" href="coverage-matrix.html">查看 30 题覆盖证据</a></div></div>'
        '<aside class="hero-note"><p class="kicker">课程不做什么</p><ul><li>不把题目分成主项目与缩水迁移项目。</li>'
        '<li>不把算法题硬绑系统设计主题。</li><li>不自动生成 ElevenLabs 音频或消耗 credits。</li>'
        '<li>不允许未验证的页面级泛链或猜测锚点进入页面。</li></ul></aside></section>'
        '<section class="metrics"><div><span>完整题目</span><strong>30</strong></div>'
        '<div><span>学习日</span><strong>84</strong></div><div><span>算法</span><strong>252</strong></div>'
        '<div><span>每题核心闭环</span><strong>2 日</strong></div></section>'
        '<section><div class="section-heading"><div><p class="kicker">Week by week</p>'
        '<h2>从读扩展到 LLM Serving Capstone</h2></div></div>'
        f'<div class="week-grid">{week_cards}</div></section>'
        '<section class="panel"><p class="kicker">每日完成定义</p><h2>Task → Artifact → Acceptance → Repair</h2>'
        '<p>每个页面只保留执行所需的信息：精确时间段、直达源锚点、唯一产出物、可观察验收标准、'
        '失败后的修复动作，以及独立推进的 3 道算法。配套中文讲义、Staff Q&amp;A、GPT Live Mock 和复盘表。</p></section>'
    )
    return page(
        title=SITE_TITLE,
        eyebrow="Verified, project-complete curriculum",
        description="12 周、30 题、252 道算法；每个外部学习源在生成前在线核验。",
        content=content,
        show_hero=False,
    )


STYLE = r"""
:root{--ink:#13221c;--muted:#5d6d65;--paper:#f6f3eb;--panel:#fffdfa;--line:#d8d7cd;--green:#135f46;--mint:#dcefe5;--amber:#f0b95b;--red:#9b3a35;--blue:#235b78;--shadow:0 18px 45px rgba(26,45,35,.08);font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Noto Sans CJK SC",sans-serif;color:var(--ink);background:var(--paper)}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 90% 0,#e7f2ea 0,transparent 32rem),var(--paper);line-height:1.72}a{color:var(--green);text-underline-offset:3px}a:hover{color:#0a3e2d}.site-header{position:sticky;top:0;z-index:20;display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.8rem max(1.2rem,calc((100vw - 1180px)/2));background:rgba(246,243,235,.92);border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.brand{display:flex;align-items:center;gap:.65rem;font-weight:800;color:var(--ink);text-decoration:none;white-space:nowrap}.brand span{display:grid;place-items:center;width:2.1rem;height:2.1rem;border-radius:50%;background:var(--ink);color:#fff;font-size:.75rem}.site-header nav{display:flex;gap:.85rem;overflow:auto}.site-header nav a{color:var(--muted);text-decoration:none;font-size:.86rem;white-space:nowrap}.site-header nav a:hover{color:var(--ink)}main{max-width:1180px;margin:0 auto;padding:2rem 1.2rem 5rem}.hero{padding:4rem 0 2.5rem}.hero.compact{padding:2.7rem 0 1.4rem}.hero-grid{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(280px,.55fr);gap:2rem;align-items:end;padding:5rem 0 3rem}.hero h1,.hero-grid h1{max-width:920px;margin:.2rem 0;font-family:Georgia,"Songti SC",serif;font-size:clamp(2.5rem,6vw,5.5rem);line-height:1.03;letter-spacing:-.045em}.hero.compact h1{font-size:clamp(2.3rem,5vw,4.4rem)}.eyebrow,.kicker{text-transform:uppercase;letter-spacing:.14em;font-size:.72rem;font-weight:800;color:var(--green);margin:0}.lede{max-width:780px;color:var(--muted);font-size:1.08rem}.hero-note{background:var(--ink);color:#eef5f0;padding:1.5rem;border-radius:1.2rem;box-shadow:var(--shadow);transform:rotate(1deg)}.hero-note .kicker{color:#8fd2b5}.hero-note ul{padding-left:1.15rem}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;border:1px solid var(--line);background:var(--line);border-radius:1rem;overflow:hidden;margin:1.2rem 0 2.5rem}.metrics div{background:var(--panel);padding:1.1rem 1.25rem}.metrics span{display:block;color:var(--muted);font-size:.75rem;text-transform:uppercase;letter-spacing:.08em}.metrics strong{display:block;font-family:Georgia,serif;font-size:2.1rem;line-height:1.15}.panel{background:rgba(255,253,250,.92);border:1px solid var(--line);border-radius:1.2rem;padding:clamp(1.1rem,3vw,2rem);box-shadow:var(--shadow);margin:1.2rem 0}.section-heading{display:flex;justify-content:space-between;align-items:end;gap:1rem;margin:0 0 1.2rem}.section-heading h2,.panel>h2{margin:.2rem 0;font-family:Georgia,"Songti SC",serif;font-size:clamp(1.5rem,3vw,2.3rem);line-height:1.15}.badge{display:inline-flex;align-items:center;padding:.35rem .7rem;border-radius:99rem;background:var(--mint);color:var(--green);font-size:.73rem;font-weight:800;white-space:nowrap}.button{display:inline-flex;align-items:center;justify-content:center;border:0;border-radius:.7rem;padding:.68rem .95rem;background:var(--green);color:white!important;text-decoration:none;font:inherit;font-size:.86rem;font-weight:750;cursor:pointer}.button.secondary{background:transparent;color:var(--green)!important;border:1px solid #9db8aa}.page-actions,.audio-actions{display:flex;gap:.6rem;flex-wrap:wrap}.two-col{display:grid;grid-template-columns:1fr 1fr;gap:1.2rem}.card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:1rem}.project-card,.question-card{background:var(--panel);border:1px solid var(--line);border-radius:1rem;padding:1.25rem}.project-card h3,.question-card h3{margin:.25rem 0 .7rem}.source-list{padding-left:1.15rem}.source-list li{margin:.48rem 0}.source-link{font-weight:650;overflow-wrap:anywhere}.source-gap{border-left:4px solid var(--amber);background:#fff7e6;padding:.85rem 1rem;margin-top:1rem}.source-gap p{margin:.25rem 0}.repair{border-left:4px solid var(--red);background:#fff3f0;padding:.85rem 1rem;margin-top:1rem}.repair p{margin:.25rem 0}.takeaway{border-left:4px solid var(--green);background:#edf8f1;padding:.85rem 1rem;margin-top:.85rem}.table-wrap{overflow-x:auto}.schedule,.calendar,.coverage,.scorecard{width:100%;border-collapse:collapse;min-width:720px}.schedule th,.schedule td,.calendar th,.calendar td,.coverage th,.coverage td,.scorecard th,.scorecard td{padding:.85rem .75rem;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}thead th{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}tbody th{font-weight:750}.schedule td:first-child{white-space:nowrap;font-variant-numeric:tabular-nums}.calendar small{display:block;color:var(--muted)}.algo-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.8rem}.algo-card{position:relative;display:flex;flex-direction:column;gap:.35rem;min-height:130px;padding:1rem;border:1px solid var(--line);border-radius:.9rem;background:#fbfaf5}.algo-card .number{width:1.7rem;height:1.7rem;display:grid;place-items:center;border-radius:50%;background:var(--ink);color:white;font-size:.75rem}.algo-card a{font-weight:800;font-size:1.02rem}.algo-card code{color:var(--muted);font-size:.7rem;overflow-wrap:anywhere}.micro{color:var(--muted);font-size:.82rem}.config{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:.8rem;overflow:hidden;margin-top:1.2rem}.config div{background:#fbfaf5;padding:.9rem}.config dt{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.08em}.config dd{margin:.2rem 0 0;font-weight:700}.script{white-space:pre-wrap;background:#f1efe7;border-radius:.9rem;padding:1.2rem}.week-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem}.week-tile{display:flex;flex-direction:column;gap:.45rem;min-height:170px;padding:1.2rem;background:var(--panel);border:1px solid var(--line);border-radius:1rem;text-decoration:none;box-shadow:0 8px 22px rgba(26,45,35,.04)}.week-tile:hover{transform:translateY(-2px);box-shadow:var(--shadow)}.week-tile span{font-family:Georgia,serif;font-size:2rem;color:var(--amber)}.week-tile strong{color:var(--ink);font-size:1.02rem}.week-tile small{color:var(--muted)}.route-list{display:grid;gap:.9rem}.route-card{display:grid;grid-template-columns:100px 1fr;gap:1.2rem;padding:1.4rem;border-top:1px solid var(--line)}.week-number{font:3rem/1 Georgia,serif;color:var(--amber)}.route-card h2{margin:.2rem 0 .5rem;font-size:1.35rem}.principles{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem}.principles p{border-top:3px solid var(--green);padding-top:.7rem}.lecture-section{display:grid;grid-template-columns:52px 1fr;gap:1rem;padding:1.5rem 0;border-top:1px solid var(--line)}.lecture-section h3{font-size:1.3rem;margin:0 0 .6rem}.lecture-section p{font-size:1.02rem}.section-index{font:1.5rem Georgia,serif;color:var(--amber)}.citations{margin-top:.8rem;font-size:.84rem}.citations .source-list{margin:.3rem 0}.qa-list{display:grid;gap:1rem}.qa-card{display:grid;grid-template-columns:58px 1fr;gap:1rem;padding:1.3rem 0;border-top:1px solid var(--line)}.qa-number{display:grid;place-items:center;width:48px;height:48px;border-radius:50%;background:var(--ink);color:white;font-weight:800}.qa-card h3{font-size:1.28rem;margin:0 0 .7rem}.trigger{color:var(--muted)}.answer{background:#edf8f1;padding:1rem;border-radius:.8rem}.answer p{margin:.35rem 0}.score-box{white-space:nowrap}.notes{min-width:180px;height:70px}.next-prev{display:flex;justify-content:space-between;margin-top:1.5rem}.next-prev a{font-weight:750}.coverage td:nth-child(4),.coverage td:nth-child(5){min-width:300px}footer{padding:2rem;text-align:center;border-top:1px solid var(--line);color:var(--muted);font-size:.78rem}
@media(max-width:860px){.hero-grid,.two-col{grid-template-columns:1fr}.hero-grid{padding-top:3rem}.metrics{grid-template-columns:repeat(2,1fr)}.week-grid{grid-template-columns:repeat(2,1fr)}.principles{grid-template-columns:1fr 1fr}.algo-grid{grid-template-columns:1fr}.config{grid-template-columns:1fr}.site-header{align-items:flex-start;flex-direction:column}.site-header nav{width:100%}}
@media(max-width:520px){main{padding-inline:.8rem}.hero h1,.hero-grid h1{letter-spacing:-.025em}.week-grid{grid-template-columns:1fr}.metrics{grid-template-columns:1fr 1fr}.section-heading{align-items:flex-start;flex-direction:column}.route-card{grid-template-columns:55px 1fr;padding-inline:.3rem}.week-number{font-size:2rem}.principles{grid-template-columns:1fr}.qa-card{grid-template-columns:1fr}.page-actions{width:100%}.page-actions .button{flex:1}.panel{border-radius:.8rem}}
@media print{.site-header,footer,.button,.next-prev{display:none!important}body{background:white;color:black}.panel,.project-card,.question-card{box-shadow:none;break-inside:avoid}.hero,.hero.compact{padding:1rem 0}.source-link{color:black}.table-wrap{overflow:visible}main{max-width:none;padding:.5rem}.lecture-section,.qa-card{break-inside:avoid}}
"""


SCRIPT = r"""
document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-copy]");
  if (!button) return;
  const target = document.querySelector(button.dataset.copy);
  if (!target) return;
  await navigator.clipboard.writeText(target.textContent.trim());
  const previous = button.textContent;
  button.textContent = "已复制";
  setTimeout(() => { button.textContent = previous; }, 1400);
});
"""


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


GENERATED_INDEX = Path("docs/.curriculum-generated-files.json")
GENERATED_ROOT_FILES = {
    Path("docs/.nojekyll"),
    GENERATED_INDEX,
    Path("docs/index.html"),
    Path("docs/system-design-project-route.html"),
    Path("docs/coverage-matrix.html"),
    Path("docs/source-verification.json"),
    Path("docs/project-driven-picture.html"),
    Path("docs/assets/curriculum.css"),
    Path("docs/assets/curriculum.js"),
}
GENERATED_WEEK_FILES = {
    "lecture.html",
    "staff-qa.html",
    "live-mock.html",
    "scorecard.html",
    "style.css",
}
LEGACY_DAY_FILE = re.compile(r"day-[1-7](?:-[a-z0-9-]+)?\.html")


def _is_known_generated_path(relative: Path) -> bool:
    if relative in GENERATED_ROOT_FILES:
        return True
    parts = relative.parts
    if (
        len(parts) == 2
        and parts[0] == "docs"
        and re.fullmatch(r"week(?:[1-9]|1[0-8])-action-guide\.html", parts[1])
    ):
        return True
    if (
        len(parts) == 3
        and parts[0] == "docs"
        and re.fullmatch(r"week(?:[1-9]|1[0-8])", parts[1])
        and (parts[2] in GENERATED_WEEK_FILES or LEGACY_DAY_FILE.fullmatch(parts[2]))
    ):
        return True
    return bool(
        len(parts) == 2
        and parts[0] == "curriculum"
        and re.fullmatch(r"week-(?:0[1-9]|1[0-8])\.json", parts[1])
    )


def _validate_relative(relative: Path) -> None:
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise CurriculumError(f"unsafe generated path: {relative}")
    if not _is_known_generated_path(relative):
        raise CurriculumError(f"path is outside the generated allowlist: {relative}")


def _safe_target(target_root: Path, relative: Path) -> Path:
    _validate_relative(relative)
    root = target_root.resolve()
    destination = target_root / relative
    try:
        destination.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise CurriculumError(f"generated path escapes repository: {relative}") from exc
    return destination


def _legacy_generated_paths(target_root: Path) -> set[Path]:
    """Return only files owned by this generator, never whole directories."""

    candidates = set(GENERATED_ROOT_FILES)
    for week_number in range(1, 19):
        candidates.add(Path(f"docs/week{week_number}-action-guide.html"))
        for filename in GENERATED_WEEK_FILES:
            candidates.add(Path(f"docs/week{week_number}/{filename}"))
        week_dir = target_root / "docs" / f"week{week_number}"
        if week_dir.is_dir() and not week_dir.is_symlink():
            for path in week_dir.iterdir():
                if path.is_file() and LEGACY_DAY_FILE.fullmatch(path.name):
                    candidates.add(path.relative_to(target_root))
        candidates.add(Path(f"curriculum/week-{week_number:02d}.json"))

    index_path = target_root / GENERATED_INDEX
    if index_path.is_file() and not index_path.is_symlink():
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            for raw in payload.get("files", []):
                relative = Path(str(raw))
                _validate_relative(relative)
                candidates.add(relative)
        except (json.JSONDecodeError, AttributeError, TypeError) as exc:
            raise CurriculumError(f"invalid generated-file index: {exc}") from exc
    return candidates


def _copy_atomically(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def _publish_staged(
    stage_root: Path,
    target_root: Path,
    generated_paths: set[Path],
) -> None:
    """Publish a fully rendered tree transactionally and delete only owned files."""

    if not generated_paths or GENERATED_INDEX not in generated_paths:
        raise CurriculumError("staged build is incomplete: generated index is missing")
    previous_paths = _legacy_generated_paths(target_root)
    affected = previous_paths | generated_paths

    for relative in affected:
        destination = _safe_target(target_root, relative)
        if destination.is_symlink():
            raise CurriculumError(f"refusing to replace generated symlink: {relative}")
        if destination.exists() and not destination.is_file():
            raise CurriculumError(f"generated destination is not a file: {relative}")
    for relative in generated_paths:
        source = stage_root / relative
        if not source.is_file() or source.is_symlink():
            raise CurriculumError(f"staged output is missing or unsafe: {relative}")

    with tempfile.TemporaryDirectory(prefix="curriculum-publish-backup-") as backup_name:
        backup_root = Path(backup_name)
        existed: set[Path] = set()
        for relative in affected:
            destination = target_root / relative
            if destination.is_file():
                backup = backup_root / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup)
                existed.add(relative)
        try:
            for relative in sorted(generated_paths, key=str):
                _copy_atomically(stage_root / relative, target_root / relative)
            for relative in sorted(previous_paths - generated_paths, key=str):
                destination = target_root / relative
                if destination.is_file():
                    destination.unlink()
        except Exception:
            for relative in affected:
                destination = target_root / relative
                if relative in existed:
                    _copy_atomically(backup_root / relative, destination)
                elif destination.is_file() and not destination.is_symlink():
                    destination.unlink()
            raise

    # Remove only directories that became empty after stale generated files left.
    for week_number in range(18, 0, -1):
        directory = target_root / "docs" / f"week{week_number}"
        if directory.is_dir() and not directory.is_symlink():
            try:
                directory.rmdir()
            except OSError:
                pass


def _render_staged(
    model: CurriculumModel,
    live_report: dict[str, Any],
    stage_root: Path,
) -> set[Path]:
    docs = stage_root / "docs"
    curriculum = stage_root / "curriculum"
    write_text(docs / ".nojekyll", "")
    write_text(docs / "assets" / "curriculum.css", STYLE.strip() + "\n")
    write_text(docs / "assets" / "curriculum.js", SCRIPT.strip() + "\n")
    write_text(docs / "index.html", render_index(model))
    write_text(docs / "system-design-project-route.html", render_route(model))
    write_text(docs / "coverage-matrix.html", render_coverage(model))
    verification_record = {
        "status": "passed",
        "mode": "live",
        "verified_snapshot_generated_at": model.source_manifest.get("generated_at"),
        **live_report,
    }
    write_text(
        docs / "source-verification.json",
        json.dumps(verification_record, ensure_ascii=False, indent=2) + "\n",
    )

    day_page_count = 0
    for route_week in model.route["weeks"]:
        week_number = int(route_week["week"])
        case_week = model.weeks[week_number]
        week_dir = docs / f"week{week_number}"
        write_text(
            docs / f"week{week_number}-action-guide.html",
            render_week_guide(model, route_week, case_week),
        )
        manifest_days: list[dict[str, Any]] = []
        for day_number in range(1, 8):
            day_html, manifest_day = render_day(
                model, route_week, case_week, day_number
            )
            write_text(week_dir / f"day-{day_number}.html", day_html)
            day_page_count += 1
            manifest_days.append(manifest_day)
        write_text(
            week_dir / "lecture.html",
            render_lecture(model, route_week, case_week),
        )
        write_text(
            week_dir / "staff-qa.html",
            render_staff_qa(model, route_week, case_week),
        )
        write_text(
            week_dir / "live-mock.html",
            render_mock(model, route_week, case_week),
        )
        write_text(
            week_dir / "scorecard.html",
            render_scorecard(route_week, case_week),
        )
        manifest = {
            "schema_version": "2.0",
            "week": week_number,
            "theme": route_week["theme"],
            "start_date": manifest_days[0]["date"],
            "end_date": manifest_days[-1]["date"],
            "algorithm_block": route_week["algorithm_block"],
            "projects": [
                {
                    "slug": project["slug"],
                    "title": project["title"],
                    "complete_read_day": next(
                        day["day"]
                        for day in manifest_days
                        if day["kind"] == "project-read"
                        and route_week["days"][day["day"] - 1].get("project")
                        == project["slug"]
                    ),
                    "deep_dive_day": next(
                        day["day"]
                        for day in manifest_days
                        if day["kind"] == "project-deep"
                        and route_week["days"][day["day"] - 1].get("project")
                        == project["slug"]
                    ),
                }
                for project in case_week["projects"]
            ],
            "audio_preview": {
                "title": case_week["audio_preview"]["title"],
                "script": case_week["audio_preview"]["script"],
                "provider": model.audio["provider"],
                "voice": model.audio["voice"],
                "model": model.audio["model"],
                "auto_generate": False,
            },
            "days": manifest_days,
        }
        write_text(
            curriculum / f"week-{week_number:02d}.json",
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )

    generated_paths = {
        path.relative_to(stage_root)
        for path in stage_root.rglob("*")
        if path.is_file()
    }
    if day_page_count != 84:
        raise CurriculumError(f"staged build expected 84 day pages, found {day_page_count}")
    week_manifests = sorted((stage_root / "curriculum").glob("week-*.json"))
    if len(week_manifests) != 12:
        raise CurriculumError(
            f"staged build expected 12 week manifests, found {len(week_manifests)}"
        )
    generated_paths.add(GENERATED_INDEX)
    for relative in generated_paths:
        _validate_relative(relative)
    write_text(
        stage_root / GENERATED_INDEX,
        json.dumps(
            {
                "schema_version": 1,
                "files": [str(path) for path in sorted(generated_paths, key=str)],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    return generated_paths


def build(model: CurriculumModel, live_report: dict[str, Any]) -> None:
    current_manifest_digest = hashlib.sha256(
        (ROOT / "sources" / "source-manifest.json").read_bytes()
    ).hexdigest()
    current_algorithm_digest = hashlib.sha256(
        (ROOT / "curriculum" / "algorithm-blocks.json").read_bytes()
    ).hexdigest()
    if live_report.get("source_manifest_sha256") != current_manifest_digest:
        raise CurriculumError(
            "source manifest changed after live verification; refusing generation"
        )
    if live_report.get("algorithm_blocks_sha256") != current_algorithm_digest:
        raise CurriculumError(
            "algorithm blocks changed after live verification; refusing generation"
        )
    with tempfile.TemporaryDirectory(prefix="curriculum-build-") as stage_name:
        stage_root = Path(stage_name)
        generated_paths = _render_staged(model, live_report, stage_root)
        _publish_staged(stage_root, ROOT, generated_paths)


def verify_live(workers: int) -> dict[str, Any]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "verify_sources.py"),
        "--manifest",
        str(ROOT / "sources" / "source-manifest.json"),
        "--algorithm-blocks",
        str(ROOT / "curriculum" / "algorithm-blocks.json"),
        "--workers",
        str(workers),
    ]
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        if len(detail) > 12000:
            detail = detail[-12000:]
        raise CurriculumError(
            "live source verification failed"
            + (f":\n{detail}" if detail else " without diagnostic output")
        ) from exc
    output = result.stdout.strip()
    if output:
        print(output)
    try:
        return json.loads(output.splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise CurriculumError("source verifier did not return a JSON report") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Live-verify sources and build the 12-week curriculum."
    )
    parser.add_argument("--workers", type=int, default=6)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        live_report = verify_live(args.workers)
        model = load_model(ROOT)
        errors = validate_model(model)
        if errors:
            raise CurriculumError(
                "curriculum model validation failed:\n- " + "\n- ".join(errors)
            )
        build(model, live_report)
    except CurriculumError as exc:
        print(f"build blocked: {exc}", file=sys.stderr)
        return 1
    print("Built 12 weeks, 84 day pages, 30 complete projects, and 252 algorithm slots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
