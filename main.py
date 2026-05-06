#!/usr/bin/env python3
import os
import sys

from skills import SkillLibrary
from router import pick_skill
from executor import run_skill_turn
from attachments import parse_attachments

REPO = "EDU-Ops-Team/Ops-Skills"


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
    print("Commands: 'new' to reset, 'skills' to list, 'quit' to exit.")
    print("Attach files with @path (e.g. 'compare @existing.pdf @proposed.pdf').\n")

    current_skill = None
    conversation: list[dict] = []

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
            print("\n")
        except Exception as e:
            print(f"\n[Error: {e}]\n")
            conversation.pop()


if __name__ == "__main__":
    main()
