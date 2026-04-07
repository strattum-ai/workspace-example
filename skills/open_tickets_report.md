---
name: open_tickets_report
display_name: Tickets em Aberto
description: Lista todos os tickets em aberto, agrupados por cliente e prioridade.
category: support
tags: [tickets, suporte, atendimento]
---

# Tickets em Aberto

Liste os tickets em aberto agrupados por cliente:

1. Verifique o schema disponível:
   - Call `get_schema()` e identifique nós de ticket (ex: `Ticket`, `Issue`, `Case`)

2. Busque tickets em aberto no grafo:
   - Call `run_cypher("MATCH (c:Customer)-[:HAS_TICKET]->(t:Ticket) WHERE t.status IN ['open','pending','new'] RETURN c.name as cliente, t.subject as assunto, t.priority as prioridade, t.created_at as criado_em ORDER BY t.priority DESC, t.created_at ASC LIMIT 50")`

3. Se disponível no data lake, complemente com SQL:
   - Call `run_sql("SELECT customer_name, subject, priority, status, created_at FROM clean__tickets WHERE status NOT IN ('closed','resolved','done') ORDER BY priority DESC, created_at ASC LIMIT 50")`

4. Retorne uma tabela com: cliente, assunto, prioridade, data de abertura. Agrupe por cliente se houver mais de um ticket do mesmo.
