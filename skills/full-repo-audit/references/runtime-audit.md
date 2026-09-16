# Optional runtime / browser audit

Use available project tests, browser tools or an existing Playwright setup. Playwright is an example, never a hard dependency. Libraries/CLIs can use suitable smoke checks instead.

- `off`: runtime discovery is `not_applicable`, with an explicit static-only scope reason.
- `auto`: assess existing scripts, URLs, tools and test accounts. Use a suitable authorized environment when available. Declare selected routes/roles/viewports and all omitted runtime scope. With no environment, record why runtime was not performed; static work continues.
- `on`: enumerate the requested runtime matrix. Missing setup/accounts/tools becomes `unreviewable`, with reason, impact and unblock action. Ask only for genuinely missing prerequisites while continuing independent static work; do not silently downgrade to off.

Record environment URL/build identity, relation to the audited snapshot, role/tenant, viewport, fixtures and timestamps. A deployed build of unknown provenance cannot certify the local checkout. Never persist cookies, tokens, passwords or personal records in traces/reports.

1. Observe each selected route/flow directly and through navigation, including primary actions and relevant loading/empty/error/forbidden/expired-session cases.
2. Inspect console/network, keyboard/focus and declared viewport layouts. Record actual observations rather than invented accessibility/performance scores. Sampling cannot be labeled exhaustive runtime coverage.
3. Inspect side effects before tests or browser actions. Use safe fixtures/test tenants within existing authorization. Do not send messages, make purchases, run migrations, destroy data or write to production merely to prove a finding. If a required scenario exceeds authorization, document the gap and ask only for that action when needed.
4. Save minimal redacted evidence. A screenshot supports only visible details; HTTP 200 alone does not prove correct authorization or UI.
5. Record steps, expected/actual results, commands/exit codes where available, skipped cases and cleanup actually performed. Environment setup failure is a limitation, not automatically an app defect.

Static and runtime coverage stay separate. Missing browser tools never justify leaving static page/route/API review pending.
