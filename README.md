# Adaptive-RAG

## Overview
- Adaptive RAG pipeline using LangChain + LangGraph.
- Routes between vectorstore and web search, grades retrieval, and rewrites queries when needed.
- Includes a Streamlit app for interactive querying.

## Setup
1. Create a `.env` file with your keys:
	- `OPENAI_API_KEY=...`
	- `TAVILY_API_KEY=...`

2. (Optional) Use the provided `rag_env` virtual environment or create your own.

3. Install dependencies:

```powershell
# Windows PowerShell
pip install -r requirements.txt
```

## Run the Streamlit app

```powershell
streamlit run streamlit_app.py
```

The first run will build a FAISS index from the default URLs and cache it under `data/index/faiss_index`.

## Project Structure
- `adaptive_rag/config.py` – Env and defaults (URLs, models, paths)
- `adaptive_rag/indexing.py` – Build/load FAISS vectorstore
- `adaptive_rag/router.py` – Datasource router (vectorstore vs web search)
- `adaptive_rag/graders.py` – Retrieval, hallucination, and answer graders
- `adaptive_rag/chains.py` – RAG prompt chain and question rewriter
- `adaptive_rag/web_search.py` – Tavily search tool wrapper
- `adaptive_rag/graph.py` – LangGraph workflow assembly (`build_app()`)
- `streamlit_app.py` – UI that invokes the compiled graph

## Notes
- The vectorstore indexes posts on agents, prompt engineering, and adversarial attacks. Questions on these topics are routed to the vectorstore; others go to web search.
- Ensure your API keys are valid and rate limits sufficient for the queries you run.