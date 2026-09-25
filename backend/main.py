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
from fastapi import FastAPI, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
import httpx

from backend.schemas import SynthesisRequest, SynthesisResponse, AudioItemResult
from backend.security import verify_api_key
from backend.services import synthesize_elevenlabs, upload_to_supabase

# Initialize the primary FastAPI application instance
app = FastAPI(
    title="Voice AI Microservice Dispatcher",
    description="High-performance asynchronous microservice for voice synthesis and cloud asset dispatch.",
    version="1.0.0"
)

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
async def dispatch_tts(
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
    # Start high-precision execution timer to benchmark end-to-end performance
    start_time = time.perf_counter()

    # Instantiate a shared async HTTP client session for non-blocking network calls
    async with httpx.AsyncClient() as client:
        # Step 1: Create concurrent asynchronous TTS synthesis tasks for each phrase
        tts_tasks = [
            synthesize_elevenlabs(
                client=client,
                text=phrase,
                voice_id=payload.voice_id,
                stability=payload.settings.stability,
                similarity_boost=payload.settings.similarity_boost,
                custom_elevenlabs_key=x_elevenlabs_key
            )
            for phrase in payload.phrases
        ]
        
        # Execute all voice synthesis requests concurrently in parallel
        audio_bytes_list = await asyncio.gather(*tts_tasks)

        # Step 2: Create concurrent upload tasks to persist synthesized audio to Supabase
        upload_tasks = [
            upload_to_supabase(audio_bytes) 
            for audio_bytes in audio_bytes_list
        ]
        
        # Execute all cloud uploads concurrently in parallel
        public_urls = await asyncio.gather(*upload_tasks)

    # Compute total processing latency in seconds
    elapsed_time = time.perf_counter() - start_time

    # Map original text phrases to their corresponding public storage CDN URLs
    results = [
        AudioItemResult(phrase=phrase, audio_data=url)
        for phrase, url in zip(payload.phrases, public_urls)
    ]

    # Construct and return standardized API response
    return SynthesisResponse(
        status="success",
        total_processed=len(results),
        elapsed_time_seconds=round(elapsed_time, 2),
        results=results
    )