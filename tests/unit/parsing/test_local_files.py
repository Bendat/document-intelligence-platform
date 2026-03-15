from pathlib import Path

import pytest

from document_intelligence.adapters.parsing.local_files import LocalFileSourceReader


@pytest.mark.parametrize(
    "source_path",
    [
        "C:/tmp/file.md",
        r"C:\tmp\file.md",
    ],
)
def test_resolve_path_accepts_windows_absolute_path(source_path: str) -> None:
    reader = LocalFileSourceReader()

    resolved = reader.resolve_path(source_path)

    assert isinstance(resolved, Path)
    assert "C:" in str(resolved)


def test_resolve_path_rejects_non_local_uri() -> None:
    reader = LocalFileSourceReader()

    with pytest.raises(ValueError, match="Only local file paths"):
        reader.resolve_path("https://example.com/file.md")
