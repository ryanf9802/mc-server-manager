from __future__ import annotations


def create_slug(display_name: str) -> str:
    cleaned = display_name.strip().lower()
    if not cleaned:
        raise ValueError("Display name is required.")

    characters: list[str] = []
    last_was_dash = False
    for character in cleaned:
        if character.isalnum():
            characters.append(character)
            last_was_dash = False
            continue

        if not last_was_dash:
            characters.append("-")
            last_was_dash = True

    slug = "".join(characters).strip("-")
    return slug or "world"


def ensure_unique_slug(base_slug: str, existing_slugs: set[str]) -> str:
    if base_slug not in existing_slugs:
        return base_slug

    index = 2
    while f"{base_slug}-{index}" in existing_slugs:
        index += 1
    return f"{base_slug}-{index}"
