import json
import re

from fastapi import HTTPException, status
from groq import GroqError
from pydantic import ValidationError

from src.app.schemas.voice import InstructionPayload
from src.app.services.groq_client import complete_chat
from src.app.store.tasks import list_tasks

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)

SYSTEM_PROMPT = """You are a routing assistant for a voice-controlled todo list API.

Given a user transcription and the current task list, respond with ONLY a JSON object (no markdown, no explanation) with exactly these keys:
- "endpoint": string path (e.g. "/tasks" or "/tasks/3")
- "method": one of GET, POST, PUT, PATCH, DELETE
- "params": object with request body fields (use {} when none are needed)

Available endpoints:
- GET /tasks — list all tasks. params: {}
- POST /tasks — create task. params: { "title": string, "done": boolean (optional, default false) }
- PUT /tasks/{id} — replace task. params: { "title": string, "done": boolean }
- PATCH /tasks/{id} — partial update. params: any of { "title": string, "done": boolean }
- DELETE /tasks/{id} — delete task. params: {}

Current tasks:
__TASKS_JSON__

Example:
User: "add buy groceries to my list"
Response: {"endpoint": "/tasks", "method": "POST", "params": {"title": "Buy groceries"}}

Put the task id in the endpoint path for PUT, PATCH, and DELETE (e.g. "/tasks/2"), not in params.
"""


def build_system_prompt() -> str:
    current_tasks = [task.model_dump() for task in list_tasks()]
    return SYSTEM_PROMPT.replace(
        "__TASKS_JSON__",
        json.dumps(current_tasks, indent=2),
    )


def _parse_llm_json(raw: str) -> dict:
    cleaned = _JSON_FENCE_RE.sub("", raw.strip()).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM returned invalid JSON: {exc.msg}",
        ) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM response must be a JSON object.",
        )
    return parsed


def route_transcription(transcription: str) -> InstructionPayload:
    try:
        raw_response = complete_chat(build_system_prompt(), transcription)
    except GroqError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq API error during routing: {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    parsed = _parse_llm_json(raw_response)
    try:
        return InstructionPayload.model_validate(parsed)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM routing JSON failed validation: {exc.errors()}",
        ) from exc
