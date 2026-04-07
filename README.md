---
title: Adaptive RAG Chat
emoji: 🧠
colorFrom: yellow
colorTo: red
sdk: docker
pinned: false
---

# 🚀 Adaptive-RAG – Intelligent Retrieval-Augmented Generation System

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"/>
  <img src="https://img.shields.io/badge/LangGraph-latest-green.svg" alt="LangGraph"/>
  <img src="https://img.shields.io/badge/LangChain-latest-yellow.svg" alt="LangChain"/>
   <img src="https://img.shields.io/badge/FastAPI-latest-009688.svg" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Next.js-latest-black.svg" alt="Next.js"/>
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"/>
</p>

<p align="center">
  <strong>An adaptive Retrieval-Augmented Generation (RAG) system that dynamically routes queries between vector search and web search for accurate, grounded answers.</strong>
</p>

<p align="center">
  <a href="#-features">✨ Features</a> •
  <a href="#-architecture">🏗️ Architecture</a> •
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-how-it-works">🔬 How It Works</a> •
  <a href="#-project-structure">📂 Project Structure</a>
</p>

---

## 🎯 Overview

Adaptive-RAG is a **production-oriented RAG pipeline** built using **LangChain and LangGraph** that intelligently decides **how to retrieve information** before generating an answer.

Instead of relying on a single data source, the system:

* Routes questions to a **local FAISS vectorstore** when internal knowledge is sufficient
* Falls back to **web search (Tavily)** when information is missing or outdated
* Grades retrieved documents and generated answers
* Automatically **rewrites queries** when retrieval quality is poor

This results in **more accurate, less hallucinated, and context-aware answers**.

---

## 💡 Why I Built This

**The Problem:**
Traditional RAG systems blindly retrieve documents from a vectorstore, even when:

* The question is out of domain
* Knowledge is outdated
* Retrieval quality is poor

This leads to hallucinations or incomplete answers.

**My Goal:**
Build a **self-correcting RAG pipeline** that can:

* Decide *where* to retrieve from
* Judge *how good* the retrieval is
* Improve itself by rewriting queries when needed

**Key Learning:**
LangGraph is ideal for building **conditional, feedback-driven RAG workflows** instead of linear chains.

---

## ✨ Key Features

* **Adaptive Routing**
  Automatically selects between vectorstore retrieval and web search.

* **Retrieval Grading**
  Evaluates whether retrieved documents are relevant to the query.

* **Hallucination Detection**
  Grades generated answers against retrieved context.

* **Query Rewriting**
  Reformulates weak questions to improve retrieval quality.

* **Graph-based Control Flow**
  Uses LangGraph for explicit decision-making and retry loops.

* **Interactive UI**
  Modern Next.js dashboard for real-time streaming chat and visualization.

---

## 🏗️ Architecture

### High-Level Workflow

```
User Query
   │
   ▼
Router Node
(Vectorstore or Web?)
   │
   ├──► Vectorstore Retrieval (FAISS)
   │
   └──► Web Search (Tavily)
           │
           ▼
Document Grader
   │
   ├── Relevant → Answer Generator
   │
   └── Not Relevant → Query Rewriter
                            │
                            └── Loop Back to Router
```

### LangGraph Advantage

LangGraph enables:

* Conditional edges
* Feedback loops
* Explicit state transitions
* Clean separation of logic

---

## 🔬 How It Works

### 1. Routing

A router node decides whether the query should go to:

* **Vectorstore** (domain-specific questions)
* **Web Search** (open-ended or current topics)

### 2. Retrieval

* Vectorstore uses **FAISS embeddings**
* Web search uses **Tavily API**

### 3. Grading

LLM-based graders check:

* Document relevance
* Answer grounding
* Hallucination risk

### 4. Query Rewriting

If retrieval is weak, the query is rewritten and re-routed automatically.

---

## 🛠️ Tech Stack

| Component     | Technology |
| ------------- | ---------- |
| Orchestration | LangGraph  |
| RAG Framework | LangChain  |
| Vector Store  | FAISS      |
| Web Search    | Tavily     |
| LLM           | Groq (Llama 3.3) |
| Backend       | FastAPI    |
| Frontend      | Next.js    |
| Language      | Python     |

---

## 🚀 Quick Start

### Prerequisites

* Python 3.10+
* Groq API key
* Tavily API key

### Environment Setup

Create a `.env` file:

```
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
```

### Install Dependencies

```powershell
pip install -r requirements.txt
```

### Run the Backend

```powershell
uvicorn backend:app --reload --port 8000
```

### Run the Frontend

```powershell
cd frontend
npm run dev
```

On first run:

* A FAISS index is built
* Cached under `data/index/faiss_index`

---

## 📂 Project Structure (this repo)

```
.
├── backend.py                 # FastAPI backend entry point
├── requirements.txt           # Python dependencies
├── frontend/                  # Next.js frontend application
├── src/
│   ├── graphs/graph_builder.py  # FAISS index + retriever setup
│   ├── llms/llm.py              # RAG prompt and LLM chain
│   ├── nodes/node_implementation.py # Router, retrieve, web_search, graders, transform
│   └── states/state.py          # Graph state + compile (app)
└── data/faiss_index/          # Vectorstore cache (created at runtime)
```

## 🚀 Deployment

The project is structured to be deployed as a decoupled application:
1. **Backend**: FastAPI can be containerized using a `Dockerfile` and deployed to platforms like Render, AWS, or Hugging Face Spaces (Docker SDK).
2. **Frontend**: The Next.js app can be deployed to Vercel or similar static hosting platforms.

Note: Ensure `NEXT_PUBLIC_API_BASE_URL` in the frontend reflects your production backend URL.

Notes:
- First run may build a FAISS index and cache under `src/data/faiss_index/`.
- If web search is disabled (missing Tavily key), queries will route to the vectorstore.

---

## 📊 What Makes This Project Strong

* Not a basic RAG demo
* Uses **decision-making and self-correction**
* Demonstrates **real LangGraph value**
* Clean separation of concerns
* Directly aligned with **industry GenAI systems**

This is the kind of RAG system used in:

* Enterprise knowledge assistants
* AI support bots
* Research copilots
* Internal search tools

---

## 🔮 Future Improvements

* Multi-vector routing (code, docs, FAQs)
* Tool-augmented RAG
* Caching and latency optimization
* Confidence-based answer refusal
* Evaluation dashboards

---

## 👨‍💻 Author

**Vivek Kumar Gupta**
AI Engineering Student | GenAI & Agentic Systems Builder

* GitHub: [https://github.com/vivek34561](https://github.com/vivek34561)
* LinkedIn: [https://linkedin.com/in/vivek-gupta-0400452b6](https://linkedin.com/in/vivek-gupta-0400452b6)
* Portfolio: [https://resume-sepia-seven.vercel.app/](https://resume-sepia-seven.vercel.app/)

---

## 📄 License

MIT License © 2025 Vivek Kumar Gupta

