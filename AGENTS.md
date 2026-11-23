# KAREN OS startup

For read-only interactive exploration, load the organisational core with `python3 -B scripts/startup.py read --explore`. No task file or claim is needed. Give a brief human-readable explanation of context, limits, and unknowns. Do not label it a validated PASS or create a task for every question.

Before actionable changes, require an explicit authorised task. Read `context/manifest.json`, all applicable complete core sources, and that task. `python3 -B scripts/startup.py read --task <relative-task-path>` returns full core text and hashes without writes or network access. Retrieve detailed sources when their triggers apply.

For routine pipeline steps (claim, PR, ready, cleanup, board sync), use `python3 -B scripts/pipeline.py`. Before the first shell call, state the request and exact command purpose. Respect guards; never disable them. If tools are unavailable, use direct reads and disclose unverified capabilities.

When a workflow requests machine validation, return only its declared JSON receipt, maximum 250 words including field names and values. The template and external assessor remain strict. Missing, conflicting, unverified, or partially read mandatory context cannot PASS. Normal human conversation is not a machine receipt. Apply the contract and SOPs for design, execution, skills, and handoff.
