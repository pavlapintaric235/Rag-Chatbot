from app.services.source_service import get_source_status, load_source_manifest


def main() -> None:
    records = load_source_manifest()
    status_rows = get_source_status()

    print("\nLoaded source records:")
    print("-" * 80)

    for record in records:
        print(f"ID: {record.source_id}")
        print(f"Title: {record.title}")
        print(f"Work: {record.work}")
        print(f"Section: {record.section}")
        print(f"Themes: {', '.join(record.themes)}")
        print(f"Mode: {record.mode}")
        print(f"Tone: {record.tone}")
        print("-" * 80)

    print("\nFile status:")
    print("-" * 80)

    for row in status_rows:
        print(
            f"{row['source_id']}: "
            f"path={row['relative_path']} | "
            f"type={row['source_type']} | "
            f"exists={row['exists']}"
        )


if __name__ == "__main__":
    main()