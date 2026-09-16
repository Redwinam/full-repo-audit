# Code-quality review and catalog

Read this for every whole-repository audit. Quality review is a first-class track, alongside functional/security review and coverage accounting. It must not disappear into batch summaries merely because higher-priority bugs exist.

## Three kinds, one canonical catalog

Every finding in `findings.json` has `kind`:

| Kind | Meaning | Evidence and classification |
|---|---|---|
| `defect` | An evidenced behavior, security, data-integrity or reliability problem | Describe the trigger and actual impact. Structural defects also carry `quality_dimensions`, so one root cause appears once, with its design implications attached. |
| `maintainability_debt` | An evidenced ongoing maintenance cost without a proven behavioral failure | Explain duplicated ownership, change amplification, coupling, ambiguous contracts or similar concrete cost. Name a simpler design and its tradeoffs. Usually P2/P3. |
| `improvement_opportunity` | A concrete, worthwhile structural improvement with a supported benefit; current behavior may be valid | Clearly non-blocking. Explain why it is worth considering, what it simplifies, and when the change may not pay off. P2/P3 is planning priority, not release severity. |

`confirmed` means the claim in that kind is supported. A confirmed improvement is not a confirmed bug. Do not demote material debt into a passing mention, promote preferences into defects, or invent findings to fill sections. P0/P1 risks with demonstrated behavioral consequences belong in `defect`.

Enter worthwhile observations as candidates in `findings.json` when discovered, including optional refactors. Before closing, confirm or reject every candidate using evidence. Rejected candidates retain their rationale; ordinary positive observations stay in the ledger. No quota, top-N limit or cosmetic-note flood: retain **all identified, evidence-backed, actionable items**, deduplicated by root cause. This is not a claim to have found every possible issue.

Do not record "duplicate helper, could clean up" only in a batch. Either create a debt/opportunity record with location, cost, proposal and verification, or document why the observation is not worth acting on. Preserve canonical finding IDs across the main report, code-quality report, ledger and fixes. Do not create a second debt ID for the design cause of an existing defect.

## Required finding fields

Keep all fields from output-contract.md. Add:

- `kind`: one of the three values above.
- `quality_dimensions`: an explicit list of applicable dimension names below; `[]` is allowed for defects without a code-quality implication.
- For debt/opportunities, nonempty `tradeoffs` and `behavior_to_preserve` (array).

For debt/opportunities, existing fields have precise meanings: `trigger` describes the maintenance/change scenario; `impact` states the concrete current cost or supported improvement benefit; `root_cause` identifies the design mechanism; `recommendation` describes the simpler design, its canonical owner and the proposed scope. `acceptance_checks` verify behavior preservation and the intended simplification. Do not replace an implementation with a broad "refactor this" suggestion.

Example (illustrative English prose, not a language preference or an actual repository finding):

```json
{
  "id": "Q-001",
  "kind": "maintainability_debt",
  "quality_dimensions": ["duplication", "ownership"],
  "status": "confirmed",
  "priority": "P2",
  "category": "maintainability",
  "confidence": "high",
  "title": "Two clients maintain the same session transition logic",
  "unit_ids": ["module:session-a", "module:session-b"],
  "locations": [{"path":"src/session-a.ts","start_line":8,"end_line":42}],
  "evidence": ["batches/B003.md#shared-session; both implementations and consumers compared"],
  "trigger": "Changing expiry, retry or logout semantics requires two coordinated edits.",
  "impact": "The same session contract has two maintenance and regression surfaces.",
  "root_cause": "State ownership is duplicated outside the existing shared client boundary.",
  "counterevidence": "The UI layouts differ, but the state transitions and protocol are equivalent.",
  "verification": {"method":"static","result":"confirmed","details":"Compared implementations and both consumers; no runtime divergence claimed."},
  "recommendation": "Move the session state machine to the existing shared client module; retain local UI adapters.",
  "tradeoffs": "Share protocol behavior only; coupling local presentation would reduce flexibility.",
  "behavior_to_preserve": ["Current login/logout results", "Both local UI layouts"],
  "acceptance_checks": ["One transition implementation serves both clients", "Expiry/error/logout regressions pass for each consumer"],
  "fix_scope": ["Shared client session module", "Two consuming adapters"],
  "depends_on": [],
  "history": [],
  "rejection_reason": ""
}
```

## Quality dimensions

New ledgers set `quality_contract_version: 1` and contain `quality_review` with all seven entries:

| Dimension | Questions to answer |
|---|---|
| `structure` | Can a simpler domain model remove concepts/layers/flags? Are large modules cohesive, or do responsibilities justify decomposition? |
| `ownership` | Does behavior live in the canonical layer? Are dependencies and mutation owners clear? |
| `duplication` | Are equivalent rules/helpers independently maintained? Are similarities intentional adaptations or a shared-owner opportunity? |
| `state_flow` | Are state transitions, derived state, cancellation and synchronization explicit? Do branch combinations create impossible/ambiguous states? |
| `type_contracts` | Are invariants expressed at boundaries? Do casts, optionality or fallbacks hide a real mismatch? |
| `failure_orchestration` | Are concurrency, partial failure, retries, resource cleanup and atomic publication coherent? |
| `clarity_dead_code` | Is indirection justified? Are old entrypoints/helpers/imports truly unused? Does naming or organization obscure a meaningful contract rather than taste? |

Each entry has `status`, `unit_ids`, `finding_ids`, `evidence`; add `reason` for `not_applicable` and `reason`, `impact`, `unblock` for `unreviewable`. Use the same check statuses as the coverage protocol. `reviewed` needs a nonempty unit scope and concrete observations; `finding_ids: []` explicitly means no catalog item was found for that dimension. `not_applicable` needs evidence of absence, not a missing finding.

Example shape:

```json
{
  "duplication": {
    "status": "reviewed",
    "unit_ids": ["module:session-a", "module:session-b"],
    "finding_ids": ["Q-001"],
    "evidence": ["batches/B003.md#shared-session; same transition owner duplicated, local layouts intentionally distinct"]
  }
}
```

All units with applicable `maintainability` checks must be represented in the dimension scopes; also include relevant API/job/permission/etc. boundaries. This is not a file-by-seven Cartesian checklist: choose relevant dimensions and explain scope. It complements rather than replaces unit-level checks. Confirmed findings and dimension `finding_ids` must reference each other; every affected unit must be included in that dimension's scope.

During the final cross-reference pass, reconcile batch observations, per-unit conclusions, quality dimensions and the canonical finding catalog. Ensure debt and optional improvements have not been lost during summarization. Resolve candidates; keep unreachable/uninspectable areas as limitations. Do not rewrite an entire product to settle an audit observation.

## Generated reports and completion

For the current quality contract, `check` writes:

- `code-quality.json`: all confirmed records grouped by kind, the quality matrix, pending/rejected candidates, limitations and source snapshot.
- `code-quality.md`: a complete readable rendering of the same data, with every finding field, source links and all three sections, including empty sections. There is no top-N truncation.
- `coverage.json`: both ordinary coverage and `quality_review` closure status/counts. These are review-completion statistics, not quality scores.

Fix information in `ledger.json` / `findings.json`, then rerun `check`; do not edit generated quality reports or maintain a competing catalog. `report.md` provides synthesis and links the full quality report. The final chat may be brief but must name the counts of defects, debt and opportunities and link the detailed report; do not make the user search batch logs to find recommendations.

For multi-root audits, generate these reports per state directory. The combined report links each root's quality catalog, identifies records by root/audit plus finding ID, and presents shared root causes once with all affected roots linked. Do not flatten ambiguous relative paths or count the same shared issue as independent discoveries. Combined completion requires all included roots and shared-boundary work to close.

Open candidates, unclassified items, missing dimensions, unrepresented maintainability units, inconsistent references and missing debt/opportunity tradeoffs prevent completion. Known unfixed items do not: review closure is distinct from remediation. Unreviewable quality dimensions permit only `complete_with_limitations` when all other required work is closed.

### Language of generated headings

Finding prose and observations must already use the resolved output language. Fixed schema fields, status values and dimension names remain English. English and Simplified Chinese report headings are built in. For another language, the agent creates `quality-labels.json` in the state directory without asking the user to translate. Its shape is:

```json
{
  "language": "fr",
  "labels": {
    "title": "Revue de la qualité du code",
    "defect": "Défauts confirmés",
    "maintainability_debt": "Dette de maintenabilité",
    "improvement_opportunity": "Améliorations structurelles facultatives (non bloquantes)",
    "matrix": "Dimensions examinées",
    "pending": "Candidats non résolus ou non classés",
    "rejected": "Candidats écartés",
    "limitations": "Limites",
    "empty": "Aucun élément enregistré dans cette section ; consulter le périmètre et les limites.",
    "notice": "La couverture de la revue n'est pas une note de qualité. Tous les éléments confirmés sont inclus ; les champs du protocole restent en anglais."
  }
}
```

Translate these ten values for the actual resolved language. A missing/invalid label file produces draft English headings and an `in_progress` result; static work can continue. This uses no translation API or new dependency. Rerunning `check` after supplying labels regenerates the full report.

## Continuing older audits

Core `schema_version` remains 1. A ledger without `quality_contract_version` is an older contract: `check` preserves its original coverage gate and reports `quality_review.status=legacy_not_assessed` plus an explicit warning. It does **not** certify the expanded quality review.

Before continuing an older audit under this Skill, run:

```text
python3 <skill-dir>/scripts/audit_state.py upgrade --state-dir <state-dir>
```

This backs up existing state under `pre-quality-upgrade-*`, adds pending quality dimensions, and marks missing finding classifications `unclassified`. It preserves finding IDs/statuses, core review evidence, language and source snapshot; it does not guess classifications or reopen unchanged source checks. Review the old batch observations for omitted debt/opportunities, classify retained findings, complete the quality matrix, then run `check`. Reconcile actual source changes separately. Repeated upgrades are a no-op. Do not remove the contract marker to bypass the new gate, and do not rewrite historical audits unless the user is continuing/reassessing them.
