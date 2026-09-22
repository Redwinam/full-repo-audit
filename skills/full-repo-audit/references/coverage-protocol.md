# Coverage protocol

## Durable state and helper

Resolve `<skill-dir>` from the loaded skill path, not the current directory. Use absolute, shell-quoted paths. The helper requires only Python 3; audit execution itself can use equivalent JSON bookkeeping if Python is unavailable, with the same gate applied manually and this limitation recorded.

```text
python3 <skill-dir>/scripts/audit_state.py init --root <repo-root> --state-dir <state-dir> --resolved-output-language <resolved-language>
python3 <skill-dir>/scripts/audit_state.py snapshot --root <repo-root> --state-dir <state-dir>
python3 <skill-dir>/scripts/audit_state.py check --state-dir <state-dir>
```

`init` creates `ledger.json`, `findings.json`, `resume.md` and `batches/` without overwriting existing state. `snapshot` emits current metadata to stdout without changing the ledger. `check` rechecks the snapshot, validates state and writes `coverage.json`; exit 0 means the completion gate passes (including explicit limitations), 2 means unfinished/invalid state, 1 means execution/input failure. Always read the JSON status, not only the exit code. `--runtime on|off|auto`, `--output-language auto|<language-tag>` and `--resolved-output-language <language-tag>` are init options.

New audits also set `quality_contract_version: 1` and seed seven pending entries in `quality_review`. `check` writes `code-quality.json` and `code-quality.md` before publishing its coverage result. Both the surface checks and quality catalog/matrix must close. Read [code-quality.md](code-quality.md) for finding kinds, quality dimensions, localized labels and the `upgrade` command for older ledgers. A legacy gate is explicitly labeled `legacy_not_assessed` for this expanded track.

`output_language` defaults to `auto`. The agent resolves user/conversation preferences using SKILL.md and passes the concrete tag; the standalone helper cannot inspect a conversation and falls back to `en` when no resolution is supplied. An explicit `--output-language` always wins over the resolution hint. Persist `resolved_output_language` to keep resumed reports consistent. Existing explicit-language ledgers without that new field remain valid. The helper's initial resume scaffold is available in English and Simplified Chinese; localize it to the resolved language before user-facing delivery rather than treating the scaffold language as a preference.

Use one writer; write UTF-8 JSON to a temporary sibling and atomically replace the destination. Keep audit artifacts outside the repository. State directories within the repository are omitted from snapshots, but should not overlap application paths. Never put state at the repository root or a parent of it.

The initial scanner uses Git tracked + non-ignored untracked paths (or all non-`.git` files without Git). It records hashes without emitting file contents, symlink identity without following external targets, and missing/unreadable/submodule boundaries. It deliberately does **not** recursively review submodules, ignored files, remote objects or dynamic registrations. Inspect `.gitignore`, ignored-path inventories and configuration; add relevant ignored sources to `extra_paths` (explicit root-relative file paths), then reconcile the snapshot. Enumerate separate roots/submodules and report inaccessible ones. File discovery is not semantic discovery.

## Schema version 1

`ledger.json`:

- `schema_version`, `audit_id`, `root`, `config` (defaults in SKILL.md), `extra_paths`.
- `snapshot`: `head`, `fingerprint`, `files` (relative path → content/type digest), `method`. Fingerprint represents actual tracked/untracked contents and file modes, not HEAD alone. No secret values belong in evidence.
- `surfaces`: all fixed surface names, each with `status`, `evidence`; `reason`, `impact`, `unblock` when needed. `status=pending|complete|not_applicable|unreviewable` describes discovery, not review coverage. `unreviewable` discovery means the denominator is unknown and names the missing registry/environment; add all known objects anyway.
- `units`: stable unique `id`, `surface`, `label`, `sources` (root-relative paths present in the snapshot), `depends_on` (unit IDs), `checks` (named check objects), optionally `batch_id`, `finding_ids`, `notes` and external object references. The helper seeds file-classification units. Add semantic units yourself.
- `quality_contract_version: 1`, `quality_review`: the dimension-scoped review and bidirectional catalog references defined in code-quality.md. Core `schema_version` stays at 1 for compatibility; the additional contract is explicit rather than retroactively certifying old audits.
- Check: `status=pending|in_progress|stale|reviewed|unreviewable|not_applicable`; `evidence` is an array of specific references/observations. `reviewed` needs a unit/check-specific observation or an exact batch section/case reference explaining the result; a generic batch-wide assurance is insufficient. Shared invariants can use common evidence with explicit applicability. `not_applicable` needs evidence and reason; `unreviewable` needs evidence, reason, impact and unblock action. Add domain-specific checks freely; the defaults in review-standards.md remain mandatory.

Example semantic unit (a shape example, not a finding about the user's project):

```json
{
  "id": "route:web:/settings",
  "surface": "route",
  "label": "/settings",
  "sources": ["src/routes.ts"],
  "depends_on": ["module:auth"],
  "batch_id": "B003",
  "checks": {
    "registration": {"status":"reviewed","evidence":["src/routes.ts:41–48; 已核对注册入口及参数解析"]},
    "access": {"status":"pending","evidence":[]},
    "navigation": {"status":"pending","evidence":[]}
  }
}
```

Do not force a framework dependency where none exists: a CLI may have no pages, routes or DB. Set those discovery surfaces to `not_applicable`, with the entrypoint/config evidence establishing absence. A failed search alone is insufficient. For runtime off/auto without setup, justify runtime absence; runtime on cannot be declared not applicable merely because tooling is missing.

## Discovery reconciliation

For each surface record the discovery commands/registries, excluded scope and count. At least reconcile file structure against applicable semantic registrations:

- pages/routes: router/file conventions, redirects, generated registrations and navigation entries; dynamic path patterns are units with relevant parameter/state classes, not every possible URL;
- APIs: method + normalized path or RPC/GraphQL identity; mounted prefixes, middleware, internal/admin handlers and webhooks;
- database: current effective schema and object definitions, migration chain, model/query references; external/live drift is a separate explicit scope/limitation;
- permissions: each policy/grant/guard plus role/action/resource/tenant allow-deny matrix, including anonymous and privileged paths;
- jobs: each task plus schedule/trigger/queue registration, retries and worker deployment;
- shared modules/components/integrations: exports, import consumers, external clients and first-party orphan/dead code;
- tests/delivery: test and fixture registries, scripts/CI, environment/dependency/build/deploy config and operational docs;
- cross-reference: every applicable flow template in SKILL.md and its concrete instances. Different permission or data boundaries need separate instances.

A generic unit such as "all APIs" cannot replace known endpoints. Group only genuinely equivalent generated objects with a recorded complete membership list, shared implementation evidence and checked per-member differences. Mark every member explicitly; group sampling is not exhaustive review.

## Coverage arithmetic and completion

For each surface, count all required and added checks:

```text
applicable = all checks minus justified not_applicable checks
reviewed_coverage = reviewed / applicable
accounted_coverage = (reviewed + explicitly unreviewable) / applicable
```

`unreviewable` stays in the applicable denominator and never enters the reviewed numerator. `pending`, `in_progress` and `stale` block completion. Surface absence yields `not_applicable`, not a fabricated 100%. Unknown discovery yields `reviewed_coverage=unknown`; report a separate known-check fraction without hiding unknown scope. Do not average surfaces into a misleading overall score. Report units and checks as well as percentages; one check cannot conceal unfinished sibling checks. Separate file accountability, semantic static coverage, runtime scope/coverage and cross-reference coverage.

Known-check closure at 100% with explicit gaps only permits `complete_with_limitations`. Empty/missing required checks, incomplete discovery, stale snapshot and unresolved candidates force `in_progress`. The checker also reports identical semantic evidence reused across units in `evidence_reuse` (file classifications excluded). This is an advisory traceability diagnostic, not a quality score or automatic failure: check the referenced observations instead of inventing different wording. The reviewer must reject weak evidence, unjustified exclusions and an incomplete semantic inventory even if the script passes.

## Resume and change invalidation

1. Read `ledger.json`, `findings.json`, `resume.md` and latest batches. Do not create a new state directory for a requested continuation.
2. Compare a fresh snapshot with the saved one, including additions/deletions, untracked content, mode changes and changed HEAD. The checker refuses a changed snapshot.
3. Before accepting the new snapshot, record old/new fingerprints and changed paths in a reconciliation batch. Reconcile manifest/file units and semantic inventory. Mark checks on changed units and their transitive consumers `stale`; revisit findings tied to those units. Add new units as pending, retain deleted-unit history in batch evidence, and remove retired units only with a reason.
4. Shared auth, schema, routing, config or generated-registration changes can invalidate an entire domain; broaden dependency tracing instead of trusting an incomplete graph. Reopen affected discovery surfaces and cross-reference checks. A HEAD-only change with identical content can retain review evidence after recording that fact.
5. Record why retained units remain valid. Only then replace `snapshot` with the fresh snapshot and continue. Never change a fingerprint just to silence the checker. Preserve unaffected reviews; after further source changes, repeat reconciliation.

Before final delivery rerun snapshot/gate checks and inspect findings references. Time/context exhaustion leaves a checkpoint, not completion.
