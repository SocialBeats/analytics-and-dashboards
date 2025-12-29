"""
Azure Translator endpoints - Translation API
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field

from app.middleware.authentication import get_current_user
from app.middleware.rate_limiter import limiter
from app.services.translator_service import TranslatorService

router = APIRouter()


class TranslationRequest(BaseModel):
    """Request model for translation"""

    text: str = Field(..., description="Text to translate", min_length=1, max_length=10000)
    target_language: str = Field(
        default="es", description="Target language code (e.g., 'es', 'fr', 'de')"
    )
    source_language: str = Field(
        default="en", description="Source language code (e.g., 'en', 'es', 'fr')"
    )


class TranslationResponse(BaseModel):
    """Response model for translation"""

    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    detected_language: str
    confidence: float


def get_translator_service() -> TranslatorService:
    """Factory function for TranslatorService"""
    return TranslatorService()


@router.post(
    "/analytics/translate",
    response_model=TranslationResponse,
    summary="Translate text using Azure Translator",
    description="""
    Translate text from one language to another using Azure Translator API.

    Features:
    - Requires authentication
    - Intelligent caching: Translations are cached for 24 hours based on text + language pair
    - Cached translations served from Redis for performance
    - Falls back to API if cache unavailable
    - Rate limiting: 30 requests/minute (authenticated users)
    - Supports automatic language detection
    - Returns confidence score for detected language

    Common language codes:
    - en: English
    - es: Spanish
    - fr: French
    - de: German
    - it: Italian
    - pt: Portuguese
    - zh-Hans: Chinese (Simplified)
    - ja: Japanese
    - ar: Arabic

    Response includes:
    - Original text
    - Translated text
    - Source and target language codes
    - Detected language (useful when source is auto-detected)
    - Confidence score for language detection

    Error handling:
    - 429: Quota exceeded - Free tier limit reached or rate limit exceeded.
           The API is functioning correctly, please wait or upgrade your plan.
    - 500: API error or connection issue
    """,
)
@limiter.limit("30/minute")
async def translate_text(
    translation_request: TranslationRequest,
    request: Request,
    response: Response,
    user: dict = Depends(get_current_user),
) -> TranslationResponse:
    """
    Translate text using Azure Translator API.

    Endpoint con autenticación que traduce texto entre idiomas.
    Las traducciones se cachean durante 24 horas.
    """
    service = get_translator_service()
    result = await service.translate_text(
        text=translation_request.text,
        target_language=translation_request.target_language,
        source_language=translation_request.source_language,
    )
    return TranslationResponse(**result)


@router.get(
    "/analytics/translate/languages",
    response_model=Dict[str, Any],
    summary="Get supported languages",
    description="""
    Get list of all languages supported by Azure Translator.

    Features:
    - Requires authentication
    - Cached for 7 days
    - Returns language codes, names, and native names
    - Rate limiting: 10 requests/minute

    Response includes translation scope with all supported languages.

    Error handling:
    - 429: Quota exceeded - Free tier limit reached or rate limit exceeded.
           The API is functioning correctly, please wait or upgrade your plan.
    - 500: API error or connection issue
    """,
)
@limiter.limit("10/minute")
async def get_supported_languages(
    request: Request,
    response: Response,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get list of supported languages from Azure Translator.

    Endpoint con autenticación que devuelve los idiomas soportados.
    """
    service = get_translator_service()
    return await service.get_supported_languages()


@router.post(
    "/analytics/translate/quote",
    response_model=TranslationResponse,
    summary="Translate a Quotable quote to Spanish",
    description="""
    Convenience endpoint to translate English quotes (from Quotable API) to Spanish.

    Features:
    - Requires authentication
    - Pre-configured for English to Spanish translation
    - Same caching and rate limiting as standard translate endpoint
    - Rate limiting: 30 requests/minute

    This endpoint is specifically designed to work with quotes from the Quotable API,
    automatically translating them from English to Spanish.

    Error handling:
    - 429: Quota exceeded - Free tier limit reached or rate limit exceeded.
           The API is functioning correctly, please wait or upgrade your plan.
    - 500: API error or connection issue
    """,
)
@limiter.limit("30/minute")
async def translate_quote(
    request: Request,
    response: Response,
    text: str = Query(..., description="Quote text to translate", min_length=1),
    user: dict = Depends(get_current_user),
) -> TranslationResponse:
    """
    Translate a quote from English to Spanish.

    Endpoint específico para traducir quotes de Quotable API.
    """
    service = get_translator_service()
    result = await service.translate_text(text=text, target_language="es", source_language="en")
    return TranslationResponse(**result)
