#!/usr/bin/env python3
"""Install the bundled Skill locally; preserve existing installations as backups."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

NAME = "full-repo-audit"
SOURCE = Path(__file__).resolve().parents[1] / "skills" / NAME


def install(source, codex_home, *, link=False, replace=False):
    source = source.resolve()
    codex_home = codex_home.expanduser().resolve()
    target = codex_home / "skills" / NAME
    if not (source / "SKILL.md").is_file():
        raise ValueError("Source must contain SKILL.md")
    if target.is_symlink() and target.resolve() == source and link:
        return {"status": "unchanged", "target": str(target), "mode": "link"}
    if ((target.resolve() == source and not target.is_symlink())
            or target in source.parents or source in target.parents):
        raise ValueError("Source and destination must not overlap")
    exists = os.path.lexists(target)
    if exists and not replace:
        raise FileExistsError("An installation already exists; use --replace to back it up first")
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    # Stage first so a failed copy cannot displace an existing working Skill.
    with tempfile.TemporaryDirectory(prefix=".skill-install-", dir=codex_home) as staging:
        payload = Path(staging) / NAME
        if link:
            payload.symlink_to(source, target_is_directory=True)
        else:
            shutil.copytree(source, payload, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if exists:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = codex_home / "skill-backups" / f"{NAME}-{stamp}-{uuid.uuid4().hex[:8]}"
            backup.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink():
                old_link = Path(os.readlink(target))
                # Relative links must keep their meaning after moving out of skills/.
                backup.symlink_to(old_link if old_link.is_absolute() else target.parent / old_link,
                                  target_is_directory=True)
                target.unlink()
            else:
                target.rename(backup)
        try:
            os.replace(payload, target)
        except OSError:
            if backup is not None and not os.path.lexists(target):
                backup.rename(target)
            raise
    return {"status": "installed", "target": str(target), "source": str(source),
            "mode": "link" if link else "copy", "backup": str(backup) if backup else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path,
                        default=Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex"))
    parser.add_argument("--link", action="store_true", help="Link to this checkout instead of copying")
    parser.add_argument("--replace", action="store_true", help="Back up an existing installation before replacing it")
    args = parser.parse_args()
    try:
        result = install(SOURCE, args.codex_home, link=args.link, replace=args.replace)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
