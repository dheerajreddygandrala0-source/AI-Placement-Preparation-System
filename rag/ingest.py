from pathlib import Path
import re

import chromadb
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
CHROMA_DIR = BASE_DIR / "chroma_db"

COLLECTION_NAME = "placement_knowledge"


print("Loading embedding model...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path=str(CHROMA_DIR))

# Delete old collection so stale whole-document embeddings are not kept
try:
    client.delete_collection(name=COLLECTION_NAME)
    print("Old knowledge collection deleted.")
except Exception:
    pass

collection = client.get_or_create_collection(
    name=COLLECTION_NAME
)


def split_into_chunks(text: str, max_chars: int = 1200):
    """
    Split Markdown content mainly by headings.
    Large sections are further split into smaller chunks.
    """

    lines = text.splitlines()

    chunks = []
    current_section = ""
    current_content = []

    for line in lines:

        # Detect Markdown headings
        if re.match(r"^#{1,3}\s+", line):

            if current_content:
                section_text = "\n".join(current_content).strip()

                if section_text:
                    chunks.append({
                        "section": current_section,
                        "text": section_text
                    })

            current_section = line.strip()
            current_content = [line]

        else:
            current_content.append(line)

    # Add final section
    if current_content:
        section_text = "\n".join(current_content).strip()

        if section_text:
            chunks.append({
                "section": current_section,
                "text": section_text
            })

    # Split sections that are too large
    final_chunks = []

    for chunk in chunks:

        text_content = chunk["text"]

        if len(text_content) <= max_chars:
            final_chunks.append(chunk)
            continue

        # Further split large sections by paragraphs
        paragraphs = text_content.split("\n\n")

        current_text = ""

        for paragraph in paragraphs:

            paragraph = paragraph.strip()

            if not paragraph:
                continue

            if len(current_text) + len(paragraph) + 2 <= max_chars:
                current_text += paragraph + "\n\n"

            else:
                if current_text.strip():
                    final_chunks.append({
                        "section": chunk["section"],
                        "text": current_text.strip()
                    })

                current_text = paragraph + "\n\n"

        if current_text.strip():
            final_chunks.append({
                "section": chunk["section"],
                "text": current_text.strip()
            })

    return final_chunks


def load_documents():

    documents = []
    metadatas = []
    ids = []

    for file_path in KNOWLEDGE_BASE_DIR.rglob("*.md"):

        text = file_path.read_text(encoding="utf-8")

        if not text.strip():
            continue

        relative_path = file_path.relative_to(KNOWLEDGE_BASE_DIR)

        category = relative_path.parts[0]
        filename = file_path.stem

        chunks = split_into_chunks(text)

        for chunk_index, chunk in enumerate(chunks):

            documents.append(chunk["text"])

            metadatas.append({
                "category": category,
                "source": filename,
                "file": str(relative_path),
                "section": chunk["section"],
                "chunk_index": chunk_index
            })

            ids.append(
                f"{relative_path}::chunk_{chunk_index}"
            )

    return documents, metadatas, ids


def ingest_documents():

    documents, metadatas, ids = load_documents()

    print(f"Created {len(documents)} chunks.")

    if not documents:
        print("No documents found.")
        return

    print("Creating embeddings...")

    embeddings = embedding_model.encode(
        documents,
        show_progress_bar=True
    ).tolist()

    print("Adding chunks to ChromaDB...")

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print("\nKnowledge base ingestion completed!")
    print(f"Total chunks stored: {len(documents)}")


if __name__ == "__main__":
    ingest_documents()