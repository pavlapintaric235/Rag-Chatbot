import json
from pathlib import Path

from app.core.config import settings
from app.models.card import InterpretationCard, InterpretationCardSeed


def load_card_seed_manifest() -> list[InterpretationCardSeed]:
    """
    Load and validate the card seed manifest.
    """
    manifest_path = settings.cards_seed_manifest_path

    if not manifest_path.exists():
        raise FileNotFoundError(f"Card seed manifest not found: {manifest_path}")

    raw_data = json.loads(manifest_path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, list):
        raise ValueError("Card seed manifest must contain a list of card objects.")

    return [InterpretationCardSeed.model_validate(item) for item in raw_data]


def build_card_text(seed: InterpretationCardSeed) -> str:
    """
    Turn the structured card seed into a single retrieval-friendly text block.
    """
    user_patterns = ", ".join(seed.user_patterns) if seed.user_patterns else "N/A"
    references = ", ".join(seed.primary_references) if seed.primary_references else "N/A"
    source_ids = ", ".join(seed.source_ids) if seed.source_ids else "N/A"
    tags = ", ".join(seed.tags) if seed.tags else "N/A"

    return (
        f"Theme: {seed.theme}\n"
        f"User example: {seed.user_message_example}\n"
        f"User patterns: {user_patterns}\n"
        f"Nietzschean angle: {seed.nietzschean_angle}\n"
        f"Plain explanation: {seed.plain_explanation}\n"
        f"Sharp reply style: {seed.sharp_reply_style}\n"
        f"Primary references: {references}\n"
        f"Source IDs: {source_ids}\n"
        f"Tags: {tags}"
    ).strip()


def build_interpretation_card(seed: InterpretationCardSeed) -> InterpretationCard:
    """
    Convert one card seed into a saved interpretation card.
    """
    return InterpretationCard(
        card_id=seed.card_id,
        theme=seed.theme,
        user_message_example=seed.user_message_example,
        user_patterns=seed.user_patterns,
        nietzschean_angle=seed.nietzschean_angle,
        plain_explanation=seed.plain_explanation,
        sharp_reply_style=seed.sharp_reply_style,
        primary_references=seed.primary_references,
        source_ids=seed.source_ids,
        tags=seed.tags,
        card_text=build_card_text(seed),
    )


def _card_output_path(card_id: str) -> Path:
    """
    Build the output path for a saved card.
    """
    return settings.cards_dir / f"{card_id}.json"


def save_interpretation_card(card: InterpretationCard) -> Path:
    """
    Save one interpretation card as JSON.
    """
    settings.cards_dir.mkdir(parents=True, exist_ok=True)
    output_path = _card_output_path(card.card_id)

    output_path.write_text(
        json.dumps(card.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def build_all_cards() -> list[Path]:
    """
    Build and save all interpretation cards from the seed manifest.
    """
    seeds = load_card_seed_manifest()
    saved_paths: list[Path] = []

    for seed in seeds:
        card = build_interpretation_card(seed)
        output_path = save_interpretation_card(card)
        saved_paths.append(output_path)

    return saved_paths