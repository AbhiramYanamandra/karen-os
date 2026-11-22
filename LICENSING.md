# Licensing: Apache-2.0

`LICENSE` contains the unmodified official Apache License 2.0 text (from https://www.apache.org/licenses/LICENSE-2.0.txt). The owner confirmed Apache-2.0 and Abhiram Yanamandra as the rights holder and public commit author. No `NOTICE` file, per-file copyright header or contributor agreement exists; add them only if a later need arises. The licence body needs no holder name; the appendix boilerplate is only a template for per-file headers, which this candidate does not use.

Dependency review: the utilities use only Python's standard library and vendor no third-party code, so no dependency licence conflicts exist. OmniRoute is cited as an optional design reference only; nothing from it is included.

## MIT and Apache-2.0

| Choice | Practical trade-off |
| --- | --- |
| MIT | Short permissive terms allowing broad reuse, modification and distribution, conditioned on retaining the copyright and permission notices. Its text has no express patent-grant section. [Official MIT text](https://opensource.org/license/mit). |
| Apache-2.0 | Permissive copyright terms with an express contributor patent grant and patent-litigation termination provision. Redistribution includes licence and attribution obligations, modified-file notices, and relevant NOTICE obligations when a NOTICE file is supplied. [Official Apache text, sections 2–4](https://www.apache.org/licenses/LICENSE-2.0). |

Recommendation: Apache-2.0, subject to the rights holder's approval. Its explicit patent provisions fit an intended reusable platform with future extensions and contributions. MIT is a reasonable alternative if the owner prioritises shorter terms and accepts the absence of an express patent grant in its text.

Apache section 5 addresses intentionally submitted contributions unless otherwise stated. It does not create a separate contributor agreement for this candidate. The current utilities use Python's standard library and vendor no third-party package. Future dependencies and contributions still need licence review; neither choice automatically makes every dependency compatible. Apache's [compatibility discussion](https://www.apache.org/licenses/GPL-compatibility.html) is relevant if future distribution incorporates GPL-covered code.

## Exact adoption proposal

After the owner selects a licence and confirms rights and public attribution:

1. Add `LICENSE` containing the complete, unmodified selected official licence text. For MIT, populate its year and holder fields only from confirmed information. For Apache-2.0, use the full official text and confirm any project copyright notices separately.
2. Add `NOTICE` only if relevant attribution obligations or confirmed project notices justify it; do not invent a copyright owner or fictitious third-party attribution.
3. Replace README's pending-licence sentence with `Licensed under Apache-2.0; see LICENSE.` or the corresponding selected licence, only after adoption.
4. Confirm contribution terms and a public commit identity before accepting outside contributions or creating a public initial commit.

Publication, licence adoption, author identity and the promotion of this artifact into a canonical public project are separate decisions. No GitHub action is authorised here.
