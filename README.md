# full-repo-audit

English · [简体中文](README.zh-CN.md)

**Coverage-driven whole-repository audit for Codex.**

Review the current complete project, including old and unchanged code. Build an inventory, inspect each applicable page, route, API, database object, permission policy and background job, persist evidence, resume interrupted batches, and finish with cross-reference checks.

The default is **report-only**. Instructions and machine-readable keys stay in English; reports follow the user's language automatically. Code symbols, paths, commands and error messages remain unchanged.

## Install

Requires Python 3.10+. The installer and audit helper use only the standard library. Playwright, external model APIs and deployment credentials are not required. Installation and automated checks currently cover macOS and Linux.

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

A linked installation follows checkout changes and requires the checkout to remain in place. Use `--codex-home /path/to/codex` for another configuration directory. Reopen Codex if its Skill list has not refreshed.

## Use

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

`runtime_audit=auto` uses a suitable existing environment. `off` selects static review. `on` includes the requested runtime checks; unavailable prerequisites remain explicit limitations while independent static work continues.

## Language behavior

`output_language=auto` is the default. Codex uses an explicit language request first, preserves a resumed audit's language unless asked to change it, then follows applicable user/session preferences and the user's substantive conversation. Pasted source, paths and the stock English invocation prompt are not language preferences. With no language context, the fallback is English.

The resolved language is saved in `config.resolved_output_language`. Set `output_language=zh-CN`, `en`, `ja`, `pt-BR`, etc. to override auto behavior. Existing explicit-language ledgers remain compatible. You do not need to repeat a known language preference in every request.

The standalone Python helper cannot read a conversation. Codex passes its decision through `--resolved-output-language`; a manual CLI call without that hint falls back to `en`. Initial resume scaffolds are English or Simplified Chinese; the agent localizes them to the selected language before delivery.

## Coverage and completion

Inventory spans files, pages, routes, APIs, databases, permissions, jobs, components, modules, integrations, tests, delivery configuration, optional runtime checks and final cross-reference flows. Framework-generated methods such as HEAD/OPTIONS are distinguished from application-defined handlers.

| Result | Meaning |
|---|---|
| `complete` | All applicable review checks and discovery are closed, with 100% actual review coverage and no pending or stale work. |
| `complete_with_limitations` | All reviewable work is done; remaining gaps explicitly record scope, reason, impact and how to unblock them. |
| `in_progress` | Review work, snapshot reconciliation or bookkeeping remains incomplete. |

Unreviewable checks never count as reviewed. Unknown denominators stay `unknown`. File accountability, semantic coverage, runtime scope and cross-reference coverage are reported separately. Audit completion does not imply quality approval or that findings are fixed.

Every check needs a concrete observation or a precise section/case reference. `evidence_reuse` highlights identical evidence shared across units for inspection; legitimate shared proof is allowed and reuse alone does not fail the gate. The helper validates bookkeeping, not the truth of reasoning or completeness of semantic discovery.

## Artifacts and handoff

State is stored outside the repository by default, under `$CODEX_HOME/audits/<repo-name>-<root-path-hash>/<audit-id>/` (`~/.codex` when unset), or at an explicit destination.

| Artifact | Purpose |
|---|---|
| `ledger.json` | Inventory, source snapshot, dependencies, checks and evidence |
| `findings.json` | Stable IDs, impact, root cause, locations, verification and acceptance checks |
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
- [Optional runtime audit](skills/full-repo-audit/references/runtime-audit.md)

## Helper CLI

Codex normally runs these commands. Replace the example paths with the actual root and an external state directory:

```bash
python3 skills/full-repo-audit/scripts/audit_state.py init \
  --root /path/to/project --state-dir /path/to/audit-state \
  --resolved-output-language en
python3 skills/full-repo-audit/scripts/audit_state.py check \
  --state-dir /path/to/audit-state
```

`check` exits with `0` when the bookkeeping gate passes (possibly with limitations), `2` for incomplete/invalid review state, and `1` for input or execution failure. Read the JSON status and limitations, not only the exit code.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python tools/validate_skill.py
.venv/bin/python -m unittest discover -s tests -v
```

PyYAML is a development-only validation dependency. Tests use isolated temporary directories; they do not modify the real Codex installation or project data. CI runs the same checks on Linux and macOS.

Keep instructions, check names and output contracts consistent. Add behavioral tests for changed completion or installation behavior. Do not commit real audit artifacts, credentials, personal machine paths or temporary work. Validation of this package does not guarantee review quality for every large project or browser environment.
