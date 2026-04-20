from app.services.vector_store_service import build_vector_store


def main() -> None:
    summary = build_vector_store()

    print("\nVector store build complete.")
    print("-" * 80)
    print(f"Collection: {summary['collection_name']}")
    print(f"Storage path: {summary['storage_path']}")
    print(f"Indexed documents: {summary['document_count']}")
    print(f"Indexed chunks: {summary['indexed_chunk_count']}")
    print(f"Indexed cards: {summary['indexed_card_count']}")


if __name__ == "__main__":
    main()