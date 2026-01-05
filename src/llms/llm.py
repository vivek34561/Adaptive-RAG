
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

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

def make_rag_chain(openai_api_key: str):
    """Construct a RAG chain bound to the provided OpenAI API key."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)
    return prompt | llm | StrOutputParser()

# Post-processing
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def get_llm_info():
    return {"llm": "OpenAI Chat model used via make_rag_chain(openai_api_key)."}
