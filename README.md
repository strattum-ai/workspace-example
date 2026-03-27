# Strattum Workspace

Repositório de configuração do workspace Strattum. Contém skills do agente Claw, transformações de dados e mapeamento de ontologia.

## Estrutura

```
workspace/
├── claw/
│   └── skills/          # Skills customizadas do agente Claw (.md)
├── transformations/     # Transformações SQL e pipelines
│   └── staging/
└── ontology/            # Mapeamento de ontologia (graph_mapping.yaml)
```

## Como usar

1. Faça fork deste repositório para a sua organização
2. Conecte o repositório no Strattum Console → Configurações → Workspace Git
3. Clique em "Sincronizar agora" para importar as configurações
4. Adicione suas skills, transformações e ontologia

## Documentação

- [Skills do Claw](./claw/skills/README.md)
- [Transformações](./transformations/README.md)
- [Ontologia](./ontology/README.md)
