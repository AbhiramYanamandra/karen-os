# Ponytail plugin: data, precedence and adoption plan

**Issue:** [#51](https://github.com/AbhiramYanamandra/karen-os/issues/51), part of [epic #43](https://github.com/AbhiramYanamandra/karen-os/issues/43). **Catalogue entry:** `ponytail-plugin` in [`skill-candidates.json`](skill-candidates.json).
**Status:** **approved, installed and registered** on 24 November 2026 ([approval](https://github.com/AbhiramYanamandra/karen-os/issues/51#issuecomment-7122275188), bound to the `v5.3.3` runtime tree hash). The owner chose the full plugin. The installed files match the pin in both runtimes, Codex has persisted hook trust, and Claude Code has the Ponytail status line configured. Live-session and full rollback checks remain open under #51. Results are under "Install record" and "Verification follow-up".
**Review:** agent self-review on 24 November 2026, from the upstream source read at both candidate commits. The owner chose `v5.3.3`. The install and its checks were run on 24 November.

## Source and pin

**Owner decision, 24 November 2026: pin the official release `v5.3.3`, unmodified, so the plugin runs as its developer released it.**

| | Pinned (owner-chosen) | Not chosen |
|---|---|---|
| Ref | release `v5.3.3`, `7801d061243d7b753bad0e0b3c057cd250b11755` | `main` at `ebd8654c2c627f721eb8f9c0d1bd4090a29f9e10` |
| Runtime tree SHA-256 | `5d64c155b77430005b735aa0d0348125a16ac2ae0e6d452bce81b4b497090395` | `5a294a24abd1728d3cd401d6e405d91bdbb3e898a7314fd8c4a80df96ff67c2f` |
| Difference | | Four commits later, with two hook fixes: stdin decoded as UTF-8 across chunk boundaries (upstream #1495), and subagent usage kept readable during partial imports (#1461) |

Known upstream issues in `v5.3.3`, fixed only after the release: hooks can garble non-ASCII input split across stdin chunks, and one unreadable subagent log can stop a transcript import. Moving to a later release is a new owner decision.

Repository: `DietrichGebert/ponytail`, MIT. The runtime tree is the 30 files in `.claude-plugin/`, `.codex-plugin/`, `hooks/` and `skills/`. Each file's hash is in the catalogue's `pinned_files`. The other folders hold other hosts' adapters, benchmarks, docs and tests, which neither runtime loads. `skills/ponytail/SKILL.md` is `9badd22a…a509` at both refs.

## What runs

**Claude Code** loads `.claude-plugin/plugin.json`: two hook files, the band and six skills (`ponytail`, `ponytail-review`, `ponytail-audit`, `ponytail-debt`, `ponytail-gain`, `ponytail-help`).

| Component | Trigger | What it does |
|---|---|---|
| `ponytail-activate.js` | SessionStart (startup, resume, clear, compact) | Writes the `.ponytail-active` mode flag in the Claude config folder. Injects the mode instructions, plus a repository map from `git ls-files` of up to 2,000 characters. Checks `settings.json` for a status line and may ask the model once to configure it |
| `ponytail-subagent.js` | SubagentStart | Injects the mode into every subagent, or only those matching `PONYTAIL_SUBAGENT_MATCHER`. Uses `node:vm` only to time-limit that regex test (100 ms) |
| `ponytail-mode-tracker.js` | UserPromptSubmit | Handles `/ponytail` mode changes. `/ponytail band import` starts the background transcript import, and `/ponytail band on\|off` writes `.ponytail-band` |
| Band (`hooks/band/register.tsx`) | Every turn | Shows the status band. Writes the task's ledger row, rebuilds `board.html`, and POSTs to the webhook if one is set |
| `ponytail-band-import.js` | Only on `/ponytail band import`, detached | Reads past transcripts and backfills ledger rows |

Every hook runs Node with a 15-second timeout.

**Codex** loads `.codex-plugin/plugin.json`: the same skills and `claude-codex-hooks.json` only. There is no band, so Codex has no ledger, board, import or webhook. The band and import commands are disabled under Codex, and Codex asks the owner to trust each hook in `/hooks`.

## Data inventory

### Read

| Source | When | Fields used |
|---|---|---|
| Current Claude Code session (band engine) | Every turn | Session id, start time, cost, per-turn cost, turns, busy time, token counts (input, output, cache read, cache write), model, Ponytail level, files created or reused this session, open callers, test results |
| Current transcript | Every turn | Session title and model |
| **Every** Claude Code transcript in the Claude config folder's `projects/*/*.jsonl`, plus each session's `subagents/` folder | Only on `/ponytail band import` | Usage records, message ids, custom title or the first line of the first prompt, and the working directory. Skips sessions run in temporary directories and sessions with no human first prompt (`claude -p`, benchmarks). There is no project filter |
| Repository | SessionStart | File list from `git ls-files`, given only to the model as context |
| Claude `settings.json` | SessionStart | `statusLine.command` only |

### Stored locally

| Location | Content | Written by |
|---|---|---|
| `$XDG_CONFIG_HOME/ponytail/band/<project>.csv`, or the `.config` folder in the user's home when unset | One row per task, replaced every turn. Columns: `key,started,project,name,cost_usd,turns,agent_minutes,tokens_total,tokens_output,reuse_pct,reused,new,callers_open,tests,level,model`. `key` is the first 8 characters of the session id plus the start time. `project` is the repository folder's name (a worktree counts as its main repository). `name` is the session title or the first line of the first prompt, up to 60 characters | Band and import |
| `…/ponytail/band/board.html` | Static board built from every project's CSV. Opens in the default browser and loads no external scripts or assets | Band, every turn |
| `…/ponytail/config.json` | `defaultMode` | `/ponytail` configuration |
| Claude config folder: `.ponytail-active`, `.ponytail-band`, `.ponytail-statusline-nudged`, a status-line script copy | Mode and display flags | Hooks |
| System keychain | `webhookToken`, declared `sensitive` | Claude Code plugin configuration |

Ponytail has **no built-in retention or pruning**. Rows stay until someone deletes them. Upstream creates the `band` folder owner-only (`0700`) and its files owner read and write (`0600`), as observed after install.

### Transmitted

Only the webhook sends anything, and only when `webhookUrl` is set. Nothing is sent by default.

- **When:** after every turn, in Claude Code only.
- **Request:** `POST <webhookUrl>` with `content-type: application/json`, plus `authorization: Bearer <webhookToken>` when a token is set. HTTPS is required. Plain `http` is allowed only to `localhost`, `127.0.0.1` or `[::1]`.
- **Payload** (`Snapshot`): `key`, `started`, `project`, `name` (empty when `sendNames` is false), `session` (the **full** session id), `level`, `model`, `cost`, `lastTurn`, `turns`, `agentMs`, `tokens` {`input`, `output`, `cacheRead`, `cacheWrite`}, `reuse`, `reused`, `created`, `callersOpen` and `tests`.
- **Not sent:** file names, prompt text beyond `name`, and code. `reused`, `created` and `callersOpen` are counts only.
- **Failure:** shows a status message. There is no retry or queue.

`$.ui.copy` puts a markdown summary on the clipboard, and only when the owner asks for it.

### Credentials

None are required. `webhookToken` is optional and is stored in the system keychain through Claude Code's sensitive plugin configuration. It must never be committed, logged or written to the ledger.

### Retention and access controls

| Control | Setting |
|---|---|
| Ledger on or off | Plugin config `ledger` (default true) |
| Ledger location | `XDG_CONFIG_HOME` |
| Task names off the wire | `sendNames: false` |
| Webhook off | Empty `webhookUrl` |
| Repository map | `PONYTAIL_MAP=0`. Size: `PONYTAIL_MAP_CHARS` |
| Subagent scope | `PONYTAIL_SUBAGENT_MATCHER` |
| Level | `PONYTAIL_DEFAULT_MODE` or `config.json` |
| Startup and status | `PONYTAIL_QUIET_STARTUP`, `PONYTAIL_HIDE_STATUS` |
| Band display | `/ponytail band off`. It hides the band, but recording continues |

KAREN OS adds no controls of its own (decision 4a): the ledger uses upstream's location, permissions and unlimited retention. It is outside every repository because it lives in the user config folder.

## Precedence

Ponytail is a coding-stage aid, subordinate to KAREN OS:

1. **KAREN first.** Startup, the engineering standard, project rules, the task and its lifecycle profile (#45) all win over Ponytail's mode text. Ponytail's own rule, never cut validation, data-loss handling, security, accessibility or anything the user asked for, is consistent with this. Where the two differ, KAREN wins.
2. **Level.** `full` by default. `ultra` only per task when the profile allows it. Ponytail's `review` mode never replaces KAREN review stages.
3. **No silent configuration.** The status-line nudge asks the model to edit `settings.json`. The owner approved it (decision 8), so agents may accept that one edit. Ponytail never changes repository settings, labels or Engineering HQ.
4. **Usage is not quality.** Ledger data is evidence of usage. It never replaces tests, verification or review receipts.
5. **Approval binds to content.** Approval covers the pinned runtime tree hash. Any plugin update returns the entry to `under-review`.

## Install and verification plan

This runs only after the owner's decisions are recorded.

**0. Baseline** (read-only):
- Record the Claude Code and Codex versions.
- Record the current hooks and status line in `settings.json`.
- Confirm the `ponytail` config folder doesn't exist yet.
- Time 10 prompts without Ponytail.

**1. Pin.** Confirm that the installed runtime files hash to `pinned_files` for the approved ref.

**2. Claude Code.**
- Add the marketplace at the pinned ref, then run `/plugin install ponytail@ponytail`, as two separate prompts.
- Leave `ledger` on and `webhookUrl` empty (decisions 4a and 5). No token is entered.
- Accept the status-line offer once (decision 8).

**3. Codex.**
- Upstream's Codex marketplace file installs `main`, even at the `v5.3.3` tag. To keep the pin (owner decision, 24 November), add a one-entry local marketplace that copies upstream's entry with `ref` set to `7801d061243d7b753bad0e0b3c057cd250b11755`, then `codex plugin add ponytail@ponytail`. Only the download pointer is local; the plugin files are upstream's.
- The owner trusts both hooks in `/hooks`.
- Expect skills and mode hooks only.

**4. Verify Claude Code.**
- `/plugin` lists Ponytail.
- Installed files hash to the approved values.
- A new session shows the SessionStart injection.
- One turn writes exactly one ledger row in the expected CSV, and `board.html` rebuilds.
- `webhookUrl` is empty, and no POST is made after a turn (decision 5).
- The status line appears in `settings.json` after the one accepted offer (decision 8).
- A subagent receives the injection, or doesn't, per the matcher.
- Negative control: with `ledger: false`, no row is written.

**5. Verify Codex.**
- `codex debug prompt-input` lists the Ponytail skills at the plugin path.
- The hook files hash to the approved values.
- A session log shows the SessionStart injection.
- Nothing is written under `ponytail/band`.

**6. Hook performance.**
- Run SessionStart, UserPromptSubmit and SubagentStart 20 times each, in karen-os and in the largest project repository.
- Pass: p95 of 1 second or less per hook, and no timeouts. The 15-second timeout is the hard ceiling.
- Record the transcript import's duration and CPU separately.

**7. Rollback** (each step independent):
- `/plugin remove ponytail` and `codex plugin remove ponytail`.
- Run upstream `scripts/uninstall.js` for the flags, config, status-line copy and its `settings.json` entry. Read it first, because it edits `settings.json`.
- Remove the keychain token.
- Delete `ponytail/band` only by owner choice: it holds the ledger history.
- Confirm that no hooks remain in either runtime and that timing returns to the baseline.

## Install record (24 November 2026)

| Check | Result |
|---|---|
| Baseline | Claude Code 2.1.330, Codex 0.171.0, Node 24.15.0. No Ponytail marketplace, plugin, config folder or flags. No `statusLine` and no hooks in Claude Code `settings.json` |
| Claude Code install | `claude plugin marketplace add <upstream git URL>#v5.3.3`. The clone is at `7801d061` (tag `v5.3.3`). `claude plugin install ponytail@ponytail`, user scope, defaults (ledger on, no webhook) |
| Codex install | Local one-entry marketplace, then `codex plugin add ponytail@ponytail`. `codex plugin list` shows ref `7801d061` |
| Pin | All 30 runtime files match `pinned_files` in both runtimes, with no extra runtime files |
| Hook timing (20 runs each, karen-os) | SessionStart p50 69 ms, p95 90 ms. SubagentStart p95 25 ms. UserPromptSubmit p95 27 ms. All exit 0, empty stderr. Pass (p95 ≤ 1 s) |
| Injection | SessionStart emits "PONYTAIL MODE ACTIVE — level: full" and the repository map. SubagentStart returns the same mode as `additionalContext` |
| Ledger | One headless turn wrote one row to `karen-os.csv` and rebuilt `board.html`. The board loads no external URLs |
| Network | No Ponytail plugin configuration is stored, so `webhookUrl` is empty and nothing is sent |
| Codex skills | `codex debug prompt-input` lists `ponytail:ponytail-*` skills from the pinned install |

Test side effects:
- The hook runs and the headless turn each set `.ponytail-statusline-nudged` without adding a status line. The agent deleted that flag, so the first interactive session still makes the one offer the owner approved.
- The ledger keeps the headless test row ("Reply with exactly: ok").

## Verification follow-up (24 November 2026)

Codex checked the installed files and configuration after the owner returned #51 to `status:ready`. This is an agent self-review. It does not establish live-session behaviour.

| Check | Observed result |
|---|---|
| Installed runtime files | All 30 `pinned_files` match in both Claude Code and Codex, with no extra files in the four runtime folders |
| Install sources | Claude Code's marketplace uses `v5.3.3`; Codex's local marketplace points to commit `7801d061243d7b753bad0e0b3c057cd250b11755` |
| Codex hook trust | Persisted trust records exist for SessionStart, UserPromptSubmit and SubagentStart. The plugin is enabled. Configuration alone does not prove execution |
| Claude Code status line | The enabled plugin's status-line command names `ponytail-statusline`. Rendering was not observed |
| Codex discovery | `codex debug prompt-input` lists the Ponytail skills. This command renders context, not a live hook run |
| Isolated cleanup | Upstream `scripts/uninstall.js` removed synthetic mode flags, configuration and status-line files. It preserved unrelated settings, unrelated Cursor hooks and the synthetic ledger. Repeating cleanup succeeded |

The cleanup check used a temporary directory, a synthetic home resolver and temporary configuration paths. It covered both a Ponytail-only status line and one combined with another command. It did not remove either live plugin or alter the owner's configuration. Host unregistration, reinstall and timing recovery remain unverified.

## Engineering HQ

Ponytail doesn't talk to GitHub. These are options for a follow-up issue:

- **A. Local importer (recommended first).** A KAREN script reads the CSV ledgers and posts per-issue cost, agent minutes, tokens and turns as a PR comment or as Project fields. It maps sessions to issues through `<type>/<issue>-<slug>` branch names. No external endpoint is needed. New Project fields need owner approval.
- **B. Webhook to an owner-operated endpoint.** The endpoint writes to Engineering HQ. Needs a hosted service, a token and a data-destination approval.
- **C. Board only.** `board.html` locally, with no HQ link.

## Owner decisions

1. ~~Pinned ref.~~ **Decided 24 November 2026: `v5.3.3`, the official release, unmodified.**
All decided by the owner on 24 November 2026. The principle: run Ponytail as its developer released it.

2. **Install: both runtimes.** Upstream marketplace in Claude Code (full plugin) and in Codex (skills and mode hooks), with both Codex hooks trusted.
3. **Transcript import: allowed** across all local Claude Code projects, on `/ponytail band import`. Data stays on this Mac.
4. **Ledger: upstream default (4a).** Default location, default file permissions, no retention limit. KAREN adds no `chmod`, pruning or backup rule.
5. **Webhook: none.** `webhookUrl` stays empty, so nothing leaves the Mac.
6. Webhook payload: not applicable while there is no webhook.
7. Webhook token: not applicable. None is issued.
8. **Status line: allowed.** Agents may accept Ponytail's one-time offer to add its status line to Claude Code `settings.json`.
9. **Engineering HQ: option C, board only.** `board.html` stays local. No new Project fields or automation. Option A can be proposed later as its own issue.

Installation and registry promotion are complete. The remaining work is verification, not another installation approval.

## Not verified

- A fresh Codex session executing the trusted hooks. Persisted trust covers three hook events; the earlier two-hook checklist was incomplete.
- The status line and band rendering in an interactive Claude Code session. The status line is configured.
- Hook timing was measured by running the hook scripts directly, not inside a live session, and only in karen-os, not the largest project repository. No before-install prompt timing was taken.
- The band was observed in one headless turn. An interactive session's band display was not.
- Network silence comes from the empty webhook setting and from reading the code. Traffic was not captured.
- The transcript import (`/ponytail band import`) was not run.
- Full host removal, absence of registered hooks, reinstall at the approved pin and timing recovery. The isolated cleanup check above covers only upstream's state-cleanup script.
