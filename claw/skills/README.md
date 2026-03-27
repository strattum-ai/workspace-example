# Skills do Workspace

Coloque aqui as skills customizadas do agente Claw.

Cada skill é um arquivo `.md` com frontmatter YAML seguido do prompt da skill.

## Formato

```yaml
---
name: nome_da_skill
display_name: Nome Exibido
description: Descrição breve do que a skill faz.
category: analytics
tags: [tag1, tag2]
---

# Título da Skill

Instruções para o agente...
```

## Categorias disponíveis

- `analytics` — análise de dados e relatórios
- `context` — enriquecimento de contexto de entidades
- `automation` — automações e workflows
- `custom` — skills customizadas do cliente
