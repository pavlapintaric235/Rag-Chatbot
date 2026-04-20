from app.services.chunking_service import build_all_chunks


def main() -> None:
    saved_paths = build_all_chunks()

    print("\nChunk building complete.")
    print("-" * 80)

    for path in saved_paths:
        print(path)


if __name__ == "__main__":
    main()