# Engineering standard

Applies to every code or documentation change in KAREN OS and in connected projects. Project instructions may make it stricter, never looser. Reference: the [Microsoft Code-With Engineering Playbook](https://microsoft.github.io/code-with-engineering-playbook/), adapted for one owner working with agents.

## The pipeline

GitHub holds the queue, the review and the history. The work happens in a local checkout or a cloud agent session.

`scripts/pipeline.py` does the routine steps, one shell call each, so agents spend effort on the work rather than the paperwork. Run it from the project's checkout (other projects call it from the KAREN OS checkout): `claim <issue>` (step 3 and 4), `pr <issue>` (step 6, opens the draft; add `--refs` for design gates), `ready <pr>` (waits for CI, records the times, marks the PR ready and moves the issue to `status:in-review`), and `cleanup` (step 8). Pass `--agent` and `--machine` to `claim` without personal details such as the hostname. Each step also moves the item's card on the board, one way from label to card; `sync` adds missing items from the repositories listed in `context/board.json` and corrects any card whose Status disagrees with its label. The script refuses merges, approvals, closing issues, pushes to the default branch and settings changes. Do a step by hand only when the script cannot run, and keep the same order.

1. **Issue.** Every piece of work is a GitHub issue in the project's repository, written with the task template: outcome, why, scope, out of scope, acceptance criteria, and a link to any detailed plan. The issue is the task record. Only issues labelled `status:ready` may be started. An agent that files an issue labels it `status:needs-owner`. When the owner asks an agent directly for work that has no issue, the agent files the issue first and stops; it starts only after the owner marks it `status:ready`. Work the owner dispatches through the daily review (epic #17) starts from a `status:ready` issue the same way. A GitHub Projects board (such as [Engineering HQ](../architecture/github-projects.md)) only shows and plans issues: moving a card or changing its Status never authorises work, and when a card and its issue's label disagree, the label wins. Whoever changes an issue's `status:*` label also moves its card.
2. **Pick.** Work on the issue the owner names. Otherwise take the open `status:ready` issue with the highest priority (`P0` first), then the oldest. Skip `status:blocked`, `status:needs-owner` and anything already claimed.
3. **Claim.** Replace `status:ready` with `status:in-progress` and comment with the agent, the session or machine, and the branch name. One worker per issue. Check for an existing claim before starting.
4. **Branch.** From the current default branch, create `<type>/<issue>-<short-description>`.
5. **Work.** Run the KAREN OS startup check and follow [Context retrieval](policy.md#context-retrieval) for the issue, linked plan and any additional reads. Follow the [plan baseline guidance](#plans), drift checks and STOP conditions. Before moving, renaming or deleting files, check whether any open issue or plan's scope or drift check covers them. Reconcile affected references and any required approvals before the change. Commit in small, logical steps.
6. **Pull request.** Push the branch and open a PR using the template, with `Closes #<issue>`. Open it as a draft until CI passes and the self-check is done, then mark it ready and move the issue to `status:in-review`.
7. **Review and merge.** The owner reviews, tests and merges. Merging is the code approval and closes the issue. Agents never merge.
8. **After merge.** GitHub deletes the branch automatically. The agent runs `git fetch --prune` and deletes its local copy of the branch. File deferred or follow-up work as new issues.

If a STOP condition or owner decision blocks the work, comment on the issue with what is needed, set `status:blocked` or `status:needs-owner`, and push what is safe as a draft PR.

## Standing authority

Owner grant, 23 November 2026. In KAREN OS and in projects whose `.karen/project.json` declares a `pipeline`, agents may:

- create and push branches other than the default branch;
- open and update pull requests, including drafts;
- create issues (`status:needs-owner` unless the owner asked for them), comment on issues and PRs, and apply the project's labels to the issue they are working on.

Agents may not, without a separate owner instruction:

- push or force-push the default branch, force-push a branch they did not create, merge or approve a PR;
- close, delete or transfer issues or PRs, except through a merged `Closes` link;
- create tags or releases, deploy, or write to hardware;
- change repository settings, rulesets, secrets, collaborators, visibility or Actions permissions;
- spend money or start paid services.

A PR that changes CI workflows says so in its summary. Public repositories make issues, PRs and branches public: never include personal records, credentials, home-directory paths or private details.

## Branches

`<type>/<issue>-<short-description>`, lowercase and kebab-case, one purpose per branch.

| Type | Use |
|---|---|
| `feat` | New behaviour |
| `fix` | Bug fix |
| `hotfix` | Urgent fix to released behaviour |
| `refactor` | Restructure without changing behaviour |
| `docs` | Documentation only |
| `test` | Tests only |
| `chore` | Maintenance, dependencies, tooling |
| `ci` | Pipeline and workflow changes |
| `release` | Release preparation |

Example: `fix/12-combo-layer-cycle`. Where a project already has a different convention, follow it.

## Commits

Conventional Commits: `type(scope): summary`, imperative, 72 characters or fewer. The body explains why and notes risk. The footer has `Refs #<issue>`. Each commit builds. Never commit secrets, build products or personal data.

## Pull requests

One issue per PR. Split large plans into slices, each with its own issue and PR. Prefer PRs under about 400 changed lines, excluding generated files and assets, and explain larger ones. The PR body has:

- **Summary** of what changed.
- **Why**, with `Closes #<issue>` and the plan or design link.
- **How to test**, as steps the owner can follow, including device or manual checks.
- **Evidence**: commands run and their results.
- **Not verified**: anything unproven, such as a hardware check.
- **Risk and rollback.**

Link long records rather than pasting them. Any review the agent did itself is labelled a self-review.

The PR template has no checkboxes for the agent to tick. CI's **PR metadata** job (`scripts/check_pr.py`) checks what a machine can: the branch name, a `Closes #<issue>` or `Refs #<issue>` link, and that the diff adds no home-directory paths or common secret patterns. A line that must show such an example carries `pr-check: allow`. Judgement items (docs updated, follow-ups filed, self-review labelled) are prompts in the template, answered only where they apply.

Every PR also carries a `karen-profile` block under `## Profile`, which `scripts/pipeline.py pr` pre-fills from the workflow profiles (`scripts/profiles.py`). The agent sets the real risk and flags, and lists each required skill with its registry hash, runtime and load evidence, the second reviewer for medium or high risk, the tests run, and how many times the owner stepped in. The same job fails the PR when the block is missing, the type doesn't fit the branch, the diff needs an undeclared flag (`ci_change`, `pinned_policy`, `new_dependency`), a required skill is missing or at the wrong hash, a design gate lacks a merged design PR, or medium or high risk has only a self-review. Evidence and reviewer independence are claims CI can see but not prove; the second reviewer and the owner judge them ([proposal](../proposals/pr-enforcement.md)). The PR metadata job blocks merge only if the repository ruleset requires it.

## Continuous integration

Every project has a GitHub Actions workflow on `pull_request` and on pushes to the default branch. It runs the build, the tests, any linters, and project checks. Use read-only permissions by default, pin actions to a major version, and need no secrets for PR checks. Failing CI blocks review. Fix the cause, and never disable or skip a check to make it pass.

## Repository setup

Every project's GitHub repository has these before agents work in it. Settings changes are owner actions; an agent may apply them only when the owner asks.

1. **Labels** from `docs/templates/github/labels.json`.
2. **Templates** in `.github/`: the pull request template and the Task issue form from `docs/templates/github/`.
3. **CI workflow** that runs the project's checks, as described above.
4. **Ruleset on the default branch:** require a pull request, require the CI checks to pass, and block force pushes and deletion. It requires no approving review, because agents act through the owner's account and GitHub does not let an author approve their own PR. The owner's merge is the approval.
5. **Automatically delete head branches** turned on, so merged branches disappear from GitHub without manual cleanup.
6. **Project record** in `.karen/project.json` declaring the `pipeline` and `karen_os_repository`.

## Definition of done

- The issue's acceptance criteria are met.
- CI passes.
- The PR body is complete, including How to test and Not verified.
- Docs are updated where behaviour, formats or setup changed.
- Plan status and issue labels are current.
- Deferred work is filed as issues.

## Delivery

Merging to the default branch integrates the work. Releases are owner decisions: semantic version tags with notes from the merged PRs. Agents never deploy to hardware or production. Preview deployments are allowed only where the project declares them.

## Labels

Every project uses the set in `docs/templates/github/labels.json`: priorities `P0` to `P3`, `type:*` matching the branch types, `status:ready`, `status:in-progress`, `status:in-review`, `status:blocked`, `status:needs-owner`, and `hardware-check` for work that needs a physical test.

## Plans

A large piece of work may keep a detailed plan file in the repository. The issue links to it and stays the tracking record for priority, status and discussion.

A plan's drift check uses its **last approved baseline**, with the exact commit SHA, plan revision, approval reference and expected paths recorded together. The task's starting commit and the latest `main` are not substitutes for that baseline. Compare current changes with the recorded baseline, including both paths of a rename and untracked files. Reconcile unexpected changes under the plan's STOP conditions. Update the baseline only after the owner accepts the affected plan revision, retaining the prior baseline and its approval in history.

For example, approved plan revision 2 records `<approved-sha>` and expects changes to `src/widget.py` and `tests/test_widget.py`. Run:

```sh
git diff --name-status <approved-sha> --
git status --short
```

If the output also shows `docs/archive.png` moved, check the open issues and plans that reference it. Reconcile the move before continuing; a passing build does not resolve plan drift. If the owner accepts revision 3, record its approved baseline SHA, approval reference and expected paths instead of silently replacing `<approved-sha>` with the latest commit.

## Working from anywhere

A cloud or remote agent without the local KAREN OS checkout clones `karen_os_repository` from the project record and runs the startup check from that clone. Hardware and other owner-only checks go in the PR's How to test and Not verified sections.
