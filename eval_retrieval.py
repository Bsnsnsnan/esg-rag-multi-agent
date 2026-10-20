
import os
import sys
import csv
from retrieve import retrieve

OUTPUT_FILE = "results/retrieval_eval.csv"
K = 5

# (query, company) pairs. Company names must match the metadata in ChromaDB exactly.
# Mix of E / S / G topics and different industries.
TEST_QUERIES = [
    ("Scope 1 and Scope 2 greenhouse gas emissions", "Apple"),
    ("Share of renewable electricity used in operations", "Microsoft"),
    ("Total water withdrawal and water consumption", "Coca Cola"),
    ("Waste generated and recycling rate", "Unilever"),
    ("Gender diversity of employees and women in management", "HSBC"),
    ("Workplace health and safety incident rates", "Toyota Motor Corporation"),
    ("Board independence and board composition", "Shell"),
    ("Anti-corruption and anti-bribery policy", "Samsung"),
    ("Climate-related risks and scenario analysis", "Nestle"),
    ("Net-zero target and decarbonisation timeline", "Amazon"),
]

FIELDS = ["query_id", "query", "company", "rank", "chunk_id",
          "distance", "text_preview", "relevant"]


def run():
    os.makedirs("results", exist_ok=True)
    if os.path.exists(OUTPUT_FILE):
        answer = input(f"'{OUTPUT_FILE}' already exists (it may contain your labels). Overwrite? [y/N] ")
        if answer.lower() != "y":
            print("Cancelled.")
            return

    rows = []
    for qid, (query, company) in enumerate(TEST_QUERIES, start=1):
        print(f"[{qid}/{len(TEST_QUERIES)}] {company}: {query}")
        results = retrieve(query, company=company, k=K)
        if not results:
            print(f"  WARNING: no results. Is '{company}' spelled exactly as in the metadata?")
        for rank, r in enumerate(results, start=1):
            rows.append({
                "query_id": qid,
                "query": query,
                "company": company,
                "rank": rank,
                "chunk_id": r["id"],
                "distance": round(r["distance"], 4),
                
                "text_preview": " ".join(r["text"].replace("\x00", "").split())[:400],
                "relevant": "",
            })

    # utf-8-sig so Excel opens special characters correctly
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} rows to '{OUTPUT_FILE}'.")
    print("Now open it, put 1 or 0 in the 'relevant' column for every row, save as CSV,")
    print("then run: python eval_retrieval.py score")


def score():
    if not os.path.exists(OUTPUT_FILE):
        raise SystemExit("No CSV found. Run 'python eval_retrieval.py run' first.")

    with open(OUTPUT_FILE, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    unlabeled = [r for r in rows if r["relevant"].strip() not in ("0", "1")]
    if unlabeled:
        print(f"{len(unlabeled)} rows are not labelled 0/1 yet, e.g. query {unlabeled[0]['query_id']} "
              f"rank {unlabeled[0]['rank']}. Finish labelling first.")
        return

    per_query = {}
    for r in rows:
        key = (int(r["query_id"]), r["company"], r["query"])
        per_query.setdefault(key, []).append(int(r["relevant"]))

    print(f"{'#':<3} {'Company':<12} {'P@5':<5} Query")
    precisions = []
    for (qid, company, query), labels in sorted(per_query.items()):
        p = sum(labels) / K
        precisions.append(p)
        print(f"{qid:<3} {company:<12} {p:<5.2f} {query}")

    mean_p = sum(precisions) / len(precisions)
    print(f"\nMean precision@{K} over {len(precisions)} queries: {mean_p:.2f}")

    with open("results/retrieval_eval_summary.txt", "w") as f:
        f.write(f"Mean precision@{K}: {mean_p:.2f}\n")
        for (qid, company, query), labels in sorted(per_query.items()):
            f.write(f"Q{qid} {company} | {query} | P@5 = {sum(labels)/K:.2f}\n")
    print("Summary saved to results/retrieval_eval_summary.txt")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "run":
        run()
    elif mode == "score":
        score()
    else:
        print("Usage: python eval_retrieval.py run   |   python eval_retrieval.py score")