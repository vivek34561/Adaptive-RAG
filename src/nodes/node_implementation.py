
from src.graphs.graph_builder import retriever
from src.llms.llm import rag_chain
from langchain_core.documents import Document

# Node: retrieve
def retrieve(state):
    question = state["question"]
    documents = retriever.invoke(question)
    return {"documents": documents, "question": question}

# Node: generate
def generate(state):
    question = state["question"]
    documents = state["documents"]
    generation = rag_chain.invoke({"context": documents, "question": question})
    return {"documents": documents, "question": question, "generation": generation}

def get_node_info():
    return {"node": "Node functions for retrieve and generate implemented."}
