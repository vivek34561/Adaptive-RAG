import os
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

# Load environment variables.
load_dotenv()

st.set_page_config(page_title="Adaptive RAG Chat", layout="wide")

st.title("Adaptive RAG Chat")

API_BASE_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000").rstrip("/")


def _safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return {}


def api_get(path: str) -> Any:
    response = requests.get(f"{API_BASE_URL}{path}", timeout=30)
    if response.status_code >= 400:
        body = _safe_json(response)
        detail = body.get("detail") if isinstance(body, dict) else response.text
        raise RuntimeError(str(detail))
    return _safe_json(response)


def api_post(path: str, payload: dict[str, Any]) -> Any:
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=90)
    if response.status_code >= 400:
        body = _safe_json(response)
        detail = body.get("detail") if isinstance(body, dict) else response.text
        raise RuntimeError(str(detail))
    return _safe_json(response)


def load_chat_history(session_id: str) -> list[dict[str, str]]:
    items = api_get(f"/sessions/{session_id}/messages")
    history = []
    for item in items:
        role = item.get("role", "assistant")
        if role not in {"user", "assistant"}:
            continue
        history.append({"role": role, "content": item.get("content", "")})
    return history


if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "steps" not in st.session_state:
    st.session_state.steps = []
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "sessions" not in st.session_state:
    st.session_state.sessions = []

try:
    st.session_state.sessions = api_get("/sessions")
except Exception:
    # Keep app usable even if backend session API is temporarily unavailable.
    st.session_state.sessions = st.session_state.get("sessions", [])


with st.sidebar:
    st.header("Settings")
    env_groq = os.getenv("GROQ_API_KEY", "")

    groq_api_key = st.text_input("Groq API Key", type="password", value="")
    if groq_api_key:
        st.session_state["groq_api_key"] = groq_api_key
    elif env_groq and not st.session_state.get("groq_api_key"):
        st.session_state["groq_api_key"] = env_groq

    st.caption(f"Backend: {API_BASE_URL}")

    st.header("Conversations")
    if st.button("+ New Chat", use_container_width=True):
        st.session_state.current_session_id = None
        st.session_state.chat_history = []
        st.session_state.steps = []
        st.rerun()

    for session in st.session_state.sessions:
        session_id = session.get("id")
        title = session.get("title") or "New chat"
        if not session_id:
            continue
        pressed = st.button(
            title[:36],
            key=f"session_{session_id}",
            use_container_width=True,
        )
        if pressed:
            st.session_state.current_session_id = session_id
            try:
                st.session_state.chat_history = load_chat_history(session_id)
                st.session_state.steps = []
            except Exception as exc:
                st.error(f"Failed to load history: {exc}")
            st.rerun()

    st.header("Steps")
    if st.session_state.steps:
        st.markdown("\n".join(f"- {step}" for step in st.session_state.steps))
    else:
        st.write("No steps yet.")

# Chat UI
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("Type your message...")


if question:
    if not st.session_state.get("groq_api_key"):
        st.error("Missing Groq API Key. Set it via Spaces Secrets or paste it in the sidebar.")
    else:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        try:
            payload = {
                "question": question,
                "groq_api_key": st.session_state["groq_api_key"],
                "session_id": st.session_state.current_session_id,
            }
            result = api_post("/chat", payload)

            st.session_state.current_session_id = result.get("session_id")
            answer = result.get("answer", "No answer returned.")
            steps = result.get("steps", [])
            escalated = result.get("escalated", False)
            reason = result.get("escalation_reason")
            if escalated and reason:
                answer = f"{answer}\n\nEscalation reason: {reason}"

            try:
                st.session_state.sessions = api_get("/sessions")
            except Exception:
                pass
        except Exception as e:
            msg = str(e)
            if "api key" in msg.lower():
                answer = "Error: Invalid or missing Groq API Key. Please check your key and try again."
            else:
                answer = f"Error: {e}"
            steps = []
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.session_state.steps = steps
        with st.chat_message("assistant"):
            st.markdown(answer)
        