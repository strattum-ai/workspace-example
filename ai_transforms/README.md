# ai_transforms — LLM enrichment (code-first)

Transforms de enriquecimento via LLM da RD Station. Cada arquivo define uma
subclasse de `AITransform` (contrato da plataforma). A plataforma **descobre**
estes transforms pinados num commit SHA e o **engine genérico** os executa
(cache, concorrência bounded, retry, persistência, custo) — aqui mora só a
lógica do cliente (prompt, schema, filtro, pós-processamento).

Arquitetura: ClickUp 86aj74pmx.

| Transform | Saída | Tabela enrichment |
|---|---|---|
| [`playbook_adherence.py`](./playbook_adherence.py) | Check-up de Qualidade da call de CS contra a Matriz de Critérios da RD (score + status por critério + evidência) | `enrichment.rd_station__playbook_adherence` |

O resultado é consumido na camada clean por
[`transformations/staging/tldv_playbook_adherence.sql`](../transformations/staging/tldv_playbook_adherence.sql)
(LEFT JOIN nas reuniões → toda call aparece, `pending` quando ainda não analisada).

## Convenções para escrever um `AITransform`

Regras aprendidas rodando o engine e o **preview** de verdade. Seguir evita os
erros que mais aparecem (todos viram "preview falhou" / linhas `failed`).

### 1. `model` usa id do LiteLLM **com prefixo de provider**

O engine roteia o modelo via LiteLLM. Um nome "limpo" sem provider não roteia.

```python
model = "anthropic/claude-sonnet-4-6"   # ✅ LiteLLM sabe que é Anthropic
# model = "claude-sonnet-4-6"           # ❌ sem provider → "LLM Provider NOT provided"
# model = "gpt-4o"                       # ✅ OpenAI é inferido; "openai/gpt-4o" também vale
```

A credencial é resolvida pela env do provider (`ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, …) — não precisa casar com o `LLM_PROVIDER` configurado, então
um transform pode pedir Sonnet mesmo num ambiente default OpenAI, desde que a
chave do provider exista.

### 2. `output_schema` precisa ser **structured-output-compatible**

Anthropic e OpenAI (modo strict) exigem `additionalProperties: false` em todo
objeto e **não aceitam `dict` aberto**. Logo:

- ❌ `dict[str, float]`, `dict[str, Any]` → "additionalProperties ... is not supported".
- ✅ Use `list[ItemModel]` (ex.: `list[BlockScore]`) ou campos fixos nomeados.
- Mantenha o schema do LLM **enxuto**: só o que o LLM realmente gera. Números
  derivados (scores, contagens, agregações) **não** vão no schema do LLM.

### 3. Separe o schema do LLM do que é persistido — calcule em `post()`

Padrão recomendado: um schema enxuto que o LLM retorna + `post()` que enriquece.

```python
class FooLLM(BaseModel):          # output_schema — o que o LLM devolve
    items: list[Item]
    summary: str

class Foo(BaseModel):            # persistido (result_json) — LLM + derivados
    items: list[Item]
    summary: str
    score: float | None = None

class FooTransform(AITransform):
    output_schema = FooLLM
    def post(self, result: FooLLM, row) -> Foo:   # números determinísticos aqui
        return Foo(items=result.items, summary=result.summary, score=_compute(result.items))
```

Vantagens: o LLM não "inventa" números, o resultado é reprodutível, e o schema
enviado ao provider fica simples (sem campos opcionais/computados).

### 4. `from __future__ import annotations` + modelos aninhados

Se usar `from __future__ import annotations` (anotações viram strings), o engine
já registra o módulo em `sys.modules` antes de importar, então forward-refs como
`list[CriterionResult]` resolvem. Só não defina o schema dentro de uma função
(classe aninhada em escopo local não é resolvível pelo Pydantic).

### 5. Atributos do contrato (rápido)

`connector`, `source` (SQL/`delta_scan(...)`), `target` (`enrichment.<tabela>`),
`output_schema`, `model`, `prompt_version` (bump invalida o cache → reprocessa),
`id_field` (PK estável da linha), `max_concurrency`, `failure_policy`
(`proceed`/`block`). Opcional: `price_per_1m_input`/`price_per_1m_output` como
fallback de custo quando o LiteLLM não conhece o preço do modelo.

> Antes de ligar o pipeline, use o **Preview** no painel do conector (roda 1
> linha real e estima o custo) — pega esses erros de schema/modelo na hora.

## `playbook_adherence.py` — Check-up de Qualidade de CS

Avalia cada transcrição contra a **Matriz de Critérios de Qualidade** oficial
("Guia | Critérios de Qualidade"), na escala de 4 níveis:

- `executou` — completo, consistente, alinhado às boas práticas
- `executou_parcialmente` — observado, mas com profundidade/consistência insuficiente
- `nao_executou` — não observado na reunião
- `na` — não se aplica ao contexto (regra de N/A própria por critério)

**Saída** (`result_json`): `criteria[]` (status + evidência por critério),
`summary`, `strengths`, `improvements`, e — calculados deterministicamente em
`post()` a partir dos status — `adherence_score` (0..1, ponderado, exclui N/A),
`classificacao` (`boa` ≥ 0,75 / `regular` [0,5; 0,75) / `ruim` < 0,5),
`followed_playbook` (== `boa`), contagens `n_executou/n_parcial/n_nao_executou/n_na`
e `block_scores` por bloco da matriz.

### Validação contra labels do cliente

Benchmark contra `quality_labels.jsonl` (validado pela RD), 16 calls / 384
comparações de critério. A fórmula de score e os thresholds de `classificacao`
reproduzem exatamente os do cliente; o que se calibrou foi o grader.

| Config | Exata | ±1 nível | MAE score | Falso "executou" p/ comportamento ausente |
|---|---|---|---|---|
| gpt-4o (sem few-shot) | 77% | 89% | 0,09 | 13 ❌ |
| gpt-4o (few-shot) | 79% | 88% | 0,09 | 14 ❌ |
| **Sonnet (few-shot, v5)** | 67% | 92% | 0,12 | **2 ✅** |

Decisão: **`claude-sonnet-4-6` + few-shot (v5)**. O few-shot (snippets reais dos
labels) só surte efeito no Sonnet — o gpt-4o ignora e continua leniente,
marcando "executou" para comportamentos ausentes (13–14 casos). Num check-up de
qualidade esse é o erro caro: um falso "executou" esconde um gap de coaching. O
Sonnet derruba isso para ~2. Custo: o Sonnet é um avaliador mais duro que os
humanos do cliente na fronteira executou/parcial (rebaixa alguns "executou"
limítrofes para "parcial"), o que reduz a concordância exata e leva o score a
ficar levemente abaixo do label. Para fins de coaching é o viés mais seguro.

> Medido em 16 calls — amostra pequena, classes negativas com poucos pontos.
> Rodar um lote maior (100-200 calls) antes de cravar números finais.

### Escopo: o que dá para avaliar por transcrição

A matriz tem **26 itens**. Os itens **22–26 são registro pós-call no Gainsight**
(Activity, CTA de risco, CTA de expansão, Contacts·People·Summary, Success
Plan·Cockpit·Timeline) — **não observáveis numa transcrição**. Este transform
avalia os **24 critérios falados na call**:

- **1–21** — Abertura · Diagnóstico · Condução · Fechamento
- **3 RDC** (RD Conversas / WhatsApp) — marcados `na` quando a call não é RDC

A aderência de registro (22–26) deve virar um enrichment próprio cruzado com o
Gainsight, quando essa fonte estiver conectada.
