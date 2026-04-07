---
name: customer_health
display_name: Saúde do Cliente
description: Avalia a saúde de um cliente específico — atividade recente, tickets abertos, contratos e relacionamentos.
category: customer_success
tags: [cliente, saúde, churn, cs]
---

# Saúde do Cliente

Avalie a saúde de um cliente específico. Use o nome ou ID mencionado pelo usuário.

1. Localize o cliente no grafo:
   - Call `run_cypher("MATCH (c:Customer) WHERE toLower(c.name) CONTAINS toLower('<nome do cliente>') RETURN c.name, c.external_id, c.created_at, c.status LIMIT 5")`

2. Verifique atividade recente (últimos 30 dias):
   - Call `run_cypher("MATCH (c:Customer {external_id: '<id>'})-[r]->(n) WHERE r.timestamp > datetime() - duration('P30D') RETURN type(r) as tipo, count(r) as ocorrencias, max(r.timestamp) as ultimo ORDER BY ocorrencias DESC")`

3. Verifique tickets em aberto:
   - Call `run_cypher("MATCH (c:Customer {external_id: '<id>'})-[:HAS_TICKET]->(t:Ticket) WHERE t.status IN ['open','pending','new'] RETURN t.subject, t.priority, t.created_at ORDER BY t.created_at DESC LIMIT 10")`

4. Verifique contratos e MRR (se disponível):
   - Call `run_cypher("MATCH (c:Customer {external_id: '<id>'})-[:HAS_CONTRACT]->(contract) RETURN contract.value, contract.start_date, contract.end_date, contract.status LIMIT 5")`

5. Retorne um resumo estruturado:
   - **Status geral:** ativo/em risco/inativo
   - **Última interação:** data e tipo
   - **Tickets abertos:** quantidade e prioridade mais alta
   - **Contrato:** valor e validade (se disponível)
