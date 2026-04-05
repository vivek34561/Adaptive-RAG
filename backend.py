import io
import os
from contextlib import redirect_stdout
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.states import state

# Load .env values for local development.
load_dotenv()

app = FastAPI(
    title="Adaptive RAG Backend",
    description="FastAPI backend for the Adaptive RAG workflow",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    groq_api_key: str | None = Field(
        default=None,
        description="Groq API key. Falls back to GROQ_API_KEY environment variable.",
    )
    tavily_api_key: str | None = Field(
        default=None,
        description="Optional Tavily API key. Overrides TAVILY_API_KEY for this process.",
    )


class ChatResponse(BaseModel):
    question: str
    answer: str
    documents_used: int
    steps: list[str]


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Adaptive RAG FastAPI backend is running."}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/models")
def models() -> dict[str, Any]:
    return {
        "llm": "llama-3.3-70b-versatile",
        "embedding": "sentence-transformers/all-MiniLM-L6-v2",
        "routing": ["vectorstore", "web_search"],
    }


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    groq_api_key = payload.groq_api_key or os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise HTTPException(
            status_code=400,
            detail="Missing Groq API key. Provide groq_api_key in request or set GROQ_API_KEY.",
        )

    if payload.tavily_api_key:
        os.environ["TAVILY_API_KEY"] = payload.tavily_api_key

    execution_buffer = io.StringIO()
    try:
        with redirect_stdout(execution_buffer):
            result = state.app.invoke(
                {
                    "question": payload.question,
                    "groq_api_key": groq_api_key,
                }
            )
    except Exception as exc:
        message = str(exc)
        status_code = 400 if "api key" in message.lower() else 500
        raise HTTPException(status_code=status_code, detail=message) from exc

    steps = [line.strip() for line in execution_buffer.getvalue().splitlines() if line.strip()]
    documents = result.get("documents") or []

    return ChatResponse(
        question=payload.question,
        answer=result.get("generation", "No answer returned."),
        documents_used=len(documents),
        steps=steps,
    )
