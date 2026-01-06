from src.graphs.graph_builder import get_retriever
from src.llms.llm import make_rag_chain, format_docs
from langchain_core.documents import Document
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from typing import Literal

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
    print("---GENERATE---")
    question = state["question"]
    documents = state["documents"]
    openai_api_key = state.get("openai_api_key")
    if not openai_api_key:
        raise ValueError("OpenAI API key is required for generation.")
    # Normalize documents to text context
    if isinstance(documents, list):
        if documents and isinstance(documents[0], Document):
            context_text = format_docs(documents)
        else:
            context_text = "\n\n".join(str(d) for d in documents)
    elif isinstance(documents, Document):
        context_text = documents.page_content
    else:
        context_text = str(documents)

    generation = make_rag_chain(openai_api_key).invoke({"context": context_text, "question": question})
    return {"documents": documents, "question": question, "generation": generation, "openai_api_key": openai_api_key}


# --- ADAPTIVE RAG NODES ---
def grade_documents(state):
    print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state["question"]
    documents = state["documents"]
    openai_api_key = state.get("openai_api_key")

    class GradeDocuments(BaseModel):
        binary_score: str = Field(description="Documents are relevant to the question, 'yes' or 'no'")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)
    system = (
        "You are a grader assessing relevance of a retrieved document to a user question.\n "
        "If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant.\n"
        "It does not need to be a stringent test. The goal is to filter out erroneous retrievals.\n"
        "Give a binary score 'yes' or 'no' to indicate whether the document is relevant to the question."
    )
    grade_prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", "Retrieved document:\n\n {document} \n\n User question: {question}"),
    ])
    retrieval_grader = grade_prompt | llm.with_structured_output(GradeDocuments)

    filtered_docs = []
    for d in documents:
        score = retrieval_grader.invoke({"question": question, "document": getattr(d, "page_content", str(d))})
        if getattr(score, "binary_score", "no") == "yes":
            print("---GRADE: DOCUMENT RELEVANT---")
            filtered_docs.append(d)
        else:
            print("---GRADE: DOCUMENT NOT RELEVANT---")
    return {"documents": filtered_docs, "question": question, "openai_api_key": openai_api_key}

def transform_query(state):
    print("---TRANSFORM QUERY---")
    question = state["question"]
    documents = state["documents"]
    openai_api_key = state.get("openai_api_key")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)
    system = (
        "You are a question re-writer that converts an input question to a better version optimized for vectorstore retrieval.\n "
        "Look at the input and reason about the underlying semantic intent/meaning."
    )
    re_write_prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", "Here is the initial question:\n\n {question} \n Formulate an improved question."),
    ])
    question_rewriter = re_write_prompt | llm | StrOutputParser()
    better_question = question_rewriter.invoke({"question": question})
    return {"documents": documents, "question": better_question, "openai_api_key": openai_api_key}

def route_question(state):
    print("---ROUTE QUESTION---")
    question = state["question"]
    openai_api_key = state.get("openai_api_key")

    class RouteQuery(BaseModel):
        datasource: Literal["vectorstore", "web_search"] = Field(
            ..., description="Choose to route to web search or a vectorstore."
        )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)
    system = (
        "You are an expert at routing a user question to a vectorstore or web search."
        "The vectorstore contains documents related to agents, prompt engineering, and adversarial attacks."
        "Use the vectorstore for questions on these topics. Otherwise, use web-search."
    )
    route_prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", "{question}"),
    ])
    question_router = route_prompt | llm.with_structured_output(RouteQuery)
    source = question_router.invoke({"question": question})
    if source.datasource == "web_search":
        print("---ROUTE QUESTION TO WEB SEARCH---")
        return "web_search"
    else:
        print("---ROUTE QUESTION TO RAG---")
        return "vectorstore"

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
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]
    openai_api_key = state.get("openai_api_key")

    class GradeHallucinations(BaseModel):
        binary_score: str = Field(description="Answer is grounded in the facts, 'yes' or 'no'")

    class GradeAnswer(BaseModel):
        binary_score: str = Field(description="Answer addresses the question, 'yes' or 'no'")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)

    hallucination_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a grader assessing whether an LLM generation is grounded in a set of retrieved facts. Give 'yes' or 'no'."),
        ("human", "Set of facts:\n\n {documents} \n\n LLM generation: {generation}"),
    ])
    hallucination_grader = hallucination_prompt | llm.with_structured_output(GradeHallucinations)

    answer_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a grader assessing whether an answer addresses/resolves a question. Give 'yes' or 'no'."),
        ("human", "User question:\n\n {question} \n\n LLM generation: {generation}"),
    ])
    answer_grader = answer_prompt | llm.with_structured_output(GradeAnswer)

    # For documents input, provide text to graders
    if isinstance(documents, list) and documents and isinstance(documents[0], Document):
        docs_text = format_docs(documents)
    elif isinstance(documents, Document):
        docs_text = documents.page_content
    else:
        docs_text = str(documents)

    score = hallucination_grader.invoke({"documents": docs_text, "generation": generation})
    if getattr(score, "binary_score", "no") == "yes":
        print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        score2 = answer_grader.invoke({"question": question, "generation": generation})
        if getattr(score2, "binary_score", "no") == "yes":
            print("---DECISION: GENERATION ADDRESSES QUESTION---")
            return "useful"
        else:
            print("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
            return "not useful"
    else:
        print("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        return "not supported"

def get_node_info():
    return {"node": "Node functions for retrieve and generate implemented."}



