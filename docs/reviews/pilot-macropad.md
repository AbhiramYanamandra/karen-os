# Pilot log: Macropad

The first engineering pilot of KAREN OS, run 22 and 23 November 2026 in the independent Macropad repository ([AbhiramYanamandra/macropad](https://github.com/AbhiramYanamandra/macropad)). It covers connecting the project, two plan runs by fresh agent sessions, independent review, publication, and the rollout of the issue-to-PR pipeline that the pilot made necessary.

**Status: in progress.** The work is merged, but no step has been verified on the physical pad yet. The pad checks are Macropad issues [#3](https://github.com/AbhiramYanamandra/macropad/issues/3), [#4](https://github.com/AbhiramYanamandra/macropad/issues/4) and [#5](https://github.com/AbhiramYanamandra/macropad/issues/5).

## What was measured and how

- **Timings** are elapsed times between Git commits (local time, UTC+10) and GitHub pull request timestamps. Start times of agent sessions were not recorded, so each figure is approximate. No agent measured its own elapsed time.
- **Owner interventions** are counted from the session transcripts: decisions, approvals, clarifications and manual commands.
- **Reliability** means what the reviewer found when checking each run, not self-reported results.

## Timeline

| When | What | Who |
|---|---|---|
| 22 Nov, 21:38 | Macropad connected as a Level 2 project: `AGENTS.md` pointer block, `CLAUDE.md`, `.karen/project.json` | Claude Code, KAREN OS session |
| 22 Nov | Fresh Claude Code (2.1.330) and Codex (0.171.0) sessions in the Macropad both found the pointer, ran the reader and reported the rules and plans correctly | Owner ran both |
| 22 Nov, 22:12 | Plan 008 written: rebuild Macropad Studio in the approved Porcelain design, with an architecture approval gate | Claude Code |
| 22 Nov, 22:16 | Gap found while planning: the knob is not fitted, and the only layer switch was the knob press, so the pad was stuck on layer 0 | Claude Code, confirmed by owner |
| 22 Nov, 22:32 | Plan 009 written from owner decisions: keys 7 + 9 cycle forward through layers when no knob is fitted | Claude Code |
| 22 Nov, 22:48 | Plan 009 implemented and committed on its branch, stopping before the pad check as instructed | Codex, fresh session |
| 22 Nov, 22:52 | Independent review, then fast-forward merge to `main`, marked done with the pad check pending | Claude Code |
| 22 Nov, 23:15 | Plan 008 Steps 1 and 2: design inventory and architecture proposal, stopped at the approval gate | Fresh Macropad session |
| 22 Nov, 23:21 | Owner approved the architecture as written; approval and file hash recorded | Owner, recorded by Claude Code |
| 22 Nov, 23:23 | Privacy scan, KMK licence added, home paths removed; repository published publicly | Claude Code, owner chose public |
| 22 Nov, 23:25 | Plan 008 Step 3 stopped at its drift check on an unexpected file; baseline rebased after owner clarification | Macropad session, then Claude Code |
| 22 Nov, 23:59 | Slice 1 built: native Keys window, real keymap editing, safe sync with backup and recovery | Macropad session |
| 23 Nov, 00:12 | Self-review: seven correctness fixes, review record and pad checklist | Same Macropad session |
| 23 Nov, 00:17 | PR #1 opened and merged by the owner 14 seconds later, with an empty description and no pad check | Owner |
| 23 Nov, 00:49 | KAREN OS engineering standard merged (KAREN OS PR #2); rulesets on `main` in both repositories | Claude Code, owner merged |
| 23 Nov, 01:12 | Macropad adopted the pipeline: CI, templates, agent rules, open work as issues #3 to #12 (Macropad PR #13) | Claude Code, owner merged |

## Measurements

| Run | Elapsed (approx.) | Size | Result |
|---|---|---|---|
| Plan 009, Codex | 16 min from plan commit to implementation commit | 10 files, +319 −28 | Correct on review. Host checks pass. Pad check open. |
| Plan 008 Steps 1 and 2 | 23 min | 2 documents, 408 lines | Thorough proposal, approved unchanged |
| Plan 008 slice 1, build | 34 min after the drift fix | 19 files, +1708 −57 | 19 Swift tests pass, also in CI |
| Plan 008 slice 1, self-review | 13 min | 9 files, +238 −14 | Found and fixed seven real defects |
| Pipeline rollout, both repositories | About 1 hour 15 min, including owner review | KAREN OS PR #2 (+493), Macropad PR #13 | CI green on every PR |

Owner interventions during the plan runs:

- **Decisions:** 4. Layer switching by 7 + 9, cycle forward only, run 009 before 008, approve the architecture as written.
- **Clarifications:** 1. The drift check's unexpected file was expected.
- **Command approvals:** 3 Git commands in the Codex run, plus Swift and Git sandbox prompts in the slice 1 run.
- **Manual commands:** 3 `git push` runs, because the auto-mode classifier blocked agent pushes before the pipeline gave standing authority.

## What worked

- **The pointer block works across tools.** Both Claude Code and Codex loaded the shared rules from an independent repository on the first try, and Codex's default sandbox could read KAREN OS from another workspace.
- **STOP conditions held.** Every executor stopped where told: before pad checks, at the architecture gate, and on the unexpected file in the drift check. None improvised past a gate.
- **Honest evidence.** Runs separated what they proved from what they did not, for example "Saved to pad; firmware reload not verified", and labelled renders as renders, not photographs.
- **Scope held.** No run touched `kmk/`, the firmware outside its plan, or the real `CIRCUITPY` drive.
- **The self-review found real bugs.** Slice 1's review caught seven correctness defects, including a sync path that could replace a valid keymap before detecting a missing image.
- **Independent review added value.** Checking plan 009 against the vendored KMK confirmed the new layer key uses KMK's own layer-change path, which was the plan's main risk.

## What went wrong

### Process

- **No pipeline at first.** Work lived on local branches and in chat. The owner had no single place to review a change, which led to PR #1 being merged in 14 seconds with an empty description and before its pad check. This gap is why decision D17 and the engineering standard exist.
- **The plan 008 drift check was too brittle.** It compared against an old commit and failed on an archived image moved by an unrelated tidy-up. It stopped correctly, but the plan had to be rebased.
- **Hardware is the bottleneck.** Every merged change still waits for a physical pad check, so the pilot cannot finish without the owner and the device.

### Claude Code (KAREN OS session)

- Moved a design image in a tidy-up commit without checking active plans' drift checks, which tripped plan 008's.
- Wrote a temporary file to `/tmp` against the session rule to use the job directory, and deleted it afterwards.
- A path-replacement script mangled a note in plan 008, which had to be rewritten.
- Claimed a stray `true` file existed when it was command output, then corrected itself.
- Pinned CI to Python 3.9, which current GitHub runners no longer provide. CI failed once.
- Ticked "CI passes" in a pull request description before CI had finished.

### Codex (plan 009)

- Read the execution contract, SOPs, specification, skills list and templates for a small bug fix. That cost tokens without improving the result.
- Took over the owner's desktop to drive Chrome, and the file picker automation still failed.
- Added a `checks/` folder the plan did not list. It turned out useful and CI now runs it, but it was unplanned scope.

### Macropad session (plan 008)

- Its "separate review" was a self-review. It said so honestly, but the plan intended a second reviewer.
- A commit titled "record pad checks" only recorded the checklist, not results. Both slice commits had empty message bodies.
- Its documents were thorough but dense and long, which costs tokens and owner reading time.
- It did not measure elapsed time, although the plan asked for coordination data.

## Lessons and proposed follow-ups

None of these are applied yet. Each would be its own issue and pull request.

1. **For plan-sized work, the startup core and the plan are enough.** Say so in the standard or SOPs, so agents stop loading detailed documents by default.
2. **Drift checks should use the last approved baseline** and list expected paths, not a fixed old commit.
3. **Agents record their own timings** in the pull request: start and end of work, and owner interventions.
4. **Commit and pull request titles must not claim results they do not contain**, such as "pad checks" when only the checklist exists.
5. **A real second reviewer for medium-risk work.** A different session or provider reviews the diff before the owner, rather than the author reviewing itself.
6. **Documents for the owner are short first.** Lead with a summary and decisions, and put detail below.
7. **Agents check active plans before moving or deleting files** in a project.
8. **Exercise the untested paths natively:** a stale pin, an unreachable KAREN OS core, a project rule that tries to weaken the shared rules, and a cloud agent cloning KAREN OS from GitHub to complete an issue.

## Still open

- Pad checks: Macropad issues #3 (slice 1), #4 (plan 009) and #5 (plans 003 to 006).
- The first cloud-agent run of the pipeline.
- Whether the lessons above become changes to the standard, the SOPs or the project template.
