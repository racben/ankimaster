#!/usr/bin/env python3

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()

NORMAL_PATHS = [
    HOME / "Chinese Text Analysis",
]

DEEP_PATHS = [
    HOME / "Chinese Text Analysis",
    HOME / "src" / "TurnBasedGameData",
    HOME / "src" / "AnimeGameData",
]


def run_opencc(text: str, config: str) -> str:
    result = subprocess.run(
        ["opencc", "-c", config],
        input=text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.strip()


def variants(text: str) -> list[str]:
    simp = run_opencc(text, "t2s.json")
    trad = run_opencc(text, "s2t.json")

    seen = []
    for item in [text, simp, trad]:
        if item and item not in seen:
            seen.append(item)

    return seen


def clean_line(line: str) -> str:
    line = line.rstrip("\r\n")

    # Strip leading bracketed IDs, e.g. [146782006]
    line = re.sub(r"^\[.*?\]\s*", "", line)

    # Strip Unity/HTML-ish tags, e.g. <color=#dbc291ff>, </color>
    line = re.sub(r"<[^>]+>", "", line)

    # Decode entities if any show up
    line = html.unescape(line)

    return line.strip()


def rg_search(targets: list[str], paths: list[Path], deep: bool) -> list[str]:
    cmd = [
        "rg",
        "--fixed-strings",
        "--no-filename",
        "-N",
    ]

    for target in targets:
        cmd.extend(["-e", target])

    if deep:
        cmd.extend(["--max-filesize", "100M"])
    else:
        cmd.extend(["-ttxt", "-tmd", "--max-filesize", "5M"])

    cmd.extend([
        "-g", "!old/",
        "-g", "!Anki_dump/",
    ])

    cmd.extend(str(path) for path in paths)

    result = subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode not in (0, 1):
        print(result.stderr, file=sys.stderr, end="")
        sys.exit(result.returncode)

    return result.stdout.splitlines()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mine Chinese sentence examples by target + anchor text."
    )
    parser.add_argument(
        "-d", "--deep",
        action="store_true",
        help="Search HSR/Genshin dump folders too.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Print all matching lines instead of the first match.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not strip IDs or tags from output.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional corpus paths. Overrides default/deep paths.",
    )

    args = parser.parse_args()

    if args.paths:
        paths = [Path(p).expanduser() for p in args.paths]
    else:
        paths = DEEP_PATHS if args.deep else NORMAL_PATHS

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        if len(parts) < 2:
            print(f"Skipping line without target + anchor: {raw}", file=sys.stderr)
            continue

        target, anchor = parts
        target_variants = variants(target)
        anchor_variants = variants(anchor)

        hits = rg_search(target_variants, paths, args.deep)

        for hit in hits:
            if not any(anchor_variant in hit for anchor_variant in anchor_variants):
                continue

            output = hit if args.no_clean else clean_line(hit)
            print(f"{target}\t{output}")

            if not args.all:
                break


if __name__ == "__main__":
    main()
