"""
Data Transfer Objects & Validation Schemas Module
=================================================

This module defines all inbound and outbound data structures for the Voice AI 
Dispatcher API using Pydantic v2 models.

It enforces payload validation rules, data type guarantees, and default bounds 
for voice synthesis parameters before requests reach core service logic.
"""

from pydantic import BaseModel, Field


class VoiceSettingsSchema(BaseModel):
    """
    Validation schema for fine-tuning voice output characteristics in ElevenLabs.
    
    Attributes:
        stability (float): Controls voice consistency vs. emotional variation (0.0 to 1.0).
        similarity_boost (float): Controls voice clarity and adherence to the original speaker (0.0 to 1.0).
    """
    
    stability: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Voice stability factor balancing natural variability against vocal consistency."
    )
    
    similarity_boost: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Clarity enhancement factor enforcing similarity to the target speaker profile."
    )


class SynthesisRequest(BaseModel):
    """
    Inbound request payload schema for batch text-to-speech processing.
    
    Attributes:
        phrases (List[str]): List of text strings to synthesize in parallel (1 to 5 items).
        voice_id (Optional[str]): Target ElevenLabs voice ID override. Defaults to system setting if None.
        delivery_mode (str): Output format preference. Defaults to public 'cloud_url'.
        settings (VoiceSettingsSchema): Fine-tuning settings applied across all requested phrases.
    """
    
    phrases: list[str] = Field(
        ...,
        min_items=1,
        max_items=5,
        description="Array of text phrases to convert into audio. Enforces a maximum batch size of 5 phrases."
    )
    
    voice_id: str | None = Field(
        default=None,
        description="Optional ElevenLabs target voice identifier. Uses system default when omitted."
    )
    
    delivery_mode: str = Field(
        default="cloud_url",
        description="Delivery strategy for audio output (e.g., 'cloud_url' for Supabase public link)."
    )
    
    settings: VoiceSettingsSchema = Field(
        default_factory=VoiceSettingsSchema,
        description="Fine-tuning parameter bundle for emotional range and voice clarity."
    )


class AudioItemResult(BaseModel):
    """
    Outbound model representing an individually processed text phrase and its generated audio asset.
    
    Attributes:
        phrase (str): The original input text string.
        audio_data (str): The resulting public cloud storage URL pointing to the synthesized MP3 asset.
    """
    
    phrase: str = Field(
        ...,
        description="Original input phrase supplied for synthesis."
    )
    
    audio_data: str = Field(
        ...,
        description="Public HTTPS URL pointing to the hosted .mp3 audio asset in Supabase Storage."
    )


class SynthesisResponse(BaseModel):
    """
    Root outbound response payload returned to API consumers upon batch completion.
    
    Attributes:
        status (str): High-level processing execution status indicator.
        total_processed (int): Total number of successfully processed phrases.
        elapsed_time_seconds (float): Total processing time recorded across async synthesis and upload tasks.
        results (List[AudioItemResult]): Collection containing mapped input phrases to their hosted audio URLs.
    """
    
    status: str = Field(
        default="success",
        description="Status flag indicating success or failure state of the batch operation."
    )
    
    total_processed: int = Field(
        ...,
        description="Total count of text phrases successfully synthesized and stored."
    )
    
    elapsed_time_seconds: float = Field(
        ...,
        description="Total duration in seconds spent processing the parallel synthesis batch."
    )
    
    results: list[AudioItemResult] = Field(
        ...,
        description="List containing original phrases paired with their hosted public audio URLs."
    )