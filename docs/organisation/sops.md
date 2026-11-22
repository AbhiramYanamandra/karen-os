# Essential agent SOPs

Public candidate procedure. These procedures expand architecture SOP01–SOP05 and SOP07. SOP06 release and SOP08 briefings remain future scope. Use the [templates](../templates/records.md) for durable outputs.

## Startup

1. Identify exploration versus actionable work. Read-only exploration uses `read --explore`, requires no task or claim, and loads the organisational core. Actionable work and machine validation require a supplied authorised task, the applicable complete sources, and current task read to the end. Detailed documents remain conditional; hashing is not reading.
2. Use the local startup reader when available. State the request and exact purpose before the first shell command; follow guards without disabling them. Direct file reads and manual hashes are valid fallback evidence, with unverified capabilities disclosed.
3. Ordinary exploration may use a concise human-readable explanation without a formal PASS. When machine validation is requested, separate source location, reading coverage, and revision verification in the JSON receipt. Record actual tools and six policy-scenario answers. Follow `context/receipt-template.json`; maximum 250 words, including field names and values, independent of JSON whitespace.
4. Missing, stale, or conflicting required policy means BLOCKED. Other mandatory gaps, missing evidence, false capability claims, or invalid format mean PARTIAL. PASS requires externally verified complete coverage, revisions, policy answers, and permitted capabilities. An unlocated current task blocks dependent implementation.
5. For substantive design, execution, skill use, or handoff, load the triggered detailed sources before acting and record their coverage too. Inspect Git status and history before writes. A startup-only PASS does not approve those actions.

## Intake and risk classification

1. For private work, use an authorised private workspace outside this public tree. Public platform tasks must be reviewed for publication; `docs/tasks/` here contains only synthetic validation source. Record outcome, owner instruction, criteria, exclusions, sensitivity, dependencies, action types, resource bound, and owner.
2. Classify impact independently from file count. Low risk means reversible local work with known behaviour and no meaningful UX, security, permission, sensitive-data, or spending change. A small authentication change requires design review.
3. Classify substantial UX, backend, architecture, infrastructure, or data changes as design-required. Mark uncertain risk unresolved and hold dependent implementation. Identify the precise unresolved decision, while continuing independent reads or drafts.
4. Record required design and action approvals separately. Intake passes when scope, risk, criteria, ownership, and gates are explicit. No issue or remote action is implied by a local task record.

## Design approval

1. Prepare the proposal template with current and intended behaviour, alternatives, reuse, affected systems, diagrams or visuals, permissions, costs, failure handling, verification, and rollback.
2. For UX, use editable Figma or an owner-accepted preview. For backend and infrastructure, show current and proposed structure and request or data flow. Use the proportionality rules in architecture section 11.
3. Present the concrete revision for owner review. Record actor, date, exact content hash, scope, constraints, evidence, and revocation or expiry conditions. Unknown approval is not approval.
4. Start substantial implementation only within that approval. Material scope, UX, architecture, permission, destination, or cost changes return here. Design approval does not pass any later publication gate.

## Implementation and verification

1. Recheck current context, approvals, scope, available permissions, resources, dependencies, task owner, and uncertain external actions. Claim the task only if unowned or the prior worker is confirmed stopped.
2. Select an isolated branch or worktree where appropriate. Small single-worker local foundation edits may use the existing checkout with the initial dirty state documented. Never discard the owner's work.
3. Perform bounded work, checkpoint on interruption or quota exhaustion, and use deterministic local tools where sufficient. No paid fallback. Stop repeated failures under the bounded recovery rules in architecture section 10.
4. Verify observable acceptance criteria. Record actual commands, artefact revisions, results, limitations, and a separate review pass. Do not turn a successful static check into a passing runtime test.
5. Prepare a reviewable diff and handoff. Consequential writes require their own current owner approval, even if tools permit them. A preparation or validation task grants no implicit commit, remote, publication, spending or deployment authority.

## Handoff and recovery

1. Save a numbered handoff in the authorised private workspace. This public tree contains templates, not private handoffs. Include objective, criteria, context and approval revisions, changed files, base commit plus dirty diff or hashes, completed work, checks, unresolved decisions, external-action uncertainty, and next safe action.
2. Update the task's latest-handoff pointer and state. Confirm that the outgoing worker has stopped before marking the claim released. Uncertain ownership blocks reassignment.
3. The recipient reruns startup, reads the canonical task and handoff, verifies the saved artefacts and approvals, checks tools and resources, reconciles unknown external results, then claims the task. Expired or missing approval cannot transfer as authority.
4. Recover from the last verified checkpoint. For an uncertain write response, reconcile external state using its operation key before retrying. A lost response is unknown, not proof of failure.
5. If a session can only export text, return the packet and have an authorised worker incorporate it before execution. Recovery passes only with known ownership, current context, and a bounded next action.
