from app.services.retrieval_prep_service import build_retrieval_corpus


def main() -> None:
    saved_path = build_retrieval_corpus()

    print("\nRetrieval corpus build complete.")
    print("-" * 80)
    print(saved_path)


if __name__ == "__main__":
    main()