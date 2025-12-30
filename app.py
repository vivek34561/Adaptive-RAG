import streamlit as st
import requests

st.set_page_config(page_title="Adaptive RAG Chat", layout="wide")

st.title("Adaptive RAG Chat")


# Sidebar for API key and steps
with st.sidebar:
    st.header("Settings")
    openai_api_key = st.text_input("OpenAI API Key", type="password", value= "")
    if openai_api_key:
        st.session_state["openai_api_key"] = openai_api_key
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
    if not st.session_state.get("openai_api_key"):
        st.error("Please fill in your OpenAI API Key in the sidebar before chatting.")
    else:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        # Call FastAPI backend
        headers = {}
        headers["OPENAI_API_KEY"] = st.session_state["openai_api_key"]
        try:
            resp = requests.post(
                "http://localhost:8000/rag/answer",
                json={"question": question},
                headers=headers,
                timeout=60
            )
            if resp.status_code == 401 or (resp.status_code == 400 and 'invalid api key' in resp.text.lower()):
                answer = "Error: Invalid OpenAI API Key. Please check your key and try again."
                steps = []
            else:
                resp.raise_for_status()
                data = resp.json()
                answer = data.get("answer", "No answer returned.")
                steps = data.get("steps", [])
        except Exception as e:
            if "invalid api key" in str(e).lower():
                answer = "Error: Invalid OpenAI API Key. Please check your key and try again."
            else:
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
