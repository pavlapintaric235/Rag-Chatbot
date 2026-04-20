from app.services.ingestion_service import ingest_all_sources


def main() -> None:
    saved_paths = ingest_all_sources()

    print("\nIngestion complete.")
    print("-" * 80)

    for path in saved_paths:
        print(path)


if __name__ == "__main__":
    main()