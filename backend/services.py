"""
Core External Services Integration Module
=========================================

This module manages external integration boundaries for the microservice:
1. ElevenLabs REST API: Handles asynchronous Text-to-Speech (TTS) audio synthesis.
2. Supabase Cloud Storage: Handles bucket operations and public CDN URL resolution for generated .mp3 assets.

It uses asynchronous HTTP clients (`httpx.AsyncClient`) to enable concurrent 
non-blocking API executions across batches of phrases.
"""

import uuid
import httpx
from fastapi import HTTPException, status
from supabase import create_client, Client
from backend.config import settings

# Initialize the global Supabase client singleton using validated environment credentials
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


async def synthesize_elevenlabs(
    client: httpx.AsyncClient,
    text: str,
    voice_id: str | None,
    stability: float,
    similarity_boost: float,
    custom_elevenlabs_key: str | None = None
) -> bytes:
    """
    Asynchronously converts a single text phrase into binary MP3 audio data via ElevenLabs API.

    Args:
        client (httpx.AsyncClient): Shared non-blocking HTTP client instance.
        text (str): Plain text phrase to be synthesized into speech.
        voice_id (str | None): Optional target voice ID. Falls back to system default if None.
        stability (float): Fine-tuning stability factor (0.0 to 1.0).
        similarity_boost (float): Fine-tuning speaker similarity factor (0.0 to 1.0).
        custom_elevenlabs_key (str | None): Dynamic per-request API key override for multi-tenant or demo modes.

    Raises:
        HTTPException: 502 BAD GATEWAY if ElevenLabs returns an error status code.
        HTTPException: 503 SERVICE UNAUTHORIZED if network connectivity fails.

    Returns:
        bytes: Raw binary content of the generated .mp3 audio file.
    """
    # Determine effective API key: prioritize user-provided key over system environment default
    api_key_to_use = custom_elevenlabs_key or settings.ELEVENLABS_API_KEY
    
    # Fall back to configured default voice ID if no specific voice ID was supplied
    target_voice = voice_id or settings.DEFAULT_VOICE_ID
    
    # Construct ElevenLabs Text-to-Speech REST endpoint URL
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{target_voice}"
    
    # Prepare authorization and content headers
    headers = {
        "xi-api-key": api_key_to_use,
        "Content-Type": "application/json"
    }
    
    # Construct payload using multilingual model v2 for natural accents
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost
        }
    }
    
    try:
        # Issue non-blocking POST request to ElevenLabs synthesis endpoint
        response = await client.post(url, json=payload, headers=headers, timeout=30.0)
        
        # Intercept upstream errors and translate them into descriptive HTTPExceptions
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"ElevenLabs synthesis error ({response.status_code}): {response.text}"
            )
            
        # Return binary MP3 payload upon success
        return response.content

    except httpx.RequestError as exc:
        # Catch connection timeouts or DNS resolution issues
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to communicate with ElevenLabs voice service: {str(exc)}"
        )


async def upload_to_supabase(audio_bytes: bytes) -> str:
    """
    Persists binary MP3 audio bytes to Supabase Cloud Storage and retrieves its public HTTPS URL.

    Args:
        audio_bytes (bytes): Binary content of the MP3 audio file.

    Raises:
        HTTPException: 500 INTERNAL SERVER ERROR if bucket upload or URL extraction fails.

    Returns:
        str: Publicly accessible HTTPS CDN URL pointing to the uploaded audio asset.
    """
    # Generate a collision-free unique filename using UUID4
    filename = f"audio_{uuid.uuid4().hex[:8]}.mp3"
    
    try:
        # Perform file upload operation to the configured Supabase Storage bucket
        supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
            path=filename,
            file=audio_bytes,
            file_options={"content-type": "audio/mpeg"}
        )
        
        # Resolve and return the public CDN URL for the uploaded file asset
        public_url = supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(filename)
        return public_url

    except Exception as exc:
        # Handle storage quota limits, bucket permission errors, or network issues
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist audio asset to Supabase Storage: {str(exc)}"
        )