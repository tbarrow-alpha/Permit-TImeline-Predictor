import anthropic


def run_skill_turn(skill, conversation: list[dict]) -> str:
    client = anthropic.Anthropic()
    messages = _build_messages(skill, conversation)
    system = [{"type": "text", "text": skill.system_prompt, "cache_control": {"type": "ephemeral"}}]

    full_text = ""
    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_text += text

    return full_text


def _build_messages(skill, conversation: list[dict]) -> list[dict]:
    if not conversation:
        return []

    result = [dict(msg) for msg in conversation]

    if skill.references and result[0]["role"] == "user":
        ref_block = "\n\n".join(
            f"=== {name} ===\n{content}"
            for name, content in sorted(skill.references.items())
        )
        original = result[0]["content"]
        result[0] = {
            "role": "user",
            "content": f"<reference_files>\n{ref_block}\n</reference_files>\n\n{original}",
        }

    return result
