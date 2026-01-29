
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

# Prompt for RAG
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful assistant for question-answering. Use the provided context to answer the question. "
        "If the answer is not contained in the context, say you don't know."
    ),
    (
        "human",
        "Question: {question}\n\nContext:\n{context}\n\nAnswer:"
    ),
])

def make_rag_chain(groq_api_key: str):
    """Construct a RAG chain bound to the provided Groq API key."""
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, groq_api_key=groq_api_key)
    return prompt | llm | StrOutputParser()

# Post-processing
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def get_llm_info():
    return {"llm": "Groq Chat model (llama-3.3-70b-versatile) used via make_rag_chain(groq_api_key)."}