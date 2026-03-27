# Transformações

Coloque aqui as transformações SQL e configurações de pipeline.

## Estrutura recomendada

```
transformations/
├── staging/          # Transformações de staging (limpeza e padronização)
│   └── stg_clientes.sql
├── marts/            # Marts analíticos (visões de negócio)
│   └── clientes_ativos.sql
└── README.md
```

## Formato SQL

Arquivos `.sql` com comentários de documentação:

```sql
-- Nome: Clientes Ativos
-- Descrição: Lista clientes com atividade nos últimos 90 dias
-- Atualização: diária

SELECT
    id,
    nome,
    last_activity_at
FROM clientes
WHERE last_activity_at >= CURRENT_DATE - INTERVAL '90 days'
```
