"""Local-only persistence for skill notes and overrides.

Layout: ~/.ops-skills-local/<skill-name>/
  - any *.md, *.txt, *.csv, *.json files are loaded as additional reference
    context whenever that skill runs (merged with the read-only remote refs).
  - notes.md is appended to by the /note command in the REPL.

Nothing in here is ever sent back to GitHub — it stays on your machine.
"""

import datetime
from pathlib import Path

LOCAL_ROOT = Path.home() / ".ops-skills-local"
TEXT_SUFFIXES = {".md", ".txt", ".csv", ".json"}


def skill_dir(skill_name: str) -> Path:
    return LOCAL_ROOT / skill_name


def load_local_references(skill_name: str) -> dict[str, str]:
    d = skill_dir(skill_name)
    if not d.is_dir():
        return {}
    refs: dict[str, str] = {}
    for path in sorted(d.iterdir()):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            refs[f"local/{path.name}"] = path.read_text(encoding="utf-8", errors="replace")
    return refs


def append_note(skill_name: str, text: str) -> Path:
    d = skill_dir(skill_name)
    d.mkdir(parents=True, exist_ok=True)
    notes = d / "notes.md"
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    entry = f"\n## {timestamp}\n\n{text.strip()}\n"
    with notes.open("a", encoding="utf-8") as f:
        f.write(entry)
    return notes
