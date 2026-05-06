import json
import re
from typing import Optional
import anthropic

_client = anthropic.Anthropic()


def pick_skill(library, user_request: str, current_skill=None) -> Optional[object]:
    skills_summary = "\n".join(
        f'"{s.name}": {s.description[:350]}'
        for s in library.skills
    )

    sticky_hint = ""
    if current_skill:
        sticky_hint = (
            f'\n\nThe user is currently in a "{current_skill.name}" conversation. '
            f"If this looks like a follow-up or continuation, return that skill."
        )

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=64,
        system='You are a skill router. Respond ONLY with valid JSON: {"skill": "skill-name"} or {"skill": null} if no skill fits.',
        messages=[{
            "role": "user",
            "content": f"Skills:\n{skills_summary}{sticky_hint}\n\nUser request: {user_request}",
        }],
    )

    text = response.content[0].text.strip()
    json_match = re.search(r'\{[^}]+\}', text)
    if json_match:
        try:
            result = json.loads(json_match.group())
            skill_name = result.get("skill")
            if skill_name:
                return next((s for s in library.skills if s.name == skill_name), None)
        except json.JSONDecodeError:
            pass

    return None
