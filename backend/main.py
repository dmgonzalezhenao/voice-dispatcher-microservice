"""
Main Application Entrypoint & Router Module
============================================

This module initializes the core FastAPI application instance, sets up Cross-Origin 
Resource Sharing (CORS) middleware, and exposes the primary batch voice dispatching 
API endpoint.

It orchestrates asynchronous execution across ElevenLabs text-to-speech synthesis 
and Supabase cloud storage persistence using `asyncio.gather` for optimal concurrency.
"""

import asyncio
import time
from fastapi import FastAPI, Depends, Header, status, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.schemas import SynthesisRequest, SynthesisResponse, AudioItemResult
from backend.security import verify_api_key
from backend.services import synthesize_elevenlabs, upload_to_supabase

# Initialize the primary FastAPI application instance
app = FastAPI(
    title="Voice AI Microservice Dispatcher",
    description="High-performance asynchronous microservice for voice synthesis and cloud asset dispatch.",
    version="1.0.0"
)

# Initialize rate limiter using client remote IP address
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure Cross-Origin Resource Sharing (CORS) for external frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Simple health check endpoint used by deployment platforms (Render/Railway/Kubernetes) 
    to verify service availability.
    """
    return {"status": "healthy", "service": "voice-dispatcher-microservice"}


@app.post(
    "/api/v1/dispatch",
    response_model=SynthesisResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)]
)
@limiter.limit("3/day", exempt_when=lambda request: bool(request.headers.get("X-ElevenLabs-Key")))
async def dispatch_tts(
    request: Request,
    payload: SynthesisRequest,
    x_elevenlabs_key: str | None = Header(default=None, alias="X-ElevenLabs-Key")
):
    """
    Batch Voice Dispatching Endpoint.

    Processes an array of text phrases in parallel, synthesizes audio via ElevenLabs, 
    persists generated files to Supabase Storage, and returns public CDN URLs.

    Args:
        payload (SynthesisRequest): Validated input containing phrases and voice settings.
        x_elevenlabs_key (str | None): Dynamic ElevenLabs API key passed in request headers.

    Returns:
        SynthesisResponse: Payload containing total items processed, latency, and asset URLs.
    """
    start_time = time.perf_counter()

    # Traffic light system to limit simultaneous calls to ElevenLabs to a maximum of two.
    semaphore = asyncio.Semaphore(2)

    async def safe_synthesize(phrase: str) -> bytes:
        async with semaphore:
            return await synthesize_elevenlabs(
                client=client,
                text=phrase,
                voice_id=payload.voice_id,
                stability=payload.settings.stability,
                similarity_boost=payload.settings.similarity_boost,
                custom_elevenlabs_key=x_elevenlabs_key
            )

    async with httpx.AsyncClient() as client:
        # Step 1: Trigger asynchronous synthesis while respecting the semaphore (maximum of 2 in parallel).
        tts_tasks = [safe_synthesize(phrase) for phrase in payload.phrases]
        audio_bytes_list = await asyncio.gather(*tts_tasks)

        # Step 2: Upload to Supabase in parallel (no concurrency restriction)
        upload_tasks = [
            upload_to_supabase(audio_bytes) 
            for audio_bytes in audio_bytes_list
        ]
        public_urls = await asyncio.gather(*upload_tasks)

    elapsed_time = time.perf_counter() - start_time

    results = [
        AudioItemResult(phrase=phrase, audio_data=url)
        for phrase, url in zip(payload.phrases, public_urls)
    ]

    return SynthesisResponse(
        status="success",
        total_processed=len(results),
        elapsed_time_seconds=round(elapsed_time, 2),
        results=results
    )