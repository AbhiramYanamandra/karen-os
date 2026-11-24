# Proposal: stage-aware workflow profiles

Revision 1, 24 November 2026. Issue [#45](https://github.com/AbhiramYanamandra/karen-os/issues/45), epic [#43](https://github.com/AbhiramYanamandra/karen-os/issues/43), charter slice **PR B**. Status: **awaiting owner approval** (merging this PR approves this revision). Change type: policy and tooling design. No code or policy changes in this PR.

## Summary

Every KAREN-managed task gets a **profile** chosen from its issue type, risk and a few flags. The profile says, for each lifecycle stage, which gates apply and which skills are **required**, **recommended** or **optional**. A small local script resolves the profile deterministically, so agents don't decide for themselves whether a mandatory step applies, and you don't have to repeat skill names in every issue.

Seven profiles: **feature, ui, bug, chore, docs, security, testing.**

What never changes, in every profile: issue with `status:ready` → claim → branch → PR → CI → **owner merge**, with KAREN core startup loaded. Profiles only vary what happens between claim and PR.

## Risk levels

Risk follows the intake SOP: impact, not line count.

| Level | Meaning | Review before owner |
|---|---|---|
| **low** | Reversible, known behaviour. No meaningful UX, security, permission, data or spending change | Self-review, labelled as such |
| **medium** | Behaviour users notice, shared code, CI workflows, hash-pinned policy, or any design-required change without security impact | **A different session or provider** reviews, using `code-review`. Its findings and identity go in the PR |
| **high** | Security, authentication, permissions, sensitive data, spending, destructive data changes, publication, or new third-party code | Separate review with `code-review`, plus `thermo-nuclear-code-quality-review`, plus `ecc:security-review` (checklist) when security-relevant |

How to request the second review (from #13): open the PR as a draft, start a fresh Claude Code or Codex session, load `code-review` on the PR with the issue as its spec, and paste its findings and session or provider into the PR's reviewer notes. The worker fixes the findings before marking the PR ready.

## The seven profiles

Stages: **spec → design → implement → verify → review**. R = required, Rec = recommended, — = not applicable. Every required skill must be approved in the catalogue and registered. Short names map to catalogue ids: `ponytail` is `ponytail-plugin`, and `ui-ux-pro-max` is `ui-ux-pro-max@shared-agents-skills`.

| Profile | Risk floor | Spec | Design gate | Implement | Verify | Review |
|---|---|---|---|---|---|---|
| **feature** | low | Acceptance criteria in an issue comment; a proposal if design-required | **Technical proposal, owner-approved revision**, when design-required (new architecture, data flow, service or integration) | R `ponytail` · Rec `tdd` | R `principle-prove-it-works` · tests for new logic | By risk |
| **ui** | low; **medium** if substantial | Current UI, untouched behaviour, measurable criteria | Substantial UI: R `ui-ux-pro-max` + R `figma`, **editable revision with device variants and states, owner-approved**. Existing-pattern tweak: none | R `ponytail` | R `principle-prove-it-works` · project style, accessibility and visual checks | By risk |
| **bug** | low | **Reproduction first**: a failing signal before hypotheses | — (a fix that needs redesign switches to feature or ui) | Rec `diagnosing-bugs` (R when the cause is unknown) · Rec `tdd` · R `ponytail` (root cause, fixed once) | R `principle-prove-it-works` · **regression test**, or a written reason it's impractical | By risk |
| **chore** | low; **medium** for CI workflows | One-line intent | — | R `ponytail` when code changes | R `principle-prove-it-works` · build and tests pass | By risk; a new dependency is **high** and needs install approval |
| **docs** | low; **medium** for hash-pinned policy | — | — | — | R `principle-prove-it-works` (links, commands and claims checked against the real artefact) | By risk; pinned-policy changes need a reviewed repin |
| **security** | **high** (always) | Threat assessment: assets, boundaries, attacker, abuse cases | **Technical proposal with data flow and threat boundaries, owner-approved** | R `ponytail` | R `principle-prove-it-works` · R `ecc:security-review` (checklist) · security tests | Separate review + R `thermo-nuclear-code-quality-review`. No external scans without approval |
| **testing** | low | What behaviour the tests pin down | — | Rec `tdd` | R `principle-prove-it-works` · tests fail without the behaviour they cover. **Never weaken or skip a check to pass** | By risk |

**Publication text** (for example LinkedIn) is a flag on any profile, not a profile: R `unslop` before the owner's exact-text approval. Posting stays under the existing exact-text approval, and a merge never authorises posting.

## Resolution rules

The resolver takes the issue's **type**, a declared **risk** and **flags** (`substantial_ui`, `design_required`, `security_sensitive`, `ci_change`, `pinned_policy`, `new_dependency`, `unknown_cause`, `public_text`), plus the project's own profile file if it has one.

1. **Mixed tasks take the union.** Every profile the type and flags trigger applies. A UI change that also touches authentication gets the ui gates and the security gates.
2. **Strictest wins.** Required beats recommended beats optional. Risk is the highest of the declared risk and every triggered floor. A design gate applies if any triggered profile has one.
3. **Duplicates collapse.** A skill named twice resolves once, at its strictest level. One skill per purpose: the profile names which.
4. **Missing required skill holds that stage**, not the whole task. Missing means not approved, not registered, or not resolving to its approved hash. The resolver reports it, and the agent continues with stages that don't depend on it.
5. **Missing recommended skill** permits an explained fallback, disclosed in the PR.
6. **Projects can tighten, never loosen.** A project profile may add skills, raise floors or add gates. A project rule that drops a company requirement is a **conflict**: the resolver fails and the work holds for an owner decision.
7. **Exceptions are owner-only.** An exception names the requirement, the scope, and a durable owner reference (an issue comment or PR). Without a reference the resolver ignores it.
8. **Load only what the stage needs.** The resolver lists skills per stage. Agents load a skill's body at its stage, not the whole library at startup. Nothing runs centrally.

## Files (next PR, after approval)

- `docs/organisation/workflow-profiles.json`: the seven profiles, risk levels and flags, as data.
- `scripts/profiles.py`: standard library only. `python3 -B scripts/profiles.py resolve --type ui --risk medium --flag security_sensitive` prints the stages, gates, skills and holds as JSON.
- `tests/test_profiles.py`: every profile, plus the edge cases in #45: a high-risk mixed case, duplicates, a missing required skill, a missing recommended skill, an exception with and without a reference, and a project conflict.

Out of scope here: PR checks and CI enforcement (#46), discovery of new skills (#47), and the LookAtMe pilot (#48).

## Decisions this revision makes

Merging approves these. Say if any should change.

1. **Activation reads the registry.** Required skills count as available only when they're in `skills.json`, the hash-pinned registry, which is still empty. Until #51 promotes the approved entries, the resolver correctly reports holds, so the profiles exist but aren't live. The alternative is reading the catalogue's `approved` state directly, which goes live sooner but skips the reviewed repin.
2. **Risk is declared by the agent at claim, then checked.** The resolver raises it to the floors and flags, never lowers it. The owner can override in the issue.
3. **Publication text is a flag, not an eighth profile.**
4. **`ponytail` is required for code in feature, ui, bug, chore and security**, per the charter's coding-stage rule.

## Rollback

Revert the PR. Nothing depends on the profiles until #46 wires them into PR checks.

## Not decided here

- How CI checks the PR against the resolved profile, and what counts as load evidence (#46).
- Which profile files individual projects such as LookAtMe need (#48).
