"""
cli.py — Interface de Linha de Comando do Blog Automation System.

Uso:
    python main.py <comando> [opções]

Comandos disponíveis:
    generate-ideas              Gera lista de pautas via Gemini
    generate-draft <slug>       Gera rascunho para uma pauta existente
    approve <slug>              Move um draft para approved/
    schedule <slug> <datetime>  Agenda um post aprovado para publicação
    export-pdf <slug>           Exporta post aprovado/agendado para PDF
    publish <slug>              Publica manualmente um post agendado
    status                      Lista todos os posts e seus status
"""

import sys
import os
from pathlib import Path
from datetime import datetime

import click
import yaml
from dotenv import load_dotenv

# Garante UTF-8 no terminal Windows
import sys, io
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from workspace import WorkspaceManager, _read_frontmatter
from generator import generate_ideas, generate_draft
from pdf_exporter import PDFExporter
from scheduler import Scheduler
from publisher import Publisher


ROOT         = Path(__file__).parent.parent          # raiz do projeto
WORKSPACE    = ROOT / "workspace"
CONFIG_FILE  = ROOT / "config" / "settings.yaml"

load_dotenv(ROOT / ".env")


def _load_config() -> dict:
    """Carrega as configurações do sistema."""
    if not CONFIG_FILE.exists():
        click.echo(f"❌ Arquivo de configuração não encontrado: {CONFIG_FILE}", err=True)
        sys.exit(1)
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ── CLI Principal ─────────────────────────────────────────────────────────────

@click.group()
def cli():
    """
    \b
    ==========================================
      Blog Automation System v0.1.0
      Seguro Estagiario -- Content Hub
    ==========================================
    """
    pass


# ── generate-ideas ────────────────────────────────────────────────────────────

@cli.command("generate-ideas")
@click.option("--n", default=5, show_default=True, help="Número de pautas a gerar")
def cmd_generate_ideas(n):
    """Gera sugestões de pautas para posts via Gemini AI."""
    config = _load_config()
    ws     = WorkspaceManager(ROOT, config)

    # Lista temas já existentes para evitar repetição
    existing = [p["slug"] for p in ws.list_all()]

    click.echo(f"\n🔍 Gerando {n} pautas para o nicho: {config['blog']['niche']}\n")

    ideas = generate_ideas(config, WORKSPACE, n=n, existing_topics=existing)

    if not ideas:
        click.echo("⚠  Nenhuma pauta gerada. Verifique sua API key e tente novamente.")
        return

    click.echo(f"\n✅ {len(ideas)} pautas geradas:\n")

    for idea in ideas:
        click.echo(f"  [{idea.get('id', '?')}] {idea.get('titulo', '(sem título)')}")
        click.echo(f"      Slug: {idea.get('slug', '')}")
        click.echo(f"      Ângulo: {idea.get('angulo', '')}\n")

        # Salva cada ideia como arquivo _idea.md no inbox
        content = _idea_to_markdown(idea, config)
        ws.save_post(idea.get("slug", f"ideia-{idea.get('id', '0')}"), content, "idea")

    click.echo(f"\n📂 Pautas salvas em: workspace/inbox/")


def _idea_to_markdown(idea: dict, config: dict) -> str:
    """Converte uma pauta em arquivo Markdown com frontmatter."""
    from datetime import date
    fm = {
        "title":        idea.get("titulo", ""),
        "subtitle":     idea.get("subtitulo", ""),
        "slug":         idea.get("slug", ""),
        "tags":         idea.get("palavras_chave", []),
        "formato":      idea.get("formato", ""),
        "publico":      idea.get("publico", ""),
        "status":       "idea",
        "created_at":   date.today().isoformat(),
        "updated_at":   date.today().isoformat(),
    }
    fm_str = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    body   = f"## Ângulo Editorial\n\n{idea.get('angulo', '')}\n"
    return f"---\n{fm_str}---\n\n{body}"


# ── generate-draft ────────────────────────────────────────────────────────────

@cli.command("generate-draft")
@click.argument("slug")
def cmd_generate_draft(slug):
    """Gera o rascunho completo de um post a partir de uma pauta (slug)."""
    config = _load_config()
    ws     = WorkspaceManager(ROOT, config)

    # Localiza a pauta no inbox
    post_path, state = ws.find_post(slug)
    if post_path is None:
        click.echo(f"❌ Pauta não encontrada para slug: '{slug}'", err=True)
        click.echo("   Use 'python main.py generate-ideas' para gerar pautas primeiro.")
        return

    fm   = _read_frontmatter(post_path)
    idea = {
        "titulo":         fm.get("title", ""),
        "subtitulo":      fm.get("subtitle", ""),
        "slug":           fm.get("slug", slug),
        "angulo":         "",
        "palavras_chave": fm.get("tags", []),
    }

    # Lê o ângulo do corpo do arquivo
    body = post_path.read_text(encoding="utf-8").split("---", 2)[-1].strip()
    if "Ângulo Editorial" in body:
        idea["angulo"] = body.split("## Ângulo Editorial")[-1].strip()

    click.echo(f"\n✍  Gerando rascunho: \"{idea['titulo']}\"\n")

    content = generate_draft(idea, config, WORKSPACE)
    ws.save_post(slug, content, "draft")

    click.echo(f"\n✅ Rascunho salvo! Revise o arquivo e use 'approve {slug}' quando estiver pronto.")


# ── approve ───────────────────────────────────────────────────────────────────

@cli.command("approve")
@click.argument("slug")
def cmd_approve(slug):
    """Aprova um rascunho e move para approved/."""
    config = _load_config()
    ws     = WorkspaceManager(ROOT, config)

    post_path, state = ws.find_post(slug)
    if post_path is None:
        click.echo(f"❌ Post não encontrado para slug: '{slug}'", err=True)
        return

    if state != "draft":
        click.echo(f"⚠  O post está em '{state}', não em 'draft'. Nenhuma ação realizada.")
        return

    ws.advance_state(slug, "draft", "approved")
    click.echo(f"\n✅ Post aprovado! Próximo passo: 'schedule {slug} YYYY-MM-DDTHH:MM'")


# ── schedule ──────────────────────────────────────────────────────────────────

@cli.command("schedule")
@click.argument("slug")
@click.argument("publish_at")
def cmd_schedule(slug, publish_at):
    """Agenda um post aprovado para publicação (formato: YYYY-MM-DDTHH:MM)."""
    config = _load_config()
    ws     = WorkspaceManager(ROOT, config)

    try:
        dt   = datetime.fromisoformat(publish_at)
        date = dt.strftime("%Y-%m-%d")
    except ValueError:
        click.echo(f"❌ Formato de data inválido. Use: YYYY-MM-DDTHH:MM (ex: 2026-09-01T10:00)")
        return

    post_path, state = ws.find_post(slug)
    if post_path is None:
        click.echo(f"❌ Post não encontrado: '{slug}'", err=True)
        return

    if state != "approved":
        click.echo(f"⚠  O post está em '{state}'. Aprove-o primeiro com 'approve {slug}'.")
        return

    ws.advance_state(slug, "approved", "scheduled", date=date)

    # Atualiza a data no frontmatter do arquivo movido
    scheduled_path = ws.get_post_path(slug, "scheduled", date=date)
    if scheduled_path.exists():
        content = scheduled_path.read_text(encoding="utf-8")
        from workspace import _update_frontmatter
        content = _update_frontmatter(content, {"publish_date": publish_at, "status": "scheduled"})
        scheduled_path.write_text(content, encoding="utf-8")

    click.echo(f"\n✅ Post agendado para {dt.strftime('%d/%m/%Y às %H:%M')}!")
    click.echo(f"   Use 'export-pdf {slug}' para gerar o PDF.")


# ── export-pdf ────────────────────────────────────────────────────────────────

@cli.command("export-pdf")
@click.argument("slug")
def cmd_export_pdf(slug):
    """Exporta um post aprovado ou agendado para PDF estilizado."""
    config = _load_config()
    ws     = WorkspaceManager(ROOT, config)

    post_path, state = ws.find_post(slug)
    if post_path is None:
        click.echo(f"❌ Post não encontrado: '{slug}'", err=True)
        return

    if state not in ("approved", "scheduled", "published"):
        click.echo(f"⚠  Post em estado '{state}'. Aprove-o primeiro antes de exportar PDF.")
        return

    click.echo(f"\n📄 Exportando PDF: \"{post_path.name}\"...\n")

    exporter   = PDFExporter(ROOT, config)
    output_pdf = exporter.export(post_path)

    click.echo(f"\n✅ PDF disponível em: {output_pdf}")


# ── publish ───────────────────────────────────────────────────────────────────

@cli.command("publish")
@click.argument("slug")
def cmd_publish(slug):
    """Publica manualmente um post agendado ou aprovado na plataforma de blog."""
    config = _load_config()

    click.echo("\n⚠  O módulo de publicação ainda não está implementado.")
    click.echo("   Defina a plataforma de blog em config/settings.yaml e implemente publisher.py.")


# ── status ────────────────────────────────────────────────────────────────────

@cli.command("status")
def cmd_status():
    """Lista todos os posts do workspace com seus status."""
    config = _load_config()
    ws     = WorkspaceManager(ROOT, config)
    posts  = ws.list_all()

    if not posts:
        click.echo("\n📭 Nenhum post no workspace ainda.")
        click.echo("   Use 'python main.py generate-ideas' para começar.\n")
        return

    # Agrupa por estado
    state_emoji = {
        "idea":      "💡",
        "draft":     "✏️ ",
        "approved":  "✅",
        "scheduled": "🗓️ ",
        "published": "🌐",
    }

    click.echo(f"\n{'─'*60}")
    click.echo(f"  {'ESTADO':<12} {'ARQUIVO':<38} {'DATA'}")
    click.echo(f"{'─'*60}")

    for p in posts:
        emoji = state_emoji.get(p["state"], "  ")
        date  = p["date"][:10] if p["date"] else "—"
        click.echo(f"  {emoji} {p['state']:<10} {p['file']:<38} {date}")

    click.echo(f"{'─'*60}")
    click.echo(f"  Total: {len(posts)} post(s)\n")


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
