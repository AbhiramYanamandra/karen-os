# Pilot log: LookAtMe design-to-PR

The second engineering pilot of KAREN OS ([#48](https://github.com/AbhiramYanamandra/karen-os/issues/48)), run on 24 November 2026 in the LookAtMe portfolio repository. One real feature went from issue to spec, then to an editable Figma design, exact owner approval, Ponytail-guided implementation, tests, review and a PR with CI. Two supporting changes went alongside it: repinning the project to the current core, and a typography check.

**Status: waiting for the owner.** All three LookAtMe PRs are open, pass CI and are marked ready. None is merged. PR #9 has an open decision about a rendering test.

| Change | Issue | PR | Profile |
|---|---|---|---|
| Repin to `engineering-7` and sync the PR template | LookAtMe #4 | LookAtMe #7 | chore, low |
| Fail the check on any font outside the font tokens | LookAtMe #5 | LookAtMe #8 | testing, low |
| Optional Outcome fact in Quick facts (the feature) | LookAtMe #6 | LookAtMe #9 | ui, medium, `substantial_ui` |

## What was measured and how

- **Timings** come from `pipeline.py` claim stamps and GitHub PR timestamps (UTC). The agent did not time itself.
- **Owner interventions** are counted from the session transcript.
- **Token and context load** is only partly measured. The three reviewer subagents report their own token counts. The main session's use was not metered. It ran in a session that had already been summarised once, after the #47 work.
- **Quality** means what the reviewers and the profile resolver found, not self-reported results.

## Timeline

| When (UTC) | What |
|---|---|
| 09:26 | #48 claimed. LookAtMe startup read reported `stale`: it pinned `engineering-1`, while the current core is `engineering-7`. The owner was told before any action, as LookAtMe's `AGENTS.md` requires. |
| 09:26 to 09:35 | Core changes from `engineering-2` to `engineering-7` reviewed for their effect on LookAtMe. The pin was moved and the PR template synced. Startup read then reported `ok`. PR #7 opened. |
| 09:39 to 09:40 | #5 claimed, test written and shown to fail on a deliberate wrong font. PR #8 opened. |
| 09:41 to 09:44 | Figma revision 1 built in a new file: current block, proposed desktop (450px) and proposed phone (335px, with a 138-character outcome). One clipping defect was found by screenshot and fixed. |
| After 09:44 | The owner replied "Approve revision 1". |
| 09:45 to 09:49 | #6 claimed after the approval. Implemented and checked in the browser at 1280 and 375px. PR #9 opened. |
| 09:49 to 09:54 | Profile resolver run by hand. Three fresh-context reviews (Standards, Spec, correctness and accessibility) ran. Review fixes landed in `9543650` and the PR profile was corrected. |

From claim to three ready PRs took about 23 minutes. Another 6 minutes went on review and fixes. The owner's own time is not included.

## Results against the acceptance criteria

| Criterion | Result |
|---|---|
| Correct company and project policy load, skill versions and gaps | **Met.** Startup read showed `stale` before the repin and `ok` after. Installed tree hashes matched the registry for `ponytail-plugin`, `principle-prove-it-works`, `code-review` and `ui-ux-pro-max@shared-agents-skills`. **Gaps:** `figma` is a remote connector with no hash. The `testing` profile recommends `tdd`, which wasn't used; that is disclosed in PR #8. |
| Owner approval bound to the reviewed design revision, no UI code before it | **Met, with a weak binding.** No #6 code existed before the approval. Figma's plugin API could not save a named version (`saveVersionHistoryAsync` is not supported). So the approval is pinned to the file, section node `1:110` and date, not to an immutable version. |
| Deliberate wrong typography and missing-stage checks caught or flagged | **Met.** Setting `home.css:85` to `"Times New Roman", serif` failed the new test with `src/styles/home.css:85: "Times New Roman", serif`. Removing `figma` from a copy of the registry made `profiles.py resolve --type ui --flag substantial_ui` report `design: hold ["figma"]`. |
| Behavioural, accessibility and visual tests, shortcomings, independently reviewed evidence | **Partly met.** Validation tests: 78 pass. The browser check gave measurements at both widths, and a project without an outcome stays unchanged. **Shortcomings:** there is no QuickFacts render test, because LookAtMe tests run plain `node --test` with no JSX transform; that is an owner decision on PR #9. The PR has no screenshots, and keyboard and reduced-motion were not tested separately. Reviews came from subagents of the implementing session, not an independent top-level session. |
| Elapsed time, token and context load, interventions, quality versus the current pipeline | **Met, except that main-session tokens were not metered.** See the next section. |
| No default-branch writes, deployment, publishing or merge by an agent | **Met.** All work is on issue branches through PRs. Vercel preview builds ran automatically from the PRs; that is the repository's own setup, not an agent deployment. |

## Measurements

| Item | Value |
|---|---|
| Elapsed, claim to three ready PRs | About 23 min |
| Elapsed, review and fixes | About 6 min |
| Size | PR #7: +13 −9. PR #8: +62. PR #9: two commits, about +56 −10 across 6 files. |
| CI | Green on all three PRs, including after the review fixes |
| Reviewer load | About 96k, 98k and 102k tokens for the three reviewer subagents |
| Owner interventions | 4. (1) Picked the feature. (2) Picked again after the agent's first recommendation turned out to exist already as Quick facts. (3) Marked three issues ready. (4) Approved design revision 1. Merges are still to come. |

**Compared with the Macropad pilot:**
- Every change had its own issue, branch and PR with a profile, and CI passed before each was marked ready. In the Macropad pilot, one PR merged 14 seconds after opening, with an empty body.
- The design gate held: no UI code was written before approval.
- The new weakness is that a connected project's CI does not check PR profiles, so profile mistakes surface only when someone runs the resolver.

## What went wrong

1. **Wrong feature recommendation.** The agent proposed a "case-study summary panel", which already exists as `QuickFacts`, so the owner had to choose twice. Cause: it recommended before reading the component tree.
2. **Profile mistakes that CI did not catch.**
   - PR #8 declared type `test`, but `test/` branches require `testing`.
   - PR #9 declared `low` risk, but the resolver raises `ui` + `substantial_ui` to `medium`, which requires `code-review`. The agent didn't run `profiles.py resolve` before opening the PR.

   Both were found by running the resolver by hand and fixed in the PR bodies. LookAtMe's CI runs `npm run check` only.

   Running `check_pr.py` locally against the LookAtMe bodies found three more:
   - PRs #8 and #9 used `exceptions` for disclosed gaps, but that field holds only owner waivers of required skills.
   - PR #9 gave `figma` an empty hash where the registry has `null`.
   - PR #9's Figma approval fails the design gate, as item 3 below explains.

   The first two are fixed. The design gate is expected to fail until follow-up 2.
3. **The design approval can't name an immutable revision.** `check_pr.py` accepts only a merged design PR for `design_approval`, and the Figma API can't save a version. The approval is recorded as text in the PR profile.
4. **No rendering test.** The issue asked for tests "for validation and rendering". Only validation is tested.
5. **`check_pr.py` crashes on a string exception.** A plain string in `exceptions` raises `AttributeError` in `profiles.resolve` instead of producing a problem message.
6. **The first validation was looser than intended.** Reviewers found that a bare `\r` passed the one-line check, that length was counted in UTF-16 units, and that a date gave a misleading message. All were fixed in `9543650`.

## Proposed follow-ups

1. Make `pipeline.py pr` run `profiles.py resolve` with the declared type, risk and flags, and refuse when the PR profile's risk or required skills fall short. This would have caught both profile mistakes.
2. Define a design-approval format for Figma: file key, node, version ID where the owner saved one, and the owner's quoted reply. Accept it in `check_pr.py` alongside a merged design PR.
3. Decide whether reviewer subagents spawned by the implementing session count as "a different session" for medium-risk review, and write the answer into the engineering standard.
4. Add to the design SOP: read the existing components before recommending a feature.
5. Make `check_pr.py` and `profiles.resolve` report a malformed `exceptions` entry instead of crashing.
6. LookAtMe: choose a way to render-test components (for example an existing transform, or a check against the built HTML) before the next UI issue.

None is filed as an issue yet. Each needs the owner's choice.
