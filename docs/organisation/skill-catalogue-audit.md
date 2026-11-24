# Skill catalogue audit

**Issue:** [#44](https://github.com/AbhiramYanamandra/karen-os/issues/44), part of [epic #43](https://github.com/AbhiramYanamandra/karen-os/issues/43). **Charter slice:** PR A in the [engineering organisation charter](../engineering-organisation-charter.md).
**Status:** Agent self-review dated 2026-11-23, updated on 2026-11-24 for [#51](https://github.com/AbhiramYanamandra/karen-os/issues/51) (see "Follow-up findings"). It is not an independent review. Nothing here approves, installs or revokes a skill.
**Data:** [`skill-candidates.json`](skill-candidates.json) holds one entry per candidate. Each entry records the source, version, hashes, licence, dependencies, tools, privileges, compatibility, state, recommendation and any owner decision. The dated findings below retain the review history; the owner decisions and verification follow-up describe the current adoption state.

The approved registry, [`skills.json`](skills.json), holds the ten approved entries, promoted on 24 November 2026 under #51 with a manifest repin to revision `engineering-2`.

## Method

1. Listed the shared Skills CLI folder, the Claude Code user skill folder, the Codex user skill folder and the installed plugins. Private paths are reduced to location labels in the committed files.
2. Read provenance from the Skills CLI lock files and the plugin install records.
3. Hashed every file in each candidate package. The script read the files and executed nothing from them.
4. Read each candidate's whole SKILL.md and every bundled file under 1 KB. For larger bundled scripts, I read the imports and searched for network, subprocess, environment and install calls.
5. Compared each Skills CLI SKILL.md with its upstream repository's default branch, and checked upstream licences with `gh api`.

No skill was invoked, installed, updated or given credentials. No local skill content was copied into this repository.

## Initial findings (23 November 2026)

**Provenance.** 96 shared skills come from two repositories, `cursor/plugins` (60) and `mattpocock/skills` (36). Three more come from `vercel-labs/skills`, `shadcn/improve` and `cursor/plugins` through a second lock file. The ECC plugin is version 2.2.3 from `affaan-m/ECC`. All of these sources are MIT-licensed. The design skills in the Claude Code folder (`ui-ux-pro-max`, `design`, `ui-styling`, `brand`, `banner-design`, `slides`, `design-system`) have no lock entry, and `ui-ux-pro-max` has no licence at all.

**Drift.** Six reviewed SKILL.md files match upstream byte for byte. `unslop` and `principle-prove-it-works` do not. Either upstream changed after the 2026-11-09 install or the local copy was edited. Both need one pinned, re-read revision before approval.

**Runtime resolution and duplicates.**
- Claude Code sees shared skills through symlinks under unprefixed names, and plugin skills under an `ecc:` prefix. The same name can therefore mean different things. For example, `code-review` (mattpocock, two-axis review), `ecc:code-review` (a command) and Claude Code's built-in `/code-review` are three unrelated procedures.
- `ui-ux-pro-max` exists as two real directories with different SKILL.md files: 55 KB in the Claude Code folder and 28 KB in the shared folder. The catalogue lists them as two entries, `ui-ux-pro-max@claude-user-skills` and `ui-ux-pro-max@shared-agents-skills`. Both are unresolved: neither has a known source or licence, and I haven't established which variant each runtime loads under the shared name. Neither is preferred.
- `design` exists as two byte-identical copies.
- The ECC plugin ships each skill several more times, in its `.agents`, `.kiro` and `pi` folders and in translated docs. Only `skills/` is what Claude Code loads.
- I did not verify in a Codex session which folders Codex resolves. Its own user folder holds one skill (`hiring-panel`) plus the bundled system skills.

**Invocation.** `unslop`, `tdd`, `thermo-nuclear-code-quality-review` and `principle-prove-it-works` set `disable-model-invocation: true`. The model cannot select them on its own. A stage that makes one of them mandatory must load it explicitly, either from the lifecycle profile in PR B or from the pipeline. Agent judgement can't be relied on to pick them up.

**Not found (23 November).** Ponytail is not installed anywhere and appears in no lock file. Figma is available only as a hosted MCP connector. The `/figma-use` skill it names has no local package to inspect. *Superseded on 24 November: see "Follow-up findings". Ponytail's source is now identified, and Figma is also enabled in Codex desktop.*

## Follow-up findings (#51, 24 November 2026)

**Ponytail.** The source is `DietrichGebert/ponytail` (MIT). The owner chose the **full plugin**: hooks, ledger, cost and token tracking, transcript import, board, extra skills and webhook. The catalogue entry `ponytail-plugin` pins the 30 runtime files at the official release `v5.3.3` (owner decision, 24 November). [`ponytail.md`](ponytail.md) holds the data inventory, precedence rules, install, verification and rollback plan, and the owner decisions, all decided on 24 November. **Approved and installed** on 24 November in both runtimes, hash-verified; see the install record in ponytail.md.

**ui-ux-pro-max.** Both variants come from `nextlevelbuilder/ui-ux-pro-max-skill` v2.15.0 (`a38d04c3`, MIT). Their 67 non-SKILL files are byte-identical to that release. Each SKILL.md is the upstream installer's render of one template for a different target: Claude (55 KB, quick reference inlined) or generic (28 KB). The owner approved the generic render and rejected the other variant. The Claude user folder now links to the shared copy.

**unslop and principle-prove-it-works.** Both match `cursor/plugins` commit `182f2ce4` byte for byte, with no local edits. Upstream `2f87c854` later shortened both, and for prove-it-works it removed the broken adapter link.

**Figma.** It is enabled in Claude Code as the hosted connector and in **Codex desktop** as the curated plugin. A missing entry in the Codex CLI's MCP list reflects CLI configuration only, and doesn't show the desktop plugin is absent. Figma skills are served remotely and cannot be hash-pinned.

**Runtime resolution** (observed on Claude Code 2.1.330 and Codex 0.171.0):

| | Claude Code | Codex |
|---|---|---|
| Skill folders read | Claude user folder (shared skills arrive as symlinks), project `.claude/skills`, plugins (namespaced, such as `ecc:`) | Codex user folder, the shared folder, bundled system skills. It doesn't read the Claude user folder |
| `ui-ux-pro-max` resolves to | The Claude user-folder symlink to the shared generic render | The same shared generic render |
| `disable-model-invocation: true` | Honoured. Hidden from the model and loaded through `/name` | **Ignored.** The rendered prompt (`codex debug prompt-input`) lists the skill as model-selectable |
| Load evidence | Transcript line `Base directory for this skill: <path>`. It records the symlink path, with no hash | Session log shows a shell read of the SKILL.md path. No hash |
| ECC plugin skills | Available | Not available |
| Ponytail (when installed) | Full plugin: hooks, band, skills | Skills and mode hooks only. Hooks need trust |
| Figma | Hosted connector | Desktop curated plugin |

Neither runtime records a content hash at load time, so the load-receipt step in "Testing that a mandatory skill was loaded" has to hash the resolved file separately.

## Owner decisions (#51, 24 November 2026)

Recorded in each entry's `owner_decision` in [`skill-candidates.json`](skill-candidates.json). Every approved hash was recomputed from the files on disk before recording, or from upstream for prove-it-works. Authentication is procedural: the owner merges the PR that records them.

| Entry | Decision |
|---|---|
| `ui-ux-pro-max@shared-agents-skills` | Approved: one shared copy of the v2.15.0 generic render. Installed: the Claude user folder links to it. |
| `ui-ux-pro-max@claude-user-skills` | Rejected: superseded by the shared copy. |
| `unslop` | Approved at `182f2ce4`, with examples. Mandatory for LinkedIn drafts. |
| `principle-prove-it-works` | Approved at `2f87c854`. Installed. |
| `tdd`, `diagnosing-bugs`, `code-review` | Approved. `code-review` takes the GitHub issue as its spec. |
| `thermo-nuclear-code-quality-review` | Approved for high-impact review only, alongside a correctness and security review. |
| `ecc:security-review` | Approved as a checklist only. Its dependency-changing steps need their own approval. |
| `figma` | Approved: read and write tools in **all** Figma projects, broader than the named-projects recommendation. Remote and unpinned, so the approval binds to scope only. |

### Install record (24 November 2026)

| Step | Result |
|---|---|
| Backups | The Claude render of `ui-ux-pro-max` and the `182f2ce4` prove-it-works SKILL.md were copied, byte-identical, to a backup folder under the Claude config folder (outside every skill folder) |
| `ui-ux-pro-max` | The Claude user-folder directory was replaced by a relative symlink to the shared copy, the same style as the other shared skills |
| `principle-prove-it-works` | The shared SKILL.md was replaced with the read-only upstream fetch at `2f87c854`, after its SHA-256 matched |
| Hashes | All seven approved local skills hash to their `approved_sha256` through both the Claude user folder and the shared folder. The Codex user folder holds no copies under the same names |
| Codex resolution | `codex debug prompt-input` (Codex 0.171.0) lists both skills from the shared folder |
| Rollback | Remove the symlink and copy both backups back. Not rehearsed |

**Risk: the Skills CLI lock does not pin a ref.** The home-level lock records `cursor/plugins` with no commit, so `npx skills update` would move `unslop` and `principle-prove-it-works` to upstream's default branch and break their approved hashes. Don't run it for these skills until a pinning method is chosen. `ui-ux-pro-max` has no lock entry.

Not verified: an actual skill load in a new Claude Code or Codex session, and Claude Code's resolution beyond the filesystem symlink.

These entries are promoted into the registry [`skills.json`](skills.json), each with its hash, scope and decision reference. The manifest is repinned to revision `engineering-2`.

### Verification follow-up (24 November 2026)

Codex repeated the installed-file checks after the owner returned #51 to `status:ready`. This is a self-review, not an independent review or a claim that the skills were followed.

| Package | Observed result |
|---|---|
| `unslop`, `tdd`, `diagnosing-bugs`, `principle-prove-it-works`, `thermo-nuclear-code-quality-review`, `code-review`, `ui-ux-pro-max` | Each SKILL.md and package tree matches its approved catalogue hash. Each Claude user-folder entry resolves to its corresponding shared package |
| `ecc:security-review` | SKILL.md and package tree match the approved hash in the Claude Code plugin. It remains unavailable in Codex |
| `ponytail-plugin` | All 30 runtime files match the pin in both runtimes, with no extra runtime files. See [Ponytail verification](ponytail.md#verification-follow-up-24-november-2026) for trust, status-line and isolated-cleanup results |
| `figma` | Remote connector, unpinned by design. No new connector invocation or editable-design test was performed |

The tree check used the catalogue's `os.walk` ordering, sorted directory and file names, and one `relative-path NUL file-sha256 LF` record per file, including the final newline. It compared package bytes, not just the entry names.

`codex debug prompt-input` lists the seven shared skills and Ponytail skills, and does not list `ecc:security-review`. Discovery does not prove a skill was loaded in a task. No personal paths, configuration contents or session transcripts are published here.

Remaining acceptance gaps for #51:

- Actual skill-load records from fresh Claude Code and Codex sessions, tied to the approved package hashes. Claude Code's name resolution still needs runtime evidence beyond the symlinks.
- Ponytail live-session checks, the ledger-disabled negative control, transcript import and the outstanding timing measurements in [its verification plan](ponytail.md#install-and-verification-plan).
- Full host-plugin rollback and restore. Isolated upstream cleanup succeeded, but it does not establish host unregistration or recovery of live-session timing.

The registry promotion criterion is complete. Keep #51 open until the remaining criteria are met or the owner explicitly changes their scope.

## Risky additions

| Candidate | Problem | Recommendation |
|---|---|---|
| `find-skills` | Treats install counts and GitHub stars as trust, then runs `npx skills add -g -y`, a global install with confirmation skipped. | Reject. Replace with the PR D discovery procedure. |
| `design` | Generator scripts load `.env` files from the user's agent configuration folders, send prompts to Google Gemini and suggest `pip install`. | Reject as a default. It needs a sensitive-data destination and spending approval. |
| `ecc:security-scan` | Runs `ecc-agentshield` through `npx` with no pinned version. `--fix` rewrites agent configuration, and `--opus` needs a paid API key. | Reject. |
| `ecc:security-bounty-hunter` | Targets external bounty programmes, downloads Semgrep rules and builds working exploits. | Reject outside a separately authorised security engagement. |
| `ecc:security-review` | A good checklist, but it suggests `npm audit fix` and `npm update`. | Use as a checklist only. Dependency changes need their own approval. |

## Adopted set by stage

The registry records the approved content and scope. [`workflow-profiles.json`](workflow-profiles.json) defines when each skill is required or recommended. Approval does not establish runtime availability or compliance with the instructions.

| Stage | Required | Selected by task | Not in the set |
|---|---|---|---|
| All managed work | KAREN core: startup, engineering standard, project rules (already enforced) | | |
| Substantial UI design | Approved Figma connector and shared `ui-ux-pro-max` | `ui-styling` only after separate approval | The rejected Claude render; `design` is not approved |
| Implementation | Approved, installed and registered Ponytail `v5.3.3` for applicable coding profiles ([ponytail.md](ponytail.md)) | Project and language conventions | |
| Bugs and tests | | `diagnosing-bugs`, `tdd` | `ecc:tdd-workflow` (duplicate, heavier) |
| Verification | Approved `principle-prove-it-works` | Project test and lint commands | `ecc:verification-loop` (npm-only, weaker secret scan) |
| Medium- and high-risk review | Approved `code-review` with the GitHub issue as its spec | Low-risk self-review, labelled as such | |
| High-impact review | `thermo-nuclear-code-quality-review`, alongside a correctness and security review | | |
| Security-sensitive work | `ecc:security-review` as a checklist | | `ecc:security-scan`, `ecc:security-bounty-hunter` |
| LinkedIn writing | Approved `unslop` | | `watermarks-remover:clean-user-facing-text` overlaps it (not reviewed) |
| Skill discovery | Not yet implemented. PR D is tracked in #47 | | `find-skills` is not approved |

## Owner decisions: approve, reject, revoke

`skill-candidates.json` declares `owner_decision_schema`. A candidate's `state` may become `approved`, `rejected` or `revoked` only through a matching `owner_decision`. The agent's `recommendation` never changes `state`.

| Decision | Sets state | Required fields | Meaning |
|---|---|---|---|
| `approve` | `approved` | `by`, `date`, `reference`, `approved_sha256`, `scope` | Allows that exact content (the hash must equal the entry's `tree_sha256`) for the stated stages or projects. Any content change returns the entry to `under-review`. |
| `reject` | `rejected` | `by`, `date`, `reference`, `reason` | Declines the candidate as reviewed. A later revision can be proposed again as a new review. |
| `revoke` | `revoked` | `by`, `date`, `reference`, `reason`, `revokes`, `revoked_sha256` | Withdraws an earlier approval. It cites that approval's `reference` and the hash it covered. From `date` the skill may not be loaded for KAREN work. It doesn't uninstall anything, and approving it again needs a new `approve`. |

The difference is that approval binds to content, while revocation binds to an earlier approval. A revoke without a prior approval to cite is invalid. A reject needs no hash because nothing was ever allowed.

### What a recorded decision proves

The tests check only the **shape** of a decision: required fields, a matching hash, and a decision type that agrees with the state. They do **not** prove that the owner made it. Agents act through the owner's GitHub account under the standing authority in the engineering standard, so an agent can write a schema-valid `owner_decision` and push it on a branch. The only control today is procedural: the owner reviews the diff and merges. A decision buried in a large diff could be missed.

The owner chose procedural authentication for now: review and merge of decision changes. The profiles and PR checks consume the approved registry, but do not independently prove who approved it. Stronger controls remain possible follow-ups, not current requirements:

1. **Owner-signed decisions.** Decision changes land only in commits signed with a key agents don't hold. CI verifies each signature against a key fingerprint allowlisted in the repository. This is verifiable today with `git verify-commit`, and needs no new service.
2. **Separate agent identity.** Agents use their own GitHub identity or app, so the owner's account actions become distinguishable. This changes repository access and needs explicit owner approval, as the charter's Limits section notes.
3. **Decision diffs flagged for review.** CI fails or labels any PR that changes `owner_decision` or `skills.json` unless the PR is marked as a decision PR, so the change can't hide inside other work. This is weaker: it makes the change visible but doesn't prove who made it.

Until one of these exists, treat every recorded decision as **procedural**, not technically verified.

## Testing that a mandatory skill was loaded

A skill file existing on disk, or appearing in a listing, does not show that an agent loaded it, still less that it followed it. Four candidates set `disable-model-invocation: true` (`unslop`, `tdd`, `thermo-nuclear-code-quality-review`, `principle-prove-it-works`). In Claude Code that flag stops the model from invoking the skill itself, so a mandatory stage has to load it some other way: the owner types `/<name>`, or the pipeline supplies the body. Reading the file directly does not establish Claude Code's native invocation path. Codex 0.171.0 lists these skills as model-selectable despite the flag, as observed in the runtime-resolution table above.

Proposed protocol for #46. None of it has been run here.

1. **Resolution.** In each runtime, record which file the name resolves to and hash it. Pass only if the hash equals the approved `tree_sha256`. The `ui-ux-pro-max` collision shows why: one name, two files.
2. **Load evidence.** Capture the runtime's own record of the load, not the agent's statement. For Claude Code, that is the session transcript entry for the skill invocation or slash-command expansion, with session id and skill name. For Codex, it is the equivalent session log entry. Both formats must be confirmed by test before CI relies on them.
3. **Negative control.** Run the same task without invoking the skill and confirm there's no load record. For a flagged skill, confirm the model's own attempt to invoke it is refused.
4. **Behaviour canary.** Use a synthetic test-only skill with a harmless, checkable instruction (for example, end the reply with a fixed token) and confirm the output obeys it after an explicit load. This shows the load path works for that fixture only. Installing even a synthetic skill counts as installation, so it needs owner approval and an isolated folder.
5. **PR load receipt.** The ready PR states the skill id, resolved hash, runtime, session id and how the skill was invoked. CI can check the hash against the approved entry and that a receipt exists. Without the attached runtime record it remains an agent attestation, and whether the agent followed the skill's prose can't be verified mechanically.

## Decisions for the owner

1. ~~Approve, reject or change each recommendation in `skill-candidates.json`.~~ Answered on 24 November for the entries above. The rejection recommendations (`find-skills`, `design`, `ecc:tdd-workflow`, `ecc:verification-loop`, `ecc:security-scan`, `ecc:security-bounty-hunter`) and the `ui-styling` hold are still undecided. Each decision is recorded in that entry's `owner_decision` using the schema above, ideally in an owner-signed commit.
2. ~~Name Ponytail's source repository.~~ Answered: `DietrichGebert/ponytail`, full plugin. All its decisions are recorded in [ponytail.md](ponytail.md).
3. ~~Say where each `ui-ux-pro-max` variant came from.~~ Answered: v2.15.0, MIT, one shared copy of the generic render.
4. ~~Figma write tools.~~ Answered: allowed in all projects.
4a. ~~unslop and principle-prove-it-works versions.~~ Answered: unslop stays at `182f2ce4`, prove-it-works moves to `2f87c854`.
5. Decide whether to remove or disable the rejected skills locally. That is a change to your own machine, so this PR doesn't do it.
6. ~~Choose how decisions will be authenticated for #46.~~ Answered for now: procedural (the owner's merge). Signed commits remain the stronger option for later.

## Not covered

- Of the 106 shared skills and 314 ECC skills, all but the candidates in this inventory were listed and not read. Only the candidates named in #44 were reviewed. They include `ecc:coding-standards` and `create-verification-skill`.
- Codex discovery was checked with `codex debug prompt-input`. Fresh-session skill loads remain unverified. Ponytail's earlier direct hook checks and limited timing evidence are recorded in [its install record](ponytail.md#install-record-24-november-2026). No webhook is configured.
- The meaning of the lock files' own `computedHash` values was not established. The hashes above are computed independently.
- Whether a model follows a skill's prose cannot be proved by this inventory.
- Recorded owner decisions are validated for shape only. The owner chose procedural authentication; #46 does not prove decision authenticity.
- The explicit-loading protocol is a proposal. No runtime load, negative control or canary was run.
