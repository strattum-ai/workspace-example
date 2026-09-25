---
name: klavi_agregacao
display_name: Agregação certificada — o "quanto"
description: Cinco consultas nomeadas que respondem "quanto" (valor, compras, pessoas) por uma dimensão declarada. Três (share_de_marca, volume_de_marca, ranking_de_marcas) preenchem os buracos do molde único de agregação com supressão complementar (piso k=50) sobre clean__klavi_spend_cube; as outras duas (ticket_de_marca, gasto_medio_na_coorte) têm piso próprio, documentado em cada seção. Escolha a consulta pelo catálogo (skill skills_klavi_catalogo), leia a ficha aqui e preencha os buracos — buraco não preenchido não roda. NÃO responde lista de pessoas nem consulta livre.
category: consumer_insights
tags: [agregação, molde, supressão, piso, privacidade, klavi]
---

# Agregação certificada — o "quanto"

Cinco consultas nomeadas. O molde abaixo serve três delas (`share_de_marca`, `volume_de_marca`,
`ranking_de_marcas`); as outras duas (`ticket_de_marca`, `gasto_medio_na_coorte`) têm piso
próprio, explicado na seção de cada uma. **Você não escreve SQL.** Escolhe a consulta pelo
catálogo (skill acionada via MCP `skills_klavi_catalogo`), lê a ficha dela aqui, e preenche os buracos.

**Buraco não preenchido não roda.** Isso é intencional: é o que faz a declaração ser obrigatória
em vez de recomendada.

Os valores legais de cada buraco estão na skill acionada via MCP `skills_klavi_catalogo`,
seção "Os buracos compartilhados".

## O molde de agregação

```sql
-- ═══ PREFIXO OBRIGATÓRIO — cole antes de qualquer métrica agregada ═══
WITH cells AS (
  SELECT CAST(<DIM> AS VARCHAR)          AS dim,
         SUM(amount)                     AS valor,
         -- COUNT(DISTINCT purchase_key), never COUNT(*): an instalment purchase is one
         -- row per instalment in the card feed, so COUNT(*) counts instalments and any
         -- per-purchase average comes out roughly halved (1.32x on this base).
         COUNT(DISTINCT purchase_key)    AS compras,
         COUNT(DISTINCT external_id)     AS pessoas
  FROM clean__klavi_spend_cube
  WHERE <FILTROS>
  GROUP BY CAST(<DIM> AS VARCHAR)
),
marcado AS (
  SELECT *,
         SUM(CASE WHEN pessoas < 50 THEN 1 ELSE 0 END) OVER () AS pequenas,
         ROW_NUMBER() OVER (ORDER BY pessoas, dim)             AS rn,
         COUNT(*) OVER ()                                      AS celulas_no_escopo
  FROM cells
),
base AS (
  -- COMPLEMENTARY SUPPRESSION: a cell below the floor becomes `outros`; and if it were
  -- the ONLY one, the second smallest goes too — otherwise the bucket IS the suppressed
  -- cell and subtracting the total recovers it exactly.
  SELECT CASE WHEN pessoas < 50 OR (pequenas = 1 AND rn <= 2) THEN 'outros' ELSE dim END
             AS bucket,
         CASE WHEN pessoas < 50 OR (pequenas = 1 AND rn <= 2) THEN 1 ELSE 0 END
             AS suprimida,
         valor, compras, pessoas, celulas_no_escopo
  FROM marcado
)

-- and the final SELECT, which changes only in the columns the ficha asks for:

SELECT bucket                                          AS <DIM_ROTULO>,
       SUM(pessoas)                                    AS pessoas,
       SUM(compras)                                    AS compras,
       ROUND(SUM(valor), 2)                            AS valor,
       ANY_VALUE(celulas_no_escopo)                    AS celulas_no_escopo,
       SUM(suprimida)                                  AS celulas_suprimidas
FROM base
GROUP BY bucket
ORDER BY valor DESC;
```

**Toda ficha que usa este molde declara `<DIM>`, `<DIM_ROTULO>` e `<FILTROS>`** na linha
"Buracos obrigatórios", junto dos buracos próprios dela. Os três são buracos do prefixo do
piso (definidos na skill `skills_klavi_catalogo`, seção "Os buracos compartilhados"), mas o lint exige a
declaração na ficha — e a razão é que um buraco que ninguém declarou é um buraco que ninguém
sabe que precisa preencher.

### Regra de publicação do balde

**Se a linha `outros` vier com `celulas_suprimidas = 1`, não publique.** O balde *é* a célula
suprimida, e subtrair do total a recupera exata. Diga que o recorte é fino demais e peça um
escopo mais amplo.

## share_de_marca

**Responde:** que fração do mercado uma marca representa, no nível de taxonomia declarado.

**Decisão embutida:** o denominador **escapa** do filtro da marca — sem isso o share é sempre
100%. E o nível é obrigatório: o mesmo numerador dividido pelos três níveis dá respostas que
diferem por mais de 2×, e publicar um sem dizer qual é o erro que esta skill existe para
impedir.

**Buracos obrigatórios:** `<MARCA>`, `<NIVEL>`, `<JANELA>`, `<RECORTE>` — e os três do prefixo
do piso: `<DIM>` (fixo em `brand`), `<DIM_ROTULO>` (fixo em `marca`), `<FILTROS>` (a linha do
nível escolhido, escrita por extenso no corpo abaixo).

**Dimensões permitidas na quebra:** a dimensão é fixa em `brand` — share é sempre por marca.

**Descobrir antes:** a grafia de `<MARCA>`, por `valores_de_dimensao` com `<DIMENSAO> = brand`
e `<ESCOPO>` do setor da pergunta.

**Não responde:** valor absoluto sem denominador — isso é `volume_de_marca`.

**Piso:** um portão, pelo prefixo de supressão complementar, sobre as células por marca.

### O corpo — o `<NIVEL>` derivado da marca

`<DIM>` é fixo em `brand` e `<DIM_ROTULO>` em `marca`. `<FILTROS>` é a cláusula que liga o
nível escolhido ao `alvo` — as três formas estão escritas por extenso abaixo, para que
preencher seja escolher uma linha e não redigir SQL:

```sql
-- The denominator is drawn at the declared level, DERIVED from the brand — never from a
-- hardcoded sector id. This is what makes the ficha portable to another base.
WITH alvo AS (
  SELECT DISTINCT sector_l1, sector_l2, sector_l3_id
  FROM clean__klavi_spend_cube
  WHERE brand = <MARCA>
    AND <RECORTE>
    AND transaction_date >= (SELECT MAX(transaction_date) - <JANELA>
                             FROM clean__klavi_spend_cube)
)
-- <FILTROS> takes ONE of these three lines, according to <NIVEL>:
--
--   segmento   AND sector_l3_id IN (SELECT sector_l3_id FROM alvo)
--   grupo      AND sector_l2    IN (SELECT sector_l2    FROM alvo)
--   categoria  AND sector_l1    IN (SELECT sector_l1    FROM alvo)
--
-- always followed by:
--   AND <RECORTE>
--   AND transaction_date >= (SELECT MAX(transaction_date) - <JANELA>
--                            FROM clean__klavi_spend_cube)
```

Com `<NIVEL> = todos`, rode as três e apresente os três blocos. Não há forma de "todos" numa
consulta só sem duplicar o prefixo três vezes, e duplicar o prefixo é exatamente o que a fonte
única existe para evitar — então `todos` são três execuções.

### `<NIVEL> = todos` é o valor sugerido

Com `todos`, o resultado traz os três blocos e **não há um número para publicar como "o
share"** — escolher passa a ser decisão de quem lê, que é onde ela pertence. O resultado
também mostra *por que* varia: no nível de categoria entram no denominador marcas que não
competem no segmento, cada uma podendo ser maior que a marca perguntada.

### Se a marca resolver para mais de um segmento, pergunte

A derivação assume que uma marca vive num segmento só. Se o `alvo` devolver mais de uma linha,
**pare e pergunte qual segmento**. Não escolha, e não use o primeiro.

Há teste que afirma essa propriedade na base atual
(`golden-set/tests_pytest/test_marca_nao_atravessa_segmento.py`). Ele existe para que a
mudança falhe alto em vez de virar escopo errado em silêncio.

## volume_de_marca

**Responde:** quanto uma marca movimentou — valor, compras e pessoas — no período declarado,
opcionalmente quebrado por uma dimensão.

**Decisão embutida:** esta consulta **não tem denominador**, logo não responde share. E o
período é obrigatório: sem ele a resposta é o histórico inteiro, que quase nunca é a pergunta.

**Buracos obrigatórios:** `<MARCA>`, `<PERIODO>`, `<QUEBRA>`, `<RECORTE>` — e os três do
prefixo do piso: `<DIM>` (recebe a `<QUEBRA>`), `<DIM_ROTULO>` (o nome da quebra, em
português), `<FILTROS>` (a composição escrita por extenso no corpo abaixo).

**Descobrir antes:** a grafia de `<MARCA>`, por `valores_de_dimensao`.

**Não responde:** share (é `share_de_marca`), nem ticket (é `ticket_de_marca`).

**Piso:** um portão, sobre as células da `<QUEBRA>`.

### O corpo — os buracos na posição executável

`<DIM>` recebe a `<QUEBRA>`; com `<QUEBRA> = nenhuma`, `<DIM>` é a constante `'total'` (uma
célula só, o escopo inteiro) e `<DIM_ROTULO>` é `total`. `<FILTROS>` é a composição abaixo:

```sql
-- <FILTROS> for volume_de_marca — the brand, the declared period, the declared recorte:
--
--   brand = <MARCA>
--   AND <PERIODO>
--   AND <RECORTE>
--
-- <PERIODO> is a WHERE clause, never absent. Two legal shapes:
--   a calendar month named in the question:   month = DATE '<yyyy-mm-01>'
--   a relative window, anchored at the base:  transaction_date >=
--     (SELECT MAX(transaction_date) - <JANELA> FROM clean__klavi_spend_cube)
-- Never now(), never CURRENT_DATE — the base is static and the clock is ahead of it.
```

## ranking_de_marcas

**Responde:** as marcas de um escopo, ordenadas, com corte no top N.

**Decisão embutida:** ranquear por pessoas, por valor ou por compras produz **listas
diferentes**, e a pergunta "as maiores" não diz qual. O critério é obrigatório e vai declarado
na resposta.

**Buracos obrigatórios:** `<ESCOPO>`, `<CRITERIO>`, `<TOP_N>`, `<PERIODO>` — e os três do
prefixo do piso: `<DIM>` (fixo em `brand`), `<DIM_ROTULO>` (fixo em `marca`), `<FILTROS>` (a
composição escrita por extenso no corpo abaixo).

**Descobrir antes:** o valor de `<ESCOPO>`, por `valores_de_dimensao`.

**Não responde:** "as N maiores do mercado" — responde "as N maiores do escopo declarado". Se o
escopo é uma lista curada de marcas em vez de um setor da taxonomia, a manutenção dessa lista é
de quem a escreveu, e a resposta tem que dizer isso.

**Piso:** um portão, sobre as células por marca.

### O corpo — os buracos na posição executável

`<DIM>` é fixo em `brand` e `<DIM_ROTULO>` em `marca` — as linhas do ranking são marcas.
`<CRITERIO>` e `<TOP_N>` entram no `SELECT` final do molde, que nesta ficha é **substituído
pelo bloco abaixo** (os CTEs `resultado` e `topo` continuam o `WITH` do prefixo, depois de
`base`):

```sql
-- <FILTROS> for ranking_de_marcas — the declared scope plus the declared period:
--
--   <ESCOPO>
--   AND <PERIODO>
--
-- <PERIODO> takes the same shapes as in volume_de_marca; TRUE is legal here ONLY as the
-- explicit "whole history" declaration, said next to the number.
--
-- The LIMIT applies to brand rows ONLY. The `outros` bucket carries <50-people cells, so it
-- typically ranks last — a plain LIMIT would cut it before anyone sees it: every visible row
-- would say celulas_suprimidas = 0 and the bucket-publication rule would have nothing to
-- check. The UNION ALL below fetches the outros row unconditionally, so suppression can
-- never be cut unseen.

resultado AS (
  SELECT bucket                                          AS marca,
         SUM(pessoas)                                    AS pessoas,
         SUM(compras)                                    AS compras,
         ROUND(SUM(valor), 2)                            AS valor,
         ANY_VALUE(celulas_no_escopo)                    AS celulas_no_escopo,
         SUM(suprimida)                                  AS celulas_suprimidas
  FROM base
  GROUP BY bucket
),
topo AS (
  SELECT * FROM resultado
  WHERE marca <> 'outros'
  -- <CRITERIO> is one of the output columns (pessoas / valor / compras), declared in the
  -- answer next to the list — a different criterion is a different list.
  ORDER BY <CRITERIO> DESC
  LIMIT <TOP_N>
),
final AS (
  SELECT * FROM topo
  UNION ALL
  SELECT * FROM resultado WHERE marca = 'outros'  -- unconditional: present iff suppression acted
)
SELECT * FROM final
ORDER BY (marca = 'outros'), <CRITERIO> DESC;
```

A linha `outros`, quando vier, não é uma marca e **não ocupa posição do ranking** — o bloco
acima já a mantém fora do `LIMIT` e a devolve por último. Reporte-a junto da lista, com
`celulas_suprimidas`, e aplique a "Regra de publicação do balde" antes de publicar.

## ticket_de_marca

**Responde:** o valor médio por marca, no denominador declarado.

**Decisão embutida:** "ticket" tem dois denominadores legítimos e eles diferem por cerca de
2,4× nesta base. A ficha do caso 11 decide (`usecases/analise-casos.md`, caso 11): *"Pela
redação — 'dos usuários' — o denominador é gente, não transação. Nossa decisão para o
conjunto: valor total ÷ pessoas ativas no mês."* `ticket_por_compra` é uma pergunta legítima
por conta própria (preço médio por transação) e **não** é a resposta a "ticket mensal".
Publicar um rotulado como o outro é um erro de cerca de 2,4× que nenhum verificador numérico
pega — os dois números são individualmente corretos.

**Buracos obrigatórios:** `<ESCOPO>`, `<DENOMINADOR>`, `<PERIODO>`

**`<DENOMINADOR>` sugerido:** `ambos`. Com `ambos` as duas colunas vêm lado a lado e a resposta
**tem que dizer qual está entregando** — o que evita publicar uma rotulada como a outra.

**Descobrir antes:** o valor de `<ESCOPO>`, por `valores_de_dimensao`.

**Base:** `clean__klavi_purchase`, não o cubo. O grão aqui é a compra, e contar parcela como
compra infla o volume em quase 2× e derruba o ticket pela metade.

**Não responde:** gasto médio de um grupo de pessoas — isso é `gasto_medio_na_coorte`, e o
denominador lá é outro.

**Piso:** um portão, sobre as células por marca.

### Esta ficha não usa o molde de agregação

A base é `clean__klavi_purchase`, não `clean__klavi_spend_cube` — o prefixo do molde está
escrito sobre o cubo (`amount`, `purchase_key`, `transaction_date`) e não se aplica byte a byte
aqui. O grão do resultado são células por marca com um portão `HAVING` simples, então os três
buracos do prefixo (`<DIM>`, `<DIM_ROTULO>`, `<FILTROS>`) **não existem nesta ficha** — a linha
"Buracos obrigatórios" declara só os buracos próprios dela. O buraco que abandonar o prefixo
abre está registrado por extenso abaixo, em "O piso é fraco neste caso" — é o aviso de partição
que cobre a lacuna, não uma dispensa dela.

### O corpo — os buracos na posição executável

```sql
-- This ficha does NOT paste the suppression prefix: the base is clean__klavi_purchase
-- (purchase grain), not the cube, and the floor here is a plain HAVING gate per brand
-- cell. The gap this opens is recorded below, in "O piso é fraco neste caso".
WITH celulas AS (
  SELECT brand                                        AS marca,
         COUNT(DISTINCT external_id)                  AS pessoas,
         -- COUNT(*) is correct HERE and only here: the grain of clean__klavi_purchase is
         -- the purchase (one row per purchase, amount_total already whole). On the cube it
         -- would count instalment rows and halve any per-purchase average.
         COUNT(*)                                     AS compras,
         SUM(amount_total)                            AS valor,
         COUNT(DISTINCT external_id || '|' || month)  AS pessoa_mes
  FROM clean__klavi_purchase
  WHERE <ESCOPO>
    AND <PERIODO>
  GROUP BY brand
  HAVING COUNT(DISTINCT external_id) >= 50
)
SELECT marca,
       pessoas,
       compras,
       ROUND(valor, 2) AS valor,
       -- <DENOMINADOR> lands here, in executable position — left unfilled, the SELECT
       -- list is invalid SQL and the query errors instead of degrading silently:
       <DENOMINADOR>
FROM celulas
ORDER BY valor DESC;

-- <DENOMINADOR> takes ONE of these three column blocks, per the declared value:
--
--   pessoa_mes  ROUND(valor / pessoa_mes, 2) AS ticket_por_pessoa_mes
--   compra      ROUND(valor / compras, 2)    AS ticket_por_compra
--   ambos       ROUND(valor / pessoa_mes, 2) AS ticket_por_pessoa_mes,
--               ROUND(valor / compras, 2)    AS ticket_por_compra
--
-- <PERIODO> is a WHERE clause, never absent. Legal shapes, anchored at THIS base's date
-- column (purchase_date — clean__klavi_purchase has no transaction_date):
--   a calendar month named in the question:   month = DATE '<yyyy-mm-01>'
--   a relative window, anchored at the base:  purchase_date >=
--     (SELECT MAX(purchase_date) - <JANELA> FROM clean__klavi_purchase)
--   TRUE is legal ONLY as the explicit "whole history" declaration, said next to the number.
-- Never now(), never CURRENT_DATE.
```

### O piso é fraco neste caso, e isso está registrado

As marcas dentro de um setor **particionam** o total do setor, então a subtração reconstrói a
célula suprimida. O desenho pediria o prefixo de supressão complementar. Correção pendente,
registrada — não a trate como resolvida.

## gasto_medio_na_coorte

**Responde:** o gasto médio de um grupo de pessoas, quebrado por uma dimensão.

**Decisão embutida duas vezes.** Primeira: **dois portões de piso.** A coorte passa o piso para
poder virar filtro, **e** cada célula publicada passa o piso de novo — sem o segundo, uma coorte
de 60 pessoas quebrada em três categorias publica células de 20, a partir de dois passos que
individualmente passaram. Segunda: **média por pessoa do grupo ≠ média por quem gastou.** As
duas são legítimas e bem diferentes, e a resposta tem que dizer qual.

**Buracos obrigatórios:** `<COORTE>`, `<DIMENSAO>`, `<DENOMINADOR_COORTE>`, `<PERIODO>`

**`<DENOMINADOR_COORTE>` é buraco local desta ficha, não o `<DENOMINADOR>` compartilhado do
catálogo** — o eixo aqui é grupo-inteiro × comprador-de-fato, diferente do eixo pessoa-mês ×
transação de `ticket_de_marca`. Mesmo símbolo para os dois seria exatamente o defeito que este
redesenho existe para fechar: o mesmo nome de buraco significando coisas diferentes em fichas
diferentes.

**`<DENOMINADOR_COORTE>` sugerido:** `ambos`. Com `ambos` as duas leituras vêm lado a lado e a resposta
**tem que dizer qual está entregando** — o que evita publicar uma rotulada como a outra, o mesmo
defeito de 2,4× que `ticket_de_marca` fecha, aqui com um par diferente de denominadores.

**`<COORTE>` recebe o nome de uma consulta de coorte com os buracos dela preenchidos**, não o
SQL dela. Passar SQL cru aqui reabre o caminho de escrever consulta livre.

**Descobrir antes:** os valores da `<DIMENSAO>`, por `valores_de_dimensao`.

**Não responde:** ticket de marca — isso é `ticket_de_marca`, e o denominador lá é outro.

**Piso:** **dois portões**, conforme acima.

### O corpo — os buracos na posição executável

Base: `clean__klavi_person_sector_month` — o grão é pessoa-mês-categoria, o mesmo grão de que os
dois portões e os dois blocos de `<DENOMINADOR_COORTE>` dependem. `<DIMENSAO>` aqui é o **valor**
do nível pai que a resposta desagrega (nesta base, um valor de `sector_l1`); a quebra em categorias-filhas
(`sector_l3`, coluna fixa desta tabela — estrutural, não taxonomia) é automática e devolve
**todas** as que existirem, não uma lista escolhida à mão. Ver a seção seguinte.

```sql
-- <COORTE> is NOT raw SQL: it names one of the four cohort queries (skills_klavi_coorte) with its
-- own holes already filled. Substitute this CTE with that query's own people-defining logic,
-- reduced to the set of external_id it certifies — copied from its ficha, never freehand.
WITH coorte AS (
  <COORTE>
),
-- Gate 1, as a HAVING with no GROUP BY: it collapses to one row when the cohort clears the
-- floor and to ZERO rows when it doesn't — the CROSS JOIN below then wipes every category row
-- at once if it fails, not just flags them one by one.
coorte_ok AS (
  SELECT COUNT(*) AS pessoas FROM coorte
  HAVING COUNT(*) >= 50
),
-- The cohort's OWN active person-months in the declared period, regardless of which category
-- (or none) each member bought — the denominator of the "grupo" reading below.
pessoa_mes_grupo AS (
  SELECT COUNT(DISTINCT external_id || '|' || month) AS n
  FROM clean__klavi_person_month
  WHERE external_id IN (SELECT external_id FROM coorte)
    AND <PERIODO>
),
celulas AS (
  SELECT s.sector_l3                                      AS categoria,
         COUNT(DISTINCT s.external_id)                    AS compradores,
         COUNT(DISTINCT s.external_id || '|' || s.month)  AS pessoa_mes_compradores,
         ROUND(SUM(s.spend), 2)                            AS valor
  FROM clean__klavi_person_sector_month s
  JOIN coorte c ON c.external_id = s.external_id
  WHERE s.sector_l1 = <DIMENSAO>
    AND <PERIODO>
  GROUP BY s.sector_l3
  -- Gate 2, the other HAVING: each published category clears the floor on its own — this
  -- alone is NOT enough, see Gate 1 above.
  HAVING COUNT(DISTINCT s.external_id) >= 50
)
SELECT categoria,
       compradores,
       valor,
       <DENOMINADOR_COORTE>
FROM celulas
CROSS JOIN coorte_ok        -- zero rows here means zero rows out: Gate 1 failing wipes all
CROSS JOIN pessoa_mes_grupo
ORDER BY compradores DESC;

-- <DENOMINADOR_COORTE> takes ONE of these column blocks, per the declared value:
--
--   grupo      ROUND(valor / (SELECT n FROM pessoa_mes_grupo), 2) AS gasto_medio_por_membro_do_grupo
--   comprador  ROUND(valor / pessoa_mes_compradores, 2)           AS gasto_medio_por_comprador
--   ambos      ROUND(valor / (SELECT n FROM pessoa_mes_grupo), 2) AS gasto_medio_por_membro_do_grupo,
--              ROUND(valor / pessoa_mes_compradores, 2)           AS gasto_medio_por_comprador
--
-- <PERIODO> is a WHERE clause, never absent. Legal shapes, anchored at THIS base's date
-- column (month — clean__klavi_person_sector_month has no transaction_date):
--   a calendar month named in the question:   month = DATE '<yyyy-mm-01>'
--   a relative window, anchored at the base:  month >=
--     (SELECT MAX(month) - <JANELA> FROM clean__klavi_person_sector_month)
--   TRUE is legal ONLY as the explicit "whole history" declaration, said next to the number.
-- Never now(), never CURRENT_DATE.
```

`grupo` e `comprador` não são a mesma pergunta com nomes diferentes: `grupo` espalha o gasto da
categoria por **todo mundo da coorte**, tenha ou não comprado aquela categoria naquele mês;
`comprador` espalha só pelos pessoa-mês de quem **de fato** comprou. As duas caem por SQL válido
— a ficha não escolhe por conta própria, por isso `ambos` é o sugerido.

Se uma categoria some do resultado, isso não é necessariamente supressão — pode ser zero
genuíno (ninguém da coorte comprou aquela categoria naquele recorte). Distinga do jeito de
`coorte_limiar_janela` ("Zero linhas: três causas"): rode a célula isolada sem o Gate 2 antes de
rotular a ausência.

### A dimensão vem derivada, não cravada

Para "as categorias de X", derive por nível — `sector_l1` devolve todos os filhos — em vez de
listar os valores que você espera. Listar à mão produz um domínio incompleto apresentado como
completo, que é uma resposta errada com cara de resposta certa: a categoria que você não listou
existe e não aparece.

Quando a resposta usar um subconjunto das categorias, **diga que é subconjunto e quantas
existem.**
