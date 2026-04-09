# 🚀 Adaptive-RAG – Intelligent Retrieval-Augmented Generation System

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python"/>
  <img src="https://img.shields.io/badge/LangGraph-0.2+-green.svg" alt="LangGraph"/>
  <img src="https://img.shields.io/badge/LangChain-0.3+-yellow.svg" alt="LangChain"/>
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688.svg" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Next.js-16-black.svg" alt="Next.js"/>
  <img src="https://img.shields.io/badge/Docker-ready-2496ED.svg?logo=docker" alt="Docker"/>
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"/>
</p>

<p align="center">
  <a href="https://hub.docker.com/r/vivek3242/adaptive-rag-backend">
    <img src="https://img.shields.io/docker/pulls/vivek3242/adaptive-rag-backend?label=backend%20pulls&logo=docker" alt="Docker Backend Pulls"/>
  </a>
  <a href="https://hub.docker.com/r/vivek3242/adaptive-rag-frontend">
    <img src="https://img.shields.io/docker/pulls/vivek3242/adaptive-rag-frontend?label=frontend%20pulls&logo=docker" alt="Docker Frontend Pulls"/>
  </a>
</p>

<p align="center">
  <strong>A self-correcting Retrieval-Augmented Generation system that dynamically routes, grades, and rewrites queries for accurate, grounded answers — with a real-time streaming chat UI.</strong>
</p>

<p align="center">
  <a href="#-features">✨ Features</a> •
  <a href="#-architecture">🏗️ Architecture</a> •
  <a href="#-tech-stack">🛠️ Tech Stack</a> •
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-docker">🐳 Docker</a> •
  <a href="#-deployment">☁️ Deployment</a> •
  <a href="#-project-structure">📂 Project Structure</a>
</p>

---

## 🎯 Overview

Adaptive-RAG is a **production-grade RAG pipeline** built with **LangChain and LangGraph** that intelligently decides *how* to retrieve information before generating an answer.

Instead of blindly retrieving documents, the system:

- Routes queries to a **local FAISS vectorstore** for domain-specific questions
- **Escalates to a human reviewer** when the query is out-of-scope or needs expert judgment
- **Grades** retrieved documents for relevance before generating
- **Rewrites queries** when retrieval quality is poor, then retries
- **Validates answers** for hallucinations and grounding before returning

This results in **more accurate, less hallucinated, and context-aware answers**.

---

## 💡 Why I Built This

**The Problem:**
Traditional RAG systems blindly retrieve from a vectorstore even when:
- The question is out of domain
- Knowledge is stale or missing
- Retrieval quality is poor

This leads to hallucinations or incomplete answers.

**My Goal:**
Build a **self-correcting RAG pipeline** that can:
- Decide *where* to retrieve from
- Judge *how good* the retrieval is
- Improve itself by rewriting queries when needed
- Know when to escalate rather than guess

**Key Learning:**
LangGraph is ideal for building **conditional, feedback-driven RAG workflows** instead of linear chains.

---

## ✨ Key Features

- **Adaptive Routing** — Automatically routes between vectorstore retrieval and human escalation based on query type
- **Retrieval Grading** — LLM-based grader evaluates whether retrieved documents are relevant
- **Hallucination Detection** — Grades generated answers against retrieved context for factual grounding
- **Query Rewriting** — Reformulates weak or ambiguous questions to improve retrieval quality
- **Human Escalation** — Out-of-scope queries are escalated and logged to a reviewer queue
- **Real-time Streaming** — SSE-based token-by-token streaming with status updates (routing, retrieving, grading, generating)
- **Chat Persistence** — Full conversation history stored in Supabase (PostgreSQL) with in-memory fallback
- **Session Management** — LLM-generated chat titles, per-session message history, sidebar navigation
- **Graph-based Control Flow** — LangGraph manages explicit state, conditional edges, and retry loops
- **Fully Dockerized** — Backend and frontend images published to Docker Hub with CI/CD on every push

---

## 🏗️ Architecture

### LangGraph Workflow

```
User Query
   │
   ▼
┌─────────────────┐
│  route_question │  ← llama-3.1-8b-instant decides: vectorstore or human_escalation
└─────────────────┘
   │
   ├──► human_escalation   ← Query logged, graceful escalation message returned
   │
   └──► retrieve (FAISS)
            │
            ▼
       grade_documents     ← Each doc scored relevant / not relevant
            │
            ├── All relevant → generate
            │                     │
            │                     ▼
            │              grade_generation   ← Hallucination + answer quality check
            │                     │
            │                     ├── useful → ✅ Return answer
            │                     ├── not useful → generate (retry)
            │                     └── not supported → generate (retry)
            │
            └── None relevant
                     │
                     ├── retrieval_attempts < 1 → transform_query → retrieve (retry)
                     └── retrieval_attempts ≥ 1 → human_escalation
```

### System Architecture

```
┌─────────────────────┐         ┌──────────────────────────┐
│   Next.js Frontend  │ ──SSE──►│   FastAPI Backend         │
│  (Vercel)           │◄────────│  (Render)                │
└─────────────────────┘         │                          │
                                │  ┌────────────────────┐  │
                                │  │  LangGraph RAG App  │  │
                                │  │  (lazy-loaded)      │  │
                                │  └────────────────────┘  │
                                │           │              │
                                │    ┌──────┴──────┐       │
                                │    ▼             ▼       │
                                │  FAISS       Groq LLM   │
                                │  (HF API     (llama-3)  │
                                │  embeddings)            │
                                └──────────┬───────────────┘
                                           │
                                    ┌──────▼──────┐
                                    │  Supabase   │
                                    │ (PostgreSQL)│
                                    └─────────────┘
```

---

## 🛠️ Tech Stack

| Component         | Technology                                          |
| ----------------- | --------------------------------------------------- |
| Orchestration     | LangGraph ≥ 0.2                                    |
| RAG Framework     | LangChain ≥ 0.3                                    |
| LLM               | Groq — `llama-3.1-8b-instant`                      |
| Embedding Model   | `sentence-transformers/all-MiniLM-L6-v2` (via HuggingFace Inference API — no local PyTorch) |
| Vector Store      | FAISS (CPU, persisted to disk)                     |
| Backend           | FastAPI + Uvicorn (streaming via SSE)              |
| Frontend          | Next.js 16 (React, TypeScript, Tailwind CSS)       |
| Chat Storage      | Supabase (PostgreSQL) + in-memory fallback         |
| Containerization  | Docker + Docker Compose                            |
| CI/CD             | GitHub Actions → Docker Hub                        |
| Deployment        | Render (backend), Vercel (frontend)                |
| Python Version    | 3.11.11                                            |

---

## 🔬 How It Works

### 1. Routing
The `route_question` node uses `llama-3.1-8b-instant` with structured output to decide:
- **`vectorstore`** — domain questions about AI agents, prompt engineering, adversarial attacks
- **`human_escalation`** — off-topic, policy-sensitive, or time-sensitive queries

### 2. Retrieval
- FAISS vectorstore is built from web URLs + local PDFs on startup
- Embeddings are generated via **HuggingFace Inference API** (`all-MiniLM-L6-v2`) — no PyTorch required
- The index is cached to disk and reused across restarts

### 3. Document Grading
Each retrieved document is scored `yes/no` for relevance to the question. Irrelevant documents are filtered out.

### 4. Generation
Relevant context + chat history are passed to the RAG chain (`llama-3.1-8b-instant`) for answer generation.

### 5. Answer Validation
The generated answer is checked for:
- **Hallucinations** — is it grounded in the retrieved documents?
- **Adequacy** — does it actually address the question?

If either check fails, the system retries or escalates.

### 6. Streaming
The backend streams status updates and answer tokens via **Server-Sent Events (SSE)**. The frontend renders tokens word-by-word as they arrive.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Groq API key](https://console.groq.com) (free)
- [HuggingFace token](https://huggingface.co/settings/tokens) (free, for embeddings API)
- Supabase project (optional — falls back to in-memory storage)

### 1. Clone & Setup

```bash
git clone https://github.com/vivek34561/Adaptive-RAG.git
cd Adaptive-RAG
```

### 2. Create `.env`

```env
GROQ_API_KEY=your_groq_api_key
HF_TOKEN=your_huggingface_token
TAVILY_API_KEY=your_tavily_key          # optional
LANGCHAIN_API_KEY=your_langsmith_key    # optional, for tracing
DATABASE_URL=your_supabase_postgres_url # optional, falls back to in-memory
```

### 3. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Backend

```bash
uvicorn backend:app --reload --port 8000
```

On startup, the server:
1. Binds to port immediately (no startup delay)
2. Kicks off a **background warmup** — builds/loads the FAISS index
3. Logs `---WARMUP: Done. Backend ready.---` when ready

### 5. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `frontend/.env.local`.

Open [http://localhost:3000](http://localhost:3000).

---

## 🐳 Docker

Pre-built images are available on Docker Hub and updated automatically on every push to `main`.

### Pull & Run

```bash
# Backend (FastAPI on port 7860)
docker pull vivek3242/adaptive-rag-backend:latest
docker run -p 7860:7860 \
  -e GROQ_API_KEY=your_key \
  -e HF_TOKEN=your_token \
  vivek3242/adaptive-rag-backend:latest

# Frontend (Next.js on port 3000)
docker pull vivek3242/adaptive-rag-frontend:latest
docker run -p 3000:3000 vivek3242/adaptive-rag-frontend:latest
```

### Run Full Stack Locally with Docker Compose

```bash
# Clone the repo and add your .env file, then:
docker compose up --build
```

| Service  | URL                      |
|----------|--------------------------|
| Frontend | http://localhost:3000    |
| Backend  | http://localhost:7860    |
| Health   | http://localhost:7860/health |

```bash
# Run in background
docker compose up -d --build

# View logs
docker compose logs -f

# Stop everything
docker compose down
```

### Docker Hub Repositories

| Image | Link |
|-------|------|
| Backend | [vivek3242/adaptive-rag-backend](https://hub.docker.com/r/vivek3242/adaptive-rag-backend) |
| Frontend | [vivek3242/adaptive-rag-frontend](https://hub.docker.com/r/vivek3242/adaptive-rag-frontend) |

> Images are tagged with both `:latest` and `:<commit-sha>` for easy rollbacks.

---

## ☁️ Deployment

### Backend → Render

1. Push code to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Set **Start Command**: `uvicorn backend:app --host 0.0.0.0 --port $PORT`
4. Set **Python Version**: `3.11.11` (via `runtime.txt`)
5. Add all environment variables under **Environment**:

| Key | Value |
|-----|-------|
| `GROQ_API_KEY` | your key |
| `HF_TOKEN` | your key |
| `DATABASE_URL` | your Supabase URL |
| `TAVILY_API_KEY` | your key (optional) |

> ⚠️ **Free tier note:** Render free tier spins services down after 15 min of inactivity. Cold start takes ~2 min.

### Frontend → Vercel

1. Connect your GitHub repo to [Vercel](https://vercel.com)
2. Set **Root Directory** to `frontend`
3. Add environment variable:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_BASE_URL` | `https://your-backend.onrender.com` |

### CI/CD — GitHub Actions → Docker Hub

On every push to `main`, the workflow automatically:
1. Builds the backend Docker image → pushes `vivek3242/adaptive-rag-backend:latest`
2. Builds the frontend Docker image → pushes `vivek3242/adaptive-rag-frontend:latest`

**Required GitHub Secrets:**

| Secret | Value |
|--------|-------|
| `DOCKERHUB_TOKEN` | Docker Hub access token (Read & Write) |
| `NEXT_PUBLIC_API_BASE_URL` | Your Render backend URL |

---

## 📂 Project Structure

```
Adaptive-RAG/
├── backend.py                        # FastAPI app — all API endpoints + SSE streaming
├── requirements.txt                  # Python dependencies (no PyTorch!)
├── runtime.txt                       # Python 3.11.11 for Render
├── Dockerfile                        # Backend Docker image (port 7860)
├── docker-compose.yml                # Full-stack local dev (backend + frontend)
├── .dockerignore                     # Excludes venvs, secrets from backend image
├── .env                              # Local secrets (not committed)
│
├── src/
│   ├── graphs/
│   │   └── graph_builder.py          # FAISS index builder + HuggingFace API embeddings
│   ├── llms/
│   │   └── llm.py                    # RAG prompt template + Groq LLM chain
│   ├── nodes/
│   │   └── node_implementation.py    # All graph nodes: route, retrieve, grade, generate, escalate
│   ├── states/
│   │   └── state.py                  # LangGraph state schema + compiled app
│   ├── storage/
│   │   └── chat_store.py             # Supabase session/message persistence
│   └── data/
│       └── faiss_index/              # Vectorstore cache (auto-created at runtime)
│
├── frontend/
│   ├── Dockerfile                    # Frontend Docker image (multi-stage, Next.js standalone)
│   ├── .dockerignore                 # Excludes node_modules from build context
│   ├── src/
│   │   ├── app/                      # Next.js App Router pages
│   │   └── components/ui/
│   │       └── animated-ai-chat.tsx  # Main chat UI with sidebar + streaming
│   ├── .env.local                    # Frontend env (NEXT_PUBLIC_API_BASE_URL)
│   └── package.json
│
├── documents/                        # Drop PDFs here to add to the knowledge base
└── .github/workflows/main.yaml       # CI/CD → builds & pushes Docker images to Docker Hub
```

---

## 📊 What Makes This Project Stand Out

| Aspect | Detail |
|--------|--------|
| **Self-correcting** | Not a linear chain — the graph retries, rewrites, and escalates |
| **Streaming UX** | Real-time status + token streaming via SSE |
| **Production patterns** | Lazy loading, startup warmup, in-memory fallback, graceful error handling |
| **No local PyTorch** | Embeddings use HuggingFace Inference API — lightweight, deployable on free tier |
| **Persistent history** | Supabase-backed chat sessions with automatic LLM-generated titles |
| **Fully Dockerized** | Multi-stage builds, Docker Hub CI/CD, docker-compose for local dev |

This is the kind of RAG system used in enterprise knowledge assistants, AI support bots, and research copilots.

---

## 🔮 Future Improvements

- [ ] Multi-document upload via UI
- [ ] Tool-augmented RAG (calculator, code interpreter)
- [ ] Evaluation dashboard with RAGAS metrics
- [ ] Confidence-based answer refusal
- [ ] Support for multiple knowledge domains with separate vectorstores

---

## 👨‍💻 Author

**Vivek Kumar Gupta**  
AI Engineering Student | GenAI & Agentic Systems Builder

- GitHub: [github.com/vivek34561](https://github.com/vivek34561)
- LinkedIn: [linkedin.com/in/vivek-gupta-0400452b6](https://linkedin.com/in/vivek-gupta-0400452b6)
- Portfolio: [resume-sepia-seven.vercel.app](https://resume-sepia-seven.vercel.app/)

---

## 📄 License

MIT License © 2025 Vivek Kumar Gupta
