from fastapi import APIRouter, HTTPException, Request, status
from groq import GroqError

from src.app.schemas.voice import TranscribeFlowResponse
from src.app.services.groq_client import transcribe_audio
from src.app.services.instruction import route_transcription
from src.app.services.task_executor import execute_instruction
from src.app.utils.language import normalize_transcription_language

router = APIRouter(tags=["transcribe"])


@router.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


async def _extract_transcription(request: Request) -> str:
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if upload is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'file' in multipart form data.",
            )
        file_bytes = await upload.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded audio file is empty.",
            )
        filename = getattr(upload, "filename", None) or "command.webm"
        language = normalize_transcription_language(form.get("language"))
        try:
            return transcribe_audio(file_bytes, filename, language)
        except GroqError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Groq API error during transcription: {exc}",
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

    if content_type.startswith("application/json"):
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JSON body must be an object.",
            )
        transcription = body.get("transcription")
        if not isinstance(transcription, str) or not transcription.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing or invalid 'transcription' field.",
            )
        return transcription.strip()

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Use multipart/form-data with 'file' or application/json with 'transcription'.",
    )


@router.post("/transcribe", response_model=TranscribeFlowResponse)
async def transcribe_and_run_flow(request: Request) -> TranscribeFlowResponse:
    transcription = await _extract_transcription(request)
    instruction = route_transcription(transcription)
    result = execute_instruction(instruction)
    return TranscribeFlowResponse(
        transcription=transcription,
        instruction=instruction,
        result=result,
    )
