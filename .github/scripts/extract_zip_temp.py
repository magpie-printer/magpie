#!/usr/bin/env python3
import os
import re
import sys
import io
import stat
import shutil
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen, build_opener, HTTPHandler

ZIP_RE = re.compile(
    r"https://github\.com/user-attachments/files/[^\s\)\"\]]+\.zip(?:\?[^\s\)\"\]]+)?",
    re.IGNORECASE,
)

MAX_ZIP_BYTES = 50 * 1024 * 1024
MAX_FILES = 200
MAX_SINGLE_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 200 * 1024 * 1024

ALLOWED_EXTENSIONS = {
   ".FCstd, ".step", ".stl", ".3mf", ".obj",
    ".png", ".jpg", ".jpeg", ".webp",
    ".txt", ".md",
    ".json", ".yaml", ".yml",
    ".gcode", ".cfg", ".ini",
    ".pdf",
}

class NoRedirect(HTTPHandler):
    def http_response(self, request, response):
        return response
    https_response = http_response

def find_zip_url(body: str) -> str:
    matches = ZIP_RE.findall(body)
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly 1 zip link, found {len(matches)}")
    return matches[0]

def resolve_redirect(url: str, token: str) -> str:
    opener = build_opener(NoRedirect)
    req = Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("User-Agent", "magpie-mod-extractor")
    resp = opener.open(req)
    status = getattr(resp, "status", None) or resp.getcode()
    if status not in (301, 302, 303, 307, 308):
        return url
    location = resp.headers.get("Location")
    if not location:
        raise RuntimeError("Redirect missing Location header.")
    return location

def download(url: str) -> bytes:
    req = Request(url)
    req.add_header("User-Agent", "magpie-mod-extractor")
    with urlopen(req) as resp:
        data = resp.read()
    if len(data) > MAX_ZIP_BYTES:
        raise RuntimeError(f"Zip too large: {len(data)} bytes > {MAX_ZIP_BYTES}")
    return data

def is_symlink(zipinfo: zipfile.ZipInfo) -> bool:
    mode = (zipinfo.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)

def validate_zip(zf: zipfile.ZipFile) -> str:
    infos = zf.infolist()
    file_infos = [i for i in infos if not i.is_dir()]
    if not file_infos:
        raise RuntimeError("Zip contains no files.")
    if len(file_infos) > MAX_FILES:
        raise RuntimeError(f"Too many files: {len(file_infos)} > {MAX_FILES}")

    total_uncompressed = 0
    top_levels = set()

    for info in infos:
        name = info.filename

        if name.startswith("/") or name.startswith("\\"):
            raise RuntimeError(f"Unsafe absolute path: {name}")
        if "\\" in name:
            raise RuntimeError(f"Backslash path separator not allowed: {name}")
        if ".." in name.split("/"):
            raise RuntimeError(f"Unsafe parent traversal: {name}")

        parts = [p for p in name.split("/") if p]
        if parts:
            top_levels.add(parts[0])

        if info.is_dir():
            continue

        if is_symlink(info):
            raise RuntimeError(f"Symlinks not allowed: {name}")

        ext = ""
        if "." in parts[-1]:
            ext = "." + parts[-1].split(".")[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise RuntimeError(f"Disallowed file type: {name} (ext={ext or 'none'})")

        if info.file_size > MAX_SINGLE_FILE_BYTES:
            raise RuntimeError(f"File too large: {name} ({info.file_size} bytes)")
        total_uncompressed += info.file_size
        if total_uncompressed > MAX_TOTAL_UNCOMPRESSED:
            raise RuntimeError(f"Total uncompressed too large: {total_uncompressed} bytes")

    if len(top_levels) != 1:
        raise RuntimeError(f"Zip must have exactly one top-level folder, found: {sorted(top_levels)}")

    return next(iter(top_levels))

def safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = info.filename
        # Paths already validated; still resolve and guard
        out_path = (dest / name).resolve()
        if not str(out_path).startswith(str(dest.resolve())):
            raise RuntimeError(f"Unsafe resolved path: {name}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, open(out_path, "wb") as out:
            shutil.copyfileobj(src, out)

def print_tree(root: Path) -> None:
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_dir():
            print(f"[dir ] {rel}/")
        else:
            print(f"[file] {rel} ({p.stat().st_size} bytes)")

def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not body.strip():
        print("ERROR: ISSUE_BODY is empty", file=sys.stderr)
        return 2
    if not token.strip():
        print("ERROR: GITHUB_TOKEN is empty", file=sys.stderr)
        return 2

    print("Step4: extract to temp (no Mods/, no git)...")
    url = find_zip_url(body)
    print("ZIP URL:", url)

    final_url = resolve_redirect(url, token)
    data = download(final_url)

    tmp_root = Path(".tmp/mod_import")
    tmp_root.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        top = validate_zip(zf)
        # Extract exactly as-is to temp
        dest = tmp_root / top
        if dest.exists():
            shutil.rmtree(dest)
        safe_extract(zf, tmp_root)

    print(f"\nExtracted to: {tmp_root.resolve()}")
    print_tree(tmp_root)
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(1)
