from dataclasses import dataclass


@dataclass(slots=True)
class SemanticSearchQuery:
    query: str
    limit: int = 5


@dataclass(slots=True)
class AskQuestionQuery:
    question: str
    limit: int = 5
