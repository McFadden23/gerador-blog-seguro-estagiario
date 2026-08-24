"""
generator.py — Geração de conteúdo via Google Gemini API.

Usa o novo SDK: google-genai (pacote oficial atual)

Responsável por:
- Gerar lista de pautas (ideias de posts)
- Gerar rascunho completo de um post
"""

import os
import re
from pathlib import Path
from datetime import datetime, date

from google import genai
from google.genai import types
import yaml


# ── Configuração do cliente Gemini ────────────────────────────────────────────

def _get_client(config: dict) -> genai.Client:
    """Inicializa e retorna o cliente Gemini configurado."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY não encontrada. "
            "Defina-a no arquivo .env ou como variável de ambiente."
        )
    return genai.Client(api_key=api_key)


def _model_name(config: dict) -> str:
    """Retorna o nome do modelo configurado."""
    return config.get("ai", {}).get("model", "gemini-2.5-flash")


def _temperature(config: dict) -> float:
    """Retorna a temperatura configurada."""
    return float(config.get("ai", {}).get("temperature", 0.7))


# ── Leitura das Diretrizes ───────────────────────────────────────────────────

def _load_workspace_guidelines(workspace_dir: Path) -> dict:
    """Lê os 3 arquivos centrais consolidados de workspace/."""
    file_map = {
        "diretrizes": workspace_dir / "01_diretrizes_e_tom.md",
        "estrategia": workspace_dir / "02_seo_geo_estrategia.md",
        "exemplo":    workspace_dir / "03_exemplo_campeao.md",
    }
    contents = {}
    for key, path in file_map.items():
        if path.exists():
            contents[key] = path.read_text(encoding="utf-8")
        else:
            contents[key] = ""
    return contents


# ── Geração de Pautas ─────────────────────────────────────────────────────────

def generate_ideas(config: dict, workspace_dir: Path, n: int = 5,
                   existing_topics: list[str] = None) -> list[dict]:
    """
    Gera N sugestões de pautas para posts usando o Gemini, baseando-se nos arquivos de workspace/.
    """
    client = _get_client(config)
    guidelines = _load_workspace_guidelines(workspace_dir)

    existing = ", ".join(existing_topics or []) or "nenhum ainda"
    prompt = f"""Você é o especialista em estratégia de conteúdo da Nautiplus / Seguro Estágio Rápido.

== DIRETRIZES DE NEGÓCIO E TOM ==
{guidelines.get('diretrizes', '')}

== ESTRATÉGIA DE SEO E GEO ==
{guidelines.get('estrategia', '')}

== TAREFA ==
Gere uma lista com exatamente {n} pautas para posts de blog com alto potencial SEO/GEO, sem repetir os temas já existentes: {existing}.

== FORMATO DE SAÍDA OBRIGATÓRIO (YAML) ==
Retorne a lista de pautas exatamente neste bloco YAML:
```yaml
- id: 1
  titulo: "Título SEO"
  subtitulo: "Subtítulo"
  slug: "slug-kebab-case"
  angulo: "Ângulo editorial em 1 frase"
  publico: "Público-alvo"
  palavras_chave: ["kw1", "kw2"]
  formato: "Artigo"
```
"""

    print(f"  🤖 Gerando {n} pautas via Gemini ({_model_name(config)})...")

    response = client.models.generate_content(
        model=_model_name(config),
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=_temperature(config),
            max_output_tokens=config.get("ai", {}).get("max_output_tokens", 4096),
        ),
    )

    ideas = _parse_yaml_list(response.text)
    return ideas


# ── Geração de Rascunho ───────────────────────────────────────────────────────

def generate_draft(idea: dict, config: dict, workspace_dir: Path) -> str:
    """
    Gera o rascunho completo de um post aplicando SEO, GEO e o tom exato do exemplo campeão.
    """
    client = _get_client(config)
    guidelines = _load_workspace_guidelines(workspace_dir)

    today = date.today().isoformat()
    tags = idea.get("palavras_chave", config.get("post", {}).get("default_tags", []))

    prompt = f"""Você é o redator oficial da Nautiplus / Seguro Estágio Rápido, especialista em seguro para estagiários, onboarding de RH e conformidade com a Lei nº 11.788/2008.

== DIRETRIZES DE IDENTIDADE, TOM E COMPLIANCE ==
{guidelines.get('diretrizes', '')}

== DIRETRIZES DE OTIMIZAÇÃO SEO & GEO (PREFERÊNCIA DE ESTRUTURAÇÃO) ==
{guidelines.get('estrategia', '')}

== EXEMPLO CAMPEÃO PADRÃO-OURO (FEW-SHOT DEMONSTRATION) ==
Use o exemplo abaixo como referência máxima de estilo, concisão, autoridade e tom:
{guidelines.get('exemplo', '')}

== DADOS DA PAUTA ESCOLHIDA ==
- Título: {idea.get('titulo', '')}
- Subtítulo: {idea.get('subtitulo', '')}
- Slug: {idea.get('slug', '')}
- Ângulo Editorial: {idea.get('angulo', '')}
- Palavras-chave: {', '.join(idea.get('palavras_chave', []))}
- Tags: {tags}
- Data: {today}

== REQUISITOS OBRIGATÓRIOS DO ARTIGO ==
1. Extensão: 3 a 5 parágrafos no máximo, entregando alto valor informativo de forma direta ao ponto.
2. Otimização GEO: Forneça a resposta direta e a conclusão logo nos primeiros parágrafos.
3. Otimização SEO: Use títulos H2/H3 claros e tópicos organizados em lista quando oportuno.
4. Jamais use traços duplos "--".
5. Inicie com o bloco de Frontmatter YAML completo.

Escreva o artigo completo agora em Markdown:
"""

    response = client.models.generate_content(
        model=_model_name(config),
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=_temperature(config),
            max_output_tokens=config.get("ai", {}).get("max_output_tokens", 4096),
        ),
    )

    content = response.text
    content = _ensure_frontmatter(content, idea, config, today)
    return content


# ── Geração Autônoma (Ideação + Redação em 1 Fluxo) ───────────────────────────

def generate_autonomous_post(config: dict, workspace_dir: Path,
                             existing_topics: list[str] = None) -> tuple[dict, str]:
    """
    Executa o fluxo autônomo completo:
    1. Pesquisa/Identifica temas quentes e seleciona autonomamente a melhor pauta (SEO/GEO).
    2. Escreve o artigo completo com base nas 3 diretrizes consolidadas.
    
    Returns:
        tuple[dict, str]: (dados_da_pauta_selecionada, conteudo_markdown_completo)
    """
    client = _get_client(config)
    guidelines = _load_workspace_guidelines(workspace_dir)
    model = _model_name(config)
    temp = _temperature(config)

    # 1. Ideação e Seleção Autônoma da Pauta Campeã
    existing = ", ".join(existing_topics or []) or "nenhum ainda"
    ideation_prompt = f"""Você é o estrategista-chefe de SEO e GEO da Nautiplus / Seguro Estágio Rápido.

== DIRETRIZES DO PROJETO ==
{guidelines.get('diretrizes', '')}

== ESTRATÉGIA DE SEO E GEO ==
{guidelines.get('estrategia', '')}

== TAREFA DE PESQUISA & SELEÇÃO AUTÔNOMA ==
1. Identifique as dúvidas mais frequentes, dores de RH, custos operacionais e riscos trabalhistas urgentes relacionados a Seguro Estágio e à Lei do Estágio nº 11.788/2008.
2. Evite repetir os temas existentes: {existing}.
3. Analise o potencial de busca (SEO) e capacidade de resposta direta por IA (GEO).
4. Escolha AUTONOMAMENTE a pauta ÚNICA de maior impacto e relevância no momento.

== FORMATO DE SAÍDA OBRIGATÓRIO (YAML) ==
Retorne APENAS um bloco YAML com a pauta escolhida:
```yaml
id: 1
titulo: "Título SEO de Alto Impacto"
subtitulo: "Subtítulo explicativo com gancho"
slug: "slug-kebab-case-otimizado"
angulo: "Ângulo editorial e dor principal resolvida"
publico: "Empresas contratantes e profissionais de RH"
palavras_chave: ["palavra1", "palavra2", "palavra3"]
motivo_escolha: "Por que esta pauta possui o maior potencial de busca e impacto agora"
```
"""
    print(f"  🧠 Pesquisando e selecionando a pauta de maior potencial ({model})...")
    res_idea = client.models.generate_content(
        model=model,
        contents=ideation_prompt,
        config=types.GenerateContentConfig(
            temperature=temp,
            max_output_tokens=config.get("ai", {}).get("max_output_tokens", 4096),
        )
    )

    idea_match = re.search(r"```(?:yaml)?\n(.*?)```", res_idea.text, re.DOTALL)
    idea_yaml = idea_match.group(1) if idea_match else res_idea.text
    try:
        chosen_idea = yaml.safe_load(idea_yaml)
        if isinstance(chosen_idea, list) and len(chosen_idea) > 0:
            chosen_idea = chosen_idea[0]
        if not isinstance(chosen_idea, dict):
            chosen_idea = {}
    except Exception:
        chosen_idea = {}

    if not chosen_idea.get("titulo"):
        chosen_idea = {
            "titulo": "Lei 11.788/2008: Riscos Trabalhistas e Seguro Estágio Obrigatório",
            "subtitulo": "Como evitar o reconhecimento de vínculo empregatício no onboarding",
            "slug": "seguro-estagio-lei-11788-riscos",
            "angulo": "Conformidade imediata e eliminação de passivos trabalhistas",
            "palavras_chave": ["seguro estagio", "lei 11788", "passivo trabalhista"],
            "motivo_escolha": "Tema de alta urgência e busca frequente por RHs"
        }

    # 2. Redação Completa do Artigo
    today = date.today().isoformat()
    article_content = generate_draft(chosen_idea, config, workspace_dir)
    return chosen_idea, article_content


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_yaml_list(text: str) -> list[dict]:
    """Extrai e parseia a lista YAML da resposta do Gemini."""
    match = re.search(r"```(?:yaml)?\n(.*?)```", text, re.DOTALL)
    yaml_text = match.group(1) if match else text

    try:
        data = yaml.safe_load(yaml_text)
        if isinstance(data, list):
            return data
    except yaml.YAMLError as e:
        print(f"  ⚠ Erro ao parsear YAML: {e}")

    return []


def _ensure_frontmatter(content: str, idea: dict, config: dict, today: str) -> str:
    """
    Garante que o conteúdo tenha um frontmatter YAML válido.
    Se o modelo já gerou um, mantém; se não, injeta um padrão.
    """
    blog_cfg = config.get("blog", {})
    post_cfg = config.get("post", {})

    default_fm = {
        "title":            idea.get("titulo", ""),
        "subtitle":         idea.get("subtitulo", ""),
        "meta_description": "",
        "slug":             idea.get("slug", ""),
        "tags":             idea.get("palavras_chave", post_cfg.get("default_tags", [])),
        "status":           "draft",
        "publish_date":     "",
        "platform":         "",
        "author":           blog_cfg.get("author", ""),
        "created_at":       today,
        "updated_at":       today,
    }

    # Remove possíveis marcadores de código markdown ao redor do frontmatter
    content = re.sub(r"^```(?:markdown|md)?\n", "", content.strip())
    content = re.sub(r"\n```$", "", content)

    has_fm = content.strip().startswith("---")
    if not has_fm:
        fm_str = yaml.dump(default_fm, allow_unicode=True,
                           default_flow_style=False, sort_keys=False)
        content = f"---\n{fm_str}---\n\n{content}"

    return content
