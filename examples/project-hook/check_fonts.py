#!/usr/bin/env python3
"""Example project hook: fail when a stylesheet uses a font that isn't in the project's tokens.

    check_fonts.py fonts.json styles.css [more.css ...]

A product repository runs a check like this in its own CI (docs/proposals/pr-enforcement.md,
"Project hooks"). KAREN OS ships it only as an example and a test fixture.
"""
import json
import re
import sys

FONT_FAMILY = re.compile(r"font-family\s*:\s*([^;}]+)", re.I)


def unapproved(css: str, approved: set[str]) -> list[str]:
    fonts = (f.strip().strip("'\"") for decl in FONT_FAMILY.findall(css) for f in decl.split(","))
    return sorted({f for f in fonts if f and f.lower() not in approved})


def main(argv):
    approved = {f.lower() for f in json.load(open(argv[0], encoding="utf-8"))["approved_fonts"]}
    bad = {path: unapproved(open(path, encoding="utf-8").read(), approved) for path in argv[1:]}
    for path, fonts in bad.items():
        for font in fonts:
            print("%s: font %r is not in the approved tokens" % (path, font))
    return 1 if any(bad.values()) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
