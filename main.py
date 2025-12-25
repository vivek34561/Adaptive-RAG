
# Load environment variables and set API keys
import os
from dotenv import load_dotenv
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")

# Start FastAPI server
import uvicorn
from src.backend import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
