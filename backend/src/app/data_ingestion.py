import os
import re
import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss
import json


# ---------------------------------------------------------
# TEXT CLEANING
# ---------------------------------------------------------
def clean_text(text: str) -> str:
    # Remove standalone page numbers
    text = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", text)

    # Normalize whitespace
    text = text.replace("\xa0", " ")

    # Remove all lines that contain only whitespace
    text = re.sub(r"(?m)^\s*$", "", text)

    # Collapse 2+ newlines into 1 newline
    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip()


# ---------------------------------------------------------
# PDF TEXT EXTRACTION (PyMuPDF)
# ---------------------------------------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    blocks_text = []

    for page in doc:
        blocks = page.get_text("blocks")
        for block in blocks:
            block_text = block[4].strip()
            if block_text:
                blocks_text.append(block_text)

    raw_text = "\n".join(blocks_text)
    return clean_text(raw_text)


# ---------------------------------------------------------
# DOCUMENT LOADING
# ---------------------------------------------------------
def load_documents() -> list:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    docs_path = os.path.abspath(os.path.join(BASE_DIR, "../../../docs/appendices"))

    documents = [
        {"source": "country_requirements", "file": os.path.join(docs_path, "appendix1.pdf")},
        {"source": "branch_mappings", "file": os.path.join(docs_path, "appendix2.pdf")},
    ]

    loaded_docs = []
    for doc in documents:
        if os.path.exists(doc["file"]):
            text = extract_text_from_pdf(doc["file"])
            loaded_docs.append({"source": doc["source"], "text": text})
    return loaded_docs


# ---------------------------------------------------------
# CHUNKING
# ---------------------------------------------------------

def chunk_structured_document(text: str, source: str) -> list:
    """Smart chunking for appendices"""
    
    if source == "country_requirements":
        # Split by country names (case-insensitive, handles mid-text)
        chunks = []
        pattern = r'(Denmark:|Sweden:|Norway|Finland)'
        sections = re.split(pattern, text, flags=re.IGNORECASE)
        
        # Recombine: sections[0]=header, then pairs of (country_name, content)
        if sections[0].strip():
            chunks.append(sections[0].strip())  # Header
        
        for i in range(1, len(sections), 2):
            if i+1 < len(sections):
                country = sections[i]
                content = sections[i+1]
                chunks.append(f"{country}\n{content}".strip())
        
        return chunks
    
    elif source == "branch_mappings":
        # Same fix
        chunks = []
        pattern = r'(Denmark:|Sweden:|Norway:|Finland:)'
        sections = re.split(pattern, text, flags=re.IGNORECASE)
        
        if sections[0].strip():
            chunks.append(sections[0].strip())
        
        for i in range(1, len(sections), 2):
            if i+1 < len(sections):
                chunks.append(f"{sections[i]}\n{sections[i+1]}".strip())
        
        return chunks
    
    else:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100
        )
        return splitter.split_text(text)

def chunk_all_documents(documents):
    all_chunks = []
    chunk_sources = []
    
    for doc in documents:
        doc_chunks = chunk_structured_document(doc["text"], doc["source"])
        for ch in doc_chunks:
            all_chunks.append(ch)
            chunk_sources.append(doc["source"])
    
    return all_chunks, chunk_sources


# ---------------------------------------------------------
# EMBEDDINGS + INDEX
# ---------------------------------------------------------
def generate_embeddings(chunks: list, model_name: str = "all-MiniLM-L6-v2") -> list:
    model = SentenceTransformer(model_name)
    return model.encode(chunks)


def build_faiss_index(embeddings: list, chunks: list, metadata: list) -> faiss.Index:
    dim = len(embeddings[0])
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    os.makedirs('../database', exist_ok=True)
    faiss.write_index(index, "../database/vector_store.faiss")

    with open("../database/metadata.json", "w") as f:
        json.dump(metadata, f)

    return index


# ---------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------
def run_data_ingestion():
    print("Loading documents...")
    documents = load_documents()
    print(f"Loaded {len(documents)} documents")

    print("Chunking texts...")
    chunks, chunk_sources = chunk_all_documents(documents)
    print(f"Total chunks: {len(chunks)}")

    print("Generating embeddings...")
    embeddings = generate_embeddings(chunks)
    print(f"Embeddings shape: {embeddings.shape}")

    print("Building FAISS index...")
    metadata = [
        {
            "chunk_id": f"{chunk_sources[i]}_{i}",
            "chunk_index": i,
            "source": chunk_sources[i],
            "text": chunks[i],
        }
        for i in range(len(chunks))
    ]

    index = build_faiss_index(embeddings, chunks, metadata)
    print("FAISS index saved.")

    return index
