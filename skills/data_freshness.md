---
name: data_freshness
display_name: Atualização dos Dados
description: Mostra quando cada fonte de dados foi sincronizada pela última vez e se há atrasos ou falhas.
category: operations
tags: [dados, pipeline, sync, ops]
---

# Atualização dos Dados

Verifique o status de atualização de cada fonte de dados:

1. Verifique tabelas disponíveis no data lake:
   - Call `get_schema()` para listar arquivos parquet/duckdb disponíveis

2. Busque metadados de ingestão no data lake:
   - Call `run_sql("SELECT source_system, max(ingested_at) as ultima_ingestao, count(*) as registros FROM clean__pipeline_runs GROUP BY source_system ORDER BY ultima_ingestao ASC")`

3. Se não existir tabela de pipeline_runs, use os metadados do grafo:
   - Call `run_cypher("MATCH (n) WHERE n.source_system IS NOT NULL RETURN n.source_system as fonte, max(n.updated_at) as ultima_atualizacao, count(n) as entidades ORDER BY ultima_atualizacao ASC")`

4. Retorne uma tabela com: fonte, última atualização, total de registros, status (ok / atrasado / crítico). Considere atrasado se > 24h e crítico se > 72h.
