
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

# LLM
llm = ChatGroq(model_name="openai/gpt-oss-120b", temperature=0)

# Post-processing
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# Chain
rag_chain = prompt | llm | StrOutputParser()

def get_llm_info():
    return {"llm": "LLM and RAG chain initialized."}
