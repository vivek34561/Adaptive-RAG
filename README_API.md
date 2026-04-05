# FastAPI Backend

This project includes a FastAPI backend in `backend.py` with endpoints for health checks, model metadata, and chat.

## Run Locally

1. Activate your environment.
2. Set environment variables in `.env` (or your shell):

```env
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
```

3. Start the API server:

```powershell
uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

### `GET /`
Returns a basic server message.

### `GET /health`
Returns API health status.

Response:

```json
{
	"status": "healthy"
}
```

### `GET /models`
Returns model and routing metadata used by the backend.

### `POST /chat`
Runs the adaptive RAG graph and returns answer + execution steps.

Request body:

```json
{
	"question": "What is an AI agent?",
	"groq_api_key": "your_groq_key",
	"tavily_api_key": "optional_tavily_key"
}
```

Notes:
- `groq_api_key` is optional in request if `GROQ_API_KEY` is already set in environment.
- `tavily_api_key` is optional. If omitted, backend uses `TAVILY_API_KEY` from environment.

Success response:

```json
{
	"question": "What is an AI agent?",
	"answer": "...",
	"documents_used": 3,
	"steps": [
		"---ROUTE QUESTION---",
		"---ROUTE QUESTION TO RAG---",
		"---RETRIEVE---",
		"---GENERATE---"
	]
}
```
