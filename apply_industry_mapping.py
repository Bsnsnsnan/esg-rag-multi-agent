"""
Applies your filled-in industry_mapping.csv back onto chunks.json,
updating each chunk's metadata with 'company' and 'industry'.

Reads:  chunks.json, industry_mapping.csv
Writes: chunks.json (overwritten in place, with industry/company added)

Run with: python apply_industry_mapping.py
"""
import json
import csv
import os

CHUNKS_FILE = "chunks.json"
MAPPING_FILE = "docs/industry_mapping.csv"


def main():
    for path in (CHUNKS_FILE, MAPPING_FILE):
        if not os.path.exists(path):
            raise SystemExit(f"'{path}' not found.")

    mapping = {}
    with open(MAPPING_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapping[row["source_file"]] = {
                "company": row["company"].strip(),
                "industry": row["industry"].strip(),
            }

    missing = [sf for sf, v in mapping.items() if not v["industry"]]
    if missing:
        print("Warning: these files still have no industry filled in:")
        for m in missing:
            print(f"  - {m}")
        print("They'll be updated with an empty industry field. Fill in the CSV and re-run if needed.\n")

    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    updated = 0
    for c in chunks:
        source_file = c["metadata"]["source_file"]
        if source_file in mapping:
            c["metadata"]["company"] = mapping[source_file]["company"]
            c["metadata"]["industry"] = mapping[source_file]["industry"]
            updated += 1

    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print(f"Updated {updated}/{len(chunks)} chunks with company + industry metadata.")
    print(f"'{CHUNKS_FILE}' saved. Now you can run embed_and_store.py.")


if __name__ == "__main__":
    main()