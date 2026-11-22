# Platform checkout instructions

Project ID: `karen-os`. Published at `github.com/AbhiramYanamandra/karen-os`. Work follows `docs/organisation/engineering.md`: GitHub issues are the work queue, every change arrives as a pull request from a `<type>/<issue>-<short-description>` branch, and only the owner merges into `main`.

Read-only exploration uses the organisational core without a task or claim. Actionable work and machine validation require an explicitly authorised task and its current context. The platform source contains only generic instructions and synthetic examples. Never put personal tasks, handoffs, accounts, credentials, memory or runtime logs in this public tree.

Beyond the engineering standard's branch, pull-request and issue authority, preparation does not authorise remote creation, publishing, deployment, paid APIs, global configuration changes or autonomous dispatch. Instance operators must explicitly approve sensitive-data destinations and consequential actions. Current tooling does not implement an external instance loader or data storage service.

The manifest pins the public design candidate, generic vision, core policy, procedures and test fixture. Detailed architecture remains a target with explicit statuses. Local validation uses Python's standard library and requires no provider account. Source-local paths are resolved relative to the selected workspace; outside paths are rejected.

Run `python3 -B scripts/check_context.py`, `python3 -B scripts/startup.py read --explore`, and `python3 -B -m unittest discover -s tests -v`. Report unavailable tooling instead of installing dependencies. Actual agent discovery, tool permissions and account entitlements need separate environment-specific tests.
