import streamlit as st
import requests

st.set_page_config(page_title="Adaptive RAG Chat", layout="wide")

st.title("Adaptive RAG Chat")

# Sidebar for steps
with st.sidebar:
    st.header("Steps")
    steps_placeholder = st.empty()

# Chat history in session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "steps" not in st.session_state:
    st.session_state.steps = []

# Chat UI
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("Type your message...")

if question:
    st.session_state.chat_history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    # Call FastAPI backend
    try:
        resp = requests.post(
            "http://localhost:8000/rag/answer",
            json={"question": question},
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("answer", "No answer returned.")
        steps = data.get("steps", [])
    except Exception as e:
        answer = f"Error: {e}"
        steps = []
    st.session_state.chat_history.append({"role": "assistant", "content": answer})
    st.session_state.steps = steps
    with st.chat_message("assistant"):
        st.markdown(answer)

# Update steps sidebar
with st.sidebar:
    if st.session_state.steps:
        st.markdown("\n".join(f"- {step}" for step in st.session_state.steps))
    else:
        st.write("No steps yet.")
