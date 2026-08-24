"""
scheduler.py — Agendamento de publicação de posts.

⚠ MÓDULO STUB — A ser implementado quando a plataforma de blog for definida.

Placeholder que define a interface do módulo de agendamento.
"""

from pathlib import Path
from datetime import datetime


class Scheduler:
    """
    Agendador de publicações.

    STUB: Esta classe será implementada após a definição de:
    - Plataforma de blog (WordPress, Ghost, etc.)
    - Mecanismo de agendamento (APScheduler, Cron, GitHub Actions)
    """

    def __init__(self, config: dict):
        self.config    = config
        self.sched_cfg = config.get("scheduler", {})
        self.mechanism = self.sched_cfg.get("mechanism", "")

    def schedule(self, post_path: Path, publish_at: datetime) -> None:
        """
        Agenda a publicação de um post para uma data/hora específica.

        Args:
            post_path: Caminho para o arquivo .md em scheduled/
            publish_at: Data e hora de publicação desejada
        """
        raise NotImplementedError(
            "O módulo de agendamento ainda não foi implementado. "
            "Defina primeiro a plataforma de blog e o mecanismo de agendamento "
            "em config/settings.yaml."
        )

    def list_scheduled(self) -> list[dict]:
        """Lista todos os posts agendados com suas datas."""
        raise NotImplementedError("Módulo de agendamento não implementado.")

    def cancel(self, slug: str) -> None:
        """Cancela o agendamento de um post."""
        raise NotImplementedError("Módulo de agendamento não implementado.")
