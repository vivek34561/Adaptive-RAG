from src.graphs.graph_builder import get_retriever


from src.graphs.graph_builder import get_retriever
from src.llms.llm import rag_chain
from langchain_core.documents import Document
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_openai import ChatOpenAI

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Literal

# Router node
class RouteQuery(BaseModel):
    datasource: Literal["vectorstore", "web_search"] = Field(...)


system = (
    "You are an expert at routing a user question to a vectorstore or web search. "
    "The vectorstore contains documents related to agents, prompt engineering, and adversarial attacks. "
    "Use the vectorstore for questions on these topics. Otherwise, use web-search."
)
route_prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "{question}"),
])

def router(state):
    question = state["question"]
    openai_api_key = state.get("openai_api_key")
    if not openai_api_key:
        raise ValueError("OpenAI API key is required for routing.")
    llm_router = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)
    structured_llm_router = llm_router.with_structured_output(RouteQuery)
    question_router = route_prompt | structured_llm_router
    route = question_router.invoke({"question": question})
    if route.datasource == "web_search":
        print("---ROUTE QUESTION---")
        print("---ROUTE QUESTION TO WEB SEARCH---")
        return "web_search"
    else:
        print("---ROUTE QUESTION---")
        print("---ROUTE QUESTION TO RAG---")
        return "vectorstore"

# Web search node
web_search_tool = TavilySearchResults(k=3)
def web_search(state):
    print("---WEB SEARCH---")
    question = state["question"]
    openai_api_key = state.get("openai_api_key")
    docs = web_search_tool.invoke({"query": question})
    web_results = "\n".join([d["content"] for d in docs])
    web_doc = Document(page_content=web_results)
    return {"documents": [web_doc], "question": question, "openai_api_key": openai_api_key}


# Node: retrieve
def retrieve(state):
    print("---RETRIEVE---")
    question = state["question"]
    openai_api_key = state.get("openai_api_key")
    if not openai_api_key:
        raise ValueError("OpenAI API key is required for embeddings.")
    retriever = get_retriever(openai_api_key)
    documents = retriever.invoke(question)
    return {"documents": documents, "question": question, "openai_api_key": openai_api_key}



# Node: generate
def generate(state):
    question = state["question"]
    documents = state["documents"]
    openai_api_key = state.get("openai_api_key")
    generation = rag_chain.invoke({"context": documents, "question": question})
    return {"documents": documents, "question": question, "generation": generation, "openai_api_key": openai_api_key}


# --- ADAPTIVE RAG NODES ---
def grade_documents(state):
    print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state["question"]
    documents = state["documents"]
    # Dummy: pass all documents as relevant
    return {"documents": documents, "question": question}

def transform_query(state):
    print("---TRANSFORM QUERY---")
    question = state["question"]
    documents = state["documents"]
    # Dummy: just return the same question
    better_question = question
    return {"documents": documents, "question": better_question}

def route_question(state):
    return router(state)

def decide_to_generate(state):
    print("---ASSESS GRADED DOCUMENTS---")
    filtered_documents = state["documents"]
    if not filtered_documents:
        print("---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY---")
        return "transform_query"
    else:
        print("---DECISION: GENERATE---")
        return "generate"

def grade_generation_v_documents_and_question(state):
    print("---CHECK HALLUCINATIONS---")
    # Dummy: always return 'useful' to end the workflow
    return "useful"

def get_node_info():
    return {"node": "Node functions for retrieve and generate implemented."}



