"""
workspace.py — Gerenciamento do workspace de arquivos Markdown.

Responsável por:
- Mover arquivos entre pastas (inbox → drafts → approved → scheduled → published)
- Aplicar e validar naming conventions
- Listar posts e seus status
"""

import os
import shutil
import re
from pathlib import Path
from datetime import datetime
import yaml


# ── Constantes de estado ──────────────────────────────────────────────────────

STATES = {
    "idea":      ("inbox",     "_idea.md"),
    "draft":     ("drafts",    "_draft.md"),
    "approved":  ("approved",  "_final.md"),
    "scheduled": ("scheduled", "_final.md"),   # prefixo YYYY-MM-DD_ adicionado
    "published": ("published", ".md"),          # prefixo YYYY-MM-DD-platform- adicionado
}


# ── WorkspaceManager ──────────────────────────────────────────────────────────

class WorkspaceManager:
    """Gerencia o ciclo de vida dos posts no workspace."""

    def __init__(self, root: str | Path, config: dict):
        self.root = Path(root)
        self.config = config
        self.ws = config.get("workspace", {})

    def _folder(self, state: str) -> Path:
        """Retorna o Path da pasta para um dado estado."""
        folder_key = state if state != "scheduled" else "scheduled"
        folder = self.ws.get(state, STATES[state][0])
        return self.root / folder

    def _filename(self, slug: str, state: str, date: str = None, platform: str = None) -> str:
        """Gera o nome de arquivo correto conforme a naming convention."""
        if state == "idea":
            return f"{slug}_idea.md"
        elif state == "draft":
            return f"{slug}_draft.md"
        elif state == "approved":
            return f"{slug}_final.md"
        elif state == "scheduled":
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            return f"{date}_{slug}_final.md"
        elif state == "published":
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            plat = platform or "blog"
            return f"{date}-{plat}-{slug}.md"
        raise ValueError(f"Estado desconhecido: {state}")

    def get_post_path(self, slug: str, state: str, date: str = None, platform: str = None) -> Path:
        """Retorna o caminho completo de um post em um dado estado."""
        folder = self._folder(state)
        filename = self._filename(slug, state, date, platform)
        return folder / filename

    def save_post(self, slug: str, content: str, state: str) -> Path:
        """Salva o conteúdo de um post no arquivo correto."""
        path = self.get_post_path(slug, state)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"  ✔ Salvo: {path.relative_to(self.root)}")
        return path

    def advance_state(self, slug: str, from_state: str, to_state: str,
                      date: str = None, platform: str = None) -> Path:
        """Move um post de um estado para o próximo."""
        src = self.get_post_path(slug, from_state)
        if not src.exists():
            raise FileNotFoundError(f"Post não encontrado: {src}")

        dst = self.get_post_path(slug, to_state, date=date, platform=platform)
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Atualiza o frontmatter com o novo status
        content = src.read_text(encoding="utf-8")
        content = _update_frontmatter(content, {"status": to_state})

        dst.write_text(content, encoding="utf-8")
        src.unlink()  # Remove arquivo da pasta anterior

        print(f"  ✔ {from_state} → {to_state}: {dst.relative_to(self.root)}")
        return dst

    def list_all(self) -> list[dict]:
        """Lista todos os posts com seus status e metadados."""
        posts = []
        state_folders = {
            "idea":      self.ws.get("inbox", "workspace/inbox"),
            "draft":     self.ws.get("drafts", "workspace/drafts"),
            "approved":  self.ws.get("approved", "workspace/approved"),
            "scheduled": self.ws.get("scheduled", "workspace/scheduled"),
            "published": self.ws.get("published", "workspace/published"),
        }
        for state, folder_rel in state_folders.items():
            folder = self.root / folder_rel
            if not folder.exists():
                continue
            for f in sorted(folder.glob("*.md")):
                meta = _read_frontmatter(f)
                posts.append({
                    "file":   f.name,
                    "state":  state,
                    "title":  meta.get("title", "(sem título)"),
                    "slug":   meta.get("slug", f.stem),
                    "date":   meta.get("publish_date", ""),
                })
        return posts

    def find_post(self, slug: str) -> tuple[Path, str] | tuple[None, None]:
        """Busca um post pelo slug em todas as pastas. Retorna (path, state)."""
        for state in STATES:
            folder = self._folder(state)
            if not folder.exists():
                continue
            for f in folder.glob("*.md"):
                if slug in f.name:
                    return f, state
        return None, None


# ── Helpers de Frontmatter ────────────────────────────────────────────────────

def _read_frontmatter(path: Path) -> dict:
    """Lê o frontmatter YAML de um arquivo Markdown."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}
    return {}


def _update_frontmatter(content: str, updates: dict) -> str:
    """Atualiza campos no frontmatter YAML de um conteúdo Markdown."""
    match = re.match(r"^---\n(.*?)\n---\n?(.*)", content, re.DOTALL)
    if not match:
        return content
    try:
        fm = yaml.safe_load(match.group(1)) or {}
        body = match.group(2)
        fm.update(updates)
        fm["updated_at"] = datetime.now().isoformat()
        new_fm = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
        return f"---\n{new_fm}---\n{body}"
    except yaml.YAMLError:
        return content
