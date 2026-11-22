# Universal agent execution contract

Public candidate procedure. Applies to Codex, Claude Code, supported ChatGPT sessions, and optional future adapters. A file contract is guidance, not a security sandbox.

| Step | Required action and completion evidence |
| --- | --- |
| 1. Identify | Confirm repository root, project ID, and exploration or execution mode. Exploration needs no task or claim; actionable work requires an explicit authorised task. Inspect Git status and preserve existing edits. Exploration needs no artificial issue. |
| 2. Load | Check the manifest and required startup sources. Record manifest revision, source hashes, missing or stale sources, and actual access. Read the complete core and current task; retrieve the pinned detailed sources when their triggers apply. |
| 3. Reconcile | Check the provisional architecture digest and applicable SOP. Identify conflicting instructions, acceptance changes, or unavailable project context. Hold dependent writes until resolved. |
| 4. Select skills | When a skill is relevant, inspect registry metadata, choose approved compatible entries, and load pinned bodies on demand. An empty registry means no project-approved skills. Platform-required skills still apply, with their origin disclosed. |
| 5. Establish authority | Convert actionable work into a scoped task record. Record owner instruction, criteria, exclusions, affected files, and proposed actions. Brainstorming or an attractive idea is not implementation approval. |
| 6. Check design | Classify impact and risk using intake and design SOPs. Obtain a version-bound visual or architecture proposal approval before substantial implementation. Record a justified fast path only for eligible low-risk authorised work. |
| 7. Admit | Check available tools, filesystem and network permissions, data destinations, spending allowance, usage freshness, ownership, and external-action uncertainty. Unknown capacity permits bounded owner-started interactive work, not unattended admission. |
| 8. Execute | Claim one task and use an isolated branch or worktree when needed. Perform only authorised scope. Preserve checkpoints. Material deviations return to design approval. |
| 9. Verify | Compare actual artefacts with criteria and approved design. Record commands or manual steps, revisions, observed results, and limits. A separate review pass is required before consequential delivery. |
| 10. Handoff | Record decisions without silently amending policy. Save completed work, checks, approvals, uncertainty, remaining work, and next safe action in canonical records. Release ownership when stopped; receiving agents revalidate before claiming. |

Follow the [SOPs](sops.md) and instantiate only needed sections of the [record templates](../templates/records.md). Private instance tasks own personal-work status; reviewed public issues own platform work only. An outgoing export is a candidate handoff until an authorised worker or owner incorporates it into project records.

## Freshness and progressive loading

`context/manifest.json` pins source bytes and declares `startup_read: complete` versus `on-demand`. For actionable work or machine validation, the current task is supplied by the invocation and captured by hash in the receipt. Read-only exploration omits the task and validation-only receipt template, uses a human-readable explanation, and grants no write authority. Formal receipts remain mandatory when the workflow requests them. All listed required files must exist; required existence does not imply mandatory whole-document reading. The [context amendment](../architecture/export-changes.md) records the owner's authorised procedural change.

The startup reader returns complete core contents with ranges and hashes in one bounded local tool result. It performs no network action or write. Receipt assessment compares actual tool-delivered content against fixture bytes, separately from the worker's source claims. This does not establish human reading, private reasoning, or every instruction-precedence case.

A receipt locates each mandatory source, labels reading as complete, partial, or none, verifies revisions separately, answers policy scenarios, and distinguishes verified read/hash tools from unverified write/network capabilities. Invalid format or missing mandatory coverage cannot PASS. Missing or conflicting policy blocks dependent writes. Detailed source selection follows the core's triggers; an execution or handoff must load applicable detailed records before acting.

Check current owner directions for revocation and actual permissions before consequential work. Offline sessions disclose snapshot age. A hash verifies consistency, not continuing approval. Review source diffs before updating pins, increment the manifest revision, and rerun checks. There is no automatic hash-acceptance command.
