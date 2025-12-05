import faiss
import json
from sentence_transformers import SentenceTransformer
import re
import os
from typing import Tuple, List, Dict, Any

# ---------------------------
# GLOBAL SINGLETONS
# ---------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAISS_PATH = os.path.join(BASE_DIR, "..", "..", "database", "vector_store.faiss")
METADATA_PATH = os.path.join(BASE_DIR, "..", "..", "database", "metadata.json")

EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
FAISS_INDEX = faiss.read_index(FAISS_PATH) if os.path.exists(FAISS_PATH) else None

try:
    with open(METADATA_PATH, "r") as f:
        METADATA = json.load(f)
except Exception:
    METADATA = []

SIMILARITY_THRESHOLD = 0.45


# ---------------------------
# HELPERS
# ---------------------------
def semantic_search(query: str, k: int = 5) -> Tuple[List[float], List[int]]:
    """Return (distances, indices) arrays for a query using global EMBED_MODEL and FAISS_INDEX."""
    if not FAISS_INDEX:
        raise RuntimeError("FAISS index not available.")
    q_emb = EMBED_MODEL.encode([query])
    faiss.normalize_L2(q_emb)
    distances, indices = FAISS_INDEX.search(q_emb, k)
    return distances[0].tolist(), indices[0].tolist()


def top_matches_from_metadata(distances: List[float], indices: List[int], k: int = 5):
    """Return list of metadata entries that meet similarity threshold, preserving order."""
    results = []
    for dist, idx in zip(distances, indices):
        if idx is None or idx < 0 or idx >= len(METADATA):
            continue
        # FAISS returns inner product (cosine) if vectors normalized
        if dist >= SIMILARITY_THRESHOLD:
            results.append(METADATA[idx])
    return results


def safe_json_response(obj: Any) -> str:
    """Return compact JSON string for tool output (tools expect str)."""
    return json.dumps(obj, ensure_ascii=False)


def auto_notify_branch(customer_key: str, address: str, country: str) -> str:
    """
    Find responsible branch and notify it. Uses metadata.email if available.
    Returns email used or empty string.
    """
    from app.customer_api import notify_branch  # Import here to avoid circular
    from app.registry_api import get_postal_code
    try:
        postal_code = get_postal_code(address)
        # Prefer structured metadata with country/region/email fields
        query = f"{country} branch {postal_code}"
        distances, indices = semantic_search(query, k=3)
        hits = top_matches_from_metadata(distances, indices, k=3)

        # Prefer structured email field in metadata
        for h in hits:
            email = h.get("email") or extract_email(h.get("text", ""))
            if email:
                notify_branch(customer_key, email)
                return email

        # Fallback: attempt a broader search by country only
        distances, indices = semantic_search(f"{country} branch", k=5)
        hits = top_matches_from_metadata(distances, indices, k=5)
        for h in hits:
            email = h.get("email") or extract_email(h.get("text", ""))
            if email:
                notify_branch(customer_key, email)
                return email

        return ""
    except Exception:
        return ""


def extract_email(text: str) -> str:
    m = re.search(r'[\w\.-]+@[\w\.-]+', text or "")
    return m.group(0) if m else ""
