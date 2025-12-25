
from typing import List
from typing_extensions import TypedDict
from langgraph.graph import END, StateGraph, START
from src.nodes.node_implementation import retrieve, generate

class GraphState(TypedDict):
    question: str
    generation: str
    documents: List[str]

# Build workflow graph (minimal, can be extended)
workflow = StateGraph(GraphState)
workflow.add_node("retrieve", retrieve)
workflow.add_node("generate", generate)
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)
workflow.add_edge(START, "retrieve")
app = workflow.compile()

def get_state_info():
    return {"state": "Graph state and workflow compiled."}
