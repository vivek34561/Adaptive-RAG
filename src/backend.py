
import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from src.graphs import graph_builder
from src.llms import llm
from src.nodes import node_implementation

# Import the compiled workflow graph from your notebook logic
from src.states import state

app = FastAPI()

# Mount static directory for frontend
import os
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")

@app.get("/")
def read_root():
    return {"message": "Adaptive RAG FastAPI backend is running."}

@app.get("/graph/info")
def get_graph_info():
    return graph_builder.get_graph_info()

@app.get("/llm/info")
def get_llm_info():
    return llm.get_llm_info()

@app.get("/node/info")
def get_node_info():
    return node_implementation.get_node_info()

@app.get("/state/info")
def get_state_info():
    return state.get_state_info()

# --- Main RAG endpoint ---
class QuestionRequest(BaseModel):
    question: str


# Use the compiled workflow graph (app) for answering
from fastapi import Request

@app.post("/rag/answer")
def rag_answer(request: QuestionRequest, fastapi_request: Request):
    # Get OpenAI API key from header if provided
    user_api_key = fastapi_request.headers.get("OPENAI_API_KEY")
    if user_api_key:
        os.environ["OPENAI_API_KEY"] = user_api_key
    steps = []
    import builtins
    orig_print = builtins.print
    def custom_print(*args, **kwargs):
        msg = ' '.join(str(a) for a in args)
        steps.append(msg)
        orig_print(*args, **kwargs)
    builtins.print = custom_print
    try:
        # Use the compiled workflow graph from state.py (should be named 'app')
        result = state.app.invoke({"question": request.question})
    finally:
        builtins.print = orig_print
    answer = result.get("generation", "No answer generated.")
    return {"question": request.question, "answer": answer, "steps": steps}
