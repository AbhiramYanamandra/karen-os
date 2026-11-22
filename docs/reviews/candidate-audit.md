# Local public candidate audit

Disposition: prepared for owner review; not approved for publication. Apache-2.0 `LICENSE` text is included; the owner confirmed the licence and rights holder. No hosted repository, remote, push, service or paid API was used.

## Scope and inventory

This candidate was assembled from reviewed files, not cloned from private Git history. Its local Git repository has an unborn `main` branch, no commits, no inherited objects and no remotes. An initial commit is deferred until the public author identity is chosen. The working source and its Git history were left unchanged; exact source mapping and the before/after inventory are retained privately.

| Included files | Treatment |
| --- | --- |
| `scripts/check_context.py`, `scripts/startup.py`, `scripts/collect_startup_evidence.py`, `scripts/prepare_startup_fixtures.py` | Reviewed generic utilities; byte-identical source copies |
| `tests/test_context.py`, `tests/test_startup.py`, `tests/test_handoff.py` | Reviewed deterministic tests; byte-identical source copies |
| `AGENTS.md`, `CLAUDE.md`, `context/receipt-template.json`, `docs/organisation/skills.json`, `docs/tasks/startup-validation.md` | Reviewed reusable entries, metadata and synthetic fixture |
| `context/manifest.json` | Public-only references and regenerated pins |
| `docs/architecture/platform-specification.md`, `docs/architecture/design-status.md`, `docs/architecture/export-changes.md`, `docs/vision.md` | Sanitised design and product intent, explicit candidate status and changes |
| `docs/organisation/policy.md`, `docs/organisation/execution-contract.md`, `docs/organisation/sops.md`, `docs/organisation/startup-coverage.md`, `docs/projects/karen-os/instructions.md`, `docs/templates/records.md` | Generic policy and procedures with explicit public/private destinations |
| `README.md`, `.gitignore`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSING.md`, `docs/PUBLIC_PRIVATE.md`, `examples/instance-config.example.json`, this report | Public preparation documentation and proposed configuration |

Excluded: private Git history and metadata; raw owner-vision and conversation provenance; historical personal tasks, approvals and handoffs; raw runtime logs and evidence; private readiness/review reports; account configuration, caches and machine metadata. Those exclusions do not delete the underlying generic architectural requirements. The private mapping must never be added to the public candidate.

## Privacy findings

Candidate source and new Git metadata were inspected for credentials, private identifiers, personal account references, unnecessary machine paths and sensitive records. Known identifying markers and credential-pattern checks found no remaining matches. Manual review also covered architecture, policy, templates, synthetic fixtures, configuration and documentation; a credential scan alone was not treated as sufficient evidence.

Personal project examples and provenance were generalised. Generic privacy, recovery, permission and resource requirements remain. Private records and history stay outside this tree. `.gitignore` excludes common credentials, runtime data, logs, handoffs and real task records, but is not a security boundary. The example instance configuration contains no user settings or credentials and is not loaded by current utilities.

This is a bounded review, not a guarantee that every possible sensitive fact can be recognised automatically. Owner review of the sanitised design and rights to distribute remains necessary.

## Architecture and behaviour

All 79 original requirement/decision identifiers remain: R01–R16, ADR01–ADR15, N01–N12, AC01–AC20 and D01–D16. All four Mermaid blocks are byte-identical. ADR16 explicitly proposes the public-platform/private-instance boundary. See [export changes](../architecture/export-changes.md).

The public architecture is a review candidate, not an imported private approval. Generic vision replaces the personal profile. Source-local loading, approval flags, task-free exploration, task-bound execution, strict 250-word machine receipts and supervised manual handoff remain. No runtime Python implementation was changed. External private-instance loading and synchronisation remain unimplemented proposals.

## Validation evidence

The candidate's complete deterministic suite passed: **40 tests**. A separate clean source copy, excluding Git metadata and all private or ignored files, also passed all **40 tests**. Context/hash validation passed in both locations. Exploration loaded five mandatory sources without a task; the synthetic task workflow loaded seven required sources. Missing/conflicting context, receipt constraints and handoff behaviour are exercised by the suite. Local evidence was retained privately rather than embedding tool logs in public source.

Validation used macOS and Python 3.13.7. No native agent/model sessions were rerun. Historical native-startup or cross-agent observations from the private source are not claimed as candidate compatibility evidence. ChatGPT/Work integration, wider precedence cases, other operating systems, other Python versions and autonomous dispatch remain unvalidated. The clean-copy check is not a third-party reproduction or a remote clone.

Local Markdown file targets, manifest hashes, ignore rules, source-code identity, retained requirement IDs, diagrams and independent empty Git history were checked. Original source files and Git metadata were compared against the export baseline for content, mode and modification time. No source changes were found.

## Publication decisions

Recommend Apache-2.0, subject to the rights holder's decision; see [licensing](../../LICENSING.md) for the MIT comparison and adoption steps. No active `LICENSE` or invented attribution is supplied. Choose public commit identity and a confidential security-reporting route, approve the public design and inventory, and explicitly authorise any later publication.

The [maintenance proposal](../PUBLIC_PRIVATE.md) keeps one reusable platform authority and private instance data outside public source. Promotion requires an explicit authority transfer; there is no second independently governed project or synchronisation service.
