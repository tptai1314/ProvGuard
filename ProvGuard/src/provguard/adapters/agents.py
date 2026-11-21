"""Callback contracts for the four paper agents; concrete integrations remain external."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..schemas import Action, Transcript


class AgentCallbackAdapter(ABC):
    """Same-model, isolated, stateless callback required by paper Assumption 5."""

    agent_name: str

    @abstractmethod
    def decide(self, transcript: Transcript) -> Action:
        raise NotImplementedError

    @abstractmethod
    def identity(self) -> dict[str, str]:
        """Return pinned version/checkpoint/model digest metadata."""


class UnavailableExternalAgent(AgentCallbackAdapter):
    def decide(self, transcript: Transcript) -> Action:
        raise RuntimeError(
            f"{self.agent_name} is not installed. Provision its pinned repository and model on EC2."
        )

    def identity(self) -> dict[str, str]:
        return {"agent": self.agent_name, "status": "adapter_stub_waiting_for_external_dependency"}


class MobileAgentV3Adapter(UnavailableExternalAgent):
    agent_name = "Mobile-Agent-v3"


class DroidRunAdapter(UnavailableExternalAgent):
    agent_name = "DroidRun/Mobilerun"


class OpenAutoGLMAdapter(UnavailableExternalAgent):
    agent_name = "Open-AutoGLM"


class UITARSAdapter(UnavailableExternalAgent):
    agent_name = "UI-TARS"

