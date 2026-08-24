import os
import re
from pathlib import Path
from datetime import datetime, date
import yaml
import streamlit as st

# Tenta carregar os SDKs do Gemini
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


# ── Configuração da Página do Streamlit ─────────────────────────────────────────
st.set_page_config(
    page_title="Gerador de Blog Posts — Nautiplus",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Carregamento de Diretrizes do Projeto ───────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent

def load_project_guidelines() -> dict:
    """Carrega os 3 arquivos centrais consolidados de workspace/ e diretrizes gerais."""
    guidelines = {
        "diretrizes": "",
        "estrategia": "",
        "exemplo": "",
        "context": "",
        "antigravity": ""
    }

    paths = {
        "antigravity": [ROOT_DIR / "Antigravity.md", ROOT_DIR / "ANTIGRAVITY.md"],
        "context": [ROOT_DIR / "CONTEXT.md", ROOT_DIR / "context.md"],
        "diretrizes": [ROOT_DIR / "workspace/01_diretrizes_e_tom.md"],
        "estrategia": [ROOT_DIR / "workspace/02_seo_geo_estrategia.md"],
        "exemplo": [ROOT_DIR / "workspace/03_exemplo_campeao.md"],
    }

    for key, candidate_paths in paths.items():
        for p in candidate_paths:
            if p.exists():
                try:
                    guidelines[key] = p.read_text(encoding="utf-8")
                    break
                except Exception:
                    pass
    return guidelines


def load_settings() -> dict:
    """Carrega as configurações do settings.yaml se existir."""
    settings_file = ROOT_DIR / "config/settings.yaml"
    if settings_file.exists():
        try:
            return yaml.safe_load(settings_file.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}


# ── Função de Geração Autônoma de Conteúdo via Gemini ─────────────────────────
def generate_autonomous_article_with_gemini(api_key: str, guidelines: dict, settings: dict) -> tuple[dict, str]:
    """
    Executa a ideação autônoma (pesquisa de dúvidas e temas quentes) e a redação completa
    usando os 3 arquivos de workspace/, priorizando SEO/GEO e Few-Shot learning do exemplo campeão.
    """
    preferred_model = settings.get("ai", {}).get("model", "gemini-3.7-flash")
    candidate_models = [
        preferred_model,
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.1-pro",
    ]
    candidate_models = list(dict.fromkeys(candidate_models))

    # 1. Prompt de Ideação e Seleção Autônoma
    ideation_prompt = f"""Você é o estrategista-chefe de SEO e GEO da Nautiplus / Seguro Estágio Rápido.

== DIRETRIZES DO PROJETO ==
{guidelines.get('diretrizes', '')}

== ESTRATÉGIA DE SEO E GEO ==
{guidelines.get('estrategia', '')}

== TAREFA DE PESQUISA & SELEÇÃO AUTÔNOMA ==
1. Pesquise e identifique as dúvidas mais frequentes, temas quentes, dores de RH, custos operacionais e riscos trabalhistas urgentes relacionados a Seguro Estágio e à Lei do Estágio nº 11.788/2008.
2. Analise o potencial de busca orgânica (SEO) e capacidade de resposta direta para IAs (GEO).
3. Escolha AUTONOMAMENTE a pauta ÚNICA de maior relevância e impacto para redigir agora.

== FORMATO DE SAÍDA OBRIGATÓRIO (YAML) ==
Retorne APENAS o bloco YAML abaixo preenchido:
```yaml
titulo: "Título SEO de Alto Impacto"
subtitulo: "Subtítulo explicativo com gancho"
slug: "slug-kebab-case-otimizado"
angulo: "Ângulo editorial e dor principal resolvida"
publico: "Empresas contratantes e profissionais de RH"
palavras_chave: ["palavra1", "palavra2", "palavra3"]
motivo_escolha: "Justificativa da escolha com base em busca e conformidade legal"
```
"""

    def _call_gemini_with_fallback(prompt_text: str) -> str:
        last_err = None
        if HAS_GOOGLE_GENAI:
            client = genai.Client(api_key=api_key)
            for mod in candidate_models:
                try:
                    res = client.models.generate_content(
                        model=mod,
                        contents=prompt_text,
                        config=types.GenerateContentConfig(
                            temperature=float(settings.get("ai", {}).get("temperature", 0.7)),
                            max_output_tokens=settings.get("ai", {}).get("max_output_tokens", 4096),
                        )
                    )
                    if res and res.text:
                        return res.text
                except Exception as err:
                    last_err = err
                    err_str = str(err).lower()
                    # Não tenta fallback se for erro de quota (429) ou permissão (403), propaga para tratamento
                    if "429" in str(err) or "quota" in err_str or "resource_exhausted" in err_str or "403" in str(err) or "permission_denied" in err_str:
                        raise err
                    if "404" in err_str or "not_found" in err_str or "503" in err_str or "unavailable" in err_str or "demand" in err_str:
                        continue
                    raise err

        if HAS_LEGACY_GENAI:
            legacy_genai.configure(api_key=api_key)
            for mod in candidate_models:
                try:
                    model = legacy_genai.GenerativeModel(mod)
                    res = model.generate_content(prompt_text)
                    if res and res.text:
                        return res.text
                except Exception as err:
                    last_err = err
                    err_str = str(err).lower()
                    if "429" in str(err) or "quota" in err_str or "resource_exhausted" in err_str or "403" in str(err) or "permission_denied" in err_str:
                        raise err
                    if "404" in err_str or "not_found" in err_str or "503" in err_str or "unavailable" in err_str or "demand" in err_str:
                        continue
                    raise err

        if last_err:
            raise last_err
        raise ImportError("Nenhuma biblioteca compatível do Gemini encontrada.")

    # Passo 1: Executa a Ideação
    ideation_raw = _call_gemini_with_fallback(ideation_prompt)
    idea_match = re.search(r"```(?:yaml)?\n(.*?)```", ideation_raw, re.DOTALL)
    idea_yaml = idea_match.group(1) if idea_match else ideation_raw

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
            "titulo": "Lei 11.788/2008 não é sugestão: Compliance no Onboarding de Estagiários",
            "subtitulo": "A ausência ou irregularidade no Seguro de Acidentes Pessoais gera caracterização de vínculo empregatício",
            "slug": "compliance-onboarding-estagiarios",
            "angulo": "Eliminar passivos trabalhistas e latência na contratação de estagiários",
            "palavras_chave": ["seguro estagio", "lei 11788", "passivo trabalhista"],
            "motivo_escolha": "Tema crítico de conformidade e mitigação de risco financeiro para empresas."
        }

    # Passo 2: Prompt de Redação Completa (com Few-Shot Demonstration e prioridade SEO/GEO)
    today = date.today().isoformat()
    tags = chosen_idea.get("palavras_chave", ["seguro estagio", "lei 11788", "compliance", "onboarding"])

    draft_prompt = f"""Você é o redator oficial da Nautiplus / Seguro Estágio Rápido, especialista em seguro para estagiários, onboarding de RH e conformidade com a Lei nº 11.788/2008.

== DIRETRIZES DE IDENTIDADE, TOM E COMPLIANCE (01_diretrizes_e_tom.md) ==
{guidelines.get('diretrizes', '')}

== DIRETRIZES DE OTIMIZAÇÃO SEO & GEO - PREFERÊNCIA DE ESTRUTURAÇÃO (02_seo_geo_estrategia.md) ==
{guidelines.get('estrategia', '')}

== EXEMPLO CAMPEÃO PADRÃO-OURO - FEW-SHOT DEMONSTRATION (03_exemplo_campeao.md) ==
Use o exemplo abaixo como referência de tom, ritmo, concisão e autoridade técnica para que o post tenha o estilo exato do projeto:
{guidelines.get('exemplo', '')}

== DADOS DA PAUTA SELECIONADA ==
- Título: {chosen_idea.get('titulo', '')}
- Subtítulo: {chosen_idea.get('subtitulo', '')}
- Slug: {chosen_idea.get('slug', '')}
- Ângulo Editorial: {chosen_idea.get('angulo', '')}
- Palavras-chave: {', '.join(chosen_idea.get('palavras_chave', []))}
- Data: {today}

== REQUISITOS OBRIGATÓRIOS DO ARTIGO ==
1. Extensão: 3 a 5 parágrafos no máximo, entregando alto valor informativo de forma direta ao ponto.
2. Otimização GEO: Forneça a resposta direta e a dor central logo no 1º parágrafo.
3. Otimização SEO: Títulos H2/H3 bem posicionados e tópicos organizados em tópicos/lista.
4. Jamais utilize traços duplos "--".
5. Inicie com o bloco de Frontmatter YAML completo:
---
title: "{chosen_idea.get('titulo', '')}"
subtitle: "{chosen_idea.get('subtitulo', '')}"
slug: "{chosen_idea.get('slug', '')}"
status: "draft"
created_at: "{datetime.now().isoformat()}"
updated_at: "{datetime.now().isoformat()}"
author: "{settings.get('blog', {}).get('author', 'Nautiplus Editorial')}"
category: "Seguro Estágio"
tags:
  - seguro estagio
  - lei 11788
  - compliance
  - onboarding
seo:
  meta_description: "{chosen_idea.get('subtitulo', '')[:160]}"
  focus_keyword: "{chosen_idea.get('palavras_chave', ['seguro estagio'])[0]}"
---

Escreva o artigo completo agora em Markdown:
"""

    article_raw = _call_gemini_with_fallback(draft_prompt)
    return chosen_idea, article_raw


import io
import markdown2
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
from src.pdf_exporter import generate_linkedin_carousel_pdf, get_brand_colors


def generate_pdf_bytes(content: str, config: dict) -> bytes:
    """Gera um PDF estilizado diretamente em memória (bytes) a partir do conteúdo Markdown."""
    # Separa frontmatter do corpo
    match = re.match(r"^---\n(.*?)\n---\n?(.*)", content, re.DOTALL)
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1)) or {}
            body_md = match.group(2).strip()
        except yaml.YAMLError:
            frontmatter = {}
            body_md = content.strip()
    else:
        frontmatter = {}
        body_md = content.strip()

    # Converte corpo Markdown para HTML
    body_html = markdown2.markdown(
        body_md,
        extras=["fenced-code-blocks", "tables", "strike", "header-ids"]
    )

    pdf_cfg = config.get("pdf", {})
    blog_cfg = config.get("blog", {})
    assets_dir = ROOT_DIR / "assets"
    logo_path = assets_dir / "Logo_nautiplus.png"
    if not logo_path.exists():
        logo_path = assets_dir / "logo.png"
    logo_exists = logo_path.exists()
    css_path = ROOT_DIR / pdf_cfg.get("stylesheet", "assets/pdf_style.css")

    # Formatação de data
    raw_date = frontmatter.get("publish_date") or date.today().isoformat()
    try:
        dt = datetime.fromisoformat(str(raw_date))
        formatted_date = dt.strftime("%d/%m/%Y")
    except Exception:
        formatted_date = str(raw_date)

    ctx = {
        "title": frontmatter.get("title", "(sem título)"),
        "subtitle": frontmatter.get("subtitle", ""),
        "meta_description": frontmatter.get("meta_description") or (frontmatter.get("seo", {}) if isinstance(frontmatter.get("seo"), dict) else {}).get("meta_description", ""),
        "author": frontmatter.get("author") or blog_cfg.get("author", "Nautiplus Editorial"),
        "publish_date": formatted_date,
        "blog_name": blog_cfg.get("blog_name", "Nautiplus"),
        "blog_url": blog_cfg.get("blog_url", "https://nautiplus.com.br"),
        "year": date.today().year,
        "logo_path": logo_path.as_posix() if logo_exists else "",
        "logo_exists": logo_exists,
        "body_html": body_html,
        "css_path": css_path.as_posix(),
        "assets_dir": assets_dir.as_posix(),
        "brand_primary": pdf_cfg.get("brand_color_primary", "#1A3C6E"),
        "brand_accent": pdf_cfg.get("brand_color_accent", "#E87722"),
        "font_heading": pdf_cfg.get("font_heading", "Helvetica"),
        "font_body": pdf_cfg.get("font_body", "Helvetica"),
    }

    template_path = ROOT_DIR / pdf_cfg.get("template", "assets/pdf_template.html")
    env = Environment(loader=FileSystemLoader(str(template_path.parent)))
    template = env.get_template(template_path.name)
    html_content = template.render(**ctx)

    pdf_buffer = io.BytesIO()
    result = pisa.CreatePDF(
        src=html_content,
        dest=pdf_buffer,
        encoding="utf-8",
    )
    if result.err:
        raise RuntimeError(f"Erro ao compilar PDF: {result.err} erros encontrados.")

    return pdf_buffer.getvalue()


def sanitize_markdown(content: str) -> str:
    """Remove eventuais blocos de código triplo delimitando o markdown inteiro."""
    cleaned = content.strip()
    if cleaned.startswith("```markdown") or cleaned.startswith("```md"):
        cleaned = re.sub(r"^```(?:markdown|md)?\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned)
    return cleaned.strip()


def extract_slug(content: str, default_topic: str) -> str:
    """Extrai o slug do frontmatter YAML ou gera a partir do tópico."""
    match = re.search(r"slug:\s*[\"']?([^\"'\n]+)[\"']?", content)
    if match:
        return match.group(1).strip()
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", default_topic).strip().lower()
    return re.sub(r"[\s_]+", "-", slug) or "artigo-blog"


# ── Interface Streamlit ────────────────────────────────────────────────────────

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurações")
    st.markdown("Insira sua chave de API do **Google Gemini** para habilitar o gerador.")

    # Tenta recuperar chave do .env se existir para conveniência
    default_key = os.getenv("GEMINI_API_KEY", "")

    api_key_input = st.text_input(
        "🔑 Gemini API Key",
        value=default_key,
        type="password",
        placeholder="Cole aqui: AIzaSy...",
        help="Obtenha sua chave gratuita em https://aistudio.google.com/app/apikey"
    )

    if api_key_input.strip():
        st.success("✅ Chave de API pronta para uso!")
        has_valid_key = True
    else:
        st.warning("⚠️ Insira a GEMINI_API_KEY para liberar a geração.")
        has_valid_key = False

    model_choice = st.selectbox(
        "🤖 Modelo Gemini",
        options=[
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.1-pro",
        ],
        index=0,
        help="Selecione o modelo desejado. Modelos flash são mais rápidos e eficientes."
    )

    st.markdown("---")
    st.markdown("### 🏛️ Arquitetura Integrada (3 Arquivos)")
    st.caption("• `01_diretrizes_e_tom.md`: Identidade & Compliance")
    st.caption("• `02_seo_geo_estrategia.md`: SEO, GEO & Frontmatter")
    st.caption("• `03_exemplo_campeao.md`: Padrão-Ouro & Referências")


# Área Principal
st.title("✍️ Gerador Autônomo de Blog — Nautiplus")
st.markdown(
    """
    Geração autônoma de artigos de alta autoridade baseada em **Pesquisa Ativa (Dúvidas & Riscos de RH)**,
    otimizada para **SEO** e **GEO** (Generative Engine Optimization) e fundamentada na **Lei nº 11.788/2008**.
    """
)

# Instruções de Uso
with st.expander("ℹ️ Como funciona a Geração Autônoma", expanded=False):
    st.markdown(
        """
        1. Insira sua **GEMINI_API_KEY** na barra lateral.
        2. Clique no botão **Pesquisar e Gerar Post Autônomo (SEO + GEO)**.
        3. O sistema analisa autonomamente os temas quentes e riscos trabalhistas para empresas, selecionando a pauta de maior impacto de busca.
        4. O artigo é redigido seguindo as 3 diretrizes consolidadas do `workspace/` com **Few-Shot Demonstration** do exemplo campeão.
        5. Copie com 1 clique ou baixe em **Markdown (.md)** ou **PDF Estilizado (.pdf)**.
        """
    )

generate_clicked = st.button(
    "🚀 Pesquisar e Gerar Post Autônomo (SEO + GEO)",
    type="primary",
    disabled=not has_valid_key,
    use_container_width=True,
    help="O Gemini pesquisará os temas mais quentes e redigirá o post completo automaticamente."
)

if generate_clicked:
    guidelines = load_project_guidelines()
    settings = load_settings()
    settings.setdefault("ai", {})["model"] = model_choice

    with st.spinner("🤖 Pesquisando temas quentes de RH/Lei 11.788 e gerando post autônomo otimizado (SEO + GEO)..."):
        try:
            chosen_idea, raw_article = generate_autonomous_article_with_gemini(
                api_key=api_key_input.strip(),
                guidelines=guidelines,
                settings=settings
            )
            article_content = sanitize_markdown(raw_article)
            st.session_state["generated_article"] = article_content
            st.session_state["chosen_idea"] = chosen_idea
            st.session_state["article_topic"] = chosen_idea.get("titulo", "artigo-autonomo")
            st.success(f"🎉 Pauta Selecionada e Artigo Gerado com Sucesso: **{chosen_idea.get('titulo', '')}**")
        except Exception as e:
            err_msg = str(e)
            err_lower = err_msg.lower()

            # Tratamento de Quota Exceeded / Erro 429
            if "429" in err_msg or "resource_exhausted" in err_lower or "quota exceeded" in err_lower or "quota" in err_lower:
                st.error("🚨 **Limite de Requisições Excedido (Erro 429 / Quota Exceeded)**")
                st.info(
                    "A cota de requisições do modelo selecionado foi atingida temporariamente na sua API Key. "
                    "👉 **Como continuar agora:** Vá ao menu lateral (**🤖 Modelo Gemini**), selecione outro modelo da lista (como `gemini-3.6-flash`, `gemini-3.5-flash` ou `gemini-3.1-pro`) e clique novamente no botão de geração."
                )
            # Tratamento de Permissão / Erro 403
            elif "403" in err_msg or "permission_denied" in err_lower:
                st.error("❌ **Erro 403: Permissão Negada (PERMISSION_DENIED)**")
                st.markdown(
                    """
                    **Possíveis causas e como resolver:**
                    1. **Chave Incorreta ou Inativa**: Verifique se a chave foi copiada integralmente de [Google AI Studio](https://aistudio.google.com/app/apikey).
                    2. **Restrições de IP/API Key**: Certifique-se de que a chave criada não possui restrições no Google Cloud Console.
                    3. **Tente um Modelo Diferente**: Altere o modelo no menu lateral para outra opção da lista.
                    """
                )
            # Tratamento de Alta Demanda / Erro 503
            elif "503" in err_msg or "unavailable" in err_lower or "high demand" in err_lower:
                st.warning("⚠️ **Alta Demanda Momentânea nos Servidores do Google (503 UNAVAILABLE)**")
                st.info("Os servidores do modelo selecionado estão com pico de acessos. Por favor, aguarde alguns segundos ou selecione outro modelo no menu lateral e tente novamente.")
            else:
                st.error(f"❌ Ocorreu um erro ao gerar o artigo: {err_msg}")

# Exibição do Resultado
if "generated_article" in st.session_state and st.session_state["generated_article"]:
    content = st.session_state["generated_article"]
    slug = extract_slug(content, st.session_state.get("article_topic", "artigo"))
    settings = load_settings()

    st.markdown("---")
    st.subheader("📄 Ações e Pré-visualização do Artigo")

    # Barra de Ações Rápidas (Downloads de Markdown, Carrossel LinkedIn e PDF Completo)
    col_md, col_carousel, col_pdf = st.columns(3)

    with col_md:
        st.download_button(
            label="📥 Baixar Markdown (.md)",
            data=content,
            file_name=f"{slug}_draft.md",
            mime="text/markdown",
            use_container_width=True,
            help="Baixar o arquivo completo com cabeçalho Frontmatter YAML para a esteira de publicação."
        )

    with col_carousel:
        try:
            carousel_pdf_bytes = generate_linkedin_carousel_pdf(
                content=content,
                workspace_dir=ROOT_DIR / "workspace",
                assets_dir=ROOT_DIR / "assets"
            )
            st.download_button(
                label="📱 Baixar Carrossel para LinkedIn (PDF)",
                data=carousel_pdf_bytes,
                file_name=f"{slug}_carrossel_linkedin.pdf",
                mime="application/pdf",
                use_container_width=True,
                help="Baixar carrossel no formato quadrado 1080x1080px com a identidade visual da Nautiplus para publicação direta no LinkedIn."
            )
        except Exception as carousel_err:
            st.error(f"Erro ao compilar Carrossel LinkedIn: {carousel_err}")

    with col_pdf:
        try:
            pdf_data = generate_pdf_bytes(content, settings)
            st.download_button(
                label="📄 Baixar Artigo em PDF (.pdf)",
                data=pdf_data,
                file_name=f"{slug}.pdf",
                mime="application/pdf",
                use_container_width=True,
                help="Baixar documento PDF completo diagramado com capa, cabeçalho e tipografia institucional."
            )
        except Exception as pdf_err:
            st.error(f"Erro ao compilar PDF: {pdf_err}")

    # Área de Cópia Rápida para Publicação Manual
    st.markdown("#### 📋 Copiar Conteúdo para Publicação Manual")
    st.caption("Passe o cursor sobre o bloco abaixo e clique no ícone de cópia 📋 (canto superior direito) para copiar instantaneamente:")
    st.code(content, language="markdown")

    # Abas com Visualizações
    tab_render, tab_raw = st.tabs(["👁️ Leitura Renderizada", "📝 Editor / Código Fonte"])
    with tab_render:
        st.markdown(content)
    with tab_raw:
        st.text_area(
            "Conteúdo em texto bruto (selecionável):",
            value=content,
            height=350,
            help="Você também pode selecionar todo o texto (Ctrl + A) e copiar (Ctrl + C)."
        )
