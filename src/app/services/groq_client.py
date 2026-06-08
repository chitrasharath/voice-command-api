import io
from functools import lru_cache

from groq import Groq

from src.app.core.config import get_settings


@lru_cache
def get_groq_client() -> Groq:
    settings = get_settings()
    return Groq(api_key=settings.groq_api_key)


def transcribe_audio(
    file_bytes: bytes,
    filename: str,
    language: str | None = None,
) -> str:
    settings = get_settings()
    client = get_groq_client()
    kwargs: dict = {
        "model": settings.groq_transcription_model,
        "file": (filename, io.BytesIO(file_bytes)),
        "response_format": "json",
        "timeout": settings.request_timeout_seconds,
    }
    if language:
        kwargs["language"] = language

    response = client.audio.transcriptions.create(**kwargs)
    text = response.text.strip() if response.text else ""
    if not text:
        raise ValueError("Groq Whisper returned an empty transcription.")
    return text


def complete_chat(system_prompt: str, user_message: str) -> str:
    settings = get_settings()
    client = get_groq_client()
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
        timeout=settings.request_timeout_seconds,
    )
    content = response.choices[0].message.content
    if not content or not content.strip():
        raise ValueError("Groq LLM returned an empty response.")
    return content.strip()
