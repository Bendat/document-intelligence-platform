import pytest

import document_intelligence.adapters.ai.openai_compatible as openai_compatible
from document_intelligence.adapters.ai import (
    OpenAICompatibleGenerationProvider,
    ProviderRequestError,
)


def test_generation_provider_returns_message_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post_json(**_: object) -> dict[str, object]:
        return {"choices": [{"message": {"content": "hello"}}]}

    monkeypatch.setattr(openai_compatible, "_post_json", fake_post_json)
    provider = OpenAICompatibleGenerationProvider(
        model_api_base_url="https://example.test/v1",
        model_name="test-model",
    )

    assert provider.generate("prompt") == "hello"


def test_generation_provider_raises_for_empty_choices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post_json(**_: object) -> dict[str, object]:
        return {"choices": []}

    monkeypatch.setattr(openai_compatible, "_post_json", fake_post_json)
    provider = OpenAICompatibleGenerationProvider(
        model_api_base_url="https://example.test/v1",
        model_name="test-model",
    )

    with pytest.raises(ProviderRequestError, match="did not contain message content"):
        provider.generate("prompt")
