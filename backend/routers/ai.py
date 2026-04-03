"""
Susu Books - AI Router
Endpoints for Gemma 4 interaction: text chat and image/OCR upload.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import ChatRequest, ChatResponse, ImageChatResponse
from services.gemma_service import GemmaService
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api", tags=["ai"])


# ---------------------------------------------------------------------------
# Text / Voice Chat
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Main chat endpoint. Accepts a user message (from voice or text input),
    sends it through the Gemma 4 function-calling loop, and returns:
      - response: natural language reply from Gemma (in the user's language)
      - transactions: list of transactions that were recorded
      - function_calls: audit log of all function calls made
    """
    svc = GemmaService(db)
    try:
        response_text, transactions, fn_calls = await svc.chat(
            message=payload.message,
            language=payload.language,
            conversation_history=payload.conversation_history,
        )
    except Exception as exc:
        logger.exception("Gemma chat error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {exc}. Is Ollama running with the model loaded?",
        )
    finally:
        await svc.close()

    return ChatResponse(
        response=response_text,
        transactions=transactions,
        function_calls=fn_calls,
        language_detected=payload.language,
    )


# ---------------------------------------------------------------------------
# Image / OCR
# ---------------------------------------------------------------------------

@router.post("/chat/image", response_model=ImageChatResponse)
async def chat_with_image(
    image: UploadFile = File(..., description="Receipt, handwritten note, or product label photo"),
    message: Optional[str] = Form(
        default="What transactions can you see in this image?",
        description="Optional text prompt to accompany the image",
    ),
    language: str = Form(default="en", description="User's language code"),
    db: AsyncSession = Depends(get_db),
):
    """
    OCR endpoint. Accepts an image file (JPEG/PNG/WEBP) and an optional
    text prompt. Gemma 4's vision capability extracts transaction information
    from receipts, handwritten notes, or product labels.
    """
    # Validate content type
    allowed_types = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type: {image.content_type}. Use JPEG, PNG, or WEBP.",
        )

    # Enforce size limit
    max_bytes = settings.max_image_size_mb * 1024 * 1024
    image_bytes = await image.read()
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image too large. Maximum size is {settings.max_image_size_mb}MB.",
        )

    svc = GemmaService(db)
    try:
        response_text, transactions, fn_calls, raw_ocr = await svc.chat_with_image(
            image_bytes=image_bytes,
            text_prompt=message or "What transactions can you see in this image?",
            language=language,
        )
    except Exception as exc:
        logger.exception("Gemma image chat error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI vision service error: {exc}. Is Ollama running with the model loaded?",
        )
    finally:
        await svc.close()

    return ImageChatResponse(
        response=response_text,
        transactions=transactions,
        function_calls=fn_calls,
        raw_ocr_text=raw_ocr,
    )


# ---------------------------------------------------------------------------
# Health / Status
# ---------------------------------------------------------------------------

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
):
    """
    Check connectivity to Ollama and whether the Gemma model is loaded.
    Also verifies database connectivity.
    """
    svc = GemmaService(db)
    ollama_status = await svc.health_check()
    await svc.close()

    # Quick DB check
    try:
        await db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.error("DB health check failed: %s", exc)
        db_ok = False

    return {
        "status": "ok" if (ollama_status["ollama_reachable"] and db_ok) else "degraded",
        "database": "ok" if db_ok else "error",
        **ollama_status,
    }


@router.get("/models")
async def list_models(
    db: AsyncSession = Depends(get_db),
):
    """List Ollama models available on this machine."""
    svc = GemmaService(db)
    status_data = await svc.health_check()
    await svc.close()
    return {
        "available_models": status_data.get("available_models", []),
        "target_model": settings.ollama_model,
        "model_loaded": status_data.get("model_loaded", False),
    }
