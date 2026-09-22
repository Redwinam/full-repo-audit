# full-repo-audit

English · [简体中文](README.zh-CN.md)

**Coverage-driven whole-repository audit for Codex and Claude Code.**

Review the current complete project, including old and unchanged code. Build an inventory, inspect each applicable page, route, API, database object, permission policy and background job, persist evidence, resume interrupted batches, and finish with cross-reference checks.

The default is **report-only**. Asking it to fix what it finds switches to **audit-then-fix**: the audit closes first, then each finding is fixed and recorded with how the fix was verified. Instructions and machine-readable keys stay in English; reports follow the user's language automatically. Code symbols, paths, commands and error messages remain unchanged.

Code quality has a dedicated, complete report: confirmed defects, maintainability debt, and optional structural improvements. A concise chat summary never replaces the full item-by-item catalog.

## Install

Requires Python 3.10+. The installer and audit helper use only the standard library. Playwright, external model APIs and deployment credentials are not required. Installation and automated checks currently cover macOS and Linux.

Both hosts share one `skills/full-repo-audit/`, so the review rules are maintained once. Host differences stay at the edges: `.codex-plugin/` with `.agents/plugins/` and `.claude-plugin/` make this repository installable as a plugin in each host, and `agents/openai.yaml` serves the Codex UI.

### Claude Code

Install as a plugin from within Claude Code:

```text
/plugin marketplace add Redwinam/full-repo-audit
/plugin install full-repo-audit@full-repo-audit
```

The plugin invocation is `/full-repo-audit:full-repo-audit`. Alternatively, copy it into `${CLAUDE_CONFIG_DIR:-~/.claude}/skills/`, where it is invoked as `/full-repo-audit`:

```bash
python3 tools/install_skill.py --agent claude
```

`--replace` and `--link` work as described for Codex below; add `--agent claude`.

### Codex

Install as a plugin from GitHub:

```bash
codex plugin marketplace add Redwinam/full-repo-audit
codex plugin add full-repo-audit@full-repo-audit
```

To upgrade later, refresh the snapshot and install again:

```bash
codex plugin marketplace upgrade full-repo-audit
codex plugin add full-repo-audit@full-repo-audit
```

Alternatively, copy the Skill with the installer:

```bash
git clone https://github.com/Redwinam/full-repo-audit.git
cd full-repo-audit
python3 tools/install_skill.py
```

This copies `skills/full-repo-audit/` into the `skills/` directory under `CODEX_HOME`, or `~/.codex` when unset. Existing installations are protected. To update with a backup:

```bash
python3 tools/install_skill.py --replace
```

Backups go to `skill-backups/` outside Skill discovery. The installer prints their exact paths. To use this checkout as the maintained source:

```bash
python3 tools/install_skill.py --link --replace
```

A linked installation follows checkout changes and requires the checkout to remain in place. Use `--home /path/to/dir` (the older `--codex-home` still works) for another configuration directory. Reopen Codex if its Skill list has not refreshed.

## Use

Examples use the Codex `$full-repo-audit` form. In Claude Code use `/full-repo-audit` (`/full-repo-audit:full-repo-audit` when installed as a plugin), or simply ask for a whole-repository audit.

In the project to review, ask Codex in your preferred language:

```text
Use $full-repo-audit to audit this entire project. Report findings and coverage without changing application code.
```

Optional settings:

```text
Use $full-repo-audit with runtime_audit=off.
Use $full-repo-audit with runtime_audit=on and output_language=ja.
Use $full-repo-audit to resume the audit at the state-dir from the previous report. Reconcile the snapshot before continuing pending units.
```

`runtime_audit=auto` uses a suitable existing environment. `off` selects static review. `on` includes the requested runtime checks; unavailable prerequisites remain explicit limitations while independent static work continues. Under `auto`, missing runtime environments are reported in a separate runtime section and do not downgrade the headline result; only `on` makes them count.

To audit and then fix:

```text
Use $full-repo-audit to audit this entire project, then fix everything it finds.
```

The agent closes the audit before touching source, then records each finding as `fixed` (with the verification run), `deferred` or `wont_fix`.

## Language behavior

`output_language=auto` is the default. The agent uses an explicit language request first, preserves a resumed audit's language unless asked to change it, then follows applicable user/session preferences and the user's substantive conversation. Pasted source, paths and the stock English invocation prompt are not language preferences. With no language context, the fallback is English.

The resolved language is saved in `config.resolved_output_language`. Set `output_language=zh-CN`, `en`, `ja`, `pt-BR`, etc. to override auto behavior. Existing explicit-language ledgers remain compatible. You do not need to repeat a known language preference in every request.

The standalone Python helper cannot read a conversation. The agent passes its decision through `--resolved-output-language`; a manual CLI call without that hint falls back to `en`. Initial resume scaffolds are English or Simplified Chinese; the agent localizes them to the selected language before delivery.

Generated quality-report headings support English and Simplified Chinese directly. For other languages the agent supplies `quality-labels.json` as described in the quality protocol; users do not need to translate it or configure an external service. Finding prose and fixed schema keys retain the same language rules.

## Coverage and completion

Inventory spans files, pages, routes, APIs, databases, permissions, jobs, components, modules, integrations, tests, delivery configuration, optional runtime checks and final cross-reference flows. Framework-generated methods such as HEAD/OPTIONS are distinguished from application-defined handlers.

| Result | Meaning |
|---|---|
| `complete` | All applicable review checks and discovery are closed, with 100% actual review coverage and no pending or stale work. |
| `complete_with_limitations` | All reviewable work is done; remaining gaps explicitly record scope, reason, impact and how to unblock them. |
| `in_progress` | Review work, snapshot reconciliation or bookkeeping remains incomplete. |

Unreviewable checks never count as reviewed. Unknown denominators stay `unknown`. File accountability, semantic coverage, runtime scope and cross-reference coverage are reported separately. Audit completion does not imply quality approval or that findings are fixed.

Every check needs a concrete observation or a precise section/case reference. `evidence_reuse` highlights identical evidence shared across units for inspection; legitimate shared proof is allowed and reuse alone does not fail the gate. The helper validates bookkeeping, not the truth of reasoning or completeness of semantic discovery.

## Dedicated code-quality review

The reviewer checks seven dimensions: structure, ownership, duplication, state/control flow, type contracts, failure/concurrency orchestration, and clarity/dead code. Applicable maintainability units must be represented in these scopes. This is a review matrix, not a numeric quality score.

All identified, evidence-backed, actionable items go into one canonical `findings.json` catalog:

| Kind | What the detailed report records |
|---|---|
| `defect` | Trigger, behavioral impact, root cause, evidence, remedy and acceptance checks |
| `maintainability_debt` | Concrete ongoing maintenance cost, simpler design, tradeoffs and behavior to preserve |
| `improvement_opportunity` | A worthwhile, supported structural improvement, explicitly non-blocking, with scope and verification |

There is no finding quota or top-N cap. Optional improvements are not silently dropped because bugs rank higher. Cosmetic preferences and speculative redesigns are not manufactured into issues. A structural cause attached to a defect keeps that defect's ID rather than becoming a duplicate debt record.

`check` generates `code-quality.md` and `code-quality.json` from the canonical data, retaining every confirmed item and all fields. Missing classification, unreviewed dimensions, missing scope, inconsistent references or unresolved candidates block completion. Unfixed findings do not prevent the review from closing. Fix the source ledger/catalog and regenerate; do not maintain a second report-specific list.

## Artifacts and handoff

State is stored outside the repository by default, under the host agent's home: `<agent-home>/audits/<repo-name>-<root-path-hash>/<audit-id>/`, where `<agent-home>` is `$CODEX_HOME` (`~/.codex` when unset) for Codex and `$CLAUDE_CONFIG_DIR` (`~/.claude` when unset) for Claude Code, or at an explicit destination. Claude Code asks before writing outside the project; use `/add-dir` for that directory before a long audit.

| Artifact | Purpose |
|---|---|
| `ledger.json` | Inventory, source snapshot, dependencies, checks and evidence |
| `findings.json` | Stable IDs, impact, root cause, locations, verification and acceptance checks |
| `code-quality.md` / `code-quality.json` | Complete generated catalog in three sections, quality dimensions, candidates and limitations |
| `coverage.json` | Per-surface counts, gaps, evidence-reuse diagnostics and completion result |
| `report.md` | User-facing review and independent fix-agent handoff |
| `resume.md` | Exact continuation point and next actions |
| `batches/*.md` | Work performed, observations and actual command outcomes |

Source changes require reconciliation and invalidate affected reviews. Findings can remain unfixed when a review closes. Fixing, deployment and external mutations require their own task scope.

## Standards and detailed protocol

The review retains ambitious structural simplification, control of branching complexity, clear types and ownership boundaries, canonical helper reuse, appropriate concurrency and atomicity. A 1,000-line file is an inspection trigger, not an automatic defect. Priorities follow concrete security, correctness, data integrity and maintenance impact.

These standards were informed by a supplied Grok `Strict Code Quality Review` text and rewritten for whole-repository review. The original text is not redistributed here; no official Grok or Cursor affiliation is claimed.

- [Skill entrypoint](skills/full-repo-audit/SKILL.md)
- [Review standards](skills/full-repo-audit/references/review-standards.md)
- [Coverage and resume protocol](skills/full-repo-audit/references/coverage-protocol.md)
- [Output and handoff contract](skills/full-repo-audit/references/output-contract.md)
- [Code-quality catalog and completion protocol](skills/full-repo-audit/references/code-quality.md)
- [Optional runtime audit](skills/full-repo-audit/references/runtime-audit.md)

## Helper CLI

The agent normally runs these commands. Replace the example paths with the actual root and an external state directory:

```bash
python3 skills/full-repo-audit/scripts/audit_state.py init \
  --root /path/to/project --state-dir /path/to/audit-state \
  --resolved-output-language en
python3 skills/full-repo-audit/scripts/audit_state.py apply \
  --state-dir /path/to/audit-state --file ops.jsonl
python3 skills/full-repo-audit/scripts/audit_state.py check \
  --state-dir /path/to/audit-state
```

`check` exits with `0` when the bookkeeping gate passes (possibly with limitations), `2` for incomplete/invalid review state, and `1` for input or execution failure. Read the JSON status and limitations, not only the exit code.

To continue an older audit without `quality_contract_version`, first run:

```bash
python3 skills/full-repo-audit/scripts/audit_state.py upgrade --state-dir /path/to/audit-state
```

The upgrade backs up existing state, preserves source reviews and finding IDs, and adds pending quality dimensions and unclassified existing items for the reviewer. It never guesses debt/defect classifications. Historical legacy checks remain readable but explicitly report `legacy_not_assessed` for the expanded quality track; they do not certify it.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python tools/validate_skill.py
.venv/bin/python -m unittest discover -s tests -v
```

PyYAML is a development-only validation dependency. Tests use isolated temporary directories; they do not modify real Codex or Claude installations or project data. CI runs the same checks on Linux and macOS.

Keep instructions, check names and output contracts consistent. Add behavioral tests for changed completion or installation behavior. Do not commit real audit artifacts, credentials, personal machine paths or temporary work. Validation of this package does not guarantee review quality for every large project or browser environment.
