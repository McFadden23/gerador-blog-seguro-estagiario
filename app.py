"""
app.py — Painel de Controle e Monitoramento do Agente Autônomo de SEO/GEO.

Foco: Ranquear https://nautiplus.com.br/landingpages/estagiario/pasi/
para a busca "seguro estagiário".

Ciclo de Growth:
    1. Gera artigo otimizado (gerar_artigo_autonomo)
    2. Publica no WordPress (publicar_artigo_wp)
    3. Gera PDF Carrossel LinkedIn (gerar_pdf_carrossel)
    4. Atualiza estratégia autônoma (atualizar_estrategia_autonoma)
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st

# ── Adiciona src/ ao path ──────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from src.generator  import gerar_artigo_autonomo
from src.publisher  import publicar_artigo_wp
from src.pdf_exporter import gerar_pdf_carrossel
from src.analytics  import (
    carregar_estado,
    salvar_estado,
    registrar_execucao,
    atualizar_estrategia_autonoma,
    formatar_historico_para_exibicao,
)

DATA_DIR    = ROOT_DIR / "data"
ASSETS_DIR  = ROOT_DIR / "assets"
WORKSPACE_DIR = ROOT_DIR / "workspace"

# ── Configuração da Página ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Agente SEO/GEO — Nautiplus",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS Personalizado ──────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Paleta institucional */
:root {
    --primary:   #00B7AA;
    --secondary: #12477B;
    --accent:    #E87722;
    --bg-card:   #F8FAFC;
    --text-dark: #1E293B;
    --text-muted:#64748B;
    --success:   #10B981;
    --border:    #E2E8F0;
}

/* Card de métricas */
.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.metric-card .label {
    font-size: 0.78rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-bottom: .3rem;
}
.metric-card .value {
    font-size: 1.7rem;
    font-weight: 700;
    color: var(--secondary);
}
.metric-card .sub {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: .2rem;
}

/* Badge de status */
.badge {
    display: inline-block;
    padding: .22rem .7rem;
    border-radius: 9999px;
    font-size: .75rem;
    font-weight: 600;
    letter-spacing: .04em;
}
.badge-green  { background:#D1FAE5; color:#065F46; }
.badge-blue   { background:#DBEAFE; color:#1E40AF; }
.badge-orange { background:#FEF3C7; color:#92400E; }

/* Cabeçalho hero */
.hero-header {
    background: linear-gradient(135deg, var(--secondary) 0%, #1a5fa8 100%);
    border-radius: 16px;
    padding: 2rem 2.4rem;
    margin-bottom: 1.5rem;
    color: white;
}
.hero-header h1 { margin: 0; font-size: 1.9rem; font-weight: 800; }
.hero-header p  { margin: .4rem 0 0; opacity: .85; font-size: .95rem; }

/* Regras atuais */
.rules-box {
    background: #EFF6FF;
    border-left: 4px solid var(--primary);
    border-radius: 0 8px 8px 0;
    padding: .9rem 1.1rem;
    font-size: .85rem;
    color: var(--text-dark);
}

/* Log de histórico */
.history-entry {
    background: white;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: .8rem;
}
.history-entry .ciclo-badge {
    display: inline-block;
    background: var(--secondary);
    color: white;
    border-radius: 6px;
    padding: .15rem .5rem;
    font-size: .72rem;
    font-weight: 700;
    margin-right: .5rem;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Configurações
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Configurações do Agente")
    st.markdown("---")

    # ── Gemini API Key ────────────────────────────────────────────────────────
    st.markdown("### 🤖 Google Gemini")
    default_key = os.getenv("GEMINI_API_KEY", "")
    api_key = st.text_input(
        "GEMINI_API_KEY",
        value=default_key,
        type="password",
        placeholder="AIzaSy...",
        help="Obtenha em https://aistudio.google.com/app/apikey",
    )
    if api_key.strip():
        st.success("✅ API Key configurada")
        has_key = True
    else:
        st.warning("⚠️ Insira sua GEMINI_API_KEY")
        has_key = False

    st.markdown("---")

    # ── WordPress ─────────────────────────────────────────────────────────────
    st.markdown("### 📝 WordPress")
    blog_url = st.text_input(
        "URL do Blog",
        value="https://nautiplus.com.br/blog/",
        help="URL base do WordPress (com /blog/ no final)",
    )
    wp_user = st.text_input(
        "Usuário WP",
        value="",
        placeholder="admin ou seu usuário WP",
    )
    wp_pass = st.text_input(
        "Senha de Aplicação WP",
        value="ULvV BgVf vGcF 21KO U4Eo PINx",
        type="password",
        help="Application Password gerada no painel do WordPress",
    )

    st.markdown("---")

    # ── Informações do Agente ─────────────────────────────────────────────────
    st.markdown("### 🎯 Objetivo do Agente")
    st.markdown("""
**Ranquear para:** seguro estagiário

**Landing Page Alvo:**
`nautiplus.com.br/landingpages/estagiario/pasi/`

**Âncoras obrigatórias:**
- contratar seguro estagiário
- seguro PASI para estagiários
- seguro obrigatório Lei 11.788
""")


# ═══════════════════════════════════════════════════════════════════════════════
# CARREGAMENTO DO ESTADO
# ═══════════════════════════════════════════════════════════════════════════════
state = carregar_estado(DATA_DIR)
history = state.get("history", [])
rules   = state.get("current_rules", {})
ciclo_atual = len(history) + 1

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER HERO
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="hero-header">
    <h1>🚀 Agente Autônomo de SEO/GEO</h1>
    <p>
        <strong>Nautiplus · Seguro Estágio Rápido</strong> &nbsp;|&nbsp;
        Ciclo atual: <strong>#{ciclo_atual}</strong> &nbsp;|&nbsp;
        Foco: <strong>seguro estagiário</strong>
    </p>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 1 — STATUS DO AGENTE
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("### 📊 Status do Agente")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Publicações Realizadas</div>
        <div class="value">{len(history)}</div>
        <div class="sub">total de ciclos</div>
    </div>""", unsafe_allow_html=True)

with col2:
    ultimo = history[-1] if history else {}
    ultima_data = ultimo.get("timestamp", "—")[:10] if ultimo else "—"
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Última Publicação</div>
        <div class="value" style="font-size:1.2rem">{ultima_data}</div>
        <div class="sub">data da última execução</div>
    </div>""", unsafe_allow_html=True)

with col3:
    tom_atual = rules.get("tone", "autônomo/persuasivo")
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Tom Atual</div>
        <div class="value" style="font-size:1.0rem">{tom_atual}</div>
        <div class="sub">regra de escrita ativa</div>
    </div>""", unsafe_allow_html=True)

with col4:
    anchor = rules.get("anchor_link_density", "alto")
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Densidade de Âncoras</div>
        <div class="value">{anchor.upper()}</div>
        <div class="sub">links para a landing page</div>
    </div>""", unsafe_allow_html=True)

# ── Regras atuais ─────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
faq_flag   = "✅ Ativo" if rules.get("include_faq") else "❌ Inativo"
table_flag = "✅ Ativo" if rules.get("include_comparison_table") else "❌ Inativo"
max_par    = rules.get("max_paragraphs_per_section", 3)

st.markdown(f"""
<div class="rules-box">
    <strong>Regras do Ciclo #{ciclo_atual}:</strong> &nbsp;
    Tom: <code>{tom_atual}</code> &nbsp;·&nbsp;
    FAQ: {faq_flag} &nbsp;·&nbsp;
    Tabela Comparativa: {table_flag} &nbsp;·&nbsp;
    Parágrafos/Seção: <code>{max_par}</code> &nbsp;·&nbsp;
    Âncoras: <code>{anchor}</code>
</div>
""", unsafe_allow_html=True)

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 2 — BOTÃO DE AÇÃO PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("### ⚡ Executar Ciclo de Growth")

if not has_key:
    st.info("🔑 Insira sua **GEMINI_API_KEY** na sidebar para habilitar o agente.")

btn_disabled = not has_key
run_clicked = st.button(
    "🚀 Executar Ciclo de Growth Agora",
    type="primary",
    disabled=btn_disabled,
    use_container_width=True,
    help="Gera artigo → Publica no WP → Gera PDF Carrossel → Atualiza Estratégia",
)

# ── Execução do Ciclo ─────────────────────────────────────────────────────────
if run_clicked and has_key:
    resultado = {
        "artigo": None,
        "publicacao": None,
        "pdf_bytes": None,
        "erro": None,
    }

    with st.status("🤖 Executando Ciclo de Growth Autônomo...", expanded=True) as status:

        # ── ETAPA 1: Geração do Artigo ────────────────────────────────────────
        st.write("📝 **Etapa 1/4** — Gerando artigo otimizado para SEO/GEO...")
        try:
            artigo = gerar_artigo_autonomo(
                api_key=api_key.strip(),
                state=state,
            )
            resultado["artigo"] = artigo
            st.write(f"   ✅ Artigo gerado: **{artigo['titulo']}**")
            st.write(f"   📌 {len(artigo.get('resumo_carrossel', []))} pontos para o carrossel extraídos")
        except Exception as e:
            err_msg = str(e)
            err_lower = err_msg.lower()
            if "429" in err_msg or "quota" in err_lower or "resource_exhausted" in err_lower:
                resultado["erro"] = f"⚠️ Limite de quota da API Gemini atingido (429). Aguarde alguns minutos e tente novamente.\n\nDetalhe: {err_msg}"
            elif "403" in err_msg or "permission_denied" in err_lower:
                resultado["erro"] = f"❌ Permissão negada (403). Verifique se a GEMINI_API_KEY está correta e ativa.\n\nDetalhe: {err_msg}"
            else:
                resultado["erro"] = f"❌ Erro ao gerar artigo: {err_msg}"
            status.update(label="❌ Ciclo interrompido na Etapa 1", state="error")

        # ── ETAPA 2: Publicação no WordPress ─────────────────────────────────
        if resultado["artigo"] and not resultado["erro"]:
            st.write("📤 **Etapa 2/4** — Publicando no WordPress...")
            artigo = resultado["artigo"]
            if wp_user.strip() and wp_pass.strip():
                pub = publicar_artigo_wp(
                    titulo=artigo["titulo"],
                    conteudo_markdown=artigo["conteudo_markdown"],
                    wp_user=wp_user.strip(),
                    wp_app_pass=wp_pass.strip(),
                    blog_url=blog_url.strip(),
                )
                resultado["publicacao"] = pub
                if pub["success"]:
                    st.write(f"   ✅ Publicado em: {pub['post_url']}")
                else:
                    st.write(f"   ⚠️ Publicação falhou: {pub['error']}")
                    st.write("   ℹ️ O ciclo continua (artigo gerado está disponível para download).")
            else:
                resultado["publicacao"] = {
                    "success": False,
                    "post_url": None,
                    "post_id": None,
                    "error": "Credenciais WP não fornecidas — publicação ignorada.",
                }
                st.write("   ℹ️ Credenciais WP não configuradas — publicação ignorada.")

        # ── ETAPA 3: Geração do PDF Carrossel ────────────────────────────────
        if resultado["artigo"] and not resultado["erro"]:
            st.write("📱 **Etapa 3/4** — Gerando PDF Carrossel para LinkedIn...")
            artigo  = resultado["artigo"]
            pub     = resultado["publicacao"] or {}
            post_url_para_cta = pub.get("post_url") if pub.get("success") else None
            try:
                pdf_bytes = gerar_pdf_carrossel(
                    resumo_carrossel=artigo.get("resumo_carrossel", []),
                    titulo=artigo["titulo"],
                    assets_dir=ASSETS_DIR,
                    workspace_dir=WORKSPACE_DIR,
                    post_url=post_url_para_cta,
                )
                resultado["pdf_bytes"] = pdf_bytes
                st.write(f"   ✅ PDF gerado ({len(pdf_bytes) // 1024} KB)")
            except Exception as e:
                st.write(f"   ⚠️ Erro ao gerar PDF: {e}")

        # ── ETAPA 4: Atualização da Estratégia ────────────────────────────────
        if resultado["artigo"] and not resultado["erro"]:
            st.write("🧠 **Etapa 4/4** — Atualizando estratégia autônoma para o próximo ciclo...")
            artigo = resultado["artigo"]
            pub    = resultado["publicacao"] or {}
            post_url_salvo = pub.get("post_url") if pub.get("success") else None

            # Registra execução no histórico
            entrada = registrar_execucao(
                post_url=post_url_salvo,
                titulo=artigo["titulo"],
                estado_atual=state,
            )
            state["history"].append(entrada)

            # Evolui as regras para o próximo ciclo
            state = atualizar_estrategia_autonoma(state)
            salvar_estado(state, DATA_DIR)

            proximas_rules = state.get("current_rules", {})
            st.write(f"   ✅ Estratégia atualizada — próximo ciclo: tom **{proximas_rules.get('tone')}**")
            status.update(label="✅ Ciclo de Growth concluído com sucesso!", state="complete")

        elif resultado["erro"]:
            pass  # Status já foi atualizado acima
        else:
            status.update(label="✅ Ciclo parcialmente concluído", state="complete")

    # Persiste resultados na session_state para as abas
    st.session_state["ultimo_artigo"]    = resultado.get("artigo")
    st.session_state["ultima_publicacao"] = resultado.get("publicacao")
    st.session_state["ultimo_pdf"]       = resultado.get("pdf_bytes")
    st.session_state["erro_ciclo"]       = resultado.get("erro")

    if resultado.get("erro"):
        st.error(resultado["erro"])
    elif not resultado.get("artigo"):
        st.warning("Nenhum artigo gerado neste ciclo.")
    else:
        st.success("🎉 Ciclo de Growth concluído! Confira as abas abaixo.")
        st.rerun()


st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 3 — ABAS
# ═══════════════════════════════════════════════════════════════════════════════
tab1, tab2 = st.tabs([
    "📰 Última Publicação & Download do Carrossel",
    "🧠 Log de Aprendizado do Agente",
])


# ── ABA 1: Última Publicação ──────────────────────────────────────────────────
with tab1:
    artigo_ss = st.session_state.get("ultimo_artigo")
    pub_ss    = st.session_state.get("ultima_publicacao")
    pdf_ss    = st.session_state.get("ultimo_pdf")

    if not artigo_ss and history:
        # Sem session_state, usa o último histórico
        ultimo_entry = history[-1]
        st.markdown(f"""
        <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;padding:1rem 1.4rem;">
            <h4 style="margin:0 0 .4rem;color:#065F46;">✅ Último Artigo Publicado</h4>
            <p style="margin:0;font-size:.9rem;color:#1E293B;">
                <strong>{ultimo_entry.get('titulo', '—')}</strong><br>
                <span style="color:#64748B;">Publicado em {ultimo_entry.get('timestamp','')[:16].replace('T',' ')}</span>
            </p>
        </div>
        """, unsafe_allow_html=True)
        if ultimo_entry.get("post_url"):
            st.markdown(f"🔗 **URL do Post:** [{ultimo_entry['post_url']}]({ultimo_entry['post_url']})")
        st.info("Execute um novo ciclo para gerar o PDF carrossel e disponibilizá-lo para download aqui.")

    elif artigo_ss:
        titulo_art = artigo_ss.get("titulo", "Artigo")
        import re as _re
        slug = _re.sub(r'[^a-z0-9]+', '-', titulo_art.lower()).strip('-')[:60]

        st.markdown(f"### 📄 {titulo_art}")

        # Link do post
        if pub_ss and pub_ss.get("success") and pub_ss.get("post_url"):
            url = pub_ss["post_url"]
            st.markdown(f"""
            <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;padding:.9rem 1.2rem;margin-bottom:1rem;">
                🎉 <strong>Post publicado com sucesso!</strong><br>
                🔗 <a href="{url}" target="_blank">{url}</a>
            </div>
            """, unsafe_allow_html=True)
        elif pub_ss and not pub_ss.get("success"):
            err_pub = pub_ss.get("error", "Erro desconhecido")
            st.warning(f"⚠️ Publicação no WP não realizada: {err_pub}")

        # Downloads
        col_md, col_pdf = st.columns(2)

        with col_md:
            st.download_button(
                label="📥 Baixar Artigo em Markdown (.md)",
                data=artigo_ss.get("conteudo_markdown", ""),
                file_name=f"{slug}.md",
                mime="text/markdown",
                use_container_width=True,
            )

        with col_pdf:
            if pdf_ss:
                st.download_button(
                    label="📱 Baixar Carrossel LinkedIn (PDF)",
                    data=pdf_ss,
                    file_name=f"{slug}_carrossel_linkedin.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.button(
                    "📱 PDF não disponível",
                    disabled=True,
                    use_container_width=True,
                )

        # Preview do artigo
        with st.expander("👁️ Pré-visualização do Artigo", expanded=False):
            content = artigo_ss.get("conteudo_markdown", "")
            # Remove frontmatter para renderização limpa
            import re as _re2
            body = _re2.sub(r'^---\n.*?\n---\n?', '', content, flags=_re2.DOTALL).strip()
            st.markdown(body)

        # Pontos do carrossel
        pontos = artigo_ss.get("resumo_carrossel", [])
        if pontos:
            with st.expander("📌 Pontos do Carrossel Gerados", expanded=False):
                for i, p in enumerate(pontos, 1):
                    st.markdown(f"**{i}.** {p}")
    else:
        st.info("ℹ️ Nenhum ciclo executado ainda nesta sessão. Clique em **Executar Ciclo de Growth** para começar.")
        st.markdown("""
        O ciclo irá:
        1. **Gerar** um artigo SEO/GEO sobre seguro estagiário
        2. **Publicar** automaticamente no WordPress Nautiplus
        3. **Criar** o PDF Carrossel para LinkedIn
        4. **Registrar** e **evoluir** a estratégia de conteúdo
        """)


# ── ABA 2: Log de Aprendizado ────────────────────────────────────────────────
with tab2:
    # Recarrega state atualizado
    state_atual = carregar_estado(DATA_DIR)
    hist = state_atual.get("history", [])

    st.markdown("### 🧠 Evolução Autônoma das Regras de Conteúdo")
    st.markdown(
        "O agente ajusta automaticamente as regras de escrita a cada ciclo para testar "
        "diferentes abordagens de SEO/GEO e identificar o que performa melhor."
    )

    if not hist:
        st.info("📭 Nenhuma execução registrada ainda. Execute o primeiro ciclo de Growth para ver o aprendizado aqui.")
    else:
        # ── Tabela resumida ───────────────────────────────────────────────────
        rows = formatar_historico_para_exibicao(hist)

        import pandas as pd
        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "URL": st.column_config.LinkColumn("URL do Post"),
                "Ciclo": st.column_config.NumberColumn("Ciclo", width="small"),
            }
        )

        st.markdown("---")
        st.markdown("#### 📋 Detalhes por Ciclo")

        for entry in reversed(hist):
            ciclo_n  = entry.get("ciclo", "?")
            titulo_e = entry.get("titulo", "—")
            ts       = entry.get("timestamp", "")[:16].replace("T", " ")
            url_e    = entry.get("post_url") or "Não publicado"
            r_used   = entry.get("rules_used", {})

            badge_color = "#065F46" if entry.get("post_url") else "#92400E"
            badge_bg    = "#D1FAE5" if entry.get("post_url") else "#FEF3C7"
            badge_txt   = "✅ Publicado" if entry.get("post_url") else "⚠️ Não publicado"

            st.markdown(f"""
            <div class="history-entry">
                <div style="display:flex;align-items:center;gap:.6rem;margin-bottom:.5rem;">
                    <span class="ciclo-badge">Ciclo #{ciclo_n}</span>
                    <span style="font-weight:600;color:#1E293B;">{titulo_e}</span>
                    <span style="margin-left:auto;background:{badge_bg};color:{badge_color};
                                 padding:.15rem .55rem;border-radius:9999px;font-size:.72rem;font-weight:600;">
                        {badge_txt}
                    </span>
                </div>
                <div style="font-size:.8rem;color:#64748B;margin-bottom:.6rem;">
                    🕐 {ts} &nbsp;&nbsp;
                    {"🔗 <a href='" + url_e + "' target='_blank'>" + url_e[:60] + "...</a>" if entry.get("post_url") else "📭 " + url_e}
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:.5rem;font-size:.78rem;">
                    <span style="background:#EFF6FF;color:#1D4ED8;padding:.15rem .5rem;border-radius:6px;">
                        🎨 Tom: <strong>{r_used.get("tone", "—")}</strong>
                    </span>
                    <span style="background:#F0FDF4;color:#166534;padding:.15rem .5rem;border-radius:6px;">
                        📋 FAQ: <strong>{"Sim" if r_used.get("include_faq") else "Não"}</strong>
                    </span>
                    <span style="background:#FFF7ED;color:#9A3412;padding:.15rem .5rem;border-radius:6px;">
                        📊 Tabela: <strong>{"Sim" if r_used.get("include_comparison_table") else "Não"}</strong>
                    </span>
                    <span style="background:#F5F3FF;color:#5B21B6;padding:.15rem .5rem;border-radius:6px;">
                        🔗 Âncoras: <strong>{r_used.get("anchor_link_density", "—")}</strong>
                    </span>
                    <span style="background:#FDF2F8;color:#701A75;padding:.15rem .5rem;border-radius:6px;">
                        📝 Par/Seção: <strong>{r_used.get("max_paragraphs_per_section", "—")}</strong>
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ── Próximas regras (preview) ────────────────────────────────────────
        st.markdown("---")
        next_rules = state_atual.get("current_rules", {})
        st.markdown("#### 🔮 Regras para o Próximo Ciclo (Preview)")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.markdown(f"""
            - **Tom:** `{next_rules.get("tone", "—")}`
            - **FAQ:** {"✅ Ativo" if next_rules.get("include_faq") else "❌ Inativo"}
            - **Tabela Comparativa:** {"✅ Ativo" if next_rules.get("include_comparison_table") else "❌ Inativo"}
            """)
        with col_r2:
            st.markdown(f"""
            - **Âncoras:** `{next_rules.get("anchor_link_density", "—")}`
            - **Parágrafos/Seção:** `{next_rules.get("max_paragraphs_per_section", "—")}`
            - **Keyword:** `seguro estagiário`
            """)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#94A3B8;font-size:.78rem;'>"
    "🚀 Agente Autônomo de SEO/GEO · Nautiplus · Seguro Estágio Rápido · "
    "<a href='https://nautiplus.com.br/landingpages/estagiario/pasi/' target='_blank' style='color:#00B7AA;'>"
    "Contratar Seguro Estagiário</a>"
    "</p>",
    unsafe_allow_html=True,
)
