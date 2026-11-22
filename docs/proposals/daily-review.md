# Proposal: daily review

Revision 2, 23 November 2026. Issue #17. Status: **awaiting owner approval**. Change type: backend (specification section 11).

Revision 1, a GitHub-only Python command, was replaced after owner feedback on PR #20. The owner wants the review in chat with an assistant, covering GitHub, calendar, email, workouts, meals and sleep, with a top 3 for the day, every morning and evening. Muse (Meta AI) is the first assistant. Any other assistant must be able to take over without a redesign.

## Summary

The product is a **model-agnostic review spec**, not a program and not a Muse integration. A short public spec defines what the review checks, how it ranks the top 3, what the morning and evening outputs look like, and the rules every assistant must follow. A prompt template turns the spec into instructions any chat assistant can follow. Each assistant is an **adapter**: whichever one can read the owner's sources is given the prompt. Changing assistants means pasting the same prompt somewhere else. Nothing else changes.

KAREN OS keeps the parts that must not depend on any one assistant: the spec, the prompt template, a stdlib checker that tells whether an assistant's output meets the spec, and, only if a trial shows it is needed, a deterministic GitHub collector.

## Decisions needed

Approving the proposal as written accepts all of the recommendations.

| # | Decision | Recommendation | Alternative |
|---|---|---|---|
| R1 | What the product is | The spec plus prompt template; assistants are replaceable adapters. Already the owner's direction (model agnostic). | A Muse-specific integration. Faster, but it ties the review to one vendor. |
| R2 | Top-3 ranking | 1. Hard commitments due today or tomorrow. 2. Things blocking other people or agents (PRs waiting for the owner, `status:needs-owner`). 3. Health basics not yet done (workout planned, sleep debt). 4. Highest-priority `status:ready` work that fits a free block. Ties go to whatever fits the next free block. | Let each assistant rank freely. Less consistent, and harder to check. |
| R3 | Workouts, meals and sleep | Read them from a connected source when the assistant has one (for example a workout log). Otherwise the evening review asks one short question ("sleep last night? meals today?"), and the next morning uses the answer. Never inferred. | Require a connected source for each, and leave them out until one exists. |
| R4 | Sensitive data | Email, calendar and health data reach an assistant only after the owner consents to that assistant, recorded in the private instance (`docs/PUBLIC_PRIVATE.md`). Muse already has the owner's calendar and email. Health data and private repositories need a separate yes. | A single blanket consent. Policy does not allow it. |
| R5 | Deterministic GitHub collector | Not built now. Built only if the trial shows the assistant's GitHub connector cannot see labels, drafts or CI. Revision 1's design (commit `54fb7c5` on this branch) is the reference if it is needed. | Build it now anyway. Wasted if the connector is enough. |
| R6 | Timing | The owner asks for each review, morning and evening. Scheduled delivery stays decision D06. | Use an assistant's own scheduler. It is fine as an adapter detail, but the spec does not depend on one. |

## The spec (what implementation writes)

Location: `docs/daily-review/spec.md` and `docs/daily-review/prompt-template.md`. Generic, with synthetic examples only.

**Sources**, each one optional and named in the output:

| Source | Items |
|---|---|
| GitHub | PRs merged since the last review; open non-draft PRs; issues labelled `status:needs-owner` or `status:blocked`; `status:ready` issues, `P0` first; failing CI on default branches |
| Calendar | Today's commitments with times; free blocks of 90 minutes or more |
| Email | Messages needing a reply or action: sender, one line, why |
| Workouts | Planned or done today; last session |
| Meals | Logged or reported today |
| Sleep | Last night, from a source or self-reported |

**Morning output:** Today, Needs me, Ready for agents, Health, then Top 3 for today, each item placed in a free block with a one-line reason. Under 200 words.

**Evening output:** Done today, Slipped from the morning top 3 and why, Health check-in (asks only for what no source supplied), Tomorrow's first commitment, Proposed top 3 for tomorrow. Under 200 words.

**Rules for every assistant:**

1. Start by stating which sources it could read this time. Any source it could not read is shown as `unavailable`, never guessed or filled from memory.
2. Every item names its source.
3. Read-only: no replies, calendar changes, GitHub writes or logging on the owner's behalf unless the owner asks in that conversation.
4. No health advice beyond the facts, unless asked.
5. Follow the formats above so outputs compare from day to day and across assistants.

## Prompt template

The template has placeholders filled from the owner's private instance: `{repositories}`, `{workout_source}`, and so on. The filled-in prompt never enters the public repository. Draft for the morning:

> **Daily review, morning.** Use my {sources}. Repositories: {repositories}.
> First list which sources you could read; mark the others unavailable.
> 1. Today: commitments with times, free blocks of 90+ minutes.
> 2. Needs me: emails needing action (sender, one line, why), open non-draft PRs, issues labelled status:needs-owner or status:blocked.
> 3. Ready for agents: status:ready issues, P0 first.
> 4. Health: workout planned or done, meals so far, last night's sleep.
> 5. Top 3 for today, ranked by: commitments due today or tomorrow; what blocks others; health basics; priority work that fits a free block. Place each in a free block with one line on why.
> Name the source of every item. Never guess. Read-only. Under 200 words.

The evening template follows the evening output above.

## Conformance checker

`scripts/check_daily_review.py <output.txt>`, standard library only. It checks a pasted assistant output against the spec: the required sections are present, a source line exists, each source is either read or marked unavailable, there are exactly three top items, and it is under the word limit. It cannot check whether the facts are true. It shows whether a new assistant follows the contract, which is what makes switching assistants safe. Tests use synthetic sample outputs (passing and failing) and need no network.

## Trial before implementation is final

After approval, the owner runs the drafted prompts in Muse for three to five days and notes:

- whether it sees GitHub labels, drafts and CI (this decides R5);
- whether it ever invents items;
- which health sources it can read (this tunes R3);
- whether the formats are useful, or sections should be cut.

Findings adjust the spec before the implementation PR merges.

## Failure handling

| Failure | Result |
|---|---|
| Assistant cannot read a source | That section shows `unavailable`. The review continues. |
| No health source | Evening check-in question; nothing inferred. |
| Assistant ignores the format | The checker fails; the owner tightens the prompt or switches adapter. |
| Assistant retired or replaced | Paste the same filled prompt into the new assistant and run the checker on its first outputs. |

## Privacy and cost

- The public repo holds only the generic spec, template, checker and synthetic samples. Repository lists, health answers, outputs and consent records stay in the private instance.
- No KAREN OS code calls a model or a paid API. Cost is whatever the owner's assistant subscription already covers. Zero additional spend.
- Sending data to Meta (or any later assistant) is an owner decision per R4. Public repositories are already public. Private repositories and health data need explicit consent.

## Implementation, rollout and rollback

- One PR: the spec, prompt templates (morning and evening), checker with tests, and a README section on running the review in any assistant. Expected well under 400 lines.
- Rollback: revert that PR. Nothing runs automatically and no state is stored, so the owner just stops using the prompt.

## Out of scope

Scheduled or pushed delivery (D06), any write on the owner's behalf, a private instance store or loader (D08), health advice, and a KAREN OS chat interface. Local checkout state was dropped because the owner did not select it.
