from app.services.card_service import build_all_cards


def main() -> None:
    saved_paths = build_all_cards()

    print("\nCard building complete.")
    print("-" * 80)

    for path in saved_paths:
        print(path)


if __name__ == "__main__":
    main()