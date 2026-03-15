import json
import re
from collections.abc import Sequence


class DeterministicEmbeddingProvider:
    """Deterministic local fallback used for tests and offline development."""

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return [self._embed_text(text) for text in texts]

    def _embed_text(self, text: str) -> list[float]:
        normalized = text.lower()
        token_count = float(len(normalized.split()))
        char_count = float(len(normalized))
        digit_count = float(sum(character.isdigit() for character in normalized))
        alpha_count = float(sum(character.isalpha() for character in normalized))
        ascii_checksum = float(sum(ord(character) for character in normalized) % 1009)
        return [
            token_count,
            char_count,
            digit_count,
            alpha_count,
            ascii_checksum / 1009.0,
            (token_count + 1.0) / (char_count + 1.0),
        ]


class DeterministicGenerationProvider:
    """Rule-based fallback that emulates structured generation responses."""

    def generate(self, prompt: str) -> str:
        lowered = prompt.lower()
        source_text = _extract_document_text(prompt)

        if '{"label":"<taxonomy-label>","confidence":0.0}' in prompt:
            label = _classify_by_keyword(source_text.lower())
            return json.dumps({"label": label, "confidence": 0.58})

        if '{"summary":"<one concise paragraph>"}' in prompt:
            summary = _summarize(source_text)
            return json.dumps({"summary": summary})

        if "reply with exactly: ok" in lowered:
            return "OK"

        return json.dumps({"text": source_text[:160] or "No content"})


def _extract_document_text(prompt: str) -> str:
    marker_match = re.search(
        r"<<<DOCUMENT>>>\s*(.*?)\s*<<<END_DOCUMENT>>>",
        prompt,
        flags=re.DOTALL,
    )
    if marker_match is None:
        return prompt
    return marker_match.group(1).strip()


def _classify_by_keyword(source_text: str) -> str:
    if "adr" in source_text or "architecture decision record" in source_text:
        return "adr"
    if "incident" in source_text or "postmortem" in source_text:
        return "incident-review"
    if "runbook" in source_text or "recovery" in source_text:
        return "runbook"
    if "support" in source_text or "ticket" in source_text:
        return "support-note"
    if "architecture" in source_text:
        return "architecture-doc"
    if "service overview" in source_text or "service" in source_text:
        return "service-overview"
    return "service-overview"


def _summarize(source_text: str) -> str:
    compact = " ".join(source_text.split())
    if len(compact) <= 240:
        return compact
    return f"{compact[:237].rstrip()}..."
