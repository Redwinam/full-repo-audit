# Output contract and fix-agent handoff

Use schema keys/status values in English. Narrative fields and Markdown use the concrete `config.resolved_output_language` when `config.output_language=auto` (the default), or the explicitly configured language otherwise. Follow SKILL.md to resolve the user's preference; existing explicit-language ledgers remain valid. Keep symbols, commands, paths, errors and identifiers unchanged. Paths are repository-relative in JSON plus the ledger's absolute root; report links should resolve for the user.

## Artifacts

- `ledger.json`: authoritative inventory, source snapshot, dependencies, checks and limitations.
- `findings.json`: `{"schema_version":1,"findings":[]}`. Empty findings are valid; they do not prove full coverage.
- `code-quality.json` and `code-quality.md`: helper-generated complete views of the canonical catalog, grouped as defects, maintenance debt and optional improvements, with the quality matrix and limitations. Read [code-quality.md](code-quality.md) for required fields and migration. Never maintain a second independent finding list.
- `coverage.json`: machine-generated gate result, per-surface counts, explicit gaps, validation errors and source drift. Do not edit it to improve results.
- `batches/<batch-id>.md`: actual work/evidence, commands and exit outcomes, candidate verification, limitations and next units. Redact sensitive outputs.
- `resume.md`: exact resumable position and outstanding work; after closure say which follow-up work belongs to a separate fixing task.
- `report.md`: user-facing review and handoff. Link the machine artifacts and supporting evidence.

## Finding schema

Every record has a stable ID. Preserve IDs across resume/revalidation; merge duplicates using a canonical finding and related IDs. One root cause can affect many units. Store candidates/rejections as well as confirmed records; only confirmed records appear in the main defect list.

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

This is a shape example using `zh-CN`, not a default-language instruction or a finding about the current project. Use actual verified line ranges. `locations` may be empty for an external object if evidence gives its stable identity; never invent code positions. `history` entries, when used, carry commit ID/path/conclusion. `depends_on` contains finding IDs that should be resolved first. Do not treat fix suggestions as already applied or execution steps as already run.

- `status`: `candidate|confirmed|rejected`. A candidate needs a concrete validation next step and prevents audit closure until confirmed/rejected or converted to an explicit unreviewable coverage gap. Rejection needs `rejection_reason` and counterevidence; retaining its trail is useful.
- `priority`: P0 active catastrophic/broad security or data loss; P1 substantial exploitable/correctness/integrity risk; P2 material bounded defect or evidenced maintainability debt; P3 minor actionable improvement. Priority comes from impact, not Grok strictness, file length or speculation. Optional architectural opportunities must say so and not imply a proven defect.
- `kind` and `quality_dimensions` are required under the current quality contract. Debt/opportunities also require `tradeoffs` and `behavior_to_preserve`. Use existing `impact`, `recommendation` and `acceptance_checks` to explain concrete cost, simpler design and verification; see code-quality.md.
- `category`: descriptive English term such as `correctness`, `authorization`, `data-integrity`, `reliability`, `maintainability`, `accessibility`, `performance`, `delivery`.
- `confidence`: `high|medium|low`; insufficient evidence remains candidate or a coverage gap. Do not promote guesses to confirmed to meet a quota.
- `verification.method`: `static|test|runtime|history|mixed`; `result` and details state observed verification honestly, including what was not executed.

## Report structure

1. Scope, root(s), snapshot, output language, runtime scope, and result `complete`, `complete_with_limitations` or `in_progress`. Distinguish audit completion from quality approval; no unsupported "safe to ship" verdict.
2. Findings ordered by impact, with counts for each kind. Explain trigger, impact, root cause, evidence and remedy, with direct locations. Link the full generated quality report: it contains every confirmed item, even if the synthesis highlights only the most important ones. Do not replace the detailed debt/improvement catalog with a few vague paragraphs.
3. Coverage table per surface: discovery status, known units/checks, reviewed, unreviewable, pending/stale, not applicable, actual reviewed coverage. Unknown totals stay unknown. Keep static, file, runtime and cross-reference figures distinct. Break down application-defined and framework-generated API methods. Describe material traceability limitations if batch summaries cannot substantiate individual check outcomes; do not let a bookkeeping pass conceal them.
4. Explicit limitations: each affected unit/check or missing inventory area, reason, impact, unblock action. Include source/build mismatch and omitted runtime scope. Do not hide these in a footnote while claiming 100%.
5. Cross-reference conclusions, commands actually run and their outcomes; distinguish failed environment setup from application failure. Link evidence and describe targeted history conclusions when used.
6. Fix-agent handoff: stable finding IDs, affected units/paths, dependencies, suggested fix scope, invariants to preserve, acceptance/regression checks and unresolved questions. Prioritize shared root causes before local symptoms. The fixing agent must recheck the snapshot and findings before changes; the handoff is not authorization to deploy or mutate external systems.

End with the artifact locations, a direct link to code-quality.md and, if unfinished, the exact continuation invocation/state directory. Do not include credentials, raw personal data or unnecessary source dumps.
