#!/usr/bin/env python3
"""Validate portable Skill packaging; PyYAML is a development-only dependency."""

import re
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "full-repo-audit"


def main():
    errors = []
    content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = re.match(r"\A---\n(.*?)\n---\n", content, re.S)
    if not frontmatter:
        errors.append("SKILL.md needs YAML frontmatter")
    else:
        metadata = yaml.safe_load(frontmatter[1])
        if metadata.get("name") != SKILL.name:
            errors.append("Skill name must match its directory")
        description = metadata.get("description", "")
        if not isinstance(description, str) or not 1 <= len(description) <= 1024:
            errors.append("Skill needs a concise description")
        if set(metadata) - {"name", "description", "license", "allowed-tools", "metadata"}:
            errors.append("Unsupported frontmatter fields")
    ui = yaml.safe_load((SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8"))
    interface = ui.get("interface", {})
    if "$full-repo-audit" not in interface.get("default_prompt", ""):
        errors.append("UI prompt must explicitly invoke the Skill")
    if not 25 <= len(interface.get("short_description", "")) <= 64:
        errors.append("UI short_description must be 25–64 characters")
    for path in [ROOT / "README.md", *SKILL.rglob("*.md")]:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" not in target and not target.startswith("#"):
                if not (path.parent / target.split("#", 1)[0]).is_file():
                    errors.append(f"Missing reference in {path.relative_to(ROOT)}: {target}")
        if "[TODO:" in text:
            errors.append(f"Unfinished scaffold: {path.relative_to(ROOT)}")
    for path in SKILL.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".py", ".yaml"}:
            text = path.read_text(encoding="utf-8")
            if re.search(r"/Users/|/home/[a-zA-Z0-9_-]+/|[A-Z]:\\\\Users\\\\", text):
                errors.append(f"Machine-specific path: {path.relative_to(ROOT)}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Skill metadata, references and portable paths are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
