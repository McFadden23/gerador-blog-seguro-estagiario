"""
analytics.py — Persistência de Estado e Aprendizado Autônomo do Agente SEO/GEO.

Funções:
    carregar_estado(data_dir)            → dict  (lê strategy_state.json)
    salvar_estado(state, data_dir)       → None  (grava strategy_state.json)
    registrar_execucao(post_url, titulo, estado_atual) → dict (entrada de histórico)
    atualizar_estrategia_autonoma(state) → dict  (evolui current_rules para o próximo ciclo)

Lógica de Evolução Autônoma:
    A cada ciclo, o agente rotaciona levemente as current_rules para testar
    diferentes abordagens de SEO/GEO, registrando o que foi usado em cada publicação.
"""

import json
import copy
from datetime import datetime
from pathlib import Path


# ── Caminho padrão do arquivo de estado ───────────────────────────────────────
DEFAULT_STATE_FILE = "strategy_state.json"

# ── Configurações de Evolução Autônoma ────────────────────────────────────────
TONE_ROTATION = [
    "autônomo/persuasivo",
    "direto/técnico",
    "narrativo/educativo",
    "consultivo/especialista",
]

ANCHOR_ROTATION = ["alto", "médio", "alto", "alto"]  # Tende ao alto para SEO

# Estado inicial de fallback (caso o arquivo não exista)
DEFAULT_STATE = {
    "target_url": "https://nautiplus.com.br/landingpages/estagiario/pasi/",
    "blog_url": "https://nautiplus.com.br/blog/",
    "main_keyword": "seguro estagiário",
    "current_rules": {
        "tone": "autônomo/persuasivo",
        "max_paragraphs_per_section": 3,
        "include_faq": True,
        "include_comparison_table": True,
        "anchor_link_density": "alto",
    },
    "history": [],
}


# ── Persistência ──────────────────────────────────────────────────────────────

def carregar_estado(data_dir: Path = None) -> dict:
    """
    Carrega o strategy_state.json da pasta data/.

    Args:
        data_dir: Diretório onde está o strategy_state.json.
                  Se None, usa ./data/ relativo ao cwd.

    Returns:
        dict com o estado atual do agente.
    """
    if data_dir is None:
        data_dir = Path("data")

    state_file = Path(data_dir) / DEFAULT_STATE_FILE

    if not state_file.exists():
        # Cria o arquivo com o estado padrão se não existir
        state_file.parent.mkdir(parents=True, exist_ok=True)
        salvar_estado(DEFAULT_STATE, data_dir)
        return copy.deepcopy(DEFAULT_STATE)

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        # Garante estrutura mínima
        state.setdefault("history", [])
        state.setdefault("current_rules", copy.deepcopy(DEFAULT_STATE["current_rules"]))
        return state
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠ Erro ao carregar strategy_state.json: {e}. Usando estado padrão.")
        return copy.deepcopy(DEFAULT_STATE)


def salvar_estado(state: dict, data_dir: Path = None) -> None:
    """
    Salva o dicionário de estado no strategy_state.json.

    Args:
        state: Dicionário de estado do agente.
        data_dir: Diretório onde salvar. Se None, usa ./data/.
    """
    if data_dir is None:
        data_dir = Path("data")

    state_file = Path(data_dir) / DEFAULT_STATE_FILE
    state_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"⚠ Erro ao salvar strategy_state.json: {e}")


# ── Registro de Execução ──────────────────────────────────────────────────────

def registrar_execucao(
    post_url: str,
    titulo: str,
    estado_atual: dict,
) -> dict:
    """
    Cria uma entrada de histórico com os dados da execução atual.

    Args:
        post_url: URL do post publicado (ou None se falhou).
        titulo: Título do artigo gerado.
        estado_atual: Estado atual (current_rules usadas nesta execução).

    Returns:
        dict com a entrada de histórico criada (mas NÃO salva — chame salvar_estado).
    """
    entrada = {
        "timestamp": datetime.now().isoformat(),
        "titulo": titulo,
        "post_url": post_url,
        "rules_used": copy.deepcopy(estado_atual.get("current_rules", {})),
        "ciclo": len(estado_atual.get("history", [])) + 1,
    }
    return entrada


# ── Evolução Autônoma das Regras ──────────────────────────────────────────────

def atualizar_estrategia_autonoma(state: dict) -> dict:
    """
    Evolui as current_rules para o próximo ciclo de publicação.

    Estratégia de Evolução:
    - Rotaciona o tom de escrita entre 4 variações
    - Alterna FAQ e tabela comparativa (liga/desliga) para testar performance
    - Mantém ancoragem sempre alta (essencial para SEO)
    - Incrementa max_paragraphs a cada 4 ciclos e reinicia

    Args:
        state: Estado atual do agente (com history preenchido).

    Returns:
        Novo dicionário de estado com current_rules atualizadas.
    """
    new_state = copy.deepcopy(state)
    history = new_state.get("history", [])
    ciclo = len(history)  # Número do PRÓXIMO ciclo (0-indexed)

    rules = new_state.get("current_rules", copy.deepcopy(DEFAULT_STATE["current_rules"]))

    # ── Rotação de tom ────────────────────────────────────────────────────────
    rules["tone"] = TONE_ROTATION[ciclo % len(TONE_ROTATION)]

    # ── Rotação de densidade de âncoras ──────────────────────────────────────
    rules["anchor_link_density"] = ANCHOR_ROTATION[ciclo % len(ANCHOR_ROTATION)]

    # ── Alternância de FAQ (ativa nos ciclos pares, mas nunca desativa por mais de 1 ciclo) ──
    rules["include_faq"] = ciclo % 3 != 1  # Desativa apenas 1 em 3 ciclos

    # ── Alternância de tabela comparativa ────────────────────────────────────
    rules["include_comparison_table"] = ciclo % 2 == 0

    # ── Variação de comprimento por seção ────────────────────────────────────
    # Ciclos: 2, 3, 2, 3, 2... para explorar posts mais longos a cada par
    rules["max_paragraphs_per_section"] = 3 if ciclo % 2 == 0 else 4

    new_state["current_rules"] = rules

    # ── Registra a mutação no log (para rastreabilidade) ─────────────────────
    if history:
        last = history[-1]
        last["next_rules_preview"] = copy.deepcopy(rules)

    return new_state


# ── Utilitários de Exibição ───────────────────────────────────────────────────

def formatar_historico_para_exibicao(history: list) -> list[dict]:
    """
    Prepara o histórico para exibição no painel Streamlit.

    Returns:
        Lista de dicts simples com colunas: Ciclo, Data, Título, URL, Tom Usado.
    """
    rows = []
    for entry in reversed(history):  # Mais recente primeiro
        rows.append({
            "Ciclo": entry.get("ciclo", "—"),
            "Data": entry.get("timestamp", "")[:16].replace("T", " "),
            "Título": entry.get("titulo", "—"),
            "URL": entry.get("post_url") or "Não publicado",
            "Tom Usado": entry.get("rules_used", {}).get("tone", "—"),
            "FAQ": "✅" if entry.get("rules_used", {}).get("include_faq") else "❌",
            "Tabela": "✅" if entry.get("rules_used", {}).get("include_comparison_table") else "❌",
            "Âncoras": entry.get("rules_used", {}).get("anchor_link_density", "—"),
        })
    return rows
