---
name: revenue_at_risk
display_name: Receita em Risco
description: Identifica clientes com alto MRR e sinais negativos — inatividade, tickets em aberto ou contratos próximos do vencimento.
category: analytics
tags: [mrr, receita, churn, risco]
---

# Receita em Risco

Identifique receita em risco combinando MRR com sinais de saúde negativos:

1. Verifique o schema disponível:
   - Call `get_schema()` para confirmar quais nós e tabelas existem

2. Busque clientes com MRR alto e inatividade recente:
   - Call `run_cypher("MATCH (c:Customer) WHERE c.mrr IS NOT NULL AND NOT (c)-[]-() OR (c:Customer) WHERE NOT EXISTS { MATCH (c)-[r]-() WHERE r.timestamp > datetime() - duration('P30D') } RETURN c.name, c.mrr, c.last_activity ORDER BY c.mrr DESC LIMIT 20")`

3. Clientes com MRR alto e tickets abertos de alta prioridade:
   - Call `run_cypher("MATCH (c:Customer)-[:HAS_TICKET]->(t:Ticket) WHERE t.status IN ['open','pending'] AND t.priority IN ['high','urgent','critical'] AND c.mrr IS NOT NULL RETURN c.name, c.mrr, count(t) as tickets_criticos ORDER BY c.mrr DESC LIMIT 20")`

4. Contratos próximos do vencimento (90 dias) com MRR relevante:
   - Call `run_cypher("MATCH (c:Customer)-[:HAS_CONTRACT]->(contract) WHERE contract.end_date < datetime() + duration('P90D') AND contract.status = 'active' RETURN c.name, contract.value, contract.end_date ORDER BY contract.value DESC LIMIT 15")`

5. Retorne uma tabela consolidada com: cliente, MRR, principal sinal de risco, urgência.
