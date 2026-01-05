
# Index building and retriever setup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from pathlib import Path
import os

# Set embeddings to use OpenAI

def _faiss_dir():
    base = Path(os.path.dirname(os.path.dirname(__file__))) / "data" / "faiss_index"
    base.mkdir(parents=True, exist_ok=True)
    return str(base)

def build_vectorstore_with_key(openai_api_key):
    # Set embeddings to use OpenAI with user-supplied key
    embd = OpenAIEmbeddings(openai_api_key=openai_api_key)

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


def get_retriever(openai_api_key):
    # Simple in-memory cache for vectorstores per API key
    if not hasattr(get_retriever, "_cache"):
        get_retriever._cache = {}
    cache = get_retriever._cache
    if openai_api_key in cache:
        vectorstore = cache[openai_api_key]
    else:
        vectorstore = build_vectorstore_with_key(openai_api_key)
        cache[openai_api_key] = vectorstore
    return vectorstore.as_retriever()

def get_graph_info():
    return {"graph": "Vectorstore and retriever initialized."}
