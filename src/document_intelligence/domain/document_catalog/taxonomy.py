DOCUMENT_TAXONOMY: tuple[str, ...] = (
    "architecture-doc",
    "runbook",
    "adr",
    "incident-review",
    "service-overview",
    "support-note",
)


def is_valid_document_label(label: str) -> bool:
    return label in DOCUMENT_TAXONOMY
