from app.services.cleaning_service import clean_all_extracted_documents


def main() -> None:
    saved_paths = clean_all_extracted_documents()

    print("\nCleaning complete.")
    print("-" * 80)

    for path in saved_paths:
        print(path)


if __name__ == "__main__":
    main()