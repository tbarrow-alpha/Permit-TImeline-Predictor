import base64
from dataclasses import dataclass, field
from typing import Optional
import requests
import frontmatter

from local_store import load_local_references


@dataclass
class Skill:
    name: str
    description: str
    metadata: dict
    system_prompt: str
    references: dict = field(default_factory=dict)


class SkillLibrary:
    def __init__(self, repo: str, token: Optional[str] = None):
        self.repo = repo
        self.token = token
        self.skills: list[Skill] = []

    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github.v3+json", "User-Agent": "ops-skills-agent"}
        if self.token:
            h["Authorization"] = f"token {self.token}"
        return h

    def _get_json(self, path: str) -> list | dict:
        url = f"https://api.github.com/repos/{self.repo}/contents/{path}"
        r = requests.get(url, headers=self._headers(), timeout=15)
        r.raise_for_status()
        return r.json()

    def _file_text(self, path: str) -> str:
        data = self._get_json(path)
        if isinstance(data, dict) and data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8")
        raise ValueError(f"Unexpected response for {path}")

    def load(self) -> None:
        items = self._get_json("")
        dirs = [item["name"] for item in items if item["type"] == "dir"]
        for dir_name in dirs:
            self._try_load_skill(dir_name)

    def _try_load_skill(self, dir_name: str) -> None:
        try:
            raw = self._file_text(f"{dir_name}/SKILL.md")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return
            raise

        post = frontmatter.loads(raw)
        name = str(post.get("name", dir_name))
        description = str(post.get("description", "")).strip()
        metadata = dict(post.get("metadata", {}))

        references: dict[str, str] = {}
        try:
            ref_items = self._get_json(f"{dir_name}/references")
            for item in ref_items:
                if item["type"] == "file":
                    content = self._file_text(f"{dir_name}/references/{item['name']}")
                    references[item["name"]] = content
        except requests.HTTPError:
            pass

        local_refs = load_local_references(name)
        references.update(local_refs)

        self.skills.append(Skill(
            name=name,
            description=description,
            metadata=metadata,
            system_prompt=raw,
            references=references,
        ))
        local_tag = f" (+{len(local_refs)} local)" if local_refs else ""
        print(f"  ✓ {name}{local_tag}")
