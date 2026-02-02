#!/usr/bin/env python3
import os
import re
import sys
import io
import stat
import zipfile
from urllib.request import Request, urlopen, build_opener, HTTPHandler

ZIP_RE = re.compile(
    r"https://github\.com/user-attachments/files/[^\s\)\"\]]+\.zip(?:\?[^\s\)\"\]]+)?",
    re.IGNORECASE,
)

MAX_ZIP_BYTES = 50 * 1024 * 1024          # 50MB downloaded zip
MAX_FILES = 200                           # cap file count
MAX_SINGLE_FILE_BYTES = 25 * 1024 * 1024  # 25MB per file uncompressed
MAX_TOTAL_UNCOMPRESSED = 200 * 1024 * 1024  # 200MB total uncompressed

ALLOWED_EXTENSIONS = {
    ".stl", ".3mf", ".obj",
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
    if len(matches) == 0:
        raise RuntimeError("No .zip link found in issue body.")
    if len(matches) > 1:
        raise RuntimeError(f"More than one .zip link found ({len(matches)}). Please attach only one.")
    return matches[0]

def resolve_redirect(url: str, token: str) -> str:
    opener = build_opener(NoRedirect)
    req = Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("User-Agent", "magpie-mod-validator")
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
    req.add_header("User-Agent", "magpie-mod-validator")
    with urlopen(req) as resp:
        data = resp.read()
    if len(data) > MAX_ZIP_BYTES:
        raise RuntimeError(f"Zip too large: {len(data)} bytes > {MAX_ZIP_BYTES}")
    return data

def is_symlink(zipinfo: zipfile.ZipInfo) -> bool:
    # Unix symlink bit check if present
    mode = (zipinfo.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)

def validate_zip(zf: zipfile.ZipFile) -> None:
    infos = zf.infolist()

    # Count only actual files (not dirs)
    file_infos = [i for i in infos if not i.is_dir()]
    if len(file_infos) == 0:
        raise RuntimeError("Zip contains no files.")
    if len(file_infos) > MAX_FILES:
        raise RuntimeError(f"Too many files in zip: {len(file_infos)} > {MAX_FILES}")

    total_uncompressed = 0
    top_levels = set()

    for info in infos:
        name = info.filename

        # Basic path safety
        if name.startswith("/") or name.startswith("\\"):
            raise RuntimeError(f"Unsafe absolute path: {name}")
        if ".." in name.split("/"):
            raise RuntimeError(f"Unsafe parent path traversal: {name}")
        if "\\" in name:
            # force unix-style paths; blocks odd windows separators
            raise RuntimeError(f"Backslash path separator not allowed: {name}")

        # Track top-level folder(s)
        parts = [p for p in name.split("/") if p]
        if parts:
            top_levels.add(parts[0])

        if info.is_dir():
            continue

        if is_symlink(info):
            raise RuntimeError(f"Symlinks are not allowed: {name}")

        # Extension allowlist
        ext = ""
        if "." in parts[-1]:
            ext = "." + parts[-1].split(".")[-1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise RuntimeError(f"Disallowed file type: {name} (ext={ext or 'none'})")

        # Size checks (uncompressed)
        if info.file_size > MAX_SINGLE_FILE_BYTES:
            raise RuntimeError(f"File too large: {name} ({info.file_size} bytes)")
        total_uncompressed += info.file_size
        if total_uncompressed > MAX_TOTAL_UNCOMPRESSED:
            raise RuntimeError(f"Total uncompressed size too large: {total_uncompressed} bytes")

    # Nice-to-have structural rule: one top-level folder
    if len(top_levels) != 1:
        raise RuntimeError(f"Zip must contain exactly one top-level folder, found: {sorted(top_levels)}")

def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not body.strip():
        print("ERROR: ISSUE_BODY is empty", file=sys.stderr)
        return 2
    if not token.strip():
        print("ERROR: GITHUB_TOKEN is empty", file=sys.stderr)
        return 2

    print("Step3: validating zip (no extraction)...")
    url = find_zip_url(body)
    print("ZIP URL:", url)

    final_url = resolve_redirect(url, token)
    data = download(final_url)
    print(f"Downloaded zip bytes: {len(data)}")

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        validate_zip(zf)
        print("✅ Validation passed.")
        print("ZIP entries:")
        for n in zf.namelist():
            print(" -", n)

    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"❌ Validation failed: {e}", file=sys.stderr)
        raise SystemExit(1)
