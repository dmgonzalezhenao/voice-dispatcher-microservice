"""
Security & Authentication Dependency Module
===========================================

This module implements API key authorization middleware for protecting internal 
microservice endpoints. 

It intercepts incoming requests, extracts the custom 'X-API-KEY' header, and validates 
it against the system's expected 'API_SECRET_KEY' setting. Unauthorized or missing 
keys trigger immediate HTTP 401 Unauthorized exceptions.
"""

from fastapi import Header, HTTPException, status
from backend.config import settings


def verify_api_key(x_api_key: str = Header(..., alias="X-API-KEY")) -> str:
    """
    FastAPI dependency function that validates the caller's authorization key.

    Args:
        x_api_key (str): The secret API key passed in the 'X-API-KEY' HTTP request header.

    Raises:
        HTTPException: 401 UNAUTHORIZED if the header is missing, invalid, or does not 
                       match the configured 'API_SECRET_KEY'.

    Returns:
        str: The validated API key string if authentication succeeds.
    """
    # Compare the provided header against the secret key configured in settings
    if x_api_key != settings.API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access: Invalid or missing X-API-KEY header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # Return the key upon successful verification
    return x_api_key