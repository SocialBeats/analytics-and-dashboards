"""
Azure Translator service - Translation API with Redis caching
"""

import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.exceptions import DatabaseException, QuotaExceededException
from app.core.logging import logger
from app.middleware import rate_limiter


class TranslatorService:
    """Service for Azure Translator API with caching"""

    TRANSLATE_API_PATH = "/translate"
    API_VERSION = "3.0"
    CACHE_KEY_PREFIX = "translator"
    CACHE_TTL = 86400  # 24 horas
    HTTP_TIMEOUT = 10.0

    def __init__(self):
        self.api_key = settings.AZURE_TRANSLATOR_KEY
        self.endpoint = settings.AZURE_TRANSLATOR_ENDPOINT
        self.region = settings.AZURE_TRANSLATOR_REGION

    async def translate_text(
        self, text: str, target_language: str = "es", source_language: str = "en"
    ) -> Dict[str, Any]:
        """
        Translate text using Azure Translator API with caching.

        Args:
            text: Text to translate
            target_language: Target language code (default: 'es' for Spanish)
            source_language: Source language code (default: 'en' for English)

        Returns:
            dict: Translation response with original text, translated text, and metadata

        Raises:
            DatabaseException: If API call fails or configuration is invalid
        """
        # Validar configuración
        if not self.api_key:
            logger.error("Azure Translator API key not configured")
            raise DatabaseException("Azure Translator is not configured")

        # Generar cache key basado en texto y lenguajes
        cache_key = self._generate_cache_key(text, source_language, target_language)

        # Intentar caché
        cached_translation = await self._get_from_cache(cache_key)
        if cached_translation:
            logger.info("Translation served from Redis cache")
            return cached_translation

        logger.info(f"Cache miss - translating from {source_language} to {target_language}")
        fresh_translation = await self._fetch_from_api(text, source_language, target_language)

        # Guardar en caché
        await self._save_to_cache(cache_key, fresh_translation)

        return fresh_translation

    def _generate_cache_key(self, text: str, source_language: str, target_language: str) -> str:
        """Generate a unique cache key for the translation"""
        # Crear un hash del texto para evitar claves muy largas
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"{self.CACHE_KEY_PREFIX}:{source_language}:{target_language}:{text_hash}"

    async def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get translation from Redis cache"""
        if not rate_limiter.redis_client:
            logger.warn("Redis not available - skipping cache")
            return None

        try:
            cached_data = await rate_limiter.redis_client.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit: {cache_key}")
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.warn(f"Cache read failed: {str(e)}")
            return None

    async def _fetch_from_api(
        self, text: str, source_language: str, target_language: str
    ) -> Dict[str, Any]:
        """Fetch translation from Azure Translator API"""
        try:
            # Construir URL
            url = f"{self.endpoint}{self.TRANSLATE_API_PATH}"
            params = {
                "api-version": self.API_VERSION,
                "from": source_language,
                "to": target_language,
            }

            # Construir headers
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Ocp-Apim-Subscription-Region": self.region,
                "Content-Type": "application/json",
                "X-ClientTraceId": str(uuid.uuid4()),
            }

            # Body de la petición
            body = [{"text": text}]

            async with httpx.AsyncClient(timeout=self.HTTP_TIMEOUT, verify=True) as client:
                logger.info(f"Calling Azure Translator API: {url}")
                response = await client.post(url, params=params, headers=headers, json=body)

                # Manejar errores de cuota
                if response.status_code == 403:
                    logger.warn("Azure Translator quota exceeded (403)")
                    raise QuotaExceededException(
                        service="Azure Translator",
                        detail=(
                            "Azure Translator quota exceeded. The free tier limit has been reached. "
                            "The API is functioning correctly, but no more translations can be processed "
                            "until the quota resets or you upgrade your plan."
                        ),
                    )

                if response.status_code == 429:
                    logger.warn("Azure Translator rate limit exceeded (429)")
                    raise QuotaExceededException(
                        service="Azure Translator",
                        detail=(
                            "Azure Translator rate limit exceeded. Too many requests in a short period. "
                            "The API is functioning correctly. Please wait a moment before trying again."
                        ),
                    )

                if response.status_code != 200:
                    logger.error(f"API error: {response.status_code} - {response.text}")
                    raise DatabaseException(
                        f"Azure Translator API returned status {response.status_code}"
                    )

                api_response = response.json()
                logger.info("Translation successful")

                # Formatear respuesta
                if not api_response or len(api_response) == 0:
                    raise DatabaseException("Empty response from Azure Translator")

                translation_result = api_response[0]
                translations = translation_result.get("translations", [])

                if not translations:
                    raise DatabaseException("No translations in response")

                translated_text = translations[0].get("text", "")

                # Construir respuesta estructurada
                result = {
                    "original_text": text,
                    "translated_text": translated_text,
                    "source_language": source_language,
                    "target_language": target_language,
                    "detected_language": translation_result.get("detectedLanguage", {}).get(
                        "language", source_language
                    ),
                    "confidence": translation_result.get("detectedLanguage", {}).get("score", 1.0),
                }

                return result

        except httpx.TimeoutException:
            logger.error("Azure Translator API timeout")
            raise DatabaseException("Azure Translator API timeout")
        except httpx.RequestError as e:
            logger.error(f"Connection error: {str(e)}")
            raise DatabaseException(f"Failed to connect: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {str(e)}")
            raise DatabaseException("Invalid response from API")
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise DatabaseException(f"Failed to translate text: {str(e)}")

    async def _save_to_cache(self, cache_key: str, translation_data: Dict[str, Any]) -> None:
        """Save translation to Redis with TTL"""
        if not rate_limiter.redis_client:
            logger.warn("Redis not available - skipping cache write")
            return

        try:
            cached_value = json.dumps(translation_data)
            await rate_limiter.redis_client.setex(cache_key, self.CACHE_TTL, cached_value)
            logger.info(f"Translation cached with TTL={self.CACHE_TTL}s")
        except Exception as e:
            logger.warn(f"Failed to cache: {str(e)}")

    async def get_supported_languages(self) -> Dict[str, Any]:
        """
        Get list of supported languages from Azure Translator.

        Returns:
            dict: Dictionary with supported languages

        Raises:
            DatabaseException: If API call fails
        """
        if not self.api_key:
            logger.error("Azure Translator API key not configured")
            raise DatabaseException("Azure Translator is not configured")

        cache_key = f"{self.CACHE_KEY_PREFIX}:languages"

        # Intentar caché
        cached_languages = await self._get_from_cache(cache_key)
        if cached_languages:
            logger.info("Languages served from Redis cache")
            return cached_languages

        # Cache miss - fetch from API
        try:
            url = f"{self.endpoint}/languages"
            params = {"api-version": self.API_VERSION, "scope": "translation"}

            async with httpx.AsyncClient(timeout=self.HTTP_TIMEOUT, verify=True) as client:
                logger.info(f"Fetching supported languages: {url}")
                response = await client.get(url, params=params)

                # Manejar errores de cuota
                if response.status_code == 403:
                    logger.warn("Azure Translator quota exceeded (403)")
                    raise QuotaExceededException(
                        service="Azure Translator",
                        detail=(
                            "Azure Translator quota exceeded. The free tier limit has been reached. "
                            "The API is functioning correctly, but no more requests can be processed "
                            "until the quota resets or you upgrade your plan."
                        ),
                    )

                if response.status_code == 429:
                    logger.warn("Azure Translator rate limit exceeded (429)")
                    raise QuotaExceededException(
                        service="Azure Translator",
                        detail=(
                            "Azure Translator rate limit exceeded. Too many requests in a short period. "
                            "The API is functioning correctly. Please wait a moment before trying again."
                        ),
                    )

                if response.status_code != 200:
                    logger.error(f"API error: {response.status_code}")
                    raise DatabaseException(
                        f"Azure Translator API returned status {response.status_code}"
                    )

                languages_data = response.json()
                logger.info("Languages fetched successfully")

                # Guardar en caché con TTL más largo (7 días)
                await self._save_to_cache(cache_key, languages_data)

                return languages_data

        except httpx.TimeoutException:
            logger.error("Azure Translator API timeout")
            raise DatabaseException("Azure Translator API timeout")
        except httpx.RequestError as e:
            logger.error(f"Connection error: {str(e)}")
            raise DatabaseException(f"Failed to connect: {str(e)}")
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise DatabaseException(f"Failed to fetch languages: {str(e)}")
