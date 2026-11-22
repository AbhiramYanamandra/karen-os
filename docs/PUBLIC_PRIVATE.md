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

During preparation, the existing working source remains authoritative. This candidate is a publication artifact: only the documented sanitisation and release-preparation overlays are permitted here. No independent feature work or competing decisions happen here. Functional changes must be proposed to the working authority and require a fresh privacy-reviewed export. The working source is not edited during this preparation task. Exact mapping is retained privately, not distributed with the source.

If the owner later promotes a public repository, approve one explicit authority transfer. The public platform becomes canonical for reusable code, generic policy, architecture and templates. Freeze the earlier working source as a private archive instead of maintaining a second editable platform fork.

An instance pins a public platform revision and keeps private preferences, stricter restrictions and runtime records separately. Public platform changes follow reviewed source changes. Instance operators review upgrades and reconcile snapshots before dependent actions. Private overrides cannot silently relax approvals, data permissions or spending boundaries. There is no automatic bidirectional record or policy synchronisation.

Only sanitised platform bugs, synthetic reproductions and generic improvements may return to public issues. Sharing any private excerpt requires explicit consent for the exact destination and purpose. A context pack or handoff grants no new authority.
