#!/usr/bin/env python3
"""Shared loading and validation for the 12-week curriculum."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_WEEK_PROJECTS = {
    1: ["bitly", "dropbox"],
    2: ["distributed-rate-limiter", "distributed-cache", "job-scheduler"],
    3: ["whatsapp", "fb-live-comments", "online-chess"],
    4: ["fb-news-feed", "instagram", "youtube"],
    5: ["google-docs", "leetcode"],
    6: ["ticketmaster", "online-auction", "payment-system"],
    7: ["robinhood", "uber"],
    8: ["tinder", "gopuff", "yelp"],
    9: ["google-news", "fb-post-search", "web-crawler"],
    10: ["metrics-monitoring", "ad-click-aggregator", "top-k"],
    11: ["camelcamelcamel", "strava"],
    12: ["chatgpt"],
}


class CurriculumError(ValueError):
    """A curriculum invariant failed."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CurriculumError(f"missing required file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise CurriculumError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc


def json_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_source_entries(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = manifest.get("sources") or manifest.get("entries")
    if isinstance(raw, dict):
        entries = raw
    elif isinstance(raw, list):
        entries = {str(item["id"]): item for item in raw}
    else:
        raise CurriculumError("sources/source-manifest.json must contain sources or entries")
    if len(entries) != len(set(entries)):
        raise CurriculumError("source ids must be unique")
    return entries


@dataclass(frozen=True)
class SourceHeading:
    text: str
    fragment: str
    level: int


class SourceResolver:
    """Resolve only exact, verified page titles and heading text."""

    def __init__(self, manifest: dict[str, Any]) -> None:
        self.manifest = manifest
        self.entries = normalized_source_entries(manifest)

    def entry(self, source_id: str) -> dict[str, Any]:
        try:
            return self.entries[source_id]
        except KeyError as exc:
            raise CurriculumError(f"unknown source id: {source_id}") from exc

    def page_title(self, source_id: str) -> str:
        item = self.entry(source_id)
        title = str(item.get("title") or item.get("display_title") or item.get("h1") or "").strip()
        if not title:
            raise CurriculumError(f"{source_id}: missing exact page title")
        return title

    def page_url(self, source_id: str) -> str:
        item = self.entry(source_id)
        url = str(item.get("url") or item.get("canonical_url") or "").strip()
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise CurriculumError(f"{source_id}: invalid https URL")
        return url.split("#", 1)[0]

    def headings(self, source_id: str) -> list[SourceHeading]:
        item = self.entry(source_id)
        raw = item.get("headings")
        if not isinstance(raw, list):
            raise CurriculumError(f"{source_id}: headings must be a list")
        result: list[SourceHeading] = []
        for heading in raw:
            text = str(heading.get("text") or heading.get("title") or "").strip()
            fragment = str(heading.get("id") or heading.get("fragment") or "").strip()
            level_raw = heading.get("level", 0)
            if isinstance(level_raw, str) and level_raw.lower().startswith("h"):
                level_raw = level_raw[1:]
            try:
                level = int(level_raw)
            except (TypeError, ValueError):
                level = 0
            if text and fragment:
                result.append(SourceHeading(text=text, fragment=fragment, level=level))
        return result

    def heading(self, source_id: str, exact_text: str) -> SourceHeading:
        matches = [heading for heading in self.headings(source_id) if heading.text == exact_text]
        if len(matches) != 1:
            raise CurriculumError(
                f"{source_id}: expected exactly one heading {exact_text!r}, found {len(matches)}"
            )
        heading = matches[0]
        if heading.level not in {1, 2, 3, 4, 5, 6}:
            raise CurriculumError(f"{source_id}: {exact_text!r} is not a verified heading")
        return heading

    def href(self, source_id: str, exact_heading: str) -> str:
        heading = self.heading(source_id, exact_heading)
        return f"{self.page_url(source_id)}#{heading.fragment}"


@dataclass
class CurriculumModel:
    route: dict[str, Any]
    algorithms: dict[str, Any]
    audio: dict[str, Any]
    source_manifest: dict[str, Any]
    resolver: SourceResolver
    weeks: dict[int, dict[str, Any]]
    projects: dict[str, dict[str, Any]]


def load_model(root: Path = ROOT) -> CurriculumModel:
    route = load_json(root / "curriculum" / "route.json")
    algorithms = load_json(root / "curriculum" / "algorithm-blocks.json")
    audio = load_json(root / "curriculum" / "audio-preview.json")
    source_manifest = load_json(root / "sources" / "source-manifest.json")
    resolver = SourceResolver(source_manifest)
    weeks: dict[int, dict[str, Any]] = {}
    projects: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "cases").glob("week-*.json")):
        payload = load_json(path)
        week_number = int(payload["week"])
        if week_number in weeks:
            raise CurriculumError(f"duplicate case week: {week_number}")
        weeks[week_number] = payload
        for project in payload.get("projects", []):
            slug = str(project["slug"])
            if slug in projects:
                raise CurriculumError(f"duplicate project case: {slug}")
            project["_week"] = week_number
            projects[slug] = project
    return CurriculumModel(
        route=route,
        algorithms=algorithms,
        audio=audio,
        source_manifest=source_manifest,
        resolver=resolver,
        weeks=weeks,
        projects=projects,
    )


def iter_source_refs(project: dict[str, Any]) -> Iterable[tuple[str, str]]:
    yield str(project["source"]), str(project["read"]["headings"][0])
    for heading in project["read"]["headings"]:
        yield str(project["source"]), str(heading)
    for heading in project["deep"]["headings"]:
        if (
            heading == "Senior"
            and project["deep"].get("senior_source")
            and not project["deep"].get("senior_headings")
        ):
            yield str(project["deep"]["senior_source"]), str(heading)
        else:
            yield str(project["source"]), str(heading)
    for heading in project["deep"].get("senior_headings", []):
        yield str(project["deep"]["senior_source"]), str(heading)
    for group in ("concepts", "ddia", "ai_extensions"):
        for ref in project.get(group, []):
            yield str(ref["source"]), str(ref["heading"])
    for node in project.get("staff_qa", []):
        for ref in node.get("sources", []):
            yield str(ref["source"]), str(ref["heading"])


def algorithm_blocks(model: CurriculumModel) -> dict[str, dict[str, Any]]:
    blocks = model.algorithms.get("blocks", [])
    result = {str(block["id"]): block for block in blocks}
    if len(result) != len(blocks):
        raise CurriculumError("algorithm block ids must be unique")
    return result


def route_start(model: CurriculumModel) -> date:
    return date.fromisoformat(str(model.route["start_date"]))


def day_date(model: CurriculumModel, week_number: int, day_number: int) -> date:
    return route_start(model) + timedelta(days=(week_number - 1) * 7 + day_number - 1)


def leetcode_url(model: CurriculumModel, problem: dict[str, Any]) -> str:
    template = str(model.algorithms["url_template"])
    return template.format(slug=problem["slug"])


def scheduled_algorithms(
    model: CurriculumModel, block_id: str, day_number: int
) -> tuple[str, str, list[dict[str, Any]]]:
    block = algorithm_blocks(model).get(block_id)
    if not block:
        raise CurriculumError(f"unknown algorithm block: {block_id}")
    days = block.get("days", [])
    if len(days) != 7:
        raise CurriculumError(f"{block_id}: must contain seven algorithm days")
    indexes = days[day_number - 1]
    if len(indexes) != 3:
        raise CurriculumError(f"{block_id} day {day_number}: must contain exactly three indexes")
    problems = block.get("problems", [])
    selected: list[dict[str, Any]] = []
    for index in indexes:
        try:
            problem = dict(problems[int(index)])
        except (IndexError, TypeError, ValueError) as exc:
            raise CurriculumError(f"{block_id} day {day_number}: invalid problem index {index}") from exc
        problem["url"] = leetcode_url(model, problem)
        selected.append(problem)
    modes = block.get("day_mode", [])
    mode = str(modes[day_number - 1]) if len(modes) == 7 else "new"
    return str(block["tag"]), mode, selected


def chinese_chars(text: str) -> int:
    return sum("\u4e00" <= char <= "\u9fff" for char in text)


def validate_model(model: CurriculumModel) -> list[str]:
    errors: list[str] = []

    route_weeks = model.route.get("weeks", [])
    if len(route_weeks) != 12:
        errors.append(f"route must contain 12 weeks, found {len(route_weeks)}")
    if sorted(model.weeks) != list(range(1, 13)):
        errors.append(f"case weeks must be 1..12, found {sorted(model.weeks)}")
    declared_projects: list[str] = []
    read_count: dict[str, int] = {}
    deep_count: dict[str, int] = {}
    algorithm_slots = 0
    declared_block_ids = [
        str(block.get("id")) for block in model.algorithms.get("blocks", [])
    ]
    routed_block_ids = [
        str(week.get("algorithm_block")) for week in route_weeks
    ]
    if len(declared_block_ids) != 12 or len(set(declared_block_ids)) != 12:
        errors.append("algorithm source must define 12 unique tag blocks")
    if routed_block_ids != declared_block_ids:
        errors.append(
            "route must use every algorithm tag block exactly once in declared "
            f"order; route={routed_block_ids}, blocks={declared_block_ids}"
        )

    for expected_week, route_week in enumerate(route_weeks, start=1):
        week_number = int(route_week.get("week", -1))
        if week_number != expected_week:
            errors.append(f"route week order mismatch at {expected_week}: {week_number}")
        days = route_week.get("days", [])
        if len(days) != 7:
            errors.append(f"week {week_number}: route must have seven days")
        case_week = model.weeks.get(week_number)
        if not case_week:
            continue
        route_projects = list(route_week.get("projects", []))
        case_projects = [str(project["slug"]) for project in case_week.get("projects", [])]
        if route_projects != EXPECTED_WEEK_PROJECTS.get(week_number):
            errors.append(
                f"week {week_number}: project route drifted from the "
                "reviewed 12-week plan"
            )
        if route_projects != case_projects:
            errors.append(
                f"week {week_number}: route projects {route_projects} != case projects {case_projects}"
            )
        declared_projects.extend(route_projects)
        if route_week.get("theme") != case_week.get("theme"):
            errors.append(f"week {week_number}: route/case theme drift")
        week_reads: Counter[str] = Counter()
        week_deeps: Counter[str] = Counter()
        allowed_kinds = {
            "project-read",
            "project-deep",
            "integration",
            "mock",
            "repair",
        }
        for day_number, route_day in enumerate(days, start=1):
            try:
                _, _, selected = scheduled_algorithms(
                    model, str(route_week["algorithm_block"]), day_number
                )
                algorithm_slots += len(selected)
            except CurriculumError as exc:
                errors.append(str(exc))
            kind = route_day.get("kind")
            slug = route_day.get("project")
            assignment = route_day.get("assignment")
            if kind not in allowed_kinds:
                errors.append(f"week {week_number} day {day_number}: unknown kind {kind!r}")
            if kind in {"project-read", "project-deep"}:
                if slug not in route_projects:
                    errors.append(
                        f"week {week_number} day {day_number}: project {slug!r} "
                        "is not declared in this week"
                    )
                if assignment is not None:
                    errors.append(
                        f"week {week_number} day {day_number}: project days "
                        "must use their project case assignment"
                    )
            elif slug is not None:
                errors.append(
                    f"week {week_number} day {day_number}: non-project day "
                    "must not declare a project"
                )
            elif not isinstance(assignment, dict):
                errors.append(
                    f"week {week_number} day {day_number}: non-project day "
                    "requires a specific assignment"
                )
            else:
                for field in ("focus", "artifact", "repair"):
                    value = str(assignment.get(field, "")).strip()
                    if chinese_chars(value) < (6 if field == "focus" else 18):
                        errors.append(
                            f"week {week_number} day {day_number}: assignment "
                            f"{field} is too shallow"
                        )
                acceptance = assignment.get("acceptance", [])
                if (
                    not isinstance(acceptance, list)
                    or len(acceptance) != 3
                    or any(chinese_chars(str(item)) < 12 for item in acceptance)
                ):
                    errors.append(
                        f"week {week_number} day {day_number}: assignment "
                        "needs exactly three concrete acceptance checks"
                    )
                source_refs = assignment.get("source_refs", [])
                source_pairs = [
                    (str(ref.get("source")), str(ref.get("heading")))
                    for ref in source_refs
                    if isinstance(ref, dict)
                ]
                if len(source_pairs) < 2 or len(source_pairs) != len(set(source_pairs)):
                    errors.append(
                        f"week {week_number} day {day_number}: assignment "
                        "needs at least two unique exact source refs"
                    )
                for source_id, heading in source_pairs:
                    try:
                        model.resolver.heading(source_id, heading)
                        source_kind = model.resolver.entry(source_id).get("kind")
                        if source_kind == "official_ai_extension":
                            if week_number != 12 or source_id not in {
                                "openai.building-agents",
                                "anthropic.building-effective-agents",
                            }:
                                errors.append(
                                    f"week {week_number} day {day_number}: "
                                    f"AI source {source_id} is out of scope"
                                )
                    except CurriculumError as exc:
                        errors.append(
                            f"week {week_number} day {day_number}: {exc}"
                        )
                expected_times = {
                    "integration": [
                        "19:30–20:10",
                        "20:10–20:50",
                        "20:50–21:30",
                        "21:30–22:10",
                    ],
                    "mock": [
                        "19:30–20:15",
                        "20:15–20:45",
                        "20:45–21:25",
                        "21:25–22:10",
                    ],
                    "repair": [
                        "19:30–20:00",
                        "20:00–20:50",
                        "20:50–21:30",
                        "21:30–22:10",
                    ],
                }.get(str(kind), [])
                design_blocks = assignment.get("design_blocks", [])
                actual_times = [
                    str(block.get("time"))
                    for block in design_blocks
                    if isinstance(block, dict)
                ]
                if len(design_blocks) != 4 or actual_times != expected_times:
                    errors.append(
                        f"week {week_number} day {day_number}: assignment "
                        f"design blocks must use exact {kind} time windows"
                    )
                for block in design_blocks:
                    if not isinstance(block, dict) or any(
                        chinese_chars(str(block.get(field, ""))) < minimum
                        for field, minimum in (("title", 2), ("instruction", 10))
                    ):
                        errors.append(
                            f"week {week_number} day {day_number}: assignment "
                            "design block is too shallow"
                        )
                        break
                for resource in assignment.get("internal_resources", []):
                    if not isinstance(resource, dict):
                        errors.append(
                            f"week {week_number} day {day_number}: invalid internal resource"
                        )
                        continue
                    href = str(resource.get("href", ""))
                    label = str(resource.get("label", "")).strip()
                    if not re.fullmatch(
                        r"\.\./(?:index|coverage-matrix|system-design-project-route|"
                        r"week(?:[1-9]|1[0-2])-action-guide)\.html(?:#[a-z0-9-]+)?",
                        href,
                    ) or not label:
                        errors.append(
                            f"week {week_number} day {day_number}: unsafe or "
                            f"empty internal resource {href!r}"
                        )
            if kind == "project-read" and slug:
                read_count[str(slug)] = read_count.get(str(slug), 0) + 1
                week_reads[str(slug)] += 1
            if kind == "project-deep" and slug:
                deep_count[str(slug)] = deep_count.get(str(slug), 0) + 1
                week_deeps[str(slug)] += 1
        if set(week_reads) != set(route_projects) or any(
            week_reads[slug] != 1 for slug in route_projects
        ):
            errors.append(f"week {week_number}: every declared project needs one local read day")
        if set(week_deeps) != set(route_projects) or any(
            week_deeps[slug] != 1 for slug in route_projects
        ):
            errors.append(f"week {week_number}: every declared project needs one local deep day")
        for slug in route_projects:
            read_positions = [
                index
                for index, day in enumerate(days)
                if day.get("kind") == "project-read" and day.get("project") == slug
            ]
            deep_positions = [
                index
                for index, day in enumerate(days)
                if day.get("kind") == "project-deep" and day.get("project") == slug
            ]
            if (
                len(read_positions) == 1
                and len(deep_positions) == 1
                and deep_positions[0] != read_positions[0] + 1
            ):
                errors.append(
                    f"week {week_number} {slug}: deep day must immediately follow read day"
                )
        kind_counts = Counter(str(day.get("kind")) for day in days)
        project_count = len(route_projects)
        expected_non_project = (
            {"mock": 1}
            if project_count == 3
            else {"integration": 1, "mock": 1, "repair": 1}
            if project_count == 2
            else {"integration": 3, "mock": 1, "repair": 1}
            if project_count == 1
            else {}
        )
        for kind in ("integration", "mock", "repair"):
            if kind_counts[kind] != expected_non_project.get(kind, 0):
                errors.append(
                    f"week {week_number}: expected {expected_non_project.get(kind, 0)} "
                    f"{kind} day(s), found {kind_counts[kind]}"
                )
        if not days or days[-1].get("kind") not in {"mock", "repair"}:
            errors.append(f"week {week_number}: week must end in mock or repair")

    if len(declared_projects) != 30 or len(set(declared_projects)) != 30:
        errors.append(
            f"route must declare 30 unique projects, found {len(declared_projects)} / "
            f"{len(set(declared_projects))} unique"
        )
    if set(declared_projects) != set(model.projects):
        missing = sorted(set(declared_projects) - set(model.projects))
        extra = sorted(set(model.projects) - set(declared_projects))
        errors.append(f"case coverage mismatch; missing={missing}, extra={extra}")
    roster_entries = model.source_manifest.get("roster", {}).get("entries", [])
    roster_source_ids = {
        str(item.get("source_id"))
        for item in roster_entries
        if item.get("source_id")
    }
    project_source_ids = {
        str(project.get("source")) for project in model.projects.values()
    }
    if len(roster_source_ids) != 30 or project_source_ids != roster_source_ids:
        errors.append(
            "project sources must exactly match the verified 30-item Hello "
            f"Interview roster; missing={sorted(roster_source_ids - project_source_ids)}, "
            f"extra={sorted(project_source_ids - roster_source_ids)}"
        )
    for slug in declared_projects:
        if read_count.get(slug) != 1:
            errors.append(f"{slug}: expected one complete read day, found {read_count.get(slug, 0)}")
        if deep_count.get(slug) != 1:
            errors.append(f"{slug}: expected one deep-dive day, found {deep_count.get(slug, 0)}")
    if algorithm_slots != 252:
        errors.append(f"expected 252 algorithm slots, found {algorithm_slots}")

    for slug, project in model.projects.items():
        try:
            exact_title = model.resolver.page_title(str(project["source"]))
            if str(project["title"]) != exact_title:
                errors.append(
                    f"{slug}: project title {project['title']!r} != exact source "
                    f"title {exact_title!r}"
                )
        except CurriculumError as exc:
            errors.append(f"{slug}: {exc}")
        try:
            project_kind = model.resolver.entry(str(project["source"])).get("kind")
            if project_kind != "hello_interview_breakdown":
                errors.append(f"{slug}: project source must be a breakdown")
            senior_source = str(
                project.get("deep", {}).get("senior_source")
                or project["source"]
            )
            senior_kind = model.resolver.entry(senior_source).get("kind")
            if senior_kind not in {
                "hello_interview_breakdown",
                "hello_interview_senior_expectations",
            }:
                errors.append(
                    f"{slug}: Senior expectations source has wrong kind {senior_kind!r}"
                )
            expected_group_kinds = {
                "concepts": {
                    "hello_interview_core_concept",
                    "hello_interview_key_technology",
                    "hello_interview_pattern",
                },
                "ddia": {"ddia_chinese_chapter"},
                "ai_extensions": {"official_ai_extension"},
            }
            for group, allowed_kinds in expected_group_kinds.items():
                for ref in project.get(group, []):
                    source_id = str(ref.get("source"))
                    actual_kind = model.resolver.entry(source_id).get("kind")
                    if actual_kind not in allowed_kinds:
                        errors.append(
                            f"{slug}: {group} ref {source_id} has wrong "
                            f"source kind {actual_kind!r}"
                        )
        except CurriculumError as exc:
            errors.append(f"{slug}: {exc}")
        read_headings = project.get("read", {}).get("headings", [])
        deep_headings = project.get("deep", {}).get("headings", [])
        if (
            not read_headings
            or read_headings[0]
            not in {"Understanding the Problem", "Understand the Problem"}
            or read_headings[-1] != "High-Level Design"
        ):
            errors.append(
                f"{slug}: complete read range must start at Understanding/Understand "
                "the Problem and end at High-Level Design"
            )
        else:
            try:
                source_headings = model.resolver.headings(str(project["source"]))
                positions: list[int] = []
                for exact_text in read_headings:
                    matches = [
                        index
                        for index, heading in enumerate(source_headings)
                        if heading.text == exact_text
                    ]
                    if len(matches) != 1:
                        raise CurriculumError(
                            f"complete-read heading {exact_text!r} resolves "
                            f"{len(matches)} times"
                        )
                    positions.append(matches[0])
                if positions != sorted(positions) or len(set(positions)) != len(positions):
                    errors.append(f"{slug}: complete-read headings are not in live source order")
                elif [
                    heading.text
                    for heading in source_headings[
                        positions[0] : positions[-1] + 1
                    ]
                ] != [str(heading) for heading in read_headings]:
                    errors.append(
                        f"{slug}: complete-read headings must include every "
                        "linkable source heading through High-Level Design"
                    )
            except CurriculumError as exc:
                errors.append(f"{slug}: {exc}")
        if not deep_headings or deep_headings[0] not in {"Potential Deep Dives", "Deep Dives"}:
            errors.append(f"{slug}: deep day must begin with the exact deep-dive heading")
        if "Senior" not in deep_headings and not project.get("deep", {}).get(
            "senior_headings"
        ):
            errors.append(f"{slug}: deep day must include exact Senior expectations")
        if len(project.get("lecture", [])) < 6:
            errors.append(f"{slug}: lecture needs at least six teaching sections")
        for index, item in enumerate(project.get("lecture", []), start=1):
            if chinese_chars(str(item.get("body", ""))) < 140:
                errors.append(f"{slug}: lecture section {index} is too shallow")
        if len(project.get("staff_qa", [])) < 5:
            errors.append(f"{slug}: Staff Q&A needs at least five questions")
        for index, item in enumerate(project.get("staff_qa", []), start=1):
            if chinese_chars(str(item.get("answer", ""))) < 105:
                errors.append(f"{slug}: Staff Q&A answer {index} is too shallow")
            if not item.get("sources"):
                errors.append(f"{slug}: Staff Q&A answer {index} has no sources")
        try:
            for source_id, heading in iter_source_refs(project):
                model.resolver.heading(source_id, heading)
        except CurriculumError as exc:
            errors.append(f"{slug}: {exc}")

    for week_number, case_week in model.weeks.items():
        preview = case_week.get("audio_preview", {})
        script = str(preview.get("script", ""))
        script_length = chinese_chars(script)
        if script_length < 300:
            errors.append(f"week {week_number}: two-minute audio preview script is too short")
        if script_length > 520:
            errors.append(f"week {week_number}: two-minute audio preview script is too long")

    week_one_refs = {
        (str(ref.get("source")), str(ref.get("heading")))
        for project in model.weeks.get(1, {}).get("projects", [])
        for group in ("concepts", "ddia")
        for ref in project.get(group, [])
    }
    week_one_source_ids = {source_id for source_id, _ in week_one_refs}
    required_week_one_sources = {
        "hi.core.api-design",
        "hi.core.data-modeling",
        "hi.core.caching",
        "hi.core.db-indexing",
        "hi.core.networking-essentials",
        "hi.pattern.large-blobs",
        "hi.deep.dynamodb",
        "hi.deep.postgres",
        "hi.pattern.realtime-updates",
        "hi.core.cap-theorem",
        "ddia.ch2",
        "ddia.ch4",
        "ddia.ch6",
        "ddia.ch9",
    }
    missing_week_one = sorted(required_week_one_sources - week_one_source_ids)
    if missing_week_one:
        errors.append(
            f"week 1: required Bitly/Dropbox source coverage is missing "
            f"{missing_week_one}"
        )
    cdn_refs = {
        (
            "hi.core.networking-essentials",
            "Content Delivery Networks (CDNs)",
        ),
        ("hi.core.caching", "CDN (Content Delivery Network)"),
    }
    if not week_one_refs.intersection(cdn_refs):
        errors.append("week 1: exact CDN source coverage is missing")

    expected_audio = {
        "provider": "ElevenLabs",
        "voice": "Siqi Liu - Calm, Warm and Gentle",
        "model": "Eleven v3",
        "source": "elevenlabs.tts.optional",
        "heading": "Text input",
    }
    for key, expected in expected_audio.items():
        if model.audio.get(key) != expected:
            errors.append(
                f"audio preview {key} must remain {expected!r}, "
                f"found {model.audio.get(key)!r}"
            )
    audio_policy = model.audio.get("policy", {})
    if audio_policy.get("auto_generate") is not False:
        errors.append("audio previews must never auto-generate or consume credits")
    if audio_policy.get("target_duration_minutes") != 2:
        errors.append("audio preview target duration must remain two minutes")

    allowed_ai_week = 12
    for week_number, case_week in model.weeks.items():
        serialized = json.dumps(case_week, ensure_ascii=False).lower()
        if week_number != allowed_ai_week and any(
            token in serialized for token in ("openai.", "anthropic.", "agent loop", "applied ai")
        ):
            errors.append(f"week {week_number}: AI extension leaked outside ChatGPT week")
        for project in case_week.get("projects", []):
            extensions = project.get("ai_extensions", [])
            is_chatgpt = (
                week_number == allowed_ai_week
                and project.get("slug") == "chatgpt"
            )
            if not is_chatgpt and extensions:
                errors.append(
                    f"week {week_number} {project.get('slug')}: AI extensions are "
                    "allowed only for ChatGPT"
                )
            if is_chatgpt:
                extension_sources = {
                    str(ref.get("source")) for ref in extensions
                }
                expected_sources = {
                    "openai.building-agents",
                    "anthropic.building-effective-agents",
                }
                if (
                    extension_sources != expected_sources
                    or len(extensions) != len(expected_sources)
                ):
                    errors.append(
                        "chatgpt: AI extensions must use exactly the official "
                        f"OpenAI and Anthropic sources; found {sorted(extension_sources)}"
                    )
                for source_id in extension_sources:
                    try:
                        source_kind = model.resolver.entry(source_id).get("kind")
                    except CurriculumError as exc:
                        errors.append(f"chatgpt: {exc}")
                        continue
                    if source_kind != "official_ai_extension":
                        errors.append(
                            f"chatgpt: {source_id} must be typed as "
                            "official_ai_extension"
                        )

    return errors
