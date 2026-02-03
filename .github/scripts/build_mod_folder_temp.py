#!/usr/bin/env python3
import os
import re
import sys
import shutil
from pathlib import Path

def sanitize_folder_name(name: str) -> str:
    # Keep spaces + case, just remove illegal filesystem chars and normalize whitespace
    s = re.sub(r"\s+", " ", name.strip())
    # Windows-illegal chars + path separators; safe for cross-platform
    s = re.sub(r'[\/\\:\*\?"<>\|]', "-", s)
    s = s.strip(" .")
    return s[:80] if s else "Untitled Mod"

def parse_issue_body(body: str) -> dict:
    def grab(field: str) -> str:
        pattern = rf"### {re.escape(field)}\s*(.+?)(?=\n### |\Z)"
        m = re.search(pattern, body, flags=re.S)
        return (m.group(1).strip() if m else "")

    return {
        "mod_name": grab("Mod name"),
        "author_name": grab("Author name (displayed)"),
        "author_links": grab("Author links (optional)"),
        "short_description": grab("Short description"),
        "long_description": grab("Full description (becomes README)"),
        "mod_version": grab("Mod version (optional)"),
    }

def write_readme(dest: Path, meta: dict):
    lines = []
    lines.append(f"# {meta['mod_name']}")
    lines.append("")
    lines.append(f"**Author:** {meta['author_name']}")
    if meta.get("author_links"):
        lines.append(f"**Links:** {meta['author_links']}")
    if meta.get("mod_version"):
        lines.append(f"**Version:** {meta['mod_version']}")
    lines.append("")
    lines.append("## Summary")
    lines.append(meta["short_description"])
    lines.append("")
    lines.append("## Details")
    lines.append(meta["long_description"])
    lines.append("")
    (dest / "README.md").write_text("\n".join(lines), encoding="utf-8")

def print_tree(root: Path) -> None:
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_dir():
            print(f"[dir ] {rel}/")
        else:
            print(f"[file] {rel} ({p.stat().st_size} bytes)")

def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    if not body.strip():
        print("ERROR: ISSUE_BODY is empty", file=sys.stderr)
        return 2

    meta = parse_issue_body(body)
    for k in ["mod_name", "author_name", "short_description", "long_description"]:
        if not meta.get(k):
            print(f"ERROR: missing required field in issue body: {k}", file=sys.stderr)
            return 3

    extracted_root = Path(".tmp/mod_import")
    if not extracted_root.exists():
        print("ERROR: .tmp/mod_import not found. Run extract_zip_temp.py first.", file=sys.stderr)
        return 4

    top_levels = [p for p in extracted_root.iterdir() if p.is_dir()]
    if len(top_levels) != 1:
        print(f"ERROR: expected 1 top-level folder under .tmp/mod_import, found {len(top_levels)}", file=sys.stderr)
        return 5
    extracted_mod_folder = top_levels[0]

    out_root = Path(".tmp/mod_ready")
    out_mod_name = sanitize_folder_name(meta["mod_name"])
    out_mod = out_root / out_mod_name

    if out_mod.exists():
        shutil.rmtree(out_mod)
    out_mod.mkdir(parents=True, exist_ok=True)

    # Copy extracted files directly into the mod folder (flatten one top-level folder)
    for item in extracted_mod_folder.iterdir():
        # Optional: drop test-only helper file if present
        if item.is_file() and item.name.lower() == "readme_test.txt":
            continue

        dest = out_mod / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    # Always generate README.md (required by hub)
    write_readme(out_mod, meta)

    print("Step5: built mod folder (temp only, drop-in Mods-compatible).")
    print(f"Output: {out_mod.resolve()}\n")
    print_tree(out_mod)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
