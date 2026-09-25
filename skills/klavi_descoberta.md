---
name: klavi_descoberta
display_name: Descoberta de valores de dimensão
description: Passo de descoberta, consultado ANTES das outras skills — devolve quais valores existem numa dimensão (marca, setor, canal, uf, city) e quantas pessoas cada um tem. A lista devolvida é o domínio publicável, não o completo — valores abaixo do piso de anonimato não aparecem. É daqui que saem os valores que preenchem <ESCOPO>, <RECORTE>, <MARCA> e afins nas demais fichas. NÃO responde valor, gasto, ticket ou share.
category: consumer_insights
tags: [descoberta, dimensões, domínio, valores, piso, privacidade, klavi]
---

# Descoberta de valores de dimensão

O passo consultado **primeiro**. Toda ficha que pede um valor de taxonomia num buraco
(`<ESCOPO>`, `<RECORTE>`, `<MARCA>`, `<VALOR>`, …) manda descobrir o valor aqui — as fichas não
carregam valores de taxonomia por desenho, então a grafia exata armazenada só existe nesta
consulta.

**Você não escreve SQL livre.** Use a consulta como está, trocando só os buracos indicados.

## valores_de_dimensao

**Responde:** quais valores existem numa dimensão, e quantas pessoas cada um tem.

**Decisão embutida:** o piso de anonimato vale **na lista de valores**, não só na resposta
final. Uma lista de valores que inclui uma célula abaixo do piso confirma que a célula existe,
e a supressão da resposta vira decorativa.

**Buracos obrigatórios:** `<DIMENSAO>`, `<ESCOPO>`

**Dimensões permitidas:** as da tabela da skill acionada via MCP `skills_klavi_catalogo`,
seção "Os buracos compartilhados".

**Não responde:** valor, gasto, ticket ou share. É só o domínio.

**Piso:** um portão, no `HAVING`.

```sql
SELECT <DIMENSAO>                        AS valor,
       COUNT(DISTINCT external_id)       AS pessoas
FROM clean__klavi_spend_cube
WHERE <ESCOPO>
GROUP BY <DIMENSAO>
HAVING COUNT(DISTINCT external_id) >= 50
ORDER BY pessoas DESC;
```

### A lista é o domínio publicável, não o completo

Um valor que existe na base mas fica abaixo do piso **não aparece** nesta lista. Então
"não está na lista" e "não existe" são indistinguíveis daqui.

Quando o usuário pedir um valor que não aparece, a resposta correta é: *"esse valor não está no
domínio publicável — ele pode não existir, ou existir abaixo do piso de 50 pessoas"*. **Nunca
"não existe".**

### Escopar a descoberta resolve ambiguidade de nome

Buscar marca sem escopo devolve marcas de setores diferentes que compartilham prefixo de nome —
e escolher uma delas em silêncio é escolher o setor errado. Passe `<ESCOPO>` com o setor da
pergunta, e a ambiguidade desaparece por construção em vez de depender de atenção.
