# Review standards

## Quality standards

Apply ambitious structural simplification, rigorous checking and canonical ownership to all current code, without inventing historical regressions. Every identified, worthwhile, evidenced defect, maintenance cost or concrete improvement belongs in the catalog.

- **Structural simplification / code judo:** seek designs that remove concepts, branches, modes or layers while preserving behavior. Require a concrete simpler alternative, current maintenance cost, compatibility constraints and verification plan. Moving complexity is not removing it; speculative redesign is not a blocker.
- **File size / cohesion:** 1,000 lines is an inspection trigger, not an automatic defect. Evaluate responsibilities, coupling, ownership and navigation; name coherent extraction boundaries and expected benefit. Record generated/declarative exceptions. Do not claim an existing file recently crossed the threshold without history evidence.
- **Spaghetti growth:** repeated condition chains, flag combinations, nullable modes and scattered feature checks may indicate a missing model. Prefer removing exceptional states over centralizing the same complexity.
- **Direct implementation:** question identity wrappers, pass-through layers and generic magic without replacing simple code with an unnecessary framework.
- **Types / boundaries:** inspect casts, `any`, optionality, ad-hoc object shapes and silent fallbacks for obscured invariants. `unknown` with validation can be correct; flag actual contract ambiguity, not keywords.
- **Canonical ownership:** reuse existing helpers; keep behavior in the owning package/layer. Explain the concrete inconsistency or maintenance burden of duplication/boundary leakage.
- **Orchestration / atomicity:** examine avoidable sequential work, partial writes, retries and compensation. Suggest concurrency only when operations are independent and ordering/rate limits allow it. Do not propose a transaction across incompatible systems.

The source's presumptive blockers become evidence-based quality concerns here. Be strict about substantial design costs without treating taste, line counts or imagined simplifications as release blockers. Security/correctness/data-loss impact outranks maintainability; within maintainability prioritize structural simplification, branching, boundaries/types, decomposition, then legibility. Avoid cosmetic noise.

Follow [code-quality.md](code-quality.md) to distinguish defects, debt and non-blocking improvements and close the seven quality dimensions. Prioritization determines order, not omission. A concrete simplification can deserve an improvement record even when there is no current bug; a speculative or purely stylistic preference does not.

## Required checks by surface

These names match the helper's defaults. Add domain-specific checks; justify any `not_applicable` check with evidence.

| Surface | Checks and focus |
|---|---|
| `file` | `classification`: ownership, purpose and semantic mapping; first-party/generated/vendor/sensitive. File accountability alone is not semantic correctness. |
| `page` | `behavior`: actions; `states`: loading/empty/error/success/stale; `access`: identity/role/data; `ux_accessibility`: focus/keyboard/labels/responsive assumptions; `contracts`: API/navigation/state; `maintainability`: cohesion/shared logic. Separate unobserved runtime aspects. |
| `route` | `registration`: actual path/params/redirects/reachability; `access`: guards/bypass; `navigation`: deep links, back/forward, invalid params/not-found. |
| `api` | `authn_authz`: identity/tenant/object/field access; `validation`: coercion/bounds/injection; `contracts`: errors/status/serialization/pagination; `side_effects`: atomicity/idempotency/races; `resilience`: limits/timeouts/cancellation. Include RPC, GraphQL resolvers and webhooks. |
| `database` | `integrity`: keys/constraints/nullability; `access`: grants/RLS/security context; `lifecycle`: effective schema/migrations/backfills/rollback; `performance`: indexes/query shape/locks. Each table, view, index, constraint, function/procedure, trigger and sequence used by the project is accounted for; repository schema is not proof of live schema. |
| `permission` | `allow_deny`: role/action/object matrix and negative cases; `tenant_boundary`: tenant/object scope; `bypass`: service/privileged/anonymous identity, direct endpoints, UI-only guards and storage access. Record expected-rule source. |
| `job` | `registration`: trigger/schedule/timezone/queue; `idempotency`: duplicates/partial work; `failure_recovery`: retry/backoff/dead letter; `concurrency`: overlap/locks/races; `privilege`: credentials/tenant propagation. |
| `component` | `behavior`: state/event contracts; `accessibility`: semantics/interaction; `maintainability`: cohesion/reuse/effects. |
| `module` | `contracts`: types/invariants; `maintainability`: structural standards; `failure_modes`: state/concurrency/resources. Include CLI/library entrypoints. |
| `integration` | `contracts`: external data/config; `resilience`: timeout/retry/idempotency/limits; `trust`: input/secret/data exposure. |
| `test` | `risk_coverage`: requirements and negative/concurrency cases; `reliability`: fixtures/isolation/flaky or vacuous assertions. |
| `delivery` | `build_config`: scripts/dependencies/lock consistency; `security_config`: secrets/access/version-specific dependency risk; `operations`: CI/deploy/rollback/logging/recovery. |
| `runtime` | `observations`: actual steps per route/role/environment; `negative_cases`: forbidden/error/empty cases; `console_network`: exceptions/failed requests. Add responsive/a11y checks as appropriate. |
| `cross_reference` | `end_to_end`: connected invariants and negative paths; `consistency`: shared contracts/ownership/canonical helpers. |

## Evidence bar

Establish a concrete trigger or maintenance cost, impact, root cause and current evidence. Read surrounding flow and consumers. Look for counterevidence in guards, caller invariants, constraints, feature flags and tests. Use the smallest safe relevant verification when useful. Clear static causality can confirm a defect without running it; label execution status accurately. Store unresolved hypotheses as candidates, rejected ones with rejection evidence. Do not fill a finding quota.

For reproductions, identify the precondition that makes the result meaningful and verify it directly. A browser wait must target the actual response, state or rendered text establishing that precondition; arbitrary delays, an unrelated selector or a swallowed timeout cannot prove a refresh completed. Preserve the failing observation but narrow the claimed verification when a precondition was not established. Keep current-data exposure distinct from supported future-input scenarios: code may prove a possible mismatch without proving existing records are already affected.

Describe the fixture boundary: list replaced modules/services and framework adapters, explain what remains real, and separate directly asserted outcomes from static implications or untested variants. A confirmed finding may combine static and runtime proof, but its verification description must not silently promote an unexecuted variant into a reproduced result.

Preserve fixture setup/reset steps and the source snapshot or relevant file hashes so another agent can replay the case from a known state. If a script imports from an active checkout, disclose that dependency and require snapshot reconciliation before replay; a saved script alone is not a self-contained reproducer.
