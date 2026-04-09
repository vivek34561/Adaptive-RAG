import io
import os
import re
import threading
from contextlib import redirect_stdout
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import asyncio
from pydantic import BaseModel, Field

from src.storage.chat_store import (
    ChatStoreError,
    append_message,
    create_session,
    get_messages,
    list_sessions,
    update_session_title,
    log_escalation,
)
# NOTE: Heavy imports (langchain_groq, src.states.state) are loaded LAZILY
# to ensure the FastAPI server binds to the port immediately on startup.
# This prevents Render's port-scan timeout.

_rag_app_cache = None

def _get_rag_app():
    """Lazy-load the LangGraph RAG app (heavy imports: PyTorch, sentence-transformers)."""
    global _rag_app_cache
    if _rag_app_cache is None:
        from src.states import state
        _rag_app_cache = state.app
    return _rag_app_cache

# Load .env values for local development.
load_dotenv()


def _generate_title_with_llm(question: str, groq_api_key: str) -> str:
    """Call Groq LLM to produce a concise ≤6-word chat title."""
    try:
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0,
            groq_api_key=groq_api_key,
            max_tokens=20,
        )
        prompt = (
            "Generate a concise chat title (maximum 6 words, no quotes, no punctuation at the end) "
            f"that summarises this question: {question}"
        )
        response = llm.invoke(prompt)
        title = response.content.strip().strip('"').strip("'")[:80]
        return title if title else question[:60]
    except Exception:
        return question[:60] + ("…" if len(question) > 60 else "")


def _rename_session_async(
    session_id: str,
    question: str,
    groq_api_key: str,
    memory_sessions: dict,
) -> None:
    """Generate an LLM title in a background thread and update the session."""

    def _worker() -> None:
        title = _generate_title_with_llm(question, groq_api_key)
        # Update DB (best-effort)
        try:
            update_session_title(session_id, title)
        except ChatStoreError:
            pass
        # Also update in-memory store if present
        if session_id in memory_sessions:
            memory_sessions[session_id]["title"] = title

    threading.Thread(target=_worker, daemon=True).start()

from contextlib import asynccontextmanager

def _background_warmup():
    """Pre-warm the RAG app and vectorstore in a background thread on startup."""
    try:
        import os
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            print("---WARMUP: Loading RAG app and vectorstore...---")
            from src.states import state as _state_mod
            _ = _state_mod.app
            # Also pre-build the vectorstore
            from src.graphs.graph_builder import get_retriever
            _ = get_retriever(groq_key)
            print("---WARMUP: Done. Backend ready.---")
        else:
            print("---WARMUP: GROQ_API_KEY not set, skipping vectorstore pre-warm.---")
    except Exception as exc:
        print(f"---WARMUP ERROR (non-fatal): {exc}---")

@asynccontextmanager
async def lifespan(app_instance):
    # Start background warmup thread so port binds immediately
    warmup_thread = threading.Thread(target=_background_warmup, daemon=True)
    warmup_thread.start()
    yield

app = FastAPI(
    title="Adaptive RAG Backend",
    description="FastAPI backend for the Adaptive RAG workflow",
    version="1.0.0",
    lifespan=lifespan,
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
        "llm": "openai/gpt-oss-20b",
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


class UpdateSessionRequest(BaseModel):
    title: str


@app.patch("/sessions/{session_id}", response_model=SessionResponse)
def rename_session(session_id: str, payload: UpdateSessionRequest) -> SessionResponse:
    title = payload.title.strip()[:80] or "New chat"
    try:
        update_session_title(session_id, title)
        rows = list_sessions()
        row = next((r for r in rows if r["id"] == session_id), None)
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        return SessionResponse(**row)
    except ChatStoreError:
        if session_id in _memory_sessions:
            _memory_sessions[session_id]["title"] = title
            return SessionResponse(**_memory_sessions[session_id])
        raise HTTPException(status_code=404, detail="Session not found")


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
            chat_title = payload.question[:60] + ("…" if len(payload.question) > 60 else "")
            created = create_session(chat_title)
            session_id = created["id"]
            # Kick off LLM title generation in background (non-blocking)
            groq_key = payload.groq_api_key or os.getenv("GROQ_API_KEY") or ""
            if groq_key:
                _rename_session_async(session_id, payload.question, groq_key, _memory_sessions)
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
            chat_title = payload.question[:60] + ("…" if len(payload.question) > 60 else "")
            created = _create_memory_session(chat_title)
            session_id = created["id"]
            # Kick off LLM title generation in background (non-blocking)
            groq_key = payload.groq_api_key or os.getenv("GROQ_API_KEY") or ""
            if groq_key:
                _rename_session_async(session_id, payload.question, groq_key, _memory_sessions)

    # Fetch history before appending current message to use as context
    chat_history_str = ""
    if session_id:
        if use_memory_store:
            history_msgs = _get_memory_messages(session_id)
        else:
            try:
                history_msgs = get_messages(session_id)
            except ChatStoreError:
                history_msgs = _get_memory_messages(session_id)
        
        formatted_history = []
        for m in history_msgs[-10:]:
            r = m.get("role", "")
            if r in ("user", "assistant"):
                formatted_history.append(f"{r.capitalize()}: {m.get('content', '')}")
        chat_history_str = "\n".join(formatted_history)

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
        from src.states import state
        # Ensure it's imported correctly
        _rag_app_cache = state.app
        with redirect_stdout(execution_buffer):
            result = _rag_app_cache.invoke(
                {
                    "question": payload.question,
                    "chat_history": chat_history_str,
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
    escalation_reason = result.get("escalation_reason") or "Unknown reason"

    if escalated and not use_memory_store:
        try:
            log_escalation(session_id, payload.question, chat_history_str, escalation_reason)
        except ChatStoreError:
            pass

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

@app.post("/chat/stream")
async def chat_stream(payload: ChatRequest):
    use_memory_store = False
    try:
        if payload.session_id:
            session_id = payload.session_id
        else:
            chat_title = payload.question[:60] + ("…" if len(payload.question) > 60 else "")
            created = create_session(chat_title)
            session_id = created["id"]
            groq_key = payload.groq_api_key or os.getenv("GROQ_API_KEY") or ""
            if groq_key:
                _rename_session_async(session_id, payload.question, groq_key, _memory_sessions)
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
            chat_title = payload.question[:60] + ("…" if len(payload.question) > 60 else "")
            created = _create_memory_session(chat_title)
            session_id = created["id"]
            groq_key = payload.groq_api_key or os.getenv("GROQ_API_KEY") or ""
            if groq_key:
                _rename_session_async(session_id, payload.question, groq_key, _memory_sessions)

    chat_history_str = ""
    if session_id:
        if use_memory_store:
            history_msgs = _get_memory_messages(session_id)
        else:
            try:
                history_msgs = get_messages(session_id)
            except ChatStoreError:
                history_msgs = _get_memory_messages(session_id)
        
        formatted_history = []
        for m in history_msgs[-10:]:
            r = m.get("role", "")
            if r in ("user", "assistant"):
                formatted_history.append(f"{r.capitalize()}: {m.get('content', '')}")
        chat_history_str = "\n".join(formatted_history)

    if use_memory_store:
        _append_memory_message(session_id=session_id, role="user", content=payload.question)
    else:
        try:
            append_message(session_id=session_id, role="user", content=payload.question)
        except ChatStoreError:
            use_memory_store = True
            _append_memory_message(session_id=session_id, role="user", content=payload.question)

    async def event_generator():
        yield f"data: {json.dumps({'type': 'session_init', 'session_id': session_id})}\n\n"

        if _is_simple_greeting(payload.question):
            ans = "Hi! How can I help you today?"
            yield f"data: {json.dumps({'type': 'content', 'content': ans})}\n\n"
            if use_memory_store:
                _append_memory_message(session_id=session_id, role="assistant", content=ans)
            else:
                try:
                    append_message(session_id=session_id, role="assistant", content=ans)
                except ChatStoreError:
                    _append_memory_message(session_id=session_id, role="assistant", content=ans)
            yield "data: [DONE]\n\n"
            return

        groq_api_key = payload.groq_api_key or os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Missing API key.'})}\n\n"
            return
            
        full_answer = ""
        try:
            yield f"data: {json.dumps({'type': 'status', 'content': 'Initializing components (may take a moment)...'})}\n\n"
            
            from src.states import state
            rag_app = state.app
            
            async for event in rag_app.astream_events(
                {
                    "question": payload.question,
                    "chat_history": chat_history_str,
                    "groq_api_key": groq_api_key,
                    "retrieval_attempts": 0,
                    "generation_attempts": 0,
                    "escalated": False,
                    "escalation_reason": "",
                },
                version="v1"
            ):
                if event["event"] == "on_chain_start":
                    node_name = event.get("name")
                    status_map = {
                        "route_question": "Routing your question...",
                        "retrieve": "Searching knowledge base...",
                        "grade_documents": "Evaluating document relevance...",
                        "transform_query": "Re-writing query for better search...",
                        "generate": "Generating answer...",
                        "grade_generation_v_documents_and_question": "Double-checking answer..."
                    }
                    if node_name in status_map:
                        yield f"data: {json.dumps({'type': 'status', 'content': status_map[node_name]})}\n\n"
                        
                elif event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    if chunk:
                        full_answer += chunk
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                        await asyncio.sleep(0.01)
                elif event["event"] == "on_chain_end" and event.get("name") == "human_escalation":
                    output = event["data"].get("output", {})
                    
                    if not use_memory_store:
                        try:
                            log_escalation(
                                session_id,
                                payload.question,
                                chat_history_str,
                                output.get("escalation_reason", "Reason not specified")
                            )
                        except ChatStoreError:
                            pass
                            
                    if isinstance(output, dict) and "generation" in output:
                        chunk = output["generation"]
                        if chunk:
                            full_answer += chunk
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                            await asyncio.sleep(0.01)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            
        if not full_answer:
            full_answer = "This query is out of context. Your query has been escalated to a human reviewer."
            yield f"data: {json.dumps({'type': 'content', 'content': full_answer})}\n\n"
            
        if use_memory_store:
            _append_memory_message(session_id=session_id, role="assistant", content=full_answer)
        else:
            try:
                append_message(session_id=session_id, role="assistant", content=full_answer)
            except ChatStoreError:
                _append_memory_message(session_id=session_id, role="assistant", content=full_answer)

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", "8002"))
    print(f"---STARTING BACKEND ON PORT {port}---")
    uvicorn.run(app, host="0.0.0.0", port=port)
