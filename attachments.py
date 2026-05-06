import base64
import os
import re
from pathlib import Path

IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
DOCUMENT_TYPES = {".pdf": "application/pdf"}
TEXT_TYPES = {".md", ".txt", ".csv", ".json"}

_AT_PATTERN = re.compile(r'@(\S+)')


def parse_attachments(user_input: str) -> tuple[str, list[dict]]:
    """Pull @path tokens out of user_input and return (clean_text, content_blocks).

    Each path becomes an image or document content block. The remaining text
    becomes a single text block at the end. Returns (text, []) if no
    attachments — caller can keep using a plain string in that case.
    """
    paths: list[str] = []

    def _capture(match: re.Match) -> str:
        paths.append(match.group(1))
        return ""

    cleaned = _AT_PATTERN.sub(_capture, user_input).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)

    blocks: list[dict] = []
    for raw_path in paths:
        block = _file_to_block(raw_path)
        blocks.append(block)

    return cleaned, blocks


def _file_to_block(raw_path: str) -> dict:
    path = Path(os.path.expanduser(raw_path)).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Attachment not found: {raw_path}")

    suffix = path.suffix.lower()
    if suffix in TEXT_TYPES:
        body = path.read_text(encoding="utf-8", errors="replace")
        return {"type": "text", "text": f"=== {path.name} ===\n{body}"}
    if suffix in IMAGE_TYPES:
        media_type = IMAGE_TYPES[suffix]
        block_type = "image"
    elif suffix in DOCUMENT_TYPES:
        media_type = DOCUMENT_TYPES[suffix]
        block_type = "document"
    else:
        supported = sorted(IMAGE_TYPES) + sorted(DOCUMENT_TYPES) + sorted(TEXT_TYPES)
        raise ValueError(f"Unsupported file type: {suffix} (supported: {', '.join(supported)})")

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 30:
        raise ValueError(f"{path.name} is {size_mb:.1f}MB — too large (max ~30MB)")

    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": block_type,
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }
