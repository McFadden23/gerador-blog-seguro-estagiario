"""
publisher.py — Publicação automática no WordPress via REST API v2.

Função principal:
    publicar_artigo_wp(titulo, conteudo_markdown, wp_user, wp_app_pass, blog_url) -> dict

- Converte Markdown → HTML (biblioteca markdown)
- POST para {blog_url}/wp-json/wp/v2/posts
- Autenticação HTTP Basic (Application Password do WP)
- Publica diretamente com status 'publish'
- Trata erros de conexão e credenciais
"""

import requests
from requests.auth import HTTPBasicAuth

try:
    import markdown as md_lib
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False


def _markdown_to_html(conteudo_markdown: str) -> str:
    """Converte Markdown para HTML. Usa biblioteca markdown se disponível."""
    if HAS_MARKDOWN:
        return md_lib.markdown(
            conteudo_markdown,
            extensions=["tables", "fenced_code", "nl2br", "toc"],
        )
    # Fallback mínimo sem dependência
    import re
    html = conteudo_markdown
    # Headers
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    # Bold / Italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    # Links
    html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)
    # Bullets
    html = re.sub(r'^\- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    # Parágrafos
    paragraphs = html.split('\n\n')
    html = '\n'.join(
        f'<p>{p.strip()}</p>' if not p.strip().startswith('<') else p.strip()
        for p in paragraphs if p.strip()
    )
    return html


def _strip_frontmatter(conteudo_markdown: str) -> str:
    """Remove o frontmatter YAML do topo do Markdown antes de converter para HTML."""
    import re
    # Remove bloco --- ... ---
    stripped = re.sub(r'^---\n.*?\n---\n?', '', conteudo_markdown, flags=re.DOTALL)
    return stripped.strip()


def publicar_artigo_wp(
    titulo: str,
    conteudo_markdown: str,
    wp_user: str,
    wp_app_pass: str,
    blog_url: str,
) -> dict:
    """
    Publica um artigo no WordPress via REST API v2.

    Args:
        titulo: Título do post.
        conteudo_markdown: Conteúdo completo em Markdown (pode incluir frontmatter YAML).
        wp_user: Nome de usuário do WordPress.
        wp_app_pass: Application Password gerada no painel do WordPress.
        blog_url: URL base do blog (ex.: "https://nautiplus.com.br/blog/").

    Returns:
        dict com:
            - success (bool): True se publicado com sucesso
            - post_url (str | None): URL do post publicado
            - post_id (int | None): ID do post criado
            - error (str | None): Mensagem de erro, se houver
    """
    # Normaliza a URL base (remove barra dupla antes de /wp-json)
    base = blog_url.rstrip('/')
    api_url = f"{base}/wp-json/wp/v2/posts"

    # Converte Markdown → HTML (sem o frontmatter)
    body_md = _strip_frontmatter(conteudo_markdown)
    body_html = _markdown_to_html(body_md)

    payload = {
        "title": titulo,
        "content": body_html,
        "status": "publish",
        "comment_status": "open",
        "ping_status": "open",
    }

    try:
        response = requests.post(
            api_url,
            json=payload,
            auth=HTTPBasicAuth(wp_user, wp_app_pass.strip()),
            timeout=30,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        if response.status_code in (200, 201):
            data = response.json()
            post_url = data.get("link") or data.get("guid", {}).get("rendered", "")
            post_id = data.get("id")
            return {
                "success": True,
                "post_url": post_url,
                "post_id": post_id,
                "error": None,
            }

        # Trata erros HTTP conhecidos
        error_map = {
            401: "Credenciais inválidas (401). Verifique o usuário e a Application Password do WordPress.",
            403: "Sem permissão para publicar (403). O usuário precisa ter papel de Editor ou superior.",
            404: "Endpoint não encontrado (404). Verifique se a URL do blog está correta e se a REST API está ativa.",
            429: "Muitas requisições (429). Aguarde alguns segundos e tente novamente.",
            500: "Erro interno do servidor WordPress (500). Verifique os logs do servidor.",
        }
        status = response.status_code
        detail = error_map.get(status, f"Erro HTTP {status}: {response.text[:300]}")

        try:
            wp_error = response.json()
            wp_msg = wp_error.get("message", "")
            if wp_msg:
                detail = f"{detail} | WP: {wp_msg}"
        except Exception:
            pass

        return {
            "success": False,
            "post_url": None,
            "post_id": None,
            "error": detail,
        }

    except requests.exceptions.ConnectionError as e:
        return {
            "success": False,
            "post_url": None,
            "post_id": None,
            "error": f"Erro de conexão: não foi possível alcançar {base}. Verifique a URL e sua conexão. Detalhe: {e}",
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "post_url": None,
            "post_id": None,
            "error": f"Timeout: o servidor {base} não respondeu em 30 segundos.",
        }
    except Exception as e:
        return {
            "success": False,
            "post_url": None,
            "post_id": None,
            "error": f"Erro inesperado: {e}",
        }
