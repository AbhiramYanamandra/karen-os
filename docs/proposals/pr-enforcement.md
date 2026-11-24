# Proposal: enforce workflow profiles in PR checks

Revision 1, 24 November 2026. Issue [#46](https://github.com/AbhiramYanamandra/karen-os/issues/46), epic [#43](https://github.com/AbhiramYanamandra/karen-os/issues/43), charter slice **PR C**. Status: **awaiting owner approval** (merging this PR approves this revision). Resolved profile for this work: **feature, medium risk**, design gate, second review.

## Summary

The workflow profiles (#45) say what each task needs. Today nothing checks that a PR did it. This proposal makes every PR carry a small **profile block** in its description, and extends the existing `scripts/check_pr.py` so CI fails when the block is missing, contradicts the diff, names the wrong skill versions, lacks a required design approval, or claims medium or high risk with only a self-review.

It's honest about the limit. CI can check that **evidence exists and is consistent**. It can't check that a model followed a skill's prose, or that a reviewer was truly independent. Each check below is labelled **verified**, **attested** or **judgement**.

## The profile block

`pipeline.py pr` pre-fills it from the resolver: the type comes from the branch, and the required skills and registry hashes are filled in. The agent completes the rest.

````markdown
## Profile

```karen-profile
{
  "type": "feat",
  "risk": "medium",
  "flags": ["design_required"],
  "design_approval": "https://github.com/AbhiramYanamandra/karen-os/pull/58",
  "skills": [
    {"id": "ponytail-plugin", "stage": "implement", "sha256": "5d64c155…", "runtime": "claude-code",
     "evidence": "transcript: Base directory for this skill: …/ponytail/5.3.3/skills/ponytail"}
  ],
  "review": {"by": "Codex gpt-6.1-sol", "session": "01a20c0a-…", "findings": "1 minor, fixed in af254dd"},
  "tests": ["python3 -B -m unittest discover -s tests: 168 OK"],
  "owner_interventions": 0,
  "exceptions": []
}
```
````

## What CI checks

| # | Check | Fails when | Kind |
|---|---|---|---|
| 1 | Block present and valid | Missing, invalid JSON, or unknown fields | verified |
| 2 | Type matches branch | `feat/…` branch but `"type": "docs"` | verified |
| 3 | Resolves cleanly | The resolver reports a conflict or unknown input | verified |
| 4 | Flags cover the diff | The diff touches `.github/workflows/` without `ci_change`, a manifest-pinned file without `pinned_policy`, or adds a dependency without `new_dependency` | verified |
| 5 | Required skills listed at the registry version | A required skill for any stage is missing, or its `sha256` differs from the registry entry, unless an exception has an owner reference | verified (consistency) |
| 6 | Load evidence present | A listed skill has empty `evidence` | attested: CI can't open a local transcript |
| 7 | Design approval | The profile has a design gate but `design_approval` is empty, or isn't a **merged** PR in the same repository (checked through the GitHub API) | verified |
| 8 | Second review | Risk is medium or high and `review` is missing, empty, or `by` is "self" | verified presence; reviewer independence is attested |
| 9 | Tests recorded | `tests` is empty | attested. CI's own test job is the verified evidence |
| 10 | Owner interventions (#11) | `owner_interventions` isn't a whole number | attested |

What CI can't detect: whether `substantial_ui` or `security_sensitive` should have been set, whether the reviewer was really another session, and whether the agent followed the skill. Those stay with the second reviewer and the owner's review, and the PR template asks for them explicitly.

## Project hooks (the font example)

Product rules live in the product repo. A project adds a `.karen/profile.json` with project gates (the resolver already supports this from #45), and runs its own style checks in its own CI. KAREN OS provides:
- the project-profile merge, so project gates appear in the resolved profile and check 5 enforces project-required skills;
- `examples/project-hook/`, a minimal example: a token file with approved fonts and a 20-line check that fails on any other font. Tests run it against a stylesheet using Times New Roman (fails) and Helvetica (passes).

Real LookAtMe checks come in #48.

## Changes (next PR, after approval)

- `scripts/check_pr.py`: checks 1 to 10, reusing `scripts/profiles.py` and the registry. Standard library only.
- `.github/workflows/checks.yml`: adds `pull-requests: read` so check 7 can confirm a merge. **This is a CI workflow change.**
- `scripts/pipeline.py pr`: pre-fills the profile block.
- `.github/pull_request_template.md` and `docs/templates/github/pull_request_template.md`: a Profile section, plus "Who reviewed, and in which session?" (#13).
- `docs/organisation/engineering.md`: a short section on the profile block. It's hash-pinned, so this needs a reviewed repin.
- `examples/project-hook/` plus tests: the simulations #46 asks for. A skipped skill, missing approval, bogus hash, self-review at medium risk, an unflagged workflow change and a wrong font each produce the expected failure.

## Limits, stated plainly

- **"PR metadata" is not a required check today.** The `main` ruleset requires only the two test jobs, so a failing PR-metadata check doesn't block merge. Making it required is a repository setting, **an owner action**. Until then, enforcement is visible but not blocking.
- **Agents use the owner's GitHub account.** GitHub can't tell an agent's push or comment from the owner's, so the ruleset can't prove who merged. The owner's merge stays the approval, and that is procedural.
- **Attested fields are claims.** A false `evidence` or `review` entry passes CI. That's why medium and high risk need a second reviewer, and why the owner sees the evidence before merging.

## Decisions this revision makes

Merging approves these. Say if any should change.

1. **The block is required on every PR from the merge onward**, with no opt-out. Omitting it fails check 1.
2. **Checks live in `check_pr.py`** (the existing "PR metadata" job), not a new script or job.
3. **CI gets `pull-requests: read`** to verify that design approvals were merged.
4. **After this ships, you make "PR metadata" a required check** in the `main` ruleset. I'll give the exact setting, and won't change settings myself.

## Rollback

Revert the implementation PR. Without the block requirement, PRs pass as they do today.
