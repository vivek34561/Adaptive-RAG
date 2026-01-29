from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from dotenv import load_dotenv
import os


load_dotenv()

from src.states import state

app = FastAPI(
    title="Adaptive RAG API",
    description="FastAPI backend for Adaptive RAG Chat with Groq LLM",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(..., description="User's question to the RAG system")
    groq_api_key: Optional[str] = Field(None, description="Groq API key (optional if set in environment)")
    tavily_api_key: Optional[str] = Field(None, description="Tavily API key for web search (optional)")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="Generated answer from the RAG system")
    question: str = Field(..., description="Original question")
    steps: List[str] = Field(default_factory=list, description="Processing steps taken")
    documents_used: int = Field(0, description="Number of documents used in generation")

class HealthResponse(BaseModel):
    status: str
    message: str


def get_groq_api_key(request: ChatRequest) -> str:
    """Get Groq API key from request or environment"""
    api_key = request.groq_api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Groq API key is required. Provide it in the request or set GROQ_API_KEY environment variable."
        )
    return api_key


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - API health check"""
    return HealthResponse(
        status="healthy",
        message="Adaptive RAG API is running. Visit /docs for API documentation."
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="API is operational"
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, groq_api_key: str = Depends(get_groq_api_key)):
    """
    Process a question through the Adaptive RAG system
    
    - **question**: The user's question
    - **groq_api_key**: Optional Groq API key (uses environment variable if not provided)
    - **tavily_api_key**: Optional Tavily API key for web search
    """
    try:
      
        if request.tavily_api_key:
            os.environ["TAVILY_API_KEY"] = request.tavily_api_key
        
    
        steps = []
        import builtins
        orig_print = builtins.print
        
        def custom_print(*args, **kwargs):
            msg = ' '.join(str(a) for a in args)
            steps.append(msg)
            orig_print(*args, **kwargs)
        
        builtins.print = custom_print
        
        try:
            result = state.app.invoke({
                "question": request.question,
                "groq_api_key": groq_api_key
            })
        finally:
            builtins.print = orig_print
        
        answer = result.get("generation", "No answer generated.")
        documents = result.get("documents", [])
        
        return ChatResponse(
            answer=answer,
            question=request.question,
            steps=steps,
            documents_used=len(documents) if documents else 0
        )
    
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        error_msg = str(e)
        if "api key" in error_msg.lower():
            raise HTTPException(
                status_code=401,
                detail=f"Invalid or missing API key: {error_msg}"
            )
        raise HTTPException(status_code=500, detail=f"Internal server error: {error_msg}")

@app.get("/models")
async def get_models():
    """Get information about the models being used"""
    return {
        "llm": "llama-3.3-70b-versatile (Groq)",
        "embeddings": "sentence-transformers/all-MiniLM-L6-v2 (HuggingFace)",
        "provider": "Groq"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
