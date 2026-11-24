#!/usr/bin/env python3
"""Resolve a task's workflow profile (docs/proposals/workflow-profiles.md, revision 1).

    profiles.py resolve --type ui --risk medium --flag substantial_ui \
        [--project FILE] [--exceptions FILE] [--registry FILE]

Prints the profiles applied, the final risk, and per stage the gates, skills,
holds and fallbacks, as JSON. Holds are reported, not failures: exit 0. A project
rule that loosens company policy, or unknown input, exits 1.

A required skill is available only when the registry (docs/organisation/skills.json)
lists it as approved. Checking that a runtime resolves it to the approved hash is #46.
Standard library only; reads files and runs nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "docs/organisation/workflow-profiles.json"
REGISTRY = ROOT / "docs/organisation/skills.json"


class InvalidInput(ValueError):
    """An unknown type, risk, flag, stage or level."""


def _merge(stage, add, levels, conflicts=None, where=""):
    """Add gates and skills to a stage, strictest level winning. With `conflicts`, a lower level is recorded, not ignored."""
    for gate in add.get("gates", []):
        if gate not in stage["gates"]:
            stage["gates"].append(gate)
    for skill, level in add.get("skills", {}).items():
        if level not in levels:
            raise InvalidInput("unknown level %r for %s" % (level, skill))
        have = stage["skills"].get(skill)
        if have is None or levels.index(level) > levels.index(have):
            stage["skills"][skill] = level
        elif conflicts is not None and levels.index(level) < levels.index(have):
            conflicts.append("%s: %s lowered from %s to %s" % (where, skill, have, level))


def _apply_project(project, applied, stages, data, floor, conflicts):
    """Projects can add gates and skills and raise floors. Anything that would loosen company policy is a conflict."""
    risks, levels = data["risks"], data["levels"]
    for name, rules in project.get("profiles", {}).items():
        if name not in applied:
            continue
        where = "project %s" % name
        for key in sorted(rules.keys() - {"risk_floor", "stages"}):
            conflicts.append("%s: unsupported key %r; projects can only add or raise" % (where, key))
        if "risk_floor" in rules:
            raised = rules["risk_floor"]
            if raised not in risks:
                raise InvalidInput("unknown risk %r in %s" % (raised, where))
            if risks.index(raised) < risks.index(data["profiles"][name]["risk_floor"]):
                conflicts.append("%s: risk floor lowered to %s" % (where, raised))
            floor = max(floor, risks.index(raised))
        for stage, add in rules.get("stages", {}).items():
            if stage not in stages:
                raise InvalidInput("unknown stage %r in %s" % (stage, where))
            for key in sorted(add.keys() - {"gates", "skills"}):
                conflicts.append("%s/%s: unsupported key %r; projects can only add or raise" % (where, stage, key))
            _merge(stages[stage], add, levels, conflicts, "%s/%s" % (where, stage))
    return floor


def resolve(data, type_, risk, flags=(), project=None, exceptions=(), registry=()):
    """Return the resolved profile. `registry` is the set of approved, registered skill ids."""
    risks, levels = data["risks"], data["levels"]
    type_ = data["type_aliases"].get(type_, type_)
    if type_ not in data["profiles"]:
        raise InvalidInput("unknown type %r" % type_)
    if risk not in risks:
        raise InvalidInput("unknown risk %r" % risk)
    unknown = [f for f in flags if f not in data["flags"]]
    if unknown:
        raise InvalidInput("unknown flags %s" % unknown)
    flags = list(dict.fromkeys(flags))

    applied = [type_]
    for flag in flags:
        applied += [p for p in data["flags"][flag].get("profiles", []) if p not in applied]

    # Risk is only ever raised: the declared level, then every triggered floor.
    floor = max([risks.index(risk)]
                + [risks.index(data["profiles"][p]["risk_floor"]) for p in applied]
                + [risks.index(data["flags"][f]["risk_floor"]) for f in flags if "risk_floor" in data["flags"][f]])
    stages = {s: {"gates": [], "skills": {}} for s in data["stages"]}
    for rules in [data["profiles"][p] for p in applied] + [data["flags"][f] for f in flags]:
        for stage, add in rules.get("stages", {}).items():
            _merge(stages[stage], add, levels)

    conflicts = []
    if project:
        floor = _apply_project(project, applied, stages, data, floor, conflicts)
    final = risks[floor]
    _merge(stages["review"], data["review_by_risk"][final], levels)

    waived, ignored = {}, []
    for item in exceptions:
        stage, skill = item.get("stage"), item.get("skill")
        if not all(item.get(k) for k in ("skill", "stage", "scope", "reference")):
            ignored.append(dict(item, why="an exception needs skill, stage, scope and an owner reference"))
        elif stages.get(stage, {}).get("skills", {}).get(skill) != "required":
            ignored.append(dict(item, why="no such required skill at that stage"))
        else:
            waived[(stage, skill)] = item["reference"]

    for name, stage in stages.items():
        stage["waived"] = {s: ref for (st, s), ref in waived.items() if st == name}
        stage["holds"] = [s for s, lvl in stage["skills"].items()
                          if lvl == "required" and s not in registry and s not in stage["waived"]]
        stage["fallbacks"] = [s for s, lvl in stage["skills"].items() if lvl == "recommended" and s not in registry]
        stage["status"] = "hold" if stage["holds"] else "ready"

    return {"profiles": applied, "declared_risk": risk, "risk": final, "flags": flags,
            "always": data["always"], "stages": stages,
            "conflicts": conflicts, "ignored_exceptions": ignored}


def registered(registry):
    """Skill ids the hash-pinned registry lists as approved."""
    return {e["id"] for e in registry.get("entries", []) if e.get("approval_status") == "approved"}


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Resolve a task's workflow profile.")
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("resolve", help="resolve a task's profile")
    r.add_argument("--type", required=True, help="profile or issue type, e.g. ui or feat")
    r.add_argument("--risk", required=True, help="the risk the agent declares: low, medium or high")
    r.add_argument("--flag", action="append", default=[], help="repeat for each flag")
    r.add_argument("--project", help="the project's profile file, if any")
    r.add_argument("--exceptions", help="JSON list of owner exceptions")
    r.add_argument("--registry", default=str(REGISTRY))
    a = parser.parse_args(argv)
    try:
        result = resolve(_load(PROFILES), a.type, a.risk, a.flag,
                         project=_load(a.project) if a.project else None,
                         exceptions=_load(a.exceptions) if a.exceptions else (),
                         registry=registered(_load(a.registry)))
    except InvalidInput as exc:
        print("profiles: %s" % exc, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 1 if result["conflicts"] else 0


if __name__ == "__main__":
    sys.exit(main())
