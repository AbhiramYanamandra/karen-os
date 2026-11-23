# Notion workspace for the daily review

Issue #23, part of epic #17 ([proposal](../proposals/daily-review.md)). This is the generic shape of the owner's Notion dashboard, plus a guide for building it on the free plan. Every example is made up. The owner's real goals, tasks, plans and drafts stay in Notion and never enter this repository.

## What Notion is for, and what it is not

Notion is the owner's **personal dashboard**: goals, personal tasks and daily plans, with a read-only view of engineering facts. It is the private instance for the personal layer (decision D08). Any assistant the owner connects (Muse, Claude Code, Codex) reads and writes the same pages.

It is not the source of truth for everything:

| Record | Authority | What Notion shows |
|---|---|---|
| Goals, personal tasks, daily plans, check-ins | **Notion** | The record itself |
| Engineering issues, PRs, labels, CI | GitHub | A read-only digest with links and an observed-at time (#24). Change things on GitHub, never in the digest. |
| Calendar events | Google Calendar | Nothing copied. The assistant reads the calendar directly and writes plan blocks only to the KAREN plan calendar (#25). |
| Email | Gmail | Nothing copied |
| Platform rules, prompts, scripts | KAREN OS Git | Nothing copied; link to the repository |
| Approval to publish a LinkedIn post | The approval record designed in #27, bound to the exact text | Draft text and outcome only. A Notion status is not an approval. |
| Tokens and credentials | macOS Keychain or environment | Never |

A row that reflects another source carries the source link and when it was observed. If it is stale or the source was unreadable, the row says so instead of guessing.

## Build order

1. **Now (MVP):** Goals, Tasks, Daily plans and the Dashboard page.
2. **With #24:** the Engineering digest database, which only the digest script writes.
3. **With #27:** the LinkedIn drafts database.

Each database is useful on its own. Nothing needs a paid feature: no Notion AI, no Custom Agents, no automations.

## Data model

Property types are Notion's names. "Owner" means the owner edits it; "Assistant" means the connected assistant may write it; "Script" means only a KAREN script writes it.

### Goals

| Property | Type | Values or notes | Written by |
|---|---|---|---|
| Name | Title | The goal, one line | Owner, assistant proposes |
| Level | Select | `Month`, `Week`, `Day` | Owner, assistant proposes |
| Period | Date | Start and end dates of the month, week or day | Owner, assistant proposes |
| Status | Status | `Proposed`, `Active`, `Done`, `Dropped` | Owner. The assistant creates weekly and daily goals as `Proposed`; only the owner makes them `Active`. |
| Parent goal | Relation → Goals | A week goal's month goal, a day goal's week goal | Owner, assistant proposes |
| Tasks | Relation → Tasks | Two-way with Tasks → Goal | Either |
| Progress | Rollup | Tasks → Status, percent per group (`Done`) | Calculated |
| Notes | Text | Why it matters, how to measure it | Owner |

Monthly goals are always the owner's. On Sundays the assistant proposes weekly goals, and each morning it proposes daily goals. The owner adjusts or accepts them (#25).

### Tasks

| Property | Type | Values or notes | Written by |
|---|---|---|---|
| Name | Title | | Owner, assistant |
| Status | Status | `To do`, `Doing`, `Done`, `Dropped` | Owner. The assistant may create tasks, but only the owner ticks them off. |
| Goal | Relation → Goals | Optional | Owner, assistant |
| Due | Date | Optional; time optional | Owner, assistant |
| Priority | Select | `High`, `Normal`, `Low` | Owner |
| Source | Select | `Personal`, `GitHub issue`, `Email`, `Meeting` | Assistant sets it on tasks it creates |
| Link | URL | For a GitHub issue, the issue URL. The issue stays the engineering record; this task only reminds the owner of their own part, such as reviewing. | Assistant |
| Created by | Created by | Shows whether the owner or an integration made it | Notion |

Engineering work is not copied into Tasks. The digest shows it, and GitHub tracks it.

### Daily plans

One page per day.

| Property | Type | Values or notes | Written by |
|---|---|---|---|
| Name | Title | `2026-03-14`, the date in ISO format | Assistant |
| Date | Date | | Assistant |
| Morning plan | Text | Short summary of the ranked day. The time blocks themselves are on the KAREN plan calendar. | Assistant |
| Day goals | Relation → Goals | Today's day goals | Assistant |
| Planned tasks | Relation → Tasks | | Assistant |
| Evening review | Text | Done, waiting, slipped | Assistant, from the evening conversation |
| Carryovers | Relation → Tasks | Tasks moved to tomorrow | Assistant |
| Check-in | Text | Meals, sleep, energy: only what the owner reports | Assistant, from the owner's words |
| Digest observed at | Date (with time) | Observed-at time of the digest the plan used, or empty if none | Assistant |
| Sources unavailable | Multi-select | `Digest`, `Calendar`, `Email`, `Notion`, `GitHub`, set when a source could not be read | Assistant |

The page body can hold the full briefing text. The assistant writes today's page and never rewrites an earlier day's page, except to add the evening review.

### Engineering digest (with #24)

One row per item the digest reports. Only the digest script writes here; people and assistants read it. Rows are keyed so that a later run updates them rather than duplicating them.

| Property | Type | Values or notes |
|---|---|---|
| Item | Title | `octo/demo#12 Add retry to the uploader` |
| Key | Text | Stable upsert key: `<owner/repo>#<number>:<section>`, or `<owner/repo>:<section>` for repository-level rows |
| Section | Select | `Waiting for you`, `Blocked`, `Needs you`, `Ready`, `Failing CI`, `Done since last digest`, `Source unavailable` |
| Repository | Select | `owner/name` |
| Link | URL | The GitHub issue, PR or workflow run |
| Priority | Select | `P0`–`P3` where the issue has one |
| Observed at | Date (with time) | When the script read GitHub, UTC |
| State | Select | `Current` while the item still appears; `Cleared` once a later run no longer sees it. Cleared rows are kept for "since last digest" and can be archived by hand. |
| Age (hours) | Formula | `dateBetween(now(), prop("Observed at"), "hours")` shows how stale the row is |

The script never edits the other databases, and never edits a row it did not create (it matches on Key). If GitHub cannot be read, it writes or updates a `Source unavailable` row for that repository rather than clearing that repository's items.

### LinkedIn drafts (with #27)

| Property | Type | Values or notes | Written by |
|---|---|---|---|
| Title | Title | Short label | Drafting agent |
| Text | Text | The post as drafted. The owner may edit it before approving. | Agent, owner |
| Source | URL | The merged PR or finished project | Agent |
| State | Select | `Draft`, `Waiting for approval`, `Posted`, `Withdrawn` | Agent and posting script. Display only. |
| Post link | URL | Set after posting | Posting script |
| Posted at | Date (with time) | | Posting script |

`State` only displays the workflow. Changing it to anything does not approve a post. #27 defines the separate, owner-only approval, which is bound to the exact text, the account and an expiry. Any edit to `Text` after approval cancels that approval.

## Dashboard page

A single page named **KAREN**, the parent of every database above, opened on the phone each morning. From top to bottom:

1. **Today:** a linked view of Daily plans filtered to `Date` is today, showing Morning plan and Sources unavailable.
2. **Waiting for you:** a linked view of Engineering digest where `Section` is `Waiting for you` or `Needs you` and `State` is `Current`, sorted by Priority. With #27, also LinkedIn drafts where `State` is `Waiting for approval`.
3. **Goals:** a linked view of Goals where `Status` is `Active` or `Proposed`, grouped by Level. Proposed goals are shown so the owner can accept them.
4. **Open tasks:** a linked view of Tasks where `Status` is `To do` or `Doing`, sorted by Due, then Priority.
5. **Digest freshness:** a linked view of Engineering digest showing the newest `Observed at` and its `Age (hours)`, so a stale digest is obvious.

Keep the dashboard short. Full databases stay one tap away.

## Setup guide (owner, about 30 minutes)

Everything happens in the owner's own Notion account on the free plan. Nothing here goes into the repository.

### 1. Pages and databases

1. In the sidebar, create a private page named **KAREN**.
2. Inside it, type `/database` and choose **Database – inline** three times, naming them **Goals**, **Tasks** and **Daily plans**.
3. Add the properties from the tables above. To add one, click **+** at the right of the table header, then pick the type. For a **Status** property, rename its options to match the tables.
4. Add the relations:
   - In Tasks, add **Goal** (Relation → Goals) and turn on **Show on Goals**, naming the other side **Tasks**.
   - In Goals, add **Parent goal** (Relation → Goals) for the self-relation.
   - In Daily plans, add **Day goals** (→ Goals), **Planned tasks** (→ Tasks) and **Carryovers** (→ Tasks).
5. In Goals, add the **Progress** rollup: Relation **Tasks**, property **Status**, calculate **Percent per group** → `Done`.

### 2. Dashboard

At the top of the KAREN page, add the linked views listed under [Dashboard page](#dashboard-page). Type `/linked view of data source` and choose the database, then set the filter and sort. Leave the database blocks below them.

### 3. Digest and drafts later

Create **Engineering digest** when #24 is ready to write to it, and **LinkedIn drafts** with #27, using the tables above.

### 4. Integration for scripts (with #24)

Scripts reach Notion through an **internal integration**. Its token is a secret and never goes into the repository, an issue, a PR or a chat.

1. Open Notion's integrations page (Settings → Connections → **Develop or manage integrations**), choose **New integration**, type **Internal**, and name it **KAREN scripts**.
2. Under **Capabilities**, keep **Read content**, **Update content** and **Insert content**, set comments off, and choose **No user information**.
3. Copy the token and store it in the macOS Keychain. In Terminal, run the command below and paste the token when asked. It is not echoed, and it doesn't go into shell history:

   ```bash
   security add-generic-password -a karen-os -s notion-token -w
   ```

4. Share **only the databases a script needs** with the integration: open the database as a full page, choose **•••** → **Connections** → **KAREN scripts**. For #24 that is Engineering digest only, and for #27, LinkedIn drafts. Don't share the KAREN page itself, because children inherit the connection.
5. Copy each shared database's link, then put the IDs in `~/.config/karen-os/daily-review.json`, outside the repository. A synthetic example:

   ```json
   {
     "notion": {
       "token_keychain": {"account": "karen-os", "service": "notion-token"},
       "engineering_digest_database": "00000000000000000000000000000000"
     },
     "repositories": ["octo/demo", "octo/other"]
   }
   ```

To revoke access, remove the connection from the database or delete the integration. Then remove the token with `security delete-generic-password -a karen-os -s notion-token`.

### 5. Assistants

Connect Muse (or another assistant) through its own Notion connector, and share the KAREN page with it. The assistant follows the "Written by" columns above and the rules in the briefing prompts (#25).

## Check before connecting real data

Confirm these in the owner's own workspace before any script writes there. #24 records the results:

- [ ] The integration appears and can be limited to the capabilities above on the free plan.
- [ ] The integration sees only the databases shared with it. A search from the API returns nothing else.
- [ ] Which Notion API version is used. From version `2025-09-03`, a database holds one or more data sources, and rows are queried and created through the data source, so the config may need the data source ID instead of the database ID.
- [ ] Rate limits are respected. Notion asks for about three requests a second on average, and a digest run stays well under that.
- [ ] A dry run prints what would be written and writes nothing.
- [ ] Notion stores the data on its own servers under the owner's account. The owner accepts that destination for these records.

## Retention

The owner keeps or archives pages as they like. Cleared digest rows can be archived after a week. Archiving is Notion's soft delete and can be undone from Trash for a limited time. Scripts never delete pages.
