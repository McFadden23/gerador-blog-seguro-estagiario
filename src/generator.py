"""
generator.py — Agente Autônomo de Geração de Conteúdo SEO/GEO.

Objetivo único: Ranquear https://nautiplus.com.br/landingpages/estagiario/pasi/
e https://nautiplus.com.br/blog/ para a busca "seguro estagiário".

Recursos:
- gerar_artigo_autonomo(): geração completa via Gemini com regras do state
- Otimização GEO: respostas diretas, listas, tabelas, dados estruturados
- Ancoragem obrigatória para a landing page PASI com textos-âncora variados
- Fallback automático entre modelos Gemini
"""

import re
from datetime import date, datetime

try:
    from google import genai
    from google.genai import types
    HAS_GOOGLE_GENAI = True
except ImportError:
    HAS_GOOGLE_GENAI = False

try:
    import google.generativeai as legacy_genai
    HAS_LEGACY_GENAI = True
except ImportError:
    HAS_LEGACY_GENAI = False


# ── Modelos candidatos (ordem de preferência) ──────────────────────────────────
CANDIDATE_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
]

# ── Âncoras variadas obrigatórias para a landing page ─────────────────────────
ANCHOR_TEXTS = [
    "contratar seguro estagiário",
    "seguro de vida para estagiários PASI",
    "seguro obrigatório para estagiário",
    "apólice de seguro estagiário PASI",
    "emitir seguro estagiário online",
    "seguro estagiário rápido Nautiplus",
    "seguro de acidentes pessoais para estagiário",
    "seguro estagiário Lei 11.788",
]

TARGET_URL = "https://nautiplus.com.br/landingpages/estagiario/pasi/"
BLOG_URL   = "https://nautiplus.com.br/blog/"


def _call_gemini(api_key: str, prompt: str, temperature: float = 0.75,
                 max_tokens: int = 6000) -> str:
    """
    Chama a API Gemini iniciando pelo gemini-3.7-flash e, se acabarem os tokens/quota
    ou houver indisponibilidade, migra automaticamente para o modelo subsequente (3.6-flash, 3.5-flash).
    """
    last_err = None

    if HAS_GOOGLE_GENAI:
        client = genai.Client(api_key=api_key)
        for idx, model in enumerate(CANDIDATE_MODELS):
            try:
                res = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    ),
                )
                if res and res.text:
                    return res.text
            except Exception as err:
                last_err = err
                err_str = str(err).lower()
                # Erro de chave/permissão inválida geral
                if "403" in str(err) or "permission_denied" in err_str:
                    raise err
                # Esgotamento de tokens/quota (429, resource_exhausted) ou indisponibilidade (404, 503)
                # Faz fallback automático para o próximo modelo da lista
                if any(c in str(err) for c in ["429", "404", "503"]) or \
                   any(k in err_str for k in ["quota", "resource_exhausted", "token", "unavailable", "not_found"]):
                    next_model = CANDIDATE_MODELS[idx + 1] if idx + 1 < len(CANDIDATE_MODELS) else None
                    if next_model:
                        print(f"⚠️ Tokens/Quota esgotados ou erro no modelo {model}. Alternando automaticamente para {next_model}...")
                    continue
                raise err

    if HAS_LEGACY_GENAI:
        legacy_genai.configure(api_key=api_key)
        for idx, model in enumerate(CANDIDATE_MODELS):
            try:
                m = legacy_genai.GenerativeModel(model)
                res = m.generate_content(prompt)
                if res and res.text:
                    return res.text
            except Exception as err:
                last_err = err
                err_str = str(err).lower()
                if "403" in str(err) or "permission_denied" in err_str:
                    raise err
                if any(c in str(err) for c in ["429", "404", "503"]) or \
                   any(k in err_str for k in ["quota", "resource_exhausted", "token", "unavailable", "not_found"]):
                    next_model = CANDIDATE_MODELS[idx + 1] if idx + 1 < len(CANDIDATE_MODELS) else None
                    if next_model:
                        print(f"⚠️ Tokens/Quota esgotados ou erro no modelo {model}. Alternando automaticamente para {next_model}...")
                    continue
                raise err

    if last_err:
        raise last_err
    raise ImportError(
        "Nenhuma biblioteca Gemini encontrada. "
        "Instale google-genai ou google-generativeai."
    )


def _build_anchor_examples(n: int = 4) -> str:
    """Retorna exemplos de âncoras formatadas como Markdown."""
    selected = ANCHOR_TEXTS[:n]
    return "\n".join(
        f'- [{anchor}]({TARGET_URL})' for anchor in selected
    )


def gerar_artigo_autonomo(api_key: str, state: dict) -> dict:
    """
    Gera um artigo completo e otimizado para SEO/GEO com base nas regras atuais do state.

    Args:
        api_key: Chave da API do Gemini.
        state: Dicionário com target_url, blog_url, main_keyword e current_rules.

    Returns:
        dict com chaves:
            - titulo (str): título do artigo
            - conteudo_markdown (str): artigo completo em Markdown
            - resumo_carrossel (list[str]): lista de 4–6 pontos-chave para o carrossel PDF
    """
    rules = state.get("current_rules", {})
    keyword = state.get("main_keyword", "seguro estagiário")
    target = state.get("target_url", TARGET_URL)
    blog = state.get("blog_url", BLOG_URL)

    tone = rules.get("tone", "autônomo/persuasivo")
    max_par = rules.get("max_paragraphs_per_section", 3)
    include_faq = rules.get("include_faq", True)
    include_table = rules.get("include_comparison_table", True)
    anchor_density = rules.get("anchor_link_density", "alto")

    anchor_count = {"alto": 5, "médio": 3, "baixo": 2}.get(anchor_density, 4)
    anchor_examples = _build_anchor_examples(anchor_count)
    today = date.today().isoformat()

    faq_instruction = (
        "## Seção Obrigatória: FAQ (Perguntas Frequentes)\n"
        "Inclua 3 a 5 perguntas e respostas diretas no formato pergunta/resposta ao final do artigo. "
        "Essas perguntas devem ser as dúvidas mais comuns dos RHs sobre seguro estagiário.\n"
        if include_faq else ""
    )

    table_instruction = (
        "## Seção Obrigatória: Tabela Comparativa\n"
        "Inclua uma tabela Markdown comparando cenários (ex.: com seguro x sem seguro, "
        "ou comparando coberturas básicas x avançadas para estagiários).\n"
        if include_table else ""
    )

    prompt = f"""Você é um agente autônomo especialista em SEO e GEO (Generative Engine Optimization) \
da Nautiplus / Seguro Estágio Rápido. Seu ÚNICO OBJETIVO é ranquear o site {target} \
e o blog {blog} para a busca "{keyword}" nos motores de busca tradicionais E nas IAs \
(ChatGPT, Gemini, Perplexity, Claude).

== TOM E ESTILO ==
Tom: {tone}
Máximo de parágrafos por seção: {max_par}
Data atual: {today}

== OBJETIVO 1: SEO CLÁSSICO ==
- Título H1 com a palavra-chave exata "{keyword}" no início
- Use H2 e H3 estruturados com variações da keyword
- Meta description (160 caracteres) otimizada para CTR
- Densidade de keyword: 1,5% a 2% — natural, sem keyword stuffing
- Resposta direta à intenção de busca logo no 1º parágrafo
- Use dados, números e referências à Lei nº 11.788/2008

== OBJETIVO 2: GEO (Generative Engine Optimization) ==
Para que IAs como ChatGPT, Gemini e Perplexity CITEM a Nautiplus como fonte:
- Forneça a resposta definitiva nos primeiros 2 parágrafos (zero-click answer)
- Use listas numeradas e bullets para pontos-chave
- Inclua dados factuais e estatísticas
- Estruture com padrão: [Pergunta implícita] → [Resposta direta] → [Contexto/Detalhes]
- Use linguagem de autoridade: "segundo a Lei 11.788/2008", "de acordo com a SUSEP"

== OBJETIVO 3: ANCORAGEM ESTRATÉGICA (OBRIGATÓRIO) ==
Inclua EXATAMENTE {anchor_count} links internos apontando para {target} distribuídos naturalmente no texto.
Exemplos de textos-âncora a usar (varie-os, não repita):
{anchor_examples}
Os links devem aparecer em contextos que INCENTIVEM o clique e a conversão.

{table_instruction}
{faq_instruction}

== ESTRUTURA OBRIGATÓRIA DO ARTIGO ==
1. Frontmatter YAML completo (entre --- e ---)
2. Introdução: resposta direta à intenção de busca + 1 link âncora
3. Por que o seguro estagiário é obrigatório (Lei 11.788/2008)
4. Como funciona na prática (lista numerada)
5. O que cobre o seguro estagiário PASI — Nautiplus
{"6. Tabela comparativa" if include_table else "6. Vantagens de contratar online"}
{"7. FAQ" if include_faq else "7. Como contratar agora"}
8. Conclusão com CTA forte para {target}

== FORMATO DO FRONTMATTER ==
---
title: "[TÍTULO SEO COM A KEYWORD]"
subtitle: "[SUBTÍTULO COM GANCHO]"
slug: "[slug-kebab-case]"
status: "publish"
created_at: "{datetime.now().isoformat()}"
author: "Equipe Nautiplus"
category: "Seguro Estagiário"
tags: ["{keyword}", "Lei 11.788", "seguro PASI", "seguro obrigatório estagiário"]
seo:
  meta_description: "[160 caracteres máx]"
  focus_keyword: "{keyword}"
---

Escreva o artigo completo em Markdown a partir do frontmatter agora. \
O artigo deve ter NO MÍNIMO 800 palavras e ser altamente informativo, \
persuasivo e com autoridade técnica sobre seguro estagiário.
"""

    raw = _call_gemini(api_key, prompt, temperature=0.72, max_tokens=7000)

    # ── Extração do título ────────────────────────────────────────────────────
    titulo = keyword.title()
    title_match = re.search(r'title:\s*["\']?(.+?)["\']?\s*$', raw, re.MULTILINE)
    if title_match:
        titulo = title_match.group(1).strip().strip('"\'')
    else:
        h1_match = re.search(r'^#\s+(.+)$', raw, re.MULTILINE)
        if h1_match:
            titulo = h1_match.group(1).strip()

    # ── Limpeza do conteúdo ───────────────────────────────────────────────────
    conteudo = raw.strip()
    if conteudo.startswith("```markdown") or conteudo.startswith("```md"):
        conteudo = re.sub(r'^```(?:markdown|md)?\n', '', conteudo)
        conteudo = re.sub(r'\n```$', '', conteudo)
    conteudo = conteudo.strip()

    # ── Geração do Resumo para Carrossel ─────────────────────────────────────
    resumo_carrossel = _extrair_resumo_carrossel(api_key, titulo, conteudo)

    return {
        "titulo": titulo,
        "conteudo_markdown": conteudo,
        "resumo_carrossel": resumo_carrossel,
    }


def _extrair_resumo_carrossel(api_key: str, titulo: str, conteudo: str) -> list:
    """
    Extrai ou gera 4–6 pontos-chave do artigo para o carrossel PDF do LinkedIn.
    Usa uma segunda chamada leve ao Gemini.
    """
    prompt = f"""A partir do artigo abaixo sobre seguro estagiário, extraia exatamente 5 pontos-chave \
de alto impacto para um carrossel do LinkedIn. Cada ponto deve:
- Ter no máximo 20 palavras
- Ser direto, impactante e educativo
- Estar em português do Brasil

Retorne APENAS uma lista Python válida de strings, sem código extra, assim:
["Ponto 1 aqui", "Ponto 2 aqui", "Ponto 3 aqui", "Ponto 4 aqui", "Ponto 5 aqui"]

== ARTIGO ==
Título: {titulo}

{conteudo[:3000]}
"""

    try:
        raw = _call_gemini(api_key, prompt, temperature=0.5, max_tokens=500)
        # Tenta parsear a lista Python
        list_match = re.search(r'\[(.+?)\]', raw, re.DOTALL)
        if list_match:
            import ast
            pontos = ast.literal_eval(f"[{list_match.group(1)}]")
            if isinstance(pontos, list) and len(pontos) >= 3:
                return [str(p).strip() for p in pontos[:6]]
    except Exception:
        pass

    # Fallback: extrai bullets do próprio conteúdo
    bullets = []
    for line in conteudo.split('\n'):
        line = line.strip()
        if line.startswith(('- ', '* ', '• ')) and len(line) > 20:
            clean = line.lstrip('-*• ').strip()
            if len(clean.split()) <= 25:
                bullets.append(clean)
        if len(bullets) >= 5:
            break

    if not bullets:
        bullets = [
            "Seguro estagiário é obrigatório pela Lei 11.788/2008",
            "Empresa que não contrata seguro pode ter vínculo empregatício reconhecido",
            "A PASI cobre acidentes pessoais durante o período de estágio",
            "Emissão online em minutos com a Nautiplus",
            "Apólice digital enviada imediatamente por e-mail",
        ]

    return bullets[:6]
