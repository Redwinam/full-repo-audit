# full-repo-audit

**Coverage-driven whole-repository audit for Codex.**

以覆盖率驱动的全仓库审查 Skill：从当前完整项目建立 inventory，逐页面、路由、API、数据库对象、权限策略和后台任务审查，分批记录证据，支持中断续审，最后做跨模块核对。

默认只报告、不修改代码。机器指令和固定术语使用英文；报告、finding 解释与建议默认简体中文，可设置 `output_language`。代码符号、路径、命令与错误文本保持原文。

## 安装

需要 Python 3.10+。安装工具和审查账本工具只使用标准库；不要求 Playwright、外部模型 API 或部署凭据。当前安装与自动测试支持 macOS 和 Linux。

```bash
git clone https://github.com/Redwinam/full-repo-audit.git
cd full-repo-audit
python3 tools/install_skill.py
```

默认将 `skills/full-repo-audit/` 复制到 `${CODEX_HOME:-~/.codex}/skills/full-repo-audit/`。已有安装时不会覆盖。更新时使用：

```bash
python3 tools/install_skill.py --replace
```

旧版本会保存在 Codex 目录的 `skill-backups/` 下；安装工具输出准确位置，不删除旧版本。备份不放在 `skills/` 内，避免被重复发现。

维护本仓库时，可以把安装改为指向当前 checkout 的符号链接：

```bash
python3 tools/install_skill.py --link --replace
```

此后当前 checkout 的修改会直接用于 Skill；移动或删除 checkout 会使链接失效。使用 `--codex-home /path/to/codex` 可指定另一个 Codex 配置目录。若界面暂未显示 Skill，可重新打开 Codex。

## 调用

在待审项目的 Codex 任务中输入：

```text
使用 $full-repo-audit 对当前项目做完整全仓库审查，只报告不修改代码，输出中文 findings 和 coverage 报告。
```

仅静态审查：

```text
使用 $full-repo-audit 审查当前完整项目，runtime_audit=off。
```

要求运行时审查：

```text
使用 $full-repo-audit 审查当前完整项目，runtime_audit=on。无法执行的检查逐项列为限制，同时继续完成其他静态审查。
```

续审：

```text
使用 $full-repo-audit 继续上次审查，state-dir 为上次报告中的目录。先核对代码快照，再从 ledger.json 和 resume.md 中的未完成项继续。
```

## 配置与输出

| 配置 | 默认值 | 含义 |
|---|---|---|
| `output_language` | `zh-CN` | 用户可读内容的语言，例如 `en` |
| `mode` | `report-only` | 只写审查产物；修复是独立任务 |
| `runtime_audit` | `auto` | `off` 仅静态；`auto` 使用现有适合的环境；`on` 将请求的运行时范围纳入必要检查 |
| `batch_target_units` | `15` | 每批的起始规模，按复杂度调整，不裁剪全库范围 |

默认状态目录位于仓库外的 `$CODEX_HOME/audits/<repo-name>-<root-path-hash>/<audit-id>/`，未设置 `CODEX_HOME` 时使用 `~/.codex`。也可以明确指定产物目录。

| 产物 | 用途 |
|---|---|
| `ledger.json` | inventory、文件快照、对象依赖、逐项状态和证据 |
| `findings.json` | 稳定 finding ID、影响、根因、位置、验证与修复验收要求 |
| `coverage.json` | 各审查面的真实覆盖率、未知范围、限制与完成门槛结果 |
| `report.md` | 面向用户的结论和修复交接 |
| `resume.md` | 精确续审位置、未完成项和下一步 |
| `batches/*.md` | 每批实际检查和命令结果 |

## 覆盖率与完成门槛

覆盖范围包括文件、页面、路由、API、数据库、权限、后台任务、组件、模块、集成、测试、交付、可选 runtime 和最终 cross-reference。文件分类覆盖率与语义审查覆盖率分别记录；测试文件已审查也不等于产品测试覆盖率。

- `complete`：所有适用审查面实际覆盖 100%，inventory 和跨模块检查闭合，没有待审、过期检查或未决候选问题。
- `complete_with_limitations`：所有可审查部分完成，剩余部分逐项说明范围、原因、影响及解除条件。不可审查项不计为已审查，未知总量显示 `unknown`。
- `in_progress`：仍有未完成工作或无效账本。留下 checkpoint 后可继续。

审查完成不代表项目质量通过，也不代表发现的问题已经修复。源文件快照变化会阻止结案；续审时必须核对变更并重审受影响对象及其消费者。

辅助脚本只负责文件清单、指纹和账本校验。语义 inventory、证据质量、跨模块推理仍由审查 agent 完成，不能靠填满状态字段证明审查质量。

## 审查标准

保留严格代码质量审查中的结构简化（code judo）、减少特殊分支、类型边界、规范 helper 复用、职责归属、合理并发和原子性检查。千行文件是重点检查信号，结合内聚性和职责判断；不机械按行数判错。严重安全、正确性、数据完整性问题按实际影响优先。

这些标准受设计时提供的 Grok `Strict Code Quality Review` 文本启发，已改写并扩展为全库流程；仓库不包含该来源全文，也不声称与 Grok 或 Cursor 官方存在关联。

详细协议：

- [Skill 入口](skills/full-repo-audit/SKILL.md)
- [审查标准](skills/full-repo-audit/references/review-standards.md)
- [覆盖率与续审协议](skills/full-repo-audit/references/coverage-protocol.md)
- [输出与修复交接](skills/full-repo-audit/references/output-contract.md)
- [可选运行时审查](skills/full-repo-audit/references/runtime-audit.md)

## 手动检查账本

通常由 Codex 根据 Skill 调用。以下路径需替换为实际项目根目录和仓库外状态目录：

```bash
python3 skills/full-repo-audit/scripts/audit_state.py init \
  --root /path/to/project --state-dir /path/to/audit-state
python3 skills/full-repo-audit/scripts/audit_state.py check \
  --state-dir /path/to/audit-state
```

`check` 的退出码：`0` 表示账本完成门槛通过（可能包含明确限制），`2` 表示未完成或校验不通过，`1` 表示输入/执行失败。必须同时读取 JSON 的 `status` 和限制清单。

## 开发与验证

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python tools/validate_skill.py
.venv/bin/python -m unittest discover -s tests -v
```

`PyYAML` 仅用于仓库开发验证，不是已安装 Skill 的运行依赖。测试使用隔离临时目录，不修改真实 Codex 安装或目标项目。CI 在 Linux/macOS 执行相同检查。

改动审查规则时，保持机器协议字段稳定；行为变化应有可观察结果或完成门槛的测试。检查项、账本协议和输出说明需同步。提交前不要包含真实审查报告、凭据、账户数据、本机路径或临时工作文件。

已有验证覆盖：结构和引用校验、覆盖率与中断/漂移边界、安装备份/回退，以及独立小样例的真实全库审查。大型真实项目和具体浏览器环境仍需在使用时验证，不能由样例推断全面有效。
