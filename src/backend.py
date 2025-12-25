
import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from pydantic import BaseModel
from src.graphs import graph_builder
from src.llms import llm
from src.nodes import node_implementation
from src.states import state

app = FastAPI()

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

@app.post("/rag/answer")
def rag_answer(request: QuestionRequest):
    # Run the workflow graph with the user's question
    result = state.app.invoke({"question": request.question})
    # The result should contain the answer in 'generation'
    answer = result.get("generation", "No answer generated.")
    return {"question": request.question, "answer": answer}
