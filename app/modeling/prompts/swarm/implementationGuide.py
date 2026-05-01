from __future__ import annotations

import re

from app.domain.conversationContextMarkers import FULL_CURRENT_USER_MESSAGE_LEADER

_SECTION_OVERVIEW = """\
**Visão geral do swarm**
Cada mensagem HTTP passa pelo caso de uso de mensagens: opcionalmente guardrails de entrada, roteador LLM (JSON com `route` e `rationale`), despacho para um agente ou resposta estática do roteador em modo degradado, opcionalmente guardrails de saída, persistência do turno (pedido, resposta, rota, `traceId`) e envelope com `status`, `reply`, `traceId`, e quando aplicável `route`, `routerModel`, `agentModel`, `replySource`.
Rotas implementadas: `knowledge` (conhecimento de produto e contexto recuperado), `support` (conta e ferramentas de sessão), `swarm` (este guia sobre o próprio sistema)."""

_SECTION_ROUTING = """\
**Roteamento**
O roteador é um modelo de chat configurável via ambiente (`ROUTER_MODEL`). Devolve JSON estrito: `route` ∈ {`knowledge`, `support`, `swarm`} e `rationale`. Se o JSON for inválido ou a rota for desconhecida, o sistema cai em modo degradado com rota `knowledge` e mensagem estática. O valor legado `fallback` no JSON é tratado como `knowledge`. Quando o roteador preenche `reply` (degradado), essa resposta é usada diretamente sem chamar agente."""

_SECTION_KNOWLEDGE = """\
**Agente de conhecimento (`knowledge`)**
- **Recuperação (RAG):** consulta vetorial à base (pgvector) com limite configurável de trechos e limiar de relevância; respostas devem fundamentar-se nos trechos (e opcionalmente em busca na web quando configurada).
- **Ingestão por URL:** se a intenção detectada for adicionar URL e houver link na mensagem, chama a ferramenta de ingestão (crawl, chunk, embed, armazenamento) e devolve confirmação com identificadores da execução.
- **Busca web (opcional):** quando o adaptador de busca está presente, pode haver fallback por relevância RAG insuficiente; há limiar mais alto de score RAG quando a web está ativa; o fluxo pode repetir busca se o formatador sinalizar contexto insuficiente.
- **Resposta:** pode incluir sufixo com fontes quando há URLs válidas nos trechos; não emite bloco de fontes só com placeholders vazios."""

_SECTION_SUPPORT = """\
**Agente de suporte (`support`)**
- **Contexto:** operações aplicam-se ao dono da conversa (`guest:<userId>` ou `google:<subject>` do token), injetado pelo servidor — o modelo não deve colocar chaves de proprietário nos payloads.
- **Entrada do modelo:** prompt de sistema + contrato JSON + bloco **PERFIL_ATUAL** (snapshot de nome exibido e `profile_metadata` lidos da persistência) quando esta existe.
- **Ferramentas (array `operations`):**
  - `noop`: sem alteração.
  - `profile_patch`: mescla `display_name` e/ou `profile_metadata` (objeto chave-valor); chaves desconhecidas extras no payload de perfil são ignoradas pelo executor conforme regras de sanitização.
  - `delete_turns`: `scope` = `all` | `by_trace_ids` | `by_turn_ids` com listas correspondentes; remove turnos apenas do dono atual.
- **Saída:** o executor aplica operações; a resposta ao utilizador inclui o texto do assistente e um bloco **confirmado** com o perfil após gravar, quando a persistência está ativa. Perfil vazio: o prompt obriga a orientar que dados podem ser enviados (nome + metadados) sem o utilizador pedir lista explícita."""

_SECTION_SWARM = """\
**Agente de conhecimento do swarm (`swarm`) — esta rota**
Responde apenas com informação alinhada à implementação atual: arquitetura lógica, roteamento, agentes, ferramentas, guardrails, identidade e API. Não substitui o agente de conhecimento sobre produtos InfinitePay nem o suporte operacional da conta."""

_SECTION_GUARDRAILS = """\
**Guardrails (opcional)**
Modo configurável por ambiente: pode estar desligado, em regras (bloqueio ou truncagem de entrada, bloqueio de saída por substrings) ou no-op. Avaliam a mensagem contextual (incluindo histórico do dia quando existir) e a resposta final; bloqueio de entrada fixa rota registrada como conhecimento com racional de guardrail."""

_SECTION_IDENTITY = """\
**Identidade e histórico**
- **Convidado:** chave de conversa `guest:<userId>` do corpo da API.
- **Google:** com token válido, chave `google:<subject>` e ligação a utilizador na persistência; exige verificador de token e base de sessão configurados.
- **Contexto do dia:** antes de rotear, podem ser carregados turnos do mesmo dono no dia (limite configurável) e antepostos ao pedido atual com marcador explícito da mensagem corrente.
- **Histórico via API:** pedido autenticado igual ao de mensagem permite listar turnos do dia (`POST` dedicado no mesmo padrão de identidade)."""

_SECTION_API = """\
**API relevante**
- `GET /health` — estado do serviço.
- `POST /messages` — corpo: `message`, `userId`, `googleIdToken` opcional; resposta: envelope com `reply`, `traceId`, `status`, campos opcionais de rota e modelos.
- `POST /messages/history` — mesmo critério de dono da conversa; devolve lista cronológica de turnos persistidos do dia."""

_BRIEF_INTRO = """\
Sou o guia interno deste assistente: explico como ele está montado (rotas, agentes, ferramentas), com base no que está implementado — não substituo respostas sobre produtos da InfinitePay nem operações na tua conta.

Em resumo: um roteador encaminha o pedido para **conhecimento** (RAG e, se existir, reforço na web), para **suporte** (perfil e histórico na sessão com ferramentas estruturadas) ou para **esta conversa** quando o assunto é o próprio sistema."""

_MENU_HINT = """\
Se quiseres ir ao ponto, pergunta por um destes temas — começo curto e aprofundo só se pedires detalhe técnico: **roteamento**, **agente de conhecimento** (RAG, URLs, web), **suporte** (perfil, apagar turnos), **guardrails**, **identidade** (convidado/Google, histórico) ou **API** (mensagens, histórico do dia)."""

_TEASERS: dict[str, str] = {
    "overview": (
        "Há três rotas principais: uma trata de informação de produto com recuperação de contexto; "
        "outra trata da tua sessão e dados guardados com ferramentas; "
        "esta rota explica o funcionamento do stack quando perguntas por ele."
    ),
    "routing": (
        "O roteador é um modelo que classifica cada mensagem e devolve uma rota em JSON. "
        "Se a classificação falhar, há um modo degradado com mensagem fixa, sem chamar os outros agentes."
    ),
    "knowledge": (
        "O agente de conhecimento procura trechos relevantes numa base vetorial, pode ingerir uma URL que indiques "
        "e, quando configurado, recorre à web se a recuperação local for fraca. "
        "A ideia é responder com base em fontes, não inventar factos."
    ),
    "support": (
        "O agente de suporte responde em JSON com operações que o servidor aplica só ao dono da conversa: "
        "por exemplo atualizar nome e metadados de perfil ou apagar turnos guardados, conforme o pedido."
    ),
    "swarm": (
        "A rota em que estás agora existe para perguntas sobre o próprio assistente — rotas, ferramentas e políticas — "
        "e não para dúvidas comerciais nem para alterar a tua conta."
    ),
    "guardrails": (
        "Opcionalmente, há filtros na entrada e na saída (regras ou truncagem), configuráveis por ambiente; "
        "se bloquearem a entrada, o turno fica registado como conhecimento com motivo de política."
    ),
    "identity": (
        "Identificas-te com um `userId` de convidado ou com token Google; isso define a chave da conversa e o que é carregado "
        "do histórico do dia antes de responder."
    ),
    "api": (
        "Há um endpoint de saúde, um para enviar mensagens com envelope de resposta e outro para listar turnos do dia, "
        "sempre com o mesmo critério de dono da conversa."
    ),
}

_TOPIC_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("routing", ("roteament", "rotead", "roteador", "classif", "despacho", "route")),
    ("knowledge", ("conheciment", "rag", "vetor", "embed", "ingest", "trecho", "recuper", "pgvector")),
    ("support", ("suporte", "perfil", "profile_patch", "delete_turns", "turno", "sessão", "sessao", "metadado")),
    ("swarm", ("esta rota", "este guia", "arquitetura do sis", "implement")),
    ("guardrails", ("guardrail", "política", "politica", "bloqueio", "trunc")),
    ("identity", ("google", "convidado", "guest", "histórico", "historico", "identidade")),
    ("api", ("api", "endpoint", "health", "envelope")),
)

_SECTION_ORDER = (
    "overview",
    "routing",
    "knowledge",
    "support",
    "swarm",
    "guardrails",
    "identity",
    "api",
)

_SECTIONS: dict[str, str] = {
    "overview": _SECTION_OVERVIEW,
    "routing": _SECTION_ROUTING,
    "knowledge": _SECTION_KNOWLEDGE,
    "support": _SECTION_SUPPORT,
    "swarm": _SECTION_SWARM,
    "guardrails": _SECTION_GUARDRAILS,
    "identity": _SECTION_IDENTITY,
    "api": _SECTION_API,
}

_MAX_REPLY_CHARS = 14_000
_MAX_FULL_SECTIONS = 5
_MAX_TEASER_TOPICS = 4

_DETAIL_HINTS = re.compile(
    r"\b(detalh|específic|especific|complet[oa]|técnico|tecnico|profund|"
    r"lista\s+completa|passo\s+a\s+passo|exatamente|mostre\s+tudo|"
    r"documenta(çc)?(ãa|a)o|especifica(çc)?(ãa|a)o|json|payload|schema|"
    r"tudo\s+sobre|explica(\s+em)?\s+detalhe)\b",
    re.IGNORECASE,
)

_GREETING_ONLY = re.compile(
    r"^(oi|ol[aá]|hey|hello|bom dia|boa tarde|boa noite|obrigad[oa]|valeu)[\s!?.,]*$",
    re.IGNORECASE,
)


def _currentUserSlice(contextualMessage: str) -> str:
    if FULL_CURRENT_USER_MESSAGE_LEADER in contextualMessage:
        return contextualMessage.split(FULL_CURRENT_USER_MESSAGE_LEADER)[-1].strip()
    return contextualMessage.strip()


def _mentionsThisSwarm(haystack: str) -> bool:
    if re.search(r"\bai[- ]?swarm\b", haystack):
        return True
    if re.search(r"\b(deste|desta|neste|nesta|este|esta)\s+swarm\b", haystack):
        return True
    if "multiagente" in haystack and re.search(r"\b(este|deste|neste)\b", haystack):
        return True
    return False


def _pickTopics(haystack: str) -> list[str]:
    picked: list[str] = []
    for topic, keywords in _TOPIC_KEYWORDS:
        if any(kw.casefold() in haystack for kw in keywords):
            picked.append(topic)
    if _mentionsThisSwarm(haystack) and "overview" not in picked:
        picked.insert(0, "overview")
    seen: set[str] = set()
    ordered: list[str] = []
    for t in _SECTION_ORDER:
        if t in picked and t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered


def composeSwarmGuideReply(contextualMessage: str) -> str:
    text = _currentUserSlice(contextualMessage)
    haystack = text.casefold()
    if not haystack:
        return f"{_BRIEF_INTRO}\n\n{_MENU_HINT}"

    if _GREETING_ONLY.match(text.strip()):
        return f"{_BRIEF_INTRO}\n\n{_MENU_HINT}"

    topics = _pickTopics(haystack)
    wants_detail = bool(_DETAIL_HINTS.search(text))

    if not topics:
        return f"{_BRIEF_INTRO}\n\n{_MENU_HINT}"

    if wants_detail:
        parts = [_SECTIONS[t] for t in topics[:_MAX_FULL_SECTIONS] if t in _SECTIONS]
        body = "\n\n".join(parts)
        if len(body) > _MAX_REPLY_CHARS:
            body = body[:_MAX_REPLY_CHARS].rstrip() + "\n\n[Podes pedir o restante por tema.] "
        return body

    teasers = [_TEASERS[t] for t in topics[:_MAX_TEASER_TOPICS] if t in _TEASERS]
    if not teasers:
        return f"{_BRIEF_INTRO}\n\n{_MENU_HINT}"

    bridge = (
        "Sobre o que perguntaste, em linhas gerais:"
        if len(teasers) > 1
        else "Sobre isso, em linhas gerais:"
    )
    blocks = [bridge, "\n\n".join(teasers), _MENU_HINT]
    if len(topics) > _MAX_TEASER_TOPICS:
        blocks.insert(
            -1,
            f"(Há mais {len(topics) - _MAX_TEASER_TOPICS} tema(s) relacionados — pergunta por um de cada vez ou pede **detalhe técnico**.)",
        )
    return f"{_BRIEF_INTRO}\n\n" + "\n\n".join(blocks)
