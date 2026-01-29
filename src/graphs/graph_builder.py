
# Index building and retriever setup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from pathlib import Path
import os

# Set embeddings to use HuggingFace (free alternative)

def _faiss_dir():
    base = Path(os.path.dirname(os.path.dirname(__file__))) / "data" / "faiss_index"
    base.mkdir(parents=True, exist_ok=True)
    return str(base)

def build_vectorstore_with_key(groq_api_key):
    # Set embeddings to use HuggingFace (no API key needed for embeddings)
    embd = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Docs to index
    urls = [
        "https://lilianweng.github.io/posts/2023-06-23-agent/"
    ]

    # Load with a default USER_AGENT to avoid warnings
    headers = {"User-Agent": os.getenv("USER_AGENT", "Adaptive-RAG-Streamlit/1.0")}
    loader = WebBaseLoader(web_paths=urls, header_template=headers)
    docs_list = loader.load()

    # Split
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=500, chunk_overlap=50
    )
    doc_splits = text_splitter.split_documents(docs_list)

    # Add to vectorstore
    # Try to load a cached index; if not present, build and save
    index_dir = _faiss_dir()
    try:
        vectorstore = FAISS.load_local(index_dir, embd, allow_dangerous_deserialization=True)
        print("---VECTORSTORE LOADED FROM DISK---")
    except Exception:
        vectorstore = FAISS.from_documents(
            documents=doc_splits,
            embedding=embd
        )
        try:
            vectorstore.save_local(index_dir)
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
    return vectorstore.as_retriever()

def get_graph_info():
    return {"graph": "Vectorstore and retriever initialized."}