#!/usr/bin/env python3
import datetime
import os
import re
import sys
from pathlib import Path

from skills import SkillLibrary
from router import pick_skill
from executor import run_skill_turn
from attachments import parse_attachments
from local_store import append_note, skill_dir

REPO = "EDU-Ops-Team/Ops-Skills"
OUTPUT_ROOT = Path.home() / "ops-skills-output"


def save_response(skill_name: str, response_text: str, custom_name: str | None) -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    if custom_name:
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", custom_name).strip("_") or "output"
        if not stem.endswith(".md"):
            stem += ".md"
        path = OUTPUT_ROOT / stem
    else:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        path = OUTPUT_ROOT / f"{skill_name}_{timestamp}.md"
    header = f"# {skill_name} — {datetime.datetime.now().isoformat(timespec='seconds')}\n\n"
    path.write_text(header + response_text, encoding="utf-8")
    return path


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: GITHUB_TOKEN not set — private repos will fail.\n")

    print(f"Loading skills from {REPO}...")
    library = SkillLibrary(repo=REPO, token=token)
    try:
        library.load()
    except Exception as e:
        print(f"\nFailed to load skills: {e}")
        sys.exit(1)

    if not library.skills:
        print("No skills found in repository.")
        sys.exit(1)

    print(f"\nReady — {len(library.skills)} skills loaded.")
    print("Commands: 'new' to reset, 'skills' to list, '/note <text>' to save a note,")
    print("          '/save [filename]' to write last result to ~/ops-skills-output/, 'quit' to exit.")
    print("Attach files with @path (e.g. 'calculate capacity @plan.pdf').")
    print("Include previous iterations as reference: '@new_plan.pdf @prior_plan.pdf @prior_calc.md'.")
    print("Local notes/refs live in ~/.ops-skills-local/<skill>/ (loaded automatically, never uploaded).\n")

    current_skill = None
    conversation: list[dict] = []
    last_response: str | None = None

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        if user_input.lower() in ("new", "/new", "reset", "/reset"):
            current_skill = None
            conversation = []
            print("[Conversation reset]\n")
            continue

        if user_input.lower() == "/save" or user_input.lower().startswith("/save "):
            if last_response is None or current_skill is None:
                print("[No result yet — run a request first]\n")
                continue
            custom_name = user_input[len("/save"):].strip() or None
            path = save_response(current_skill.name, last_response, custom_name)
            print(f"[Saved to {path}]\n")
            continue

        if user_input.startswith("/note "):
            if current_skill is None:
                print("[No active skill — pick one first by sending a request]\n")
                continue
            note_text = user_input[len("/note "):].strip()
            if not note_text:
                print("[Empty note — nothing saved]\n")
                continue
            path = append_note(current_skill.name, note_text)
            current_skill.references[f"local/notes.md"] = path.read_text(encoding="utf-8")
            print(f"[Saved to {path}]\n")
            continue

        if user_input.lower() in ("skills", "/skills", "list"):
            for s in library.skills:
                print(f"  • {s.name}: {s.description[:80]}...")
            print()
            continue

        try:
            text_part, attachment_blocks = parse_attachments(user_input)
        except (FileNotFoundError, ValueError) as e:
            print(f"[Attachment error: {e}]\n")
            continue

        routing_text = text_part or "(file attachments only)"
        selected = pick_skill(library, routing_text, current_skill=current_skill)
        if selected is None:
            available = ", ".join(s.name for s in library.skills)
            print(f"No matching skill found. Available: {available}\n")
            continue

        if current_skill is not None and selected.name != current_skill.name:
            print(f"\n[Switching to skill: {selected.name}]\n")
            conversation = []
        elif current_skill is None:
            print(f"[Skill: {selected.name}]\n")

        current_skill = selected

        if attachment_blocks:
            print(f"[Attached {len(attachment_blocks)} file(s)]")
            content_blocks = list(attachment_blocks)
            if text_part:
                content_blocks.append({"type": "text", "text": text_part})
            conversation.append({"role": "user", "content": content_blocks})
        else:
            conversation.append({"role": "user", "content": text_part})

        try:
            response_text = run_skill_turn(current_skill, conversation)
            conversation.append({"role": "assistant", "content": response_text})
            last_response = response_text
            print("\n")
        except Exception as e:
            print(f"\n[Error: {e}]\n")
            conversation.pop()


if __name__ == "__main__":
    main()
