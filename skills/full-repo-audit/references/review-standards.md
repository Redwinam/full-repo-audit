# Review standards

## Adaptation of the user-supplied Grok Skill

The supplied `Strict Code Quality Review` targets current-branch changes. Retain ambitious structural simplification, rigorous checking, canonical ownership and a small number of high-conviction findings. Extend these to all current code without inventing a historical regression. Claimed Cursor lineage has not been independently verified.

- **Structural simplification / code judo:** seek designs that remove concepts, branches, modes or layers while preserving behavior. Require a concrete simpler alternative, current maintenance cost, compatibility constraints and verification plan. Moving complexity is not removing it; speculative redesign is not a blocker.
- **File size / cohesion:** 1,000 lines is an inspection trigger, not an automatic defect. Evaluate responsibilities, coupling, ownership and navigation; name coherent extraction boundaries and expected benefit. Record generated/declarative exceptions. Do not claim an existing file recently crossed the threshold without history evidence.
- **Spaghetti growth:** repeated condition chains, flag combinations, nullable modes and scattered feature checks may indicate a missing model. Prefer removing exceptional states over centralizing the same complexity.
- **Direct implementation:** question identity wrappers, pass-through layers and generic magic without replacing simple code with an unnecessary framework.
- **Types / boundaries:** inspect casts, `any`, optionality, ad-hoc object shapes and silent fallbacks for obscured invariants. `unknown` with validation can be correct; flag actual contract ambiguity, not keywords.
- **Canonical ownership:** reuse existing helpers; keep behavior in the owning package/layer. Explain the concrete inconsistency or maintenance burden of duplication/boundary leakage.
- **Orchestration / atomicity:** examine avoidable sequential work, partial writes, retries and compensation. Suggest concurrency only when operations are independent and ordering/rate limits allow it. Do not propose a transaction across incompatible systems.

The source's presumptive blockers become evidence-based quality concerns here. Be strict about substantial design costs without treating taste, line counts or imagined simplifications as release blockers. Security/correctness/data-loss impact outranks maintainability; within maintainability prioritize structural simplification, branching, boundaries/types, decomposition, then legibility. Avoid cosmetic noise.

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
