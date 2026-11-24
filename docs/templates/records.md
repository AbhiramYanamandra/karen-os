# Durable record templates

Public template. Copy only the applicable template into its authorised destination. Personal and private-instance records belong outside this public source tree; public examples must be synthetic. Replace placeholders with evidence or an explicit `unknown` or `not applicable` reason. Task, proposal and handoff records lead with a summary and the decisions needed from the owner. A template never grants authority. Use UTC timestamps and show owner-facing times in the instance-configured timezone.

## Task

```yaml
summary: <what this record says, in one or two lines>
decisions_needed: [] # owner decisions, or none
task_id: <stable-id>
project_id: karen-os
record_revision: 1
updated_at: <UTC>
mode: <exploration|interactive-execution|delegated>
state: <scoped|awaiting-design|ready|working|blocked|checkpointed|review-ready|done|cancelled>
objective: <outcome>
acceptance_criteria: []
scope: []
exclusions: []
owner_instruction: <quoted scope and evidence reference>
risk: <low|design-required|unresolved with reason>
sensitivity: <classification and permitted destinations>
dependencies: []
context: <manifest revision and source hashes>
proposal: <path and hash or justified fast-path reason>
approvals: []
permissions_and_tools: []
resources: <usage observation and time; spending bound; stop condition>
execution_owner: <worker identity or null>
ownership_confirmed_at: <UTC or unknown>
base_commit: <sha>
workspace: <branch and dirty state>
uncertain_external_actions: []
latest_handoff: <path or null>
next_safe_action: <bounded action>
```

## Proposal and approval

```yaml
summary: <what this record says, in one or two lines>
decisions_needed: [] # owner decisions, or none
proposal_id: <stable-id>
revision: 1
state: proposed
task_id: <id>
approved_baseline: <exact commit SHA from the last approved plan revision>
baseline_approval: <owner decision reference and approved plan revision>
expected_paths: []
problem_and_current_behaviour: <evidence>
intended_outcome: <behaviour>
constraints: []
alternatives_and_tradeoffs: []
reuse: []
affected_systems: []
visuals_or_architecture: <versioned paths and hashes>
permissions_data_and_cost: <boundaries>
risks_and_failure_handling: []
acceptance_and_verification: []
rollout_and_rollback: <plan>
```

For plans that use drift checks, follow the engineering standard's [baseline guidance](../organisation/engineering.md#plans). Keep the approved baseline separate from the task's starting `base_commit`; use `not applicable` when no drift baseline is needed.

Record approval separately after owner review, so the proposal hash does not include its own hash:

```yaml
approval_id: <stable-id>
owner: <identity>
recorded_at: <UTC>
evidence: <owner statement and durable reference>
proposal_or_action_hash: <sha256>
task_id: <id>
action: <design|commit|create-private-remote|push|merge|deploy|send|other>
target: <exact artefact or destination>
scope_and_constraints: <limits>
expiry_or_revocation: <condition and current check>
state: <pending|approved|rejected|revoked|expired>
```

## Handoff

```yaml
summary: <what this record says, in one or two lines>
decisions_needed: [] # owner decisions, or none
handoff_id: <task-id/sequence>
project_id: karen-os
task_record: <path and revision>
created_at: <UTC>
from_worker: <identity>
claim_state: <released-after-stop|still-active|unknown>
objective_and_criteria: <task reference and any relevant detail>
context: <manifest revision, architecture, policy, and project hashes>
approved_scope: <proposal and approval references with exact revisions>
base_commit_and_branch: <sha and branch>
workspace_and_changed_files: <paths; saved diff or file hashes if uncommitted>
completed: []
verification: <commands, observed results, revision, limitations>
remaining: []
open_decisions_and_blockers: []
uncertain_external_actions: <operation keys, targets, observed state or none>
next_safe_action: <bounded action and gates>
```

Keep decisions with the task unless they change architecture or organisational authority, in which case propose an ADR and owner review. Preserve earlier handoffs rather than rewriting the prior worker's evidence.
