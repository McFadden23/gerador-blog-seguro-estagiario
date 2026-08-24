"""
publisher.py — Publicação automática de posts na plataforma de blog.

⚠ MÓDULO STUB — A ser implementado quando a plataforma de blog for definida.

Placeholder que define a interface do módulo de publicação.
"""

from pathlib import Path


class Publisher:
    """
    Publicador automático de posts.

    STUB: Esta classe será implementada após a definição da plataforma de blog.

    Plataformas suportadas (futuro):
    - WordPress (REST API v2)
    - Ghost (Admin API)
    - Outras via plugin
    """

    def __init__(self, config: dict):
        self.config   = config
        self.pub_cfg  = config.get("publisher", {})
        self.platform = self.pub_cfg.get("platform", "")

    def publish(self, post_path: Path) -> str:
        """
        Publica um post na plataforma de blog configurada.

        Args:
            post_path: Caminho para o arquivo .md em scheduled/ ou approved/

        Returns:
            URL do post publicado
        """
        raise NotImplementedError(
            f"Plataforma '{self.platform}' não implementada. "
            "Configure 'publisher.platform' em config/settings.yaml "
            "e implemente o método publish() para a plataforma escolhida."
        )

    def update(self, post_path: Path, post_id: str) -> str:
        """Atualiza um post já publicado."""
        raise NotImplementedError("Módulo de publicação não implementado.")

    def delete(self, post_id: str) -> None:
        """Remove um post da plataforma."""
        raise NotImplementedError("Módulo de publicação não implementado.")
