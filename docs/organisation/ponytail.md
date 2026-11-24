# Ponytail plugin: data, precedence and adoption plan

**Issue:** [#51](https://github.com/AbhiramYanamandra/karen-os/issues/51), part of [epic #43](https://github.com/AbhiramYanamandra/karen-os/issues/43). **Catalogue entry:** `ponytail-plugin` in [`skill-candidates.json`](skill-candidates.json).
**Status:** under review. Nothing is installed. The owner chose the **full plugin** on 23 November 2026, keeping every capability, including features that read session metadata, run hooks or send telemetry. Installation waits for the decisions at the end of this document.
**Review:** agent self-review on 24 November 2026, from the upstream source read at both candidate commits. No plugin code was run.

## Source and pin

| | Recommended | Alternative |
|---|---|---|
| Ref | `main` at `ebd8654c2c627f721eb8f9c0d1bd4090a29f9e10` | release `v5.3.3`, `7801d061243d7b753bad0e0b3c057cd250b11755` |
| Runtime tree SHA-256 | `5a294a24abd1728d3cd401d6e405d91bdbb3e898a7314fd8c4a80df96ff67c2f` | `5d64c155b77430005b735aa0d0348125a16ac2ae0e6d452bce81b4b497090395` |
| Difference | Two hook fixes: stdin decoded as UTF-8 across chunk boundaries (upstream #1495), and subagent usage kept readable during partial imports (#1461). No new network calls, files or permissions | |

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

Ponytail has **no built-in retention or pruning**. Rows stay until someone deletes them. Files take the default umask, and no permissions are set explicitly.

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

KAREN OS adds three controls of its own:
- `chmod 700` on the `ponytail/band` folder.
- An owner-chosen retention period, enforced by deleting rows older than that, manually or on a schedule. Ponytail has no pruning.
- The folder stays out of every repository and every backup the owner doesn't control.

## Precedence

Ponytail is a coding-stage aid, subordinate to KAREN OS:

1. **KAREN first.** Startup, the engineering standard, project rules, the task and its lifecycle profile (#45) all win over Ponytail's mode text. Ponytail's own rule, never cut validation, data-loss handling, security, accessibility or anything the user asked for, is consistent with this. Where the two differ, KAREN wins.
2. **Level.** `full` by default. `ultra` only per task when the profile allows it. Ponytail's `review` mode never replaces KAREN review stages.
3. **No silent configuration.** The status-line nudge asks the model to edit `settings.json`. Agents decline it unless the owner approves it (decision 8). Ponytail never changes repository settings, labels or Engineering HQ.
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
- Set `ledger`, `sendNames` and `webhookUrl` per the decisions.
- The owner enters `webhookToken`, so only the keychain holds it.
- Apply `chmod 700` to the ledger folder.

**3. Codex.**
- `codex plugin marketplace add DietrichGebert/ponytail` at the same ref, then `codex plugin add ponytail@ponytail`.
- The owner trusts both hooks in `/hooks`.
- Expect skills and mode hooks only.

**4. Verify Claude Code.**
- `/plugin` lists Ponytail.
- Installed files hash to the approved values.
- A new session shows the SessionStart injection.
- One turn writes exactly one ledger row in the expected CSV, and `board.html` rebuilds.
- With a webhook:
  - Check against a local `http://127.0.0.1` receiver first, then the approved destination.
  - One POST per turn, with exactly the payload fields above.
  - `name` is empty when `sendNames` is false.
  - The bearer token is present.
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

## Engineering HQ

Ponytail doesn't talk to GitHub. These are options for a follow-up issue:

- **A. Local importer (recommended first).** A KAREN script reads the CSV ledgers and posts per-issue cost, agent minutes, tokens and turns as a PR comment or as Project fields. It maps sessions to issues through `<type>/<issue>-<slug>` branch names. No external endpoint is needed. New Project fields need owner approval.
- **B. Webhook to an owner-operated endpoint.** The endpoint writes to Engineering HQ. Needs a hosted service, a token and a data-destination approval.
- **C. Board only.** `board.html` locally, with no HQ link.

## Owner decisions

1. Pinned ref: `ebd8654c` (recommended) or `v5.3.3`.
2. Install from the upstream marketplace in Claude Code and in Codex, including trusting the Codex hooks.
3. Transcript import across **all** local Claude Code projects. Upstream has no project filter.
4. Ledger location, `chmod 700`, and a retention period (for example 180 days).
5. Webhook destination URL and its operator, or no webhook for now.
6. Webhook payload: whether to send task names (`sendNames`), and acceptance that the full session id is sent.
7. Webhook token: whether to issue one, held only in the keychain.
8. Whether to allow Ponytail's status line in `settings.json`.
9. Engineering HQ option A, B or C, including approval of any new Project fields or automation.

## Not verified

- Hook timing, ledger writes and webhook behaviour come from reading the code. None of it has been run.
- Codex hook trust prompts and plugin paths come from documentation, and haven't been observed in a session.
- Upstream `uninstall.js` was read but not run.
