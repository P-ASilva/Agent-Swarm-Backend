from __future__ import annotations

import json
import logging
from typing import Any, cast

from app.domain.models import SupportOperation, SupportOperationKind, SupportParsedOutput

logger = logging.getLogger(__name__)

_VALID_KINDS = frozenset({"noop", "profile_patch", "delete_turns"})


def parseSupportModelOutput(rawContent: str) -> SupportParsedOutput:
    try:
        payload: dict[str, Any] = json.loads(rawContent)
    except json.JSONDecodeError:
        logger.info("support output json parse failed")
        return SupportParsedOutput(
            assistantReply="Não consegui processar a resposta do modelo de suporte. Tente novamente.",
            operations=(),
        )

    if not isinstance(payload, dict):
        return SupportParsedOutput(
            assistantReply="Formato de saída inválido do suporte.",
            operations=(),
        )

    replyRaw = payload.get("assistant_reply")
    assistantReply = (
        replyRaw.strip() if isinstance(replyRaw, str) and replyRaw.strip() else "Processado."
    )

    opsRaw = payload.get("operations")
    if not isinstance(opsRaw, list):
        return SupportParsedOutput(assistantReply=assistantReply, operations=())

    operations: list[SupportOperation] = []
    for item in opsRaw:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        if not isinstance(kind, str) or kind.strip().lower() not in _VALID_KINDS:
            logger.info("support operation skipped unknown kind=%s", type(kind).__name__)
            continue
        normalizedKind = kind.strip().lower()
        pl = item.get("payload")
        if pl is None:
            pl = {}
        if not isinstance(pl, dict):
            logger.info("support operation skipped non-object payload kind=%s", normalizedKind)
            continue
        payloadCopy = _stripForbiddenProfileKeys(dict(pl))
        operations.append(
            SupportOperation(kind=cast(SupportOperationKind, normalizedKind), payload=payloadCopy),
        )

    return SupportParsedOutput(
        assistantReply=assistantReply,
        operations=tuple(operations),
    )


_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "conversation_owner_key",
        "user_id",
        "google_subject",
        "owner_key",
    },
)


def _stripForbiddenProfileKeys(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k not in _FORBIDDEN_PAYLOAD_KEYS}
