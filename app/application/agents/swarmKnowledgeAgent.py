from __future__ import annotations

import logging
from dataclasses import dataclass

from app.domain.ports import AgentHandlerPort
from app.modeling.prompts.swarm import composeSwarmGuideReply

logger = logging.getLogger(__name__)


@dataclass
class SwarmKnowledgeAgent(AgentHandlerPort):
    def handleMessage(self, message: str) -> str:
        logger.info("swarm guide agent composing implementation reply")
        return composeSwarmGuideReply(message)
