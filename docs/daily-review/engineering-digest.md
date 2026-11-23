# Engineering digest

Issue #24, part of epic #17. `scripts/daily_digest.py` collects engineering facts from GitHub for the morning and evening reviews. It is a script, not AI: it uses no model and costs no usage. An assistant reads its output instead of crawling GitHub.

## Run it

```bash
python3 -B scripts/daily_digest.py
```

| Option | Effect |
|---|---|
| `--repo owner/name` | Repositories to read; repeat for several. Without it, the script uses `repositories` from `~/.config/karen-os/daily-review.json`, falling back to `context/board.json`. |
| `--since 2026-03-13T07:00:00Z` | Report what was merged or closed since this time, instead of since the last run |
| `--top 5` | How many `status:ready` issues to list per repository |
| `--json` | JSON instead of Markdown, for an assistant or a later Notion writer |
| `--output FILE` | Write to a file instead of stdout |
| `--no-state` | Don't read or update the saved last-run time |

**Exit codes:** 0 means everything was read. 2 means the digest was produced but some sources were unavailable; they are listed at the top.

## What it reports

Sections, in the order the owner acts on them:

1. **Waiting for you:** open, non-draft PRs. Agents never merge, so every ready PR waits for the owner. Each shows CI passing, failing or running, and whether changes were requested.
2. **Needs you:** issues labelled `status:needs-owner`.
3. **Blocked:** issues labelled `status:blocked`.
4. **Failing CI on default branches:** workflows whose latest completed run on the default branch failed.
5. **Ready to start:** the top `status:ready` issues per repository, by priority (`P0` first) then age.
6. **In progress:** claimed issues.
7. **Done since last digest:** PRs merged and issues closed since the previous run (24 hours on the first run).

Every item links to GitHub, and the header gives the observed-at time. GitHub stays the record; the digest is a snapshot.

## Unavailable, never guessed

If a source can't be read (no access, network down, `gh` signed out), the digest lists it under **Unavailable** at the top, with the error, and leaves that section incomplete rather than empty-by-assumption. The saved last-run time advances only for repositories that were read completely, so a failed run never hides changes from the next one.

## Read-only

The script runs only `gh pr list`, `gh issue list`, `gh run list` and `gh repo view`. Its runner refuses any other command, and the tests check that. It needs no token beyond the owner's existing `gh` sign-in, and nothing goes to the repository.

Local files, both outside the repository:

- `~/.config/karen-os/daily-review.json`: optional, the repository list.
- `~/.local/state/karen-os/digest-state.json`: the last observed time per repository.

## Not yet

- **Writing to Notion.** The Engineering digest database is defined in `docs/daily-review/notion-workspace.md` (#23). The writer waits until the owner has built the workspace and confirmed the free-plan API checks there. It is filed as #35.
- **Running on a schedule.** A `launchd` job comes after manual runs have shown the digest is useful, per the architecture review on #24.
