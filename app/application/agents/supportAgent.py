from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.application.support_execution_context import supportConversationOwnerKeyContext
from app.application.support_operations_executor import SupportOperationsExecutor
from app.domain.models import ConversationProfileSnapshot
from app.domain.ports import AgentHandlerPort, OpenAiChatPort
from app.modeling.prompts.support import (
    SUPPORT_OUTPUT_CONTRACT,
    SUPPORT_SYSTEM_PROMPT,
    parseSupportModelOutput,
)

logger = logging.getLogger(__name__)

_PROFILE_DISCLOSURE_MAX_METADATA_CHARS = 4000


def _profileSystemBlock(snapshot: ConversationProfileSnapshot) -> str:
    body = json.dumps(
        {
            "display_name": snapshot.displayName,
            "profile_metadata": snapshot.metadata,
        },
        ensure_ascii=False,
    )
    return (
        "PERFIL_ATUAL (fonte: base de sessão; use estes valores para responder a perguntas sobre dados guardados):\n"
        f"{body}\n"
        "Se o usuário pedir para ver dados, cite estes campos. "
        "Para alterar, emita profile_patch; o servidor anexará o estado confirmado após a resposta."
    )


def _formatProfileDisclosure(snapshot: ConversationProfileSnapshot) -> str:
    lines = [
        "",
        "——",
        "**Dados confirmados no seu perfil (nesta conversa):**",
    ]
    if snapshot.displayName:
        lines.append(f"- Nome exibido: {snapshot.displayName}")
    else:
        lines.append("- Nome exibido: (não definido)")
    if snapshot.metadata:
        raw = json.dumps(snapshot.metadata, ensure_ascii=False, indent=2)
        if len(raw) > _PROFILE_DISCLOSURE_MAX_METADATA_CHARS:
            raw = raw[:_PROFILE_DISCLOSURE_MAX_METADATA_CHARS].rstrip() + "…"
        lines.append("- Metadados:")
        lines.extend(f"  {ln}" for ln in raw.splitlines())
    else:
        lines.append("- Metadados: (vazio)")
    return "\n".join(lines)


@dataclass
class SupportAgent(AgentHandlerPort):
    openAiChat: OpenAiChatPort
    executor: SupportOperationsExecutor
    supportModel: str = "gpt-4o-mini"

    def handleMessage(self, message: str) -> str:
        ownerKey = supportConversationOwnerKeyContext.get()
        if not ownerKey:
            logger.info("support agent missing conversation owner context")
            return (
                "Não foi possível aplicar operações de suporte (contexto de conversação ausente)."
            )

        persistence = self.executor.userMessagePersistence
        profile_for_prompt: ConversationProfileSnapshot | None = None
        if persistence is not None:
            try:
                profile_for_prompt = persistence.getConversationProfile(
                    conversationOwnerKey=ownerKey,
                )
            except Exception as exc:
                logger.info("support profile preload failed error=%s", type(exc).__name__)
                profile_for_prompt = None

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SUPPORT_SYSTEM_PROMPT},
            {"role": "system", "content": SUPPORT_OUTPUT_CONTRACT},
        ]
        if profile_for_prompt is not None:
            messages.append({"role": "system", "content": _profileSystemBlock(profile_for_prompt)})
        messages.append({"role": "user", "content": message})

        logger.info("support model=%s", self.supportModel)
        try:
            raw = self.openAiChat.chatCompletion(
                messages=messages,
                model=self.supportModel,
                temperature=0.1,
                responseFormat={"type": "json_object"},
            )
        except Exception as exc:
            logger.info("support llm call failed error=%s", type(exc).__name__)
            return (
                "Serviço de suporte indisponível no momento. Tente novamente em instantes."
            )

        parsed = parseSupportModelOutput(raw)
        self.executor.run(conversationOwnerKey=ownerKey, operations=parsed.operations)
        logger.info(
            "support operations dispatched parsedCount=%s",
            len(parsed.operations),
        )
        reply = parsed.assistantReply
        if persistence is not None:
            try:
                profile_after = persistence.getConversationProfile(
                    conversationOwnerKey=ownerKey,
                )
                reply = reply + _formatProfileDisclosure(profile_after)
            except Exception as exc:
                logger.info("support profile disclosure skipped error=%s", type(exc).__name__)
        return reply
