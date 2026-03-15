from collections.abc import Sequence
from typing import Protocol


class EmbeddingProvider(Protocol):
    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


class GenerationProvider(Protocol):
    def generate(self, prompt: str) -> str: ...
