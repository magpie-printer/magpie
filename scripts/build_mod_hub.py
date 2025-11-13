#!/usr/bin/env python3
"""
Generate the Magpie Mod Hub data file.

The script inspects every immediate subdirectory under Mods/ and extracts a
small set of metadata such as title, summary, author, readme path, and images.
It produces a JSON payload consumed by the static Mod Hub front-end.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional


DEFAULT_OUTPUT = Path("mod-hub/mods.json")
VALID_README_NAMES = ("README.md", "Readme.md", "Readme.MD", "readme.md", "Readme.txt", "README.txt", "readme.txt")
IMG_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp")


def find_readme(mod_dir: Path) -> Optional[Path]:
    for name in VALID_README_NAMES:
        candidate = mod_dir / name
        if candidate.exists():
            return candidate
    return None


def extract_title(lines: Iterable[str]) -> Optional[str]:
    heading_pattern = re.compile(r"^#\s+(.*)")
    for raw in lines:
        match = heading_pattern.match(raw.strip())
        if match:
            return match.group(1).strip()
    return None


def _clean_line(line: str) -> str:
    return line.strip().strip("*_`> ")


def extract_summary(lines: List[str]) -> Optional[str]:
    summary_lines: List[str] = []
    after_title = False
    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            if summary_lines:
                break
            # reset until actual content
            continue
        if stripped.startswith("#"):
            after_title = True
            continue
        if not after_title:
            continue
        if stripped.startswith("!") or stripped.startswith("|"):
            # Skip image markdown and tables
            if summary_lines:
                break
            continue
        if stripped.lower().startswith(("made by", "bom", "**bom")):
            break
        summary_lines.append(_clean_line(stripped))
        if len(" ".join(summary_lines)) >= 240:
            break
    summary = " ".join(summary_lines).strip()
    return summary or None


def extract_author(lines: Iterable[str]) -> Optional[str]:
    author_pattern = re.compile(r"made by[:\-]?\s*(.*)", re.IGNORECASE)
    for raw in lines:
        match = author_pattern.search(raw)
        if match:
            return match.group(1).strip()
    return None


def extract_images(readme_text: str, mod_dir: Path, repo_root: Path) -> List[str]:
    rel_paths: List[str] = []
    image_pattern = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    for match in image_pattern.finditer(readme_text):
        candidate = match.group(1).strip()
        if candidate.startswith("http"):
            rel_paths.append(candidate)
            continue
        image_path = (mod_dir / candidate).resolve()
        if image_path.exists():
            rel_paths.append(image_path)
    if not rel_paths:
        # Fallback to first image file in the directory
        for path in sorted(mod_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in IMG_EXTENSIONS:
                rel_paths.append(path)
                break
    return rel_paths_to_strings(rel_paths, repo_root)


def rel_paths_to_strings(paths: List[Path | str], repo_root: Path) -> List[str]:
    result: List[str] = []
    for path in paths:
        if isinstance(path, str):
            result.append(path)
        else:
            try:
                rel = path.relative_to(repo_root)
            except ValueError:
                rel = path
            result.append(rel.as_posix())
    return result


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
    return slug.strip("-")


def collect_mods(repo_root: Path) -> List[dict]:
    mods_dir = repo_root / "Mods"
    if not mods_dir.exists():
        raise SystemExit(f"Mods directory not found at {mods_dir}")
    mods: List[dict] = []
    for entry in sorted(mods_dir.iterdir()):
        if not entry.is_dir():
            continue
        readme_path = find_readme(entry)
        if not readme_path:
            continue
        text = readme_path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        title = extract_title(lines) or entry.name
        summary = extract_summary(lines)
        author = extract_author(lines)
        images = extract_images(text, entry, repo_root)
        mods.append(
            {
                "id": slugify(entry.name),
                "name": title,
                "author": author,
                "summary": summary,
                "path": entry.relative_to(repo_root).as_posix(),
                "readme": readme_path.relative_to(repo_root).as_posix(),
                "images": images,
                "last_modified": datetime.utcfromtimestamp(readme_path.stat().st_mtime).strftime("%Y-%m-%d"),
            }
        )
    return mods


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Magpie Mod Hub data file.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Path to the repository root (default: current working directory).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Location for the generated JSON file (default: {DEFAULT_OUTPUT}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    mods = collect_mods(root)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mods": mods,
    }
    output_path = (args.output if args.output.is_absolute() else root / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    rel_output = output_path.relative_to(root)
    print(f"Wrote {len(mods)} mods to {rel_output}")


if __name__ == "__main__":
    main()
