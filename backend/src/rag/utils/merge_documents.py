from pathlib import Path

logs_dir = Path("extraction_logs")

groups = {}

for md_file in logs_dir.glob("*.md"):
    base_name = md_file.name.split("_pages_")[0]

    groups.setdefault(base_name, []).append(md_file)

for doc_name, files in groups.items():
    files = sorted(files)

    merged_text = ""

    for file in files:
        merged_text += file.read_text(encoding="utf-8")
        merged_text += "\n\n"

    output_path = logs_dir / "merged_docs" / f"{doc_name}_complete.md"

    output_path.write_text(merged_text, encoding="utf-8")

    print(f"Created {output_path}")
