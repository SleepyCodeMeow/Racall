"""Request-local citation labels keep models from having to reproduce hashes."""


def prepare_evidence(evidence: list[dict]) -> tuple[list[dict], dict[str, dict]]:
    originals = {item["id"]: item for item in evidence}
    references = {f"E{index}": item for index, item in enumerate(originals.values(), 1)}
    visible = [
        {"id": label, **{key: item[key] for key in ("title", "quote", "location", "url") if key in item}}
        for label, item in references.items()
    ]
    return visible, references
