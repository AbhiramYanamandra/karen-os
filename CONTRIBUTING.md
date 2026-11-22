# Contributing to the future public platform

This is a local preparation candidate. Public contributions are not open yet: the confidential security-reporting route still needs to be enabled after the repository exists. Under the intended Apache-2.0 licence, contributions you intentionally submit are licensed under its terms (section 5) unless you state otherwise. No contributor agreement, developer certificate, governing body or external service is established by this document.

When a public project is approved, start with a small publishable problem statement, expected behaviour and a synthetic reproduction. Discuss substantial architecture, security, permission, cost or UI changes before implementation. Reuse established contracts and prefer the smallest maintainable change. Keep personal instance data out of issues, diffs and test fixtures.

## Local validation

Use an existing compatible Python interpreter, with no dependency installation:

```sh
python3 -B scripts/check_context.py
python3 -B -m unittest discover -s tests -v
```

Record what ran and its limits. Test observable behaviour; a static suite cannot validate provider accounts, native app discovery or an autonomous workflow. Update source hashes only after reviewing the affected changes; do not repin unexplained drift. Keep source paths workspace-relative and preserve strict approval and receipt gates.

## Lightweight preparation choices

| Item | Current decision |
| --- | --- |
| Contributing and security guidance | Included because privacy and reproducible local checks matter now. |
| Code of conduct | Defer adoption until maintainers and an escalation route are defined; no contact is invented. |
| Issue and PR templates | Defer until the public workflow is approved; use concise ordinary descriptions initially. |
| Automated test workflow | Local checks are reproducible. A future minimal read-only test workflow can be reviewed separately; no CI or release service is enabled here. |
| Roadmap | README and the architecture's phased roadmap are sufficient at this maturity. |

Contribute only material you have authority to submit. Confirm the approved outbound and contribution terms before accepting external contributions. Do not assume that the licensing recommendation has already granted rights.
