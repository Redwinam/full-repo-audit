#!/usr/bin/env python3
"""Seed audit state and verify coverage bookkeeping. Never review or edit source."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


CHECKS = {
    "file": ["classification"],
    "page": ["behavior", "states", "access", "ux_accessibility", "contracts", "maintainability"],
    "route": ["registration", "access", "navigation"],
    "api": ["authn_authz", "validation", "contracts", "side_effects", "resilience"],
    "database": ["integrity", "access", "lifecycle", "performance"],
    "permission": ["allow_deny", "tenant_boundary", "bypass"],
    "job": ["registration", "idempotency", "failure_recovery", "concurrency", "privilege"],
    "component": ["behavior", "accessibility", "maintainability"],
    "module": ["contracts", "maintainability", "failure_modes"],
    "integration": ["contracts", "resilience", "trust"],
    "test": ["risk_coverage", "reliability"],
    "delivery": ["build_config", "security_config", "operations"],
    "runtime": ["observations", "negative_cases", "console_network"],
    "cross_reference": ["end_to_end", "consistency"],
}
STATES = {"pending", "in_progress", "stale", "reviewed", "unreviewable", "not_applicable"}


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    fd, name = tempfile.mkstemp(prefix=".audit-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def git(root, *args):
    try:
        proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                              env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
        return proc.stdout if proc.returncode == 0 else None
    except FileNotFoundError:
        return None


def relative_path(value):
    return (isinstance(value, str) and bool(value) and not Path(value).is_absolute()
            and ".." not in Path(value).parts and ".git" not in Path(value).parts
            and value != ".")


def snapshot(root, state_dir, extra_paths=()):
    root, state_dir = root.resolve(), state_dir.resolve()
    if not root.is_dir():
        raise ValueError("Audit root is not a directory")
    if root == state_dir or state_dir in root.parents:
        raise ValueError("State directory cannot equal or contain the audit root")
    top = git(root, "rev-parse", "--show-toplevel")
    if top and Path(os.fsdecode(top).strip()).resolve() != root:
        raise ValueError("Use the Git repository root, not a subdirectory")
    listed = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard") if top else None
    names = set()
    if listed is not None:
        names.update(os.fsdecode(p) for p in listed.split(b"\0") if p)
        method = "git tracked + non-ignored untracked; ignored files/submodules require reconciliation"
    else:
        method = "filesystem walk excluding .git and audit state; no Git history available"
        def walk_error(error):
            raise error
        for parent, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
            base = Path(parent)
            dirs[:] = [d for d in dirs if d != ".git" and (base / d).resolve() != state_dir]
            for d in list(dirs):
                if (base / d).is_symlink():
                    names.add((base / d).relative_to(root).as_posix())
                    dirs.remove(d)
            names.update((base / f).relative_to(root).as_posix() for f in files)
    for name in extra_paths:
        if not relative_path(name):
            raise ValueError("extra_paths must contain safe root-relative file paths")
        names.add(name)
    files = {}
    for name in sorted(names):
        path = root / name
        if path == state_dir or state_dir in path.parents:
            continue
        # Do not traverse a directory symlink outside the audit root.
        if any(p.is_symlink() for p in path.parents if p != root and root in p.parents):
            files[name] = "symlink-parent-boundary"
            continue
        try:
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                digest = "symlink:" + hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
            elif stat.S_ISREG(info.st_mode):
                h = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        h.update(chunk)
                digest = f"file:{stat.S_IMODE(info.st_mode):o}:{h.hexdigest()}"
            elif stat.S_ISDIR(info.st_mode):
                digest = "directory-boundary:review-as-separate-root"
            else:
                digest = "special-file:unread"
        except OSError as error:
            digest = "unreadable:" + type(error).__name__
        files[name] = digest
    head = git(root, "rev-parse", "--verify", "HEAD") if top else None
    encoded = json.dumps(files, sort_keys=True, ensure_ascii=True).encode()
    return {"head": os.fsdecode(head).strip() if head else None,
            "fingerprint": hashlib.sha256(encoded).hexdigest(), "files": files, "method": method}


def unit(surface, label, sources):
    return {"id": f"{surface}:{label}", "surface": surface, "label": label,
            "sources": sources, "depends_on": [],
            "checks": {name: {"status": "pending", "evidence": []} for name in CHECKS[surface]}}


def initialize(args):
    root, state = args.root.resolve(), args.state_dir.resolve()
    if state.exists() and any(state.iterdir()):
        raise ValueError("State directory is not empty; resume it or choose a new audit ID")
    snap = snapshot(root, state)
    ledger = {"schema_version": 1, "audit_id": state.name, "root": str(root),
              "config": {"output_language": args.output_language, "mode": "report-only",
                         "runtime_audit": args.runtime, "batch_target_units": 15},
              "extra_paths": [], "snapshot": snap,
              "surfaces": {s: {"status": "pending", "evidence": []} for s in CHECKS},
              "units": [unit("file", p, [p]) for p in snap["files"]]}
    state.mkdir(parents=True, exist_ok=True)
    (state / "batches").mkdir()
    atomic_json(state / "ledger.json", ledger)
    atomic_json(state / "findings.json", {"schema_version": 1, "findings": []})
    (state / "resume.md").write_text(
        "# 审查续审位置\n\n状态：in_progress\n\n已建立文件清单；尚未进行语义 inventory 或审查。下一步：核对各审查面注册入口，补齐 units 与 discovery 证据。\n"
        if args.output_language == "zh-CN" else
        "# Resume\n\nStatus: in_progress. File manifest seeded; semantic discovery and review have not started. Reconcile registries and add semantic units next.\n",
        encoding="utf-8")
    return {"state_dir": str(state), "files": len(snap["files"]), "status": "in_progress"}


def validate(ledger, findings, current):
    errors, gaps, exclusions = [], [], []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def filled(value):
        return isinstance(value, str) and bool(value.strip())

    def strings(value):
        return isinstance(value, list) and bool(value) and all(filled(x) for x in value)

    def evidence(record, label):
        require(strings(record.get("evidence")), f"{label}: specific evidence required")

    def limitation(record, label):
        evidence(record, label)
        for key in ("reason", "impact", "unblock"):
            require(filled(record.get(key)), f"{label}: {key} required")
        gaps.append({"id": label, **{k: record.get(k) for k in ("reason", "impact", "unblock")}})

    require(ledger.get("schema_version") == 1, "Unsupported ledger schema_version")
    config = ledger.get("config", {})
    require(config.get("mode") == "report-only", "This audit contract requires report-only mode")
    require(config.get("runtime_audit") in {"off", "auto", "on"}, "Invalid runtime_audit")
    require(filled(config.get("output_language")), "output_language required")
    saved = ledger["snapshot"]
    drift = saved.get("fingerprint") != current["fingerprint"] or saved.get("head") != current["head"]
    changed_paths = sorted(p for p in set(saved["files"]) | set(current["files"])
                           if saved["files"].get(p) != current["files"].get(p))
    require(not drift, "Snapshot changed: reconcile changed units/consumers before accepting a new snapshot")
    require(saved.get("files") == current["files"], "Saved manifest differs from current files")
    surfaces = ledger.get("surfaces", {})
    require(set(surfaces) == set(CHECKS), "All fixed discovery surfaces must be present exactly once")
    units = ledger.get("units", [])
    require(isinstance(units, list), "units must be an array")
    ids = [u["id"] for u in units]
    require(all(filled(x) for x in ids) and len(ids) == len(set(ids)), "Unit IDs must be nonempty and unique")
    id_set = set(ids)
    by_surface = {s: [] for s in CHECKS}
    mapped_files = set()
    counts = {s: {x: 0 for x in STATES} for s in CHECKS}
    for u in units:
        label, surface = u["id"], u.get("surface")
        require(surface in CHECKS, f"{label}: invalid surface")
        if surface not in CHECKS:
            continue
        by_surface[surface].append(u)
        require(filled(u.get("label")), f"{label}: label required")
        sources = u.get("sources", [])
        require(isinstance(sources, list), f"{label}: sources must be an array")
        for path in sources:
            require(relative_path(path) and path in saved["files"], f"{label}: source absent from manifest: {path}")
        if surface == "file":
            require(len(sources) == 1, f"{label}: file unit must name exactly one source")
            require(not mapped_files.intersection(sources), f"{label}: duplicate file classification")
            mapped_files.update(sources)
        dependencies = u.get("depends_on", [])
        require(isinstance(dependencies, list) and all(d in id_set and d != label for d in dependencies),
                f"{label}: unknown/self dependency")
        checks = u.get("checks", {})
        require(set(CHECKS[surface]).issubset(checks), f"{label}: missing required checks")
        for name, check in checks.items():
            ref, status = f"{label}/{name}", check.get("status")
            require(status in STATES, f"{ref}: invalid status")
            if status not in STATES:
                continue
            counts[surface][status] += 1
            if status in {"pending", "in_progress", "stale"}:
                errors.append(f"{ref}: unfinished ({status})")
            elif status == "unreviewable":
                limitation(check, ref)
            elif status == "not_applicable":
                evidence(check, ref)
                require(filled(check.get("reason")), f"{ref}: not_applicable reason required")
                exclusions.append({"id": ref, "reason": check.get("reason"), "evidence": check.get("evidence")})
            else:
                evidence(check, ref)
    require(mapped_files == set(saved["files"]), "Every manifest file needs exactly one classification unit")
    coverage = {}
    for surface in CHECKS:
        record = surfaces.get(surface, {})
        discovery = record.get("status", "pending")
        require(discovery in {"pending", "complete", "not_applicable", "unreviewable"}, f"{surface}: invalid discovery status")
        if discovery == "pending":
            errors.append(f"{surface}: discovery not reconciled")
        elif discovery == "unreviewable":
            limitation(record, f"discovery:{surface}")
        else:
            evidence(record, f"discovery:{surface}")
        if discovery == "complete":
            require(bool(by_surface[surface]), f"{surface}: complete discovery needs units; justify absence instead")
        if discovery == "not_applicable":
            require(filled(record.get("reason")), f"{surface}: absence reason required")
            require(not by_surface[surface], f"{surface}: absent surface cannot have units")
            exclusions.append({"id": f"discovery:{surface}", "reason": record.get("reason"), "evidence": record.get("evidence")})
        if surface == "runtime":
            require(not (config.get("runtime_audit") == "on" and discovery == "not_applicable"),
                    "runtime=on cannot be silently excluded")
            require(not (config.get("runtime_audit") == "off" and by_surface[surface]),
                    "runtime=off conflicts with runtime units")
        c = counts[surface]
        applicable = sum(c.values()) - c["not_applicable"]
        def pct(n):
            if not applicable:
                return None
            # Never display 100% when a large denominator hides a small gap.
            return 100.0 if n == applicable else min(99.99, round(100 * n / applicable, 2))
        known = pct(c["reviewed"])
        coverage[surface] = {"discovery": discovery, "units": len(by_surface[surface]),
                             "counts": c, "applicable_checks": applicable,
                             "reviewed_coverage": "unknown" if discovery in {"pending", "unreviewable"} else known,
                             "known_reviewed_coverage": known,
                             "accounted_coverage": "unknown" if discovery in {"pending", "unreviewable"}
                             else pct(c["reviewed"] + c["unreviewable"]),
                             "known_accounted_coverage": pct(c["reviewed"] + c["unreviewable"])}
    semantic_units = any(by_surface[s] for s in CHECKS if s not in {"file", "runtime", "cross_reference"})
    require(not semantic_units or bool(by_surface["cross_reference"]),
            "Semantic review requires explicit cross_reference units, including any unavailable boundaries")
    require(findings.get("schema_version") == 1, "Unsupported findings schema_version")
    records = findings.get("findings", [])
    finding_ids = [f["id"] for f in records]
    require(len(finding_ids) == len(set(finding_ids)), "Duplicate finding IDs")
    required_text = ("id", "title", "trigger", "impact", "root_cause", "counterevidence", "recommendation")
    for f in records:
        ref = f["id"]
        for key in required_text:
            require(filled(f.get(key)), f"{ref}: {key} required")
        require(f.get("status") in {"candidate", "confirmed", "rejected"}, f"{ref}: invalid finding status")
        require(f.get("status") != "candidate", f"{ref}: unresolved candidate")
        require(f.get("priority") in {"P0", "P1", "P2", "P3"}, f"{ref}: invalid priority")
        require(f.get("confidence") in {"high", "medium", "low"}, f"{ref}: invalid confidence")
        require(filled(f.get("category")), f"{ref}: category required")
        evidence(f, ref)
        require(strings(f.get("unit_ids")) and all(x in id_set for x in f.get("unit_ids", [])), f"{ref}: valid unit_ids required")
        for key in ("acceptance_checks", "fix_scope"):
            require(strings(f.get(key)), f"{ref}: {key} required")
        require(all(x in finding_ids and x != ref for x in f.get("depends_on", [])), f"{ref}: invalid finding dependency")
        verification = f.get("verification", {})
        require(verification.get("method") in {"static", "test", "runtime", "history", "mixed"}
                and filled(verification.get("result")) and filled(verification.get("details")), f"{ref}: verification required")
        require(isinstance(f.get("locations"), list), f"{ref}: locations must be an array")
        for loc in f.get("locations", []):
            require(loc.get("path") in saved["files"], f"{ref}: location path absent from manifest")
            start, end = loc.get("start_line"), loc.get("end_line")
            require(isinstance(start, int) and not isinstance(start, bool) and isinstance(end, int)
                    and not isinstance(end, bool) and 1 <= start <= end, f"{ref}: invalid line range")
        if f.get("status") == "rejected":
            require(filled(f.get("rejection_reason")), f"{ref}: rejection_reason required")
    for u in units:
        require(all(x in finding_ids for x in u.get("finding_ids", [])), f"{u['id']}: unknown finding_ids")
    return {"schema_version": 1, "generated_at": now(), "audit_id": ledger.get("audit_id"),
            "status": "in_progress" if errors else ("complete_with_limitations" if gaps else "complete"),
            "quality_approval": "not_implied", "snapshot_changed": drift, "changed_paths": changed_paths,
            "source_snapshot": {"root": ledger["root"], "head": saved.get("head"), "fingerprint": saved.get("fingerprint")},
            "surfaces": coverage, "limitations": gaps, "exclusions": exclusions, "errors": errors,
            "finding_counts": {s: sum(f.get("status") == s for f in records)
                               for s in ("confirmed", "candidate", "rejected")}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "snapshot", "check"):
        command = sub.add_parser(name)
        command.add_argument("--state-dir", type=Path, required=True)
        if name != "check":
            command.add_argument("--root", type=Path, required=True)
        if name == "init":
            command.add_argument("--output-language", default="zh-CN")
            command.add_argument("--runtime", choices=("off", "auto", "on"), default="auto")
    args = parser.parse_args()
    state = args.state_dir.resolve()
    try:
        if args.command == "init":
            result = initialize(args)
        else:
            ledger_path = state / "ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {}
            root = Path(ledger["root"]).resolve() if args.command == "check" else args.root.resolve()
            current = snapshot(root, state, ledger.get("extra_paths", []))
            if args.command == "snapshot":
                result = current
            else:
                findings = json.loads((state / "findings.json").read_text(encoding="utf-8"))
                result = validate(ledger, findings, current)
                atomic_json(state / "coverage.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if args.command == "check" and result["status"] == "in_progress" else 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        failure = {"status": "in_progress", "errors": [f"Invalid state or execution failure: {error}"]}
        if args.command == "check" and state.is_dir():
            atomic_json(state / "coverage.json", failure)
        print(json.dumps(failure, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
