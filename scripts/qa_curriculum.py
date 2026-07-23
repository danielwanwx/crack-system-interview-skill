#!/usr/bin/env python3
"""Release QA for the verified 12-week curriculum and generated Pages site."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlsplit

from curriculum_model import (
    ROOT,
    CurriculumError,
    chinese_chars,
    load_model,
    scheduled_algorithms,
    validate_model,
)
from build_curriculum import manifest_day_payload


DOCS = ROOT / "docs"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.assets: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []
        self.has_viewport = False
        self.h1_count = 0
        self.ids: set[str] = set()

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(str(attributes["id"]))
        if tag == "a":
            self._href = attributes.get("href")
            self._text = []
        if (
            tag == "link"
            and "stylesheet"
            in str(attributes.get("rel") or "").lower().split()
            and attributes.get("href")
        ):
            self.assets.append(("stylesheet", str(attributes["href"])))
        if tag == "script" and attributes.get("src"):
            self.assets.append(("script", str(attributes["src"])))
        if tag == "meta" and attributes.get("name") == "viewport":
            self.has_viewport = True
        if tag == "h1":
            self.h1_count += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            text = re.sub(r"\s+", " ", " ".join(self._text)).strip()
            self.links.append((self._href, text))
            self._href = None
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)


def generated_html_paths() -> list[Path]:
    paths = [
        DOCS / "index.html",
        DOCS / "system-design-project-route.html",
        DOCS / "coverage-matrix.html",
    ]
    for week in range(1, 13):
        paths.append(DOCS / f"week{week}-action-guide.html")
        paths.extend((DOCS / f"week{week}").glob("*.html"))
    return sorted(paths)


def parse_page(path: Path) -> LinkParser:
    parser = LinkParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def source_link_map(model: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    for source_id, entry in model.resolver.entries.items():
        title = model.resolver.page_title(source_id)
        for heading in model.resolver.headings(source_id):
            url = f"{model.resolver.page_url(source_id)}#{heading.fragment}"
            label = f"{title} · {heading.text}"
            if url in result and result[url] != label:
                raise CurriculumError(
                    f"two exact labels claimed for {url}: {result[url]!r}, {label!r}"
                )
            result[url] = label
    return result


def algorithm_link_map(model: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    for block in model.algorithms["blocks"]:
        for problem in block["problems"]:
            url = model.algorithms["url_template"].format(slug=problem["slug"])
            result[url] = str(problem["title"])
    return result


def resolve_internal(source: Path, href: str) -> Path:
    target = href.split("#", 1)[0].split("?", 1)[0]
    return (source.parent / target).resolve()


def validate_pages(model: Any) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    pages = generated_html_paths()
    expected_count = 3 + 12 + 12 * 11
    if len(pages) != expected_count:
        errors.append(f"expected {expected_count} generated HTML pages, found {len(pages)}")
    missing = [path for path in pages if not path.exists()]
    if missing:
        errors.extend(f"missing page: {path.relative_to(ROOT)}" for path in missing)
        return errors, {}
    approved_sources = source_link_map(model)
    approved_algorithms = algorithm_link_map(model)
    parsed_pages = {path.resolve(): parse_page(path) for path in pages}
    external_count = 0
    internal_count = 0
    source_count = 0
    algorithm_count = 0
    local_asset_count = 0
    for path in pages:
        parser = parsed_pages[path.resolve()]
        relative = path.relative_to(ROOT)
        if not parser.has_viewport:
            errors.append(f"{relative}: missing viewport metadata")
        if parser.h1_count != 1:
            errors.append(f"{relative}: expected one H1, found {parser.h1_count}")
        for asset_kind, reference in parser.assets:
            parsed_asset = urlsplit(reference)
            if parsed_asset.scheme or parsed_asset.netloc:
                continue
            local_asset_count += 1
            if not parsed_asset.path:
                errors.append(
                    f"{relative}: empty local {asset_kind} reference {reference!r}"
                )
                continue
            asset_target = resolve_internal(path, reference)
            if not asset_target.is_file():
                errors.append(
                    f"{relative}: missing local {asset_kind} asset {reference}"
                )
        for href, label in parser.links:
            parsed = urlsplit(href)
            if parsed.scheme in {"http", "https"}:
                external_count += 1
                if href in approved_sources:
                    source_count += 1
                    if label != approved_sources[href]:
                        errors.append(
                            f"{relative}: source label {label!r} != exact "
                            f"{approved_sources[href]!r} for {href}"
                        )
                    if not parsed.fragment:
                        errors.append(f"{relative}: source URL lacks verified fragment: {href}")
                elif href in approved_algorithms:
                    algorithm_count += 1
                    if label != approved_algorithms[href]:
                        errors.append(
                            f"{relative}: algorithm label {label!r} != official "
                            f"{approved_algorithms[href]!r}"
                        )
                else:
                    errors.append(f"{relative}: unapproved external link: {label!r} -> {href}")
            elif parsed.scheme:
                errors.append(f"{relative}: unsupported link scheme: {href}")
            elif href.startswith("#"):
                fragment = unquote(parsed.fragment)
                if not fragment or fragment not in parser.ids:
                    errors.append(
                        f"{relative}: missing same-page fragment "
                        f"{fragment!r} for {href}"
                    )
            else:
                internal_count += 1
                target = resolve_internal(path, href)
                if not target.exists():
                    errors.append(f"{relative}: broken internal link {href}")
                elif parsed.fragment:
                    target_parser = parsed_pages.get(target)
                    if target_parser is None and target.suffix == ".html":
                        target_parser = parse_page(target)
                    fragment = unquote(parsed.fragment)
                    if target_parser is not None and fragment not in target_parser.ids:
                        errors.append(
                            f"{relative}: missing internal fragment "
                            f"{fragment!r} in {target.relative_to(ROOT)}"
                        )
    return errors, {
        "pages": len(pages),
        "external_links": external_count,
        "source_links": source_count,
        "algorithm_links": algorithm_count,
        "internal_links": internal_count,
        "local_assets": local_asset_count,
    }


def validate_schedule(model: Any) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    read_days: Counter[str] = Counter()
    deep_days: Counter[str] = Counter()
    scheduled: list[tuple[int, int, str, str]] = []
    for route_week in model.route["weeks"]:
        week = int(route_week["week"])
        block_id = str(route_week["algorithm_block"])
        for day, route_day in enumerate(route_week["days"], start=1):
            if route_day["kind"] == "project-read":
                read_days[str(route_day["project"])] += 1
            if route_day["kind"] == "project-deep":
                deep_days[str(route_day["project"])] += 1
            tag, _, problems = scheduled_algorithms(model, block_id, day)
            if len(problems) != 3:
                errors.append(f"week {week} day {day}: expected 3 algorithms")
            scheduled.extend((week, day, tag, str(problem["slug"])) for problem in problems)
    for slug in model.projects:
        if read_days[slug] != 1 or deep_days[slug] != 1:
            errors.append(
                f"{slug}: read/deep day counts are {read_days[slug]}/{deep_days[slug]}"
            )
    if len(scheduled) != 252:
        errors.append(f"expected 252 scheduled algorithm slots, found {len(scheduled)}")
    for route_week in model.route["weeks"]:
        week = int(route_week["week"])
        tags = {
            tag for item_week, _, tag, _ in scheduled if item_week == week
        }
        if len(tags) != 1:
            errors.append(f"week {week}: algorithms break tag-block continuity: {tags}")
    return errors, {
        "weeks": len(model.route["weeks"]),
        "projects": len(model.projects),
        "read_days": sum(read_days.values()),
        "deep_days": sum(deep_days.values()),
        "algorithm_slots": len(scheduled),
    }


def validate_depth(model: Any) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    lecture_lengths: list[int] = []
    answer_lengths: list[int] = []
    normalized_titles = sorted(
        {str(project["title"]) for project in model.projects.values()},
        key=len,
        reverse=True,
    )
    sentence_uses: dict[str, set[str]] = {}
    sentence_examples: dict[str, str] = {}

    def record_sentences(slug: str, value: str) -> None:
        normalized = value
        for title in normalized_titles:
            normalized = normalized.replace(title, "<PROJECT>")
        for sentence in re.split(r"[。！？!?]+", normalized):
            sentence = re.sub(r"\s+", " ", sentence).strip(" ，,；;：:")
            if chinese_chars(sentence) < 24:
                continue
            sentence_uses.setdefault(sentence, set()).add(slug)
            sentence_examples.setdefault(sentence, sentence)

    for slug, project in model.projects.items():
        if len(project.get("lecture", [])) < 6:
            errors.append(f"{slug}: fewer than 6 lecture sections")
        for index, section in enumerate(project.get("lecture", []), start=1):
            length = chinese_chars(str(section.get("body", "")))
            lecture_lengths.append(length)
            record_sentences(slug, str(section.get("body", "")))
            if length < 140:
                errors.append(f"{slug}: lecture {index} has only {length} Chinese chars")
        if len(project.get("staff_qa", [])) < 5:
            errors.append(f"{slug}: fewer than 5 Staff Q&A items")
        qa_with_project_source = 0
        qa_with_specific_deep_source = 0
        for index, qa in enumerate(project.get("staff_qa", []), start=1):
            length = chinese_chars(str(qa.get("answer", "")))
            answer_lengths.append(length)
            for field in (
                "question",
                "trigger",
                "answer",
                "follow_up",
                "common_miss",
                "repair",
            ):
                record_sentences(slug, str(qa.get(field, "")))
            if length < 105:
                errors.append(f"{slug}: Q&A {index} has only {length} Chinese chars")
            required = ("trigger", "follow_up", "common_miss", "repair", "sources")
            missing = [key for key in required if not qa.get(key)]
            if missing:
                errors.append(f"{slug}: Q&A {index} missing {missing}")
            project_sources = [
                ref
                for ref in qa.get("sources", [])
                if ref.get("source") == project.get("source")
            ]
            if project_sources:
                qa_with_project_source += 1
            umbrella = {
                "Potential Deep Dives",
                "Deep Dives",
                "What is Expected at Each Level?",
                "Senior",
                "Final Design",
                "Tying it all together",
                "Putting it all Together",
            }
            specific_deep_headings = {
                str(heading)
                for heading in project.get("deep", {}).get("headings", [])
                if str(heading) not in umbrella
                and not str(heading).lower().startswith("some additional")
                and not str(heading).lower().startswith("bonus")
            }
            if any(
                str(ref.get("heading")) in specific_deep_headings
                for ref in project_sources
            ):
                qa_with_specific_deep_source += 1
        if qa_with_project_source < 3:
            errors.append(
                f"{slug}: fewer than three Q&A items cite the project breakdown"
            )
        if qa_with_specific_deep_source < 2:
            errors.append(
                f"{slug}: fewer than two Q&A items cite a specific project deep dive"
            )
    for route_week in model.route["weeks"]:
        week_number = int(route_week["week"])
        for day_number, route_day in enumerate(route_week["days"], start=1):
            assignment = route_day.get("assignment")
            if not assignment:
                continue
            unit = f"route-w{week_number:02d}-d{day_number}"
            for field in ("focus", "artifact", "repair"):
                record_sentences(unit, str(assignment.get(field, "")))
            for criterion in assignment.get("acceptance", []):
                record_sentences(unit, str(criterion))
            for block in assignment.get("design_blocks", []):
                record_sentences(unit, str(block.get("instruction", "")))
    template_duplicates = [
        {
            "projects": sorted(projects),
            "sentence": sentence_examples[sentence],
        }
        for sentence, projects in sentence_uses.items()
        if len(projects) >= 3
    ]
    for duplicate in template_duplicates:
        errors.append(
            "mechanical sentence reused across curriculum units "
            f"{duplicate['projects']}: {duplicate['sentence'][:120]}"
        )
    sample_slugs = ["bitly", "dropbox", "online-chess", "payment-system", "chatgpt"]
    samples = {
        slug: {
            "lecture_sections": len(model.projects[slug]["lecture"]),
            "staff_questions": len(model.projects[slug]["staff_qa"]),
            "min_lecture_chinese_chars": min(
                chinese_chars(str(item["body"]))
                for item in model.projects[slug]["lecture"]
            ),
            "min_answer_chinese_chars": min(
                chinese_chars(str(item["answer"]))
                for item in model.projects[slug]["staff_qa"]
            ),
        }
        for slug in sample_slugs
        if slug in model.projects
    }
    return errors, {
        "lecture_sections": len(lecture_lengths),
        "staff_questions": len(answer_lengths),
        "minimum_lecture_chinese_chars": min(lecture_lengths, default=0),
        "minimum_answer_chinese_chars": min(answer_lengths, default=0),
        "cross_project_template_sentences": template_duplicates,
        "samples": samples,
    }


def validate_audio(model: Any) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    expected = {
        "provider": "ElevenLabs",
        "voice": "Siqi Liu - Calm, Warm and Gentle",
        "model": "Eleven v3",
    }
    for key, value in expected.items():
        if model.audio.get(key) != value:
            errors.append(f"audio {key}: expected {value!r}, found {model.audio.get(key)!r}")
    if model.audio.get("policy", {}).get("auto_generate") is not False:
        errors.append("audio auto_generate must be false")
    script_lengths: dict[str, int] = {}
    for week, case_week in model.weeks.items():
        length = chinese_chars(str(case_week.get("audio_preview", {}).get("script", "")))
        script_lengths[str(week)] = length
        if length < 300:
            errors.append(f"week {week}: audio preview has only {length} Chinese chars")
    return errors, {
        **expected,
        "auto_generate": False,
        "script_chinese_chars": script_lengths,
    }


def expected_generated_files() -> set[str]:
    return {
        "docs/.curriculum-generated-files.json",
        "docs/.nojekyll",
        "docs/assets/curriculum.css",
        "docs/assets/curriculum.js",
        "docs/index.html",
        "docs/system-design-project-route.html",
        "docs/coverage-matrix.html",
        "docs/source-verification.json",
        *{
            f"curriculum/week-{week:02d}.json"
            for week in range(1, 13)
        },
        *{
            f"docs/week{week}-action-guide.html"
            for week in range(1, 13)
        },
        *{
            f"docs/week{week}/{filename}"
            for week in range(1, 13)
            for filename in (
                *(f"day-{day}.html" for day in range(1, 8)),
                "lecture.html",
                "staff-qa.html",
                "live-mock.html",
                "scorecard.html",
            )
        },
    }


def validate_generated_file_index(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["generated-file index root must be an object"]
    if payload.get("schema_version") != 1:
        errors.append("generated-file index schema_version must be 1")
    files = payload.get("files")
    if not isinstance(files, list):
        errors.append("generated-file index files must be a list")
        return errors
    invalid_entries = [
        index for index, value in enumerate(files) if not isinstance(value, str)
    ]
    if invalid_entries:
        errors.append(
            "generated-file index contains non-string entries at "
            f"indices {invalid_entries}"
        )
        return errors
    duplicate_entries = sorted(
        value for value, count in Counter(files).items() if count > 1
    )
    if duplicate_entries:
        errors.append(
            "generated-file index contains duplicate entries: "
            f"{duplicate_entries}"
        )
        return errors
    if set(files) != expected_generated_files():
        errors.append(
            "generated-file index drifted from the exact 12-week output set"
        )
    return errors


def validate_pruning() -> list[str]:
    errors: list[str] = []
    for week in range(13, 19):
        for path in (
            DOCS / f"week{week}",
            DOCS / f"week{week}-action-guide.html",
            ROOT / "curriculum" / f"week-{week:02d}.json",
            ROOT
            / "plugins"
            / "crack-system-interview-skill"
            / "curriculum"
            / f"week-{week:02d}.json",
        ):
            if path.exists():
                errors.append(f"stale 18-week artifact remains: {path.relative_to(ROOT)}")
    index_path = DOCS / ".curriculum-generated-files.json"
    if not index_path.is_file():
        errors.append("missing docs/.curriculum-generated-files.json")
    else:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        errors.extend(validate_generated_file_index(payload))
    return errors


def validate_plugin_sync() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    plugin = ROOT / "plugins" / "crack-system-interview-skill"
    file_count = 0
    for name in ("curriculum", "cases", "sources"):
        canonical = ROOT / name
        packaged = plugin / name
        canonical_files = sorted(
            path.relative_to(canonical)
            for path in canonical.rglob("*")
            if path.is_file()
        )
        packaged_files = (
            sorted(
                path.relative_to(packaged)
                for path in packaged.rglob("*")
                if path.is_file()
            )
            if packaged.exists()
            else []
        )
        if canonical_files != packaged_files:
            errors.append(f"plugin {name} file set is out of sync")
            continue
        for relative in canonical_files:
            file_count += 1
            if (canonical / relative).read_bytes() != (
                packaged / relative
            ).read_bytes():
                errors.append(f"plugin {name} differs: {relative}")
    canonical_skill = ROOT / "system-design-study-coach"
    packaged_skill = plugin / "skills" / "system-design-study-coach"
    canonical_skill_files = sorted(
        path.relative_to(canonical_skill)
        for path in canonical_skill.rglob("*")
        if path.is_file()
    )
    packaged_skill_files = (
        sorted(
            path.relative_to(packaged_skill)
            for path in packaged_skill.rglob("*")
            if path.is_file()
        )
        if packaged_skill.exists()
        else []
    )
    if canonical_skill_files != packaged_skill_files:
        errors.append("plugin system-design-study-coach file set is out of sync")
    else:
        for relative in canonical_skill_files:
            file_count += 1
            if (canonical_skill / relative).read_bytes() != (
                packaged_skill / relative
            ).read_bytes():
                errors.append(
                    f"plugin system-design-study-coach differs: {relative}"
                )
    return errors, {"compared_files": file_count}


def validate_generated_manifests(model: Any) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    paths = sorted((ROOT / "curriculum").glob("week-*.json"))
    if len(paths) != 12:
        errors.append(f"expected 12 generated week manifests, found {len(paths)}")
    day_count = 0
    algorithm_count = 0
    source_count = 0
    for expected_week, path in enumerate(paths, start=1):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            errors.append(f"{path.name}: manifest root must be an object")
            continue
        week = int(payload.get("week", -1))
        if week != expected_week:
            errors.append(f"{path.name}: expected week {expected_week}, found {week}")
            continue
        route_week = model.route["weeks"][week - 1]
        case_week = model.weeks[week]
        expected_days = [
            manifest_day_payload(
                model, route_week, case_week, day_number
            )
            for day_number in range(1, 8)
        ]
        expected_projects = [
            {
                "slug": project["slug"],
                "title": project["title"],
                "complete_read_day": next(
                    day_number
                    for day_number, route_day in enumerate(
                        route_week["days"], start=1
                    )
                    if route_day.get("kind") == "project-read"
                    and route_day.get("project") == project["slug"]
                ),
                "deep_dive_day": next(
                    day_number
                    for day_number, route_day in enumerate(
                        route_week["days"], start=1
                    )
                    if route_day.get("kind") == "project-deep"
                    and route_day.get("project") == project["slug"]
                ),
            }
            for project in case_week["projects"]
        ]
        expected_audio = {
            "title": case_week["audio_preview"]["title"],
            "script": case_week["audio_preview"]["script"],
            "provider": model.audio["provider"],
            "voice": model.audio["voice"],
            "model": model.audio["model"],
            "auto_generate": False,
        }
        expected_top_level = {
            "schema_version": "2.0",
            "week": week,
            "theme": route_week["theme"],
            "start_date": expected_days[0]["date"],
            "end_date": expected_days[-1]["date"],
            "algorithm_block": route_week["algorithm_block"],
            "projects": expected_projects,
            "audio_preview": expected_audio,
        }
        if set(payload) != {*expected_top_level, "days"}:
            errors.append(
                f"{path.name}: top-level manifest fields drifted; "
                f"found {sorted(payload)}"
            )
        for field, expected_value in expected_top_level.items():
            if payload.get(field) != expected_value:
                errors.append(f"{path.name}: {field} drifted from canonical model")
        days = payload.get("days", [])
        if not isinstance(days, list):
            errors.append(f"{path.name}: days must be a list")
            continue
        if len(days) != 7:
            errors.append(f"{path.name}: expected seven days, found {len(days)}")
        for expected_day, (item, expected_item) in enumerate(
            zip(days, expected_days), start=1
        ):
            day_count += 1
            if not isinstance(item, dict):
                errors.append(
                    f"{path.name}: Day {expected_day} must be an object"
                )
                continue
            if item != expected_item:
                differing = sorted(
                    key
                    for key in set(item) | set(expected_item)
                    if item.get(key) != expected_item.get(key)
                )
                errors.append(
                    f"{path.name}: Day {expected_day} canonical payload "
                    f"drifted in {differing}"
                )
            problems = item.get("algorithms", {}).get("problems", [])
            algorithm_count += len(problems)
            sources = item.get("sources", [])
            source_count += len(sources)
            page_path = DOCS / expected_item["page"]
            if not page_path.exists():
                errors.append(
                    f"{path.name}: Day {expected_day} page is missing: "
                    f"{expected_item['page']}"
                )
    return errors, {
        "manifests": len(paths),
        "days": day_count,
        "algorithm_slots": algorithm_count,
        "source_records": source_count,
    }


def validate_verification_record() -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    path = DOCS / "source-verification.json"
    if not path.exists():
        return ["missing docs/source-verification.json"], {}
    record = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "source_manifest_sha256": hashlib.sha256(
            (ROOT / "sources" / "source-manifest.json").read_bytes()
        ).hexdigest(),
        "algorithm_blocks_sha256": hashlib.sha256(
            (ROOT / "curriculum" / "algorithm-blocks.json").read_bytes()
        ).hexdigest(),
    }
    if record.get("status") != "passed" or record.get("mode") != "live":
        errors.append("source verification record is not a passed live verification")
    for key, digest in expected.items():
        if record.get(key) != digest:
            errors.append(f"source verification record digest mismatch: {key}")
    if record.get("breakdown_count") != 30:
        errors.append("source verification record does not prove a 30-item roster")
    return errors, record


def run_live_verification(workers: int) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "verify_sources.py"),
                "--workers",
                str(workers),
            ],
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
    return json.loads(result.stdout.strip().splitlines()[-1])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QA the complete 12-week curriculum.")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument(
        "--no-live",
        action="store_true",
        help="Skip duplicate live GETs only when build_curriculum just verified them in the same release command.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report: dict[str, Any] = {"status": "failed", "checks": {}}
    errors: list[str] = []
    try:
        if not args.no_live:
            report["checks"]["live_sources"] = run_live_verification(args.workers)
        model = load_model(ROOT)
        errors.extend(validate_model(model))
        schedule_errors, schedule = validate_schedule(model)
        errors.extend(schedule_errors)
        report["checks"]["schedule"] = schedule
        depth_errors, depth = validate_depth(model)
        errors.extend(depth_errors)
        report["checks"]["depth"] = depth
        audio_errors, audio = validate_audio(model)
        errors.extend(audio_errors)
        report["checks"]["audio"] = audio
        page_errors, pages = validate_pages(model)
        errors.extend(page_errors)
        report["checks"]["pages"] = pages
        manifest_errors, manifests = validate_generated_manifests(model)
        errors.extend(manifest_errors)
        report["checks"]["generated_manifests"] = manifests
        verification_errors, verification = validate_verification_record()
        errors.extend(verification_errors)
        report["checks"]["verification_record"] = verification
        plugin_errors, plugin_sync = validate_plugin_sync()
        errors.extend(plugin_errors)
        report["checks"]["plugin_sync"] = plugin_sync
        errors.extend(validate_pruning())
    except (CurriculumError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    report["errors"] = errors
    report["status"] = "passed" if not errors else "failed"
    report_path = DOCS / "qa-report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
