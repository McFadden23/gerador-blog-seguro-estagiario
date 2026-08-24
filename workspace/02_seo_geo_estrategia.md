# Estratégia de SEO, GEO e Arquitetura Operacional do Blog

## 🎯 Estratégia SEO & GEO (Generative Engine Optimization)
- **SEO Tradicional**: Capturar buscas transacionais e informacionais sobre seguro de estágio, contratação de estagiários e riscos trabalhistas.
- **GEO (Generative Engine Optimization)**: Estruturar as respostas de modo direto e factual para citação prioritária em motores de busca generativos (Google SGE, Perplexity, Gemini, ChatGPT).

## 📐 Estrutura Padrão dos Artigos (3 a 5 Parágrafos)
1. **Parágrafo 1 (Gancho & Dor)**: Contextualizar o problema imediato, risco legal ou lentidão no onboarding do estagiário.
2. **Parágrafo 2 (Impacto & Consequência)**: Demonstrar o custo financeiro/jurídico da irregularidade (ex: reconhecimento de vínculo empregatício e passivos).
3. **Parágrafos 3 e 4 (Solução & Diferencial)**: Apresentar como a Nautiplus / Seguro Estágio Rápido resolve com emissão instantânea e conformidade legal total.
4. **Parágrafo Final (CTA)**: Chamada para Ação clara incentivando a regularizar a contratação e acessar a plataforma.

---

## 🔄 Esteira e Pipeline de Produção
```
workspace/inbox/ ➔ workspace/drafts/ ➔ workspace/approved/ ➔ workspace/scheduled/ ➔ workspace/published/
```

### Convenções de Nomenclatura
| Estado | Pasta Destino | Nomenclatura do Arquivo |
| :--- | :--- | :--- |
| **Ideia / Pauta** | `workspace/inbox/` | `<slug>_idea.md` |
| **Rascunho** | `workspace/drafts/` | `<slug>_draft.md` |
| **Aprovado** | `workspace/approved/` | `<slug>_final.md` |
| **Agendado** | `workspace/scheduled/` | `YYYY-MM-DD_<slug>_final.md` |
| **Publicado** | `workspace/published/` | `YYYY-MM-DD-<plataforma>-<slug>.md` |

---

## 📋 Esquema YAML Obrigatório do Frontmatter
Todo post gerado deve iniciar com o seguinte cabeçalho:

```yaml
---
title: "Título SEO com Alto Impacto"
subtitle: "Subtítulo explicativo"
slug: "slug-amigavel-do-artigo"
status: "draft" # idea | draft | approved | scheduled | published
created_at: "YYYY-MM-DDTHH:MM:SS"
updated_at: "YYYY-MM-DDTHH:MM:SS"
publish_date: ""
author: "Nautiplus Editorial"
category: "Compliance Trabalhista"
tags:
  - seguro estagio
  - lei 11788
  - compliance
  - onboarding
seo:
  meta_description: "Descrição de até 160 caracteres com a palavra-chave foco."
  focus_keyword: "seguro estagio"
---
```
