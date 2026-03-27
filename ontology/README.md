# Ontologia

Coloque aqui o arquivo `graph_mapping.yaml` com o mapeamento de ontologia do seu workspace.

O arquivo define como os dados do cliente são mapeados para o grafo de conhecimento (FalkorDB).

## Estrutura do graph_mapping.yaml

```yaml
version: "1.0"
entities:
  - name: Customer
    source_table: clientes
    id_field: id
    properties:
      - field: nome
        property: name
      - field: email
        property: email
    relationships: []
```

Consulte a documentação do Strattum para o schema completo.
