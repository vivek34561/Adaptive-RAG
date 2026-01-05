from src.graphs.graph_builder import get_retriever


from src.graphs.graph_builder import get_retriever
from src.llms.llm import make_rag_chain
from langchain_core.documents import Document
from langchain_community.tools.tavily_search import TavilySearchResults
def router(state):
    print("---ROUTE QUESTION---")
    print("---ROUTE QUESTION TO RAG---")
    return "vectorstore"

# Web search node
def web_search(state):
    print("---WEB SEARCH---")
    import os
    question = state["question"]
    openai_api_key = state.get("openai_api_key")
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        print("---WEB SEARCH DISABLED: missing TAVILY_API_KEY---")
        return {"documents": [], "question": question, "openai_api_key": openai_api_key}
    tool = TavilySearchResults(k=3, tavily_api_key=tavily_key)
    docs = tool.invoke({"query": question})
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
    if not openai_api_key:
        raise ValueError("OpenAI API key is required for generation.")
    generation = make_rag_chain(openai_api_key).invoke({"context": documents, "question": question})
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



