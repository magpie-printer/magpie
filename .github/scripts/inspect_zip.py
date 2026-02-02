#!/usr/bin/env python3
import os
import re
import sys
import io
import zipfile
from urllib.request import Request, urlopen, build_opener, HTTPHandler

ZIP_RE = re.compile(
    r"https://github\.com/user-attachments/files/[^\s\)\"\]]+\.zip(?:\?[^\s\)\"\]]+)?",
    re.IGNORECASE,
)

MAX_ZIP_BYTES = 50 * 1024 * 1024  # 50MB safety cap


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
    req.add_header("User-Agent", "magpie-mod-inspector")

    resp = opener.open(req)
    status = getattr(resp, "status", None) or resp.getcode()

    # If it doesn't redirect, it might already be the file
    if status not in (301, 302, 303, 307, 308):
        return url

    location = resp.headers.get("Location")
    if not location:
        raise RuntimeError("Redirect missing Location header.")
    return location


def download(url: str) -> bytes:
    req = Request(url)
    req.add_header("User-Agent", "magpie-mod-inspector")
    with urlopen(req) as resp:
        data = resp.read()

    if len(data) > MAX_ZIP_BYTES:
        raise RuntimeError(f"Zip too large: {len(data)} bytes > {MAX_ZIP_BYTES}")
    return data


def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    token = os.environ.get("GITHUB_TOKEN", "")

    if not body.strip():
        print("ERROR: ISSUE_BODY is empty", file=sys.stderr)
        return 2
    if not token.strip():
        print("ERROR: GITHUB_TOKEN is empty", file=sys.stderr)
        return 2

    print("Step2: inspecting zip from issue body...")  # cannot be silent
    url = find_zip_url(body)
    print("ZIP URL (user-attachments):", url)

    final_url = resolve_redirect(url, token)
    print("Resolved download URL:", final_url)

    data = download(final_url)
    print(f"Downloaded zip bytes: {len(data)}")

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        print(f"\nZIP entries ({len(names)}):")
        for n in names:
            print(" -", n)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(1)
