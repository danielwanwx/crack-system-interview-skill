#!/usr/bin/env python3
"""Synchronize canonical skills and curriculum into the installable plugin."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "crack-system-interview-skill"

SKILLS = ("card", "senior-sde-interview-script", "system-design-study-coach")


def sync_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def main() -> None:
    for name in SKILLS:
        sync_tree(ROOT / name, PLUGIN / "skills" / name)
    sync_tree(ROOT / "curriculum", PLUGIN / "curriculum")
    print("Synced canonical skills and curriculum into plugin package.")


if __name__ == "__main__":
    main()
