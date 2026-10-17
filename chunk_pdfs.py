
import os
import json
import fitz  # PyMuPDF

try:
    import tiktoken
    encoding = tiktoken.get_encoding("cl100k_base")
    def count_tokens(text):
        return len(encoding.encode(text))
    def tokens_to_text(tokens):
        return encoding.decode(tokens)
    def text_to_tokens(text):
        return encoding.encode(text)
except ImportError:
    print("tiktoken not installed — falling back to a word-based approximation.")
    print("For accurate token counts, run: pip install tiktoken --break-system-packages")
    encoding = None
    def text_to_tokens(text):
        return text.split()
    def tokens_to_text(tokens):
        return " ".join(tokens)

PDF_FOLDER = "docs/esg_reports"          # folder holding your downloaded PDFs
OUTPUT_FILE = "chunks.json"
CHUNK_SIZE = 500                # tokens per chunk
CHUNK_OVERLAP = 50              # tokens of overlap between consecutive chunks


def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF, page by page."""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    return full_text


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks of ~chunk_size tokens."""
    tokens = text_to_tokens(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunks.append(tokens_to_text(chunk_tokens))
        if end >= len(tokens):
            break
        start = end - overlap  # step forward, but overlap with previous chunk
    return chunks


def guess_metadata(filename):
    """
    Very simple metadata guess from the filename.
    Rename your PDFs like 'CompanyName_2024.pdf' for this to work well,
    or edit this function to hardcode company/industry per file later.
    """
    name = os.path.splitext(filename)[0]
    company = name.replace("_", " ").replace("-", " ")
    return {"company": company, "source_file": filename}


def main():
    if not os.path.isdir(PDF_FOLDER):
        raise SystemExit(
            f"Folder '{PDF_FOLDER}' not found. Put your PDFs there, or edit "
            f"PDF_FOLDER at the top of this script to match your folder name."
        )

    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith(".pdf")]
    if not pdf_files:
        raise SystemExit(f"No PDFs found in '{PDF_FOLDER}'.")

    print(f"Found {len(pdf_files)} PDF(s) in '{PDF_FOLDER}'.")

    all_chunks = []
    for filename in pdf_files:
        pdf_path = os.path.join(PDF_FOLDER, filename)
        print(f"Processing: {filename}")

        text = extract_text_from_pdf(pdf_path)
        if not text.strip():
            print(f"  Warning: no extractable text found in {filename} (might be scanned/image-only).")
            continue

        chunks = chunk_text(text)
        metadata = guess_metadata(filename)

        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "id": f"{os.path.splitext(filename)[0]}_chunk_{i}",
                "text": chunk,
                "metadata": {**metadata, "chunk_index": i},
            })

        print(f"  -> {len(chunks)} chunks created.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(all_chunks)} total chunks saved to '{OUTPUT_FILE}'.")


if __name__ == "__main__":
    main()