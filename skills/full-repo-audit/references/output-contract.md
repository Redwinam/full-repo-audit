# Output contract and fix-agent handoff

Schema keys and status values stay English; narrative fields and Markdown use `config.resolved_output_language` (or the explicit `output_language`). Keep symbols, commands, paths, errors and identifiers unchanged. Paths are repository-relative in JSON plus the ledger's absolute root; report links should resolve for the user.

## Artifacts

- `ledger.json`: authoritative inventory, source snapshot, dependencies, checks and limitations.
- `findings.json`: `{"schema_version":1,"findings":[]}`. Empty findings are valid; they do not prove full coverage.
- `code-quality.json` and `code-quality.md`: helper-generated complete views of the canonical catalog, grouped as defects, maintenance debt and optional improvements, with the quality matrix and limitations. Read [code-quality.md](code-quality.md) for required fields and migration. Never maintain a second independent finding list.
- `coverage.json`: machine-generated gate result, per-surface counts, explicit gaps, runtime scope, validation errors and source drift. Do not edit it to improve results. In `audit-then-fix`, `coverage-audit.json` preserves the gate result at `close-audit`.
- `batches/<batch-id>.md`: actual work/evidence, commands and exit outcomes, candidate verification, limitations and next units. Redact sensitive outputs.
- `resume.md`: exact resumable position and outstanding work; after closure say which follow-up work belongs to a separate fixing task.
- `report.md`: user-facing review and handoff. Link the machine artifacts and supporting evidence.

## Finding schema

Every record has a stable ID. Preserve IDs across resume/revalidation. One root cause is one finding: list every affected unit and location in it instead of filing each symptom separately; keep genuinely separate causes that share a theme as separate findings linked through `depends_on` or `related_ids`. Store candidates and rejections as well as confirmed records; only confirmed records appear in the main lists.

```json
{
  "id": "F-001",
  "kind": "defect",
  "quality_dimensions": [],
  "status": "confirmed",
  "priority": "P1",
  "category": "authorization",
  "confidence": "high",
  "title": "资源查询缺少租户范围限制",
  "unit_ids": ["api:GET:/records/{id}"],
  "locations": [{"path":"src/records.ts","start_line":42,"end_line":48,"symbol":"getRecord"}],
  "evidence": ["src/records.ts:42–48; 查询仅按 id，调用链中未发现租户约束"],
  "trigger": "已登录用户请求属于另一租户的资源 ID。",
  "impact": "可能跨租户读取记录。",
  "root_cause": "授权范围未进入读取条件。",
  "counterevidence": "已检查路由 guard、调用方及数据访问策略；未发现等效保护。",
  "verification": {"method":"static","result":"confirmed","details":"已核对完整调用链；未执行线上请求。"},
  "recommendation": "在拥有此权限规则的规范数据访问层统一施加租户范围。",
  "acceptance_checks": ["本租户访问成功", "跨租户和匿名访问拒绝", "相关列表与详情接口策略一致"],
  "fix_scope": ["资源读取边界", "授权回归测试"],
  "depends_on": [],
  "history": [],
  "rejection_reason": ""
}
```

This is a shape example using `zh-CN`, not a default-language instruction or a finding about the current project. Use actual verified line ranges; omit `start_line`/`end_line` when a location is a whole file or not yet narrowed, and leave `locations` empty for an external object identified by evidence. Never invent code positions. `history` entries, when used, carry commit ID/path/conclusion. `depends_on` contains finding IDs that should be resolved first. Do not treat fix suggestions as already applied or execution steps as already run.

- `status`: `candidate|confirmed|rejected`. A candidate needs a concrete validation next step and blocks closure until confirmed, rejected or converted into an explicit coverage gap. A rejected record needs `id`, `title`, `kind`, `unit_ids`, `evidence` and `rejection_reason`; handoff fields such as `fix_scope` are not required. `rejected` means the suspicion did not hold, never that it was fixed.
- `resolution` (audit-then-fix, after `close-audit`): `{"status": "fixed|deferred|wont_fix", "details": "...", "verification": "..."}` recorded with `apply` `resolve`. `fixed` requires the verification actually run. An earlier audit's fixed findings are summarized in `report.md`, not re-recorded as rejected.
- `priority`: P0 active catastrophic/broad security or data loss; P1 substantial exploitable/correctness/integrity risk; P2 material bounded defect or evidenced maintainability debt; P3 minor actionable improvement. Priority comes from impact, not strictness, file length or speculation. Development-only dependencies and one-off maintenance scripts rarely exceed P2 unless they are reachable in production or exploitable. Optional architectural opportunities must say so and not imply a proven defect.
- `kind` and `quality_dimensions` are required under the current quality contract. Debt/opportunities also require `tradeoffs` and `behavior_to_preserve`. Use existing `impact`, `recommendation` and `acceptance_checks` to explain concrete cost, simpler design and verification; see code-quality.md.
- `category`: descriptive English term such as `correctness`, `authorization`, `data-integrity`, `reliability`, `maintainability`, `accessibility`, `performance`, `delivery`.
- `confidence`: `high|medium|low`; insufficient evidence remains candidate or a coverage gap.
- `counterevidence` states what was checked for this finding (guards, callers, constraints, tests) and why it does not prevent the issue. A sentence shared by many findings is a template, not counterevidence.
- `verification.method`: `static|test|runtime|history|mixed`; `result` and details state observed verification honestly, including what was not executed.

## Report structure

1. Scope, root(s), snapshot, output language, runtime scope, and result `complete`, `complete_with_limitations` or `in_progress`. Distinguish audit completion from quality approval; no unsupported "safe to ship" verdict.
2. Findings ordered by impact, with counts for each kind. Explain trigger, impact, root cause, evidence and remedy, with direct locations. Link the full generated quality report: it contains every confirmed item, even if the synthesis highlights only the most important ones. Do not replace the detailed debt/improvement catalog with a few vague paragraphs.
3. Coverage table per surface: discovery status, known units/checks, reviewed, unreviewable, pending/stale, not applicable, actual reviewed coverage. Unknown totals stay unknown. Keep static, file, runtime and cross-reference figures distinct. Break down application-defined and framework-generated API methods. Describe material traceability limitations if batch summaries cannot substantiate individual check outcomes; do not let a bookkeeping pass conceal them.
4. Explicit limitations: each affected unit/check or missing inventory area, reason, impact, unblock action. Include source/build mismatch and omitted runtime scope. Do not hide these in a footnote while claiming 100%.
5. Cross-reference conclusions, commands actually run and their outcomes; distinguish failed environment setup from application failure. Link evidence and describe targeted history conclusions when used.
6. Remediation (audit-then-fix): what was fixed and how each fix was verified, what was deferred or declined and why, and the post-fix check result. Otherwise, fix-agent handoff: stable finding IDs, affected units/paths, dependencies, suggested fix scope, invariants to preserve, acceptance/regression checks and unresolved questions. Prioritize shared root causes before local symptoms. The fixing agent must recheck the snapshot and findings before changes; the handoff is not authorization to deploy or mutate external systems.

End with the artifact locations, a direct link to code-quality.md and, if unfinished, the exact continuation invocation/state directory. Do not include credentials, raw personal data or unnecessary source dumps.
