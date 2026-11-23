# Skill catalogue audit

**Issue:** [#44](https://github.com/AbhiramYanamandra/karen-os/issues/44), part of [epic #43](https://github.com/AbhiramYanamandra/karen-os/issues/43). **Charter slice:** PR A in the [engineering organisation charter](../engineering-organisation-charter.md).
**Status:** Agent self-review dated 2026-11-23. It is not an independent review. Nothing here approves, installs or revokes a skill.
**Data:** [`skill-candidates.json`](skill-candidates.json) holds one entry per candidate. Each entry records the source, the version, SHA-256 hashes, the licence, dependencies, tools, privileges, compatibility, the state, the recommendation and an empty `owner_approval`.

The approved registry, [`skills.json`](skills.json), is unchanged and still has `entries: []`. It is hash-pinned in the context manifest, so filling it needs a separately reviewed repin once you approve entries.

## Method

1. Listed the shared Skills CLI folder, the Claude Code user skill folder, the Codex user skill folder and the installed plugins. Private paths are reduced to location labels in the committed files.
2. Read provenance from the Skills CLI lock files and the plugin install records.
3. Hashed every file in each candidate package. The script read the files and executed nothing from them.
4. Read each candidate's whole SKILL.md and every bundled file under 1 KB. For larger bundled scripts, I read the imports and searched for network, subprocess, environment and install calls.
5. Compared each Skills CLI SKILL.md with its upstream repository's default branch, and checked upstream licences with `gh api`.

No skill was invoked, installed, updated or given credentials. No local skill content was copied into this repository.

## What I found

**Provenance.** 96 shared skills come from two repositories, `cursor/plugins` (60) and `mattpocock/skills` (36). Three more come from `vercel-labs/skills`, `shadcn/improve` and `cursor/plugins` through a second lock file. The ECC plugin is version 2.2.3 from `affaan-m/ECC`. All of these sources are MIT-licensed. The design skills in the Claude Code folder (`ui-ux-pro-max`, `design`, `ui-styling`, `brand`, `banner-design`, `slides`, `design-system`) have no lock entry, and `ui-ux-pro-max` has no licence at all.

**Drift.** Six reviewed SKILL.md files match upstream byte for byte. `unslop` and `principle-prove-it-works` do not. Either upstream changed after the 2026-11-09 install or the local copy was edited. Both need one pinned, re-read revision before approval.

**Runtime resolution and duplicates.**
- Claude Code sees shared skills through symlinks under unprefixed names, and plugin skills under an `ecc:` prefix. The same name can therefore mean different things. For example, `code-review` (mattpocock, two-axis review), `ecc:code-review` (a command) and Claude Code's built-in `/code-review` are three unrelated procedures.
- `ui-ux-pro-max` exists as two real directories with different SKILL.md files: 55 KB in the Claude Code folder and 28 KB in the shared folder. Claude Code and agents that read the shared folder get different instructions under the same name.
- `design` exists as two byte-identical copies.
- The ECC plugin ships each skill several more times, in its `.agents`, `.kiro` and `pi` folders and in translated docs. Only `skills/` is what Claude Code loads.
- I did not verify in a Codex session which folders Codex resolves. Its own user folder holds one skill (`hiring-panel`) plus the bundled system skills.

**Invocation.** `unslop`, `tdd`, `thermo-nuclear-code-quality-review` and `principle-prove-it-works` set `disable-model-invocation: true`. The model cannot select them on its own. A stage that makes one of them mandatory must load it explicitly, either from the lifecycle profile in PR B or from the pipeline. Agent judgement can't be relied on to pick them up.

**Not found.** Ponytail is not installed anywhere and appears in no lock file. Figma is available only as a hosted MCP connector. The `/figma-use` skill it names has no local package to inspect.

## Risky additions

| Candidate | Problem | Recommendation |
|---|---|---|
| `find-skills` | Treats install counts and GitHub stars as trust, then runs `npx skills add -g -y`, a global install with confirmation skipped. | Reject. Replace with the PR D discovery procedure. |
| `design` | Generator scripts load `.env` files from the user's agent configuration folders, send prompts to Google Gemini and suggest `pip install`. | Reject as a default. It needs a sensitive-data destination and spending approval. |
| `ecc:security-scan` | Runs `ecc-agentshield` through `npx` with no pinned version. `--fix` rewrites agent configuration, and `--opus` needs a paid API key. | Reject. |
| `ecc:security-bounty-hunter` | Targets external bounty programmes, downloads Semgrep rules and builds working exploits. | Reject outside a separately authorised security engagement. |
| `ecc:security-review` | A good checklist, but it suggests `npm audit fix` and `npm update`. | Use as a checklist only. Dependency changes need their own approval. |

## Proposed minimal set by stage

Proposals only. Each one needs your approval of the pinned hash before it becomes mandatory.

| Stage | Required | Selected by task | Not in the set |
|---|---|---|---|
| All managed work | KAREN core: startup, engineering standard, project rules (already enforced) | | |
| UI design | Figma connector plus one UI/UX guide, **on hold** until source, licence and a runtime test exist | `ui-styling` per project that uses shadcn | `design`, the second `ui-ux-pro-max` copy |
| Implementation | Ponytail, **on hold**: not installed | Project and language conventions | |
| Bugs and tests | | `diagnosing-bugs`, `tdd` | `ecc:tdd-workflow` (duplicate, heavier) |
| Verification | `principle-prove-it-works` after pinning | Project test and lint commands | `ecc:verification-loop` (npm-only, weaker secret scan) |
| Review | `code-review` with the GitHub issue as its spec | | |
| High-impact review | `thermo-nuclear-code-quality-review`, alongside a correctness and security review | | |
| Security-sensitive work | `ecc:security-review` as a checklist | | `ecc:security-scan`, `ecc:security-bounty-hunter` |
| LinkedIn writing | `unslop` after pinning | | `watermarks-remover:clean-user-facing-text` overlaps it (not reviewed) |
| Skill discovery | PR D procedure | | `find-skills` |

## Decisions for the owner

1. Approve, reject or change each recommendation in `skill-candidates.json`. An approval records your decision in that entry's `owner_approval`, along with the exact hash.
2. Name Ponytail's source repository, or drop it from the charter's coding-stage rule.
3. Pick one `ui-ux-pro-max` copy, and say where it came from, so its licence can be checked.
4. Decide whether the Figma connector's write tools are allowed for design work, and in which projects.
5. Decide whether to remove or disable the rejected skills locally. That is a change to your own machine, so this PR doesn't do it.

## Not covered

- Of the 106 shared skills and 314 ECC skills, all but the candidates in this inventory were listed and not read. Only the candidates named in #44 were reviewed. They include `ecc:coding-standards` and `create-verification-skill`.
- Codex runtime resolution was not tested in a Codex session.
- The meaning of the lock files' own `computedHash` values was not established. The hashes above are computed independently.
- Whether a model follows a skill's prose cannot be proved by this inventory.
