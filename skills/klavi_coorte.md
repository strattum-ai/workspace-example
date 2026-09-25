---
name: klavi_coorte
display_name: Coorte certificada — o "quem"
description: Quatro consultas nomeadas da família "quem". Responde quantas pessoas satisfazem uma condição declarada (limiar de gasto numa janela móvel, posse de produto, posse de dois valores, transição entre valores) e quanto elas somam — nunca quem elas são. Só coorte_limiar_janela preenche os buracos do molde de coorte sobre clean__klavi_spend_cube abaixo; as outras três (posse_e_complemento, posse_de_dois_valores, transicao_entre_valores) têm corpo próprio sobre as tabelas pessoa-mês/marca-mês, documentado em cada seção. Escolha a consulta pelo catálogo (skill skills_klavi_catalogo), leia a ficha aqui e preencha os buracos — buraco não preenchido não roda. NÃO responde lista de pessoas nem consulta livre.
category: consumer_insights
tags: [coorte, molde, limiar, janela, recorte, piso, privacidade, klavi]
---

# Coorte certificada — o "quem"

Quatro consultas nomeadas. O molde abaixo serve só `coorte_limiar_janela`; as outras três
(`posse_e_complemento`, `posse_de_dois_valores`, `transicao_entre_valores`) têm corpo próprio
sobre as tabelas pessoa-mês/marca-mês, explicado na seção de cada uma. **Você não escreve
SQL.** Escolhe a consulta pelo catálogo (skill acionada via MCP `skills_klavi_catalogo`), lê a ficha dela aqui, e preenche
os buracos.

**Buraco não preenchido não roda.** Isso é intencional: é o que faz a declaração ser obrigatória
em vez de recomendada.

Os valores legais de cada buraco estão na skill acionada via MCP `skills_klavi_catalogo`,
seção "Os buracos compartilhados".

## O molde de coorte

```sql
WITH janela AS (
  -- The rolling window is anchored on MAX(transaction_date), never on the clock:
  -- the base is static and the clock is ahead of it, so a clock-anchored window
  -- returns an empty result that looks like an answer.
  SELECT external_id, SUM(amount) AS gasto_janela
  FROM clean__klavi_spend_cube
  WHERE <DIMENSAO> = <VALOR>
    AND <RECORTE>
    AND transaction_date >= (SELECT MAX(transaction_date) - <JANELA>
                             FROM clean__klavi_spend_cube)
  GROUP BY external_id
)
SELECT COUNT(DISTINCT external_id) AS pessoas,
       ROUND(SUM(gasto_janela), 2) AS gasto_total
FROM janela
WHERE gasto_janela >= <LIMIAR>
HAVING COUNT(DISTINCT external_id) >= 50;
```

## coorte_limiar_janela

**Responde:** quantas pessoas acumularam gasto acima de um limiar, num valor de dimensão,
dentro de uma janela móvel — e quanto elas gastaram juntas.

**Decisão embutida:** a âncora da janela é `MAX(transaction_date)` do próprio dado, **nunca a
data de hoje**. Ancorar no relógio devolve zero linhas nesta base, e zero linhas com cara de
resposta é o modo de falha que estas skills existem para impedir.

**Buracos obrigatórios:** `<DIMENSAO>`, `<VALOR>`, `<JANELA>`, `<LIMIAR>`, `<RECORTE>`

**Descobrir antes:** a grafia de `<VALOR>`, por `valores_de_dimensao`.

**Não responde:** gasto médio dessa coorte — para isso ela alimenta `gasto_medio_na_coorte`
como `<COORTE>`.

**Piso:** um portão, no `HAVING`. O grão da resposta é uma contagem única, não células por
dimensão, então não há o que desagregar e o prefixo de supressão complementar não se aplica.

### `<RECORTE>` é par, e por quê

"Em São Paulo" tem duas leituras — estado e município — e elas dão respostas que diferem por
quase 2× nesta base. `<RECORTE>` é par dimensão + valor justamente para que a leitura seja
declarada em vez de escolhida em silêncio.

### Zero linhas: três causas, não duas

Diga qual antes de concluir qualquer coisa:

1. `<VALOR>` não existe com essa grafia — confirme por `valores_de_dimensao`;
2. existe, e menos de 50 pessoas cruzaram o limiar — é o piso, e a resposta é supressão;
3. a janela ficou vazia — só acontece se a âncora foi trocada pelo relógio.

**Para distinguir a 1 da 2, use `valores_de_dimensao`, não remova o `HAVING`.** A versão
anterior desta skill mandava distinguir e proibia a única operação que distinguia; a
descoberta resolve isso sem tocar na consulta que responde.

## posse_e_complemento

**Responde:** quantas pessoas do universo declarado têm um produto, e quantas não têm.

**Decisão embutida duas vezes.** Primeira: o **universo é obrigatório** — `is_in_panel` conta
quem tinha consentimento ativo naqueles meses, `is_eligible` conta quem tem consentimento
mesmo com histórico retroativo, e nos meses de rampa de captação eles divergem em pessoas
suficientes para mudar a resposta. Segunda: **a janela vale nos dois lados** — se ela recorta
"com" e não recorta o universo, a soma não fecha e o complemento fica inflado.

**Buracos obrigatórios:** `<DIMENSAO>`, `<VALOR>`, `<UNIVERSO>`, `<JANELA>`

**Descobrir antes:** a grafia de `<VALOR>`, por `valores_de_dimensao`.

**Não responde:** posse de dois produtos ao mesmo tempo — isso é `posse_de_dois_valores`.

**Piso:** **dois portões.** Tanto "com" quanto "sem" precisam passar o piso; publicar um
complemento de 12 pessoas é publicar uma célula de 12 pessoas.

### O corpo

Esta consulta **não preenche o molde de coorte** — a resposta tem dois lados, então o corpo é
próprio: dois CTEs, um por lado, com a **mesma** `<JANELA>` nos dois. A âncora é `MAX(month)`
da tabela pessoa-mês, nunca o relógio — pela mesma razão do molde.

```sql
WITH universo AS (
  -- The window applies to BOTH sides: cutting only `com` leaves the complement
  -- inflated by people who were in the universe outside the window.
  SELECT DISTINCT external_id
  FROM clean__klavi_person_month
  WHERE <UNIVERSO>
    AND month >= (SELECT MAX(month) - <JANELA> FROM clean__klavi_person_month)
),
com AS (
  SELECT DISTINCT external_id
  FROM clean__klavi_person_sector_month
  WHERE <DIMENSAO> = <VALOR>
    AND month >= (SELECT MAX(month) - <JANELA> FROM clean__klavi_person_month)
)
SELECT COUNT(u.external_id)                        AS universo,
       COUNT(c.external_id)                        AS com_produto,
       COUNT(u.external_id) - COUNT(c.external_id) AS sem_produto
FROM universo u
LEFT JOIN com c USING (external_id)
-- Two gates: publishing a small complement is publishing a small cell.
HAVING COUNT(c.external_id) >= 50
   AND COUNT(u.external_id) - COUNT(c.external_id) >= 50;
```

O `LEFT JOIN` conta "com" **dentro** do universo: quem tem o produto mas está fora do universo
declarado não entra em nenhum dos dois lados — e é isso que faz a soma fechar por construção
quando os dois CTEs carregam a mesma janela.

### Confira que fecha

`com + sem = universo`, sempre. Se não fechar, a janela foi aplicada em um lado só.

## posse_de_dois_valores

**Responde:** quantas pessoas têm dois valores de uma dimensão — duas marcas, dois ramos de
produto — na simultaneidade declarada.

**Decisão embutida:** **simultaneidade é obrigatória.** "Usam A e B" admite duas leituras
completamente diferentes — no mesmo mês, ou em qualquer momento do histórico — e elas dão
números diferentes. A versão anterior desta skill afirmava medir "ao mesmo tempo" e agrupava só
por pessoa, medindo o histórico: prosa e SQL diziam coisas diferentes sobre o mesmo número.

**Buracos obrigatórios:** `<DIMENSAO>`, `<VALOR_A>`, `<VALOR_B>`, `<SIMULTANEIDADE>`

**`<SIMULTANEIDADE>` sugerido:** `ambos`. Os dois números lado a lado tornam a diferença
**informação** em vez de contradição.

**Descobrir antes:** as grafias de `<VALOR_A>` e `<VALOR_B>`, por `valores_de_dimensao` com o
escopo do setor — o que também evita casar valor de outro setor com nome parecido.

**Não responde:** ordem temporal. Ter as duas não é ter migrado — isso é
`transicao_entre_valores`.

**Piso:** um portão, no `HAVING`.

### O corpo

Base: `clean__klavi_person_brand_month` — o grão é pessoa-mês-valor, o mesmo grão de que a
distinção "no mesmo mês" × "no histórico" depende. `<DIMENSAO>` é a coluna que carrega os dois
valores (`brand` para duas marcas; `sector_l3` para dois ramos — as duas colunas vivem nesta
mesma view).

```sql
WITH no_mes AS (
  SELECT external_id, month
  FROM clean__klavi_person_brand_month
  WHERE <DIMENSAO> IN (<VALOR_A>, <VALOR_B>)
  GROUP BY external_id, month
  HAVING COUNT(DISTINCT <DIMENSAO>) = 2
),
no_historico AS (
  SELECT external_id
  FROM clean__klavi_person_brand_month
  WHERE <DIMENSAO> IN (<VALOR_A>, <VALOR_B>)
  GROUP BY external_id
  HAVING COUNT(DISTINCT <DIMENSAO>) = 2
)
-- <SIMULTANEIDADE> lands here, in executable position — unfilled, the query is invalid SQL:
<SIMULTANEIDADE>

-- <SIMULTANEIDADE> takes ONE of these three blocks, per the declared value:
--
--   no_mes        SELECT 'no_mes' AS simultaneidade, COUNT(DISTINCT external_id) AS pessoas
--                 FROM no_mes
--                 HAVING COUNT(DISTINCT external_id) >= 50
--
--   no_historico  SELECT 'no_historico' AS simultaneidade, COUNT(*) AS pessoas
--                 FROM no_historico
--                 HAVING COUNT(*) >= 50
--
--   ambos         SELECT 'no_mes' AS simultaneidade, COUNT(DISTINCT external_id) AS pessoas
--                 FROM no_mes
--                 HAVING COUNT(DISTINCT external_id) >= 50
--                 UNION ALL
--                 SELECT 'no_historico', COUNT(*)
--                 FROM no_historico
--                 HAVING COUNT(*) >= 50
```

Com `ambos`, cada leitura carrega o próprio portão — uma pode desaparecer do resultado sem afetar
a outra. Se uma leitura sumir, aplique "Zero linhas: três causas" (seção de `coorte_limiar_janela`,
acima) antes de rotular como supressão: um valor genuinamente zero e um valor suprimido (1 a 49)
produzem a **mesma ausência de linha** neste corpo, e só rodando a leitura sem o `HAVING` — fora de
qualquer resposta publicável — dá para distinguir os dois.

## transicao_entre_valores

**Responde:** quantas pessoas usavam um valor e passaram a usar outro, com ordem temporal
estrita.

**Decisão embutida:** o destino começa **depois** do fim da origem. Coocorrência é simétrica;
transição não é. **A assimetria é a prova** — se a direção inversa devolver o mesmo número, a
consulta não está respeitando ordem, está medindo coocorrência com outro nome.

**Buracos obrigatórios:** `<DIMENSAO>`, `<VALOR_A>`, `<VALOR_B>`, `<JANELA>`

**Descobrir antes:** as grafias, por `valores_de_dimensao` com escopo.

**Não responde:** posse simultânea — isso é `posse_de_dois_valores`.

**Piso:** um portão, no `HAVING`.

### O corpo

Mesma auto-junção por pessoa que `posse_de_dois_valores`, com uma condição de ordem a mais.

```sql
WITH por_valor AS (
  SELECT external_id, <DIMENSAO>, MIN(month) AS primeiro, MAX(month) AS ultimo
  FROM clean__klavi_person_brand_month
  WHERE <JANELA>
  GROUP BY external_id, <DIMENSAO>
)
SELECT COUNT(DISTINCT a.external_id) AS pessoas
FROM por_valor a
JOIN por_valor b ON b.external_id = a.external_id
WHERE a.<DIMENSAO> = <VALOR_A>
  AND b.<DIMENSAO> = <VALOR_B>
  AND b.primeiro > a.ultimo                 -- strict: destination starts AFTER origin ends
HAVING COUNT(DISTINCT a.external_id) >= 50;

-- <JANELA> is a WHERE clause, never absent. Legal shapes, anchored at THIS table's month column:
--   a relative window: month >= (SELECT MAX(month) - INTERVAL 'N' DAY
--                                 FROM clean__klavi_person_brand_month)
--   TRUE is legal ONLY as the explicit "whole history" declaration, said next to the number.
-- Never now(), never CURRENT_DATE.
```

Para confirmar a assimetria, rode a mesma consulta **invertendo** qual valor é `a` e qual é `b`
(mantendo `b.primeiro > a.ultimo`), nunca trocando o operador — trocar `>` por `>=` não discrimina
numa base sem sobreposição de mês entre os dois valores. A prova de ordem é a direção, não o
operador.

### Ausência de linha não é "ninguém migrou"

Zero linhas tem as três causas do início deste arquivo. Em particular, ausência de linha na
direção inversa é o **resultado esperado** e a prova de que a ordem está sendo respeitada —
não um dado faltando.
