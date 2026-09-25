"""
Centralized Configuration Module (Fail-Fast Pattern)
===================================================

This module manages the loading, validation, and retrieval of all environment 
variables required by the microservice using 'pydantic-settings' and 'python-dotenv'.

By explicitly executing 'load_dotenv()', environment parameters defined in the root 
.env file are injected into OS environment variables before Pydantic instantiates 
the Settings model. If any required credential is missing, application execution 
will fail instantly during startup.
"""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from the root .env file into os.environ
load_dotenv()


class Settings(BaseSettings):
    """
    Main application settings class mapping system environment variables.
    
    Inherits from Pydantic's BaseSettings to enforce strict type checking,
    required values presence, and runtime configuration validation.
    """
    
    # Internal authorization secret key expected in incoming X-API-KEY request headers
    API_SECRET_KEY: str
    
    # ElevenLabs API authentication credential used for Text-to-Speech synthesis
    ELEVENLABS_API_KEY: str
    
    # Default ElevenLabs voice identifier (Rachel) used when no specific voice is provided
    DEFAULT_VOICE_ID: str = "pNInz6obpgDQGcFmaJgB"
    
    # Base URL for the target Supabase project instance
    SUPABASE_URL: str
    
    # Public/Anonymous API Key for Supabase SDK authentication
    SUPABASE_KEY: str
    
    # Target Supabase Storage Bucket name designated for hosting audio files
    SUPABASE_BUCKET: str

    # Pydantic configuration settings
    model_config = SettingsConfigDict(
        # Read directly from environment variables populated by load_dotenv()
        env_file_encoding="utf-8",
        # Ignore extra non-declared environment variables without raising an exception
        extra="ignore"
    )


# Global singleton instance instantiated upon module import
settings = Settings()