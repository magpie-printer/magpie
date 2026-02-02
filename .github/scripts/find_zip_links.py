#!/usr/bin/env python3
import os
import re
import sys

ZIP_RE = re.compile(r"https://github\.com/user-attachments/files/[^\s\)\"\]]+\.zip(?:\?[^\s\)\"\]]+)?", re.IGNORECASE)

def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    if not body.strip():
        print("ERROR: ISSUE_BODY env var is empty. Provide the issue body text.", file=sys.stderr)
        return 2

    matches = ZIP_RE.findall(body)

    print(f"Found {len(matches)} zip link(s).")
    for i, url in enumerate(matches, start=1):
        print(f"{i}. {url}")

    if len(matches) == 0:
        print("\nERROR: No .zip links found. Attach one .zip to the issue body.", file=sys.stderr)
        return 3

    if len(matches) > 1:
        print("\nERROR: More than one .zip link found. Please attach only one.", file=sys.stderr)
        return 4

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
