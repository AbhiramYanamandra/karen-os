# Startup coverage and evidence contract

Public candidate coverage contract. The export-changes record explains how this derivative preserves the existing validation gates.

## Minimum mandatory content

| Source | Minimum content and reading requirement |
| --- | --- |
| Runtime entry | Complete AGENTS.md plus the one-line CLAUDE.md wrapper. Covers bootstrap procedure, guard handling, selective retrieval, and result requirements. Reading the wrapper is evidence of its contents, not proof of runtime import precedence. |
| `context/manifest.json` | Complete current manifest: identity, provisional baseline disposition, source paths, hashes, freshness, reading triggers, task requirement, and receipt limit. The manifest's own hash is captured externally; it cannot pin itself. |
| `docs/organisation/policy.md` | Complete small core: identity, independent interfaces, authority hierarchy, six boundaries, permissions, resources, task and ownership requirements, failure behaviour, and detailed retrieval triggers. |
| `docs/projects/karen-os/instructions.md` | Complete project scope, exclusions, canonical ownership, current phase, and verification commands. |
| Current task | Complete invocation-selected task: outcome, criteria, mode, owner, permissions, exclusions, and resource bound. No fallback to a previous task. |
| `context/receipt-template.json` | Complete receipt fields, coverage axes, capability labels, and format. Seven rows are required for the ordinary fixture; additional mandatory policy claims add rows. |

Read-only exploration (`read --explore`) needs no task or claim and omits the validation-only receipt format. Its human-readable explanation is not a machine PASS. All task-bound validation requirements below remain unchanged.

The selected task must have a reviewed hash in `manifest.task_revisions`. An absent task pin leaves its revision unverified and makes startup PARTIAL. The manifest itself is verified as the observed snapshot digest, independently compared with the fixture index; it cannot authenticate its own authority.

The core reader delivers all mandatory text with exact source ranges and SHA-256 values in one local tool result. A file being located or hashed is not reading coverage. Complete delivery means bytes for the full required source were present in a successful tool result; it does not prove human-like reading or private reasoning.

All manifest-required detailed sources must still exist and match their pins. Architecture, acceptance, owner vision, execution contract, detailed SOPs, registry, and templates are retrieved selectively. Substantial work, consequential actions, skill use, and handoff trigger their applicable detailed records. Any added required section must have explicit scope in a task-specific receipt before dependent action.

## Receipt and external assessment

The raw response must be one JSON object matching the template, with no fence or surrounding prose, at most 250 words across all keys and values. Word count uses `scripts/startup.py` and counts word tokens independently of formatting. Unknowns stay unknown. Source rows distinguish `located`, `read` as complete, partial, or none, and `revision_verified`.

Policy comprehension is tested by six explicit scenarios; it is separate from reading coverage. Read and hash capabilities require observed successful tool output. Write and network capabilities are unverified in these read-only probes. Neither available tool names nor an agent's assertion establishes a capability.

Direct file reads and manual hashes remain valid fallback material for separate observer review. The automatic assessor intentionally accepts only the audited reader command; unsupported manual evidence stays PARTIAL rather than being inferred as a pass. This does not remove the existing manual handoff route.

The lead collects successful startup-reader output from actual CLI tool-result events, retaining content and command evidence. `scripts/startup.py assess` matches it against the frozen fixture, checks the raw receipt's schema, rows, word count, hashes, answers, and capabilities, and computes status. It never repairs, truncates, or upgrades the worker's output. Fixture snapshots and evidence remain locally reviewable; they are not cryptographic attestations against a hostile host.

- PASS requires complete mandatory tool-delivered coverage, matching revisions, valid receipt, correct policy answers, and verified permitted capabilities.
- PARTIAL means required reading, evidence, comprehension, capability, or format is incomplete without an integrity or policy conflict.
- BLOCKED means a required source is absent or changed, or policy claims conflict. It holds dependent work even if a worker falsely says PASS.

A truthful PARTIAL or BLOCKED receipt can be well formed while startup remains incomplete. The assessment separates `receipt_valid` from startup status. Deterministic checks and self-reports alone do not certify live agent integration.

## Failure fixtures and handoff preservation

`prepare_startup_fixtures.py` copies only reviewed inputs into a new temporary destination. The missing fixture deletes its copied policy. The conflict fixture adds a separately hash-valid policy claim disagreeing on publication approval. Canonical policy is never edited for a negative test. Both agents receive the same snapshot per case; hashes are checked again after probes.

Manual handoff and export reconciliation remain supported contracts; this candidate claims deterministic fixture validation only. Private historical receipts are excluded from this public candidate. A startup pass does not establish handoff or automated ownership acceptance.
