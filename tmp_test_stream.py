import asyncio
import os
import sys

# add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.states import state
from dotenv import load_dotenv

load_dotenv()

async def main():
    async for event in state.app.astream_events(
        {
            "question": "what is AI?",
            "chat_history": "",
            "groq_api_key": os.getenv("GROQ_API_KEY"),
            "retrieval_attempts": 0,
            "generation_attempts": 0,
            "escalated": False,
            "escalation_reason": "",
        },
        version="v1"
    ):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                print(content, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
