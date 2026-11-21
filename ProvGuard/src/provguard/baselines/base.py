from __future__ import annotations

from abc import ABC, abstractmethod

from ..schemas import Action, Transcript


class Baseline(ABC):
    name: str

    @abstractmethod
    def allow(self, action: Action, transcript: Transcript) -> bool:
        raise NotImplementedError


class PromptTransform(ABC):
    name: str

    @abstractmethod
    def transform(self, transcript: Transcript) -> Transcript:
        raise NotImplementedError

