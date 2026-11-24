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
FONT_SHORTHAND = re.compile(r"(?<![-\w])font\s*:\s*([^;}]+)", re.I)
# In the `font` shorthand the family list follows the size, optionally with /line-height.
SIZE_THEN_FAMILY = re.compile(r"(?:^|\s)[0-9.]+[a-z%]*(?:/\S+)?\s+(.+)$", re.I)
KEYWORDS = {"inherit", "initial", "unset", "revert", "caption", "icon", "menu", "message-box", "small-caption", "status-bar"}


def unapproved(css: str, approved: set[str]) -> list[str]:
    lists = FONT_FAMILY.findall(css)
    for value in FONT_SHORTHAND.findall(css):
        found = SIZE_THEN_FAMILY.search(value.strip())
        if found:
            lists.append(found.group(1))
        elif value.strip().lower() not in KEYWORDS:
            lists.append(value)  # unparseable shorthand is reported, not trusted
    fonts = (f.strip().strip("'\"") for decl in lists for f in decl.split(","))
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
