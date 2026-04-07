
# Index building and retriever setup
import json
import os
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings


EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_SIGNATURE_FILE = "index_signature.json"
INDEX_SOURCE_URLS = [
    "https://lilianweng.github.io/posts/2023-06-23-agent/",
]
DOCUMENTS_DIR_NAME = "documents"
INDEX_CHUNK_SIZE = 500
INDEX_CHUNK_OVERLAP = 50


def _index_signature_path() -> Path:
    return Path(_faiss_dir()) / INDEX_SIGNATURE_FILE


def _expected_index_signature() -> dict:
    return {
        "embedding_model": EMBEDDING_MODEL,
        "urls": INDEX_SOURCE_URLS,
        "pdf_files": _local_pdf_signature(),
        "chunk_size": INDEX_CHUNK_SIZE,
        "chunk_overlap": INDEX_CHUNK_OVERLAP,
    }


def _documents_dir() -> Path:
    return Path(__file__).resolve().parents[2] / DOCUMENTS_DIR_NAME


def _local_pdf_files() -> list[Path]:
    documents_dir = _documents_dir()
    if not documents_dir.exists():
        return []
    return sorted(documents_dir.glob("*.pdf"))


def _local_pdf_signature() -> list[dict[str, str]]:
    signature: list[dict[str, str]] = []
    for pdf_path in _local_pdf_files():
        try:
            signature.append(
                {
                    "path": str(pdf_path.relative_to(Path(__file__).resolve().parents[2])),
                    "mtime": str(pdf_path.stat().st_mtime_ns),
                }
            )
        except Exception:
            signature.append({"path": str(pdf_path), "mtime": "unknown"})
    return signature


def _has_valid_signature() -> bool:
    signature_path = _index_signature_path()
    if not signature_path.exists():
        return False

    try:
        current_signature = json.loads(signature_path.read_text(encoding="utf-8"))
    except Exception:
        return False

    return current_signature == _expected_index_signature()


def _write_signature() -> None:
    _index_signature_path().write_text(
        json.dumps(_expected_index_signature(), indent=2),
        encoding="utf-8",
    )

# Set embeddings to use HuggingFace (free alternative)

def _faiss_dir():
    base = Path(os.path.dirname(os.path.dirname(__file__))) / "data" / "faiss_index"
    base.mkdir(parents=True, exist_ok=True)
    return str(base)

def build_vectorstore_with_key(groq_api_key):
    # Set embeddings to use HuggingFace (no API key needed for embeddings)
    embd = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # Docs to index
    urls = INDEX_SOURCE_URLS
    pdf_files = _local_pdf_files()

    # Load with a default USER_AGENT to avoid warnings
    headers = {"User-Agent": os.getenv("USER_AGENT", "Adaptive-RAG-Streamlit/1.0")}
    loader = WebBaseLoader(web_paths=urls, header_template=headers)
    docs_list = loader.load()

    for pdf_path in pdf_files:
        try:
            pdf_loader = PyPDFLoader(str(pdf_path))
            docs_list.extend(pdf_loader.load())
            print(f"---PDF LOADED: {pdf_path.name}---")
        except Exception as exc:
            print(f"---PDF LOAD FAILED: {pdf_path.name}: {exc}---")

    # Split
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=INDEX_CHUNK_SIZE, chunk_overlap=INDEX_CHUNK_OVERLAP
    )
    doc_splits = text_splitter.split_documents(docs_list)

    if not doc_splits:
        raise ValueError("No documents available to index from web sources or local PDFs.")

    # Add to vectorstore
    # Try to load a cached index; if not present, build and save
    index_dir = _faiss_dir()
    if _has_valid_signature():
        try:
            vectorstore = FAISS.load_local(index_dir, embd, allow_dangerous_deserialization=True)
            print("---VECTORSTORE LOADED FROM DISK---")
            return vectorstore
        except Exception:
            print("---VECTORSTORE LOAD FAILED: REBUILDING---")
    else:
        print("---VECTORSTORE SIGNATURE MISMATCH: REBUILDING---")

    vectorstore = FAISS.from_documents(
        documents=doc_splits,
        embedding=embd
    )
    try:
        vectorstore.save_local(index_dir)
        _write_signature()
        print("---VECTORSTORE SAVED TO DISK---")
    except Exception:
        print("---VECTORSTORE SAVE SKIPPED---")

    return vectorstore


def get_retriever(groq_api_key):
    # Simple in-memory cache for vectorstores (embeddings don't need API key)
    if not hasattr(get_retriever, "_cache"):
        get_retriever._cache = {}
    cache = get_retriever._cache
    if "vectorstore" in cache:
        vectorstore = cache["vectorstore"]
    else:
        vectorstore = build_vectorstore_with_key(groq_api_key)
        cache["vectorstore"] = vectorstore
    return vectorstore.as_retriever(search_kwargs={"k": 2})

def get_graph_info():
    return {"graph": "Vectorstore and retriever initialized."}