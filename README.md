# KAREN OS

KAREN OS is a local-first, model-agnostic Personal AI Operating System project. It aims to reduce repeated context setup and routine administration while keeping people in control of design decisions, sensitive data, spending and consequential actions.

This checkout is a sanitised local public-release candidate. It is not yet published or independently governed. Licensed under Apache-2.0; see [LICENSE](LICENSE). See [licensing decisions](LICENSING.md) and the [candidate audit](docs/reviews/candidate-audit.md).

## Intended experience

Use a compatible agent directly to explore an idea, review a design, or perform a bounded authorised task. A new session loads shared rules and current project context. Another compatible agent can use durable private records to resume the work without needing the earlier conversation. No chief-of-staff interface or model provider is mandatory.

Read-only discussion needs no task file. Substantial implementation needs an authorised task and an approved design. Publishing, external messages, installation, sensitive-data destinations, permission changes and additional spending need their own explicit authority.

## Current state

Implemented locally:

- Thin Codex and Claude Code entry files pointing to shared context.
- A source manifest with paths, reading triggers, hashes and synthetic task revisions.
- Read-only context loading, task-free exploration and strict receipt assessment.
- Missing/conflicting policy checks and a supervised documentation-handoff fixture validator.
- Generic SOPs, record templates, empty reviewed-skill metadata and deterministic tests.

Proposed or unvalidated:

- A working autonomous assistant, coordinator, dispatch service or dashboard.
- A private-instance loader, storage backend, synchronisation service or account integrations.
- Live resource telemetry, morning/evening briefings, design-system implementation and Project Factory automation.
- This candidate's native-agent discovery, ChatGPT/Work access, remote execution and broad operating-system compatibility.

The public architecture is a [design candidate](docs/architecture/platform-specification.md), not a claim that these future capabilities exist.

## Local setup and checks

Use an existing Python installation. There are no third-party runtime dependencies, provider credentials or subscriptions needed for these commands.

```sh
python3 -B scripts/check_context.py
python3 -B scripts/startup.py read --explore
python3 -B -m unittest discover -s tests -v
```

Run them from the checkout root. Python 3.9 is the minimum API baseline used by the utilities; only the environment recorded in the audit has been tested. If your interpreter is named differently, adapt the local command. Agent evidence fixtures currently use the literal `python3` command convention.

The reader resolves sources inside its selected workspace and rejects outside paths. Its JSON output is tool context, not a required conversational response. Machine-validation workflows use the declared [receipt format](context/receipt-template.json), exact coverage evidence and a 250-word limit. A successful hash check does not prove approval, native instruction discovery or permission to act.

Optional agents can begin at [AGENTS.md](AGENTS.md); [CLAUDE.md](CLAUDE.md) imports the same entry. Installed runtimes, their accounts, tools and permissions require separate testing. Local tests make no model calls.

## Public platform, private instance

A public platform does not mean public personal memory. Source contains reusable code, generic rules and synthetic examples. Personal tasks, handoffs, preferences, calendars, messages, health and financial data, credentials and logs belong outside the public source tree.

[The boundary and maintenance proposal](docs/PUBLIC_PRIVATE.md) describes one future platform authority and private instance state. No private storage or synchronisation system is built here. [Example configuration](examples/instance-config.example.json) is a documented proposal, not a file the current reader loads.

## Roadmap

1. Review the sanitised architecture, data boundary, licensing and release identity.
2. Reproduce local checks from the approved public snapshot; validate optional adapters with explicit accounts and permissions.
3. Select one small authorised workflow and test design, verification and manual handoff before increasing automation.
4. Extract reusable components and templates from real work.
5. Consider optional personal operations, capacity monitoring, Project Factory and coordinator capabilities only with evidence and approval.

Level 2 supervised autonomy, design-first engineering, durable context, reusable skills, least privilege and zero additional spending without approval remain design principles. Optional chief-of-staff and gateway evaluations remain outside the critical path.

## Participation

See [CONTRIBUTING.md](CONTRIBUTING.md). This local candidate is not accepting public contributions yet. Private vulnerability reporting must be enabled on GitHub after the repository is created; see [SECURITY.md](SECURITY.md). No hosted service, contribution agreement or public issue backlog is created by this candidate.
