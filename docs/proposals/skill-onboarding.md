# Proposal: safe skill discovery, onboarding, updates, quarantine and revocation

Revision 1, 24 November 2026. Issue [#47](https://github.com/AbhiramYanamandra/karen-os/issues/47), epic [#43](https://github.com/AbhiramYanamandra/karen-os/issues/43), charter slice **PR D**. Status: **approved** by the owner's merge of PR #67 on 24 November 2026. The standing rule is [skill-onboarding.md](../organisation/skill-onboarding.md). Resolved profile for the implementation: **security, high risk**: threat assessment, owner-approved technical proposal, security tests, thermo-nuclear review.

## Summary

KAREN OS can already record that the owner approved, rejected or revoked an exact skill version ([skill-catalogue-audit.md](../organisation/skill-catalogue-audit.md#owner-decisions-approve-reject-revoke)). It cannot yet say how an agent finds a new skill, how it reviews one without running it, how an update is handled, or what happens when a skill looks compromised. This proposal adds those procedures and one implementation PR that makes them checkable:

- a **quarantined** state that any agent may set and only the owner may lift;
- four **separate authorisations** (install, activate, permissions, external access), each absent unless the owner grants it;
- a **static review script** that hashes a candidate package and flags scripts, install hooks, network endpoints, credential reads and prompt-injection phrases, without executing anything;
- **synthetic malicious and incompatible fixtures** that the tests prove the validator and resolver reject.

**Decisions** (owner answered "Yes, both" in a Claude Code session on 24 November 2026):

1. Any agent may quarantine a skill on its own. Only the owner may lift it.
2. Agents may run search-only discovery commands (for example `npx skills find`), which use the network but install nothing. Install and update subcommands are not allowed.
3. Still open: approve this revision by merging, or request changes.

## What exists and what is missing

| Acceptance criterion (#47) | Today | This proposal |
|---|---|---|
| Provenance and immutable version/hash required for approval | `approve` needs `approved_sha256` equal to `tree_sha256`. The source ref is free text. | Approval also needs a commit-pinned `source` ref. A branch or tag ref fails. |
| Owner authorises install, activation, permission expansion and external access separately | One `scope` field | Four explicit grant fields. A missing field means not granted. |
| Quarantine, revocation and isolated testing cover malicious instructions and dependency side effects | `revoke` exists. No quarantine, no isolation rule, no malicious tests. | `quarantined` state, isolated review procedure, static scanner, malicious fixtures. |
| No automatic trust from search ranking, installation, downloads or stars | Stated in the charter only | Procedure rule. The validator already rejects `approved` without an owner decision. |
| Missing mandatory skill holds the stage; missing optional skill allows an explained fallback | Implemented in `scripts/profiles.py` (holds and fallbacks) | Extend it: quarantined and revoked skills count as missing. |

## Threat assessment

**Assets:** the owner's machine and home folder, credentials and tokens the runtimes can reach, the owner's repositories and GitHub account, agent context (which steers every later action), and the integrity of recorded approvals.

**Trust boundaries:** (1) internet source → local disk, (2) disk → runtime skill folder, (3) skill folder → loaded into a model's context, (4) loaded skill → tools, network and files, (5) agent branch → `main` through the owner's merge.

| Attacker or failure | Abuse case | Control |
|---|---|---|
| Malicious upstream author | `SKILL.md` tells the agent to read credentials, send data out, or ignore KAREN rules | Full-package review before approval. Scanner flags credential paths, outbound endpoints and override phrases. Content is never loaded while under review. |
| Compromised repository or moved tag | Same name and ref, new content | Approval binds to `tree_sha256` and a commit SHA. Hash drift at load time means quarantine. |
| Dependency side effects | `package.json` postinstall, `setup.py` or a bundled script runs on install | Review happens in a quarantine folder with no install step. Scanner flags install hooks and executables. Install is its own owner grant. |
| Typosquat or duplicate name | A lookalike name, or two files resolving to one name | Resolution check (audit protocol step 1). Approval names the exact source and location. |
| Ranking or popularity manipulation | Top search result or many stars treated as vetted | Trust signals are never evidence. Only the review record and an owner decision change state. |
| Agent self-approval | An agent writes a schema-valid `owner_decision` | Procedural today: the owner's diff review and merge ([audit](../organisation/skill-catalogue-audit.md#what-a-recorded-decision-proves)). Quarantine lowers trust, so an agent may set it. Lifting it raises trust, so only the owner may. |
| Skill expands its own authority | Instructions to install more skills, edit settings or hooks | Permission and external-access grants are explicit. The scanner flags settings, hook and install edits. A skill never grants itself anything. |

## Lifecycle

```text
discovered → under-review → approved ──→ revoked
                 │   │          │
                 │   └→ rejected│
                 └──────→ quarantined ←┘   (owner lifts → under-review)
```

Install and activation are **grants on an approval**, not states. An approved skill may be uninstalled, or installed but not activated for any profile.

## Procedures

1. **Discover.** Start when `profiles.py` reports a hold, or when the task needs a capability no approved skill covers. Search trusted docs first, then candidate sources, using search-only commands. Add an entry with `state: discovered`, the source URL and a commit SHA. Ranking, stars, download counts and "already installed" are not evidence and are not recorded as such.
2. **Review in isolation.** Fetch the package at that commit into a quarantine folder under the session scratchpad, never into a runtime skill folder. Do not install, build or run anything from it. Run `scripts/skill_review.py <folder>` for the tree hash and flags. Read every file, including scripts and dependency manifests. Record licence, dependencies, tools, privileges, endpoints, duplicates, flags and a recommendation. Set `under-review`.
3. **Owner decision.** The owner approves (content plus grants), rejects, or holds. Approval records each grant separately:
   - `install`: runtime(s) and destination location
   - `activate`: profiles and stages that may require or recommend it
   - `permissions`: tools, scripts, write access
   - `external_access`: network endpoints and credentials

   Anything not listed is not granted. Registry promotion follows only from an approval with `activate`.
4. **Test in isolation.** Before activation, load it in a throwaway session with no credentials and network access only as granted. Run the audit's behaviour canary or a task-specific check. Record the result in the entry.
5. **Update.** A new upstream version is a new review of the new commit. Diff it against the approved tree. The old approval stays in force for the old hash until the owner approves the new one. Never run `npx skills update` on a skill whose lock entry has no pinned ref.
6. **Quarantine.** Any agent sets `quarantined` with `reason`, `observed_sha256` and evidence when the hash at load differs from the approval, review finds a hidden behaviour, upstream reports a compromise, or a load caused an unexpected side effect. The resolver then treats it as missing, so mandatory stages hold. Nothing is uninstalled automatically. Only an owner decision lifts it, back to `under-review`.
7. **Revoke.** As today: the owner cites the approval and hash. The registry drops the entry and the resolver treats the skill as missing. Local removal is a separate owner action on their own machine.

## Implementation (next PR, after this merges)

Branch `feat/47-skill-onboarding`, about 300 changed lines:

- `docs/organisation/skill-candidates.json`: add `quarantined` to `states`, a `quarantine` record schema, and the four grant fields to the `approve` schema. Existing approvals get a reviewed migration (explicit grants matching what was already allowed), shown in the PR for the owner to confirm.
- `scripts/skill_review.py` (standard library only): tree hash using the catalogue `hash_method`, plus flags for executables, install hooks, URLs, credential paths, settings or hook edits and override phrases. Read-only, no network. It reports and never decides.
- `scripts/profiles.py`: quarantined and revoked skills count as missing.
- `tests/fixtures/skills/`: inert synthetic packages (exfiltration instruction, postinstall hook, outbound URL, hash drift, duplicate name, incompatible runtime). Tests show the scanner flags each one, the validator rejects approval without grants or with an unpinned ref, an agent-lifted quarantine fails, and the resolver holds.
- `docs/organisation/skill-onboarding.md`: the procedures above as the standing rule, linked from the audit and pinned in the manifest.

## Limits

- The scanner finds patterns, not intent. A clean scan is not approval, and a careful attacker can evade it. Human or independent review stays mandatory.
- Recorded decisions remain procedural until signed commits or a separate agent identity exist ([audit options](../organisation/skill-catalogue-audit.md#what-a-recorded-decision-proves)).
- Whether a model follows a skill's prose still cannot be proved mechanically.
- Isolated testing depends on the runtime honouring a credential-free session. That needs its own runtime check.

## Out of scope

Automatic install or update, paid services, signed-commit enforcement, removing rejected skills from the owner's machine, and the fresh-session load verification left over from #51.
