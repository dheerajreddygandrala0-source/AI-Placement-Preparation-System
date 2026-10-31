from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


# Project paths
BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_db"


# Load the same embedding model used during ingestion
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


# Connect to the existing ChromaDB
client = chromadb.PersistentClient(path=str(CHROMA_DIR))

collection = client.get_collection(
    name="placement_knowledge"
)


def retrieve(query: str, top_k: int = 5):
    """
    Retrieve the most relevant knowledge-base documents
    for a given query.
    """

    query_embedding = embedding_model.encode(
        query
    ).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    retrieved = []

    for document, metadata in zip(documents, metadatas):
        retrieved.append({
            "document": document,
            "metadata": metadata
        })

    return retrieved


if __name__ == "__main__":

    query = input("\nEnter your query: ")

    results = retrieve(query)

    print("\n===== RETRIEVED KNOWLEDGE =====\n")

    for i, result in enumerate(results, start=1):

        print(f"--- Result {i} ---")

        print("Source:", result["metadata"]["file"])

        print(result["document"])

        print()