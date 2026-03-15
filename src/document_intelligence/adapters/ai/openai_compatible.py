import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


class ProviderRequestError(Exception):
    """Raised when an OpenAI-compatible provider request fails."""


@dataclass(slots=True)
class OpenAICompatibleGenerationProvider:
    model_api_base_url: str
    model_name: str
    timeout_seconds: float = 120.0
    extra_headers: Mapping[str, str] | None = None

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
        }
        body = _post_json(
            base_url=self.model_api_base_url,
            path="/chat/completions",
            payload=payload,
            timeout_seconds=self.timeout_seconds,
            extra_headers=self.extra_headers,
        )

        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderRequestError(
                "OpenAI-compatible generation response did not contain message content."
            )
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise ProviderRequestError(
                "OpenAI-compatible generation response did not contain message content."
            )
        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise ProviderRequestError(
                "OpenAI-compatible generation response did not contain message content."
            )
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ProviderRequestError(
                "OpenAI-compatible generation response did not contain message content."
            )
        return content


@dataclass(slots=True)
class OpenAICompatibleEmbeddingProvider:
    model_api_base_url: str
    model_name: str
    timeout_seconds: float = 120.0
    extra_headers: Mapping[str, str] | None = None

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        payload = {
            "model": self.model_name,
            "input": list(texts),
        }
        body = _post_json(
            base_url=self.model_api_base_url,
            path="/embeddings",
            payload=payload,
            timeout_seconds=self.timeout_seconds,
            extra_headers=self.extra_headers,
        )

        data = body.get("data")
        if not isinstance(data, list):
            raise ProviderRequestError(
                "OpenAI-compatible embedding response did not contain a data array."
            )

        vectors: list[list[float]] = []
        for item in data:
            if not isinstance(item, dict):
                raise ProviderRequestError(
                    "OpenAI-compatible embedding response contained non-object item."
                )
            embedding = item.get("embedding")
            if not isinstance(embedding, list):
                raise ProviderRequestError(
                    "OpenAI-compatible embedding response contained missing vector."
                )
            vectors.append([float(value) for value in embedding])

        if len(vectors) != len(texts):
            raise ProviderRequestError(
                "OpenAI-compatible embedding response vector count mismatch."
            )
        return vectors


def _post_json(
    *,
    base_url: str,
    path: str,
    payload: dict[str, Any],
    timeout_seconds: float,
    extra_headers: Mapping[str, str] | None,
) -> dict[str, Any]:
    url = urljoin(_normalize_base_url(base_url), path.lstrip("/"))
    encoded_payload = json.dumps(payload).encode("utf-8")
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if extra_headers is not None:
        headers.update(extra_headers)

    request = Request(
        url=url,
        data=encoded_payload,
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise ProviderRequestError(
            f"Provider request failed with HTTP {error.code}: {detail}"
        ) from error
    except URLError as error:
        raise ProviderRequestError(
            f"Provider request failed: {error.reason}"
        ) from error
    except TimeoutError as error:
        raise ProviderRequestError("Provider request timed out.") from error

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ProviderRequestError("Provider response was not valid JSON.") from error

    if not isinstance(parsed, dict):
        raise ProviderRequestError("Provider response root must be a JSON object.")
    return parsed


def _normalize_base_url(base_url: str) -> str:
    normalized = base_url.strip()
    if not normalized:
        raise ProviderRequestError("MODEL_API_BASE_URL is empty.")
    if not normalized.endswith("/"):
        return f"{normalized}/"
    return normalized
