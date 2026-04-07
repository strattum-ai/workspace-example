---
name: team_activity
display_name: Atividade da Equipe
description: Resume o que cada membro da equipe fez nos últimos 7 dias — interações, tickets resolvidos e novos clientes atendidos.
category: management
tags: [equipe, atividade, produtividade]
---

# Atividade da Equipe

Gere um resumo de atividade da equipe nos últimos 7 dias:

1. Verifique o schema:
   - Call `get_schema()` para identificar nós de usuário/agente e tipos de relacionamento

2. Interações por usuário nos últimos 7 dias:
   - Call `run_cypher("MATCH (u:User)-[r:HANDLED|RESOLVED|CREATED|UPDATED]->(n) WHERE r.timestamp > datetime() - duration('P7D') RETURN u.name as usuario, type(r) as acao, count(r) as total ORDER BY total DESC LIMIT 30")`

3. Tickets resolvidos por usuário:
   - Call `run_cypher("MATCH (u:User)-[:RESOLVED]->(t:Ticket) WHERE t.resolved_at > datetime() - duration('P7D') RETURN u.name as usuario, count(t) as tickets_resolvidos, avg(duration.inSeconds(t.created_at, t.resolved_at)/3600) as tempo_medio_horas ORDER BY tickets_resolvidos DESC")`

4. Novos clientes ou empresas criados no período:
   - Call `run_cypher("MATCH (c:Customer) WHERE c.created_at > datetime() - duration('P7D') RETURN c.name, c.created_at ORDER BY c.created_at DESC LIMIT 20")`

5. Retorne um resumo por usuário: principais ações, volume de trabalho e destaques do período.
