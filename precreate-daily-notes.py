#!/usr/bin/env python3
"""Pre-create Obsidian daily notes on one machine so synced devices never race to create them.

Renders the vault's Templater daily-note template (only the tags it actually uses), and
creates today's note plus the next N days. Existing notes are never touched.
Aborts without writing if the template contains a Templater tag this script doesn't know,
so a template change can't silently produce broken notes.
"""
import argparse
import datetime as dt
import os
import random
import re
import sys
from pathlib import Path

DAILY_FOLDER = "Daily Notes"
TEMPLATE = "Templates/Daily note.md"
QUOTES = "Templates/Quotes.md"

TAG_RE = re.compile(r"<%([*_-]?)(.*?)([_-]?)%>", re.S)


def quote_callout(vault: Path) -> str:
    # Mirrors the JS in the template: lines starting with "- ", split on " — ".
    path = vault / QUOTES
    if not path.is_file():
        return ""
    quotes = [l[2:] for l in path.read_text(encoding="utf-8").split("\n") if l.startswith("- ")]
    if not quotes:
        return ""
    parts = random.choice(quotes).split(" — ")
    text = parts[0]
    author = parts[1] if len(parts) > 1 else "Unknown"
    return f"> [!quote] Quote of the day\n> {text}\n>\n> — {author}\n"


def render_tag(kind: str, body: str, title: str, vault: Path) -> str:
    b = body.strip()
    if kind == "*":
        if "Quotes" in b and "tR" in b:
            return quote_callout(vault)
        raise ValueError(f"unsupported Templater exec block: <%*{body[:60]}...")
    if b == "tp.file.title":
        return title
    if re.fullmatch(r"tp\.file\.cursor\(\d*\)", b):
        return ""
    raise ValueError(f"unsupported Templater tag: <%{body}%>")


def render(template: str, title: str, vault: Path) -> str:
    out = []
    pos = 0
    for m in TAG_RE.finditer(template):
        left, body, right = m.group(1), m.group(2), m.group(3)
        before = template[pos:m.start()]
        # Left whitespace control: "-" trims one newline, "_" trims all whitespace.
        if left == "-" and before.endswith("\n"):
            before = before[:-1]
        elif left == "_":
            before = before.rstrip()
        out.append(before)
        out.append(render_tag("*" if left == "*" else "", body, title, vault))
        pos = m.end()
        # Right whitespace control, applied to the text after the tag.
        if right == "-" and template.startswith("\n", pos):
            pos += 1
        elif right == "_":
            while pos < len(template) and template[pos].isspace():
                pos += 1
    out.append(template[pos:])
    result = "".join(out)
    if "<%" in result:
        raise ValueError("unrendered Templater syntax left in output")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("vault", type=Path, help="path to the vault root on this machine")
    ap.add_argument("--days", type=int, default=7, help="days ahead to create, besides today (default 7)")
    ap.add_argument("--dry-run", action="store_true", help="print what would be created, write nothing")
    args = ap.parse_args()

    vault = args.vault.resolve()
    # Refuse to run against an unmounted or wrong path (Syncthing marks folder roots with .stfolder).
    if not (vault / ".stfolder").exists() or not (vault / DAILY_FOLDER).is_dir():
        print(f"error: {vault} doesn't look like the synced vault (.stfolder or '{DAILY_FOLDER}' missing)",
              file=sys.stderr)
        return 2

    template = (vault / TEMPLATE).read_text(encoding="utf-8")
    today = dt.date.today()
    created = 0
    for i in range(args.days + 1):
        title = (today + dt.timedelta(days=i)).isoformat()  # Daily Notes default format YYYY-MM-DD
        path = vault / DAILY_FOLDER / f"{title}.md"
        if path.exists():
            continue
        try:
            content = render(template, title, vault)
        except ValueError as e:
            print(f"error: {e}; template needs updating in this script. Nothing written.", file=sys.stderr)
            return 3
        if args.dry_run:
            print(f"would create {path}")
            continue
        try:
            # O_EXCL: create only if absent, so an existing note can never be overwritten.
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            continue
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        print(f"created {path}")
        created += 1
    if not args.dry_run:
        print(f"{created} note(s) created")
    return 0


if __name__ == "__main__":
    sys.exit(main())
