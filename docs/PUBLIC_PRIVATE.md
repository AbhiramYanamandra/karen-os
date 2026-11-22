# Public platform and private instance boundary

## What belongs where

| Public platform | Private instance, outside the platform tree |
| --- | --- |
| Reusable source, generic policy and execution contracts | Personal preferences and memories |
| Adapters, context utilities, SOP and skill definitions | Accounts, credentials, tokens and machine-local settings |
| Synthetic task/configuration examples and tests | Real task state, handoffs, approvals, logs and usage/billing observations |
| Public architecture, reusable assets and Project Factory designs | Calendar, messages, contacts, health, financial, relationship and private project records |

A private repository is not a secret vault. Sensitive data still needs access controls, retention, recovery and per-destination consent. A public repository is never the default memory or runtime-log sink. `.gitignore` is a convenience boundary, not encryption or a reliable secret detector.

## Proposed future layout

This example is a design, not directories or a storage service created by the candidate:

```text
platform-checkout/             public generic source
operator-selected-private/    outside the public tree
  instance-config.json        private preferences and approved references
  tasks/                      private work state
  handoffs/                   private continuation records
  memory/                     scoped private records
  runs/                       private receipts and redacted logs
```

Do not create these folders or new repositories automatically. Credentials belong in an approved secret mechanism, not the example JSON. Select data locations, permitted providers, classifications and retention before using real personal records.

The current reader is source-local. It rejects references outside its selected root and does not parse the proposed instance configuration. Until an external loader is designed and approved, use separately authorised private workspaces and reviewed, bounded context packs. A generated platform-policy snapshot in such a private pack must name its upstream revision and remain a derived read-only copy, not a second editable policy.

## One authority, without a synchronisation service

The authority transfer is complete (22 November 2026). This public repository is now the active development repository and is canonical for reusable code, policy, architecture and templates. The earlier working source is frozen as a private archive. Agents must not import its code, Git history or private records, and must not modify it. Exact mapping is retained privately, not distributed with the source.

Personalisation is expected here. Publishable descriptions of the owner's workflows, preferences and standards can live in this repository. The private records those workflows use cannot.

An instance pins a public platform revision and keeps private preferences, stricter restrictions and runtime records separately. Public platform changes follow reviewed source changes. Instance operators review upgrades and reconcile snapshots before dependent actions. Private overrides cannot silently relax approvals, data permissions or spending boundaries. There is no automatic bidirectional record or policy synchronisation.

Only sanitised platform bugs, synthetic reproductions and generic improvements may return to public issues. Sharing any private excerpt requires explicit consent for the exact destination and purpose. A context pack or handoff grants no new authority.
