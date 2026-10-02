import os
import glob
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from google import genai
from google.genai import types

# Simple in-memory vector store for the Hackathon
# In production, use pgvector or ChromaDB
KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(__file__), "knowledge_base")
_documents = []
_embeddings = []

def init_rag():
    global _documents, _embeddings
    if _documents:
        return  # Already initialized

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("RAG init skipped: No API key found.")
        return

    client = genai.Client(api_key=api_key)
    
    # Read markdown files
    md_files = glob.glob(os.path.join(KNOWLEDGE_BASE_DIR, "*.md"))
    for file_path in md_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            chunks = [c.strip() for c in content.split("\n\n") if len(c.strip()) > 20]
            
            for chunk in chunks:
                _documents.append({
                    "source": os.path.basename(file_path),
                    "content": chunk
                })

    if not _documents:
        return

    # Generate embeddings with supported model
    try:
        texts = [doc["content"] for doc in _documents]
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=texts
        )
        _embeddings = response.embeddings
        print(f"RAG initialized with {len(_documents)} chunks using gemini-embedding-001.")
    except Exception as e:
        print(f"Failed to generate embeddings: {e}")

def cosine_similarity(vec1, vec2):
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = sum(a * a for a in vec1) ** 0.5
    norm_b = sum(b * b for b in vec2) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0
    return dot_product / (norm_a * norm_b)


def search_policy(query: str) -> str:
    """
    Search the Paytm internal knowledge base and policy documents for rules.
    Use this tool to look up thresholds, SLA rules, and escalation conditions.
    """
    if not _documents or not _embeddings:
        # Fallback to pure string matching if embeddings failed
        results = [doc["content"] for doc in _documents if query.lower() in doc["content"].lower()]
        return "\n---\n".join(results[:3]) if results else "No relevant policy found."

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=query
        )
        query_emb = response.embeddings[0].values

        # Score all documents
        scores = []
        for i, emb in enumerate(_embeddings):
            score = cosine_similarity(query_emb, emb.values)
            scores.append((score, _documents[i]))

        # Sort by highest score
        scores.sort(key=lambda x: x[0], reverse=True)
        
        # Return top 3 chunks
        top_chunks = [doc["content"] for score, doc in scores[:3] if score > 0.4]
        
        if not top_chunks:
            return "No highly relevant policy found in the knowledge base."
            
        return "RAG RETRIEVAL RESULTS:\n" + "\n---\n".join(top_chunks)
        
    except Exception as e:
        # Safe fallback: keyword search if embed call fails
        results = [doc["content"] for doc in _documents if any(w in doc["content"].lower() for w in query.lower().split())]
        return "\n---\n".join(results[:3]) if results else f"Error querying knowledge base: {str(e)}"
