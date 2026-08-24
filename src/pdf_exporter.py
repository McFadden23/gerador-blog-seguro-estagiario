"""
pdf_exporter.py — Geração de PDF e Carrossel para LinkedIn (ReportLab).

Recursos:
- Exportação de Carrossel Quadrado (1080 x 1080 px) para LinkedIn
- Identidade visual dinâmica com alto contraste e legibilidade impecável
- Fundo claro (#FFFFFF / #F8F9FA), tipografia escura (#1E293B), títulos na cor primária da marca (#00B7AA / #12477B)
- Tratamento resiliente do logotipo (assets/Logo_nautiplus.png ou assets/logo.png)
"""

import io
import re
from pathlib import Path
from datetime import date, datetime
import yaml

from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.pdfgen import canvas

# ── Cores Padrão da Marca & Contraste ─────────────────────────────────────────
COLOR_PRIMARY_DEFAULT   = "#00B7AA"  # Verde-Água / Turquesa (Destaques e Títulos)
COLOR_SECONDARY_DEFAULT = "#12477B"  # Azul-Marinho (Títulos H1 e Barras)
COLOR_TEXT_DARK         = "#1E293B"  # Grafite Escuro para máxima legibilidade do corpo
COLOR_TEXT_MUTED        = "#64748B"  # Cinza neutro para rodapés e subtítulos secundários
COLOR_BG_DEFAULT        = "#FFFFFF"  # Fundo Branco puro para alto contraste


def get_brand_colors(workspace_dir: Path | None = None) -> dict:
    """Extrai cores da marca do arquivo workspace/01_diretrizes_e_tom.md mantendo contraste estrito."""
    colors = {
        "primary": COLOR_PRIMARY_DEFAULT,
        "secondary": COLOR_SECONDARY_DEFAULT,
        "text": COLOR_TEXT_DARK,
        "muted": COLOR_TEXT_MUTED,
        "bg": COLOR_BG_DEFAULT,
    }

    if workspace_dir:
        guideline_path = workspace_dir / "01_diretrizes_e_tom.md"
        if guideline_path.exists():
            try:
                text = guideline_path.read_text(encoding="utf-8")
                # Procura códigos hexadecimais no texto
                hex_codes = re.findall(r"#(?:[0-9a-fA-F]{3}){1,2}\b", text)
                if len(hex_codes) >= 2:
                    colors["primary"] = hex_codes[0]
                    colors["secondary"] = hex_codes[1]
            except Exception:
                pass

    return colors


class NumberedCanvas(canvas.Canvas):
    """Canvas de duas passagens para desenhar header, footer e numeração total de slides."""

    def __init__(self, *args, **kwargs):
        self.brand_colors = kwargs.pop("brand_colors", {})
        self.logo_path = kwargs.pop("logo_path", None)
        self.brand_name = kwargs.pop("brand_name", "Nautiplus · Seguro Estágio Rápido")
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        width, height = 1080, 1080
        c_primary = HexColor(self.brand_colors.get("primary", COLOR_PRIMARY_DEFAULT))
        c_secondary = HexColor(self.brand_colors.get("secondary", COLOR_SECONDARY_DEFAULT))
        c_muted = HexColor(self.brand_colors.get("muted", COLOR_TEXT_MUTED))
        c_bg = HexColor(self.brand_colors.get("bg", COLOR_BG_DEFAULT))

        # Fundo do slide (Branco / Claro)
        self.saveState()
        self.setFillColor(c_bg)
        self.rect(0, 0, width, height, fill=1, stroke=0)

        # ── Cabeçalho (Barra Superior com contraste e elegância) ───────────────
        bar_height = 110
        self.setFillColor(c_secondary)
        self.rect(0, height - bar_height, width, bar_height, fill=1, stroke=0)

        # Linha de destaque primária da marca
        self.setFillColor(c_primary)
        self.rect(0, height - bar_height - 8, width, 8, fill=1, stroke=0)

        # Renderiza Logo se existir
        logo_drawn = False
        if self.logo_path and Path(self.logo_path).exists():
            try:
                self.drawImage(
                    str(self.logo_path),
                    x=60,
                    y=height - bar_height + 15,
                    width=240,
                    height=80,
                    preserveAspectRatio=True,
                    mask="auto"
                )
                logo_drawn = True
            except Exception:
                logo_drawn = False

        if not logo_drawn:
            self.setFillColor(HexColor("#FFFFFF"))
            self.setFont("Helvetica-Bold", 32)
            self.drawString(60, height - bar_height + 40, "NAUTIPLUS")

        # ── Rodapé (Claro, Neutro e Elegante) ──────────────────────────────────
        footer_height = 80
        # Barra sutil acima do rodapé
        self.setStrokeColor(HexColor("#E2E8F0"))
        self.setLineWidth(2)
        self.line(60, footer_height, width - 60, footer_height)

        self.setFillColor(c_muted)
        self.setFont("Helvetica-Bold", 22)
        self.drawString(60, 36, self.brand_name)

        # Numeração de Slide (ex: Slide 1 de 5)
        slide_text = f"Slide {self._pageNumber} de {page_count}"
        self.setFont("Helvetica-Bold", 22)
        self.drawRightString(width - 60, 36, slide_text)

        self.restoreState()


def _parse_markdown_for_carousel(content: str) -> tuple[dict, list[str]]:
    """Extrai título, frontmatter e divide o corpo do post em blocos para os slides."""
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

    # Divide em parágrafos e seções
    raw_paragraphs = [p.strip() for p in body_md.split("\n\n") if p.strip()]
    cleaned_blocks = []

    for p in raw_paragraphs:
        # Pula títulos duplicados H1 no corpo
        if p.startswith("# "):
            continue
        # Limpa marcações markdown pesadas para renderização visual
        clean_text = p.replace("**", "").replace("__", "").replace("## ", "").replace("### ", "")
        # Remove caracteres indesejados
        clean_text = clean_text.replace("--", "—")
        if len(clean_text) > 15:
            cleaned_blocks.append(clean_text)

    return frontmatter, cleaned_blocks


def generate_linkedin_carousel_pdf(content: str, workspace_dir: Path, assets_dir: Path) -> bytes:
    """
    Gera o Carrossel do LinkedIn no formato quadrado 1080 x 1080 px em bytes com alto contraste.
    
    Estrutura dos Slides:
    - Slide 1: Capa com título de forte destaque, subtítulo e indicador de leitura.
    - Slides 2 a N-1: Conteúdo sintetizado em tópicos visuais escuros (#1E293B), fontes confortáveis (22-26pt).
    - Slide Final: CTA chamativo convidando a regularizar o fluxo e acessar o blog.
    """
    colors = get_brand_colors(workspace_dir)
    frontmatter, blocks = _parse_markdown_for_carousel(content)

    title = frontmatter.get("title") or "Compliance no Onboarding de Estagiários"
    subtitle = frontmatter.get("subtitle") or "Segurança Jurídica e Agilidade com a Lei nº 11.788/2008"

    logo_path = assets_dir / "Logo_nautiplus.png"
    if not logo_path.exists():
        logo_path = assets_dir / "logo.png"
    final_logo_str = str(logo_path) if logo_path.exists() else None

    # Dimensões Quadradas: 1080 x 1080 px (pontos no ReportLab)
    page_width, page_height = 1080, 1080
    margin = 80
    top_margin = 160
    bottom_margin = 120

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(page_width, page_height),
        leftMargin=margin,
        rightMargin=margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin
    )

    styles = getSampleStyleSheet()

    # Cores resolvidas
    c_primary_hex = colors.get("primary", COLOR_PRIMARY_DEFAULT)
    c_secondary_hex = colors.get("secondary", COLOR_SECONDARY_DEFAULT)
    c_text_dark_hex = colors.get("text", COLOR_TEXT_DARK)
    c_muted_hex = colors.get("muted", COLOR_TEXT_MUTED)

    # ── Estilos Tipográficos de Alto Contraste ─────────────────────────────────
    style_cover_badge = ParagraphStyle(
        "CoverBadge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=30,
        textColor=HexColor(c_primary_hex),
        alignment=0,
        spaceAfter=25,
    )

    style_cover_title = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=48,
        leading=58,
        textColor=HexColor(c_secondary_hex),
        alignment=0,
        spaceAfter=30,
    )

    style_cover_sub = ParagraphStyle(
        "CoverSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=26,
        leading=38,
        textColor=HexColor(c_text_dark_hex),
        alignment=0,
        spaceAfter=35,
    )

    style_cover_cta = ParagraphStyle(
        "CoverCTA",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=32,
        textColor=HexColor(c_primary_hex),
        alignment=0,
        spaceAfter=20,
    )

    style_slide_title = ParagraphStyle(
        "SlideTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=38,
        leading=48,
        textColor=HexColor(c_secondary_hex),
        spaceAfter=35,
    )

    style_bullet_item = ParagraphStyle(
        "SlideBullet",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=25,
        leading=38,
        textColor=HexColor(c_text_dark_hex),
        leftIndent=25,
        spaceAfter=25,
    )

    style_cta_badge = ParagraphStyle(
        "CtaBadge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=30,
        textColor=HexColor(c_primary_hex),
        alignment=1,
        spaceAfter=20,
    )

    style_cta_title = ParagraphStyle(
        "CtaTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=46,
        leading=56,
        textColor=HexColor(c_secondary_hex),
        alignment=1,
        spaceAfter=25,
    )

    style_cta_body = ParagraphStyle(
        "CtaBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=26,
        leading=40,
        textColor=HexColor(c_text_dark_hex),
        alignment=1,
        spaceAfter=35,
    )

    style_cta_action = ParagraphStyle(
        "CtaAction",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=26,
        leading=38,
        textColor=HexColor(c_primary_hex),
        alignment=1,
        spaceAfter=20,
    )

    story = []

    # ── SLIDE 1: CAPA ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 30))
    story.append(Paragraph("📌 GUIA RÁPIDO & COMPLIANCE", style_cover_badge))
    story.append(Paragraph(title, style_cover_title))
    if subtitle:
        story.append(Paragraph(subtitle, style_cover_sub))
    story.append(Spacer(1, 30))
    story.append(Paragraph("<b>Arraste para o lado 👉</b>", style_cover_cta))
    story.append(PageBreak())

    # ── SLIDES DE CONTEÚDO (Distribuição dos blocos) ──────────────────────────
    # Agrupa blocos de 1 a 2 por slide para garantir tipografia legível e confortável
    content_slides = []
    chunk = []
    for b in blocks:
        chunk.append(b)
        if len(chunk) == 2:
            content_slides.append(chunk)
            chunk = []
    if chunk:
        content_slides.append(chunk)

    # Limita a 3 slides intermediários para manter o carrossel dinâmico
    for idx, slide_blocks in enumerate(content_slides[:3], start=1):
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"💡 Ponto-Chave #{idx}", style_slide_title))
        for block in slide_blocks:
            # Se for uma lista de itens ou frase longa
            if "\n" in block:
                sub_lines = block.split("\n")
                for l in sub_lines:
                    if l.strip():
                        story.append(Paragraph(f"• {l.strip()}", style_bullet_item))
            else:
                story.append(Paragraph(f"• {block}", style_bullet_item))
            story.append(Spacer(1, 15))
        story.append(PageBreak())

    # ── SLIDE FINAL: CTA (Chamada para Ação) ──────────────────────────────────
    story.append(Spacer(1, 50))
    story.append(Paragraph("🎯 PRÓXIMO PASSO", style_cta_badge))
    story.append(Paragraph("🚀 Elimine Riscos no Onboarding", style_cta_title))
    story.append(Paragraph(
        "Não exponha sua empresa a passivos trabalhistas por falha operacional básica. "
        "Tenha emissão instantânea e apólices 100% auditadas com a <b>Nautiplus Seguro Estágio Rápido</b>.",
        style_cta_body
    ))
    story.append(Spacer(1, 20))
    story.append(Paragraph("👉 <b>Acesse o artigo completo no blog e regularize sua operação!</b>", style_cta_action))

    # Constrói o PDF com o NumberedCanvas
    def _canvas_factory(filename, **kwargs):
        return NumberedCanvas(
            filename,
            brand_colors=colors,
            logo_path=final_logo_str,
            brand_name="Nautiplus · Seguro Estágio Rápido",
            **kwargs
        )

    doc.build(story, canvasmaker=_canvas_factory)
    return buffer.getvalue()

