"""
main.py — Ponto de entrada do Blog Automation System.

Uso:
    python main.py <comando> [opções]

Exemplo:
    python main.py generate-ideas --n 5
    python main.py generate-draft seguro-estagiario-direitos
    python main.py approve seguro-estagiario-direitos
    python main.py schedule seguro-estagiario-direitos 2026-09-01T10:00
    python main.py export-pdf seguro-estagiario-direitos
    python main.py status
"""

import sys
import os

# Adiciona src/ ao path para importações
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from cli import cli

if __name__ == "__main__":
    cli()
