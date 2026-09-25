---
name: klavi_catalogo
display_name: Catálogo certificado de consumo
description: Porta de entrada das consultas de CONSUMO Klavi (share, volume, ranking, ticket, coortes, valores de dimensão). Não cobre documentação, APIs, webhooks, erros, ambientes ou capacidades dos produtos Klavi; para isso use search_knowledge. Roteia a pergunta para a consulta nomeada certa ou devolve recusa quando a pergunta cai num ramo indistinguível da taxonomia. Zero SQL executável, zero número medido.
category: consumer_insights
tags: [catálogo, roteamento, recusa, piso, privacidade, klavi]
---

# Catálogo certificado — leia primeiro

Este arquivo não responde pergunta. Ele diz **qual consulta nomeada** responde, ou que a
pergunta não tem resposta certificada.

**Zero SQL, zero número, zero valor de taxonomia.** Se você precisa de um valor, use
`valores_de_dimensao`. Se você precisa de um número, execute a consulta.

## Como usar

1. Case a redação da pergunta com uma entrada da tabela abaixo.
2. Abra a ficha da consulta no arquivo indicado.
3. Preencha os buracos obrigatórios. **Se um deles não foi declarado pelo usuário, pergunte e
   aguarde** — não escolha por ele.
4. Execute. Publique citando a consulta, o escopo, a janela e o recorte.

## Escopo deste catálogo

Este catálogo cobre consultas de consumo (share, volume, ranking, ticket, coortes, valores de
dimensão) sobre a base Klavi. Perguntas sobre documentação, integração, APIs, webhooks,
erros, ambientes ou capacidades dos produtos Klavi (Conecte, Eco, Payment, Monitore, Klaas)
não passam por aqui: use `search_knowledge`. Ausência neste catálogo não significa ausência
na plataforma Klavi.

## Roteamento

| A pergunta soa como | Consulta | Skill (acionada via MCP) |
|---|---|---|
| "quanto X tem de mercado", "share de X" | `share_de_marca` | `skills_klavi_agregacao` |
| "quanto X faturou", "volume de X no período" | `volume_de_marca` | `skills_klavi_agregacao` |
| "as N maiores de", "ranking de" | `ranking_de_marcas` | `skills_klavi_agregacao` |
| "ticket de X", "gasto médio por usuário de X" | `ticket_de_marca` | `skills_klavi_agregacao` |
| "gasto médio de quem tem X" | `gasto_medio_na_coorte` | `skills_klavi_agregacao` |
| "quantas pessoas gastaram mais de N em X" | `coorte_limiar_janela` | `skills_klavi_coorte` |
| "quem tem e quem não tem X" | `posse_e_complemento` | `skills_klavi_coorte` |
| "usam A e B", "têm A e B" | `posse_de_dois_valores` | `skills_klavi_coorte` |
| "migrou de A para B", "usava A e agora usa B" | `transicao_entre_valores` | `skills_klavi_coorte` |
| "quais valores existem", "como se escreve" | `valores_de_dimensao` | `skills_klavi_descoberta` |

## Recusas

Estas não têm consulta. O motivo está escrito **uma vez**, abaixo.

| A pergunta soa como | Veredito |
|---|---|
| ticket, gasto ou contagem de um ramo de seguro que a taxonomia não separa | **RECUSA** — ramo indistinguível |
| interseção entre dois ramos que caem no mesmo balde | **RECUSA** — ramo indistinguível |

### Ramo indistinguível

Quando dois produtos que a pergunta trata como distintos caem no **mesmo valor** da taxonomia,
nenhuma métrica sobre esse valor responde a pergunta — nem contagem, nem ticket, nem gasto.
O número sai plausível e responde outra pergunta.

**Não adapte nenhuma consulta trocando o filtro pelo balde que os contém.** Parece adaptação
natural e não é.

A recusa é **terminal**: não ofereça cálculo alternativo sobre o mesmo escopo bloqueado, nem
pergunte se o usuário quer seguir por outro caminho dentro dele. O que dá para oferecer é a
pergunta ao cliente que destravaria o caso — a separação na taxonomia.

## O contrato de declaração

Nada é publicado sem estes cinco declarados. Onde o buraco existe, ele é obrigatório no SQL;
onde não existe, é obrigação sua.

| O quê | Por quê |
|---|---|
| **Escopo** | o mesmo numerador sob fronteiras diferentes dá respostas que diferem por mais de 2× |
| **Janela** | ancorada no dado, nunca no relógio |
| **Recorte** | "em São Paulo" tem duas leituras, estado e município, e elas divergem |
| **Universo** | quem tinha consentimento no período ≠ quem tem consentimento |
| **Denominador** | por pessoa, por pessoa-mês e por compra dão números bem diferentes |

## Os buracos compartilhados

Definidos aqui — e só aqui — porque aparecem em várias fichas. Os valores legais são
**estruturais** (enums e nomes de coluna), nunca valores de taxonomia — então enumerá-los não
envelhece quando a Klavi mexer na árvore de categorias.

| Buraco | Forma | Valores legais |
|---|---|---|
| `<NIVEL>` | enum | `segmento` · `grupo` · `categoria` · `todos` (sugerido) |
| `<DENOMINADOR>` | enum | `pessoa_mes` · `compra` · `ambos` (sugerido) |
| `<SIMULTANEIDADE>` | enum | `no_mes` · `no_historico` · `ambos` (sugerido) |
| `<CRITERIO>` | enum | `pessoas` · `valor` · `compras` |
| `<UNIVERSO>` | enum | `is_in_panel` · `is_eligible` |
| `<QUEBRA>` | nome de coluna ou `nenhuma` | `channel` · `month` · `uf` · `city` · `nenhuma` |
| `<DIMENSAO>` | nome de coluna | `brand` · `sector_l1` · `sector_l2` · `sector_l3` · `channel` · `uf` · `city` |
| `<ESCOPO>` | par dimensão + valor | dimensão da lista acima; **o valor vem de `valores_de_dimensao`** |
| `<COORTE>` | **nome** de uma consulta de coorte, com os buracos dela preenchidos | as quatro da família coorte |
| `<PERIODO>` `<JANELA>` | intervalo ancorado em `MAX(transaction_date)` | — |
| `<RECORTE>` | par dimensão geográfica + valor | dimensão é `uf` ou `city`; o valor vem da descoberta |
| `<MARCA>` `<VALOR>` `<VALOR_A>` `<VALOR_B>` `<LIMIAR>` `<TOP_N>` | valor único | vêm da descoberta ou do usuário |
| `<DIM>` | nome de coluna — buraco do **prefixo do piso** | a dimensão que a resposta desagrega |
| `<DIM_ROTULO>` | rótulo da coluna de saída | palavra única, em português |
| `<FILTROS>` | cláusula `WHERE` — buraco do **prefixo do piso** | o escopo confirmado, nunca omitido |

**`<DIM>`, `<DIM_ROTULO>` e `<FILTROS>` são buracos do prefixo do piso**, não das fichas — mas
toda ficha que usa o molde de agregação **declara os três** na linha "Buracos obrigatórios",
junto dos buracos próprios dela. Isso é intencional: um buraco que ninguém declarou é um buraco
que ninguém sabe que precisa preencher.

**`<COORTE>` recebe o nome da consulta, não o SQL dela.** Passar SQL cru ali reabriria o
caminho de escrever consulta livre, que é o que este desenho fecha.

**`<RECORTE>` é par, não valor solto.** "Em São Paulo" tem duas leituras — estado e município —
e elas dão respostas diferentes. O par obriga dizer qual.

**Âncora de tempo.** `<PERIODO>` e `<JANELA>` são sempre relativos a
`(SELECT MAX(transaction_date) FROM clean__klavi_spend_cube)`. Nunca `now()`, nunca
`CURRENT_DATE`: a base é estática e o relógio está à frente dela, então uma janela ancorada no
relógio devolve zero linhas — e zero linhas com cara de resposta é o modo de falha que estas
skills existem para impedir.

**"Últimos N meses" é `INTERVAL (N-1) MONTH`, não `INTERVAL N MONTH`.** Em tabelas de grão
mês (`month` como primeiro dia do mês), `MAX(month)` já é o primeiro dos N meses pedidos —
subtrair N conta um mês a mais. Para "últimos 3 meses" com `MAX(month) = 2026-06-01`, a âncora
certa é `MAX(month) - INTERVAL 2 MONTH` = `2026-04-01` (abril, maio, junho); `INTERVAL 3 MONTH`
ancora em março e cobre quatro meses. Confira contando os meses do resultado antes de publicar,
não só a fórmula.

## O piso, e o que ele não é

Toda consulta certificada aplica `k = 50`. Nenhuma resposta entrega célula abaixo disso.

**Isso é convenção de publicação, não anonimato.** O `run_sql` alcança o cubo direto, e no cubo
há combinações de atributos que identificam pessoa. Se perguntarem "isso é anônimo?", a resposta
é **não**.

E não afirme que o controle é inviolável: nenhuma consulta certificada devolve identificador,
mas a plataforma não impede que alguém escreva a sua própria. O texto correto é *"esta consulta
não devolve identificador"*, nunca *"não é contornável"*.

## Número documentado × número medido

Se você citar um número que veio de documentação em vez de execução, **rotule como
documentado**. Só entra como resultado o que saiu de uma execução deste turno. Se você não
executou agora, você não mediu nada agora.
