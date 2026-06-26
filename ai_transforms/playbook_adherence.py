"""
AI transform — Check-up de Qualidade das calls de Customer Success da RD Station.

Avalia a transcrição de cada reunião de CS contra a **Matriz de Critérios de
Qualidade** da RD (documento "Guia | Critérios de Qualidade"). Cada critério é
classificado na escala oficial de 4 níveis (Executou / Executou Parcialmente /
Não Executou / Não se Aplica), com evidência citada da transcrição.

É descoberto pela plataforma (pinado num SHA) e executado pelo engine genérico
(cache / concorrência / retry / persist). Aqui mora só a lógica do cliente.

ESCOPO — o que dá para avaliar por transcrição
------------------------------------------------
A matriz tem 26 itens. Os itens **22 a 26** são *procedimentos pós-call de
registro no Gainsight* (Activity/CTA de risco/CTA de expansão/Contacts·People·
Summary/Success Plan·Cockpit·Timeline). Esses **não são observáveis numa
transcrição** — dependem de dados do CRM (Gainsight), uma fonte separada. Por
isso este transform avalia apenas o que acontece DENTRO da call:

  • critérios 1–21  (Abertura, Diagnóstico, Condução, Fechamento)
  • 3 critérios RDC (RD Conversas / WhatsApp) — N/A quando a call não é RDC

A aderência de registro (22–26) deve ser cruzada com o Gainsight num enrichment
próprio quando essa fonte estiver conectada.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from ai import AITransform  # contrato da plataforma (strattum-pipelines)


# ---------------------------------------------------------------------------
# Matriz de critérios (fonte: "Guia | Critérios de Qualidade" — RD Station).
# Cada item carrega o bloco, a pergunta, a definição de "Executou" e a regra de
# N/A. O bloco é derivado em código (não confiamos no LLM para ele).
# ---------------------------------------------------------------------------

ABERTURA = "Abertura e Contextualização"
DIAGNOSTICO = "Diagnóstico e Geração de Valor"
CONDUCAO = "Condução da Reunião"
FECHAMENTO = "Fechamento"
RDC = "Critérios Específicos RDC"

_CRITERIA: list[dict[str, str]] = [
    # ── ABERTURA E CONTEXTUALIZAÇÃO ──────────────────────────────────────
    {
        "id": "1", "block": ABERTURA,
        "criterio": "Aplicou o método ACE na abertura (Agradecer, Checar Tempo, Estabelecer Agenda)?",
        "executou": "Agradece a presença, confirma o tempo disponível e apresenta/valida a agenda.",
        "na": "",
    },
    {
        "id": "2", "block": ABERTURA,
        "criterio": "Apresentou com clareza a agenda e os objetivos da reunião?",
        "executou": "Explica o propósito da reunião, compartilha os tópicos e valida a agenda com o cliente.",
        "na": "",
    },
    {
        "id": "3", "block": ABERTURA,
        "criterio": "Demonstrou conhecimento prévio sobre o histórico do cliente/parceiro?",
        "executou": "Retoma decisões anteriores, cita dados/fatos específicos da conta e evita perguntas já registradas.",
        "na": "",
    },
    {
        "id": "4", "block": ABERTURA,
        "criterio": "Confirmou os stakeholders presentes e seus papéis no projeto?",
        "executou": "Identifica quem são os participantes, área de atuação, nível de influência/decisão e papel na operação.",
        "na": "Call com apenas um participante já conhecido e validado recentemente.",
    },
    {
        "id": "5", "block": ABERTURA,
        "criterio": "Contextualizou o modelo de atendimento da RD e a jornada do cliente/parceiro?",
        "executou": "Explica o modelo de atendimento, reforça responsabilidades de RD e cliente e contextualiza o estágio atual da jornada.",
        "na": "Calls extremamente operacionais/reativas (resolução de incidentes) ou interações pontuais sem caráter consultivo.",
    },
    {
        "id": "6", "block": ABERTURA,
        "criterio": "Retomou ou validou os objetivos/metas estratégicas do cliente/parceiro?",
        "executou": "Valida ou revisita objetivos estratégicos, metas prioritárias, indicadores de sucesso e resultados esperados.",
        "na": "Calls exclusivamente técnicas ou focadas em resolução de problemas urgentes sem espaço estratégico.",
    },
    {
        "id": "7", "block": ABERTURA,
        "criterio": "[CS Partners VAR] Educou o parceiro sobre métricas, requisitos e benefícios do Programa de Parceria?",
        "executou": "Explica critérios do programa, requisitos para evolução, métricas avaliadas, benefícios e próximos passos de crescimento.",
        "na": "Qualquer atendimento que não seja da operação Partners, ou quando o tema não é relevante para a pauta.",
    },
    # ── DIAGNÓSTICO E GERAÇÃO DE VALOR ───────────────────────────────────
    {
        "id": "8", "block": DIAGNOSTICO,
        "criterio": "Apresentou resultados alcançados até o momento (com dados)?",
        "executou": "Apresenta indicadores concretos (receita, leads, oportunidades, conversão, uso/adoção) contextualizados aos objetivos.",
        "na": "Calls iniciais sem histórico de resultados, ou handoffs sem tempo suficiente para gerar indicadores.",
    },
    {
        "id": "9", "block": DIAGNOSTICO,
        "criterio": "Investigou dores, entraves e causas das dificuldades atuais?",
        "executou": "Investiga sintoma, causa raiz, impacto no negócio e consequências da não resolução.",
        "na": "Praticamente nunca — mesmo em calls reativas espera-se investigar a origem do problema.",
    },
    {
        "id": "10", "block": DIAGNOSTICO,
        "criterio": "Conectou as funcionalidades dos produtos às dores e metas do cliente/parceiro?",
        "executou": "Relaciona claramente Dor → Funcionalidade → Benefício → Resultado esperado.",
        "na": "Quando a pauta não envolve orientação de produto, ou calls exclusivamente administrativas.",
    },
    {
        "id": "11", "block": DIAGNOSTICO,
        "criterio": "Propôs estratégias alinhadas ao segmento, jornada, maturidade e desafios do cliente/parceiro?",
        "executou": "Recomendações consideram segmento, maturidade, momento da jornada, estrutura operacional e objetivos.",
        "na": "Calls operacionais focadas em configuração ou execução exclusivamente técnica.",
    },
    {
        "id": "12", "block": DIAGNOSTICO,
        "criterio": "Abordou possibilidades de expansão (upgrade, cross-sell ou upsell)?",
        "executou": "Investigou novas necessidades, identificou oportunidades legítimas e conectou à geração de valor.",
        "na": "Sem adoção mínima que justifique expansão, ou pauta exclusivamente técnica/corretiva. (Baixa probabilidade de expansão NÃO é N/A.)",
    },
    {
        "id": "13", "block": DIAGNOSTICO,
        "criterio": "Fez perguntas consultivas para estimular a reflexão e orientar a conversa?",
        "executou": "Usa perguntas abertas e estratégicas e aproveita as respostas para aprofundar o diagnóstico.",
        "na": "",
    },
    # ── CONDUÇÃO DA REUNIÃO ──────────────────────────────────────────────
    {
        "id": "14", "block": CONDUCAO,
        "criterio": "Adaptou o discurso com base no perfil e maturidade do cliente/parceiro?",
        "executou": "Ajusta profundidade e linguagem ao perfil (executivo/operacional), maturidade digital e conhecimento técnico.",
        "na": "",
    },
    {
        "id": "15", "block": CONDUCAO,
        "criterio": "Demonstrou escuta ativa e empatia ao longo da reunião?",
        "executou": "Não interrompe, faz validações e resume entendimentos ('Se entendi corretamente, o desafio é…').",
        "na": "",
    },
    {
        "id": "16", "block": CONDUCAO,
        "criterio": "Conduziu a call de forma fluida, garantindo engajamento do cliente/parceiro?",
        "executou": "Mantém ritmo adequado, incentiva a participação ativa e evita monólogos longos (do IC ou do cliente).",
        "na": "",
    },
    {
        "id": "17", "block": CONDUCAO,
        "criterio": "Contornou objeções e mitigou riscos apresentando soluções consultivas e construtivas?",
        "executou": "Investiga a origem da objeção, compreende preocupações, propõe alternativas viáveis e reforça valor.",
        "na": "Nenhuma objeção apresentada e nenhum risco relevante surgiu durante a reunião.",
    },
    # ── FECHAMENTO ───────────────────────────────────────────────────────
    {
        "id": "18", "block": FECHAMENTO,
        "criterio": "Definiu próximos passos claros, com prazos e responsáveis?",
        "executou": "Toda ação tem obrigatoriamente responsável definido, prazo acordado e objetivo claro.",
        "na": "Praticamente nunca — toda reunião deve gerar encaminhamentos ou alinhamento explícito de continuidade.",
    },
    {
        "id": "19", "block": FECHAMENTO,
        "criterio": "Validou com o cliente/parceiro se o plano proposto está alinhado?",
        "executou": "Confirma explicitamente concordância com o plano, ausência de objeções e alinhamento de expectativas.",
        "na": "",
    },
    {
        "id": "20", "block": FECHAMENTO,
        "criterio": "Apontou riscos e oportunidades identificados durante a conversa?",
        "executou": "Expõe claramente riscos (baixa adoção, falta de engajamento, dependência de stakeholders) e oportunidades, com impacto.",
        "na": "",
    },
    {
        "id": "21", "block": FECHAMENTO,
        "criterio": "Encerrou a call com alinhamento de expectativas e próximos marcos?",
        "executou": "Resume decisões, reforça próximos passos, confirma entendimento mútuo e explica os próximos marcos da jornada.",
        "na": "",
    },
    # ── CRITÉRIOS ESPECÍFICOS RDC (RD Conversas / WhatsApp) ──────────────
    # Todos N/A quando a call não trata de implantação RD Conversas (WhatsApp).
    {
        "id": "rdc_chip", "block": RDC,
        "criterio": "Reforçou a importância da ativação do chip?",
        "executou": "Explica que a ativação é requisito obrigatório para usar a API oficial do WhatsApp.",
        "na": "Call que não envolve implantação de RD Conversas (WhatsApp).",
    },
    {
        "id": "rdc_meta", "block": RDC,
        "criterio": "Reforçou a necessidade de seguir as diretrizes da Meta?",
        "executou": "Orienta sobre boas práticas, políticas da Meta, riscos reais de bloqueio e consequências do descumprimento.",
        "na": "Call que não envolve implantação de RD Conversas (WhatsApp).",
    },
    {
        "id": "rdc_template", "block": RDC,
        "criterio": "Garantiu que o chip foi ativado através do teste de envio do template?",
        "executou": "Valida a ativação por meio do teste prático de envio do template e confirma o pleno funcionamento.",
        "na": "Call que não envolve implantação de RD Conversas (WhatsApp).",
    },
]

_CRITERIA_BY_ID = {c["id"]: c for c in _CRITERIA}

# Escala oficial → peso para o score de aderência. N/A sai do denominador.
_WEIGHTS = {"executou": 1.0, "executou_parcialmente": 0.5, "nao_executou": 0.0}

# Classificação qualitativa (alinhada ao label validado pelo cliente):
# ruim < 0.5 ; regular [0.5, 0.75) ; boa >= 0.75
def _classify(score: float) -> str:
    if score >= 0.75:
        return "boa"
    if score >= 0.5:
        return "regular"
    return "ruim"


# Limiar para "seguiu o playbook no geral" == classificação "boa".
_FOLLOWED_THRESHOLD = 0.75


# ---------------------------------------------------------------------------
# Schema de saída (validado por linha)
# ---------------------------------------------------------------------------

class CriterionResult(BaseModel):
    criterion_id: str = Field(description="ID do critério, exatamente como na matriz (ex.: '1', '17', 'rdc_chip')")
    status: Literal["executou", "executou_parcialmente", "nao_executou", "na"] = Field(
        description="Nível na escala oficial de 4 pontos"
    )
    evidence: str = Field(description="Justificativa curta + trecho citado da transcrição (ou por que é N/A)")


class PlaybookAdherence(BaseModel):
    # Preenchido pelo LLM
    criteria: list[CriterionResult] = Field(description="Avaliação de TODOS os critérios da matriz")
    summary: str = Field(description="Síntese executiva da qualidade da call (2-4 frases, PT-BR)")
    strengths: list[str] = Field(default_factory=list, description="Pontos fortes observados")
    improvements: list[str] = Field(default_factory=list, description="Recomendações de melhoria priorizadas")

    # Calculado deterministicamente em post() — não confiar no LLM para números
    adherence_score: Optional[float] = Field(default=None, description="Aderência ponderada 0..1 (exclui N/A)")
    classificacao: Optional[str] = Field(default=None, description="boa / regular / ruim (alinhado ao label do cliente)")
    followed_playbook: Optional[bool] = Field(default=None, description="Aderência >= limiar (== 'boa')")
    n_executou: int = 0
    n_parcial: int = 0
    n_nao_executou: int = 0
    n_na: int = 0
    block_scores: dict[str, Optional[float]] = Field(default_factory=dict, description="Score por bloco da matriz")


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

def _render_matrix() -> str:
    """Renderiza a matriz de critérios para dentro do prompt."""
    lines: list[str] = []
    current_block = ""
    for c in _CRITERIA:
        if c["block"] != current_block:
            current_block = c["block"]
            lines.append(f"\n### {current_block}")
        line = f"- [{c['id']}] {c['criterio']}\n    Executou quando: {c['executou']}"
        if c["na"]:
            line += f"\n    N/A quando: {c['na']}"
        lines.append(line)
    return "\n".join(lines)


_MATRIX = _render_matrix()

# Few-shot de calibração (snippets reais dos labels validados). Ataca o viés de
# super-crédito: ensina a fronteira executou / parcialmente / nao_executou e que
# evidência vaga ou ausente NÃO é "executou".
_FEWSHOT = """\
Exemplos de calibração (note como evidência vaga ou ausente NÃO conta como executou):

Critério 1 (método ACE — Agradecer, Checar Tempo, Estabelecer Agenda):
- executou: "Obrigado pela disponibilidade, Paulo. Temos cerca de 15 minutos, fica bom? Minha proposta é falarmos sobre resultados, desafios e próximos passos." (agradeceu + checou tempo + propôs agenda — os 3 elementos)
- executou_parcialmente: "Oi Paulo, tudo bem? Temos uns 11 minutinhos hoje. Vamos começar?" (só checou tempo; sem agradecer e sem agenda)
- nao_executou: a abertura vai direto ao conteúdo, sem agradecer, sem checar tempo e sem propor agenda.

Critério 8 (resultados com dados):
- executou: "Trouxe os números: vocês aumentaram 36% as oportunidades e reduziram 36% o tempo de resposta." (indicadores concretos)
- executou_parcialmente: "No geral melhorou bastante o uso de vocês, tá indo bem." (afirma melhora, mas sem nenhum dado)
- nao_executou: não menciona nenhum resultado ou indicador.

Critério 18 (próximos passos com prazo e responsável):
- executou: "Ficou combinado: o time revisa a segmentação até sexta, e eu faço nova análise na call de 04/04." (ação + responsável + prazo)
- executou_parcialmente: "Então a gente ajusta umas coisas e se fala depois, beleza?" (ação vaga, sem responsável nem prazo)
- nao_executou: encerra sem definir nenhuma ação.

Base histórica (por critério, entre os aplicáveis): ~48% Executou, ~32% Executou Parcialmente, ~20% Não Executou.
Os três níveis são comuns. Não infle uma tentativa vaga para 'Executou', mas também não rebaixe um comportamento que claramente aconteceu — calibre pela base histórica."""

_RUBRIC = (
    "Escala oficial (use exatamente um destes valores em `status`):\n"
    "- executou: comportamento observado de forma COMPLETA e consistente — TODOS os elementos da definição "
    "'Executou quando' estão presentes na transcrição, com evidência explícita.\n"
    "- executou_parcialmente: observado, porém com profundidade insuficiente, execução incompleta ou sem "
    "consistência — falta ALGUM elemento da definição, ou foi feito de forma superficial.\n"
    "- nao_executou: comportamento não observado na reunião (nenhuma evidência clara na transcrição).\n"
    "- na: o critério não era relevante para o contexto (aplique SOMENTE conforme a regra 'N/A quando' do item).\n\n"
    "Regra de decisão (2 passos):\n"
    "PASSO 1 — N/A: primeiro verifique a regra 'N/A quando' do item. Se o contexto da call se encaixa nela, "
    "marque 'na' e PARE. N/A é uma decisão de RELEVÂNCIA do critério, não de qualidade — nunca rebaixe um "
    "critério relevante para 'na', nem force um 'na' legítimo para 'nao_executou'.\n"
    "PASSO 2 — se o critério é relevante, avalie a execução:\n"
    "• executou: os elementos PRINCIPAIS da definição aparecem na transcrição, ainda que com pequenas "
    "variações de forma. Não exija perfeição nem todas as palavras — exija o comportamento.\n"
    "• executou_parcialmente: houve uma tentativa real, mas claramente INCOMPLETA ou superficial — falta um "
    "elemento relevante, ou foi genérico/vago (ex.: 'melhorou bastante' sem dados; 'ajusta e se fala depois' "
    "sem responsável/prazo).\n"
    "• nao_executou: o comportamento NÃO aparece na transcrição — não há evidência dele. Este é o ponto mais "
    "importante: se o IC simplesmente não fez, marque 'nao_executou', não invente crédito parcial.\n"
    "• A regra de relevância (N/A) é independente da qualidade — nunca rebaixe um 'na' legítimo para "
    "'nao_executou' nem vice-versa."
)


class PlaybookAdherenceTransform(AITransform):
    # TODO(multi-cliente): com vários clientes, usar um slug de conector escopado
    # por cliente. Aqui = "bigquery" (o conector que traz o tl;dv da RD ao raw).
    connector = "bigquery"
    source = "delta_scan('/data/raw/bigquery/sandbox/transcription_tldv_synthetic_content')"
    target = "enrichment.rd_station__playbook_adherence"
    output_schema = PlaybookAdherence
    # Sonnet responde ao few-shot e quase elimina o falso "executou" em
    # comportamentos ausentes (o erro que esconde gap de coaching). gpt-4o ignora
    # o few-shot e fica leniente. Requer LLM_MODEL=claude-sonnet-4-6 no ambiente.
    model = "claude-sonnet-4-6"
    prompt_version = "v5"       # v5 = few-shot + fronteira executou/parcial calibrada (Sonnet)
    id_field = "id_meeting"     # PK da transcrição no raw
    max_concurrency = 10

    def prompt(self, row: dict[str, Any]) -> str:
        title = row.get("title") or row.get("meeting_title") or ""
        header = f"Reunião: {title}\n\n" if title else ""
        return (
            "Você é um avaliador sênior de qualidade do time de Customer Success da RD Station. "
            "Avalie a transcrição da reunião abaixo contra a Matriz de Critérios de Qualidade, "
            "atribuindo a cada critério um nível da escala oficial e citando evidência da transcrição.\n\n"
            "Regras importantes:\n"
            "1. Avalie SOMENTE com base no que está na transcrição. Não invente fatos.\n"
            "2. Seja rigoroso: 'executou' exige execução COMPLETA e consistente; na dúvida entre completo e "
            "incompleto, use 'executou_parcialmente'.\n"
            "3. Use 'na' apenas quando a regra 'N/A quando' do item se aplicar ao contexto da call.\n"
            "4. Retorne TODOS os critérios da matriz, usando exatamente o `criterion_id` indicado entre colchetes.\n"
            "5. Em `evidence`, cite um trecho curto da transcrição que sustente o status (ou explique o N/A).\n"
            "6. Escreva summary, strengths e improvements em português (PT-BR).\n\n"
            f"{_RUBRIC}\n\n"
            f"{_FEWSHOT}\n\n"
            f"MATRIZ DE CRITÉRIOS:{_MATRIX}\n\n"
            f"{header}"
            f"TRANSCRIÇÃO:\n{row['transcription']}"
        )

    def should_process(self, row: dict[str, Any]) -> bool:
        t = row.get("transcription") or ""
        return len(t) > 200  # pula calls curtas / sem conteúdo

    def post(self, result: PlaybookAdherence, row: dict[str, Any]) -> PlaybookAdherence:
        """Calcula scores deterministicamente a partir dos status do LLM."""
        # Contagens
        result.n_executou = sum(c.status == "executou" for c in result.criteria)
        result.n_parcial = sum(c.status == "executou_parcialmente" for c in result.criteria)
        result.n_nao_executou = sum(c.status == "nao_executou" for c in result.criteria)
        result.n_na = sum(c.status == "na" for c in result.criteria)

        # Score ponderado geral (exclui N/A)
        applicable = [c for c in result.criteria if c.status != "na"]
        if applicable:
            score = sum(_WEIGHTS.get(c.status, 0.0) for c in applicable) / len(applicable)
            result.adherence_score = round(score, 4)
            result.classificacao = _classify(score)
            result.followed_playbook = score >= _FOLLOWED_THRESHOLD
        else:
            result.adherence_score = None
            result.classificacao = None
            result.followed_playbook = None

        # Score por bloco (bloco derivado em código, não do LLM)
        by_block: dict[str, list[CriterionResult]] = defaultdict(list)
        for c in result.criteria:
            block = _CRITERIA_BY_ID.get(c.criterion_id, {}).get("block", "Outros")
            by_block[block].append(c)
        block_scores: dict[str, Optional[float]] = {}
        for block, items in by_block.items():
            appl = [c for c in items if c.status != "na"]
            block_scores[block] = (
                round(sum(_WEIGHTS.get(c.status, 0.0) for c in appl) / len(appl), 4) if appl else None
            )
        result.block_scores = block_scores
        return result
