from app.services.vector_index_service import build_vector_index


def main() -> None:
    result = build_vector_index()

    print("\nVector index build complete.")
    print("-" * 80)
    print(f"Item count: {result['item_count']}")
    print(result["vectorizer_path"])
    print(result["matrix_path"])
    print(result["metadata_path"])


if __name__ == "__main__":
    main()