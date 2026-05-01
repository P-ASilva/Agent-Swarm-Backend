from __future__ import annotations

import re

from app.domain.conversationContextMarkers import FULL_CURRENT_USER_MESSAGE_LEADER

_SECTION_OVERVIEW = """\
Imagina um desenho em caixas: do lado do utilizador entra um pedido; antes de tudo pode passar por um filtro de segurança (opcional). Depois há uma caixa “decisor” que olha para a mensagem e escolhe um caminho: perguntas de produto e contexto, ajuda com a tua sessão e dados, ou esta conversa sobre o próprio assistente. A seguir, o caminho escolhido leva a um bloco que produz a resposta; outro filtro opcional revê a resposta; no fim o sistema regista o que aconteceu e devolve a resposta ao cliente. São três saídas principais desse decisor: conhecimento de produto, suporte à conta e esta rota de autoexplicação."""

_SECTION_ROUTING = """\
O decisor é, na prática, um modelo que classifica o pedido e diz qual dos três caminhos deve abrir. A aplicação espera uma resposta num formato bem definido para saber para onde encaminhar; se isso correr mal, há um plano B: uma resposta fixa e segura, sem passar pelos blocos normais. Em situações de rutura o sistema pode também devolver texto já preparado pelo próprio decisor, sem chamar o bloco seguinte."""

_SECTION_KNOWLEDGE = """\
O caminho de conhecimento liga-se a uma memória de textos (material de apoio) e tenta responder com base no que encontrou lá, em vez de inventar. Se pedires para acrescentar uma página por link, há um pipeline que trata disso por ti. Por vezes, se estiver ligado, pode ainda ir buscar informação complementar fora dessa memória. Quando faz sentido, a resposta pode indicar de onde veio a informação."""

_SECTION_SUPPORT = """\
O caminho de suporte trata do que é teu nesta conversa: quem és (convidado ou com sessão Google), o que já ficou guardado e pedidos como atualizar dados visíveis ou limpar histórico. O modelo combina uma resposta em linguagem natural com “pedidos de ação” que o servidor executa só para ti — por exemplo ajustar nome ou metadados do perfil, ou apagar mensagens guardadas conforme o âmbito que definires. O servidor aplica; o utilizador não manda chaves internas de identidade nos pedidos."""

_SECTION_SWARM = """\
Esta terceira saída sou eu a explicar o desenho do sistema: caixas, fluxos e regras gerais. Não substituo respostas sobre produtos da InfinitePay nem faço alterações na tua conta; para isso existem os outros dois caminhos."""

_SECTION_GUARDRAILS = """\
Os filtros de segurança são uma camada opcional por cima do fluxo: podem estar desligados, ativos com regras simples ou neutros. Olham para o que chega e para o que sai; se bloquearem à entrada, o episódio fica registado de forma especial para auditoria. Podem usar o histórico recente da conversa quando existe."""

_SECTION_IDENTITY = """\
Quem és determina a “gaveta” da conversa: convidado com identificador próprio, ou utilizador Google quando o token é válido e a sessão está configurada. O sistema pode carregar o que já foi dito hoje na mesma gaveta antes de decidir o caminho. Há também uma forma de listar, pelo mesmo critério de dono, o que ficou guardado no dia."""

_SECTION_API = """\
Por fora há três portas simples: uma para ver se o serviço está de pé, outra para enviar a mensagem e receber a resposta completa, e outra para pedir o histórico do dia para quem é dono daquela conversa. O critério de “dono” é o mesmo nas duas últimas."""

_SHORT_INTRO = """\
Sou o guia deste assistente: explico o desenho geral — como as peças se ligam — sem entrar em produtos InfinitePay nem em operações na tua conta.

Numa imagem rápida: o teu pedido entra, um roteador interno escolhe um de três caminhos (conhecimento de produto, suporte à sessão, ou falar comigo sobre o próprio sistema), e no fim recebes a resposta já revista e registada."""

_MENU_HINT = """\
Se quiseres ir por partes, diz o tema (encaminhamento, conhecimento, suporte, filtros de segurança, identidade, portas da API). Para a versão mais explícita com nomes técnicos e contratos, pede “detalhe técnico” ou “aprofundar”."""

_SUMMARY_TAIL = """\
Se precisares da versão mais explícita (nomes de campos, formatos, configuração), diz que queres detalhe técnico ou pergunta só por um tema."""

_COMPACT: dict[str, str] = {
    "overview": (
        "O fluxo é: entrada → filtro opcional → decisor que abre um de três caminhos (produto, sessão ou este guia) → "
        "resposta → filtro opcional → registo e resposta ao cliente. Três saídas principais do decisor."
    ),
    "routing": (
        "O roteador classifica o pedido e indica qual dos três caminhos seguir; a aplicação lê essa decisão num formato "
        "fixo. Se algo falhar, há resposta de recurso sem passar pelos blocos normais."
    ),
    "knowledge": (
        "Liga à memória de apoio, responde com base no que encontrou, pode ingerir um link que indiques e, se existir, "
        "reforçar com fontes externas. Pode citar origens quando faz sentido."
    ),
    "support": (
        "Cuida da tua sessão: o modelo responde e pede ações que o servidor aplica só para ti — perfil, metadados, "
        "apagar histórico guardado por âmbitos. O servidor impõe o dono da conversa."
    ),
    "swarm": (
        "Este caminho explica o desenho do sistema. Não é produto InfinitePay nem alterações na conta."
    ),
    "guardrails": (
        "Camada opcional antes e depois: regras ou truncagem, pode usar o histórico do dia. Entrada bloqueada fica "
        "marcada de forma especial."
    ),
    "identity": (
        "Convidado ou Google definem a gaveta da conversa; pode juntar-se o histórico de hoje antes de decidir. "
        "Há pedido para listar o dia com o mesmo critério de dono."
    ),
    "api": (
        "Três contactos: saúde do serviço, enviar mensagem com resposta completa, listar histórico do dia para o mesmo dono."
    ),
}

_TEASERS: dict[str, str] = {
    "overview": (
        "Três grandes ramos depois do decisor: produto com memória de apoio, sessão e dados teus, "
        "e este guia sobre o próprio desenho."
    ),
    "routing": (
        "O decisor encaixa cada pedido num dos caminhos; se a leitura falhar, o sistema responde por um atalho seguro."
    ),
    "knowledge": (
        "Usa material guardado para fundamentar a resposta, pode absorver um link novo e, por vezes, reforçar com fonte externa."
    ),
    "support": (
        "Mistura resposta em texto com pedidos que o servidor executa só para o dono da conversa — perfil, metadados, limpar histórico."
    ),
    "swarm": (
        "O ramo em que estás serve para entender o diagrama; não vende produto nem mexe na tua conta."
    ),
    "guardrails": (
        "Filtros opcionais na ida e na volta; se barrarem à entrada, fica rasto para revisão."
    ),
    "identity": (
        "Convidado ou Google definem a tua “gaveta”; o dia pode ser relembrado antes de decidir o caminho."
    ),
    "api": (
        "Três contactos: saúde, mensagem com resposta, histórico do dia — sempre com o mesmo dono de conversa."
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
_MAX_SUMMARY_TOPICS = 5

_DETAIL_HINTS = re.compile(
    r"\b(detalh|específic|especific|complet[oa]|técnico|tecnico|profund|aprofund|"
    r"elabore|elabora|expand\w*|mais\s+sobre|lista\s+completa|passo\s+a\s+passo|exatamente|mostre\s+tudo|"
    r"documenta(çc)?(ãa|a)o|especifica(çc)?(ãa|a)o|tudo\s+sobre|explica(\s+em)?\s+detalhe)\b",
    re.IGNORECASE,
)

_FOCUSED_QUESTION = re.compile(
    r"[?]|\A.{1,220}\Z|"
    r"\b(qual|quais|o\s+que|como|quando|onde|por\s+que|porquê|explic\w*|diz\w*|mostr\w*|"
    r"defin\w*|descrev\w*|o\s+que\s+é|funcion\w*|devolv\w+|retorn\w+)\b",
    re.IGNORECASE | re.DOTALL,
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


def _wantsTechnicalDetail(text: str) -> bool:
    return bool(_DETAIL_HINTS.search(text))


def _isFocusedQuestion(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    return bool(_FOCUSED_QUESTION.search(stripped))


def _firstSummarySentence(compact: str) -> str:
    parts = compact.split(". ", maxsplit=1)
    if len(parts) == 1:
        return compact if compact.endswith(".") else f"{compact}."
    return f"{parts[0]}."


def _composeSummary(topics: list[str]) -> str:
    lines: list[str] = []
    for t in topics[:_MAX_SUMMARY_TOPICS]:
        body = _COMPACT.get(t) or _TEASERS.get(t, "")
        if body:
            lines.append(_firstSummarySentence(body))
    if not lines:
        return f"{_SHORT_INTRO}\n\n{_MENU_HINT}"
    extra = ""
    if len(topics) > _MAX_SUMMARY_TOPICS:
        extra = f"\n(Há mais {len(topics) - _MAX_SUMMARY_TOPICS} tema(s) — pergunta por um ou pede detalhe técnico.)"
    bullets = "\n".join(f"• {line}" for line in lines)
    return f"Resumo:\n{bullets}\n\n{_SUMMARY_TAIL}{extra}"


def _composeFullSections(topics: list[str]) -> str:
    parts = [_SECTIONS[t] for t in topics[:_MAX_FULL_SECTIONS] if t in _SECTIONS]
    body = "\n\n".join(parts)
    if len(body) > _MAX_REPLY_CHARS:
        body = body[:_MAX_REPLY_CHARS].rstrip() + "\n\n[Podes pedir o restante por tema.]"
    return body


def composeSwarmGuideReply(contextualMessage: str) -> str:
    text = _currentUserSlice(contextualMessage)
    haystack = text.casefold()
    if not haystack:
        return f"{_SHORT_INTRO}\n\n{_MENU_HINT}"

    if _GREETING_ONLY.match(text.strip()):
        return f"{_SHORT_INTRO}\n\n{_MENU_HINT}"

    topics = _pickTopics(haystack)
    wants_detail = _wantsTechnicalDetail(text)

    if not topics:
        return f"{_SHORT_INTRO}\n\n{_MENU_HINT}"

    if wants_detail:
        return _composeFullSections(topics)

    if len(topics) == 1 and _isFocusedQuestion(text):
        topic = topics[0]
        block = _COMPACT.get(topic) or _TEASERS.get(topic, "")
        if not block:
            return f"{_SHORT_INTRO}\n\n{_MENU_HINT}"
        return f"{block}\n\n{_SUMMARY_TAIL}"

    return _composeSummary(topics)
