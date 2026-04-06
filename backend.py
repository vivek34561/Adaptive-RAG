import io
import os
import re
from contextlib import redirect_stdout
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.storage.chat_store import (
    ChatStoreError,
    append_message,
    create_session,
    get_messages,
    list_sessions,
)
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


_memory_sessions: dict[str, dict[str, Any]] = {}
_memory_messages: dict[str, list[dict[str, Any]]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_memory_session(title: str) -> dict[str, Any]:
    session_id = str(uuid4())
    row = {
        "id": session_id,
        "title": title[:120] if title else "New chat",
        "created_at": _now_iso(),
        "last_message_at": _now_iso(),
    }
    _memory_sessions[session_id] = row
    _memory_messages[session_id] = []
    return row


def _append_memory_message(
    session_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if session_id not in _memory_sessions:
        _memory_sessions[session_id] = {
            "id": session_id,
            "title": "Recovered chat",
            "created_at": _now_iso(),
            "last_message_at": _now_iso(),
        }
        _memory_messages.setdefault(session_id, [])
    row = {
        "id": str(uuid4()),
        "session_id": session_id,
        "role": role,
        "content": content,
        "metadata": metadata or {},
        "created_at": _now_iso(),
    }
    _memory_messages.setdefault(session_id, []).append(row)
    _memory_sessions[session_id]["last_message_at"] = _now_iso()
    return row


def _list_memory_sessions() -> list[dict[str, Any]]:
    rows = list(_memory_sessions.values())
    return sorted(rows, key=lambda item: item.get("last_message_at", ""), reverse=True)


def _get_memory_messages(session_id: str) -> list[dict[str, Any]]:
    return _memory_messages.get(session_id, [])


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    session_id: str | None = Field(default=None, description="Existing chat session id")
    groq_api_key: str | None = Field(
        default=None,
        description="Groq API key. Falls back to GROQ_API_KEY environment variable.",
    )


class ChatResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    documents_used: int
    steps: list[str]
    escalated: bool
    escalation_reason: str | None = None


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str | None = None
    last_message_at: str | None = None


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    metadata: dict[str, Any] | None = None
    created_at: str | None = None


class CreateSessionRequest(BaseModel):
    title: str | None = None


def _is_simple_greeting(text: str) -> bool:
    normalized = re.sub(r"[^a-z]", "", text.lower())
    return normalized in {"hi", "hello", "hey", "hola", "namaste"}


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
        "routing": ["vectorstore", "human_escalation"],
    }


@app.get("/sessions", response_model=list[SessionResponse])
def sessions() -> list[SessionResponse]:
    try:
        return [SessionResponse(**item) for item in list_sessions()]
    except ChatStoreError:
        return [SessionResponse(**item) for item in _list_memory_sessions()]


@app.post("/sessions", response_model=SessionResponse)
def new_session(payload: CreateSessionRequest) -> SessionResponse:
    title = payload.title or "New chat"
    try:
        row = create_session(title)
    except ChatStoreError:
        row = _create_memory_session(title)
    return SessionResponse(**row)


@app.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
def session_messages(session_id: str) -> list[MessageResponse]:
    try:
        return [MessageResponse(**item) for item in get_messages(session_id)]
    except ChatStoreError:
        return [MessageResponse(**item) for item in _get_memory_messages(session_id)]


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    use_memory_store = False
    try:
        if payload.session_id:
            session_id = payload.session_id
        else:
            created = create_session(payload.question)
            session_id = created["id"]
    except ChatStoreError:
        use_memory_store = True
        if payload.session_id:
            session_id = payload.session_id
            if session_id not in _memory_sessions:
                _memory_sessions[session_id] = {
                    "id": session_id,
                    "title": payload.question[:120] if payload.question else "Recovered chat",
                    "created_at": _now_iso(),
                    "last_message_at": _now_iso(),
                }
                _memory_messages.setdefault(session_id, [])
        else:
            created = _create_memory_session(payload.question)
            session_id = created["id"]

    if use_memory_store:
        _append_memory_message(session_id=session_id, role="user", content=payload.question)
    else:
        try:
            append_message(session_id=session_id, role="user", content=payload.question)
        except ChatStoreError:
            use_memory_store = True
            _append_memory_message(session_id=session_id, role="user", content=payload.question)

    if _is_simple_greeting(payload.question):
        greeting_response = ChatResponse(
            session_id=session_id,
            question=payload.question,
            answer="Hi! How can I help you today?",
            documents_used=0,
            steps=["---GREETING SHORT-CIRCUIT---"],
            escalated=False,
        )
        if use_memory_store:
            _append_memory_message(
                session_id=session_id,
                role="assistant",
                content=greeting_response.answer,
                metadata={"steps": greeting_response.steps, "escalated": False},
            )
        else:
            try:
                append_message(
                    session_id=session_id,
                    role="assistant",
                    content=greeting_response.answer,
                    metadata={"steps": greeting_response.steps, "escalated": False},
                )
            except ChatStoreError:
                _append_memory_message(
                    session_id=session_id,
                    role="assistant",
                    content=greeting_response.answer,
                    metadata={"steps": greeting_response.steps, "escalated": False},
                )
        return greeting_response

    groq_api_key = payload.groq_api_key or os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise HTTPException(
            status_code=400,
            detail="Missing Groq API key. Provide groq_api_key in request or set GROQ_API_KEY.",
        )

    execution_buffer = io.StringIO()
    try:
        with redirect_stdout(execution_buffer):
            result = state.app.invoke(
                {
                    "question": payload.question,
                    "groq_api_key": groq_api_key,
                    "retrieval_attempts": 0,
                    "generation_attempts": 0,
                    "escalated": False,
                    "escalation_reason": "",
                }
            )
    except Exception as exc:
        message = str(exc)
        status_code = 400 if "api key" in message.lower() else 500
        raise HTTPException(status_code=status_code, detail=message) from exc

    steps = [line.strip() for line in execution_buffer.getvalue().splitlines() if line.strip()]
    documents = result.get("documents") or []
    escalated = bool(result.get("escalated", False))
    escalation_reason = result.get("escalation_reason") or None

    answer = result.get("generation", "No answer returned.")

    if use_memory_store:
        _append_memory_message(
            session_id=session_id,
            role="assistant",
            content=answer,
            metadata={
                "steps": steps,
                "documents_used": len(documents),
                "escalated": escalated,
                "escalation_reason": escalation_reason,
            },
        )
    else:
        try:
            append_message(
                session_id=session_id,
                role="assistant",
                content=answer,
                metadata={
                    "steps": steps,
                    "documents_used": len(documents),
                    "escalated": escalated,
                    "escalation_reason": escalation_reason,
                },
            )
        except ChatStoreError:
            _append_memory_message(
                session_id=session_id,
                role="assistant",
                content=answer,
                metadata={
                    "steps": steps,
                    "documents_used": len(documents),
                    "escalated": escalated,
                    "escalation_reason": escalation_reason,
                },
            )

    return ChatResponse(
        session_id=session_id,
        question=payload.question,
        answer=answer,
        documents_used=len(documents),
        steps=steps,
        escalated=escalated,
        escalation_reason=escalation_reason,
    )
