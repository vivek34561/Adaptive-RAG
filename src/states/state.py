

from langgraph.graph import END, StateGraph, START
from src.nodes.node_implementation import (
    human_escalation,
    retrieve,
    grade_documents,
    generate,
    transform_query,
    route_question,
    decide_to_generate,
    grade_generation_v_documents_and_question,
)

# Define the graph state structure (matching notebook)
from typing import List
from typing_extensions import TypedDict
from langchain_core.documents import Document

class GraphState(TypedDict):
    question: str
    generation: str
    documents: List[Document]
    groq_api_key: str
    retrieval_attempts: int
    generation_attempts: int
    escalated: bool
    escalation_reason: str

# Build the adaptive RAG workflow graph
workflow = StateGraph(GraphState)

# Define the nodes
workflow.add_node("human_escalation", human_escalation)  # human escalation
workflow.add_node("retrieve", retrieve)  # retrieve
workflow.add_node("grade_documents", grade_documents)  # grade documents
workflow.add_node("generate", generate)  # generate
workflow.add_node("transform_query", transform_query)  # transform_query

# Build graph edges and logic
workflow.add_conditional_edges(
    START,
    route_question,
    {
        "human_escalation": "human_escalation",
        "vectorstore": "retrieve",
    },
)
workflow.add_edge("human_escalation", END)
workflow.add_edge("retrieve", "grade_documents")
workflow.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {
        "transform_query": "transform_query",
        "generate": "generate",
        "human_escalation": "human_escalation",
    },
)
workflow.add_edge("transform_query", "retrieve")
workflow.add_conditional_edges(
    "generate",
    grade_generation_v_documents_and_question,
    {
        "not supported": "generate",
        "useful": END,
        "not useful": "transform_query",
        "human_escalation": "human_escalation",
    },
)

# Compile the workflow graph
app = workflow.compile()