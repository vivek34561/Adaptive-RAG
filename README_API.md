# FastAPI Backend

This project includes a FastAPI backend in `backend.py` with endpoints for health checks, model metadata, and chat.

## Run Locally

1. Activate your environment.
2. Set environment variables in `.env` (or your shell):

```env
GROQ_API_KEY=your_groq_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

3. Initialize Supabase tables using `supabase_schema.sql` in your Supabase SQL editor.

4. Start the API server:

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

### `GET /sessions`
Returns conversation sessions ordered by latest message.

### `POST /sessions`
Creates a new conversation session.

### `GET /sessions/{session_id}/messages`
Returns message history for a conversation.

### `POST /chat`
Runs the adaptive RAG graph and returns answer + execution steps. If RAG cannot confidently solve the query, the graph escalates automatically to human review.

Request body:

```json
{
	"question": "What is an AI agent?",
	"groq_api_key": "your_groq_key",
	"session_id": "optional_existing_session_id"
}
```

Notes:
- `groq_api_key` is optional in request if `GROQ_API_KEY` is already set in environment.
- `session_id` is optional. If missing, backend creates a new chat session.
- Each user and assistant message is stored in Supabase PostgreSQL.

Success response:

```json
{
	"session_id": "f0341f0d-0000-0000-0000-6f23f0708d9a",
	"question": "What is an AI agent?",
	"answer": "...",
	"documents_used": 3,
	"escalated": false,
	"escalation_reason": null,
	"steps": [
		"---ROUTE QUESTION---",
		"---ROUTE QUESTION TO RAG---",
		"---RETRIEVE---",
		"---GENERATE---"
	]
}
```
